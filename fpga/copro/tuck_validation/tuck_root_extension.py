#!/usr/bin/env python3
"""The tuck v3 candidate-loop wiring: runs AFTER the base search's own `search` subroutine
returns (D_BVL/D_BVH/D_BC/D_BO/S_BEST_C/S_BEST_O persist in zero page/RAM past `search`'s
RTS -- confirmed by inspection of _emit_search_d3_engine, no base-routine duplication or
modification needed for this). Captures the FIXED theta-gate reference (best_base_val,
read once before any tuck candidate is tried -- NOT the rolling running-best, matching the
offline-validated root_search.py `choose_root_with_tucks` design from phase 1/2), then
iterates CANDLIST (populated by tuck_scan_v3), scoring each candidate via
tuck_cell_prep + land_place_at + resolve_capped + tuck_imm1 + tuck_slot0_inject +
tuck_ply2_score, gating at theta=150 against the FIXED reference, and keeping the best
gate-passing candidate via a strict-greater compare against the rolling running best
(D_BVL/D_BVH) -- giving deterministic ties by construction (processing CANDLIST in fixed
index order + strict->, satisfying the team-lead's rider #1 on the 98-raw-candidates
finding without needing the o_nj jitter).

Publish contract (mirrors driver-nav's ALREADY-FIXED (stage 1, commit b850159) mailbox
read side -- W_TCOL/W_TROW = 0x5087/0x5088, "copro publishes the tuck descriptor here,
0xFF = none", consumed by patch_cartridge_copro.py's D1 fix which converts W_TROW to
15-W_TROW into TUCK_R2 itself): if a tuck candidate wins the final argmax, W_TCOL <- its
approach column, W_TROW <- its trigger row (RAW, not yet 15-converted -- that conversion
is the driver's job, already implemented and tested in stage 1). Else both 0xFF.

D_BO publish uses TUCK_ORIENT_TO_O4 (tuck_orient_map.py) to convert the winning
candidate's tuck-ring orientation (H/V/RH/RV) to the o4 convention D_BO/S_BEST_O actually
carries for the driver's existing pill-rotation steering -- these are DIFFERENT encodings
in this codebase (see tuck_orient_map.py's docstring); publishing the raw tuck orient
would silently steer the wrong rotation.
"""
from __future__ import annotations

from tuck_orient_map import O4_TABLE

# ---- new zero page (next free after tuck_cell_prep's TP_* range, 0x72-0x78) ----
TK2_BBVL, TK2_BBVH = 0x79, 0x7A     # fixed best_base_val reference, captured once
TK2_BKIND = 0x7B                    # 0 = base action won, 1 = a tuck candidate won
TK2_APP, TK2_TRIG = 0x7D, 0x7E      # winning candidate's approach/trigger (valid iff BKIND==1)
TK2_TMPL, TK2_TMPH = 0x7F, 0x80     # scratch: best_base_val + THETA

THETA = 150   # dose per phase-2's accepted theta*=150 finding


def _lda_absx_label(a, label):
    """LDA <label>,X where <label> resolves at assemble() time -- same trick
    test_search_d3.py's own `_lda_absx_label` uses for its eh_terms tables."""
    import patch_vs_cpu
    a.code.append(patch_vs_cpu.OPS["LDA_absX"])
    a.fixups.append((len(a.code), "abs", label))
    a.code.append(0x00)
    a.code.append(0x00)


def emit_tuck_root_extension(a, *, D_BVL, D_BVH, D_BC, D_BO, S_BEST_C, S_BEST_O,
                              D_V1L, D_V1H, TS_CNT, D_I1L, D_I1H, W_TCOL, W_TROW,
                              TP_IDX, TP_TARGET, TP_APPROACH, TP_TRIGGER, TP_ORIENT,
                              TI1L, TI1H):
    a.label("tuck_o4_table")
    a.raw(*O4_TABLE)

    a.label("tuck_root_extension")
    a.ins("LDA_zp", D_BVL); a.ins("STA_zp", TK2_BBVL)
    a.ins("LDA_zp", D_BVH); a.ins("STA_zp", TK2_BBVH)
    a.ins("LDA_imm", 0); a.ins("STA_zp", TK2_BKIND)
    a.ins("LDA_imm", 0); a.ins("STA_zp", TP_IDX)

    a.label("tre_loop")
    a.ins("LDA_zp", TP_IDX); a.ins16("CMP_abs", TS_CNT)
    a.br("BCC", "tre_c1"); a.jmp("tre_done")
    a.label("tre_c1")
    a.jsr("tuck_cell_prep")
    a.jsr("land_place_at")
    a.jsr("resolve_capped")
    a.jsr("tuck_imm1")
    a.ins16("LDA_abs", TI1L); a.ins("STA_zp", D_I1L)
    a.ins16("LDA_abs", TI1H); a.ins("STA_zp", D_I1H)
    a.jsr("tuck_slot0_inject")
    a.jsr("tuck_ply2_score")
    # D_V1L/D_V1H now holds this candidate's full depth-3 value (tuck_ply2_score's output
    # zp addresses ARE D_V1L/D_V1H -- the caller's own zp, passed through by reference at
    # build time, so no extra copy is needed here).

    # ---- theta gate: val >= best_base_val (FIXED) + THETA ----
    a.ins("CLC"); a.ins("LDA_zp", TK2_BBVL); a.ins("ADC_imm", THETA & 0xFF); a.ins("STA_zp", TK2_TMPL)
    a.ins("LDA_zp", TK2_BBVH); a.ins("ADC_imm", (THETA >> 8) & 0xFF); a.ins("STA_zp", TK2_TMPH)
    a.ins("LDA_zp", D_V1L); a.ins("SEC"); a.ins("SBC_zp", TK2_TMPL)
    a.ins("LDA_zp", D_V1H); a.ins("SBC_zp", TK2_TMPH)
    a.br("BVC", "tre_gs1"); a.ins("EOR_imm", 0x80); a.label("tre_gs1")
    a.br("BPL", "tre_gok"); a.jmp("tre_next")   # negative -> val < ref+THETA -> gate fails
    a.label("tre_gok")

    # ---- keep-best: strict val > D_BVL/D_BVH (rolling running best) ----
    a.ins("LDA_zp", D_BVL); a.ins("SEC"); a.ins("SBC_zp", D_V1L)
    a.ins("LDA_zp", D_BVH); a.ins("SBC_zp", D_V1H)
    a.br("BVC", "tre_bs1"); a.ins("EOR_imm", 0x80); a.label("tre_bs1")
    a.br("BMI", "tre_commit"); a.jmp("tre_next")   # D_BVL-V1 < 0 <=> V1 > D_BVL -> commit
    a.label("tre_commit")
    a.ins("LDA_zp", D_V1L); a.ins("STA_zp", D_BVL)
    a.ins("LDA_zp", D_V1H); a.ins("STA_zp", D_BVH)
    a.ins("LDA_zp", TP_TARGET); a.ins("STA_zp", D_BC)
    a.ins("LDX_zp", TP_ORIENT); _lda_absx_label(a, "tuck_o4_table"); a.ins("STA_zp", D_BO)
    a.ins("LDA_zp", D_BC); a.ins16("STA_abs", S_BEST_C)
    a.ins("LDA_zp", D_BO); a.ins16("STA_abs", S_BEST_O)
    a.ins("LDA_zp", TP_APPROACH); a.ins("STA_zp", TK2_APP)
    a.ins("LDA_zp", TP_TRIGGER); a.ins("STA_zp", TK2_TRIG)
    a.ins("LDA_imm", 1); a.ins("STA_zp", TK2_BKIND)

    a.label("tre_next")
    a.ins("INC_zp", TP_IDX); a.jmp("tre_loop")

    a.label("tre_done")
    a.ins("LDA_zp", TK2_BKIND); a.br("BNE", "tre_pub")
    a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", W_TCOL); a.ins16("STA_abs", W_TROW)
    a.jmp("tre_ret")
    a.label("tre_pub")
    a.ins("LDA_zp", TK2_APP); a.ins16("STA_abs", W_TCOL)
    a.ins("LDA_zp", TK2_TRIG); a.ins16("STA_abs", W_TROW)
    a.label("tre_ret")
    a.ins("RTS")
