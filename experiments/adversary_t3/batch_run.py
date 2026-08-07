#!/usr/bin/env python3
"""Parallel paired-seed batch runner: champion vs ONE fixed opponent, across many
seeds, side-swapped, on a shared ProcessPoolExecutor. Structurally mirrors
h2h_vs.py's run()/_one()/_init() (same job shape: (seed, swap)), because that
pattern is already proven in this codebase -- this file exists only because
h2h_vs.py's _mk() hardwires BOTH sides to the blind (board,cur,nxt) calling
convention, and the adversary needs the opponent-aware (board,cur,nxt,opp_board)
convention on one side. Everything else (ProcessPoolExecutor + initializer +
boot_ci bootstrap) is the same shape on purpose.
"""
from __future__ import annotations

import sys
import os
import random
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/tmp/vs_aware",
           ROOT + "/.claude/worktrees/faithful-sim/src", QA, QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_POOL_STATE = {}


def _init_pool():
    # Cap BLAS/OpenMP thread pools as the FIRST thing this fresh worker
    # process does, before numpy/sklearn are ever touched in it -- belt and
    # suspenders alongside the same fix in learned_adversary.py's own import
    # header. Root cause: train_adversary_model.py's first run hung >5 min on
    # a dataset that should score in seconds, purely from sklearn's internal
    # thread pool thrashing across many concurrent worker PROCESSES; the
    # learned-adversary VS-match arm (which calls model.predict_proba() from
    # inside THIS pool) is exactly the same hazard and was ~5x slower than
    # the numba-only arms at matched n, consistent with the same cause.
    for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS"):
        os.environ.setdefault(_v, "1")
    import vs_harness as H
    import fast_rtl_x as FX
    from vs_run import champion_decider, pre_strand20_champion, native_d1_opponent, warmup_all
    warmup_all()
    _POOL_STATE["H"] = H
    _POOL_STATE["champ"] = champion_decider()
    _POOL_STATE["pre20"] = pre_strand20_champion()
    _POOL_STATE["native_d1"] = native_d1_opponent()


OPP_ADV = "adv"          # candidate adversary vector, opponent-aware
OPP_CHAMP = "champ"      # champion mirror (self-play baseline)
OPP_NATIVE = "native"    # native-d1 offline stand-in
OPP_PRE20 = "pre20"      # pre-strand20 champion lineage (transfer test uses this as the CHAMPION side)
OPP_LEARNED = "learned"  # distilled off-policy value model, depth-1 + learned scoring


def _build_opponent(kind, vec, champ_kind="champ"):
    """kind == OPP_CHAMP is a MIRROR of whichever decider is playing the champion
    role this call (champ_kind) -- so a self-play baseline for the pre-strand20
    lineage (champ_kind="pre20") plays pre20 vs pre20, not pre20 vs strand20. Do
    not special-case this to always mean the strand20 champion."""
    from adversary_search import AdversaryD3Decider
    import fast_rtl_x as FX
    if kind == OPP_ADV:
        w, fl = FX.variant("winner")
        d = AdversaryD3Decider.from_vector(vec, w, fl, topk2=8)
        d._opponent_aware = True
        return d
    if kind == OPP_CHAMP:
        return _POOL_STATE[champ_kind]
    if kind == OPP_NATIVE:
        return _POOL_STATE["native_d1"]
    if kind == OPP_PRE20:
        return _POOL_STATE["pre20"]
    if kind == OPP_LEARNED:
        from learned_adversary import LearnedAdversaryDecider
        d = LearnedAdversaryDecider(epsilon=0.0)   # argmax -- this is the reported policy
        d.reset_game()
        return d
    raise KeyError(kind)


def _wrap(dec, H):
    if getattr(dec, "_opponent_aware", False):
        return lambda b, c, n, opp: dec.choose(b, c, n, opp)
    return H.blind(dec)


def _attack_hook(champ_side, dec0, dec1):
    """Feeds vs_harness's per-decision `took` signal into any decider that tracks
    running attack counters (currently only LearnedAdversaryDecider -- see its
    module docstring on why exact pending garbage is unobservable but attack
    HISTORY is). A no-op for deciders without these methods."""
    decs = {0: dec0, 1: dec1}

    def hook(who, e, opp_board, action, took):
        if not took:
            return None
        target = decs.get(who)
        note_recv = getattr(target, "note_attack_received", None)
        if note_recv:
            note_recv()
        other = decs.get(1 - who)
        note_sent = getattr(other, "note_attack_sent", None)
        if note_sent:
            note_sent()
        return None
    return hook


def _one(job):
    """job = (seed, swap, champ_kind, opp_kind, vec, level, max_pills, garbage).
    champ_kind selects which decider plays the CHAMPION role (normally the shipped
    strand180_20; the transfer test substitutes pre20). Returns champion-centric
    outcome (see vs_run._outcome) with champ_side recorded."""
    from vs_run import _outcome
    seed, swap, champ_kind, opp_kind, vec, level, max_pills, garbage = job
    H = _POOL_STATE["H"]
    champ_dec = _POOL_STATE[champ_kind]
    opp_dec = _build_opponent(opp_kind, vec, champ_kind=champ_kind)
    champ_side = 0 if not swap else 1
    a_raw = champ_dec if not swap else opp_dec
    b_raw = opp_dec if not swap else champ_dec
    a = _wrap(a_raw, H)
    b = _wrap(b_raw, H)
    hook = _attack_hook(champ_side, a_raw, b_raw)
    r = H.play_match(seed, a, b, level=level, max_pills=max_pills, garbage=garbage, hook=hook)
    return {"seed": seed, "swap": swap, **_outcome(r, champ_side)}


_EXECUTOR = {}


def get_pool(workers=6):
    if _EXECUTOR.get("ex") is None:
        _EXECUTOR["ex"] = ProcessPoolExecutor(max_workers=workers, initializer=_init_pool)
    return _EXECUTOR["ex"]


def shutdown_pool():
    if _EXECUTOR.get("ex") is not None:
        _EXECUTOR["ex"].shutdown(wait=True)
        _EXECUTOR["ex"] = None


def boot_ci(xs, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = [st.mean([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n)]
    reps.sort()
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def evaluate(seeds, opp_kind, vec=None, champ_kind="champ", level=11, max_pills=300,
             garbage=True, workers=6, pool=None):
    """Champion (champ_kind) vs opponent (opp_kind[, vec]) over `seeds`, side-swapped.
    Returns per-seed averaged rows + summary stats with bootstrap CIs on the three
    fitness dimensions (death rate, dies-ahead rate, pills-to-clear)."""
    ex = pool or get_pool(workers)
    jobs = [(s, sw, champ_kind, opp_kind, vec, level, max_pills, garbage)
            for s in seeds for sw in (0, 1)]
    rows = list(ex.map(_one, jobs, chunksize=1))
    by_seed = {}
    for r in rows:
        by_seed.setdefault(r["seed"], []).append(r)
    seed_rows = []
    for s, rs in sorted(by_seed.items()):
        died = sum(x["champ_died"] for x in rs) / len(rs)
        won = sum(x["champ_won"] for x in rs) / len(rs)
        stall = sum(x["stall"] for x in rs) / len(rs)
        outraced = sum(x["outraced"] for x in rs) / len(rs)
        dies_ahead = sum(x["dies_ahead"] for x in rs) / len(rs)
        ptc = [x["pills_to_clear"] for x in rs if x["pills_to_clear"] is not None]
        atk_c = sum(x["atk_sent_champ"] for x in rs) / len(rs)
        atk_o = sum(x["atk_sent_opp"] for x in rs) / len(rs)
        seed_rows.append({"seed": s, "died": died, "won": won, "stall": stall,
                          "outraced": outraced, "dies_ahead": dies_ahead,
                          "pills_to_clear": (sum(ptc) / len(ptc)) if ptc else None,
                          "atk_sent_champ": atk_c, "atk_sent_opp": atk_o})
    died_v = [r["died"] for r in seed_rows]
    da_v = [r["dies_ahead"] for r in seed_rows]
    ptc_v = [r["pills_to_clear"] for r in seed_rows if r["pills_to_clear"] is not None]
    dlo, dhi = boot_ci(died_v)
    alo, ahi = boot_ci(da_v)
    return {
        "n_seeds": len(seed_rows), "opp_kind": opp_kind, "vec": vec,
        "champ_death_rate": st.mean(died_v) if died_v else float("nan"),
        "death_ci": [dlo, dhi],
        "dies_ahead_rate": st.mean(da_v) if da_v else float("nan"),
        "dies_ahead_ci": [alo, ahi],
        "champ_pills_to_clear": st.mean(ptc_v) if ptc_v else None,
        "n_champ_wins": len(ptc_v),
        "champ_win_rate": st.mean([r["won"] for r in seed_rows]),
        "stall_rate": st.mean([r["stall"] for r in seed_rows]),
        "outraced_rate": st.mean([r["outraced"] for r in seed_rows]),
        "atk_sent_champ": st.mean([r["atk_sent_champ"] for r in seed_rows]),
        "atk_sent_opp": st.mean([r["atk_sent_opp"] for r in seed_rows]),
        "seed_rows": seed_rows,
    }


def fitness_scalar(res):
    """Lexicographic-ish scalar: death rate dominates (x1000), dies-ahead breaks
    ties among similar death rates (x100), pills-to-clear breaks further ties
    (x0.1, missing -> 0). Higher = more adversarial (worse for the champion)."""
    ptc = res["champ_pills_to_clear"] or 0.0
    return (res["champ_death_rate"] * 1000.0 + res["dies_ahead_rate"] * 100.0
            + ptc * 0.1)


if __name__ == "__main__":
    import time
    t0 = time.time()
    res = evaluate(range(5000, 5006), OPP_ADV, vec=(180, 20, 0, 0, 0))
    print(f"self-mirror adv(180,20,0,0,0) vs champ: death={res['champ_death_rate']:.2f} "
          f"win={res['champ_win_rate']:.2f} n={res['n_seeds']} "
          f"({time.time()-t0:.1f}s)")
    shutdown_pool()
