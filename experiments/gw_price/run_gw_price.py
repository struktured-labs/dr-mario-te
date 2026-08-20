#!/usr/bin/env python3
"""GW-increment pricing runner: co-sim farm games with a tie-deepening intervention.

PREREG_GW_PRICE.md is the contract; this file implements §4 and adds nothing it
does not declare.  Component map (rule 10):

  RTL (farm_vsim, fw s20b)   every game-line placement decision, exactly as the
                             committed cosim_farm/game.py plays them.
  faithful sim               physics / garbage / capsule stream (unchanged).
  fast-sim champion mirror   ONLY the trigger predicate (de-dup'd top-2 tie), the
                             deepening, and the rand/worst alternative selection —
                             the committed gw_design/screen_gw.py functions.

ARMS (--arm): base   = RTL move always (observer still runs: same trigger rows).
              deepen = at a trigger, play the deepened pick.
              rand   = at a trigger, play a uniform draw over de-dup'd
                       representatives excluding rep0 (Random(seed*7919+ply)).
              worst  = at a trigger, play the minimum-value representative
                       (tie-break: LAST in CHAMP_ORDER rank).

TRIGGER (all arms, identical code path): post-garbage decision AND de-dup'd
top-2 representatives exactly value-tied AND deepen() flips the pick AND the
RTL's own move lands on rep0's resulting board (mismatch => NO arm intervenes;
counted n_mirror_mismatch).  Identical prefixes make the FIRST trigger ply
common to every arm of a seed; later triggers are arm-local policy consequences,
which is the shipped semantics.

PILL-CLOSURE SAFETY: the env's capsule source is installed as a deepcopy-safe
PillDraw OBJECT (oracle_arm), never nes_pills.attach()'s lambda — the observer
forks clones, and the lambda would share ONE advancing cursor across every fork
(dr-mario-deepcopy-pill-closure).  gate_gw_price.py G1 proves byte-identity with
the stock closure-based play_game when interventions are off, and its M1 mutant
(closure source) must FAIL that gate.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FARM = os.path.abspath(os.path.join(HERE, "..", "cosim_farm"))
GWD = os.path.abspath(os.path.join(HERE, "..", "gw_design"))
RL = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
QA47 = QA + "/eval47"
for _p in (FARM, GWD, RL + "/.claude/worktrees/faithful-sim/src", QA, QA47):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ARMS = ("base", "deepen", "rand", "worst")
NO_TUCK = 0xFF


def _boot_oracle():
    import screen_gw as SG
    SG._boot()
    return SG


def make_farm_env(seed, level=11, max_pills=300, closure_source=False):
    """The farm's env, but with a deepcopy-safe capsule source.

    closure_source=True is gate mutant M1 ONLY: it reproduces the stock
    nes_pills.attach() lambda, whose deepcopies share one advancing cursor.
    """
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
    env.reset()
    src = NesPillSource(seed=seed)
    if closure_source:                      # M1 — must FAIL G1
        src.attach(env)
    else:
        _boot_oracle()
        from oracle_arm import PillDraw
        env._rand_pill = PillDraw(src)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    return env


def dedup_reps_all(env, legal, vals):
    """ALL representatives de-duplicated by resulting board, champion order.

    Same rule as screen_gw.representatives (value desc, then CHAMP_ORDER rank)
    but without the early stop at 2 — rand/worst need the full list.  G4 asserts
    reps_all[:2] == screen_gw.representatives on real boards.
    Returns [(action, board_key, value), ...].
    """
    from oracle_arm import CHAMP_ORDER
    rank = {int(a): i for i, a in enumerate(CHAMP_ORDER)}
    ranked = sorted(legal, key=lambda c: (-float(vals[c]), rank[int(c)]))
    seen, reps = set(), []
    for c in ranked:
        e = copy.deepcopy(env)
        e.step(int(c))
        k = hashlib.md5(e.board.color.tobytes()).hexdigest()
        if k in seen:
            continue
        seen.add(k)
        reps.append((int(c), k, float(vals[c])))
    return reps


def board_key_after(env, action):
    e = copy.deepcopy(env)
    e.step(int(action))
    return hashlib.md5(e.board.color.tobytes()).hexdigest()


def evaluate_trigger(env, seed, ply, rtl_action, C, bmodel, mut=None):
    """Run the §4 trigger predicate on the CURRENT (post-garbage) board.

    Returns (event dict | None).  event["fire"] is True only when every clause
    holds; event["why"] records the first clause that failed (population
    accounting; the gate's population mutant keys on it).  Never mutates env.
    """
    import numpy as np
    import screen_gw as SG
    from oracle_arm import CHAMP_ORDER
    mut = mut or {}
    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    vals = SG.champ_values_of(env.board, env.cur.a, env.cur.b,
                              env.nxt.a, env.nxt.b, w, fl, wt, ws)
    legal = [int(s) for s in CHAMP_ORDER if np.isfinite(vals[int(s)])]
    if len(legal) < 2:
        return {"fire": False, "why": "lt2legal"}
    reps = dedup_reps_all(env, legal, vals)
    if mut.get("nodedup"):                 # G2 population mutant
        rank = {int(a): i for i, a in enumerate(CHAMP_ORDER)}
        ranked = sorted(legal, key=lambda c: (-float(vals[c]), rank[int(c)]))
        reps = [(int(c), board_key_after(env, c), float(vals[c]))
                for c in ranked[:2]] + reps[2:]
    if len(reps) < 2:
        return {"fire": False, "why": "lt2reps"}
    if reps[0][2] != reps[1][2]:
        return {"fire": False, "why": "notie"}
    # unconditional never-same-board assertion (PREREG §7 G2)
    if not mut.get("nodedup"):
        assert reps[0][1] != reps[1][1], \
            f"surviving top-2 share a board at seed={seed} ply={ply}"
    cands = [reps[0][0], reps[1][0]]
    pick, scores = SG.deepen(env, cands, C, seed, bmodel, w, fl, wt, ws, ply)
    flip = int(pick) != int(cands[0])
    ev = {"why": "ok", "ply": int(ply), "cands": cands, "pick": int(pick),
          "flip": int(flip),
          "scores": [None if not np.isfinite(s) else round(float(s), 4)
                     for s in scores],
          "tie_val": round(reps[0][2], 4), "n_reps": len(reps)}
    if not flip:
        ev["fire"] = False
        ev["why"] = "noflip"
        return ev
    rtl_key = board_key_after(env, rtl_action)
    if rtl_key != reps[0][1]:
        ev["fire"] = False
        ev["why"] = "mirror_mismatch"
        return ev
    ev["fire"] = True
    ev["alt_rand"] = _pick_rand(reps, seed, ply, mut)
    ev["alt_worst"] = _pick_worst(reps, mut)
    return ev


def _pick_rand(reps, seed, ply, mut=None):
    mut = mut or {}
    pool = [a for a, k, v in reps]
    if not mut.get("rand_incl_rep0"):      # M3b
        pool = pool[1:]
    if not pool:
        return None
    return int(random.Random(seed * 7919 + ply).choice(pool))


def _pick_worst(reps, mut=None):
    mut = mut or {}
    from oracle_arm import CHAMP_ORDER
    rank = {int(a): i for i, a in enumerate(CHAMP_ORDER)}
    if mut.get("worst_max"):               # M3a
        return int(max(reps, key=lambda t: (t[2], rank[t[0]]))[0])
    # min value; tie-break LAST in CHAMP_ORDER rank (PREREG §4)
    return int(min(reps, key=lambda t: (t[2], -rank[t[0]]))[0])


def play_game_iv(cosim, seed, arm, C, bmodel, level=11, max_pills=300,
                 interventions=True, mut=None):
    """cosim_farm/game.py:play_game (exec='drop', pressure='bursty') plus the
    observer/intervention.  Inlined because play_game exposes no hook; G1 proves
    the inline copy reproduces the stock function byte-for-byte when
    interventions are off (and lists the fields it proves it on).
    """
    import numpy as np
    from game import (col_heights, garbage_hit_h, GARBAGE_MIN_PILLS,
                      DIES_AHEAD_VIRUS_THRESHOLD)
    from cosim import board_to_nes, VAR_OF_O4
    from bursty_model import inject_bursty_garbage
    mut = mut or {}
    assert arm in ARMS, arm

    env = make_farm_env(seed, level, max_pills,
                        closure_source=bool(mut.get("closure")))
    if isinstance(cosim, MirrorCosim):
        cosim.env = env
    start_viruses = env.board.virus_count()
    res = "stall"
    n_illegal = 0
    garbage = 0
    clocks = 0
    moves = []
    lat = []
    ivs = []
    n_tie = 0
    n_flip = 0
    n_mirror_mismatch = 0
    pending_pg = 0
    pending_gh = -1

    for i in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        b128 = board_to_nes(env.board)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        d = cosim.decide(b128, ca - 1, cb - 1, na - 1, nb - 1)
        clocks += d["clocks"]
        lat.append([int(d["clocks"]), -1, max(col_heights(env.board.color)),
                    pending_pg, pending_gh])
        was_pg, was_gh = pending_pg, pending_gh
        pending_pg, pending_gh = 0, -1
        col, o4 = d["col"], d["o4"]
        rtl_action = VAR_OF_O4[o4] * 8 + col

        action = rtl_action
        if was_pg and interventions is not None:
            ev = evaluate_trigger(env, seed, i, rtl_action, C, bmodel, mut)
            if ev is not None and ev["why"] not in ("lt2legal", "lt2reps",
                                                    "notie"):
                n_tie += 1
                n_flip += ev.get("flip", 0)
            if ev is not None and ev["why"] == "mirror_mismatch":
                n_mirror_mismatch += 1
            if ev is not None and ev.get("fire"):
                ev["h_hit"] = was_gh
                ev["arm"] = arm
                if interventions and arm != "base":
                    if arm == "deepen":
                        action = ev["pick"]
                    elif arm == "rand" and ev["alt_rand"] is not None:
                        action = ev["alt_rand"]
                    elif arm == "worst":
                        action = ev["alt_worst"]
                ev["played"] = int(action)
                ev["intervened"] = int(action != rtl_action)
                del ev["why"], ev["fire"]
                ivs.append(ev)

        orient, acol, pill = env._decode(int(action))
        rcells = env.board.resting_position(pill, orient, acol)
        if rcells is None:
            n_illegal += 1
            res = "topout"
            break
        lat[-1][1] = int(rcells[1][0])
        moves.append((int(action), col, o4))
        occ_before = int(np.count_nonzero(env.board.color))
        _, _, term, trunc, info = env.step(int(action))
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break

        if env.pills_placed >= GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                h_before = col_heights(env.board.color)
                gp = env.pills_placed
                added = inject_bursty_garbage(env.board, bmodel, seed, gp,
                                              clear_size)
                garbage += added
                if added > 0:
                    _n_cells, gcols = bmodel.sample(seed, gp)
                    pending_pg = 1
                    pending_gh = garbage_hit_h(h_before, gcols)
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                break

    viruses_left = env.board.virus_count()
    return {
        "seed": seed, "arm": arm, "level": level, "result": res,
        "won": int(res == "clear"), "topout": int(res == "topout"),
        "stall": int(res == "stall"),
        "pills": env.pills_placed,
        "start_viruses": start_viruses,
        "viruses_left": viruses_left,
        "viruses_cleared": start_viruses - viruses_left,
        "dies_ahead": int(res == "topout"
                          and viruses_left <= DIES_AHEAD_VIRUS_THRESHOLD),
        "n_illegal": n_illegal, "garbage": garbage, "clocks": clocks,
        "lat": lat, "moves": moves, "ivs": ivs,
        "n_tie": n_tie, "n_flip": n_flip,
        "n_mirror_mismatch": n_mirror_mismatch,
        "n_iv": sum(e["intervened"] for e in ivs),
        "fw_md5": cosim.fw_md5,
    }


class MirrorCosim:
    """PREREG §2.1 pre-screen decider: the champion MIRROR's argmax in the RTL's
    seat.  Everything else in play_game_iv is identical (same injection, same
    trigger code path).  NOT used for any pricing row — its games select seeds
    and provide dose figures only.  It reads the live env via the hook installed
    by play_game_iv (the b128 wire format carries no cur/nxt board object)."""

    fw_md5 = "mirror-stub"

    def __init__(self, C):
        self.C = C
        self.env = None            # bound by play_game_iv each ply

    def decide(self, b128, cA, cB, nA, nB):
        import screen_gw as SG
        from oracle_arm import _champ_action, CHAMP_ORDER
        from cosim import VAR_OF_O4
        env, C = self.env, self.C
        assert int(env.cur.a) - 1 == cA and int(env.cur.b) - 1 == cB, \
            "stub env out of sync with the wire"
        vals = SG.champ_values_of(env.board, env.cur.a, env.cur.b,
                                  env.nxt.a, env.nxt.b,
                                  C["w"], C["fl"], C["wt"], C["ws"])
        a = _champ_action(vals, CHAMP_ORDER)
        if a is None:
            a = 0
        v, col = divmod(int(a), 8)
        inv = {vv: i for i, vv in enumerate(VAR_OF_O4)}
        return {"col": col, "o4": inv[v], "tcol": NO_TUCK, "trow": 0,
                "clocks": 0}


# ---------------------------------------------------------------- pool runner
_W = {}


def build_farm_model():
    """The FARM's bursty v1.1 model, built exactly as run_farm._init does.

    MUST run BEFORE any oracle import: oracle_arm pushes the h13-gate eval47
    path ahead of the QA one, and the h13-gate copy of the (byte-identical)
    fitter cannot find the footage data. Resolution is asserted, not hoped
    (remote-node-code-skew rule).
    """
    # Load the QA copy EXPLICITLY by path (sitecustomize pattern): sys.path
    # resolution is hijackable — oracle_arm pushes the h13-gate eval47 dir ahead
    # of QA47, and the (byte-identical) h13 copy fails on module-relative
    # footage paths. Explicit loading cannot be raced by import order.
    import importlib.util
    _p = os.path.join(QA47, "run_bursty_v1_1_validity.py")
    _spec = importlib.util.spec_from_file_location("run_bursty_v1_1_validity", _p)
    V11 = importlib.util.module_from_spec(_spec)
    sys.modules.setdefault("run_bursty_v1_1_validity", V11)
    _spec.loader.exec_module(V11)
    assert V11.__file__ == _p
    m = V11.build_v1_1()
    m.meta = {k: v for k, v in m.meta.items() if k != "raw_events"}
    return m


def _init(fw_dir, farm_bin):
    import game  # noqa: F401  (sys.path side effects match run_farm exactly)
    from cosim import Cosim
    m = build_farm_model()          # BEFORE oracle imports — see its docstring
    SG = _boot_oracle()
    import oracle_arm as O
    C, _bmodel_lulu = O.init_rig("lulu")
    _W.update(cosim=Cosim(farm_bin, fw_dir), C=C, bmodel=m, SG=SG)


def _play(job):
    seed, arm = job
    t0 = time.time()
    r = play_game_iv(_W["cosim"], seed, arm, _W["C"], _W["bmodel"])
    r["wall_secs"] = round(time.time() - t0, 2)
    return r


def _init_stub():
    m = build_farm_model()
    SG = _boot_oracle()
    import oracle_arm as O
    C, _ = O.init_rig("lulu")
    _W.update(C=C, bmodel=m, SG=SG)


def _play_stub(seed):
    r = play_game_iv(MirrorCosim(_W["C"]), seed, "base", _W["C"], _W["bmodel"])
    r.pop("lat"); r.pop("moves")
    r["fires"] = [(e["ply"], e["h_hit"]) for e in r["ivs"]]
    r["n_fire"] = len(r["ivs"])
    r.pop("ivs")
    return r


def prescreen(args):
    seeds = list(range(args.seed_start, args.seed_start + args.seed_count))
    from concurrent.futures import ProcessPoolExecutor
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers,
                             initializer=_init_stub) as ex:
        results = list(ex.map(_play_stub, seeds, chunksize=4))
    fire_seeds = sorted(r["seed"] for r in results if r["n_fire"] > 0)
    with open(args.out, "w") as fh:
        for r in results:
            fh.write(json.dumps(r) + "\n")
    summ = {"n_seeds": len(seeds), "fire_seeds": fire_seeds,
            "N1_seeds": fire_seeds[:args.n1], "N2_seeds": fire_seeds[:args.n2],
            "n_fire_total": sum(r["n_fire"] for r in results),
            "n_tie_total": sum(r["n_tie"] for r in results),
            "n_flip_total": sum(r["n_flip"] for r in results),
            "plies_total": sum(r["pills"] for r in results),
            "secs": round(time.time() - t0, 1)}
    json.dump(summ, open(args.out + ".summary.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in summ.items() if k != "fire_seeds"},
                     indent=1))
    print("N1:", summ["N1_seeds"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prescreen", action="store_true")
    ap.add_argument("--seed-start", type=int, default=52100)
    ap.add_argument("--seed-count", type=int, default=1000)
    ap.add_argument("--verdict", default=os.path.join(
        HERE, "out", "prescreen_52100.jsonl.summary.json"))
    ap.add_argument("--fw", default="/mnt/data/drmario_cosim/fw/s20b")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--arms", default="base,deepen,rand,worst")
    ap.add_argument("--n1", type=int, default=32)
    ap.add_argument("--n2", type=int, default=16)
    ap.add_argument("--seeds", default="",
                    help="comma list override (gates/smoke only)")
    a = ap.parse_args()
    if a.prescreen:
        prescreen(a)
        return

    farm_bin = os.path.join(FARM, "build", "obj_farm", "farm_vsim")
    v = json.load(open(a.verdict))
    n1 = v["fire_seeds"][:a.n1]
    n2 = v["fire_seeds"][:a.n2]
    if a.seeds:
        n1 = n2 = [int(s) for s in a.seeds.split(",")]
    arms = a.arms.split(",")
    jobs = []
    for arm in arms:
        for s in (n1 if arm in ("base", "deepen") else n2):
            jobs.append((s, arm))

    done = set()
    if os.path.exists(a.out):
        for line in open(a.out):
            try:
                r = json.loads(line)
                done.add((r["seed"], r["arm"]))
            except Exception:
                pass
    jobs = [j for j in jobs if j not in done]
    print(f"{len(jobs)} games to run ({len(done)} already present)", flush=True)

    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(a.fw, farm_bin)) as ex, \
            open(a.out, "a") as fh:
        futs = {ex.submit(_play, j): j for j in jobs}
        for n, f in enumerate(as_completed(futs), 1):
            r = f.result()
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            print(f"[{n}/{len(jobs)}] seed={r['seed']} arm={r['arm']} "
                  f"res={r['result']} iv={r['n_iv']} "
                  f"mm={r['n_mirror_mismatch']} {r['wall_secs']}s "
                  f"({(time.time()-t0)/60:.1f} min)", flush=True)


if __name__ == "__main__":
    main()
