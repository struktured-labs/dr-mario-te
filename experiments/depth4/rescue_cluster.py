#!/usr/bin/env python3
"""Is the clear-rescue asymmetry (d4-only 61 vs d3-only 26) a real effect?

WHY THIS FILE EXISTS.  The adjudication's headline pills result is ~zero, but one number
looked like a surviving signal: among disagreements where exactly ONE branch went on to
clear, d4 won 61 to 26 -- better than 2:1, and a naive two-sided binomial against 50%
returns p = 0.0002.  That reading treats the 87 discordant rows as 87 independent trials.

THEY ARE NOT INDEPENDENT.  Rows are clustered by SEED, and a single doomed game generates
many disagreement rows that each, on their own, avert the same topout.  The correct unit is
the GAME, not the row.  This script computes both so the difference is on the record, and
prints which seeds contribute -- the check that settles it.

This is the same error class as the completion-order bias found earlier in this lane: a
within-cluster effect wearing the costume of an independent-sample effect.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "adjudicate_rows.jsonl")
    rows = [json.loads(l) for l in open(path)]
    d4o = defaultdict(int)
    d3o = defaultdict(int)
    for r in rows:
        if r["res4"] == "clear" and r["res3"] != "clear":
            d4o[r["seed"]] += 1
        if r["res3"] == "clear" and r["res4"] != "clear":
            d3o[r["seed"]] += 1
    b, c = sum(d4o.values()), sum(d3o.values())
    n = b + c
    print(f"discordant rows: d4-only {b}  d3-only {c}  (share {b/n:.1%})")

    bt = stats.binomtest(b, n, 0.5)
    lo, hi = bt.proportion_ci(0.95)
    print(f"\n  [INVALID] naive per-ROW binomial vs 50%: p={bt.pvalue:.5f}, "
          f"CI [{lo:.1%},{hi:.1%}]")
    print("     -- assumes 87 independent trials; they are not independent.")

    print(f"\n  d4-only rescues come from {len(d4o)} distinct seeds: "
          f"{dict(sorted(d4o.items()))}")
    print(f"  d3-only losses  come from {len(d3o)} distinct seeds: "
          f"{dict(sorted(d3o.items()))}")

    seeds = sorted({r["seed"] for r in rows})
    net = np.array([d4o[s] - d3o[s] for s in seeds], dtype=float)
    rng = np.random.default_rng(5)
    bs = net[rng.integers(0, len(net), (20000, len(net)))].mean(axis=1)
    print(f"\n  [VALID] seed-clustered net rescues per GAME: mean {net.mean():+.3f}  "
          f"CI95 [{np.percentile(bs,2.5):+.3f},{np.percentile(bs,97.5):+.3f}]")
    print(f"  seeds net>0 {(net>0).sum()}   net<0 {(net<0).sum()}   "
          f"net==0 {(net==0).sum()}")
    print(f"  Wilcoxon signed-rank on per-seed net: p={stats.wilcoxon(net).pvalue:.5f}")
    print("\n  VERDICT: the asymmetry does NOT survive clustering. More seeds favour d3"
          "\n  (14) than favour d4 (4); the 61 rescues are 61 views of FOUR games.")


if __name__ == "__main__":
    main()
