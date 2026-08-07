#!/usr/bin/env python3
"""Tuck v3: generalised root-action tucks, task #17 stage-2 design, ported into the
canonical firmware builder for real EMIT_TUCK_V3 integration.

Self-contained, matching v1's tuck_scan.py precedent ("owns its own first-occ scan"):
this module is assembled as its OWN Asm6502 image (a separate ROM region from the search
code), NOT emitted inside test_search_d3.py's own build(). Calls into the search's
already-assembled `resolve_capped`/`expectimax`/`eh_terms_scan` labels use their RESOLVED
ABSOLUTE ADDRESSES (Asm6502.jsr()/jmp() accept a raw int as well as a label -- see
patch_vs_cpu.py's Asm6502.assemble(), `isinstance(target, str)` branch), passed in by
build_copro_d3.py once the search image has been assembled and its labels are known. This
keeps test_search_d3.py's own emission untouched except for the one approved zero-byte
`eh_terms_scan` label (prior commit).

Ported from fpga/copro/tuck_validation/{tuck_scan_v3,tuck_cell_prep,land_place_at,
tuck_score,tuck_ply2_score,tuck_orient_map,tuck_root_extension}.py in the qa-harness repo
(stage-2 scratch validation, all differentially proven there -- see that repo's git log,
commits 7de4e62..5ff3312) with THREE corrections made for the real integration:

  1. Publish addresses corrected to the COPRO-SIDE mailbox v1 already established and the
     RTL already decodes ($6139/$613A -> cart $5087/$5088, CoproDrMario.sv's xlate table) --
     the qa-harness scratch work used $5087/$5088 directly, which is a CART-side address
     the copro cannot itself write to (copro RAM is ONLY $0000-$0FFF + $6100-$61FF); that
     only "worked" there because py65's flat memory model doesn't enforce the real
     address-space split. Caught before this integration, not after.
  2. EH_PLY1 excav+hang add-on now WIRED IN (team-lead: "REQUIRED, not optional -- the
     offline proof scored WITH eh, so a tuck value missing it while base values carry it
     is a value-scale mismatch exactly at the theta compare"). tuck_slot0_inject calls
     `eh_terms_scan` (raw address) right after resolving the tuck's b1, mirroring the base
     search's own o_nw call site; tuck_ply2_score's k_done adds D_ADL/D_ADH exactly like
     the base search's own k_done does when EH_PLY1, same instruction sequence.
  3. `expectimax`'s k_ex call site now uses the raw resolved address (cross-image), not a
     symbolic label.

RAM: unchanged from the qa-harness stage-2 audit (TUCK_V3_FIRMWARE_DESIGN.md section 7) --
CANDLIST at $61AC (14x5B), scan scratch $61A1-$61AB, TS_CNT/TS_DROP $61F6/$61F7, and the
scoring loop's zero page $70-$80. All confirmed clear of test_search_d3.py's own D_*/EH_T*
range ($40-$6F) and primitives.py's soft scratch ($CA-$E6/$DC/$DE).
"""
from __future__ import annotations

import os

# ============================================================ tuck_scan_v3 (enumerator) ==
CAPACITY = 14
CANDLIST = 0x61AC              # 14 x 5B: target, approach, trigger, rest, orient
TS_CNT = 0x61F6
TS_DROP = 0x61F7
TS_C, TS_FC, TS_A, TS_RA, TS_R, TS_RF, TS_TMP, TS_OFF, TS_SIDE, TS_FO = (
    0x61A1, 0x61A2, 0x61A3, 0x61A4, 0x61A5, 0x61A6, 0x61A7, 0x61A8, 0x61A9, 0x61AA)
TS_OFF2 = 0x61AB

ROWS, COLS, EMPTY = 16, 8, 0xFF
H, V, RH, RV = 0, 1, 2, 3                # tuck-ring orientation encoding

# ==================================================================== land_place_at ======
LA_OFFA, LA_OFFB, LA_CA, LA_CB = 0xE2, 0xE3, 0xE4, 0xE5     # reuses land_place's own zp
Z_OFFA, Z_OFFB = 0xDC, 0xDE                                  # primitives.py's placed-cell offsets
RV_CELLS, RV_VIR = 0xE0, 0xE1                                # primitives.py resolve totals

# ================================================================= tuck scoring scratch ===
TI1L, TI1H = 0x70, 0x71                       # tuck imm1 (16-bit)
TP_IDX, TP_BASE = 0x72, 0x73
TP_TARGET, TP_APPROACH, TP_TRIGGER, TP_REST, TP_ORIENT = 0x74, 0x75, 0x76, 0x77, 0x78
TK2_BBVL, TK2_BBVH = 0x79, 0x7A               # fixed best_base_val reference
TK2_BKIND = 0x7B                              # 0 = base won, 1 = a tuck won
TK2_APP, TK2_TRIG = 0x7D, 0x7E                # winning candidate's approach/trigger
TK2_TMPL, TK2_TMPH = 0x7F, 0x80               # gate-compare scratch

# Build knob (team-lead directive, task #17 stage 3 -- firmware theta mini-sweep after
# pass-1's L11 wash: fires/game 4.38 in firmware vs 2.80 at the offline theta*=150,
# indicating theta=150 is a LOOSER gate in shipped-eval units than in the offline coef-
# winner python units it was calibrated in). Read once at import time, same pattern as
# EMIT_TUCK_V3 in build_copro_d3.py -- each worker process must set this env var BEFORE
# importing tuck_v3/build_copro_d3 (a ProcessPoolExecutor initializer, one arm per
# worker), never mutate it mid-process. Default "150" preserves pass-1's exact build
# byte-for-byte (verified: unset DRCOPRO_TUCKV3_THETA -> THETA=150, identical to every
# prior build in this file's history).
THETA = int(os.environ.get("DRCOPRO_TUCKV3_THETA", "150"))

# DEBUG-ONLY readout of the quality gate's own two operands. The gate compares
# D_V1 (a candidate's ply-2 score) against TK2_BBV + THETA, and both live in copro
# zero page where nothing outside the copro can see them -- so "the gate never
# rejects anything" (measured invariant across THETA 150..20000 and -30000, two
# corpora) has several possible mechanisms that are indistinguishable from outside.
# These builds make the operands readable by REPURPOSING the four readback mailbox
# bytes, which costs no RTL change (CoproDrMario's xlate table decodes exactly nine
# cart bytes; everything above $5088 aliases to one scratch byte).
#
#   1 -> $5085/$5086 = TK2_BBV (base best, gate reference)
#        $5087/$5088 = D_BV at exit (best over base and every COMMITTED tuck)
#   2 -> $5085/$5086 = TK2_BBV
#        $5087/$5088 = max D_V1 over ALL candidates, taken BEFORE the gate, so it
#                      is visible whether or not the gate would have admitted it
#
# Mode 2 reuses TK2_APP/TK2_TRIG as the running max and suppresses the commit
# path's writes to them; that destroys the tuck descriptor, which is why these are
# measurement builds only and must never be flashed. Default 0 keeps the shipped
# build byte-identical (asserted by build_dbgpub.sh against 5d010f62).
#   3 -> $5085/$5086 = TK2_BBV (as in modes 1 and 2)
#        $5087        = occupied-cell count of the board handed to the ply-1 leaf
#        $5088        = virus count of that same board
#        both for the candidate that COMMITTED
# Mode 3 exists because the leaf reports WIN on boards carrying 44-48 viruses. Since the
# base search reads the same LEV_WIN_R on the same boards and correctly sees no win, the
# fault is in the tuck path's leaf setup; these counts say whether the board reaching the
# leaf is the tuck board at all.
DBGPUB = int(os.environ.get("DRCOPRO_TUCKV3_DBGPUB", "0"))

# Mode-3 scratch. 0x7C is the only free byte in tuck_v3's own $70-$80 window; 0x81 is
# tuck_bfs's BFS_Y, which is safe to borrow here because tuck_bfs runs to completion
# (tuck_bfs -> translate -> tuck_root_extension) before tre_loop starts, so its scratch is
# dead. Debug builds only -- nothing here is emitted at DBGPUB=0.
DBG_OCC, DBG_VIR = 0x7C, 0x81

# Candidate FIX for the spurious-WIN defect: drop tuck_slot0_inject's CMD 2, which
# overwrites the just-uploaded board with an uninitialised dpram region (see the comment
# at the emit site). Default 0 keeps the shipped build byte-identical; this is a
# behaviour change and must be measured before it is proposed, not after.
FIXSLOT = os.environ.get("DRCOPRO_TUCKV3_FIXSLOT", "0") == "1"

# TUCK-ISOLATING CONTROL. Forces the candidate list empty at the top of
# tuck_root_extension, so the loop falls straight through to tre_done: TK2_BKIND stays 0,
# the descriptor publishes 0xFF, and D_BC/D_BO are left exactly as the base search wrote
# them. It answers a question the 2x2 cannot. `fix_drop` is incoherent by construction,
# so every tier-3-vs-base comparison so far measures TIER-3-PLUS-EXECUTOR AS A PACKAGE,
# not tucks. If this image agrees with the base champion decision-for-decision, it
# isolates the tuck contribution; if it does NOT, the tier-3 image diverges from base for
# reasons that have nothing to do with tucks, and every tier-3-vs-base number in the
# project inherits that.
# ⚠ VALIDATE WITH decide_compare BEFORE SPENDING GAMES. That check cannot lose: either we
# gain a validated control, or we find the divergence -- and the second outcome is the
# more important one and costs one RTL decision per board instead of 55 games.
NOSCAN = os.environ.get("DRCOPRO_TUCKV3_NOSCAN", "0") == "1"

# orient (H/V/RH/RV) -> o4 (test_depth2.py's convention: 0-1 vertical, 2-3 horizontal).
# Derivation + self-check: fpga/copro/tuck_validation/tuck_orient_map.py (qa-harness).
O4_TABLE = [2, 1, 3, 0]      # index by H=0,V=1,RH=2,RV=3

# ---- RTL engine mailbox (test_search_d3.py, unchanged addresses) ----
LEV_BOARD = 0x7000
LEV_A_O4, LEV_A_COL, LEV_A_CA, LEV_A_CB, LEV_A_SL = 0x70E0, 0x70E1, 0x70E2, 0x70E3, 0x70E4
LEV_LEGAL, LEV_RVC, LEV_RVV, LEV_IMM = 0x70E8, 0x70E9, 0x70EA, 0x70EB
LEV_SCO, LEV_WIN_R = 0x70F0, 0x70F2
LEV_WSLOT, LEV_CMD, LEV_GO = 0x70F3, 0x70F4, 0x70F8

CUR = 0x0700

# ---- copro-side tuck descriptor mailbox (v1's addresses, RTL-decoded to cart $5087/$5088
# -- CoproDrMario.sv xlate table, $6139/$613A). v3 REUSES v1's mailbox, not a new one: same
# driver-side executor consumes it either way. ----
TUCK_COL, TUCK_ROW = 0x6139, 0x613A


def _lda_absx_label(a, label):
    """LDA <label>,X where <label> resolves at assemble() time -- ins16() only takes a
    literal int (no fixup support), so this manually pushes the opcode + a fixup entry,
    the same idiom test_search_d3.py's own _lda_absx_label uses for its eh_terms tables."""
    import patch_vs_cpu
    a.code.append(patch_vs_cpu.OPS["LDA_absX"])
    a.fixups.append((len(a.code), "abs", label))
    a.code.append(0x00)
    a.code.append(0x00)


def _far(a, cond, inv, target, tag):
    a.br(inv, f"{tag}_ok")
    a.jmp(target)
    a.label(f"{tag}_ok")


def _e_poll(a, ctr=[0]):
    n = ctr[0]; ctr[0] += 1
    a.label(f"tv3p{n}"); a.ins16("LDA_abs", LEV_GO); a.br("BEQ", f"tv3p{n}")


def _e_copy(a, sl, to_cur):
    a.ins("LDA_imm", sl); a.ins16("STA_abs", LEV_A_SL)
    a.ins("LDA_imm", 2 if to_cur else 3); a.ins16("STA_abs", LEV_CMD)
    _e_poll(a)


def _e_score(a, d_v3l, d_v3h, win, ctr=[0]):
    n = ctr[0]; ctr[0] += 1
    a.ins16("LDA_abs", LEV_WIN_R); a.br("BEQ", f"tv3_esn{n}")
    a.ins("LDA_imm", win & 0xFF); a.ins("STA_zp", d_v3l)
    a.ins("LDA_imm", (win >> 8) & 0xFF); a.ins("STA_zp", d_v3h); a.jmp(f"tv3_esd{n}")
    a.label(f"tv3_esn{n}")
    a.ins16("LDA_abs", LEV_SCO); a.ins("STA_zp", d_v3l)
    a.ins16("LDA_abs", LEV_SCO + 1); a.ins("STA_zp", d_v3h)
    a.label(f"tv3_esd{n}")


def _e_node(a, o_zp, c_zp, ca_abs, cb_abs):
    a.ins("LDA_zp", o_zp); a.ins16("STA_abs", LEV_A_O4)
    a.ins("LDA_zp", c_zp); a.ins16("STA_abs", LEV_A_COL)
    a.ins16("LDA_abs", ca_abs); a.ins("AND_imm", 0x0F); a.ins16("STA_abs", LEV_A_CA)
    a.ins16("LDA_abs", cb_abs); a.ins("AND_imm", 0x0F); a.ins16("STA_abs", LEV_A_CB)
    a.ins("LDA_imm", 4); a.ins16("STA_abs", LEV_CMD)
    _e_poll(a)


def emit_tuck_scan_v3(a, live=0x0500):
    a.label("tuck_scan_v3")
    a.ins("LDA_imm", 0); a.ins16("STA_abs", TS_CNT); a.ins16("STA_abs", TS_DROP)

    a.ins("LDA_imm", 0); a.ins16("STA_abs", TS_C)
    a.label("v3_vcol")
    a.ins16("LDX_abs", TS_C)
    a.jsr("ts3_focc")
    a.ins16("STA_abs", TS_FC)
    a.ins("CMP_imm", 0)
    _far(a, "BEQ", "BNE", "v3_vcnext", "v3vc0")

    a.ins("LDA_imm", 0); a.ins16("STA_abs", TS_SIDE)
    a.label("v3_vside")
    a.ins16("LDA_abs", TS_C); a.ins16("LDX_abs", TS_SIDE)
    a.br("BNE", "v3_vplus")
    a.ins("SEC"); a.ins("SBC_imm", 1)
    _far(a, "BCC", "BCS", "v3_vsnext", "v3vlo")
    a.jmp("v3_vhavea")
    a.label("v3_vplus")
    a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("CMP_imm", COLS)
    _far(a, "BCS", "BCC", "v3_vsnext", "v3vhi")
    a.label("v3_vhavea")
    a.ins16("STA_abs", TS_A)

    a.ins16("LDX_abs", TS_A)
    a.jsr("ts3_focc")
    a.ins("CMP_imm", 0)
    _far(a, "BEQ", "BNE", "v3_vsnext", "v3va0")
    a.ins("SEC"); a.ins("SBC_imm", 1)
    a.ins16("STA_abs", TS_RA)

    a.ins16("LDA_abs", TS_FC); a.ins16("STA_abs", TS_R)
    a.label("v3_vrow")
    a.ins16("LDA_abs", TS_R); a.ins16("CMP_abs", TS_RA)
    a.br("BEQ", "v3_vrow_ok")
    _far(a, "BCS", "BCC", "v3_vsnext", "v3vrend")
    a.label("v3_vrow_ok")

    a.ins16("LDA_abs", TS_R)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins16("ADC_abs", TS_C)
    a.ins16("STA_abs", TS_OFF)
    a.ins16("LDX_abs", TS_OFF); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "v3_vrnext")

    a.ins16("LDA_abs", TS_R); a.ins("CMP_imm", 0)
    a.br("BEQ", "v3_vrnext")
    a.ins16("LDA_abs", TS_OFF); a.ins("SEC"); a.ins("SBC_imm", COLS)
    a.ins("TAX"); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "v3_vrnext")

    a.ins16("LDA_abs", TS_R); a.ins16("STA_abs", TS_RF)
    a.label("v3_vfall")
    a.ins16("LDA_abs", TS_RF); a.ins("CMP_imm", ROWS - 1)
    a.br("BEQ", "v3_vfall_done")
    a.ins16("LDA_abs", TS_OFF); a.ins("CLC"); a.ins("ADC_imm", COLS)
    a.ins("TAX"); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "v3_vfall_done")
    a.ins16("LDA_abs", TS_OFF); a.ins("CLC"); a.ins("ADC_imm", COLS)
    a.ins16("STA_abs", TS_OFF)
    a.ins16("LDA_abs", TS_RF); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_RF)
    a.jmp("v3_vfall")
    a.label("v3_vfall_done")

    a.ins16("LDA_abs", TS_RF); a.ins16("CMP_abs", TS_FC)
    _far(a, "BCC", "BCS", "v3_vrnext", "v3vsd")

    a.ins16("LDA_abs", TS_RF); a.ins("CMP_imm", 0)
    a.br("BEQ", "v3_vrnext")
    a.ins16("LDA_abs", TS_RF); a.ins("SEC"); a.ins("SBC_imm", 1)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins16("ADC_abs", TS_C)
    a.ins("TAX"); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "v3_vrnext")

    a.jsr("ts3_emit_v")

    a.label("v3_vrnext")
    a.ins16("LDA_abs", TS_R); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_R)
    a.jmp("v3_vrow")

    a.label("v3_vsnext")
    a.ins16("LDA_abs", TS_SIDE); a.ins("CMP_imm", 1)
    a.br("BEQ", "v3_vcnext")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", TS_SIDE)
    a.jmp("v3_vside")

    a.label("v3_vcnext")
    a.ins16("LDA_abs", TS_C); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_C)
    a.ins("CMP_imm", COLS)
    _far(a, "BCC", "BCS", "v3_vcol", "v3vcd")

    a.ins("LDA_imm", 0); a.ins16("STA_abs", TS_C)
    a.label("v3_hcol")
    a.ins16("LDX_abs", TS_C)
    a.jsr("ts3_focc"); a.ins16("STA_abs", TS_TMP)
    a.ins16("LDX_abs", TS_C); a.ins("INX")
    a.jsr("ts3_focc")
    a.ins16("CMP_abs", TS_TMP); a.br("BCC", "v3_hmin")
    a.ins16("LDA_abs", TS_TMP)
    a.label("v3_hmin")
    a.ins16("STA_abs", TS_FC)
    a.ins("CMP_imm", 0)
    _far(a, "BEQ", "BNE", "v3_hcnext", "v3hc0")

    a.ins("LDA_imm", 0); a.ins16("STA_abs", TS_SIDE)
    a.label("v3_hside")
    a.ins16("LDA_abs", TS_C); a.ins16("LDX_abs", TS_SIDE)
    a.br("BNE", "v3_hplus")
    a.ins("SEC"); a.ins("SBC_imm", 1)
    _far(a, "BCC", "BCS", "v3_hsnext", "v3hlo")
    a.jmp("v3_hhavea")
    a.label("v3_hplus")
    a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("CMP_imm", COLS - 1)
    _far(a, "BCS", "BCC", "v3_hsnext", "v3hhi")
    a.label("v3_hhavea")
    a.ins16("STA_abs", TS_A)

    a.ins16("LDX_abs", TS_A)
    a.jsr("ts3_focc"); a.ins16("STA_abs", TS_TMP)
    a.ins16("LDX_abs", TS_A); a.ins("INX")
    a.jsr("ts3_focc")
    a.ins16("CMP_abs", TS_TMP); a.br("BCC", "v3_hamin")
    a.ins16("LDA_abs", TS_TMP)
    a.label("v3_hamin")
    a.ins("CMP_imm", 0)
    _far(a, "BEQ", "BNE", "v3_hsnext", "v3ha0")
    a.ins("SEC"); a.ins("SBC_imm", 1)
    a.ins16("STA_abs", TS_RA)

    a.ins16("LDA_abs", TS_FC); a.ins16("STA_abs", TS_R)
    a.label("v3_hrow")
    a.ins16("LDA_abs", TS_R); a.ins16("CMP_abs", TS_RA)
    a.br("BEQ", "v3_hrow_ok")
    _far(a, "BCS", "BCC", "v3_hsnext", "v3hrend")
    a.label("v3_hrow_ok")

    a.ins16("LDA_abs", TS_R)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins16("ADC_abs", TS_C)
    a.ins16("STA_abs", TS_OFF)
    a.ins16("LDX_abs", TS_OFF); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY); a.br("BNE", "v3_hrnext")
    a.ins16("LDA_abs", TS_OFF); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("TAX"); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY); a.br("BNE", "v3_hrnext")

    a.ins16("LDA_abs", TS_R); a.ins16("STA_abs", TS_RF)
    a.label("v3_hfall")
    a.ins16("LDA_abs", TS_RF); a.ins("CMP_imm", ROWS - 1)
    a.br("BEQ", "v3_hfall_done")
    a.ins16("LDA_abs", TS_OFF); a.ins("CLC"); a.ins("ADC_imm", COLS)
    a.ins16("STA_abs", TS_OFF2)
    a.ins("TAX"); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY); a.br("BNE", "v3_hfall_done")
    a.ins16("LDA_abs", TS_OFF2); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins("TAX"); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY); a.br("BNE", "v3_hfall_done")
    a.ins16("LDA_abs", TS_OFF2); a.ins16("STA_abs", TS_OFF)
    a.ins16("LDA_abs", TS_RF); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_RF)
    a.jmp("v3_hfall")
    a.label("v3_hfall_done")

    a.ins16("LDA_abs", TS_RF); a.ins16("CMP_abs", TS_FC)
    _far(a, "BCC", "BCS", "v3_hrnext", "v3hsd")

    a.jsr("ts3_emit_h")

    a.label("v3_hrnext")
    a.ins16("LDA_abs", TS_R); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_R)
    a.jmp("v3_hrow")

    a.label("v3_hsnext")
    a.ins16("LDA_abs", TS_SIDE); a.ins("CMP_imm", 1)
    a.br("BEQ", "v3_hcnext")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", TS_SIDE)
    a.jmp("v3_hside")

    a.label("v3_hcnext")
    a.ins16("LDA_abs", TS_C); a.ins("CLC"); a.ins("ADC_imm", 1)
    a.ins16("STA_abs", TS_C)
    a.ins("CMP_imm", COLS - 1)
    _far(a, "BCC", "BCS", "v3_hcol", "v3hcd")

    a.ins("RTS")

    a.label("ts3_emit_v")
    a.ins("LDA_imm", V); a.jsr("ts3_append")
    a.ins("LDA_imm", RV); a.jsr("ts3_append")
    a.ins("RTS")

    a.label("ts3_emit_h")
    a.ins("LDA_imm", H); a.jsr("ts3_append")
    a.ins("LDA_imm", RH); a.jsr("ts3_append")
    a.ins("RTS")

    # ts3_append borrows zp $E6 (primitives.py's own scratch numbering, unused by
    # tuck_scan_v3 itself) as noted in the qa-harness scratch version; SAFE here because
    # tuck_scan_v3 runs to completion (populating CANDLIST) BEFORE the scoring loop's own
    # land_place_at/resolve_capped calls ever touch $E6 -- no temporal overlap, verified
    # by the architecture (tuck_v3 entry point runs tuck_scan_v3 THEN tuck_root_extension
    # sequentially, never interleaved).
    a.label("ts3_append")
    a.ins16("STA_abs", TS_OFF2)
    a.ins16("LDA_abs", TS_CNT); a.ins("CMP_imm", CAPACITY)
    _far(a, "BCC", "BCS", "ts3a_ok", "ts3adr")
    a.ins16("INC_abs", TS_DROP)
    a.ins("RTS")
    a.label("ts3a_ok")
    a.ins16("LDA_abs", TS_CNT)
    a.ins("STA_zp", 0xE6)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", 0xE6)
    a.ins("TAX")
    a.ins16("LDA_abs", TS_C); a.ins16("STA_absX", CANDLIST + 0)
    a.ins16("LDA_abs", TS_A); a.ins16("STA_absX", CANDLIST + 1)
    a.ins16("LDA_abs", TS_R); a.ins16("STA_absX", CANDLIST + 2)
    a.ins16("LDA_abs", TS_RF); a.ins16("STA_absX", CANDLIST + 3)
    a.ins16("LDA_abs", TS_OFF2); a.ins16("STA_absX", CANDLIST + 4)
    a.ins16("INC_abs", TS_CNT)
    a.ins("RTS")

    a.label("ts3_focc")
    a.ins("TXA"); a.ins16("STA_abs", TS_FO)
    a.ins("LDY_imm", 0)
    a.label("ts3_fo_lp")
    a.ins16("LDX_abs", TS_FO); a.ins16("LDA_absX", live)
    a.ins("CMP_imm", EMPTY)
    a.br("BNE", "ts3_fo_hit")
    a.ins16("LDA_abs", TS_FO); a.ins("CLC"); a.ins("ADC_imm", COLS)
    a.ins16("STA_abs", TS_FO)
    a.ins("INY"); a.ins("CPY_imm", ROWS)
    a.br("BNE", "ts3_fo_lp")
    a.label("ts3_fo_hit")
    a.ins("TYA"); a.ins("RTS")


def emit_land_place_at(a, board=CUR):
    a.label("land_place_at")
    a.ins("LDA_zp", LA_CA); a.ins("ORA_imm", 0x40)
    a.ins("LDX_zp", LA_OFFA); a.ins16("STA_absX", board)
    a.ins("LDA_zp", LA_CB); a.ins("ORA_imm", 0x40)
    a.ins("LDX_zp", LA_OFFB); a.ins16("STA_absX", board)
    a.ins("LDA_zp", LA_OFFA); a.ins("STA_zp", Z_OFFA)
    a.ins("LDA_zp", LA_OFFB); a.ins("STA_zp", Z_OFFB)
    a.ins("RTS")


def emit_tuck_cell_prep(a, s_ca, s_cb):
    a.label("tuck_cell_prep")
    a.ins("LDA_zp", TP_IDX)
    a.ins("STA_zp", TP_BASE)
    a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", TP_BASE)
    a.ins("TAX")
    a.ins16("LDA_absX", CANDLIST + 0); a.ins("STA_zp", TP_TARGET)
    a.ins16("LDA_absX", CANDLIST + 1); a.ins("STA_zp", TP_APPROACH)
    a.ins16("LDA_absX", CANDLIST + 2); a.ins("STA_zp", TP_TRIGGER)
    a.ins16("LDA_absX", CANDLIST + 3); a.ins("STA_zp", TP_REST)
    a.ins16("LDA_absX", CANDLIST + 4); a.ins("STA_zp", TP_ORIENT)

    a.ins("LDA_zp", TP_REST)
    a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A")
    a.ins("CLC"); a.ins("ADC_zp", TP_TARGET)
    a.ins("STA_zp", TP_BASE)

    a.ins("LDA_zp", TP_ORIENT)
    a.ins("AND_imm", 1)
    a.br("BEQ", "tcp_horiz")
    a.ins("LDA_zp", TP_BASE); a.ins("SEC"); a.ins("SBC_imm", 8); a.ins("STA_zp", LA_OFFA)
    a.ins("LDA_zp", TP_BASE); a.ins("STA_zp", LA_OFFB)
    a.jmp("tcp_colour")
    a.label("tcp_horiz")
    a.ins("LDA_zp", TP_BASE); a.ins("STA_zp", LA_OFFA)
    a.ins("CLC"); a.ins("ADC_imm", 1); a.ins("STA_zp", LA_OFFB)

    a.label("tcp_colour")
    a.ins("LDA_zp", TP_ORIENT)
    a.ins("LSR_A"); a.ins("STA_zp", TP_BASE)
    a.ins("LDA_zp", TP_ORIENT); a.ins("AND_imm", 1)
    a.ins("CMP_zp", TP_BASE)
    a.br("BNE", "tcp_swap")
    a.ins16("LDA_abs", s_ca); a.ins("STA_zp", LA_CA)
    a.ins16("LDA_abs", s_cb); a.ins("STA_zp", LA_CB)
    a.jmp("tcp_done")
    a.label("tcp_swap")
    a.ins16("LDA_abs", s_cb); a.ins("STA_zp", LA_CA)
    a.ins16("LDA_abs", s_ca); a.ins("STA_zp", LA_CB)
    a.label("tcp_done")
    a.ins("RTS")


def emit_tuck_imm1(a):
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


def emit_tuck_slot0_inject(a, eh_terms_scan_addr, d_l1l, d_l1h, board=CUR, dest_slot=2):
    """CMD2 (bcell<-slot0), then CMD1 (LEAF -> leaf1/WIN), then -- EH_PLY1 always on for
    v3 (team-lead: required, not optional) -- JSR eh_terms_scan (raw address into the
    search's own image) to compute D_ADL/D_ADH for this board, THEN CMD3 (slot[dest]<-bcell)."""
    a.label("tuck_slot0_inject")
    a.ins("LDA_imm", 0); a.ins16("STA_abs", LEV_WSLOT)
    a.ins("LDX_imm", 0)
    a.label("tsi_up")
    a.ins16("LDA_absX", board); a.ins16("STA_absX", LEV_BOARD)
    a.ins("INX"); a.ins("CPX_imm", 128); a.br("BNE", "tsi_up")
    if not FIXSLOT:
        # ⚠ THIS PAIR IS THE DEFECT. LeafEval.sv:47 documents wslot 0 as CUR, not a slot:
        # a host write with wslot==0 goes straight into `bcell` (line 386) and the slot
        # dpram is written ONLY when wslot!=0 (line 177, `sl_we`). So the 128-byte upload
        # above has ALREADY put the tuck board in CUR -- and this CMD 2 then overwrites it
        # with dpram region 0, which nothing ever fills. The LEAF that follows scans that
        # uninitialised region, finds no virus, and latches win <= !anyvir = 1.
        # Measured consequence: every tuck candidate scores D_I1 + WIN on boards holding
        # 44-48 viruses. The base search is immune because it uploads to slot 1 and copies
        # from slot 1.
        a.ins("LDA_imm", 0); a.ins16("STA_abs", LEV_A_SL)
        a.ins("LDA_imm", 2); a.ins16("STA_abs", LEV_CMD); _e_poll(a)
    a.ins("LDA_imm", 1); a.ins16("STA_abs", LEV_CMD); _e_poll(a)
    a.ins16("LDA_abs", LEV_SCO); a.ins("STA_zp", d_l1l)
    a.ins16("LDA_abs", LEV_SCO + 1); a.ins("STA_zp", d_l1h)
    a.jsr(eh_terms_scan_addr)          # D_ADL/D_ADH <- excav+hang(this board), raw address
    a.ins("LDA_imm", dest_slot); a.ins16("STA_abs", LEV_A_SL)
    a.ins("LDA_imm", 3); a.ins16("STA_abs", LEV_CMD); _e_poll(a)
    a.ins("RTS")


def emit_tuck_ply2_score(a, *, D_C2, D_O2, D_TKC, D_J, D_MKL, D_MKH, D_MI, D_B2L, D_B2H,
                          D_I1L, D_I1H, D_I2L, D_I2H, D_L1L, D_L1H, D_V1L, D_V1H,
                          D_V3L, D_V3H, D_EL, D_EH, D_ADL, D_ADH, S_NA, S_NB,
                          TK_KL, TK_KH, TK_O, TK_C, TK_IL, TK_IH,
                          WIN, DISC, expectimax_addr):
    a.label("tuck_ply2_score")
    a.ins16("LDA_abs", LEV_WIN_R); a.br("BEQ", "t2_nw")
    a.ins("CLC"); a.ins("LDA_zp", D_I1L); a.ins("ADC_imm", WIN & 0xFF); a.ins("STA_zp", D_V1L)
    a.ins("LDA_zp", D_I1H); a.ins("ADC_imm", (WIN >> 8) & 0xFF); a.ins("STA_zp", D_V1H)
    a.ins("RTS")
    a.label("t2_nw")
    a.ins("LDA_imm", 0); a.ins("STA_zp", D_TKC); a.ins("STA_zp", D_O2)
    a.label("t2_outer"); a.ins("LDA_imm", 0); a.ins("STA_zp", D_C2)
    a.label("t2_inner")
    _e_copy(a, 2, True)
    _e_node(a, D_O2, D_C2, S_NA, S_NB)
    a.ins16("LDA_abs", LEV_LEGAL); a.br("BNE", "t2_leg"); a.jmp("t2_next")
    a.label("t2_leg")
    _e_score(a, D_V3L, D_V3H, WIN)
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
    _e_copy(a, 2, True)
    a.ins("LDA_imm", 1); a.ins16("STA_abs", LEV_CMD); _e_poll(a)
    _e_score(a, D_V3L, D_V3H, WIN)
    a.ins("CLC"); a.ins("LDA_zp", D_I1L); a.ins("ADC_zp", D_V3L); a.ins("STA_zp", D_V1L)
    a.ins("LDA_zp", D_I1H); a.ins("ADC_zp", D_V3H); a.ins("STA_zp", D_V1H)
    a.ins("CLC"); a.ins("LDA_zp", D_V1L); a.ins("ADC_zp", D_ADL); a.ins("STA_zp", D_V1L)
    a.ins("LDA_zp", D_V1H); a.ins("ADC_zp", D_ADH); a.ins("STA_zp", D_V1H)
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
    a.jsr(expectimax_addr)             # raw address (cross-image into the search's own code)
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
        a.ins("SEC"); a.ins("LDA_zp", D_B2L); a.ins("SBC_zp", D_L1L); a.ins("STA_zp", D_V1L)
        a.ins("LDA_zp", D_B2H); a.ins("SBC_zp", D_L1H)
        a.ins("CMP_imm", 0x80); a.ins("ROR_A"); a.ins("STA_zp", D_V1H)
        a.ins("LDA_zp", D_V1L); a.ins("ROR_A"); a.ins("STA_zp", D_V1L)
        a.ins("CLC"); a.ins("LDA_zp", D_V1L); a.ins("ADC_zp", D_L1L); a.ins("STA_zp", D_V1L)
        a.ins("LDA_zp", D_V1H); a.ins("ADC_zp", D_L1H); a.ins("STA_zp", D_V1H)
        a.ins("CLC"); a.ins("LDA_zp", D_V1L); a.ins("ADC_zp", D_I1L); a.ins("STA_zp", D_V1L)
        a.ins("LDA_zp", D_V1H); a.ins("ADC_zp", D_I1H); a.ins("STA_zp", D_V1H)
    else:
        a.ins("CLC"); a.ins("LDA_zp", D_I1L); a.ins("ADC_zp", D_B2L); a.ins("STA_zp", D_V1L)
        a.ins("LDA_zp", D_I1H); a.ins("ADC_zp", D_B2H); a.ins("STA_zp", D_V1H)
    # EH_PLY1 add-on (required for v3 -- see module docstring): + D_ADL/D_ADH, precomputed
    # by tuck_slot0_inject's eh_terms_scan call. Mirrors the base search's own k_done.
    a.ins("CLC"); a.ins("LDA_zp", D_V1L); a.ins("ADC_zp", D_ADL); a.ins("STA_zp", D_V1L)
    a.ins("LDA_zp", D_V1H); a.ins("ADC_zp", D_ADH); a.ins("STA_zp", D_V1H)
    a.ins("RTS")


def emit_tuck_root_extension(a, *, D_BVL, D_BVH, D_BC, D_BO, S_BEST_C, S_BEST_O,
                              D_V1L, D_V1H, D_I1L, D_I1H, resolve_capped_addr,
                              cp_live_cur_addr):
    a.label("tuck_o4_table")
    a.raw(*O4_TABLE)

    a.label("tuck_root_extension")
    if NOSCAN:
        # Empty the candidate list the translate step just built. tre_loop's first
        # compare (TP_IDX=0 vs TS_CNT=0) then fails BCC and jumps straight to tre_done,
        # so nothing is scored, nothing commits, and D_BC/D_BO keep the base search's
        # placement. Overriding TS_CNT here rather than skipping the enumerator keeps
        # the change inside this file -- build_copro_d3.py is shared and stays untouched.
        a.ins("LDA_imm", 0); a.ins16("STA_abs", TS_CNT)
    a.ins("LDA_zp", D_BVL); a.ins("STA_zp", TK2_BBVL)
    a.ins("LDA_zp", D_BVH); a.ins("STA_zp", TK2_BBVH)
    a.ins("LDA_imm", 0); a.ins("STA_zp", TK2_BKIND)
    if DBGPUB == 2:
        a.ins("LDA_imm", 0x00); a.ins("STA_zp", TK2_APP)     # running max D_V1 = -32768
        a.ins("LDA_imm", 0x80); a.ins("STA_zp", TK2_TRIG)
    elif DBGPUB == 3:                                        # 0xFF/0xFF = nothing committed
        a.ins("LDA_imm", 0xFF); a.ins("STA_zp", TK2_APP); a.ins("STA_zp", TK2_TRIG)
    a.ins("LDA_imm", 0); a.ins("STA_zp", TP_IDX)

    a.label("tre_loop")
    a.ins("LDA_zp", TP_IDX); a.ins16("CMP_abs", TS_CNT)
    a.br("BCC", "tre_c1"); a.jmp("tre_done")
    a.label("tre_c1")
    # RESET CUR TO THE ORIGINAL BOARD before land_place_at: land_place_at only writes the
    # tuck's own 2 cells and assumes the REST of CUR already holds the correct base board
    # (matching land_place_at.py's own documented contract). Without this reset, CUR still
    # holds whatever the PREVIOUS operation left there -- the base search's own last
    # eh_terms rebuild (before candidate 0) or the previous candidate's own tuck_ply2_score
    # exploration (candidate 1+), both of which mutate CUR heavily via _e_copy/_e_node.
    # Root-caused via a debug ring dumping D_V1 mid-loop during real execution: candidate
    # 0's own imm1/D_V1 differed substantially (300/30300 in isolation vs 260/4892 with
    # `search` run first) purely from CUR's stale content, not from any gate/eh/enumeration
    # bug (all three independently verified correct before this was found).
    a.jsr(cp_live_cur_addr)            # raw address (cross-image into the search's own code)
    a.jsr("tuck_cell_prep")
    a.jsr("land_place_at")
    a.jsr(resolve_capped_addr)         # raw address (cross-image into the search's own code)
    if DBGPUB == 3:
        # Count occupied cells in the board about to be handed to the leaf, and count the
        # VIRUSES in it separately. The leaf reports WIN on boards carrying 44-48 viruses,
        # so either the board reaching it is not this board, or the win flag is not this
        # board's. These two numbers tell those apart without disassembling anything.
        a.ins("LDA_imm", 0); a.ins("STA_zp", DBG_OCC); a.ins("STA_zp", DBG_VIR)
        a.ins("LDX_imm", 0)
        a.label("tre_cnt")
        a.ins16("LDA_absX", CUR); a.ins("CMP_imm", EMPTY); a.br("BEQ", "tre_cnx")
        a.ins("INC_zp", DBG_OCC)
        a.ins("AND_imm", 0xF0); a.ins("CMP_imm", 0xD0); a.br("BNE", "tre_cnx")
        a.ins("INC_zp", DBG_VIR)
        a.label("tre_cnx")
        a.ins("INX"); a.ins("CPX_imm", 128); a.br("BNE", "tre_cnt")
    a.jsr("tuck_imm1")
    a.ins16("LDA_abs", TI1L); a.ins("STA_zp", D_I1L)
    a.ins16("LDA_abs", TI1H); a.ins("STA_zp", D_I1H)
    a.jsr("tuck_slot0_inject")
    a.jsr("tuck_ply2_score")

    if DBGPUB == 2:
        # running max BEFORE the gate: signed 16-bit (max - D_V1), BPL => max wins
        a.ins("LDA_zp", TK2_APP); a.ins("SEC"); a.ins("SBC_zp", D_V1L)
        a.ins("LDA_zp", TK2_TRIG); a.ins("SBC_zp", D_V1H)
        a.br("BVC", "tre_dbgs"); a.ins("EOR_imm", 0x80); a.label("tre_dbgs")
        a.br("BPL", "tre_dbgn")
        a.ins("LDA_zp", D_V1L); a.ins("STA_zp", TK2_APP)
        a.ins("LDA_zp", D_V1H); a.ins("STA_zp", TK2_TRIG)
        a.label("tre_dbgn")

    a.ins("CLC"); a.ins("LDA_zp", TK2_BBVL); a.ins("ADC_imm", THETA & 0xFF); a.ins("STA_zp", TK2_TMPL)
    a.ins("LDA_zp", TK2_BBVH); a.ins("ADC_imm", (THETA >> 8) & 0xFF); a.ins("STA_zp", TK2_TMPH)
    a.ins("LDA_zp", D_V1L); a.ins("SEC"); a.ins("SBC_zp", TK2_TMPL)
    a.ins("LDA_zp", D_V1H); a.ins("SBC_zp", TK2_TMPH)
    a.br("BVC", "tre_gs1"); a.ins("EOR_imm", 0x80); a.label("tre_gs1")
    a.br("BPL", "tre_gok"); a.jmp("tre_next")
    a.label("tre_gok")

    a.ins("LDA_zp", D_BVL); a.ins("SEC"); a.ins("SBC_zp", D_V1L)
    a.ins("LDA_zp", D_BVH); a.ins("SBC_zp", D_V1H)
    a.br("BVC", "tre_bs1"); a.ins("EOR_imm", 0x80); a.label("tre_bs1")
    a.br("BMI", "tre_commit"); a.jmp("tre_next")
    a.label("tre_commit")
    a.ins("LDA_zp", D_V1L); a.ins("STA_zp", D_BVL)
    a.ins("LDA_zp", D_V1H); a.ins("STA_zp", D_BVH)
    a.ins("LDA_zp", TP_TARGET); a.ins("STA_zp", D_BC)
    a.ins("LDX_zp", TP_ORIENT); _lda_absx_label(a, "tuck_o4_table"); a.ins("STA_zp", D_BO)
    a.ins("LDA_zp", D_BC); a.ins16("STA_abs", S_BEST_C)
    a.ins("LDA_zp", D_BO); a.ins16("STA_abs", S_BEST_O)
    if DBGPUB == 3:                    # mode 3 latches THIS candidate's board census
        a.ins("LDA_zp", DBG_OCC); a.ins("STA_zp", TK2_APP)
        a.ins("LDA_zp", DBG_VIR); a.ins("STA_zp", TK2_TRIG)
    elif DBGPUB != 2:                  # mode 2 owns TK2_APP/TK2_TRIG as the running max
        a.ins("LDA_zp", TP_APPROACH); a.ins("STA_zp", TK2_APP)
        a.ins("LDA_zp", TP_TRIGGER); a.ins("STA_zp", TK2_TRIG)
    a.ins("LDA_imm", 1); a.ins("STA_zp", TK2_BKIND)

    a.label("tre_next")
    a.ins("INC_zp", TP_IDX); a.jmp("tre_loop")

    a.label("tre_done")
    a.ins("LDA_zp", TK2_BKIND); a.br("BNE", "tre_pub")
    a.ins("LDA_imm", 0xFF); a.ins16("STA_abs", TUCK_COL); a.ins16("STA_abs", TUCK_ROW)
    a.jmp("tre_ret")
    a.label("tre_pub")
    a.ins("LDA_zp", TK2_APP); a.ins16("STA_abs", TUCK_COL)
    a.ins("LDA_zp", TK2_TRIG); a.ins16("STA_abs", TUCK_ROW)
    a.label("tre_ret")
    if DBGPUB:
        # D_BC/D_BO, NOT S_BEST_C/S_BEST_O: build_copro_d3's stub copies the zero-page
        # pair into the mailbox unconditionally after this routine returns, so a write
        # to S_BEST_* here would be overwritten a few instructions later.
        a.ins("LDA_zp", TK2_BBVL); a.ins("STA_zp", D_BC)
        a.ins("LDA_zp", TK2_BBVH); a.ins("STA_zp", D_BO)
        lo, hi = (TK2_APP, TK2_TRIG) if DBGPUB in (2, 3) else (D_BVL, D_BVH)
        a.ins("LDA_zp", lo); a.ins16("STA_abs", TUCK_COL)
        a.ins("LDA_zp", hi); a.ins16("STA_abs", TUCK_ROW)
    a.ins("RTS")
