#!/usr/bin/env python3
"""PYTHON REFERENCE for the tuck v3 multi-candidate, both-orientation firmware enumerator.

Task #17 phase 3 stage 2 (team-lead approved decisions #1/#2, 2026-08-02): extend the
existing single-descriptor, vertical-only `tuck_scan` (tuck_scan.py) to both orientations
and a bounded candidate list. Same workflow the codebase already used for v1 -- write the
reference FIRST, validate it, THEN port to 6502 against it. tuck_scan.py's own docstring:
"The 6502 must agree with this cell-for-cell." No 6502/assembly changes here; this file is
the reference the future emitter must match.

ORIENT ENCODING matches tuck_enum.py's ring (H=0, V=1, RH=2, RV=3) and _VAR_OF_O4's
convention: geometry (which two cells) is independent of which colour lands on which cell.
A GEOMETRIC candidate (a specific pair of rest cells) is scored as TWO SEPARATE search
candidates, one per colour assignment -- exactly how the base 32-action search treats
variant 0 vs 2 (same cells, swapped colours) as distinct actions, not one action with an
implicit colour choice. Vertical geometry -> orient in {1 (V), 3 (RV)}; horizontal geometry
-> orient in {0 (H), 2 (RH)}. This DOUBLES the raw candidate count versus a naive single-
colour-per-cell-pair enumeration; see CAPACITY note below.

ALGORITHM. Same adjacent-approach-column, any-row model as v1's ref_tuck_scan (deliberately
NOT generalised beyond adjacent columns -- that restriction is what the phase-1/phase-2
offline proof, root_search._exec_reach_cells, actually measured; going further would be
unmeasured territory):

  VERTICAL (geometry unchanged from v1, now emitted at BOTH orient 1 and 3): target column
  c, approach a in {c-1,c+1}. For trigger row r in [first_occ(c), first_occ(a)-1]: if (r,c)
  is empty, the pill can enter c at r and falls to rest row rf. Keep if rf is strictly
  deeper than the straight-drop rest in c.

  HORIZONTAL (new geometry, emitted at BOTH orient 0 and 2): target ANCHOR column c (pill
  occupies columns c, c+1 at a shared row), approach ANCHOR column a in {c-1, c+1} (so the
  pill's TWO-COLUMN footprint is (a,a+1) while approaching -- a=c-1 slides one step right
  onto (c,c+1); a=c+1 slides one step left). fc = first_occ across BOTH target columns
  (min(first_occ(c), first_occ(c+1)), matching _resting()'s own horizontal formula); sd =
  fc-1. fa = first_occ across BOTH approach columns. For trigger row r in [fc, fa-1]: if
  BOTH (r,c) and (r,c+1) are empty, the pill can enter there and falls (both cells together)
  to rest row rf. Keep if rf > sd.

CANDIDATE LIST, not single-descriptor: v1 kept only the single deepest-over-everything
winner -- that decoupling from the search's own best_col is exactly defect D3, root-action's
whole point is to hand ALL legal candidates to the search's own argmax, not pre-select one.

CAPACITY + SELECTION RULE (team-lead rider, stage-2 scoring ruling): capacity-bounded to fit
the audited 64-byte RAM allocation (ram_audit.py: $61AB-$61EA, 16 slots x 4B: target,
approach, trigger, orient). The rule when a board produces MORE than 16 candidates: **strict
scan order, first 16 kept, excess DROPPED with a counter** -- vertical columns 0..7 (orient
1 then 3) before horizontal anchors 0..6 (orient 0 then 2); within each, side c-1 before
c+1; within each side, trigger row ascending. Chosen over a depth-priority (keep-the-16-
deepest) scheme deliberately: the measured real-stream maximum is 14/decision (well under
16, see decision_dist.py's L11/L20 runs) so the rule is PROVABLY INERT on anything this
firmware will actually see in play -- it only shapes behaviour on adversarial/hill-climbed
boards, where "simple and cheap to verify" beats "clever and another thing to get wrong."
A depth-priority scheme would need an insertion/replacement comparison per candidate (real
6502 cost, real code to get right) to protect a case the lead's own measurement says never
fires. If a future measurement shows the cap DOES bind on a real stream, revisit this -- but
do not add the complexity speculatively.
"""
from __future__ import annotations

import os
import sys

CANON = os.environ.get("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
sys.path.insert(0, os.path.join(CANON, "fpga", "copro"))
from tuck_scan import ROWS, COLS, EMPTY, ref_tuck_scan          # noqa: E402

CAPACITY = 16
H, V, RH, RV = 0, 1, 2, 3          # tuck_enum.py's ring
VERT_ORIENTS = (V, RV)
HORIZ_ORIENTS = (H, RH)
# colour-cell mapping per orient, matching tuck_enum.py's _FLIP: for VERTICAL cells
# (top, bottom) = ((rest-1,target),(rest,target)); for HORIZONTAL cells
# (left, right) = ((row,target),(row,target+1)). flip=0 -> cell0 gets colour A, flip=1 ->
# cell0 gets colour B. _FLIP = (0,1,1,0) for (H,V,RH,RV).
_FLIP = {H: 0, V: 1, RH: 1, RV: 0}


def occ(board, r, c):
    return board[r * COLS + c] != EMPTY


def first_occ(board, c):
    for r in range(ROWS):
        if occ(board, r, c):
            return r
    return ROWS


def first_occ2(board, c0, c1):
    """min(first_occ(c0), first_occ(c1)) -- matches _resting()'s horizontal formula."""
    return min(first_occ(board, c0), first_occ(board, c1))


def candidate_cells(target, rest, orient):
    """(r0,c0,r1,c1) in place_at order (cell0 = left/top), matching FB/tuck_enum convention."""
    if orient in VERT_ORIENTS:
        return (rest - 1, target, rest, target)
    return (rest, target, rest, target + 1)


def ref_tuck_scan_v3(board, capacity=CAPACITY):
    """Every motion-legal tuck candidate, both geometries x both colour orients each,
    capacity-bounded by strict scan-order truncation (see module docstring).

    Returns (candidates, dropped). Each candidate: {approach, trigger, rest, target, orient}
    -- orient in {0,1,2,3} (tuck_enum ring); insertion order IS the 6502 emission order.
    """
    out = []
    dropped = 0

    def emit(approach, trigger, rest, target, orients):
        nonlocal dropped
        for orient in orients:
            if len(out) >= capacity:
                dropped += 1
                continue
            out.append({"approach": approach, "trigger": trigger, "rest": rest,
                        "target": target, "orient": orient})

    # ---- VERTICAL geometry: TWO-CELL LEGAL (not v1's single-cell approximation) ----
    # v1's tuck_scan checks only the BOTTOM cell at entry and never re-checks the TOP cell
    # at the FINAL rest row -- tolerable there because tuck_scan only STEERS the driver,
    # and real NES gravity (not tuck_scan) determines the actual landing, so an
    # over-optimistic descriptor just steers imperfectly (the D3-adjacent risk root-action
    # already accepts). Root-action's land_place_at WRITES cells directly in software --
    # an illegal 2-cell placement here doesn't steer imperfectly, it CORRUPTS the scored
    # board (silently overwriting whatever was actually in the unverified cell). Ported
    # from tuck_validation/gate_fire_rate.py's already-validated `tuck_vertical(two_cell=
    # True)`, which documents exactly this: "This bites exactly when rf == r -- a pocket
    # one cell deep, where the cell above the rest position is the lip itself. Such
    # pockets are reachable by the single-cell model and NOT by a real vertical capsule."
    for c in range(COLS):
        fc = first_occ(board, c)
        if fc == 0:
            continue
        sd = fc - 1
        for a in (c - 1, c + 1):
            if not (0 <= a < COLS):
                continue
            fa = first_occ(board, a)
            if fa == 0:
                continue
            ra = fa - 1
            for r in range(fc, ra + 1):
                if occ(board, r, c):
                    continue
                if r - 1 < 0 or occ(board, r - 1, c):
                    continue                              # TOP cell can't enter here
                rf = r
                while rf + 1 < ROWS and not occ(board, rf + 1, c):
                    rf += 1
                if rf <= sd:
                    continue
                if rf - 1 < 0 or occ(board, rf - 1, c):
                    continue                              # TOP cell has no room AT REST
                emit(a, r, rf, c, VERT_ORIENTS)

    # ---- HORIZONTAL geometry: target anchor c occupies (c,c+1), x2 colour orients ----
    for c in range(COLS - 1):                 # anchor 0..6 so c+1 stays in bounds
        fc = first_occ2(board, c, c + 1)
        if fc == 0:
            continue
        sd = fc - 1
        for a in (c - 1, c + 1):
            if a < 0 or a + 1 >= COLS:
                continue
            fa = first_occ2(board, a, a + 1)
            if fa == 0:
                continue
            ra = fa - 1
            for r in range(fc, ra + 1):
                if occ(board, r, c) or occ(board, r, c + 1):
                    continue
                rf = r
                while rf + 1 < ROWS and not occ(board, rf + 1, c) and not occ(board, rf + 1, c + 1):
                    rf += 1
                if rf > sd:
                    emit(a, r, rf, c, HORIZ_ORIENTS)

    return out, dropped


# ============================================================================ self-test
def _cave_horizontal_board():
    """A lip over columns 4-6 at row 9 (like tuck_enum's _cave_board but shaped so the
    rescue is HORIZONTAL, not vertical): the only way under is a horizontal pill sliding
    in from column 3 (open) into columns 4-5, or from column 7 into columns 5-6."""
    b = [EMPTY] * (ROWS * COLS)
    for c in (4, 5, 6):
        b[9 * COLS + c] = 1
    for c in range(COLS):
        b[11 * COLS + c] = 2
        for r in (12, 13, 14, 15):
            b[r * COLS + c] = 3
    return b


def _selftest():
    fail = []

    # (1) v1 parity on the ORIGINAL golden boards: v3's vertical candidates must contain
    # v1's single answer AT BOTH colour orients (same cells, either colour assignment).
    # Boards copied from tuck_regression.py's GOLDEN (not imported -- that file is a
    # SCRIPT, not a library; importing it runs its entire suite incl. its own sys.exit(0)).
    def _blank():
        return [EMPTY] * (ROWS * COLS)

    def _mark(b, r, c):
        b[r * COLS + c] = 1

    def _board_overhang_c0():
        b = _blank(); _mark(b, 8, 0); return b

    def _board_overhang_c7():
        b = _blank(); _mark(b, 8, 7); return b

    def _board_pocket():
        b = _blank(); _mark(b, 9, 3); _mark(b, 11, 3)
        for r in range(12, ROWS):
            for c in range(COLS):
                _mark(b, r, c)
        return b

    def _board_misland():
        b = _blank(); _mark(b, 2, 0); _mark(b, 8, 1); return b

    def _board_worstcase():
        b = _blank()
        for c in (0, 2, 4, 6):
            _mark(b, 1, c)
        return b

    LOCAL_GOLDEN = [
        ("left-edge target (col 0)", _board_overhang_c0()),
        ("right-edge target (col 7)", _board_overhang_c7()),
        ("single-cell pocket", _board_pocket()),
        ("MIS-LAND REPRO", _board_misland()),
        ("worst-case latency board", _board_worstcase()),
    ]
    def v1_target_col(board, approach, trigger):
        """Re-derive the TARGET column paired with v1's (approach, trigger) answer --
        ref_tuck_scan's return tuple doesn't carry it (single-descriptor, no target field).
        Single-cell scan, matching v1's OWN (unfixed) logic exactly, so it recovers
        whichever target column v1's global deepest-wins search actually picked."""
        best = None
        for c in range(COLS):
            fc = first_occ(board, c)
            if fc == 0:
                continue
            sd = fc - 1
            for a in (c - 1, c + 1):
                if not (0 <= a < COLS) or a != approach:
                    continue
                fa = first_occ(board, a)
                if fa == 0:
                    continue
                if not (fc <= trigger <= fa - 1) or occ(board, trigger, c):
                    continue
                rf = trigger
                while rf + 1 < ROWS and not occ(board, rf + 1, c):
                    rf += 1
                if rf > sd and (best is None or rf > best[0]):
                    best = (rf, c)
        return None if best is None else best[1]

    print("(1) v1 PARITY -- v3 must contain v1's answer ONLY where it is TWO-CELL LEGAL")
    print("    (v1 is a single-cell steering heuristic tolerated because real gravity")
    print("    settles the actual landing; v3's land_place_at writes cells directly, so")
    print("    a single-cell-only 'pocket exactly 1 deep' answer -- like MIS-LAND REPRO's")
    print("    -- is CORRECTLY excluded from v3, not a bug. See gate_fire_rate.py's")
    print("    tuck_vertical(two_cell=True) for the prior art this mirrors.)")
    n_checked = n_found = n_correctly_excluded = 0
    for name, board in LOCAL_GOLDEN:
        v1 = ref_tuck_scan(board)
        if v1 == (0xFF, 0xFF):
            continue
        n_checked += 1
        approach, trigger = v1
        target = v1_target_col(board, approach, trigger)
        v3, dropped = ref_tuck_scan_v3(board)
        hits = [c for c in v3 if c["orient"] in VERT_ORIENTS and c["approach"] == approach
                and c["trigger"] == trigger]
        if hits:
            n_found += 1
            status = "FOUND (expected)"
        else:
            top_blocked = (target is None or trigger - 1 < 0
                          or occ(board, trigger - 1, target))
            if top_blocked:
                n_correctly_excluded += 1
                status = "excluded (top cell blocked at trigger -- correct divergence)"
            else:
                fail.append(f"v1-parity:{name}")
                status = "MISSING (unexplained -- investigate)"
        print(f"    {name:<30} v1={v1} target={target}  v3: {status}  "
              f"({len(v3)} v3 candidates, {dropped} dropped)")
    print(f"    {n_found} found / {n_correctly_excluded} correctly excluded / "
          f"{n_checked} checked")

    # (1b) POSITIVE case: a pocket 2+ cells deep, where a real 2-cell vertical capsule DOES
    # fit -- confirms the fix correctly INCLUDES legitimate candidates, not just excludes
    # illegitimate ones (1a above only ever showed exclusions, since all 5 hand-built
    # goldens happen to be exactly 1-deep by design).
    print("\n(1b) POSITIVE CASE -- a pocket 2 cells deep (a real vertical capsule fits)")
    b2 = [EMPTY] * (ROWS * COLS)
    b2[6 * COLS + 0] = 1                       # overhang at row 6, column 0
    for r in range(9, ROWS):
        b2[r * COLS + 0] = 2                   # floor starts at row 9 -> rows 7,8 are open
    v3b, _ = ref_tuck_scan_v3(b2)
    two_deep = [c for c in v3b if c["orient"] in VERT_ORIENTS and c["target"] == 0
               and c["rest"] == 8]
    print(f"    {len(two_deep)} candidate(s) found resting at row 8 (2-deep pocket, "
          f"top cell would sit at row 7, both empty on the parent board)")
    if not two_deep:
        fail.append("two-cell-positive-case-missing")

    # (2) horizontal rescue: the cave-horizontal board must produce >=1 HORIZONTAL-geometry
    # candidate (either colour orient) reaching under the lip (rest row 10).
    print("\n(2) HORIZONTAL RESCUE -- a lip only a horizontal pill can slide under")
    hb = _cave_horizontal_board()
    v3, dropped = ref_tuck_scan_v3(hb)
    horiz = [c for c in v3 if c["orient"] in HORIZ_ORIENTS and c["rest"] == 10]
    print(f"    {len(v3)} total candidates ({dropped} dropped); "
          f"{len(horiz)} horizontal-geometry candidates resting at row 10 (under the lip)")
    for c in horiz:
        print(f"      target={c['target']} approach={c['approach']} trigger={c['trigger']} "
              f"orient={c['orient']}")
    ok2 = len(horiz) >= 1
    if not ok2:
        fail.append("horizontal-rescue-missing")

    # (3) invariants on a batch of random boards: every emitted candidate's cells must be
    # in-bounds, empty on the parent board, and its orientation-appropriate support check
    # must hold (same invariant class tuck_enum.py's _check_invariants uses).
    print("\n(3) INVARIANTS on 300 random boards (bounds / emptiness / support)")
    import random
    rnd = random.Random(20260802)
    bad = 0
    total_cands = 0
    for _ in range(300):
        b = [EMPTY] * (ROWS * COLS)
        for c in range(COLS):
            h = rnd.randrange(0, ROWS + 1)
            for r in range(ROWS - h, ROWS):
                b[r * COLS + c] = rnd.randint(1, 3)
        for _ in range(rnd.randrange(0, 16)):
            b[rnd.randrange(1, ROWS) * COLS + rnd.randrange(0, COLS)] = EMPTY
        v3, _ = ref_tuck_scan_v3(b)
        for cand in v3:
            total_cands += 1
            r0, c0, r1, c1 = candidate_cells(cand["target"], cand["rest"], cand["orient"])
            support_ok = (max(r0, r1) == ROWS - 1)
            for (rr, cc) in ((r0, c0), (r1, c1)):
                if not (0 <= rr < ROWS and 0 <= cc < COLS) or occ(b, rr, cc):
                    bad += 1
            if not support_ok:
                if cand["orient"] in VERT_ORIENTS:
                    support_ok = occ(b, r1 + 1, c1) if r1 + 1 < ROWS else True
                else:
                    support_ok = ((occ(b, r0 + 1, c0) or occ(b, r1 + 1, c1))
                                  if r0 + 1 < ROWS else True)
            if not support_ok:
                bad += 1
    print(f"    {total_cands} candidates across 300 boards, {bad} invariant violations "
          f"(must be 0)")
    if bad:
        fail.append("invariants")

    # (4) colour-orient doubling sanity: every geometric rest position should appear
    # exactly TWICE (once per colour orient) unless truncated by capacity.
    print("\n(4) COLOUR-ORIENT DOUBLING -- each geometric candidate appears at both orients")
    from collections import Counter
    dbl_bad = 0
    for _ in range(50):
        b = [EMPTY] * (ROWS * COLS)
        for c in range(COLS):
            h = rnd.randrange(0, ROWS + 1)
            for r in range(ROWS - h, ROWS):
                b[r * COLS + c] = rnd.randint(1, 3)
        v3, dropped = ref_tuck_scan_v3(b, capacity=64)   # generous cap so doubling isn't hidden
        geo = Counter((c["approach"], c["trigger"], c["rest"], c["target"],
                      c["orient"] in VERT_ORIENTS) for c in v3)
        if any(n != 2 for n in geo.values()):
            dbl_bad += 1
    print(f"    {dbl_bad}/50 boards with an unpaired geometric candidate (must be 0)")
    if dbl_bad:
        fail.append("colour-doubling")

    print("\n" + "=" * 70)
    print("SELF-TEST " + ("PASS" if not fail else "FAIL: " + ", ".join(fail)))
    return not fail


if __name__ == "__main__":
    ok = _selftest()
    sys.exit(0 if ok else 1)
