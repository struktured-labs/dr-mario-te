#!/usr/bin/env python3
"""Task #91: two farm-regime facts the PRESTART_LATENCY_MEMO's stage-A model needs.

Runs the CHAMPION under the farm's own bursty pressure (pressure_rig.play, the same decider
and the same injector the farm uses) and records the board + hit columns at EVERY release.
The corpus matters: my earlier prestart fire-rate came from RANDOM play, which stacks far
higher than the champion, so it could only bound the answer from the pessimistic side.

Reports two things, both about garbage in the farm, neither measured before:

(1) INJECTOR SKIP RATE. `inject_bursty_garbage` (bursty_model.py:638) and its ancestor
    `_inject_garbage` (pressure_rig.py:113) both `continue` on a column whose row-0 cell is
    occupied -- "skip silently". The ROM does the OPPOSITE: checkReleaseAttack's row-0 write
    is an unconditional `sta` that OVERWRITES. So the farm silently DROPS pressure exactly
    where the board is tall, which is the regime that decides games.
    ★ The upside of the same line: because it never overwrites, the farm CANNOT produce the
    orphaned-linked-half state that breaks vs_harness.drop_garbage. That worry is closed for
    every bursty result, and this run quantifies what the farm pays for the immunity.

(2) PRESTART FIRE RATE vs h. The memo's stage-A accounting credits the prestart arm
    `min(F, 264 - 16*h)` frames at every release. That assumes the prestart always fires.
    It does not: it bails on a 4-run, on a mid-animation tile, and on an orphaned link, and
    the bail rate CLIMBS with h -- i.e. it is worst exactly where the memo says latency binds.
    An uncorrected credit overprices DRPRESTART, worst in the near-death regime.

CORPUS -- and why there is only one. This drives `pressure_rig.play`, the farm's OWN
decider and injector. There is no cheaper stand-in: random legal play at L11 tops out at a
MEDIAN OF 15 PILLS, below the drip model's own `GARBAGE_MIN_PILLS = 25`, so it records
literally zero releases on the farm's schedule -- it does not merely stack differently, it
never reaches the pressure phase at all. Measured, not assumed (20 games: 7..23 pills).
Substituting it would have produced a table that looked like an answer for a regime the
farm never visits.

`fast_rtl_x` needs numba, absent from every dr-mario env on this box. Install it into a
FRESH venv (uv), never into one another lane is running jobs out of.

    experiments/prestart/farm_regime_audit.py [n_seeds]      # default 24
"""
from __future__ import annotations

import os
import random
import sys

import numpy as np

EVAL47 = "/home/struktured/projects/dr-mario-main-wt/experiments/eval47"
SIMSRC = "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src"
COMBO = "/home/struktured/projects/dr_mario_rl/tmp/combo_term"
for p in (EVAL47, SIMSRC, COMBO, "/home/struktured/projects/dr_mario_rl/tmp/endgame"):
    if p not in sys.path:
        sys.path.insert(0, p)

from drmario.faithful_game import EMPTY, LINK_NONE            # noqa: E402

REL = []          # one record per release


def stack_height(board, c):
    """16 - topmost occupied row; 0 if empty. The h in W = 264 - 16*h."""
    for r in range(board.rows):
        if board.color[r, c] != EMPTY:
            return board.rows - r
    return 0


def prestart_verdict(board, cols):
    """Would the 6502 prestart FIRE, and if not why? Mirrors the emitted routine's bail set,
    evaluated on the PRE-release board where each fact is unambiguous.

    Deliberately a re-implementation, not a call into the driver: the driver's own agreement
    with the faithful sim is already established at 1000/1000 by test_prestart_settle.py, and
    what this file needs is the DECISION, cheaply, on tens of thousands of releases.
    """
    # orphan: the volley would overwrite a cell that is half of a linked capsule
    for c in cols:
        if board.color[0, c] != EMPTY and board.link[0, c] != LINK_NONE:
            return "bail:orphan"
    # 4-run: project the settle and look for a completed line through a landed cell
    b = board.clone()
    for c in cols:
        b.color[0, c] = random.Random(c).randint(1, 3)
        b.link[0, c] = LINK_NONE
        b.is_virus[0, c] = False
    while b._apply_gravity():
        pass
    for c in cols:
        rs = [r for r in range(b.rows) if b.color[r, c] != EMPTY]
        if not rs:
            continue
        r = min(rs)
        col = int(b.color[r, c])
        run = 0
        for cc in range(b.cols):
            run = run + 1 if int(b.color[r, cc]) == col else 0
            if run >= 4:
                return "bail:4run"
        run = 0
        for rr in range(b.rows):
            run = run + 1 if int(b.color[rr, c]) == col else 0
            if run >= 4:
                return "bail:4run"
    return "fire"


def _record(board, seed, pills_placed, k):
    """Draw the volley columns exactly as the injector will, then record what BOTH the farm
    and the 6502 prestart would do with them -- before anything mutates the board."""
    rng = random.Random(seed * 1000 + pills_placed)
    cols = rng.sample(range(board.cols), k)
    skipped = [c for c in cols if board.color[0, c] != EMPTY]
    hs = [stack_height(board, c) for c in cols]
    REL.append(dict(seed=seed, pills=pills_placed, cols=list(cols),
                    n_skipped=len(skipped), h_min=min(hs), h_max=max(hs),
                    verdict=prestart_verdict(board, cols)))


def collect_champion(n_seeds):
    import pressure_rig as PR
    orig = PR._inject_garbage

    def recorder(board, s, pills_placed, k=None):
        _record(board, s, pills_placed, PR.GARBAGE_K if k is None else k)
        return orig(board, s, pills_placed, k)

    PR._inject_garbage = recorder
    PR._init(11, 6, 20)                    # shipped champion arm (wt=6, ws=20)
    for i in range(n_seeds):
        PR.play(1000 + i)


def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    try:
        import numba  # noqa: F401
    except ImportError:
        sys.exit("FATAL: needs numba (fast_rtl_x). Install into a FRESH venv:\n"
                 "  uv venv --python 3.12 farmenv && uv pip install --python farmenv/bin/python "
                 "numba numpy gymnasium\n"
                 "Do NOT install into a venv another lane is running jobs out of, and do NOT "
                 "substitute random play -- it never reaches the drip's min_pills (see the "
                 "module docstring).")
    collect_champion(n_seeds)

    n = len(REL)
    assert n, "no releases recorded -- the injector hook did not fire"
    tot_cells = sum(len(r["cols"]) for r in REL)
    tot_skip = sum(r["n_skipped"] for r in REL)

    print("=" * 78)
    print("FARM-REGIME GARBAGE AUDIT -- champion (wt=6 ws=20), pressure_rig drip injector")
    print("=" * 78)
    print("seeds %d   releases %d   volley cells %d" % (n_seeds, n, tot_cells))
    print()
    print("(1) INJECTOR SKIP -- cells the farm silently DROPS that the ROM would deliver")
    print("    total skipped: %d / %d = %.2f%% of all volley cells"
          % (tot_skip, tot_cells, 100.0 * tot_skip / tot_cells))
    buckets = {}
    for r in REL:
        b = min(15, r["h_max"])
        d = buckets.setdefault(b, [0, 0])
        d[0] += len(r["cols"])
        d[1] += r["n_skipped"]
    print("    %-8s %8s %8s %8s" % ("h_max", "cells", "skipped", "skip%"))
    for h in sorted(buckets):
        c, s = buckets[h]
        print("    %-8d %8d %8d %7.1f%%" % (h, c, s, 100.0 * s / c))

    print()
    print("(2) PRESTART FIRE RATE by h_min (W = 264 - 16*h frames)")
    strat = {}
    for r in REL:
        d = strat.setdefault(r["h_min"], {"fire": 0, "bail:orphan": 0, "bail:4run": 0})
        d[r["verdict"]] += 1
    print("    %-6s %7s %8s %7s %7s %9s %12s" %
          ("h_min", "n", "fire%", "orphan", "4run", "W (f)", "E[credit] f"))
    for h in sorted(strat):
        d = strat[h]
        tot = sum(d.values())
        p = d["fire"] / tot
        W = 264 - 16 * h
        print("    %-6d %7d %7.1f%% %7d %7d %9d %12.1f"
              % (h, tot, 100.0 * p, d["bail:orphan"], d["bail:4run"], W, p * max(0, W)))
    allf = sum(1 for r in REL if r["verdict"] == "fire")
    print("    overall fire rate: %d/%d = %.1f%%" % (allf, n, 100.0 * allf / n))
    print()
    print("READ: column 'E[credit]' is the memo's min(F, 264-16h) credit CORRECTED by the")
    print("      probability the prestart actually fires. Stage A must use this, not W.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
