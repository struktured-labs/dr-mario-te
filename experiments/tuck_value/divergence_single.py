#!/usr/bin/env python3
"""Isolate ONE tuck: what does a single executed maneuver buy, by itself?

`divergence.py` forks three ways at the first divergence — R (reference,
drop mode), T (tuck executed, then TUCK MODE for the rest of the game) and C
(second-best base drop, then drop mode). That answers "does the tuck change
the outcome", but T's number is not a single-maneuver effect: T keeps firing
tucks for the rest of the game, so T − R is really D − B measured from the
fork point. Only C is a clean single-placement perturbation.

This file adds the missing branch:

  T1  execute the tuck at the fork, then continue in DROP MODE — the same
      continuation policy as R and C.

so that T1 − R is one tuck and nothing else, directly comparable to C − R,
one second-best drop and nothing else. Both are followed by identical policy,
so the continuation cancels.

Written as a new file rather than an edit to divergence.py, matching this
program's own convention (run_tier_sweep.py's docstring documents the same
choice) — divergence.py's numbers are already committed and a refactor to
share the game loop would put them at risk for no measurement gain.

Usage: divergence_single.py --seeds 300 --workers 6 --pressure clean
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS = os.path.dirname(HERE)
EVAL47 = os.path.join(EXPERIMENTS, "eval47")
for _p in (HERE, EXPERIMENTS, EVAL47):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import divergence as DV          # noqa: E402 -- read-only import, not edited
import run_2x2 as R2             # noqa: E402
import reach_root as RR          # noqa: E402
import report as RP              # noqa: E402 -- boot_ci / mcnemar_exact

MAX_PILLS = DV.MAX_PILLS
_C = {}


def _init(level, theta, pressure, bm=None):
    RR._lazy()
    _C.update(level=level, theta=theta, pressure=pressure, bm=bm)


def play(seed):
    """Same fork protocol as divergence.play, with the extra T1 branch."""
    import numpy as np
    level, theta, pressure = _C["level"], _C["theta"], _C["pressure"]
    bm = _C.get("bm")

    env, src = DV._new_game(level, seed)
    res, fork_info = None, None

    for _ in range(MAX_PILLS):
        env_r, src_r = DV.fork_env(env, src)
        res, info = DV._step_one(env, seed, "drop", theta, pressure, bm)
        if info is not None:
            fork_info = info
            env, src = env_r, src_r
            break
        if res is not None:
            break
    if fork_info is None:
        return {"seed": seed, "forked": 0}

    occ_fork = int(np.count_nonzero(env.board.color))
    r0, c0, r1, c1 = fork_info["tuck_cells"]
    col0, col1 = fork_info["tuck_colors"]
    sb = fork_info["second_best"]

    env_R, _ = DV.fork_env(env, src)
    env_T1, _ = DV.fork_env(env, src)
    env_C, _ = DV.fork_env(env, src)

    res_R, _ = DV._step_one(env_R, seed, "drop", theta, pressure, bm)
    R2._place_cells(env_T1, r0, c0, r1, c1, col0, col1)
    res_T1 = DV._terminal_after_place(env_T1, seed, pressure, bm, occ_fork)
    res_C = (DV._step_one(env_C, seed, "drop", theta, pressure, bm,
                          force_action=sb)[0] if sb is not None else None)

    # every branch now continues under the IDENTICAL policy (drop mode), so
    # the continuation cancels and the only difference is the fork placement
    states = {"R": (env_R, res_R), "T1": (env_T1, res_T1), "C": (env_C, res_C)}
    if sb is None:
        states.pop("C")
    for _ in range(MAX_PILLS):
        alive = [k for k, (_e, r) in states.items() if r is None]
        if not alive:
            break
        for k in alive:
            e, _r = states[k]
            nr, _ = DV._step_one(e, seed, "drop", theta, pressure, bm)
            states[k] = (e, nr)

    out = {"seed": seed, "forked": 1, "fork_at_pill": env.pills_placed}
    for k, (e, r) in states.items():
        out[f"result_{k}"] = r
        out[f"pills_{k}"] = e.pills_placed
    return out


def summarize(rows):
    f = [r for r in rows if r.get("forked") and "result_C" in r]
    n = len(f)
    print(f"\nforked {n}/{len(rows)} seeds "
          f"(a tuck won the gate and a second-best base drop existed)")
    if not n:
        return {}
    w = lambda x: 1 if x == "clear" else 0            # noqa: E731
    wr = [w(r["result_R"]) for r in f]
    wt = [w(r["result_T1"]) for r in f]
    wc = [w(r["result_C"]) for r in f]
    print(f"  clear rate   R (no perturbation) {sum(wr) / n:6.1%}   "
          f"T1 (one tuck) {sum(wt) / n:6.1%}   C (one 2nd-best drop) {sum(wc) / n:6.1%}")
    print("  ALL THREE branches continue in drop mode, so the continuation policy "
          "cancels and each delta is one placement.")
    out = {"n": n, "clear_R": sum(wr) / n, "clear_T1": sum(wt) / n,
           "clear_C": sum(wc) / n}
    for lab, arr in (("T1 - R  one tuck        ", [a - b for a, b in zip(wt, wr)]),
                     ("C  - R  one 2nd-best drop", [a - b for a, b in zip(wc, wr)]),
                     ("T1 - C  tuck vs control ", [a - b for a, b in zip(wt, wc)])):
        lo, hi = RP.boot_ci(arr)
        b = sum(1 for x in arr if x > 0)
        c = sum(1 for x in arr if x < 0)
        print(f"  {lab}: {st.mean(arr):+.3f} [{lo:+.3f},{hi:+.3f}]  "
              f"better={b} worse={c} p={RP.mcnemar_exact(b, c):.4g}  "
              f"{'REAL' if (lo > 0 or hi < 0) else 'WASH'}")
        out[lab.strip()] = {"delta": st.mean(arr), "ci": [lo, hi],
                            "better": b, "worse": c,
                            "p": RP.mcnemar_exact(b, c)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=300)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--theta", type=float, default=R2.FIRMWARE_THETA)
    ap.add_argument("--pressure", choices=("clean", "bursty"), default="clean")
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    bm = None
    if a.pressure == "bursty":
        import run_bursty_v1_1_validity as V11
        bm = V11.build_v1_1()
        bm.meta = {k: v for k, v in bm.meta.items() if k != "raw_events"}

    print(f"=== SINGLE-MANEUVER ISOLATION, L{a.level}, n={a.seeds}, "
          f"pressure={a.pressure}, theta={a.theta:g} ===", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(a.level, a.theta, a.pressure, bm)) as ex:
        futs = [ex.submit(play, s) for s in range(a.seeds)]
        for i, fu in enumerate(as_completed(futs)):
            rows.append(fu.result())
            if (i + 1) % max(1, a.seeds // 5) == 0 or (i + 1) == a.seeds:
                print(f"  {i + 1}/{a.seeds}", flush=True)

    summary = summarize(rows)
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(f"{a.out}.json", "w") as fh:
            json.dump({"config": vars(a), "summary": summary, "rows": rows}, fh)
        print(f"wrote {a.out}.json")
    print("DONE")


if __name__ == "__main__":
    main()
