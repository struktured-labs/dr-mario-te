#!/usr/bin/env python3
"""The tuck-path ply-2 exploration block -- a DUPLICATE (not shared subroutine) of
test_search_d3.py's `_emit_search_d3_engine` lines ~402-527 (the "o_nw" through "o_cand"
segment: WIN short-circuit, full ply-2 enumeration over 32 (variant,col) actions via
_e_node, top-K2=8 selection, third-ply stratified 4-pill expectimax, DISC_SHIFT temporal
blend), per the team-lead's stage-2 ruling: the byte-identity gate (flag-off must be
byte-identical) forces duplication here, since sharing would mean replacing already-
shipped inlined bytes with a JSR in the base build too.

REUSED (Python-level only, to minimize hand-written 6502 -- NOT the same as sharing the
emitted bytes): _e_copy/_e_node/_e_score/_e_poll from test_search_d3.py (generic RTL-
command emission helpers, not base-vs-tuck-specific), the "expectimax" label (JSR'd, not
inlined -- expectimax is ALREADY its own subroutine in the base build, called via JSR from
k_ex; calling it from here is the SAME kind of call the base loop itself makes, not new
sharing), and the D_*/TK_* zero-page addresses (address reuse for correctness -- my loop
and the base ply-1 loop's own ply-2 exploration are never live at the same time within one
decision, since `search` returns before this runs).

NOT YET INTEGRATED (documented, deferred -- see tuck_score.py's emit_eh_terms_reuse_label):
the EH_PLY1 excav+hang add-on (D_ADL/D_ADH, normally added at k_done in the shipped
EH_PLY1=True build). Until this is wired in, tuck-candidate values are NOT directly
comparable to base-candidate values under an EH_PLY1=True build -- the theta gate would be
miscalibrated (base gets the eh bonus, tuck candidates don't). This block is correct and
differentially tested for EH_PLY1=False; wiring the eh_terms_scan reuse before this
graduates past scratch validation is a hard prerequisite for an EH_PLY1=True build.

NOT YET INTEGRATED: the o_nj tie-break jitter. A deterministic candidate-index processing
order + a strict-greater compare already gives deterministic ties among tuck candidates,
per the team-lead's rider #1 on the 98-raw-candidates finding -- jitter is skippable for
the tuck loop specifically, not just deferred.

Caller contract:
  entry:  CUR ($0700) = the tuck's already-placed+resolved board (land_place_at +
          resolve_capped already ran). Slot 2 = the SAME board (tuck_slot0_inject already
          ran, called WITH leaf1_lo/leaf1_hi so D_L1L/D_L1H holds leaf1 and LEV_WIN_R
          reflects this board's virus count, both still valid on entry here).
          D_I1L/D_I1H = imm1 (tuck_imm1's TI1L/TI1H, copied in by the caller).
  exit:   D_V1L/D_V1H = the tuck candidate's full depth-3 blended value (same units,
          same formula, as a base candidate's D_V1L/D_V1H at o_cand). RTS.
  clobbers: A/X/Y, D_C2/D_O2/D_TKC/D_J/D_MKL/D_MKH/D_MI/D_B2L/D_B2H/D_I2L/D_I2H/D_V3L/
          D_V3H/D_EL/D_EH/TK_KL/TK_KH/TK_O/TK_C/TK_IL/TK_IH (all free to reuse -- `search`
          has already returned by the time this runs in one decision).
"""
from __future__ import annotations


def emit_tuck_ply2_score(a, *, D_C2, D_O2, D_TKC, D_J, D_MKL, D_MKH, D_MI, D_B2L, D_B2H,
                          D_I1L, D_I1H, D_I2L, D_I2H, D_L1L, D_L1H, D_V1L, D_V1H,
                          D_V3L, D_V3H, D_EL, D_EH, S_NA, S_NB,
                          TK_KL, TK_KH, TK_O, TK_C, TK_IL, TK_IH,
                          LEV_LEGAL, LEV_IMM, LEV_WIN_R, LEV_CMD,
                          WIN, DISC, _e_copy, _e_node, _e_score, _e_poll):
    """DISC: bool, mirrors test_search_d3.DISC -- selects the temporal-discount blend
    (True) vs the plain imm1+best2 sum (False) at t2_done, matching k_done's own `if DISC`
    branch exactly (same asr16 formula, byte for byte)."""
    a.label("tuck_ply2_score")
    # ---- WIN short-circuit (mirrors o_nw's entry check, base lines ~402-405) ----
    a.ins16("LDA_abs", LEV_WIN_R); a.br("BEQ", "t2_nw")
    a.ins("CLC"); a.ins("LDA_zp", D_I1L); a.ins("ADC_imm", WIN & 0xFF); a.ins("STA_zp", D_V1L)
    a.ins("LDA_zp", D_I1H); a.ins("ADC_imm", (WIN >> 8) & 0xFF); a.ins("STA_zp", D_V1H)
    a.ins("RTS")
    a.label("t2_nw")
    # board already in CUR and slot 2 (tuck_slot0_inject) -- no _e_copy(2,False) needed
    # here, unlike o_nw's base equivalent which must save CUR->slot2 itself.
    a.ins("LDA_imm", 0); a.ins("STA_zp", D_TKC); a.ins("STA_zp", D_O2)
    a.label("t2_outer"); a.ins("LDA_imm", 0); a.ins("STA_zp", D_C2)
    a.label("t2_inner")
    _e_copy(a, 2, True)                                    # CUR <- slot2 (tuck b1)
    _e_node(a, D_O2, D_C2, S_NA, S_NB)
    a.ins16("LDA_abs", LEV_LEGAL); a.br("BNE", "t2_leg"); a.jmp("t2_next")
    a.label("t2_leg")
    _e_score(a)
    a.ins("CLC"); a.ins16("LDA_abs", LEV_IMM); a.ins("ADC_zp", D_V3L); a.ins("STA_zp", D_MKL)
    a.ins16("LDA_abs", LEV_IMM + 1); a.ins("ADC_zp", D_V3H); a.ins("STA_zp", D_MKH)
    a.ins("LDX_zp", D_TKC)
    a.ins("LDA_zp", D_MKL); a.ins16("STA_absX", TK_KL); a.ins("LDA_zp", D_MKH); a.ins16("STA_absX", TK_KH)
    a.ins16("LDA_abs", LEV_IMM); a.ins16("STA_absX", TK_IL); a.ins16("LDA_abs", LEV_IMM + 1); a.ins16("STA_absX", TK_IH)
    a.ins("LDA_zp", D_O2); a.ins16("STA_absX", TK_O); a.ins("LDA_zp", D_C2); a.ins16("STA_absX", TK_C)
    a.ins("INC_zp", D_TKC)
    a.label("t2_next")
    a.ins("INC_zp", D_C2); a.ins("LDA_zp", D_C2); a.ins("CMP_imm", 8); a.br("BEQ", "t2_oc"); a.jmp("t2_inner")
    a.label("t2_oc")
    a.ins("INC_zp", D_O2); a.ins("LDA_zp", D_O2); a.ins("CMP_imm", 4); a.br("BEQ", "t2_idone"); a.jmp("t2_outer")
    a.label("t2_idone")
    a.ins("LDA_zp", D_TKC); a.br("BNE", "t2_have2")
    # ---- no legal ply-2 children: leaf-only on b1 itself (mirrors base "have2" guard) ----
    _e_copy(a, 2, True)
    a.ins("LDA_imm", 1); a.ins16("STA_abs", LEV_CMD); _e_poll(a)      # CMD 1: leaf on CUR
    _e_score(a)
    a.ins("CLC"); a.ins("LDA_zp", D_I1L); a.ins("ADC_zp", D_V3L); a.ins("STA_zp", D_V1L)
    a.ins("LDA_zp", D_I1H); a.ins("ADC_zp", D_V3H); a.ins("STA_zp", D_V1H)
    a.ins("RTS")
    a.label("t2_have2")
    a.ins("LDA_imm", 0x00); a.ins("STA_zp", D_B2L); a.ins("LDA_imm", 0x80); a.ins("STA_zp", D_B2H)
    a.ins("LDA_imm", 0); a.ins("STA_zp", D_J)
    a.label("t2_kloop")
    a.ins("LDA_zp", D_J); a.ins("CMP_imm", 8); a.br("BCC", "t2_kc1"); a.jmp("t2_kdone"); a.label("t2_kc1")
    a.ins("LDA_zp", D_J); a.ins("CMP_zp", D_TKC); a.br("BCC", "t2_kc2"); a.jmp("t2_kdone"); a.label("t2_kc2")
    a.ins("LDA_imm", 0x00); a.ins("STA_zp", D_MKL); a.ins("LDA_imm", 0x80); a.ins("STA_zp", D_MKH)
    a.ins("LDA_imm", 0xFF); a.ins("STA_zp", D_MI)
    a.ins("LDX_imm", 0)
    a.label("t2_mxloop")
    a.ins("CPX_zp", D_TKC); a.br("BEQ", "t2_mxdone")
    a.ins("LDA_zp", D_MKL); a.ins("SEC"); a.ins16("SBC_absX", TK_KL)
    a.ins("LDA_zp", D_MKH); a.ins16("SBC_absX", TK_KH)
    a.br("BVC", "t2_mxs1"); a.ins("EOR_imm", 0x80); a.label("t2_mxs1")
    a.br("BPL", "t2_mxnx")
    a.ins16("LDA_absX", TK_KL); a.ins("STA_zp", D_MKL); a.ins16("LDA_absX", TK_KH); a.ins("STA_zp", D_MKH)
    a.ins("STX_zp", D_MI)
    a.label("t2_mxnx")
    a.ins("INX"); a.jmp("t2_mxloop")
    a.label("t2_mxdone")
    a.ins("LDX_zp", D_MI)
    a.ins("LDA_imm", 0x00); a.ins16("STA_absX", TK_KL); a.ins("LDA_imm", 0x80); a.ins16("STA_absX", TK_KH)
    a.ins16("LDA_absX", TK_IL); a.ins("STA_zp", D_I2L); a.ins16("LDA_absX", TK_IH); a.ins("STA_zp", D_I2H)
    a.ins16("LDA_absX", TK_O); a.ins("STA_zp", D_O2); a.ins16("LDA_absX", TK_C); a.ins("STA_zp", D_C2)
    _e_copy(a, 2, True)
    _e_node(a, D_O2, D_C2, S_NA, S_NB)
    a.ins16("LDA_abs", LEV_WIN_R); a.br("BEQ", "t2_kex")
    a.ins("CLC"); a.ins("LDA_zp", D_I2L); a.ins("ADC_imm", WIN & 0xFF); a.ins("STA_zp", D_V3L)
    a.ins("LDA_zp", D_I2H); a.ins("ADC_imm", (WIN >> 8) & 0xFF); a.ins("STA_zp", D_V3H)
    a.jmp("t2_khaveval")
    a.label("t2_kex")
    a.jsr("expectimax")
    a.ins("CLC"); a.ins("LDA_zp", D_I2L); a.ins("ADC_zp", D_EL); a.ins("STA_zp", D_V3L)
    a.ins("LDA_zp", D_I2H); a.ins("ADC_zp", D_EH); a.ins("STA_zp", D_V3H)
    a.label("t2_khaveval")
    a.ins("LDA_zp", D_B2L); a.ins("SEC"); a.ins("SBC_zp", D_V3L); a.ins("LDA_zp", D_B2H); a.ins("SBC_zp", D_V3H)
    a.br("BVC", "t2_ks1"); a.ins("EOR_imm", 0x80); a.label("t2_ks1"); a.br("BPL", "t2_knx")
    a.ins("LDA_zp", D_V3L); a.ins("STA_zp", D_B2L); a.ins("LDA_zp", D_V3H); a.ins("STA_zp", D_B2H)
    a.label("t2_knx")
    a.ins("INC_zp", D_J); a.jmp("t2_kloop")
    a.label("t2_kdone")
    if DISC:
        # val1 = imm1 + leaf1 + asr16(best2 - leaf1)   [d = 0.5 temporal discount]
        a.ins("SEC"); a.ins("LDA_zp", D_B2L); a.ins("SBC_zp", D_L1L); a.ins("STA_zp", D_V1L)
        a.ins("LDA_zp", D_B2H); a.ins("SBC_zp", D_L1H)
        a.ins("CMP_imm", 0x80); a.ins("ROR_A"); a.ins("STA_zp", D_V1H)   # asr hi (sign-preserving)
        a.ins("LDA_zp", D_V1L); a.ins("ROR_A"); a.ins("STA_zp", D_V1L)   # ror lo with carry
        a.ins("CLC"); a.ins("LDA_zp", D_V1L); a.ins("ADC_zp", D_L1L); a.ins("STA_zp", D_V1L)
        a.ins("LDA_zp", D_V1H); a.ins("ADC_zp", D_L1H); a.ins("STA_zp", D_V1H)
        a.ins("CLC"); a.ins("LDA_zp", D_V1L); a.ins("ADC_zp", D_I1L); a.ins("STA_zp", D_V1L)
        a.ins("LDA_zp", D_V1H); a.ins("ADC_zp", D_I1H); a.ins("STA_zp", D_V1H)
    else:
        a.ins("CLC"); a.ins("LDA_zp", D_I1L); a.ins("ADC_zp", D_B2L); a.ins("STA_zp", D_V1L)
        a.ins("LDA_zp", D_I1H); a.ins("ADC_zp", D_B2H); a.ins("STA_zp", D_V1H)
    a.ins("RTS")
