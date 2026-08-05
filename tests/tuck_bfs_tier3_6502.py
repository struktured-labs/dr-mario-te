#!/usr/bin/env python3
"""emit_tier3: 6502 port of translate_ref_tier3.py's tier-3 CANDLIST translation
(task #17, tier-3 mission, 2026-08-05).

Reuses tuck_bfs_6502.py's `tb_is_legal` and `tb_vbit` VERBATIM (both are already
plane-independent -- vbit only computes a byte/mask offset, is_legal only reads
LIVE_BOARD) and tuck_bfs_translate_6502.py's `tr_first_occ`/`tr_is_empty`/
`tr_fall_vert`/`tr_fall_horiz` VERBATIM (already generic over their TR_* inputs).
Everything else here is NEW, MODE-parameterized machinery: `mono_reach` needs TWO
64-bit-plane fixed-point closures (L-restricted, R-restricted), so rather than
fully duplicating tuck_bfs_6502.py's row_fixedpoint/down_propagate/row_step/
check_and_mark/mark_state/vis_test/vis_set_new (6 routines x 2 directions), a
single T3_MODE flag (0=building MONO_VIS_L, restrict to Left+rotate; 1=building
MONO_VIS_R, restrict to Right+rotate) is threaded through ONE shared copy of each,
called twice. Only the two routines that actually TOUCH a vis-plane byte
(t3_vis_test/t3_vis_set_new) branch on T3_MODE internally to pick MONO_VIS_L vs
MONO_VIS_R -- everything upstream of them (row_fixedpoint's loop structure,
down_propagate, the rotation-kick logic) is written once and shared.

SCRATCH REUSE (time-disjoint-phase, same convention tuck_bfs_6502.py's own
docstring already establishes for tuck_v3.py's $73-$80): mono_reach construction
runs strictly AFTER tuck_bfs's main enumeration (which no longer needs its own
scratch) and BEFORE tr_translate's per-candidate loop (whose TR_* scratch isn't
alive yet either), so this reuses tuck_bfs_6502.py's BFS_Y/BFS_S/BFS_X/BFS_O/
BFS_CHANGED/RT_TX/IL_X/IL_Y/IL_O/VB_ROWBASE/VB_S/VB_BYTEIDX/VB_MASK/CM_X/CM_Y/
CM_O/PASS_CNT verbatim instead of claiming a second copy of all of it.

MEMORY:
  RAM  MONO_VIS_L = $0F80 (64B), MONO_VIS_R = $0FC0 (64B) -- extends
       tuck_bfs_6502.py's already-validated $0E00-$0F7F claim by 128B to the end
       of that page ($0FFF); same flat-WRAM region, well above the $0800-$08FF
       hardware alias, no claim found anywhere in the checked tree at this range.
  ZP   $A9-$B3 (11B), starting immediately after tuck_bfs_translate_6502.py's
       TR_TMP2=$A8: T3_MODE, T3_D, T3_A, T3_R, T3_SD, T3_FOUND, T3_MAXA,
       T3_TARGET2 (a copy of TR_TARGET the row-scan needs while TR_A is being
       reused as the "approach under test" scratch), T3_REST2, T3_ORIENT2,
       T3_ISVERT2.

CASCADE: tr3_derive is called from tr_derive (tuck_bfs_translate_6502.py) as a
fallback ONLY when tier 1 (tr_try_vert/tr_try_horiz via td_try_and_verify) did
not find a descriptor for EITHER side -- see the DRCOPRO_TUCKBFS_TIER3-gated
wiring in build_copro_d3.py for exactly where that hook goes in. tuck_bfs_6502.py
and tuck_bfs_translate_6502.py are NOT modified by this file -- it only appends
new labels, called from a small new fallback branch inserted at the tr_derive
call site (see wiring), preserving tier 1's byte-for-byte behaviour untouched.

BUG FOUND BY THE BIT-EXACT GATE (test_tuck_bfs_tier3_6502.py), fixed before this
docstring was written: the first draft computed T3_SD as plain first_occ(target)-1
for BOTH orientations. That's correct for vertical, but horizontal needs
min(first_occ(target), first_occ(target+1))-1 -- the SAME "min of two first_occ"
rule tr_try_horiz already implements for tier 1 (and the SAME TR_TMP2-not-TR_TMP
stash tr_first_occ's own docstring warns about, since a nested call clobbers
TR_TMP). Missing it made SD far too permissive whenever the target column itself
was empty but its partner column wasn't (board 8 in the corpus: target=5 fully
empty, target+1=6 occupied from row 12 -- first_occ(target) alone gives SD=15,
silently rejecting a genuinely valid rf=11 tuck candidate on the wrong side of an
uninvolved bound). Caught by the direct-call gate diverging from the Python
reference on exactly this candidate; fixed to branch on T3_ISVERT2 the same way
_phase2_ok already does. Full corpus (1490 tuck-class candidates, 200 boards): 0
mismatches after the fix.

VALIDATED (test_tuck_bfs_tier3_6502.py): bit-exact, 0/1490 mismatches on the
200-board corpus (direct tr_derive_cascade calls vs the Python cascade), plus
0/15-board full-chain mismatches through the real tuck_bfs -> tr_translate_tier3
-> CANDLIST integration path. Assembled size: 2543 bytes combined (tuck_bfs +
translate + tier3), 171 labels -- tier3 alone adds ~1116 bytes over the tier-1-
only 1427B baseline, well past the original gut-level +150-250B estimate (two
full mono-restricted fixed-point closures plus the nearest-first search loop
turned out to cost more than a first guess at "widen the existing loop bounds"
suggested; recorded here as the measured number, not the estimate).
"""
import sys
HERE = "/home/struktured/projects/dr-mario-mods"
sys.path.insert(0, HERE + "/tests")
sys.path.insert(0, HERE)
import tuck_bfs_6502 as TB
import tuck_bfs_translate_6502 as TRB

ROWS, COLS = TB.ROWS, TB.COLS
LIVE_BOARD = TB.LIVE_BOARD
EMPTY = TB.EMPTY

MONO_VIS_L = 0x0F80
MONO_VIS_R = 0x0FC0

(T3_MODE, T3_D, T3_A, T3_R, T3_SD, T3_FOUND, T3_MAXA,
 T3_TARGET2, T3_REST2, T3_ORIENT2, T3_ISVERT2) = range(0xA9, 0xA9 + 11)


# ============================================================ mode-aware vis ===
def _emit_t3_vis_test(a):
    """t3_vis_test: inputs VB_ROWBASE/VB_S/T3_MODE -> A=1 if that bit is set in
    MONO_VIS_L (T3_MODE=0) or MONO_VIS_R (T3_MODE=1), else 0. Shares tb_vbit's
    byte/mask computation verbatim; only the final plane read branches on mode."""
    a.label("t3_vis_test")
    a.jsr("tb_vbit")
    a.ins("LDX_zp", TB.VB_BYTEIDX)
    a.ins("LDA_zp", T3_MODE)
    a.br("BEQ", "t3vt_L")
    a.ins16("LDA_absX", MONO_VIS_R)
    a.jmp("t3vt_test")
    a.label("t3vt_L")
    a.ins16("LDA_absX", MONO_VIS_L)
    a.label("t3vt_test")
    a.ins("AND_zp", TB.VB_MASK)
    a.br("BEQ", "t3vt_no")
    a.ins("LDA_imm", 1)
    a.ins("RTS")
    a.label("t3vt_no")
    a.ins("LDA_imm", 0)
    a.ins("RTS")


def _emit_t3_vis_set_new(a):
    """t3_vis_set_new: same contract as tb_vis_set_new, mode-routed."""
    a.label("t3_vis_set_new")
    a.jsr("tb_vbit")
    a.ins("LDX_zp", TB.VB_BYTEIDX)
    a.ins("LDA_zp", T3_MODE)
    a.br("BEQ", "t3vsn_Lr")
    a.ins16("LDA_absX", MONO_VIS_R)
    a.jmp("t3vsn_test")
    a.label("t3vsn_Lr")
    a.ins16("LDA_absX", MONO_VIS_L)
    a.label("t3vsn_test")
    a.ins("AND_zp", TB.VB_MASK)
    a.br("BNE", "t3vsn_already")
    a.ins("LDX_zp", TB.VB_BYTEIDX)
    a.ins("LDA_zp", T3_MODE)
    a.br("BEQ", "t3vsn_Lw")
    a.ins16("LDA_absX", MONO_VIS_R)
    a.ins("ORA_zp", TB.VB_MASK)
    a.ins16("STA_absX", MONO_VIS_R)
    a.jmp("t3vsn_wrote")
    a.label("t3vsn_Lw")
    a.ins16("LDA_absX", MONO_VIS_L)
    a.ins("ORA_zp", TB.VB_MASK)
    a.ins16("STA_absX", MONO_VIS_L)
    a.label("t3vsn_wrote")
    a.ins("LDA_imm", 1)
    a.ins("RTS")
    a.label("t3vsn_already")
    a.ins("LDA_imm", 0)
    a.ins("RTS")


def _emit_t3_mark_state(a):
    """t3_mark_state: mirrors tb_mark_state, calling t3_vis_set_new instead."""
    a.label("t3_mark_state")
    a.ins("LDA_zp", TB.CM_X)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", TB.CM_O)
    a.ins("STA_zp", TB.VB_S)
    a.ins("LDA_zp", TB.CM_Y)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("STA_zp", TB.VB_ROWBASE)
    a.jsr("t3_vis_set_new")
    a.ins("CMP_imm", 1)
    a.br("BNE", "t3ms_done")
    a.ins("LDA_imm", 1)
    a.ins("STA_zp", TB.BFS_CHANGED)
    a.label("t3ms_done")
    a.ins("RTS")


def _emit_t3_check_and_mark(a):
    """t3_check_and_mark: mirrors tb_check_and_mark, calling t3_mark_state.
    tb_is_legal is reused verbatim (plane-independent)."""
    a.label("t3_check_and_mark")
    a.ins("LDA_zp", TB.CM_X); a.ins("STA_zp", TB.IL_X)
    a.ins("LDA_zp", TB.CM_Y); a.ins("STA_zp", TB.IL_Y)
    a.ins("LDA_zp", TB.CM_O); a.ins("STA_zp", TB.IL_O)
    a.jsr("tb_is_legal")
    a.ins("PHA")
    a.ins("CMP_imm", 1)
    a.br("BNE", "t3cam_done")
    a.jsr("t3_mark_state")
    a.label("t3cam_done")
    a.ins("PLA")
    a.ins("RTS")


# ==================================================== mode-restricted row-step
def _emit_t3_rot_block(a, no):
    """One unrolled rotation attempt for the mono-restricted closure -- IDENTICAL
    geometry to tuck_bfs_6502._emit_rot_block (right-wall clamp + single left-kick,
    both direction-UNRESTRICTED: rotation is never gated by T3_MODE, only Left/
    Right lateral moves are), just calling t3_check_and_mark instead of
    tb_check_and_mark."""
    is_h_no = TB._IS_H[no]
    skip = f"t3_rot{no}_skip"
    a.ins("LDA_zp", TB.BFS_O)
    a.ins("CMP_imm", no)
    a.br("BEQ", skip)
    if is_h_no:
        notx7 = f"t3_rot{no}_notx7"
        txset = f"t3_rot{no}_txset"
        a.ins("LDA_zp", TB.BFS_X)
        a.ins("CMP_imm", 7)
        a.br("BNE", notx7)
        a.ins("LDA_imm", 6)
        a.jmp(txset)
        a.label(notx7)
        a.ins("LDA_zp", TB.BFS_X)
        a.label(txset)
    else:
        a.ins("LDA_zp", TB.BFS_X)
    a.ins("STA_zp", TB.RT_TX)
    a.ins("STA_zp", TB.CM_X)
    a.ins("LDA_zp", TB.BFS_Y); a.ins("STA_zp", TB.CM_Y)
    a.ins("LDA_imm", no); a.ins("STA_zp", TB.CM_O)
    a.jsr("t3_check_and_mark")
    a.ins("CMP_imm", 1)
    a.br("BEQ", skip)
    if is_h_no:
        a.ins("LDA_zp", TB.RT_TX)
        a.br("BEQ", skip)
        a.ins("SEC"); a.ins("SBC_imm", 1)
        a.ins("STA_zp", TB.CM_X)
        a.ins("LDA_zp", TB.BFS_Y); a.ins("STA_zp", TB.CM_Y)
        a.ins("LDA_imm", no); a.ins("STA_zp", TB.CM_O)
        a.jsr("t3_check_and_mark")
    a.label(skip)


def _emit_t3_row_step(a):
    """t3_row_step: Left is tried ONLY in T3_MODE=0 (building MONO_VIS_L), Right
    ONLY in T3_MODE=1 (MONO_VIS_R) -- this is the actual direction restriction
    mono_reach needs. Rotations are always tried, both modes (a rotation isn't a
    lateral "direction")."""
    a.label("t3_row_step")
    a.ins("LDA_zp", T3_MODE)
    a.br("BNE", "t3rs_skipleft")          # mode=1 (R-only) -> skip LEFT
    a.ins("LDA_zp", TB.BFS_X)
    a.br("BEQ", "t3rs_skipleft")
    a.ins("SEC"); a.ins("SBC_imm", 1)
    a.ins("STA_zp", TB.CM_X)
    a.ins("LDA_zp", TB.BFS_Y); a.ins("STA_zp", TB.CM_Y)
    a.ins("LDA_zp", TB.BFS_O); a.ins("STA_zp", TB.CM_O)
    a.jsr("t3_check_and_mark")
    a.label("t3rs_skipleft")
    a.ins("LDA_zp", T3_MODE)
    a.ins("CMP_imm", 1)
    a.br("BNE", "t3rs_skipright")         # mode=0 (L-only) -> skip RIGHT
    a.ins("LDA_zp", TB.BFS_X)
    a.ins("CMP_imm", 7)
    a.br("BEQ", "t3rs_skipright")
    a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("STA_zp", TB.CM_X)
    a.ins("LDA_zp", TB.BFS_Y); a.ins("STA_zp", TB.CM_Y)
    a.ins("LDA_zp", TB.BFS_O); a.ins("STA_zp", TB.CM_O)
    a.jsr("t3_check_and_mark")
    a.label("t3rs_skipright")
    for no in range(4):
        _emit_t3_rot_block(a, no)
    a.ins("RTS")


def _emit_t3_row_fixedpoint(a):
    """t3_row_fixedpoint: mirrors tb_row_fixedpoint, calling t3_vis_test/
    t3_row_step instead."""
    a.label("t3_row_fixedpoint")
    a.ins("LDA_imm", TB.ROW_PASS_CAP)
    a.ins("STA_zp", TB.PASS_CNT)
    a.label("t3rfp_pass")
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", TB.BFS_CHANGED)
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", TB.BFS_S)
    a.label("t3rfp_state")
    a.ins("LDA_zp", TB.BFS_Y)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("STA_zp", TB.VB_ROWBASE)
    a.ins("LDA_zp", TB.BFS_S)
    a.ins("STA_zp", TB.VB_S)
    a.jsr("t3_vis_test")
    a.ins("CMP_imm", 1)
    a.br("BNE", "t3rfp_next")
    a.ins("LDA_zp", TB.BFS_S)
    a.ins("LSR_A"); a.ins("LSR_A")
    a.ins("STA_zp", TB.BFS_X)
    a.ins("LDA_zp", TB.BFS_S)
    a.ins("AND_imm", 3)
    a.ins("STA_zp", TB.BFS_O)
    a.jsr("t3_row_step")
    a.label("t3rfp_next")
    a.ins("INC_zp", TB.BFS_S)
    a.ins("LDA_zp", TB.BFS_S)
    a.ins("CMP_imm", 32)
    a.br("BNE", "t3rfp_state")
    a.ins("DEC_zp", TB.PASS_CNT)
    a.ins("LDA_zp", TB.BFS_CHANGED)
    a.br("BEQ", "t3rfp_done")
    a.ins("LDA_zp", TB.PASS_CNT)
    a.br("BNE", "t3rfp_pass")
    a.label("t3rfp_done")
    a.ins("RTS")


def _emit_t3_down_propagate(a):
    """t3_down_propagate: mirrors tb_down_propagate, calling t3_vis_test/
    t3_check_and_mark instead."""
    a.label("t3_down_propagate")
    a.ins("LDA_zp", TB.BFS_Y)
    a.ins("CMP_imm", ROWS - 1)
    a.br("BEQ", "t3dp_done")
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", TB.BFS_S)
    a.label("t3dp_loop")
    a.ins("LDA_zp", TB.BFS_Y)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("STA_zp", TB.VB_ROWBASE)
    a.ins("LDA_zp", TB.BFS_S)
    a.ins("STA_zp", TB.VB_S)
    a.jsr("t3_vis_test")
    a.ins("CMP_imm", 1)
    a.br("BNE", "t3dp_next")
    a.ins("LDA_zp", TB.BFS_S)
    a.ins("LSR_A"); a.ins("LSR_A")
    a.ins("STA_zp", TB.CM_X)
    a.ins("LDA_zp", TB.BFS_Y)
    a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("STA_zp", TB.CM_Y)
    a.ins("LDA_zp", TB.BFS_S)
    a.ins("AND_imm", 3)
    a.ins("STA_zp", TB.CM_O)
    a.jsr("t3_check_and_mark")
    a.label("t3dp_next")
    a.ins("INC_zp", TB.BFS_S)
    a.ins("LDA_zp", TB.BFS_S)
    a.ins("CMP_imm", 32)
    a.br("BNE", "t3dp_loop")
    a.label("t3dp_done")
    a.ins("RTS")


def _emit_t3_mono_reach(a):
    """t3_mono_reach: input T3_MODE (0=L,1=R) -> builds MONO_VIS_L or MONO_VIS_R
    (whichever T3_MODE selects) via the same row-by-row fixed-point + down-
    propagate structure as tuck_bfs's own main routine, seeded from the same
    spawn state (3,0,H). Clears only the SELECTED plane."""
    a.label("t3_mono_reach")
    a.ins("LDA_zp", T3_MODE)
    a.br("BEQ", "t3mr_clr_L")
    a.ins("LDX_imm", 63)
    a.label("t3mr_clrR")
    a.ins("LDA_imm", 0)
    a.ins16("STA_absX", MONO_VIS_R)
    a.ins("DEX")
    a.br("BPL", "t3mr_clrR")
    a.jmp("t3mr_clrdone")
    a.label("t3mr_clr_L")
    a.ins("LDX_imm", 63)
    a.label("t3mr_clrL")
    a.ins("LDA_imm", 0)
    a.ins16("STA_absX", MONO_VIS_L)
    a.ins("DEX")
    a.br("BPL", "t3mr_clrL")
    a.label("t3mr_clrdone")
    a.ins("LDA_imm", 3); a.ins("STA_zp", TB.IL_X)
    a.ins("LDA_imm", 0); a.ins("STA_zp", TB.IL_Y)
    a.ins("LDA_imm", 0); a.ins("STA_zp", TB.IL_O)
    a.jsr("tb_is_legal")
    a.ins("CMP_imm", 1)
    a.br("BEQ", "t3mr_seedok")
    a.ins("RTS")
    a.label("t3mr_seedok")
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", TB.VB_ROWBASE)
    a.ins("LDA_imm", 12)
    a.ins("STA_zp", TB.VB_S)
    a.jsr("t3_vis_set_new")
    a.ins("LDA_imm", 0)
    a.ins("STA_zp", TB.BFS_Y)
    a.label("t3mr_rowloop")
    a.jsr("t3_row_fixedpoint")
    a.jsr("t3_down_propagate")
    a.ins("INC_zp", TB.BFS_Y)
    a.ins("LDA_zp", TB.BFS_Y)
    a.ins("CMP_imm", ROWS)
    a.br("BNE", "t3mr_rowloop")
    a.ins("RTS")


# ================================================= tier-3 phase-2 (per row) ===
def _emit_t3_phase2_vert(a):
    """t3_phase2_vert: inputs T3_TARGET2 (=TR_TARGET), T3_REST2, T3_SD, T3_R (the
    row under test) -> A=1 if entering T3_TARGET2 at row T3_R falls straight to
    T3_REST2 (same geometric check as tr_try_vert's per-row body, factored out so
    it can be driven by mono_reach's row gate instead of the first_occ-bounded
    loop tier 1 uses). Does NOT touch TR_A/TR_R (tier 1's own scratch) so tier 1
    and tier 3 can share the surrounding TR_TARGET/TR_REST/TR_ISVERT cells safely
    if ever called back-to-back on the same candidate."""
    a.label("t3_phase2_vert")
    a.ins("LDA_zp", T3_R); a.ins("STA_zp", TRB.TR_R2)
    a.ins("LDA_zp", T3_TARGET2); a.ins("STA_zp", TRB.TR_C2)
    a.jsr("tr_is_empty")
    a.ins("CMP_imm", 1)
    a.br("BEQ", "t3p2v_e1ok")
    a.ins("LDA_imm", 0); a.ins("RTS")
    a.label("t3p2v_e1ok")
    a.ins("LDA_zp", T3_R)
    a.br("BEQ", "t3p2v_topok")
    a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", TRB.TR_R2)
    a.ins("LDA_zp", T3_TARGET2); a.ins("STA_zp", TRB.TR_C2)
    a.jsr("tr_is_empty")
    a.ins("CMP_imm", 1)
    a.br("BEQ", "t3p2v_topok")
    a.ins("LDA_imm", 0); a.ins("RTS")
    a.label("t3p2v_topok")
    a.ins("LDA_zp", T3_TARGET2); a.ins("STA_zp", TRB.TR_TARGET)
    a.ins("LDA_zp", T3_R); a.ins("STA_zp", TRB.TR_R)
    a.jsr("tr_fall_vert")
    a.ins("LDA_zp", TRB.TR_RF); a.ins("CMP_zp", T3_REST2)
    a.br("BEQ", "t3p2v_restmatch")
    a.ins("LDA_imm", 0); a.ins("RTS")
    a.label("t3p2v_restmatch")
    a.ins("LDA_zp", TRB.TR_RF); a.ins("CMP_zp", T3_SD)
    a.br("BEQ", "t3p2v_no")
    a.br("BCC", "t3p2v_no")
    a.ins("LDA_zp", TRB.TR_RF)
    a.br("BEQ", "t3p2v_yes")
    a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", TRB.TR_R2)
    a.ins("LDA_zp", T3_TARGET2); a.ins("STA_zp", TRB.TR_C2)
    a.jsr("tr_is_empty")
    a.ins("CMP_imm", 1)
    a.br("BEQ", "t3p2v_yes")
    a.label("t3p2v_no")
    a.ins("LDA_imm", 0); a.ins("RTS")
    a.label("t3p2v_yes")
    a.ins("LDA_imm", 1); a.ins("RTS")


def _emit_t3_phase2_horiz(a):
    """t3_phase2_horiz: same contract as t3_phase2_vert, horizontal geometry
    (mirrors tr_try_horiz's per-row body: both cells at the trigger row, fall
    check on both target/target+1)."""
    a.label("t3_phase2_horiz")
    a.ins("LDA_zp", T3_R); a.ins("STA_zp", TRB.TR_R2)
    a.ins("LDA_zp", T3_TARGET2); a.ins("STA_zp", TRB.TR_C2)
    a.jsr("tr_is_empty")
    a.ins("CMP_imm", 1)
    a.br("BEQ", "t3p2h_c1ok")
    a.ins("LDA_imm", 0); a.ins("RTS")
    a.label("t3p2h_c1ok")
    a.ins("LDA_zp", T3_R); a.ins("STA_zp", TRB.TR_R2)
    a.ins("LDA_zp", T3_TARGET2); a.ins("CLC"); a.ins("ADC_imm", 1); a.ins("STA_zp", TRB.TR_C2)
    a.jsr("tr_is_empty")
    a.ins("CMP_imm", 1)
    a.br("BEQ", "t3p2h_c2ok")
    a.ins("LDA_imm", 0); a.ins("RTS")
    a.label("t3p2h_c2ok")
    a.ins("LDA_zp", T3_TARGET2); a.ins("STA_zp", TRB.TR_TARGET)
    a.ins("LDA_zp", T3_R); a.ins("STA_zp", TRB.TR_R)
    a.jsr("tr_fall_horiz")
    a.ins("LDA_zp", TRB.TR_RF); a.ins("CMP_zp", T3_REST2)
    a.br("BEQ", "t3p2h_restmatch")
    a.ins("LDA_imm", 0); a.ins("RTS")
    a.label("t3p2h_restmatch")
    a.ins("LDA_zp", TRB.TR_RF); a.ins("CMP_zp", T3_SD)
    a.br("BEQ", "t3p2h_no")
    a.br("BCC", "t3p2h_no")
    a.ins("LDA_imm", 1); a.ins("RTS")
    a.label("t3p2h_no")
    a.ins("LDA_imm", 0); a.ins("RTS")


# ============================================================= tier-3 search ==
def _emit_tr3_derive(a):
    """tr3_derive: TIER-3 FALLBACK, called from tr_derive (tuck_bfs_translate_
    6502.py's wiring, see build_copro_d3.py) only when tier 1 already failed.
    Inputs TR_TARGET/TR_REST/TR_ORIENT/TR_ISVERT (same cells tr_derive itself
    uses -- tier 1 has already returned by the time this runs, so reusing them
    is safe). Builds MONO_VIS_L and MONO_VIS_R (T3_MODE=0 then 1), computes T3_SD
    once (first_occ(target)-1, same as tier 1's sd), then searches approach
    columns nearest-to-target-first (d=0..7, d=0 tries ONLY target itself -- the
    rotation-kick-only case, see translate_ref_tier3.py's derive_tier3
    docstring), each row 0..15 gated on t3_vis_test(MONO_VIS_L) OR
    t3_vis_test(MONO_VIS_R), phase-2-checked via t3_phase2_vert/horiz. Sets
    TR_FOUND/TR_A/TR_R on success (the SAME cells tier 1 would have set), so
    tr_translate's CANDLIST-write code needs no changes at all."""
    a.label("tr3_derive")
    a.ins("LDA_zp", TRB.TR_TARGET); a.ins("STA_zp", T3_TARGET2)
    a.ins("LDA_zp", TRB.TR_REST); a.ins("STA_zp", T3_REST2)
    a.ins("LDA_zp", TRB.TR_ORIENT); a.ins("STA_zp", T3_ORIENT2)
    a.ins("LDA_zp", TRB.TR_ISVERT); a.ins("STA_zp", T3_ISVERT2)
    a.ins("LDA_imm", 0); a.ins("STA_zp", T3_MODE)
    a.jsr("t3_mono_reach")
    a.ins("LDA_imm", 1); a.ins("STA_zp", T3_MODE)
    a.jsr("t3_mono_reach")
    # T3_SD = fc - 1, where fc = first_occ(target) for VERTICAL, or
    # min(first_occ(target), first_occ(target+1)) for HORIZONTAL -- matching
    # _phase2_ok's python fc computation exactly (and tr_try_horiz's own "min of
    # two first_occ" rule, same TR_TMP2-not-TR_TMP stash to dodge tr_first_occ's
    # internal-scratch-reuse trap -- see that routine's own docstring for the
    # concrete board that first found this bug in tier 1's port). Missing the
    # min() here for horizontal was a real bug found via the direct bit-exact
    # gate (board 8, target=5 fully empty but target+1=6 occupied shallower --
    # using first_occ(target) alone gave a wildly-too-permissive SD, rejecting a
    # valid rf=11 candidate because rf>sd was checked against the wrong bound).
    a.ins("LDA_zp", T3_ISVERT2)
    a.br("BEQ", "tr3d_fch")
    a.ins("LDA_zp", T3_TARGET2); a.ins("STA_zp", TRB.TR_FOC_X)
    a.jsr("tr_first_occ")
    a.jmp("tr3d_fcgot")
    a.label("tr3d_fch")
    a.ins("LDA_zp", T3_TARGET2); a.ins("STA_zp", TRB.TR_FOC_X)
    a.jsr("tr_first_occ"); a.ins("STA_zp", TRB.TR_TMP2)
    a.ins("LDA_zp", T3_TARGET2); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("STA_zp", TRB.TR_FOC_X)
    a.jsr("tr_first_occ")
    a.ins("CMP_zp", TRB.TR_TMP2)
    a.br("BCC", "tr3d_fcgot")
    a.ins("LDA_zp", TRB.TR_TMP2)
    a.label("tr3d_fcgot")
    a.ins("CMP_imm", 0)
    a.br("BNE", "tr3d_fcok")
    a.ins("LDA_imm", 0); a.ins("STA_zp", TRB.TR_FOUND)
    a.ins("RTS")
    a.label("tr3d_fcok")
    a.ins("SEC"); a.ins("SBC_imm", 1); a.ins("STA_zp", T3_SD)
    # T3_MAXA = COLS if vert else COLS-1 (horizontal anchor must leave room for
    # the partner cell at a+1)
    a.ins("LDA_zp", T3_ISVERT2)
    a.br("BEQ", "tr3d_maxh")
    a.ins("LDA_imm", COLS); a.ins("STA_zp", T3_MAXA)
    a.jmp("tr3d_maxdone")
    a.label("tr3d_maxh")
    a.ins("LDA_imm", COLS - 1); a.ins("STA_zp", T3_MAXA)
    a.label("tr3d_maxdone")
    a.ins("LDA_imm", 0); a.ins("STA_zp", TRB.TR_FOUND)
    # d=0: try approach==target only
    a.ins("LDA_zp", T3_TARGET2); a.ins("STA_zp", T3_A)
    a.jsr("tr3d_try_a")
    a.ins("LDA_zp", TRB.TR_FOUND)
    a.br("BEQ", "tr3d_d0miss")
    a.ins("RTS")
    a.label("tr3d_d0miss")
    a.ins("LDA_imm", 1); a.ins("STA_zp", T3_D)
    a.label("tr3d_dloop")
    a.ins("LDA_zp", T3_D); a.ins("CMP_imm", COLS)
    a.br("BEQ", "tr3d_alldone")
    # cand_lo = target - d
    a.ins("LDA_zp", T3_TARGET2); a.ins("SEC"); a.ins("SBC_zp", T3_D)
    a.br("BCC", "tr3d_lo_oob")             # target-d < 0
    a.ins("STA_zp", T3_A)
    a.jsr("tr3d_try_a")
    a.ins("LDA_zp", TRB.TR_FOUND)
    a.br("BEQ", "tr3d_lo_oob")
    a.ins("RTS")
    a.label("tr3d_lo_oob")
    # cand_hi = target + d
    a.ins("LDA_zp", T3_TARGET2); a.ins("CLC"); a.ins("ADC_zp", T3_D)
    a.ins("CMP_zp", T3_MAXA)
    a.br("BCS", "tr3d_hi_oob")             # target+d >= max_a
    a.ins("STA_zp", T3_A)
    a.jsr("tr3d_try_a")
    a.ins("LDA_zp", TRB.TR_FOUND)
    a.br("BEQ", "tr3d_hi_oob")
    a.ins("RTS")
    a.label("tr3d_hi_oob")
    a.ins("INC_zp", T3_D)
    a.jmp("tr3d_dloop")
    a.label("tr3d_alldone")
    a.ins("RTS")

    # ---- tr3d_try_a: for the current T3_A, scan rows 0..15, gate on mono, phase2
    a.label("tr3d_try_a")
    a.ins("LDA_imm", 0); a.ins("STA_zp", TRB.TR_FOUND)
    a.ins("LDA_imm", 0); a.ins("STA_zp", T3_R)
    a.label("tr3d_rloop")
    a.ins("LDA_zp", T3_A)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", T3_ORIENT2)
    a.ins("STA_zp", TB.VB_S)
    a.ins("LDA_zp", T3_R)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("STA_zp", TB.VB_ROWBASE)
    a.ins("LDA_imm", 0); a.ins("STA_zp", T3_MODE)
    a.jsr("t3_vis_test")
    a.ins("CMP_imm", 1)
    a.br("BEQ", "tr3d_rmono")
    a.ins("LDA_zp", T3_A)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", T3_ORIENT2)
    a.ins("STA_zp", TB.VB_S)
    a.ins("LDA_zp", T3_R)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("STA_zp", TB.VB_ROWBASE)
    a.ins("LDA_imm", 1); a.ins("STA_zp", T3_MODE)
    a.jsr("t3_vis_test")
    a.ins("CMP_imm", 1)
    a.br("BEQ", "tr3d_rmono")
    a.jmp("tr3d_rnext")
    a.label("tr3d_rmono")
    a.ins("LDA_zp", T3_ISVERT2)
    a.br("BEQ", "tr3d_rhoriz")
    a.jsr("t3_phase2_vert")
    a.jmp("tr3d_rcheck")
    a.label("tr3d_rhoriz")
    a.jsr("t3_phase2_horiz")
    a.label("tr3d_rcheck")
    a.ins("CMP_imm", 1)
    a.br("BEQ", "tr3d_rfound")
    a.jmp("tr3d_rnext")
    a.label("tr3d_rfound")
    a.ins("LDA_zp", T3_A); a.ins("STA_zp", TRB.TR_A)
    a.ins("LDA_zp", T3_R); a.ins("STA_zp", TRB.TR_R)
    a.ins("LDA_imm", 1); a.ins("STA_zp", TRB.TR_FOUND)
    a.ins("RTS")
    a.label("tr3d_rnext")
    a.ins("INC_zp", T3_R)
    a.ins("LDA_zp", T3_R)
    a.ins("CMP_imm", ROWS)
    a.br("BEQ", "tr3d_ta_done")            # loop body long -> invert+JMP
    a.jmp("tr3d_rloop")
    a.label("tr3d_ta_done")
    a.ins("RTS")


def _emit_tr_derive_cascade(a):
    """tr_derive_cascade: tier1 first (tr_derive, UNCHANGED, from tuck_bfs_
    translate_6502.py), falling back to tr3_derive only if tier 1 found nothing.
    This is the ONLY new call site tr_translate_tier3 (below) needs -- tier 1's
    own tr_derive/tr_try_vert/tr_try_horiz are never touched, so DRCOPRO_TUCKBFS
    without the tier-3 knob keeps its existing byte-for-byte behaviour."""
    a.label("tr_derive_cascade")
    a.jsr("tr_derive")
    a.ins("LDA_zp", TRB.TR_FOUND)
    a.br("BNE", "tdc_done")
    a.jsr("tr3_derive")
    a.label("tdc_done")
    a.ins("RTS")


def _emit_tr_translate_tier3(a):
    """tr_translate_tier3: byte-for-byte the SAME loop as tuck_bfs_translate_
    6502.tr_translate, except calling tr_derive_cascade instead of tr_derive
    directly -- duplicated rather than parameterizing tr_translate itself, same
    "new additive entry point, don't modify what's shipped" pattern as
    DRCOPRO_TUCKBFS's own relationship to DRCOPRO_TUCKV3."""
    a.label("tr_translate_tier3")
    a.ins("LDA_imm", 0)
    a.ins16("STA_abs", TRB.TS_CNT)
    a.ins16("STA_abs", TRB.TS_DROP)
    a.ins("STA_zp", TRB.TR_I)
    a.label("trt3_loop")
    a.ins("LDA_zp", TRB.TR_I); a.ins("CMP_zp", TB.BFS_OUTN)
    a.br("BEQ", "trt3_done")
    a.ins("LDX_zp", TRB.TR_I)
    a.ins16("LDA_absX", TB.BFS_OUT_X); a.ins("STA_zp", TRB.TR_TARGET)
    a.ins16("LDA_absX", TB.BFS_OUT_Y); a.ins("STA_zp", TRB.TR_REST)
    a.ins16("LDA_absX", TB.BFS_OUT_O); a.ins("STA_zp", TRB.TR_ORIENT)
    a.ins("LDA_zp", TRB.TR_ORIENT); a.ins("AND_imm", 1); a.ins("STA_zp", TRB.TR_ISVERT)
    a.jsr("tr_derive_cascade")
    a.ins("LDA_zp", TRB.TR_FOUND)
    a.br("BEQ", "trt3_dropped")
    a.ins16("LDA_abs", TRB.TS_CNT); a.ins("CMP_imm", TRB.CAPACITY)
    a.br("BCC", "trt3_room")
    a.ins16("INC_abs", TRB.TS_DROP)
    a.jmp("trt3_done")
    a.label("trt3_room")
    a.ins16("LDA_abs", TRB.TS_CNT)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins16("ADC_abs", TRB.TS_CNT)
    a.ins("TAX")
    a.ins("LDA_zp", TRB.TR_TARGET); a.ins16("STA_absX", TRB.CANDLIST + 0)
    a.ins("LDA_zp", TRB.TR_A); a.ins16("STA_absX", TRB.CANDLIST + 1)
    a.ins("LDA_zp", TRB.TR_R); a.ins16("STA_absX", TRB.CANDLIST + 2)
    a.ins("LDA_zp", TRB.TR_REST); a.ins16("STA_absX", TRB.CANDLIST + 3)
    a.ins("LDA_zp", TRB.TR_ORIENT); a.ins16("STA_absX", TRB.CANDLIST + 4)
    a.ins16("INC_abs", TRB.TS_CNT)
    a.jmp("trt3_next")
    a.label("trt3_dropped")
    a.ins16("INC_abs", TRB.TS_DROP)
    a.label("trt3_next")
    a.ins("INC_zp", TRB.TR_I)
    a.jmp("trt3_loop")
    a.label("trt3_done")
    a.ins("RTS")


def emit_tier3(a):
    """Public entry: appends every tier-3 label onto an EXISTING Asm6502 instance
    that already has tuck_bfs_6502.emit_tuck_bfs and tuck_bfs_translate_6502.
    emit_translate on it (tr3_derive calls tb_is_legal/tb_vbit/tr_first_occ/
    tr_is_empty/tr_fall_vert/tr_fall_horiz by label, which must already exist).
    tr_translate_tier3 is the call site an integration build uses IN PLACE OF
    tr_translate -- see build_copro_d3.py's DRCOPRO_TUCKBFS_TIER3 wiring."""
    _emit_t3_vis_test(a)
    _emit_t3_vis_set_new(a)
    _emit_t3_mark_state(a)
    _emit_t3_check_and_mark(a)
    _emit_t3_row_step(a)
    _emit_t3_row_fixedpoint(a)
    _emit_t3_down_propagate(a)
    _emit_t3_mono_reach(a)
    _emit_t3_phase2_vert(a)
    _emit_t3_phase2_horiz(a)
    _emit_tr3_derive(a)
    _emit_tr_derive_cascade(a)
    _emit_tr_translate_tier3(a)


def build_combined(base=0x8000):
    a = TB.build(base)
    TRB.emit_translate(a)
    emit_tier3(a)
    return a


if __name__ == "__main__":
    a = build_combined()
    code = a.assemble()
    print(f"tuck_bfs+translate+tier3 assembled: {len(code)} bytes @ ${a.base:04X}, "
          f"{len(a.labels)} labels")
