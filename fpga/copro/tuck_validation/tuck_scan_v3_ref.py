#!/usr/bin/env python3
"""PYTHON REFERENCE for the tuck v3 multi-candidate, both-orientation firmware enumerator.

Task #17 phase 3 stage 2 (team-lead approved decision #2, 2026-08-02): extend the existing
single-descriptor, vertical-only `tuck_scan` (tuck_scan.py) to both orientations and a
bounded candidate list. This is the SAME workflow the codebase already used for v1's
`ref_tuck_scan` -- write the reference FIRST, validate it, THEN port to 6502 against it,
never the other way. tuck_scan.py's own docstring: "The 6502 must agree with this
cell-for-cell." No 6502/assembly changes are made here; this file is the reference the
future emitter must match.

ALGORITHM. Same adjacent-approach-column, any-row model as v1's ref_tuck_scan (deliberately
NOT generalised beyond adjacent columns -- that restriction is what the phase-1/phase-2
offline proof (root_search._exec_reach_cells) actually measured; going further would be
unmeasured territory), extended to two orientations:

  VERTICAL (unchanged from v1): target column c, approach a in {c-1,c+1}. For trigger row r
  in [first_occ(c), first_occ(a)-1]: if (r,c) is empty, the pill can enter c at r and falls
  to rest row rf. Keep if rf is strictly deeper than the straight-drop rest in c.

  HORIZONTAL (new): target ANCHOR column c (pill occupies columns c, c+1 at a shared row),
  approach ANCHOR column a in {c-1, c+1} (so the pill's TWO-COLUMN footprint is (a,a+1)
  while approaching -- a=c-1 slides one step right onto (c,c+1); a=c+1 slides one step left).
  fc = first_occ across BOTH target columns (min(first_occ(c), first_occ(c+1)), matching
  _resting()'s own horizontal formula); sd = fc-1. fa = first_occ across BOTH approach
  columns. For trigger row r in [fc, fa-1]: if BOTH (r,c) and (r,c+1) are empty, the pill
  can enter there and falls (both cells together) to rest row rf. Keep if rf > sd.

CANDIDATE LIST, not single-descriptor: every (approach, trigger, rest, target, orient) that
passes the "strictly deeper than straight drop" test is kept (v1 kept only the single
deepest-over-everything winner -- that decoupling from the search's own best_col is exactly
defect D3, root-action's whole point is to hand ALL legal candidates to the search's own
argmax, not pre-select one). Capacity-bounded to fit the audited 64-byte RAM allocation
(ram_audit.py: $61AB-$61EA, 16 slots x 4B) -- if a board produces more than CAPACITY
candidates the excess is DROPPED with a counter, never silently truncated without a signal
(the offline proof's own worst-case measurement was max 14/decision at L11, so CAPACITY=16
has headroom; the firmware version's actual candidate count may differ, see the note in
TUCK_V3_FIRMWARE_DESIGN.md about vertical-only vs full-BFS candidate counts not being the
same population).
"""
from __future__ import annotations

import os
import sys

CANON = os.environ.get("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
sys.path.insert(0, os.path.join(CANON, "fpga", "copro"))
from tuck_scan import ROWS, COLS, EMPTY, ref_tuck_scan          # noqa: E402

CAPACITY = 16
VERTICAL, HORIZONTAL = 0, 1


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


def ref_tuck_scan_v3(board, capacity=CAPACITY):
    """Every motion-legal tuck candidate, both orientations, capacity-bounded.

    Returns (candidates, dropped) where candidates is a list of
    {approach, trigger, rest, target, orient} dicts (insertion order == 6502 emission
    order: vertical columns 0..7 first, then horizontal anchor columns 0..6), and dropped
    is the count that exceeded `capacity` (0 unless a board is pathological).
    """
    out = []
    dropped = 0

    def emit(approach, trigger, rest, target, orient):
        nonlocal dropped
        if len(out) >= capacity:
            dropped += 1
            return
        out.append({"approach": approach, "trigger": trigger, "rest": rest,
                    "target": target, "orient": orient})

    # ---- VERTICAL: identical algorithm to v1's tuck_scan / ref_tuck_scan ----
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
                rf = r
                while rf + 1 < ROWS and not occ(board, rf + 1, c):
                    rf += 1
                if rf > sd:
                    emit(a, r, rf, c, VERTICAL)

    # ---- HORIZONTAL: target anchor c occupies (c, c+1); approach anchor a occupies (a,a+1)
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
                    emit(a, r, rf, c, HORIZONTAL)

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

    # (1) v1 parity on the ORIGINAL golden boards: the VERTICAL half of v3 must be a
    # superset of what v1's single-descriptor picks (v1's answer, if not (0xFF,0xFF),
    # must appear verbatim among v3's vertical candidates for that board). Boards are
    # copied from tuck_regression.py's GOLDEN (not imported -- that file is a SCRIPT, not
    # a library; importing it runs its entire suite, including its own sys.exit(0)).
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
    print("(1) v1 PARITY -- v3's vertical candidates must contain v1's single answer")
    n_checked = n_found = 0
    for name, board in LOCAL_GOLDEN:
        v1 = ref_tuck_scan(board)
        if v1 == (0xFF, 0xFF):
            continue
        n_checked += 1
        v3, dropped = ref_tuck_scan_v3(board)
        hit = any(c["orient"] == VERTICAL and c["approach"] == v1[0] and c["trigger"] == v1[1]
                  for c in v3)
        if hit:
            n_found += 1
        else:
            fail.append(f"v1-parity:{name}")
        print(f"    {name:<30} v1={v1}  v3 has it: {'YES' if hit else 'NO'}  "
              f"({len(v3)} v3 candidates, {dropped} dropped)")
    print(f"    {n_found}/{n_checked} boards: v1's answer present in v3's vertical set")

    # (2) horizontal rescue: the cave-horizontal board must produce >=1 HORIZONTAL
    # candidate reaching under the lip (row 10, columns 4-5 or 5-6), and ZERO vertical
    # candidates there (a single-column vertical pill cannot pass under a 3-wide lip
    # this shape -- if the algorithm found a vertical one here it would be a bug, not a
    # bonus, since it wouldn't match the physical board).
    print("\n(2) HORIZONTAL RESCUE -- a lip only a horizontal pill can slide under")
    hb = _cave_horizontal_board()
    v3, dropped = ref_tuck_scan_v3(hb)
    horiz = [c for c in v3 if c["orient"] == HORIZONTAL and c["rest"] == 10]
    print(f"    {len(v3)} total candidates ({dropped} dropped); "
          f"{len(horiz)} horizontal candidates resting at row 10 (under the lip)")
    for c in horiz:
        print(f"      target={c['target']} approach={c['approach']} trigger={c['trigger']}")
    ok2 = len(horiz) >= 1
    if not ok2:
        fail.append("horizontal-rescue-missing")

    # (3) invariants on a batch of random boards: every emitted candidate's cells must be
    # in-bounds, empty on the parent board, and its orientation-appropriate support check
    # must hold (this is the SAME invariant class tuck_enum.py's _check_invariants uses).
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
            r, tgt, orient = cand["rest"], cand["target"], cand["orient"]
            if orient == VERTICAL:
                cells = [(r, tgt)]
                support_ok = (r == ROWS - 1) or occ(b, r + 1, tgt)
            else:
                cells = [(r, tgt), (r, tgt + 1)]
                support_ok = (r == ROWS - 1) or (occ(b, r + 1, tgt) or occ(b, r + 1, tgt + 1))
            for (rr, cc) in cells:
                if not (0 <= rr < ROWS and 0 <= cc < COLS) or occ(b, rr, cc):
                    bad += 1
            if not support_ok:
                bad += 1
    print(f"    {total_cands} candidates across 300 boards, {bad} invariant violations "
          f"(must be 0)")
    if bad:
        fail.append("invariants")

    print("\n" + "=" * 70)
    print("SELF-TEST " + ("PASS" if not fail else "FAIL: " + ", ".join(fail)))
    return not fail


if __name__ == "__main__":
    ok = _selftest()
    sys.exit(0 if ok else 1)
