#!/usr/bin/env python3
"""#26 -- does the TARGETED credit actually flip the probe, and does it do so monotonically?

The primary ship criterion is a FULL probe flip (3 abandoned-material positions -> 0) at
win-neutral-or-better. That makes "does w_dbl reach 0/36, and at what dose" a prerequisite
question, answerable for pennies, and it should be answered BEFORE any paired h2h spends
hours resolving win rates for an arm that cannot clear the gate anyway.

Monotonicity is the second witness the design asked for. A correctly threaded reward should
move the population in one direction as the dose rises; a response that wanders (fixes at 40,
breaks at 60, fixes at 100) would say the credit is perturbing the search rather than
expressing a preference -- the kind of thing 480 positions of a neutrality check cannot see.

★ Read alongside instant_double_price.py, which prices the SAME positions through w_cells.
The two mechanisms are expected to differ: w_cells rewards cascades too and so converts
SINGLE -> CASCADE cheaply, while w_dbl pays only the double and structurally cannot.
"""
from __future__ import annotations
import sys
from collections import Counter

for p in ("/home/struktured/projects/dr_mario_rl/tmp/vs_aware",
          "/home/struktured/projects/dr_mario_rl/tmp/combo_term",
          "/home/struktured/projects/dr_mario_rl/tmp/champion",
          "/home/struktured/projects/dr_mario_rl/tmp/pillrng",
          "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src",
          "/home/struktured/projects/dr-mario-qa-wt/experiments"):
    if p not in sys.path:
        sys.path.insert(0, p)

import fast_rtl_x as F                                              # noqa: E402
import cascade_dbl_x as D                                           # noqa: E402
from drmario.faithful_game import Pill                              # noqa: E402
from h2h_vs import ARMS, idx_map                                    # noqa: E402
from instant_double_probe import (build_at_height, enumerate_actions,  # noqa: E402
                                  RED, YEL, BLU)

DOSES = [0, 20, 40, 60, 100, 150]
HEIGHTS = [(0, "WALL"), (3, "h3"), (6, "h6"), (9, "h9")]
COLOURS = [(BLU, YEL), (RED, BLU), (YEL, RED)]


def main():
    D.warmup_dbl(8)
    w, fl = F.variant("winner")
    m = idx_map()
    for k, v in ARMS["chain180"].items():
        if k in m:
            w[m[k]] = float(v)

    positions = []
    for base_h, lbl in HEIGHTS:
        for c0 in (1, 3, 5):
            for ca, cb in COLOURS:
                e = build_at_height(c0, base_h, 12, ca, cb, Pill(RED, RED))
                res = enumerate_actions(e, e.cur)
                dbl = {r[0] for r in res if r[3] and r[3] >= 8 and r[5] == 1}
                if dbl:
                    positions.append((lbl, c0, ca, cb, e, res, dbl))
    print("positions offering an instant double: %d\n" % len(positions))

    grid = {}
    for dose in DOSES:
        dec = D.DblRewardD3Decider(w, fl, topk2=8, maxpass=0, w_chain=180, w_dbl=dose)
        per_h, left, kinds = {}, 0, {}
        for lbl, c0, ca, cb, e, res, dbl in positions:
            a = dec.choose(e.board, e.cur, e.nxt)
            r = next((x for x in res if x[0] == a), None)
            cells = (r[3] or 0) if r else 0
            k = ("DOUBLE" if a in dbl else "CASCADE" if cells >= 8
                 else "SINGLE" if cells >= 4 else "NO-CLEAR")
            per_h.setdefault(lbl, Counter())[k] += 1
            kinds[(lbl, c0, ca, cb)] = k
            if k in ("SINGLE", "NO-CLEAR"):
                left += 1
        grid[dose] = (left, kinds)
        print("w_dbl=%-4d material-left=%d/%d   %s%s"
              % (dose, left, len(positions), {h: dict(c) for h, c in per_h.items()},
                 "   <- chain180 as shipped" if dose == 0 else ""))

    print()
    seq = [grid[d][0] for d in DOSES]
    monotone = all(b <= a for a, b in zip(seq, seq[1:]))
    print("material-left across the ladder: %s" % seq)
    print("MONOTONE (never gets worse as the dose rises): %s" % monotone)
    if not monotone:
        print("  ⚠ A non-monotone response means the credit is PERTURBING the search rather")
        print("    than expressing a preference. Do not ladder it until that is understood.")

    flip = next((d for d in DOSES if grid[d][0] == 0), None)
    print()
    if flip is None:
        print("★ w_dbl NEVER reaches a full flip within %d." % DOSES[-1])
        print("  The primary ship criterion (3->0) is NOT reachable by this mechanism at")
        print("  these doses. Report that before spending h2h CPU on it.")
        base_bad = [k for k, v in grid[0][1].items() if v in ("SINGLE", "NO-CLEAR")]
        for k in base_bad:
            print("     %s : %s" % (k, [grid[d][1][k] for d in DOSES]))
    else:
        print("★ FULL FLIP (3 -> 0) at w_dbl=%d." % flip)
        print("  That is the cheapest targeted dose meeting the primary criterion; the h2h")
        print("  decides whether it is win-neutral-or-better.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
