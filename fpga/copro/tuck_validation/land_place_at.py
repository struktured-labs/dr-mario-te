#!/usr/bin/env python3
"""land_place_at: place a tuck candidate's TWO ALREADY-RESOLVED cells directly, no
first-occ walk, no orientation-based colour swap -- the enumerator (tuck_scan_v3) and its
caller have already done that work (candidate_cells() + the FLIP colour mapping in
tuck_scan_v3_ref.py). Companion to `land_place` (primitives.py / test_landplace.py),
which this does NOT replace -- base (straight-drop) ply-1 candidates still use the real
land_place via the RTL NODE path; land_place_at exists ONLY for the software-scored tuck
path (team-lead's Option B ruling, full depth-3 via slot-0 injection).

CONTRACT (mirrors land_place's, primitives.py:38 Z_OFFA/Z_OFFB, land_place's own
"ORA_imm 0x40" tile convention -- test_landplace.py:1-4):
  inputs (zp):  LA_OFFA, LA_OFFB   cell offsets 0-127 (row*8+col, cell0/cell1 already in
                                   place_at order -- top/left = cell0)
                LA_CA, LA_CB       raw colours 0-2 for cell0/cell1 (NOT yet OR'd with 0x40
                                   -- land_place_at does that, matching land_place)
  writes:       BOARD[offA] = colourA | 0x40 ; BOARD[offB] = colourB | 0x40
                Z_OFFA <- offA ; Z_OFFB <- offB   (so resolve_capped's find_clears_targeted
                consumes the SAME input it always does, unmodified)
  clobbers:     A, X. No legality check -- the caller (the scoring loop, once wired) must
                only call this for a candidate the enumerator already proved two-cell-legal
                (tuck_scan_v3's own vertical/horizontal legality gates). This is deliberate,
                not a shortcut: re-deriving legality here would duplicate logic the
                enumerator already owns and risk the two copies drifting (the exact class of
                bug the value-equivalence differential gate exists to catch on the SCORING
                side; legality itself is the enumerator's gate, tested in
                test_tuck_scan_v3.py).

ZERO-PAGE REUSE (deliberate, not accidental): LA_OFFA/LA_OFFB/LA_CA/LA_CB reuse
land_place's OWN input bytes (P_O/P_C/P_CA/P_CB at 0xE2-0xE5, test_landplace.py). Safe
because land_place and land_place_at are NEVER live at the same moment -- a given ply-1
candidate is scored via EITHER the real NODE path (base actions, which may separately
invoke land_place for eh_terms) OR land_place_at (tuck candidates), never both in the same
call. Costs zero new zero-page bytes. (0xE6, used internally by land_place's own
horizontal-branch first_occ scratch, is NOT touched by land_place_at -- it needs no
scratch of its own.)
"""
from __future__ import annotations

# reuse land_place's own zp input bytes (test_landplace.py: P_O,P_C,P_CA,P_CB = 0xE2-0xE5)
LA_OFFA, LA_OFFB, LA_CA, LA_CB = 0xE2, 0xE3, 0xE4, 0xE5
Z_OFFA, Z_OFFB = 0xDC, 0xDE            # primitives.py's dedicated placed-cell offsets


def emit_land_place_at(a, board=0x0700):
    """`board` defaults to CUR ($0700) -- the search's per-node working board, matching
    how test_search_d3.py rebinds primitives.LIVE_BOARD/BOARD for the engine build."""
    a.label("land_place_at")
    a.ins("LDA_zp", LA_CA); a.ins("ORA_imm", 0x40)
    a.ins("LDX_zp", LA_OFFA); a.ins16("STA_absX", board)
    a.ins("LDA_zp", LA_CB); a.ins("ORA_imm", 0x40)
    a.ins("LDX_zp", LA_OFFB); a.ins16("STA_absX", board)
    a.ins("LDA_zp", LA_OFFA); a.ins("STA_zp", Z_OFFA)
    a.ins("LDA_zp", LA_OFFB); a.ins("STA_zp", Z_OFFB)
    a.ins("RTS")


def cell_offsets(target, rest, orient):
    """Python mirror (for the differential test) of the offset arithmetic a caller must
    do before calling land_place_at -- matches tuck_scan_v3_ref.candidate_cells() exactly,
    expressed as flat 0-127 offsets instead of (row,col) pairs."""
    H, V, RH, RV = 0, 1, 2, 3
    if orient in (V, RV):
        return (rest - 1) * 8 + target, rest * 8 + target
    return rest * 8 + target, rest * 8 + target + 1
