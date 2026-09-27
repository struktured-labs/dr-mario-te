#!/usr/bin/env python3
"""Validate a fixed null q and compute the preregistered next calibration q."""
from __future__ import annotations

import argparse
import json
import sys

import analyse_oracle as A


def flip_counts(outdir):
    rows = A.load_run(outdir)
    return {"n": len(rows),
            "seeds": [r["seed"] for r in rows],
            "flips": sum(int(r["trt"].get("flips", 0)) for r in rows),
            "plies": sum(int(r["trt"].get("plies_scored", 0)) for r in rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--true-run", required=True)
    ap.add_argument("--null-run", required=True)
    ap.add_argument("--current-num", required=True, type=int)
    ap.add_argument("--denominator", default=1_000_000, type=int)
    a = ap.parse_args()
    t, n = flip_counts(a.true_run), flip_counts(a.null_run)
    if t["seeds"] != n["seeds"] or len(t["seeds"]) != 60:
        raise SystemExit("dose validation requires the same 60 reserved seeds")
    tr = t["flips"] / t["plies"]
    nr = n["flips"] / n["plies"]
    ratio = nr / tr
    next_num = round(a.current_num * tr / nr) if nr > 0 else a.denominator
    next_num = min(a.denominator, max(0, next_num))
    doc = {"fields_read": ["seed", "trt.flips", "trt.plies_scored"],
           "true": {k: v for k, v in t.items() if k != "seeds"},
           "null": {k: v for k, v in n.items() if k != "seeds"},
           "true_flip_rate": tr, "null_flip_rate": nr,
           "null_over_true_ratio": ratio,
           "validated": 0.90 <= ratio <= 1.10,
           "current_num": a.current_num, "denominator": a.denominator,
           "next_num_if_needed": next_num}
    print(json.dumps(doc, indent=2))
    return 0 if doc["validated"] else 1


if __name__ == "__main__":
    sys.exit(main())
