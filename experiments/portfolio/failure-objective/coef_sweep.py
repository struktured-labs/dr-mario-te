#!/usr/bin/env python3
"""failure-objective thread: coefficient search with objective = MINIMIZE
bad-ends (topout+stall) under bursty v1.1 pressure, instead of the shipped
speed objective (pills-to-clear / clear rate).

Champion point (per system prompt): fast_rtl_x.variant("winner") leaf +
eval47/terms47.g_stranded ws=20 root-only. "winner" fixes 5 constants:
  R_VRDY=8  R_BURIED=48  R_RDYEXT=8  R_SETUP=32  R_MATCHED=48
plus the g_stranded cost weight ws=20 (wt/g_tower =0, unused in the ship
config). This script perturbs those 6 numbers one axis at a time
(coordinate scan around the champion point) and re-measures bad-end rate
under the SAME bursty v1.1 pressure model + SAME paired seed range used in
eval47/BURSTY_V1_RESULTS.md sec 5, so the two champion anchor points
(ws=0 and ws=20 at n=120) can be reused from disk instead of recomputed.

Simulator: python/py65-adjacent offline (fast_rtl_x numba kernel + root_search
+ FaithfulDrMarioEnv). This is the SAME simulator eval47/ab47.py and
pressure_rig.py use for all coefficient tuning to date (coef-opt2 winner
itself was validated this way before silicon). It does NOT go through
Verilator/RTL -- per house rule, any claim here about which MOVE is chosen
is only as trustworthy as this python path (py65 vs RTL agree ~13% of the
time on move CHOICE). This experiment's claim is about a SCALAR RATE
(bad-end frequency) produced by a fixed, unmodified search algorithm run
under two different coefficient settings -- not a move-identity claim -- so
the offline test is adequate to decide ALIVE/DEAD; silicon replay would
only be needed before shipping any winning point.
"""
from __future__ import annotations

import sys
import os
import json
import time
import argparse

EVAL47 = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
if EVAL47 not in sys.path:
    sys.path.insert(0, EVAL47)

import bursty_model as BM
import fit_ensemble_source as FE
import pressure_rig as PR

HERE = os.path.dirname(os.path.abspath(__file__))

# R_* register indices, from fast_rtl_x.py (copied here as literal ints so
# this script has no import-order dependency on that module's globals beyond
# what pressure_rig already pulls in via FX.variant).
R_SETUP = 5
R_MATCHED = 6
R_BURIED = 7
R_RDYEXT = 8
R_VRDY = 9

CHAMPION_W = {R_VRDY: 8.0, R_BURIED: 48.0, R_RDYEXT: 8.0, R_SETUP: 32.0, R_MATCHED: 48.0}
CHAMPION_WS = 20
NAME_OF_R = {R_VRDY: "R_VRDY", R_BURIED: "R_BURIED", R_RDYEXT: "R_RDYEXT",
             R_SETUP: "R_SETUP", R_MATCHED: "R_MATCHED"}


def build_v1_1():
    m_v1 = BM.fit_struktured_20260804()
    raw = m_v1.meta["raw_events"]
    all_volleys, all_clears = [], []
    for mid, res in raw.items():
        all_volleys.extend(res["volleys"])
        all_clears.extend(res["clears"])
    opponent_of = dict(BM.DEFAULT_OPPONENT_OF)
    return FE.fit_per_player(all_volleys, all_clears, m_v1.n_matches, "P1", opponent_of)


def _custom_init(level, wt, ws, w_overrides, bursty_model_obj):
    """Same as pressure_rig._init but lets us perturb individual R_* entries
    of the 'winner' weight vector before it's frozen into worker-global _C."""
    import numpy as np
    import fast_rtl_x as FX
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    for idx, val in w_overrides.items():
        w[idx] = float(val)
    from terms47 import g_tower, g_stranded
    z = np.zeros(128, dtype=np.int8)
    g_tower(z, z, PR.H0)
    g_stranded(z, z)
    PR._C.update(level=level, wt=wt, ws=ws, w=w, fl=fl,
                 model_kind="bursty", bursty_model_obj=bursty_model_obj,
                 drip_period=None, drip_k=None,
                 reactive_k=0, reactive_boost=0, reactive_wt_boost=0)


def run_custom_arm(level, seeds, workers, wt, ws, w_overrides, bursty_model_obj, tag):
    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_custom_init,
                             initargs=(level, wt, ws, w_overrides, bursty_model_obj)) as ex:
        futs = [ex.submit(PR.play, s) for s in range(seeds)]
        for f in as_completed(futs):
            rows.append(f.result())
    dt = time.time() - t0
    print(f"  arm {tag} done ({len(rows)} games, {dt:.1f}s, {dt/max(1,len(rows)):.2f}s/game)",
          flush=True)
    return {r["seed"]: r for r in rows}


def load_cached_anchor(path, key):
    """Load a per-seed row dict from an existing results JSON (ctrl or arm
    list-of-dicts keyed by 'seed'). key in {'ctrl','arm'}."""
    with open(path) as fh:
        d = json.load(fh)
    return {r["seed"]: r for r in d[key]}


def bad_end_rate(rows, seeds):
    ss = [s for s in seeds if s in rows]
    n = len(ss)
    be = sum(rows[s]["topout"] + rows[s]["stall"] for s in ss)
    da = sum(rows[s].get("dies_ahead", 0) for s in ss)
    return be, da, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=60)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--which", type=str, default="ws",
                    help="'ws' = ws coordinate scan; 'r' = R_* coordinate scan "
                         "at fixed ws=CHAMPION_WS; 'both'")
    ap.add_argument("--ws-values", type=str, default="0,10,20,30,40,60",
                    help="comma-separated ws values to test (--which ws/both)")
    ap.add_argument("--r-axes", type=str, default="",
                    help="comma-separated R_* names to perturb, e.g. "
                         "R_BURIED,R_SETUP (--which r/both); empty = all 5")
    ap.add_argument("--r-mults", type=str, default="0.5,1.5",
                    help="comma-separated multipliers applied to each R_* axis's "
                         "champion value (--which r/both)")
    ap.add_argument("--out", type=str, default=os.path.join(HERE, "results"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    seeds = list(range(a.seeds))
    v1_1 = build_v1_1()
    print(f"=== failure-objective coef sweep: L{a.level} n={a.seeds} workers={a.workers} "
          f"which={a.which} ===", flush=True)

    all_results = {}

    if a.which in ("ws", "both"):
        ws_values = [int(x) for x in a.ws_values.split(",") if x != ""]
        for ws in ws_values:
            tag = f"ws{ws}"
            rows = run_custom_arm(a.level, a.seeds, a.workers, 0, ws, {}, v1_1, tag)
            be, da, n = bad_end_rate(rows, seeds)
            print(f"  [ws-scan] ws={ws:>3d}  bad_ends={be}/{n} ({be/n:.1%})  "
                  f"dies_ahead={da}/{n} ({da/n:.1%})", flush=True)
            all_results[tag] = {"wt": 0, "ws": ws, "w_overrides": {},
                                 "bad_ends": be, "dies_ahead": da, "n": n,
                                 "rows": rows}
            with open(os.path.join(a.out, f"sweep_{tag}_n{a.seeds}.json"), "w") as fh:
                json.dump({"wt": 0, "ws": ws, "w_overrides": {}, "bad_ends": be,
                           "dies_ahead": da, "n": n,
                           "rows": [rows[s] for s in sorted(rows)]}, fh)

    if a.which in ("r", "both"):
        # perturb selected winner R_* constants one at a time (multipliers
        # from --r-mults), holding ws at the champion value (20) and the
        # other 4 R_* constants at their champion values.
        r_axis_names = set(x for x in a.r_axes.split(",") if x)
        r_mults = [float(x) for x in a.r_mults.split(",") if x != ""]
        for ridx, base in CHAMPION_W.items():
            name = NAME_OF_R[ridx]
            if r_axis_names and name not in r_axis_names:
                continue
            for mult in r_mults:
                val = base * mult
                overrides = dict(CHAMPION_W)
                overrides[ridx] = val
                tag = f"{name}_{val:g}"
                rows = run_custom_arm(a.level, a.seeds, a.workers, 0, CHAMPION_WS,
                                      overrides, v1_1, tag)
                be, da, n = bad_end_rate(rows, seeds)
                print(f"  [r-scan] {name}={val:g} (base {base:g})  "
                      f"bad_ends={be}/{n} ({be/n:.1%})  dies_ahead={da}/{n} ({da/n:.1%})",
                      flush=True)
                all_results[tag] = {"wt": 0, "ws": CHAMPION_WS, "w_overrides": overrides,
                                     "bad_ends": be, "dies_ahead": da, "n": n,
                                     "rows": rows}
                with open(os.path.join(a.out, f"sweep_{tag}_n{a.seeds}.json"), "w") as fh:
                    json.dump({"wt": 0, "ws": CHAMPION_WS, "w_overrides": overrides,
                               "bad_ends": be, "dies_ahead": da, "n": n,
                               "rows": [rows[s] for s in sorted(rows)]}, fh)

    print("\nDONE")


if __name__ == "__main__":
    main()
