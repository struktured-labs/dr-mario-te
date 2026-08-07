#!/usr/bin/env python3
"""EXECUTION models for the tuck executor: what the CART does with a placement
the search has already chosen.

This is the independent-method half of the tuck-value question (team-lead's
corroboration assignment, 2026-08-06). The co-sim farm runs the real RTL and
scores a 2x2 of {s20b, s20t3} x {drop, tuck}. This module reproduces the same
2x2 in the FAST numba sim, where n is cheap, by separating the two halves the
project has always run together:

    DECISION   -- which (cells, colours) the search picks. Fixed within a
                  firmware vocabulary; identical across execution modes.
    EXECUTION  -- where the pill actually LANDS. This is what a DRTUCK=1 cart
                  would change, and it has never shipped on any cart
                  (DRTUCK appears in 2 of 67 manifests, "0" in both).

The point of splitting them is that the executor's value is then a
within-vocabulary difference with the brain held constant -- no confound from
the search seeing a different candidate set.


THE TWO FIRMWARE VOCABULARIES BEHAVE COMPLETELY DIFFERENTLY, and conflating
them is the main way this measurement could go wrong:

v1 (DRCOPRO_TUCK=1, the SHIPPED champion e970e9ab, fpga/copro/tuck_scan.py)
    publishes ONE descriptor: (approach_col, trigger_row), 0xFF = none. It
    does NOT publish a target column, and it never writes D_BC/D_BO -- the
    driver's destination stays whatever the BASE search chose (grepped by the
    co-sim farm: zero hits). So under v1 the DECISION IS PURE base32 IN BOTH
    MODES. The descriptor only changes the PATH: the executor
    (patch_cartridge_copro.py:1920-1926) steers to approach_col while the
    capsule is above trigger_row, then to best_col at/below it.

    That makes v1 the cleanest possible executor test -- literally the same
    brain, the same chosen (col, orient), only the landing row can differ --
    and it is also why v1 is incoherent by construction: tuck_scan picks
    (approach, trigger) to maximise depth for ITS OWN chosen target column,
    and the driver then flies to best_col, which need not be that column.

tier-3 (DRCOPRO_TUCKBFS=1 + DRCOPRO_TUCKBFS_TIER3=1, 5d010f62)
    scores tuck-class candidates inside the search (theta-margin gated) and,
    when one wins, OVERWRITES D_BC/D_BO with that candidate's target
    (tuck_v3.py:644-645). So the decision genuinely changes, and in `drop`
    mode the pill is steered to the tuck's column and orientation and then
    plain-dropped -- landing at the straight-drop rest, shallower than the
    cell the search scored. That is the "strictly worse than no tuck" hazard
    tuck_scan.py's own docstring names.


PHYSICS CONVENTION (row-major idx = r*8+c, colours 1-based, 0 = empty --
the fast sim's `col` plane, not the NES 0xFF-empty plane):
  horizontal variant (var in {0,1}) occupies (r, cc) and (r, cc+1)
  vertical   variant (var in {2,3}) occupies (r, cc) and (r-1, cc), anchor r
  = BOTTOM cell.
This matches descriptor_audit.py's `legal()` in the co-sim farm exactly, on
purpose: the "coherent" statistic has to mean the same thing in both rigs or
the reconciliation is meaningless. `_selftest_resting_matches_expand_core`
gates it against `fast_sim_x._expand_core`, which is the sim this rig
actually plays in -- so the physics is validated against the engine of
record, not merely against a second opinion.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
EXPERIMENTS = os.path.dirname(HERE)
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
CANON_COPRO = "/home/struktured/projects/dr-mario-canonical-wt/fpga/copro"
for _p in (HERE, EXPERIMENTS, os.path.join(EXPERIMENTS, "eval47"),
           ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src",
           QA, QA + "/tuck_v3", CANON_COPRO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ROWS, COLS = 16, 8
NES_EMPTY = 0xFF

# fast_rtl_x._VAR_OF_O4 = (2, 3, 0, 1): o4 {0,1}=VERT -> var {2,3};
# o4 {2,3}=HORIZ -> var {0,1}.  ab47.py:123 states the same test inline.
VERT_VARS = (2, 3)


def is_horizontal(var):
    return int(var) not in VERT_VARS


# --------------------------------------------------------------------------
# physics primitives (fast-sim `col` plane: 0 = empty)
# --------------------------------------------------------------------------
def occupied(col, r, c):
    return col[r * COLS + c] != 0


def legal(col, r, c, is_h):
    """Can the pill's anchor sit at (r, c)?  Anchor = left cell (H) / bottom
    cell (V)."""
    if r < 0 or r >= ROWS or c < 0 or c >= COLS:
        return False
    if is_h:
        if c + 1 >= COLS:
            return False
        return not occupied(col, r, c) and not occupied(col, r, c + 1)
    if r - 1 < 0:
        return False
    return not occupied(col, r, c) and not occupied(col, r - 1, c)


def fall_from(col, c, is_h, start_row):
    """Rest anchor row after entering at `start_row` and falling. None if the
    pill cannot even sit at the entry row."""
    if not legal(col, start_row, c, is_h):
        return None
    r = start_row
    while legal(col, r + 1, c, is_h):
        r += 1
    return r


def straight_drop_row(col, c, is_h):
    """Rest anchor row of a PLAIN drop into column c (enters from the top).
    Vertical needs r-1 >= 0 so it enters at row 1."""
    return fall_from(col, c, is_h, 0 if is_h else 1)


def first_occ(col, c):
    for r in range(ROWS):
        if occupied(col, r, c):
            return r
    return ROWS


# --------------------------------------------------------------------------
# v1 firmware descriptor -- fpga/copro/tuck_scan.py::ref_tuck_scan
# --------------------------------------------------------------------------
def _to_nes(col):
    return [NES_EMPTY if int(x) == 0 else int(x) for x in col]


def v1_descriptor(col):
    """(approach_col, trigger_row), or (None, None) when v1 publishes 0xFF.

    Delegates to the canonical firmware reference (`tuck_scan.ref_tuck_scan`,
    the file whose docstring says "the 6502 must agree with this cell-for-
    cell"), so this rig cannot drift from the shipped enumerator by
    re-deriving it. Import is deferred so that a caller that only needs the
    tier-3 arms does not depend on the canonical worktree being present."""
    import tuck_scan
    a, r = tuck_scan.ref_tuck_scan(_to_nes(col))
    if a == 0xFF:
        return (None, None)
    return (int(a), int(r))


def v1_execute(col, best_var, best_cc, approach, trigger, on_blocked="drop"):
    """Where does the pill LAND under a DRTUCK=1 cart running v1 firmware?

    The driver (patch_cartridge_copro.py:1920-1926) steers to `approach`
    while the capsule is above `trigger`, then to `best_cc` at/below it.
    There is NO check anywhere that the switch is possible -- if settled
    material blocks the traverse the capsule simply fails to move and lands
    wherever it is. That is the failure tuck_scan.py's own docstring calls
    "strictly worse than no tuck".

    Returns (rest_row, landed_col, status) where status is one of:
      "no_descriptor"  v1 published nothing -> plain drop
      "coherent"       the switch completed -> rests at fall_from(best_cc, trigger)
      "blocked"        the traverse could not complete

    `on_blocked` picks the convention for the blocked case:
      "drop"     degrade to a plain drop into best_cc. DELIBERATELY
                 CONSERVATIVE, and the same convention the co-sim farm uses,
                 so the two rigs' v1 numbers are comparable.
      "approach" the capsule lands in the approach column instead -- the
                 hazard the driver source actually implies. Reported
                 alongside "drop" rather than instead of it: the truth is
                 bracketed by the two and this rig cannot adjudicate which
                 the silicon does (the co-sim can).

    TRAVERSE MODEL (stated because it is an assumption, not a measurement):
    the capsule is treated as switching columns INSTANTANEOUSLY at `trigger`,
    requiring every intermediate anchor position at that row to be legal.
    Real DAS takes ~12 hooks per column edge while gravity keeps pulling the
    piece down, so a real capsule would traverse at progressively deeper
    rows and be blocked at least as often. This model is therefore
    OPTIMISTIC FOR THE EXECUTOR -- a null result under it is a strong null.
    """
    is_h = is_horizontal(best_var)
    plain = straight_drop_row(col, best_cc, is_h)
    if approach is None:
        return (plain, best_cc, "no_descriptor")

    # 1. the capsule must be able to occupy the approach column at the
    #    trigger row at all (it fell down `approach` to get there).
    if not legal(col, trigger, approach, is_h):
        return ((plain, best_cc, "blocked") if on_blocked == "drop"
                else (straight_drop_row(col, approach, is_h), approach, "blocked"))

    # 2. traverse approach -> best_cc at the trigger row, one column at a time.
    step = 1 if best_cc > approach else -1
    c = approach
    while c != best_cc:
        c += step
        if not legal(col, trigger, c, is_h):
            if on_blocked == "drop":
                return (plain, best_cc, "blocked")
            stuck = c - step
            return (fall_from(col, stuck, is_h, trigger), stuck, "blocked")

    rest = fall_from(col, best_cc, is_h, trigger)
    if rest is None:                       # cannot happen: legal() checked above
        return (plain, best_cc, "blocked")
    return (rest, best_cc, "coherent")


# --------------------------------------------------------------------------
# tier-3: degrade a chosen tuck to what today's cart would actually do
# --------------------------------------------------------------------------
def tier3_drop_action(p):
    """The 32-action straight drop a `drop`-mode cart performs when a tier-3
    tuck wins: tuck_v3.py:644-645 overwrites D_BC/D_BO with the winning
    candidate's target column and orientation, and the driver then plain-drops
    there. Both column and orientation come from the tuck; only the DEPTH is
    lost.

    `p` is a tuck_enum placement dict, whose own "variant"/"col" fields
    address the same (var, cc) slot `_expand_core` does -- reach_root.py's
    module docstring records that correspondence as verified by construction
    (512/512 straight drops found in TE's lookup, 0 misses), and
    `_selftest_variant_col_addresses_same_slot` re-checks it here rather than
    inheriting it on trust."""
    return int(p["variant"]) * 8 + int(p["col"])


# ==========================================================================
# self-tests -- run: python exec_model.py
# ==========================================================================
def _rand_boards(n, seed=20260806):
    """(col, vir) int8 pairs on reach_root's own random-board generator, so
    the self-tests run on the same board distribution the A/B rig's own
    self-tests (reach_root._selftest_*) already use. `_rand_board` returns a
    colour grid only; viruses are sprinkled over occupied cells here (they are
    irrelevant to the geometry these tests check, but `_expand_core` wants the
    plane)."""
    import random
    import numpy as np
    import reach_root as RR
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        grid = RR._rand_board(rnd)
        col = np.array(grid, dtype=np.int8)
        vir = np.zeros(len(grid), dtype=np.int8)
        for i, v in enumerate(grid):
            if v and rnd.random() < 0.25:
                vir[i] = 1
        out.append((col, vir))
    return out


def _selftest_resting_matches_expand_core(n_boards=400, seed=20260806):
    """THE GATE THAT MATTERS: `straight_drop_row` must reproduce the resting
    position of `fast_sim_x._expand_core` -- the function that actually places
    pills in this rig -- for every legal (variant, column) on every board.
    Tests the physics against the engine of record, not a second opinion.

    Mismatch here would silently corrupt every `drop`-mode arm, which is
    precisely the arm that claims to describe today's silicon."""
    import fast_sim_x as FS
    boards = _rand_boards(n_boards, seed)
    bad, checked = [], 0
    for col, _vir in boards:
        for var in range(4):
            for cc in range(COLS):
                # `_resting`, not `_expand_core`: the latter's third return is
                # the CLEARED-CELL COUNT (an int), not a cell tuple -- it
                # resolves the board after placing. Geometry lives in _resting.
                ok, r0, c0, r1, c1_ = FS._resting(col, var, cc)
                mine = straight_drop_row(col, cc, is_horizontal(var))
                if ok == 0:
                    # engine refuses -> my model must also find no legal rest
                    if mine is not None:
                        bad.append(("engine-illegal-mine-legal", var, cc, mine))
                    continue
                checked += 1
                anchor = max(r0, r1) if c0 == c1_ else r0
                if mine != anchor:
                    bad.append(("row", var, cc, mine, anchor))
    print(f"  resting vs _expand_core: {checked} legal placements, "
          f"{len(bad)} mismatches")
    for b in bad[:5]:
        print(f"    {b}")
    return not bad


def _selftest_variant_col_addresses_same_slot(n_boards=40, seed=20260806):
    """`tier3_drop_action(p)` is only correct if a tuck_enum placement's
    (variant, col) names the same 32-action slot `_expand_core` uses. Checked
    directly: for every STRAIGHT-DROP placement TE emits, the action it
    implies must expand to exactly the cells TE reported."""
    import fast_sim_x as FS
    import tuck_enum as TE
    from fb import FB
    boards = _rand_boards(n_boards, seed)
    bad, checked = [], 0
    for col, vir in boards:
        # link plane is all-zero here: TE.enumerate reads occupancy geometry
        # only, and these are synthetic boards with no locked pairs to track.
        # (The link plane DOES matter for gravity in real play -- see
        # board_flat_from_fb's own col/vir-only export -- but no gravity is
        # run in this self-test.)
        fb = FB.from_lists(col.tolist(), vir.tolist(), [0] * (ROWS * COLS))
        for p in TE.enumerate(fb, 1, 2, mode="free"):
            if p["is_tuck"]:
                continue
            var, cc = int(p["variant"]), int(p["col"])
            ok, r0, c0, r1, c1_ = FS._resting(col, var, cc)
            if ok == 0:
                continue
            checked += 1
            if (r0, c0, r1, c1_) != tuple(p["cells"]):
                bad.append((var, cc, (r0, c0, r1, c1_), tuple(p["cells"])))
    print(f"  TE (variant,col) -> _expand_core slot: {checked} straight drops, "
          f"{len(bad)} mismatches")
    for b in bad[:5]:
        print(f"    {b}")
    return not bad


def _selftest_v1_coherent_implies_no_shallower(n_boards=600, seed=20260807):
    """A COHERENT v1 execution can never land SHALLOWER than the plain drop it
    replaces: it enters best_col at `trigger` and falls, and the plain drop
    enters at the top and falls, so if both reach the same pocket they rest on
    the same floor. Anything else means the traverse model is wrong.

    Also reports the frequency of the outcome the whole v1 arm turns on --
    how often a coherent execution lands STRICTLY DEEPER, i.e. how often the
    executor does anything at all."""
    import fast_sim_x as FS
    boards = _rand_boards(n_boards, seed)
    shallower, coherent, deeper, published = [], 0, 0, 0
    for col, _vir in boards:
        approach, trigger = v1_descriptor(col)
        if approach is None:
            continue
        published += 1
        for var in range(4):
            for cc in range(COLS):
                ok = FS._resting(col, var, cc)[0]
                if ok == 0:
                    continue
                rest, landed, status = v1_execute(col, var, cc, approach, trigger)
                if status != "coherent":
                    continue
                coherent += 1
                plain = straight_drop_row(col, cc, is_horizontal(var))
                if rest < plain:
                    shallower.append((var, cc, rest, plain))
                elif rest > plain:
                    deeper += 1
    print(f"  v1 coherent executions: {coherent} over {published} boards with a "
          f"descriptor; {deeper} land deeper ({deeper / max(1, coherent):.1%}), "
          f"{len(shallower)} land SHALLOWER (must be 0)")
    for b in shallower[:5]:
        print(f"    {b}")
    return not shallower


def run_selftests():
    print("=== exec_model self-tests ===")
    results = {
        "resting_matches_expand_core": _selftest_resting_matches_expand_core(),
        "variant_col_same_slot": _selftest_variant_col_addresses_same_slot(),
        "v1_coherent_never_shallower": _selftest_v1_coherent_implies_no_shallower(),
    }
    print()
    ok = True
    for k, v in results.items():
        state = "SKIP" if v is None else ("PASS" if v else "FAIL")
        print(f"  {state}  {k}")
        ok = ok and (v is not False)
    print("\nALL PASS" if ok else "\nFAILURES PRESENT")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run_selftests() else 1)
