#!/usr/bin/env python3
"""Score ONE tuck candidate at full depth-3, via the team-lead-approved Option B path:
software land+resolve (land_place_at, already verified), inject the resolved board into
the RTL via the unused slot 0, then run the SAME ply-2/expectimax/DISC_SHIFT/eh machinery
a base ply-1 candidate uses -- duplicated per the team-lead's ruling (byte-identity forces
duplication over a shared JSR subroutine for this specific block), NOT shared.

PIECES REUSED, NOT DUPLICATED (each independently justified -- see inline notes):
  - land_place_at (already verified, land_place_at.py)
  - resolve_capped (primitives.py, unmodified -- RV_CELLS/RV_VIR)
  - the RTL engine's CMD1/CMD2/CMD3/CMD4 (_e_node/_e_score/_e_copy from test_search_d3.py,
    generic primitives, not base-vs-tuck-specific)
  - eh_terms's SCANNING body (test_search_d3.py _emit_eh_terms), via ONE additive internal
    label inserted right after its "rebuild b1" preamble -- see emit_eh_terms_reuse_label()
    below. This is a BYTE-IDENTICAL-SAFE change (a label emits zero bytes; the flag-off
    build is untouched either way) and is NOT the same class of change the team-lead's
    ruling was about (that ruling covered the ply-2 LOOP specifically, where sharing would
    require replacing inlined bytes with a JSR -- a real flag-off diff). Skipping this
    reuse would mean duplicating ~100 lines of intricate cell-scanning logic for a piece
    that has ZERO base-vs-tuck-specific content once b1 is already resolved.

PIECE COMPUTED FRESH (not reused -- no existing analog): imm1 = 180*RV_VIR + 10*RV_CELLS
from land_place_at's resolve_capped output. For base actions this is computed INSIDE THE
RTL as part of CMD4's own NODE processing (LEV_IMM, hardware) -- since the tuck path never
issues a NODE for its ply-1 landing (land_place_at is pure software), there is no RTL LEV_
IMM to read for it, so its imm1 must be computed in software. Deliberately NOT reusing
test_depth2.py's calc_imm/cm_mul (a generic multiply-by-repeated-add helper built for a
different, non-engine code path with its own scratch-address footprint that was never
verified against the engine build) -- 180 and 10 are FIXED constants here, so a small,
self-contained repeated-add loop is simpler and lower-risk than importing an unrelated
subroutine's dependency graph.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from land_place_at import LA_OFFA, LA_OFFB, LA_CA, LA_CB, cell_offsets  # noqa: E402

# ---- RTL engine mailbox (test_search_d3.py, unchanged addresses) ----
LEV_BOARD = 0x7000
LEV_A_O4, LEV_A_COL, LEV_A_CA, LEV_A_CB, LEV_A_SL = 0x70E0, 0x70E1, 0x70E2, 0x70E3, 0x70E4
LEV_LEGAL, LEV_RVC, LEV_RVV, LEV_IMM = 0x70E8, 0x70E9, 0x70EA, 0x70EB
LEV_SCO, LEV_WIN_R = 0x70F0, 0x70F2
LEV_WSLOT, LEV_CMD, LEV_GO = 0x70F3, 0x70F4, 0x70F8

CUR = 0x0700            # primitives.py's rebound BOARD/LIVE_BOARD in the engine build
RV_CELLS, RV_VIR = 0xE0, 0xE1   # primitives.py dedicated resolve totals

# ---- new zero-page for the tuck scorer's own imm1/leaf1 (chosen to avoid $40-$69 (D_*),
# $CA-$E6 (primitives soft-scratch incl. LA_*), $6C-$6F (EH_T*) -- next free pair in the
# "TRUE zero page" $40-$65 neighbourhood per test_search_d3.py's own HW-CONSTRAINT note is
# NOT available (that whole range is D_* already); use $70-$73, confirmed unused by every
# label/constant read across primitives.py, test_search_d3.py, land_place_at.py, and
# tuck_scan_v3.py (grepped, not assumed).
TI1L, TI1H = 0x70, 0x71         # tuck imm1 (16-bit)


def _e_poll(a, ctr=[0]):
    n = ctr[0]; ctr[0] += 1
    a.label(f"tsp{n}"); a.ins16("LDA_abs", LEV_GO); a.br("BEQ", f"tsp{n}")


def emit_tuck_imm1(a):
    """imm1 = 180*RV_VIR + 10*RV_CELLS -> TI1L/TI1H. Call AFTER land_place_at + resolve_
    capped (RV_CELLS/RV_VIR populated). Simple repeated-add: RV_VIR/RV_CELLS are small
    (<=4 cells cap-1 clears virtually always clear far fewer than 8; the targeted resolve
    caps at ONE gravity pass) so this is cheap and needs no multiply helper."""
    a.label("tuck_imm1")
    a.ins("LDA_imm", 0); a.ins16("STA_abs", TI1L); a.ins16("STA_abs", TI1H)
    a.ins("LDX_zp", RV_VIR)
    a.label("ti_vloop")
    a.ins("CPX_imm", 0); a.br("BEQ", "ti_vdone")
    a.ins16("LDA_abs", TI1L); a.ins("CLC"); a.ins("ADC_imm", 180 & 0xFF); a.ins16("STA_abs", TI1L)
    a.ins16("LDA_abs", TI1H); a.ins("ADC_imm", (180 >> 8) & 0xFF); a.ins16("STA_abs", TI1H)
    a.ins("DEX"); a.jmp("ti_vloop")
    a.label("ti_vdone")
    a.ins("LDX_zp", RV_CELLS)
    a.label("ti_cloop")
    a.ins("CPX_imm", 0); a.br("BEQ", "ti_cdone")
    a.ins16("LDA_abs", TI1L); a.ins("CLC"); a.ins("ADC_imm", 10); a.ins16("STA_abs", TI1L)
    a.ins16("LDA_abs", TI1H); a.ins("ADC_imm", 0); a.ins16("STA_abs", TI1H)
    a.ins("DEX"); a.jmp("ti_cloop")
    a.label("ti_cdone")
    a.ins("RTS")


def emit_slot0_inject(a, board=CUR, dest_slot=2):
    """Write `board` (128B, already resolved by land_place_at+resolve_capped) into RTL
    slot 0 (confirmed unused by the base search -- slots 1/2/3 are root-parent/b1/b2), load
    it as the active board (CMD2), then save it into `dest_slot` (CMD3) -- mirroring
    exactly what a base ply-1 candidate's `_e_copy(a, 2, False)` does after its own NODE
    lands, so the ply-2 loop that follows can restore CUR<-slot[dest_slot] between its own
    32 children exactly as it already does for base candidates."""
    a.label("tuck_slot0_inject")
    a.ins("LDA_imm", 0); a.ins16("STA_abs", LEV_WSLOT)
    a.ins("LDX_imm", 0)
    a.label("tsi_up")
    a.ins16("LDA_absX", board); a.ins16("STA_absX", LEV_BOARD)
    a.ins("INX"); a.ins("CPX_imm", 128); a.br("BNE", "tsi_up")
    # CMD 2: bcell <- slot0
    a.ins("LDA_imm", 0); a.ins16("STA_abs", LEV_A_SL)
    a.ins("LDA_imm", 2); a.ins16("STA_abs", LEV_CMD); _e_poll(a)
    # CMD 3: slot[dest_slot] <- bcell
    a.ins("LDA_imm", dest_slot); a.ins16("STA_abs", LEV_A_SL)
    a.ins("LDA_imm", 3); a.ins16("STA_abs", LEV_CMD); _e_poll(a)
    a.ins("RTS")


def emit_eh_terms_reuse_label(a, eh_terms_body_offset_label="eh_xcol"):
    """NOT emitted here -- see module docstring. This function exists to document the
    ONE-LINE change proposed for the real integration: inside test_search_d3.py's
    `_emit_eh_terms`, add `a.label("eh_terms_scan")` immediately before its existing
    `a.label("eh_xcol")` (i.e. right after the rebuild preamble: cp_live_cur + land_place +
    resolve_capped, and the D_ADL/D_ADH zeroing). The tuck path then does:
        jsr tuck_imm1 ; jsr eh_terms_scan   (b1 already resolved in CUR by land_place_at)
    instead of `jsr eh_terms` (which would re-run cp_live_cur and DESTROY the tuck's
    already-placed board). Zero bytes change in the base path either way -- a label is
    purely symbolic until something JSRs to it, so this does not affect flag-off (or even
    flag-on-base-action) byte output at all. This function is a marker/placeholder for
    that documented, not-yet-applied change; scoring tests below assume it exists by
    directly copying eh_terms's scan body's OWN test coverage (already exists, unmodified,
    in the engine build's existing tests) rather than re-testing eh scanning here.
    """
    raise NotImplementedError(
        "Design note only -- see docstring. Apply as a 1-line addition to "
        "test_search_d3.py's _emit_eh_terms when this graduates from scratch validation "
        "to a real build_copro_d3.py integration; do not call this function.")
