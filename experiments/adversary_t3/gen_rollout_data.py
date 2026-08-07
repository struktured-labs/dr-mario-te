#!/usr/bin/env python3
"""Off-policy data generation for the learned adversary's value model.

DIVERSITY BY DESIGN, not an afterthought: a corpus generated only from the
evolved adversary's own rollouts teaches the value model that adversary's narrow
style and nothing else -- exactly the exploration failure mode team-lead flagged.
Behaviour policies are mixed on purpose:
  evofam   40% -- the best evolved vector + Gaussian-perturbed neighbours (dense
                  coverage near what's already known to work)
  random   30% -- broadly-sampled random adversary vectors, same bounds as the
                  ES search (genuine novelty -- states the evolved policy would
                  never visit)
  selfplay 15% -- champion mirror (negative-heavy, but calibrates the model on
                  "nothing threatening is happening" states)
  natived1 15% -- native-d1 weak opponent (negative-heavy, different failure
                  shape than self-play)

MEMORY DISCIPLINE (explicit, per team-lead's caution -- this box has been
OOM-killed 5 times by unbounded jobs): each worker writes its OWN JSONL shard
directly to /mnt/data/drmario_adversary_t3/replay_buffer/ as it plays, flushing
after every game. Nothing is buffered across games and nothing is returned
through the ProcessPoolExecutor IPC channel except small per-job summary counts
-- nothing size-proportional-to-corpus ever crosses a pickle boundary.

LABELLING: only the ACTION ACTUALLY TAKEN (by the adversary-role side) is
logged per decision -- this is standard off-policy trajectory data, not an
exhaustive labelling of all 32 counterfactual placements. After a game ends,
each logged decision at ply i gets label 1 iff the champion (opponent side)
died (topout/no-move) at some ply d with i <= d <= i+N (LABEL_HORIZON), else 0.
"""
from __future__ import annotations

import sys
import os
import json
import time
import random
import argparse
import resource
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/tmp/vs_aware",
           ROOT + "/.claude/worktrees/faithful-sim/src", QA, QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DATA_DIR = "/mnt/data/drmario_adversary_t3/replay_buffer"
LABEL_HORIZON = 15          # "dies within N pills" per team-lead's spec
MEM_CAP_MB_PER_WORKER = 2500  # explicit per-worker RSS cap (soft, enforced via resource module)

BOUNDS = [(0, 500), (0, 80), (-100, 150), (-200, 400), (0, 50)]   # same as search_adversary.py


def _cap_memory():
    """Explicit, enforced per-worker memory cap (RLIMIT_AS) -- team-lead's caution
    about unbounded jobs OOM-killing this box, made concrete rather than assumed."""
    soft_bytes = MEM_CAP_MB_PER_WORKER * 1024 * 1024
    try:
        resource.setrlimit(resource.RLIMIT_AS, (soft_bytes, soft_bytes))
    except Exception as e:
        print(f"[warn] could not set RLIMIT_AS: {e}", flush=True)


_STATE = {}


def _init(best_vec):
    _cap_memory()
    import vs_harness as H
    import fast_rtl_x as FX
    from vs_run import champion_decider, native_d1_opponent, warmup_all
    from adversary_search import AdversaryD3Decider
    warmup_all()
    _STATE["H"] = H
    _STATE["champ"] = champion_decider()
    _STATE["native_d1"] = native_d1_opponent()
    _STATE["w"], _STATE["fl"] = FX.variant("winner")
    _STATE["best_vec"] = best_vec
    _STATE["AdversaryD3Decider"] = AdversaryD3Decider


def _pick_policy(rng, best_vec):
    """Returns (kind, decider, vec_or_none) for one game."""
    r = rng.random()
    Adv = _STATE["AdversaryD3Decider"]
    w, fl = _STATE["w"], _STATE["fl"]
    if r < 0.40 and best_vec is not None:
        vec = tuple(max(lo, min(hi, int(round(v + rng.gauss(0, (hi - lo) * 0.06)))))
                    for (lo, hi), v in zip(BOUNDS, best_vec))
        d = Adv.from_vector(vec, w, fl, topk2=8); d._opponent_aware = True
        return "evofam", d, vec
    if r < 0.70:
        vec = tuple(int(round(rng.uniform(lo, hi))) for lo, hi in BOUNDS)
        d = Adv.from_vector(vec, w, fl, topk2=8); d._opponent_aware = True
        return "random", d, vec
    if r < 0.85:
        return "selfplay", _STATE["champ"], None
    return "natived1", _STATE["native_d1"], None


def _play_one_game(seed, kind, dec, vec, adv_side, shard_fh):
    """Play champion vs `dec` (adv_side plays `dec`), log adv-role decisions with
    the RunningAttackCounters context, backfill labels, write to shard_fh. Returns
    (n_examples, n_positive, champ_died)."""
    import adversary_features as AF
    H = _STATE["H"]
    champ = _STATE["champ"]
    counters = AF.RunningAttackCounters()
    decisions = []   # bounded: one game's worth only, flushed immediately after

    def _wrap(d):
        if getattr(d, "_opponent_aware", False):
            return lambda b, c, n, opp: d.choose(b, c, n, opp)
        return H.blind(d)

    def hook(who, e, opp_board, action, took):
        if took:   # a release just landed on `who` this step
            if who == adv_side:
                counters.note_attack_received()
            else:
                counters.note_attack_sent()  # opponent (champion) just took damage -> it was OUR attack landing
        if who != adv_side or action is None:
            return None
        import numpy as np
        import fast_rtl_x as FX
        from cascade_chain_x import _leaf_chain, _base_scan, NBASE, NT
        from fast_sim_x import NCELL as _NC
        own_col, own_vir = FX.board_flat(e.board)
        opp_col, opp_vir = FX.board_flat(opp_board)
        own_lnk = np.ascontiguousarray(e.board.link, dtype=np.int8).reshape(-1)
        var, cl = action // 8, action % 8
        w, fl = _STATE["w"], _STATE["fl"]
        base1 = np.empty(NBASE, dtype=np.int64)
        _base_scan(own_col, own_vir, fl, base1)
        c1 = np.empty(_NC, dtype=np.int8); v1 = np.empty(_NC, dtype=np.int8)
        l1 = np.empty(_NC, dtype=np.int8); mask = np.empty(_NC, dtype=np.int8)
        terms = np.empty(NT, dtype=np.int64)
        ok, nv, cells, leaf1, ch1 = _leaf_chain(own_col, own_vir, own_lnk, base1, var, cl,
                                                e.cur.a, e.cur.b, w, fl, c1, v1, l1, mask,
                                                terms, 0, False)
        cells_cleared = int(cells) if ok else 0
        chain_depth = int(ch1) if ok else 0
        ply = e.pills_placed if hasattr(e, "pills_placed") else len(decisions)
        feat = AF.extract(own_col, own_vir, opp_col, opp_vir,
                          cells_cleared=cells_cleared, chain_depth=chain_depth,
                          atk_sent_running=counters.sent, atk_recv_running=counters.received,
                          ply=ply)
        decisions.append({"feat": feat, "ply_adv": len(decisions)})
        return None

    a_champ = _wrap(champ)
    a_dec = _wrap(dec)
    a0, a1 = (a_dec, a_champ) if adv_side == 0 else (a_champ, a_dec)
    r = H.play_match(seed, a0, a1, level=11, max_pills=300, hook=hook, garbage=True)
    champ_side = 1 - adv_side
    champ_died = (r["winner"] == adv_side) and (r["reason"] in ("topout", "no-move"))
    death_ply_adv = len(decisions) - 1 if champ_died else None  # last logged adv decision precedes the death

    n = len(decisions)
    n_pos = 0
    for i, d in enumerate(decisions):
        label = 1 if (champ_died and death_ply_adv is not None
                      and i <= death_ply_adv <= i + LABEL_HORIZON) else 0
        n_pos += label
        row = {"features": d["feat"].tolist(), "label": label,
               "seed": seed, "kind": kind, "vec": vec, "ply": d["ply_adv"]}
        shard_fh.write(json.dumps(row) + "\n")
    shard_fh.flush()
    return n, n_pos, champ_died


def _worker_job(args):
    worker_id, seeds, best_vec = args
    rng = random.Random(20260806 + worker_id * 97)
    os.makedirs(DATA_DIR, exist_ok=True)
    shard_path = os.path.join(DATA_DIR, f"shard_w{worker_id}.jsonl")
    n_games = n_examples = n_pos = n_deaths = 0
    with open(shard_path, "a") as fh:
        for seed in seeds:
            kind, dec, vec = _pick_policy(rng, best_vec)
            adv_side = rng.randrange(2)
            try:
                n, npos, died = _play_one_game(seed, kind, dec, vec, adv_side, fh)
            except Exception as e:
                print(f"[worker {worker_id}] seed {seed} FAILED: {e}", flush=True)
                continue
            n_games += 1
            n_examples += n
            n_pos += npos
            n_deaths += int(died)
    return {"worker_id": worker_id, "n_games": n_games, "n_examples": n_examples,
            "n_pos": n_pos, "n_deaths": n_deaths, "shard": shard_path}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=400)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed0", type=int, default=40000)
    ap.add_argument("--best-vec", type=int, nargs=5, default=None)
    a = ap.parse_args()

    best_vec = tuple(a.best_vec) if a.best_vec else None
    seeds = list(range(a.seed0, a.seed0 + a.games))
    per_worker = [seeds[i::a.workers] for i in range(a.workers)]
    jobs = [(w, per_worker[w], best_vec) for w in range(a.workers)]

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(best_vec,)) as ex:
        results = list(ex.map(_worker_job, jobs))

    tot_games = sum(r["n_games"] for r in results)
    tot_ex = sum(r["n_examples"] for r in results)
    tot_pos = sum(r["n_pos"] for r in results)
    tot_deaths = sum(r["n_deaths"] for r in results)
    pos_rate = (tot_pos / tot_ex) if tot_ex else 0.0
    print(f"DONE {tot_games} games, {tot_ex} examples ({tot_pos} positive, {pos_rate:.1%}), "
          f"{tot_deaths} champion deaths ({time.time()-t0:.0f}s)")
    print(f"shards in {DATA_DIR}")


if __name__ == "__main__":
    main()
