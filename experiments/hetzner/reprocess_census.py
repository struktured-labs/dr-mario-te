#!/usr/bin/env python3
"""reprocess_census.py -- apply the degenerate detector to rows already on disk,
so the classification is consistent front-to-back.

The census gained a degenerate-row detector partway through its run. Without
this, rows written before that point carry the old labels and rows after carry
the new ones, and any count over the whole file silently mixes two conventions
-- the same class of hazard as running two code versions on two nodes.

Rewrites in place (with a .bak), reports before/after counts, and re-verifies
the failure signature that the contamination would have destroyed.

Usage: reprocess_census.py results/full/census.jsonl [--dry-run]
"""
from __future__ import annotations

import os
import sys
import json
import shutil
import argparse
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
sys.path.insert(0, HERE)
sys.path.insert(0, QA)

from census import pill_stream_colours, classify_degenerate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = []
    with open(a.path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    before = Counter(r["result"] for r in rows)
    changed = []
    for r in rows:
        if r["result"] == "clear":
            continue                      # a win is never a non-game
        n_col = r.get("n_pill_colours")
        if n_col is None:
            n_col = pill_stream_colours(r["seed"])
            r["n_pill_colours"] = n_col
        reason = classify_degenerate(r.get("trace") or [], n_col)
        if reason is not None and r["result"] != "degenerate":
            changed.append((r["seed"], r["result"], reason))
            r["original_result"] = r["result"]
            r["result"] = "degenerate"
            r["degenerate_reason"] = reason
            r["dies_ahead"] = False

    after = Counter(r["result"] for r in rows)
    print(f"rows: {len(rows)}")
    print(f"before: {dict(before)}")
    print(f"after : {dict(after)}")
    print(f"\nrelabelled {len(changed)}:")
    for seed, old, reason in changed:
        print(f"  seed {seed}: {old} -> degenerate ({reason})")

    genuine = [r for r in rows if r["result"] in ("topout", "stall")]
    print(f"\nGENUINE failures: {len(genuine)}")
    for r in genuine:
        print(f"  seed {r['seed']:>6} {r['result']:>6} viruses_left={r['viruses_left']} "
              f"pills={r['pills']} moves={r['n_moves']}")
    vl = {r["viruses_left"] for r in genuine}
    if genuine:
        print(f"  viruses_left across genuine failures: {sorted(vl)}"
              f"{'  <- LAST-VIRUS signature intact' if vl == {1} else ''}")

    n_playable = sum(1 for r in rows if r["result"] != "degenerate")
    n_fail = len(genuine)
    print(f"\nfailure rate over PLAYABLE seeds: {n_fail}/{n_playable} "
          f"= {100 * n_fail / max(1, n_playable):.3f}%")

    if a.dry_run:
        print("\n(dry run -- nothing written)")
        return
    shutil.copy(a.path, a.path + ".bak")
    with open(a.path, "w") as f:
        for r in sorted(rows, key=lambda x: x["seed"]):
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
    print(f"\nrewrote {a.path} (backup {a.path}.bak)")


if __name__ == "__main__":
    main()
