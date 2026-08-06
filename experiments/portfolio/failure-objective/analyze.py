#!/usr/bin/env python3
"""Assemble the coef_sweep.py results + the champion anchor (n=120, seeds
0..39 subset for paired comparison) into the report table, with a paired
bootstrap CI on bad-end-rate delta vs the shipped ws=20 point at matched n."""
from __future__ import annotations
import glob
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
ANCHOR = ("/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/"
          "results/bursty_v1_1_n120_wt0_ws20.json")


def boot_ci_diff(rows_a, rows_b, seeds, n=10000, seed=12345):
    """Paired bootstrap CI on rate(rows_b) - rate(rows_a) over the shared seed set."""
    rng = random.Random(seed)
    k = len(seeds)
    a = [rows_a[s]["topout"] + rows_a[s]["stall"] for s in seeds]
    b = [rows_b[s]["topout"] + rows_b[s]["stall"] for s in seeds]
    reps = []
    for _ in range(n):
        idx = [rng.randrange(k) for _ in range(k)]
        ra = sum(a[i] for i in idx) / k
        rb = sum(b[i] for i in idx) / k
        reps.append(rb - ra)
    reps.sort()
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def main():
    with open(ANCHOR) as fh:
        anchor = json.load(fh)
    ctrl120 = {r["seed"]: r for r in anchor["ctrl"]}   # ws=0
    ship120 = {r["seed"]: r for r in anchor["arm"]}    # ws=20 shipped

    seeds40 = list(range(40))
    ctrl40 = {s: ctrl120[s] for s in seeds40}
    ship40 = {s: ship120[s] for s in seeds40}

    def rate(rows, seeds):
        n = len(seeds)
        be = sum(rows[s]["topout"] + rows[s]["stall"] for s in seeds)
        da = sum(rows[s].get("dies_ahead", 0) for s in seeds)
        return be, da, n

    print("=== ANCHORS (full n=120) ===")
    be0, da0, n0 = rate(ctrl120, list(ctrl120))
    be1, da1, n1 = rate(ship120, list(ship120))
    print(f"  ws=0   n={n0}  bad_ends={be0} ({be0/n0:.1%})  dies_ahead={da0} ({da0/n0:.1%})")
    print(f"  ws=20  n={n1}  bad_ends={be1} ({be1/n1:.1%})  dies_ahead={da1} ({da1/n1:.1%})")

    print("\n=== ANCHORS restricted to seeds 0..39 (paired subset vs new arms) ===")
    be0, da0, n0 = rate(ctrl40, seeds40)
    be1, da1, n1 = rate(ship40, seeds40)
    print(f"  ws=0   n={n0}  bad_ends={be0} ({be0/n0:.1%})  dies_ahead={da0} ({da0/n0:.1%})")
    print(f"  ws=20  n={n1}  bad_ends={be1} ({be1/n1:.1%})  dies_ahead={da1} ({da1/n1:.1%})  <-- CHAMPION")

    print("\n=== NEW ARMS (results/sweep_*_n40.json) vs champion ws=20 (paired, n=40) ===")
    rows_out = []
    for path in sorted(glob.glob(os.path.join(HERE, "results", "sweep_*_n40.json"))):
        with open(path) as fh:
            d = json.load(fh)
        rows = {r["seed"]: r for r in d["rows"]}
        seeds = sorted(rows)
        be, da, n = rate(rows, seeds)
        lo, hi = boot_ci_diff(ship40, rows, seeds)
        tag = os.path.basename(path).replace("sweep_", "").replace("_n40.json", "")
        verdict = "REAL" if (hi < 0 or lo > 0) else "WASH"
        beats = "BEATS ws=20" if hi < 0 else ("WORSE than ws=20" if lo > 0 else "no diff from ws=20")
        print(f"  {tag:>16s}  ws={d['ws']:>3d}  overrides={d['w_overrides']}  "
              f"n={n}  bad_ends={be} ({be/n:.1%})  dies_ahead={da} ({da/n:.1%})  "
              f"delta-vs-ws20 CI [{lo:+.1%},{hi:+.1%}] {verdict} ({beats})")
        rows_out.append({"tag": tag, "ws": d["ws"], "w_overrides": d["w_overrides"],
                         "n": n, "bad_ends": be, "bad_end_rate": be / n,
                         "dies_ahead": da, "dies_ahead_rate": da / n,
                         "ci_vs_ws20": [lo, hi], "verdict": verdict, "beats": beats})

    with open(os.path.join(HERE, "results", "analysis_summary.json"), "w") as fh:
        json.dump({"anchor_ws0_n120": rate(ctrl120, list(ctrl120)),
                   "anchor_ws20_n120": rate(ship120, list(ship120)),
                   "champion_ws20_n40_subset": rate(ship40, seeds40),
                   "arms": rows_out}, fh, indent=2)


if __name__ == "__main__":
    main()
