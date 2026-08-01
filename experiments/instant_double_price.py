#!/usr/bin/env python3
"""#26 step 2, part 1 -- PRICE the instant-double mis-ranking before designing a credit for it.

The standing instruction for the credit is "start small, vbonus400-scale overshoots". That
is a prior about magnitude, and priors about magnitude are exactly the thing this project
keeps measuring instead of assuming. So: measure the gap first, THEN pick the ladder.

THE INSTRUMENT. At the failing positions the AI passes up an 8-cell instant double and takes
a 6-cell single, so the double is already ahead on immediate reward by
`2 cells * w_cells = 20` and still loses -- something in the LEAF value of the resulting
board prefers the single by MORE than 20. Raising `w_cells` scales the part of the
comparison that favours the double, at 2 cells per step, so the value of w_cells at which a
position flips measures the leaf-value gap directly:

        gap  ~=  2 * (w_cells_flip - w_cells_ship)          [w_cells_ship = 10]

⚠ THIS IS A RULER, NOT THE PROPOSED FIX. Raising w_cells globally re-prices EVERY clear, not
just doubles, which is why the credit under design is a targeted `lines>=2 in round 1` term.
The sweep exists to turn "start small" into a number, and to say what "small" has to beat.

★ It also reports REGRESSIONS -- positions that are correct at the shipped weight and stop
being correct as the dial turns. A dose that fixes h3 by breaking h6 is not a dose, and a
one-sided sweep would never have noticed. Same reason every arm gets its own --no-garbage
control rather than borrowing another arm's.
"""
from __future__ import annotations
import sys

for p in ("/home/struktured/projects/dr_mario_rl/tmp/vs_aware",
          "/home/struktured/projects/dr_mario_rl/tmp/combo_term",
          "/home/struktured/projects/dr_mario_rl/tmp/champion",
          "/home/struktured/projects/dr_mario_rl/tmp/pillrng",
          "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src",
          "/home/struktured/projects/dr-mario-qa-wt/experiments"):
    if p not in sys.path:
        sys.path.insert(0, p)

from drmario.faithful_game import Pill                        # noqa: E402
from h2h_vs import ARMS, _mk                                  # noqa: E402
from instant_double_probe import (build_at_height, enumerate_actions,  # noqa: E402
                                  RED, YEL, BLU, COLS)

SHIP_WCELLS = 10
DOSES = [10, 12, 15, 20, 25, 30, 40, 60, 90]
HEIGHTS = [(0, "WALL"), (3, "h3"), (6, "h6"), (9, "h9")]
COLOURS = [(BLU, YEL), (RED, BLU), (YEL, RED)]


def classify(a, res, dbl):
    r = next((x for x in res if x[0] == a), None)
    cells, rounds = (r[3] or 0), (r[5] or 0)
    if a in dbl:
        return "DOUBLE", cells, rounds
    return ("CASCADE" if cells >= 8 else
            "SINGLE" if cells >= 4 else "NO-CLEAR"), cells, rounds


def main():
    # Build the position set ONCE and keep the enumeration, so every dose is graded against
    # an identical board and an identical measured notion of "what the double is".
    positions = []
    for base_h, lbl in HEIGHTS:
        for c0 in (1, 3, 5):
            for ca, cb in COLOURS:
                e = build_at_height(c0, base_h, 12, ca, cb, Pill(RED, RED))
                res = enumerate_actions(e, e.cur)
                dbl = {r[0] for r in res if r[3] and r[3] >= 8 and r[5] == 1}
                if dbl:
                    positions.append((lbl, c0, ca, cb, e, res, dbl))
    print("positions offering an instant double: %d" % len(positions))
    print("(a position with no double on the table is skipped, not graded)\n")

    base_arm = ARMS["chain180"]
    results = {}
    for dose in DOSES:
        cand = dict(base_arm, wcells=dose)
        dec = _mk(cand, 8)
        kinds = []
        for lbl, c0, ca, cb, e, res, dbl in positions:
            a = dec.choose(e.board, e.cur, e.nxt)
            k, cells, rounds = classify(a, res, dbl)
            kinds.append((lbl, c0, ca, cb, k))
        results[dose] = kinds
        from collections import Counter
        per_h = {}
        for lbl, _, _, _, k in kinds:
            per_h.setdefault(lbl, Counter())[k] += 1
        left = sum(1 for _, _, _, _, k in kinds if k in ("SINGLE", "NO-CLEAR"))
        tag = "  <- shipped" if dose == SHIP_WCELLS else ""
        print("w_cells=%-3d  material-left=%d/%d   %s%s"
              % (dose, left, len(kinds),
                 {h: dict(c) for h, c in per_h.items()}, tag))

    # ---- what actually changed, position by position -----------------------------------
    base = {(l, c, a, b): k for l, c, a, b, k in results[SHIP_WCELLS]}
    print("\n--- per-position flip points (only positions that ever change) ---")
    flip_at, regress = {}, []
    for lbl, c0, ca, cb, e, res, dbl in positions:
        key = (lbl, c0, ca, cb)
        seq = [(d, dict(((l, c, a, b), k) for l, c, a, b, k in results[d])[key])
               for d in DOSES]
        if len({k for _, k in seq}) == 1:
            continue
        print("  %-5s cols %d/%d colours %d/%d : %s"
              % (lbl, c0, c0 + 1, ca, cb,
                 "  ".join("%d:%s" % (d, k) for d, k in seq)))
        was_bad = base[key] in ("SINGLE", "NO-CLEAR")
        if was_bad:
            fixed = next((d for d, k in seq if k not in ("SINGLE", "NO-CLEAR")), None)
            if fixed is not None:
                flip_at[key] = fixed
        else:
            broke = next((d for d, k in seq if k in ("SINGLE", "NO-CLEAR")), None)
            if broke is not None:
                regress.append((key, broke))

    print("\n" + "=" * 72)
    bad0 = [k for k, v in base.items() if v in ("SINGLE", "NO-CLEAR")]
    print("At the SHIPPED weight, %d position(s) leave material on the table." % len(bad0))
    if not bad0:
        print("Nothing to price -- the probe finds no mis-ranking to pay for.")
        return 0
    if len(flip_at) < len(bad0):
        unfixed = [k for k in bad0 if k not in flip_at]
        print("⚠ %d of them NEVER flip, even at w_cells=%d:" % (len(unfixed), DOSES[-1]))
        for k in unfixed:
            print("     %s" % (k,))
        print("  Those are NOT a magnitude problem -- no amount of per-cell reward reaches")
        print("  them, so a bigger dose is the wrong lever and a targeted term may be too.")
    if flip_at:
        need = max(flip_at.values())
        print("Every FIXABLE position is correct by w_cells=%d." % need)
        print("Implied leaf-value gap: ~2 cells x (%d - %d) = ~%d points."
              % (need, SHIP_WCELLS, 2 * (need - SHIP_WCELLS)))
        print("So a targeted lines>=2 credit needs to be worth roughly that much --")
        print("compare vbonus=400, which is %.0fx larger and known to overshoot."
              % (400.0 / max(1, 2 * (need - SHIP_WCELLS))))
    if regress:
        print("\n⚠ REGRESSIONS -- correct at the shipped weight, broken by the dial:")
        for k, d in regress:
            print("     %s first breaks at w_cells=%d" % (k, d))
        print("  A global per-cell raise is therefore NOT a candidate fix, only a ruler.")
    else:
        print("\nNo position that was correct at the shipped weight regresses across the sweep.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
