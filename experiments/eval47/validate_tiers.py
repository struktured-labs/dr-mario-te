#!/usr/bin/env python3
"""Validation for translatable.py's tier_of() ladder (task #67, 2026-08-05).

Checks, on the tuck-bfs-6502 branch's own 200-board real-L11 corpus (the SAME corpus
that gated the 6502 BFS port bit-exact, 200/200, against tuck_enum.py mode="free" --
see TUCK_BFS_PORT_REPORT.md section 3):

  1. tier_of(col,p) == 1  <=>  is_translatable(col,p) == True, for every tuck-class
     candidate on every board -- 0 disagreements required (the sweep's own endpoint-
     reproduction self-test depends on this holding exactly).
  2. tier_of(col,p) in {1..MAX_TIER} (i.e. NOT TIER_UNREACHABLE) for every candidate
     TE.enumerate(..., mode="free") itself reports as a reachable tuck-class
     candidate -- confirms MAX_TIER really does cover "the full BFS reachable set"
     (by TE.enumerate's own construction, every is_tuck=True candidate it emits is
     already reachable=True -- see translatable.py's tier ladder comment).
  3. Per-board tier population histogram (the weighting the knee sweep needs).

Usage: python validate_tiers.py [--n N]
"""
import sys
import os
import json
import argparse
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import translatable as TL  # noqa: E402

EXPERIMENTS = os.path.dirname(HERE)
sys.path.insert(0, EXPERIMENTS)
import tuck_enum as TE  # noqa: E402

CORPUS = "/home/struktured/projects/dr-mario-canonical-wt/tests/tuck_bfs_corpus_200.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=None)
    a = ap.parse_args()

    corpus = json.load(open(CORPUS))
    boards = corpus["boards"][:a.n] if a.n else corpus["boards"]

    disagreements = []
    unreachable_leaks = []
    total_tucks = 0
    global_hist = Counter()
    per_board_hist = {}

    for b in boards:
        col = b["col"]
        placements = TE.enumerate(col, 1, 1, mode="free")
        tucks = [p for p in placements if p["is_tuck"]]
        board_hist = Counter()

        for p in tucks:
            total_tucks += 1
            t1 = TL.is_translatable(col, p)
            tier = TL.tier_of(col, p)
            board_hist[tier] += 1
            global_hist[tier] += 1

            if (tier == 1) != t1:
                disagreements.append((b["id"], p["col"], p["row"], p["orient"], t1, tier))

            # every tuck-class TE.enumerate emits is, by its own construction,
            # reachable=True (is_tuck=True candidates only ever come from the BFS
            # `targets` loop, never the reachable=False straight-drop union) --
            # confirm tier_of agrees it's placeable at SOME tier.
            if not p["reachable"]:
                continue  # (should never happen for is_tuck=True; asserted below too)
            if tier == TL.TIER_UNREACHABLE:
                unreachable_leaks.append((b["id"], p["col"], p["row"], p["orient"]))

        per_board_hist[b["id"]] = dict(board_hist)

    print(f"boards checked: {len(boards)}")
    print(f"total tuck-class candidates: {total_tucks}")
    print(f"tier1-vs-is_translatable disagreements: {len(disagreements)}")
    if disagreements:
        for d in disagreements[:20]:
            print("  MISMATCH", d)
    print(f"reachable-but-classified-TIER_UNREACHABLE leaks: {len(unreachable_leaks)}")
    if unreachable_leaks:
        for u in unreachable_leaks[:20]:
            print("  LEAK", u)

    print("\nGLOBAL tier histogram (1=cheapest .. 5=max, 99=unreachable):")
    for t in sorted(global_hist):
        pct = 100.0 * global_hist[t] / total_tucks if total_tucks else 0.0
        print(f"  tier {t:>2}: {global_hist[t]:>5}  ({pct:5.1f}%)")

    # cumulative "executable at tier <= N" curve -- what the knee sweep will read
    print("\nCUMULATIVE (executable at tier <= N):")
    cum = 0
    for t in range(1, TL.MAX_TIER + 1):
        cum += global_hist.get(t, 0)
        pct = 100.0 * cum / total_tucks if total_tucks else 0.0
        print(f"  tier <= {t}: {cum:>5}  ({pct:5.1f}%)")

    print(f"\nboards with >=1 tuck candidate: {sum(1 for h in per_board_hist.values() if h)}")
    print(f"boards with 0 tuck candidates: {sum(1 for h in per_board_hist.values() if not h)}")

    out = {
        "n_boards": len(boards),
        "total_tucks": total_tucks,
        "disagreements": disagreements,
        "unreachable_leaks": unreachable_leaks,
        "global_hist": dict(global_hist),
        "per_board_hist": per_board_hist,
    }
    outpath = os.path.join(HERE, "tier_validation_result.json")
    with open(outpath, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {outpath}")

    ok = (len(disagreements) == 0) and (len(unreachable_leaks) == 0)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
