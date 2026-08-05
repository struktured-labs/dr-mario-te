#!/usr/bin/env python3
"""Translatability predicate for the #17-unified reachable-root reconciliation rig.

WHY THIS EXISTS. reach_root.py's reachfull/reachfull2 arms score every BFS-reachable
tuck-class candidate (tuck_enum.py, mode="free") as if it were unconditionally
executable. It isn't: the real firmware only fires a tuck by publishing a single-
adjacent-column (approach, trigger) descriptor to the driver's steering mailbox
(TUCK_COL/TUCK_ROW) via tuck_v3.py's CANDLIST -- and dr-mario-canonical-wt's
tuck-bfs-6502 branch measured that only ~11% of BFS-reachable tuck candidates HAVE such
a descriptor (median 2 of 36 raw candidates/board survive; see TUCK_BFS_PORT_REPORT.md
section 8.1). This module exposes that same accept/reject boundary to this rig so
reconciliation can score the REAL executable set, not the full reachable one.

EXECUTABLE SET, the composition rule the rig arm should use:

    executable_set = straight_drops UNION {tuck-class candidates : translatable}

Straight drops (the base-32 (variant, col) family `fast_sim_x._expand_core` enumerates)
bypass CANDLIST entirely -- they are the search's native action space and are always
directly executable, independent of anything in this module. The translatability
predicate below is a gate ONLY for tuck-class candidates (`is_tuck=True` in tuck_enum.py's
own dicts, i.e. TE.enumerate(...)'s "reachfull"-style output already used throughout
reach_root.py). `is_straight_drop()`/`executable()` below encode this split explicitly so
callers don't have to re-derive it.

WRAPS, does not re-derive: dr-mario-canonical-wt/tests/translate_ref.py's already-
validated CANDLIST derivation (0/732 mismatches vs tuck_scan_v3_ref.py's own uncapped
rule on 400 random boards; the ACTUAL 6502 firmware chain matched this reference exactly
on 50/50 real L11 corpus boards -- see TUCK_BFS_PORT_REPORT.md section 8.2/8.4 on that
branch). Only the board representation differs at the boundary and is converted once,
at the top of is_translatable() -- nothing in translate_ref.py's logic is touched, copied,
or reimplemented here.

BOARD/CANDIDATE CONVENTIONS. This module speaks reach_root.py's own house conventions
(its module docstring, verified there, not re-verified here): `col` is a row-major
NCELL=128 int8 array (or any 128-length sequence), idx = r*8+c, colours 1-based, 0=empty.
Candidates are tuck_enum.py-style dicts (or bare (col, row, orient) tuples) carrying at
least 'col' (target column), 'row' (rest row), 'orient' (0=H,1=V,2=RH,3=RV) -- exactly
what `TE.enumerate(fb, ca, cb, mode="free")` and reach_root.py's own `tuck_cands` lists
already produce, so callers pass those dicts straight through without reshaping them.

translate_ref.py's OWN convention (matching primitives.py / the real 6502 firmware's
NES-tile board representation) uses EMPTY=0xFF as the empty-cell sentinel instead of 0.
`_to_nes_board()` is the one-line adapter; the colour VALUE written for occupied cells
doesn't matter to the derivation (only empty/non-empty is ever tested), so passing the
1-based colour straight through as the "tile byte" is correct -- the same convention
tuck_bfs_6502.py's own test harnesses use (fb_to_nes()).
"""
from __future__ import annotations

import sys
import os

CANON = "/home/struktured/projects/dr-mario-canonical-wt"
_TESTS = os.path.join(CANON, "tests")
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)
import translate_ref as TR  # noqa: E402  -- the validated derivation; wrapped, not re-derived

EMPTY_NES = 0xFF
ROWS, COLS, NCELL = 16, 8, 128


def _to_nes_board(col):
    """reach_root.py convention (0=empty, 1..3=colour) -> translate_ref.py convention
    (EMPTY=0xFF sentinel, occupied=colour byte). Accepts a numpy int8 array or any
    128-length sequence; always returns a plain list of Python ints (translate_ref.py's
    own functions index it with plain int arithmetic, no numpy dependency)."""
    return [EMPTY_NES if int(c) == 0 else int(c) for c in col]


def _unpack(candidate):
    """candidate -> (target, rest, orient) as plain ints. Accepts a tuck_enum.py-style
    dict ('col'/'row'/'orient' keys) or a bare (col, row, orient) tuple/list."""
    if isinstance(candidate, dict):
        return int(candidate["col"]), int(candidate["row"]), int(candidate["orient"])
    target, rest, orient = candidate
    return int(target), int(rest), int(orient)


def is_straight_drop(candidate):
    """True iff `candidate` is a base-32 (variant, col) straight drop rather than a
    tuck-class placement -- i.e. it bypasses CANDLIST entirely and is always executable
    without consulting is_translatable() at all. Recognises reach_root.py's own two
    candidate shapes: a `{"kind": "base"/"tuck", ...}` root-choice dict (choose_base32/
    choose_reachfull's return value) or a raw tuck_enum.py placement dict (`is_tuck`
    key, as found in TE.enumerate()'s output / reach_root.py's own `tuck_cands` lists)."""
    if isinstance(candidate, dict):
        if "kind" in candidate:
            return candidate["kind"] == "base"
        if "is_tuck" in candidate:
            return not candidate["is_tuck"]
    raise ValueError(f"is_straight_drop: unrecognised candidate shape {candidate!r}")


def precompute_visited(col):
    """Precompute the BFS visited plane for a board once, to pass into repeated
    is_translatable()/executable() calls across many candidates on that SAME board --
    the visited-plane computation (translate_ref.row_bfs_visited) is the dominant cost
    per call and does not depend on the candidate, only the board."""
    return TR.row_bfs_visited(_to_nes_board(col))


def is_translatable(col, candidate, visited=None):
    """True iff `candidate` (a tuck-class placement -- see module docstring for the
    accepted shapes) would survive the real 6502 CANDLIST translation: a valid,
    BFS-visited-verified single-adjacent-column (approach, trigger) descriptor exists
    for it in tuck_scan_v3's motion vocabulary. Only meaningful for tuck-class
    candidates; straight drops don't need this gate (see is_straight_drop/executable).

    `visited`: optional, from precompute_visited(col) -- pass it when checking many
    candidates on the same board to skip recomputing the visited plane each call."""
    target, rest, orient = _unpack(candidate)
    board = _to_nes_board(col)
    if visited is None:
        visited = TR.row_bfs_visited(board)
    return TR.derive_verified(board, target, rest, orient, visited) is not None


def executable(col, candidate, visited=None):
    """The rig arm's composition rule, as a per-candidate predicate:
    executable_set = straight_drops UNION {tucks : translatable}.
    A candidate is executable iff it's a base-32 straight drop (always executable) OR
    it's a tuck-class candidate with a verified CANDLIST descriptor."""
    if is_straight_drop(candidate):
        return True
    return is_translatable(col, candidate, visited=visited)
