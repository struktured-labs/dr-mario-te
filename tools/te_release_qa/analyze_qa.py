#!/usr/bin/env python3
"""Compare two te_release_qa.lua runs (same scenario + seed, different ROMs) frame by frame.

frames.txt rows: <frame> <mode $46> <hash $0000-$07FF> <hash minus the stack page>
The stack page is excluded from the second hash because what sits around SP at end-of-frame is the
NMI's pushed return address (CPU phase), not game state.

  usage: analyze_qa.py <runA_dir> <runB_dir> [--json out.json]
Prints: frame counts, whether the mode sequences match, the first differing frame, how many frames
differ and in which top-level modes ($46: 0 title, 1 options, 3 level init, 4 play, 5 round-end
check, 7 end screen, 8 virus placement), and the PLAY frames that differ.
"""
from __future__ import annotations
import collections
import json
import sys


def load(d: str):
    rows = []
    for line in open(f"{d.rstrip('/')}/frames.txt"):
        if line.startswith("R "):
            continue
        f, m, h, hm = line.split()
        rows.append((int(f), int(m), int(h), int(hm)))
    return rows


def compare(a_dir: str, b_dir: str) -> dict:
    A, B = load(a_dir), load(b_dir)
    n = min(len(A), len(B))
    modes_a = [r[1] for r in A]
    modes_b = [r[1] for r in B]
    first_full = next((A[i][0] for i in range(n) if A[i][2] != B[i][2]), None)
    first_game = next((A[i][0] for i in range(n) if A[i][3] != B[i][3]), None)
    diff = [i for i in range(n) if A[i][3] != B[i][3]]
    by_mode = collections.Counter(A[i][1] for i in diff)
    play_diff = [A[i][0] for i in diff if A[i][1] == 4 and B[i][1] == 4]
    return {
        "frames": [len(A), len(B)],
        "mode_sequence_identical": modes_a == modes_b,
        "first_diff_full_ram": first_full,
        "first_diff_minus_stack": first_game,
        "frames_differing_minus_stack": len(diff),
        "differing_frames_by_mode": dict(sorted(by_mode.items())),
        "play_frames_differing": len(play_diff),
        "play_frames_differing_first10": play_diff[:10],
    }


if __name__ == "__main__":
    r = compare(sys.argv[1], sys.argv[2])
    print(json.dumps(r, indent=1))
    if "--json" in sys.argv:
        json.dump(r, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
