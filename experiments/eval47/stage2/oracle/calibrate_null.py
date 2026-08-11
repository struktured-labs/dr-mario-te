#!/usr/bin/env python3
"""Freeze endpoint-blind hash thinning for the shuffled-label null.

Calibration reads only accepted/raw flip counters on reserved calibration
seeds.  It never reads game result, clear, topout, stall, pills, dies-ahead, or
viruses-left.  The output fraction is then passed unchanged to the endpoint
run; no endpoint seed may be used here.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import analyse_oracle as A


CAL_SEED_MIN = 42000
CAL_SEED_MAX = 42059


def counts(rows):
    return {
        "n": len(rows),
        "seeds": {int(r["seed"]) for r in rows},
        "flips": sum(int(r["trt"].get("flips", 0)) for r in rows),
        "raw_flips": sum(int(r["trt"].get("raw_flips",
                                           r["trt"].get("flips", 0)))
                         for r in rows),
        "plies": sum(int(r["trt"].get("plies_scored", 0)) for r in rows),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--true-run", required=True)
    ap.add_argument("--raw-mutant-run", required=True)
    ap.add_argument("--denominator", type=int, default=1_000_000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    t = counts(A.load_run(a.true_run))
    m = counts(A.load_run(a.raw_mutant_run))
    expected = set(range(CAL_SEED_MIN, CAL_SEED_MAX + 1))
    if t["seeds"] != expected or m["seeds"] != expected:
        raise SystemExit(
            f"calibration requires exactly reserved seeds {CAL_SEED_MIN}.."
            f"{CAL_SEED_MAX}; true={len(t['seeds'])}, mutant={len(m['seeds'])}")
    if t["seeds"] != m["seeds"] or m["raw_flips"] <= 0:
        raise SystemExit("invalid paired calibration runs")
    ratio = min(1.0, t["flips"] / m["raw_flips"])
    numerator = round(ratio * a.denominator)
    doc = {
        "purpose": "dose-match shuffled-label null without endpoint labels",
        "calibration_seeds": [CAL_SEED_MIN, CAL_SEED_MAX],
        "fields_read": ["seed", "trt.flips", "trt.raw_flips",
                        "trt.plies_scored"],
        "true": {k: v for k, v in t.items() if k != "seeds"},
        "raw_mutant": {k: v for k, v in m.items() if k != "seeds"},
        "null_keep_num": numerator,
        "null_keep_den": a.denominator,
        "raw_ratio_true_over_mutant": ratio,
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(doc, fh, indent=2)
    print(json.dumps(doc, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
