#!/usr/bin/env python3
"""Fail-closed paired analysis for the exact-v8 d_spawn tie arm."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

HERE = Path(__file__).resolve().parent
N_REQUIRED = 9000
B = 5000
RNG = 20260811


def load_rows(root):
    by_seed = {}
    for path in sorted(Path(root).glob("seg_*.jsonl")):
        for line in path.open():
            try:
                row = json.loads(line)
                by_seed.setdefault(int(row["seed"]), row)
            except Exception:
                pass
    return [by_seed[s] for s in sorted(by_seed)]


def binary_contrast(left, right, rng):
    """left-right paired risk difference; negative favors left."""
    left = np.asarray(left, dtype=np.int8)
    right = np.asarray(right, dtype=np.int8)
    d = left.astype(float) - right.astype(float)
    n = len(d)
    discordant = int(np.count_nonzero(left != right))
    l_better = int(np.count_nonzero((left == 0) & (right == 1)))
    l_worse = int(np.count_nonzero((left == 1) & (right == 0)))
    draws = rng.integers(0, n, size=(B, n), dtype=np.int32)
    boot = d[draws].mean(axis=1)
    halfwidth_floor = 1.96 * math.sqrt((discordant / n) / n)
    return {
        "difference": float(d.mean()),
        "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        "discordant": discordant, "left_better": l_better, "left_worse": l_worse,
        "mcnemar_exact_p": float(binomtest(l_better, discordant, 0.5).pvalue)
        if discordant else 1.0,
        "analytic_halfwidth": halfwidth_floor,
        "one_pp_margin_reachable": bool(halfwidth_floor <= 0.01),
    }


def counts(rows, arm):
    return {name: sum(int(r[arm][key]) for r in rows) for name, key in
            (("clear", "won"), ("topout", "topout"), ("stall", "stall"),
             ("bad_end", "topout"), ("dies_ahead", "dies_ahead"))} | {
        "bad_end": sum(int(r[arm]["topout"] or r[arm]["stall"]) for r in rows)}


def provenance(rows, arm):
    logs = [f for r in rows for f in r[arm].get("flip_log", [])]
    if not logs:
        return {"n": 0}
    t = np.array([f["t_to_end"] for f in logs])
    return {
        "n": len(logs), "median_t_to_end": float(np.median(t)),
        "within_last_5": int((t <= 5).sum()), "within_last_15": int((t <= 15).sum()),
        "strict_lane_improvements": int(sum(
            f["chosen_post_d_spawn_h"] < f["base_post_d_spawn_h"] for f in logs)),
        "tie_sizes": {str(k): int(sum(f["raw_tie_size"] == k for f in logs))
                      for k in sorted(set(f["raw_tie_size"] for f in logs))},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(HERE / "out" / "evaluation"))
    ap.add_argument("--allow-partial", action="store_true")
    args = ap.parse_args()
    rows = load_rows(args.root)
    if len(rows) != N_REQUIRED and not args.allow_partial:
        raise SystemExit(f"refusing verdict: have {len(rows)}/{N_REQUIRED} paired seeds")
    if not rows:
        raise SystemExit("no rows")
    expected = list(range(61000, 61000 + len(rows)))
    seeds = [r["seed"] for r in rows]
    prefix_exact = seeds == expected
    if not prefix_exact:
        raise SystemExit("rows are not the registered ascending seed prefix")

    arms = ("base", "treatment", "null")
    bad = {a: np.array([int(r[a]["topout"] or r[a]["stall"]) for r in rows])
           for a in arms}
    da = {a: np.array([r[a]["dies_ahead"] for r in rows]) for a in arms}
    rng = np.random.default_rng(RNG)
    bad_tb = binary_contrast(bad["treatment"], bad["base"], rng)
    bad_tn = binary_contrast(bad["treatment"], bad["null"], rng)
    da_tb = binary_contrast(da["treatment"], da["base"], rng)
    da_tn = binary_contrast(da["treatment"], da["null"], rng)

    flips_t = sum(r["treatment"]["flips"] for r in rows)
    flips_n = sum(r["null"]["flips"] for r in rows)
    plies_t = sum(r["treatment"]["plies"] for r in rows)
    plies_n = sum(r["null"]["plies"] for r in rows)
    dose_t, dose_n = flips_t / plies_t, flips_n / plies_n
    dose_rel = abs(dose_t - dose_n) / max(dose_t, 1e-15)
    dose_ok = dose_rel <= 0.10

    common = [r for r in rows if r["base"]["won"] and r["treatment"]["won"]]
    pd = np.array([r["treatment"]["pills"] - r["base"]["pills"]
                   for r in common], dtype=float)
    pboot = []
    if len(pd):
        for _ in range(B):
            pboot.append(pd[rng.integers(0, len(pd), len(pd))].mean())
    pills = {"n_common_clears": len(pd), "mean_treatment_minus_base":
             float(pd.mean()) if len(pd) else None,
             "ci95": [float(np.percentile(pboot, 2.5)),
                       float(np.percentile(pboot, 97.5))] if pboot else None}

    complete = len(rows) == N_REQUIRED
    adequate = bad_tb["one_pp_margin_reachable"]
    go = (complete and dose_ok and adequate and bad_tb["ci95"][1] < 0
          and bad_tn["ci95"][1] < 0)
    if not complete:
        verdict = "PARTIAL_NO_VERDICT"
    elif not dose_ok:
        verdict = "VOID_DOSE_MISMATCH"
    elif not adequate:
        verdict = "NOT_DECIDABLE_BADEND_MARGIN"
    else:
        verdict = "GO" if go else "NO_GO"

    result = {
        "version": "dspawn-tie-v8-result-v1", "verdict": verdict,
        "n_pairs": len(rows), "seed_min": min(seeds), "seed_max": max(seeds),
        "complete": complete, "prefix_exact": prefix_exact,
        "counts": {a: counts(rows, a) for a in arms},
        "dose": {"treatment_flips": flips_t, "treatment_plies": plies_t,
                 "treatment_rate": dose_t, "null_flips": flips_n,
                 "null_plies": plies_n, "null_rate": dose_n,
                 "relative_mismatch": dose_rel, "gate_le_10pct": dose_ok},
        "bad_end": {"treatment_minus_base": bad_tb,
                    "treatment_minus_null_DiD": bad_tn},
        "dies_ahead": {"treatment_minus_base": da_tb,
                       "treatment_minus_null_DiD": da_tn},
        "pills": pills,
        "provenance": {"treatment": provenance(rows, "treatment"),
                       "null": provenance(rows, "null")},
        "note": ("topout and 300-pill stall both score as bad ends; exogenous Lulu "
                 "offers are policy-independent; p2_surrogate is not a live NAV_T claim"),
    }
    out = HERE / "out" / ("result.json" if complete else "partial_result.json")
    out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
