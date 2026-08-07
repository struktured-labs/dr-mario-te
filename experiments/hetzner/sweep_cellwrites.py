#!/usr/bin/env python3
"""Classify every direct board-cell write as (a) resting, (b) gravity-corrected,
or (c) writes unsupported cells with NO gravity call.

Heuristic, deliberately conservative: for each contiguous BLOCK of cell writes,
look ahead N lines for _apply_gravity / apply_gravity. Blocks without one are
reported for manual reading -- the script triages, it does not judge.
"""
import os
import re
import sys
from collections import defaultdict

ROOTS = [
    "/home/struktured/projects/dr-mario-qa-wt/experiments",
    "/home/struktured/projects/dr_mario_rl/tmp",
    "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src",
    "/home/struktured/projects/dr-mario-selfplay-wt",
    "/home/struktured/projects/dr-mario-main-wt/experiments",
]
WRITE = re.compile(r'^\s*[A-Za-z_][A-Za-z0-9_.]*\.(color|is_virus|link)\s*\[[^\]]*\]\s*=')
GRAV = re.compile(r'_?apply_gravity')
LOOKAHEAD = 14

def scan(path):
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return []
    hits = [i for i, l in enumerate(lines) if WRITE.match(l)]
    if not hits:
        return []
    # group into blocks of consecutive-ish writes
    blocks, cur = [], [hits[0]]
    for i in hits[1:]:
        if i - cur[-1] <= 6:
            cur.append(i)
        else:
            blocks.append(cur); cur = [i]
    blocks.append(cur)
    out = []
    for b in blocks:
        lo, hi = b[0], b[-1]
        window = lines[hi + 1: hi + 1 + LOOKAHEAD]
        has_grav = any(GRAV.search(w) for w in window)
        # also look a little BEFORE (some code settles then writes at rest)
        out.append((lo + 1, hi + 1, has_grav, lines[lo].strip()[:70]))
    return out

def main():
    seen = set()
    rows = defaultdict(list)
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git")]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(dirpath, fn)
                rp = os.path.realpath(p)
                if rp in seen:
                    continue
                seen.add(rp)
                for lo, hi, grav, txt in scan(p):
                    rows["B" if grav else "C?"].append((p, lo, hi, txt))

    for kind in ("C?", "B"):
        rs = rows[kind]
        label = ("NO gravity within %d lines -- READ THESE" % LOOKAHEAD) if kind == "C?" \
                else "gravity present (class b)"
        print(f"\n===== {kind}: {label} : {len(rs)} block(s) =====")
        for p, lo, hi, txt in sorted(rs):
            print(f"  {p.replace('/home/struktured/projects/','')}:{lo}-{hi}  {txt}")

if __name__ == "__main__":
    main()
