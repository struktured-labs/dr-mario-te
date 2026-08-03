#!/usr/bin/env python3
"""Firmware-side component readback for the 20-board localization (task #17 stage 3).

Builds ONE combined image (test_search_d3's real search + tuck_v3's land_place_at/
tuck_imm1/tuck_slot0_inject/tuck_ply2_score, no tuck_cell_prep needed -- this harness
places tucks via flat cell offsets directly, matching tuck_validation/test_tuck_ply2_
score.py's OWN proven pattern, not the target/rest/orient reconstruction used elsewhere)
under the REAL SHIPPED CONFIG (build_copro_d3.build_image()'s exact overrides: NPILLS=4/
SHIFT=2/DISC=True, not the smaller 2/1/False config test_tuck_ply2_score.py itself uses
for speed) plus DEBUG_VAL1=True so the base search's own per-ply1-candidate component
breakdown (extended this session: imm1/leaf1/eh in a second ring, DBG_RING2) is
observable, not just the final value.

BASE argmax components: read back from the DBG_RING/DBG_RING2 entry whose (C1,O1)
matches the requested (var, col) -- this is deliberately "the action's components", not
"whichever action the firmware itself declared winner" -- if firmware's own (D_BC,D_BO)
disagrees with the requested action, that is reported SEPARATELY (a base-level firmware-
vs-offline disagreement, distinct from a same-action component divergence), not silently
conflated with it.

TUCK candidate components: a targeted single-candidate score (land_place_at ->
resolve_capped -> tuck_imm1 -> tuck_slot0_inject -> tuck_ply2_score) for the SAME flat
cell offsets + colours the offline candidate used, reading D_I1L/D_I1H (imm1),
D_L1L/D_L1H (leaf1), D_B2L/D_B2H (best2 raw), D_ADL/D_ADH (eh), D_V1L/D_V1H (total) --
the same zero-page cells the base search uses, since tuck_ply2_score's k_done block is a
byte-for-byte mirror of the base's own (verified in tuck_validation/test_tuck_ply2_
score.py, both paths tested bit-exact there). blend is DERIVED as V1 - I1 - eh (exact,
since this is pure addition/subtraction over already-byte-exact 16-bit values, not a new
6502 computation) rather than re-deriving a separate readback point for it.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
QA_TUCK = "/home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation"
DRIVER = os.environ.get("DRNAV", "/home/struktured/projects/dr-mario-mods-wt/driver-nav")
CANON = os.environ.get("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
for _p in (HERE, QA_TUCK, DRIVER, os.path.join(DRIVER, "tests"), QA + "/bitexact_gate",
           os.path.join(CANON, "tests"), os.path.join(CANON, "fpga", "copro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from patch_vs_cpu import Asm6502                  # noqa: E402
import patch_vs_cpu                               # noqa: E402
patch_vs_cpu.OPS.setdefault("CLD", 0xD8)
patch_vs_cpu.OPS.setdefault("SBC_absX", 0xFD)
patch_vs_cpu.OPS.setdefault("CMP_absX", 0xDD)
patch_vs_cpu.OPS.setdefault("ADC_absX", 0x7D)
patch_vs_cpu.OPS.setdefault("ROR_zp", 0x66)
patch_vs_cpu.OPS.setdefault("ROL_zp", 0x26)
patch_vs_cpu.OPS.setdefault("LSR_zp", 0x46)
patch_vs_cpu.OPS.setdefault("ASL_zp", 0x06)
patch_vs_cpu.OPS.setdefault("ORA_zp", 0x05)
patch_vs_cpu.OPS.setdefault("EOR_zp", 0x45)

import primitives                                  # noqa: E402
from py65_harness import Cpu                       # noqa: E402
import importlib.util                              # noqa: E402


def _force_load(name, path):
    """Force-load a module FROM THE CANONICAL PATH regardless of what may already be
    cached in sys.modules under that name -- the SAME trick firmware_decider.py's
    _load_d3() uses. Required here: importing component_localize.py first (which pulls
    in root_search.py's own sys.path insertions, e.g. ROOT+'/tmp/combo_term') can leave a
    DIFFERENT, older test_search_d3/tuck_v3/nes_d3_golden already cached under the plain
    module name -- confirmed directly: `import firmware_components` alone finds
    'eh_terms_scan' in D3_LABELS, but running component_localize.harvest_boards() first
    in the same process makes it disappear (a stale test_search_d3 without that label
    gets served from sys.modules instead). Never assume a plain `import X` in this
    codebase resolves to the file you think it does once other modules may have run
    first -- verify or force it."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ORDER MATTERS: test_search_d3.py itself does `import nes_d3_golden as G3` at its own
# top level -- if nes_d3_golden isn't already forced into sys.modules FIRST, that internal
# import would silently re-resolve to whatever (possibly stale) copy sys.path finds,
# defeating this force-load for D3's own G3 reference.
G3 = _force_load("nes_d3_golden", os.path.join(CANON, "tests", "nes_d3_golden.py"))
D3 = _force_load("test_search_d3", os.path.join(CANON, "tests", "test_search_d3.py"))
TV = _force_load("tuck_v3", os.path.join(CANON, "fpga", "copro", "tuck_v3.py"))
from common import arrays_to_nes                      # noqa: E402  (bitexact_gate on path via QA in caller)

primitives.BOARD = 0x0700
primitives.LIVE_BOARD = 0x0700

BASE = 0x8000

# ---- REAL SHIPPED CONFIG (build_copro_d3.build_image's own overrides, copied exactly --
# NOT test_tuck_ply2_score.py's smaller/faster 2-pill config) ----
D3.USE_ENGINE = True
D3.DISC = True
D3.EH_PLY1 = True
D3.NPILLS, D3.SHIFT = 4, 2
D3.DEBUG_VAL1 = True
G3.DISC_SHIFT = 1
G3.EXCAV_HANG_PLY1 = True
G3.BURIED_COLOR_AWARE = True
G3.W_VRDY = 12
G3.W_EXCAV = 24
G3.HANG_DEPTH_PROP = True
G3.W_HANG_GAP = 20
G3.HANG_VIRUS_COL_ONLY = True
G3.MATCHED_COVER_SETUP = True
G3.W_MATCHED_COVER = 60
G3.BURIED_NEAREST2_CAP = True
G3.READINESS_EXT_CAP = 0

D3_CODE, D3_LABELS = D3.build()
RESOLVE_CAPPED_ADDR = BASE + D3_LABELS["resolve_capped"]
EXPECTIMAX_ADDR = BASE + D3_LABELS["expectimax"]
EH_TERMS_SCAN_ADDR = BASE + D3_LABELS["eh_terms_scan"]
CP_LIVE_CUR_ADDR = BASE + D3_LABELS["cp_live_cur"]


def _build_tuck_score():
    tv = Asm6502(BASE + len(D3_CODE))
    TV.emit_land_place_at(tv, board=TV.CUR)
    TV.emit_tuck_imm1(tv)
    TV.emit_tuck_slot0_inject(tv, EH_TERMS_SCAN_ADDR, D3.D_L1L, D3.D_L1H, board=TV.CUR)
    TV.emit_tuck_ply2_score(
        tv,
        D_C2=D3.D_C2, D_O2=D3.D_O2, D_TKC=D3.D_TKC, D_J=D3.D_J,
        D_MKL=D3.D_MKL, D_MKH=D3.D_MKH, D_MI=D3.D_MI, D_B2L=D3.D_B2L, D_B2H=D3.D_B2H,
        D_I1L=D3.D_I1L, D_I1H=D3.D_I1H, D_I2L=D3.D_I2L, D_I2H=D3.D_I2H,
        D_L1L=D3.D_L1L, D_L1H=D3.D_L1H, D_V1L=D3.D_V1L, D_V1H=D3.D_V1H,
        D_V3L=D3.D_V3L, D_V3H=D3.D_V3H, D_EL=D3.D_EL, D_EH=D3.D_EH,
        D_ADL=D3.D_ADL, D_ADH=D3.D_ADH, S_NA=D3.S_NA, S_NB=D3.S_NB,
        TK_KL=D3.TK_KL, TK_KH=D3.TK_KH, TK_O=D3.TK_O, TK_C=D3.TK_C,
        TK_IL=D3.TK_IL, TK_IH=D3.TK_IH, WIN=D3.WIN, DISC=D3.DISC,
        expectimax_addr=EXPECTIMAX_ADDR,
    )
    tv.label("run_resolve")
    tv.jsr(CP_LIVE_CUR_ADDR)
    tv.jsr("land_place_at")
    tv.jsr(RESOLVE_CAPPED_ADDR)
    tv.jsr("tuck_imm1")
    tv.ins16("LDA_abs", TV.TI1L); tv.ins("STA_zp", D3.D_I1L)
    tv.ins16("LDA_abs", TV.TI1H); tv.ins("STA_zp", D3.D_I1H)
    tv.ins("RTS")
    tv.label("run_score")
    tv.jsr("tuck_slot0_inject")
    tv.jsr("tuck_ply2_score")
    tv.ins("RTS")
    code = tv.assemble()
    return code, tv.labels


TUCK_CODE, TUCK_LABELS = _build_tuck_score()
COMBINED = bytes(D3_CODE) + bytes(TUCK_CODE)
RUN_RESOLVE_ADDR = BASE + len(D3_CODE) + TUCK_LABELS["run_resolve"]
RUN_SCORE_ADDR = BASE + len(D3_CODE) + TUCK_LABELS["run_score"]


def _s16(lo, hi):
    v = lo | (hi << 8)
    return v - 0x10000 if hi >= 0x80 else v


def _new_cpu(board_nes, ca0, cb0, na0, nb0, pillA, pillB):
    cpu = Cpu()
    cpu.load(BASE, COMBINED)
    cpu.set_board(board_nes)
    D3.attach_engine_emu(cpu)
    cpu.mem[D3.S_CA] = ca0
    cpu.mem[D3.S_CB] = cb0
    cpu.mem[D3.S_NA] = na0
    cpu.mem[D3.S_NB] = nb0
    for i in range(D3.NPILLS):
        cpu.mem[D3.PILLA + i] = pillA[i]
        cpu.mem[D3.PILLB + i] = pillB[i]
    return cpu


def score_base_and_tuck(col, vir, ca, cb, na, nb, base_var, base_col,
                         tuck_offa, tuck_offb, tuck_ta, tuck_tb, npills_stream=None):
    """col/vir: root_search.py's 1..3/0..1 convention (as harvested). ca/cb/na/nb: SAME
    1..3 convention (as harvested; converted to 0..2 here, matching build_copro_d3's own
    `ca-1,cb-1,na-1,nb_-1` contract -- see firmware_decider.py's fixed decide()).
    base_var/base_col: the offline base argmax's (variant, column) -- var*8+col encoding.
    tuck_offa/offb/ta/tb: land_place_at's own flat-offset + 0..2-colour convention.

    Returns (base_components, tuck_components, base_agrees_dict) where base_agrees_dict
    reports whether the FIRMWARE'S OWN (D_BC,D_BO) winner matches the requested
    (base_var,base_col) -- a SEPARATE finding from "do the components for the SAME action
    agree", per the team-lead's ruling not to conflate the two."""
    board_nes = arrays_to_nes(list(col), list(vir))
    ca0, cb0, na0, nb0 = ca - 1, cb - 1, na - 1, nb - 1

    # fast_rtl_x._VAR_OF_O4 is self-inverse (var = _VAR_OF_O4[o4] and o4 = _VAR_OF_O4[var]
    # both hold), matching the convention already established and used throughout this
    # session (firmware_decider.py's FX._VAR_OF_O4[d_bo]*8+d_bc reconstruction).
    import fast_rtl_x as FX
    o1_target = int(FX._VAR_OF_O4[base_var])

    # arbitrary 4-pill stream: pill 0 = (ca,cb)/(na,nb), rest filler (only pill 0 matters
    # for a single decide() call -- ply1/ply2 read PILLA[0]/PILLB[0] and S_NA/S_NB).
    pillA = [ca0, ca0, ca0, ca0][:D3.NPILLS]
    pillB = [cb0, cb0, cb0, cb0][:D3.NPILLS]

    # ---- BASE: run search(), scan both rings for the requested (base_col, o1_target) ----
    cpu = _new_cpu(board_nes, ca0, cb0, na0, nb0, pillA, pillB)
    cpu.call(BASE + D3_LABELS["search"], max_steps=3_000_000_000)
    match = None
    for j1 in range(32):
        off, off2 = D3.DBG_RING + j1 * 8, D3.DBG_RING2 + j1 * 8
        c1r, o1r = cpu.mem[off + 0], cpu.mem[off + 1]
        if c1r == base_col and o1r == o1_target:
            v1 = _s16(cpu.mem[off + 2], cpu.mem[off + 3])
            b2 = _s16(cpu.mem[off + 4], cpu.mem[off + 5])
            i1 = _s16(cpu.mem[off2 + 0], cpu.mem[off2 + 1])
            l1 = _s16(cpu.mem[off2 + 2], cpu.mem[off2 + 3])
            ad = _s16(cpu.mem[off2 + 4], cpu.mem[off2 + 5])
            match = {"imm1": i1, "leaf1": l1, "best2_raw": b2, "blend": v1 - i1 - ad,
                     "eh": ad, "total": v1}
            break
    fw_bc, fw_bo = cpu.mem[D3.D_BC], cpu.mem[D3.D_BO]
    base_agrees = {"fw_winner_col": int(fw_bc), "fw_winner_o1": int(fw_bo),
                   "requested_col": int(base_col), "requested_o1": int(o1_target),
                   "same_action": (int(fw_bc) == int(base_col) and int(fw_bo) == int(o1_target))}
    assert match is not None, (
        f"no DBG_RING entry for (col={base_col},o1={o1_target}) -- either TOPK1<32 pruned "
        f"it (T1C={cpu.mem[D3.D_T1C]}) or this action was illegal on this board.")

    # ---- TUCK: run search() again (fresh CUR-dirtying state, matching the real pipeline
    # order), then the targeted single-candidate score ----
    cpu2 = _new_cpu(board_nes, ca0, cb0, na0, nb0, pillA, pillB)
    cpu2.call(BASE + D3_LABELS["search"], max_steps=3_000_000_000)
    cpu2.mem[TV.LA_OFFA] = tuck_offa
    cpu2.mem[TV.LA_OFFB] = tuck_offb
    # ROOT-CAUSE BUG FOUND HERE (post-localization re-check, task #17 stage 3): tuck_ta/
    # tuck_tb arrive in the SAME 1..3 convention as ca/cb/na/nb (tuck_enum.py's own
    # "colors" field, matching pill_a/pill_b's 1..3 docstring contract) -- but LA_CA/
    # LA_CB, like S_CA/S_CB above, expect the 0..2 tile low-nibble convention. This was
    # the EXACT off-by-one class already found and fixed twice this session
    # (firmware_decider.decide's S_CA/S_CB, and the harvest's own board encoding) --
    # missed here because ca0/cb0/na0/nb0 got the -1 conversion at the top of this
    # function but tuck_ta/tuck_tb, arriving as separate parameters, did not. Caught by
    # noticing the 20-board localization's own summary line: "mean fw-offline diff imm1
    # base=+0.0 tuck=-308.5" -- imm1 matched EXACTLY for base (no colour involved beyond
    # the already-converted S_CA/S_CB) but was systematically wrong for tuck, the
    # signature of the tuck's placed cells resolving under the WRONG colour and
    # therefore not clearing when the (correctly-computed) offline model said they
    # should.
    cpu2.mem[TV.LA_CA] = tuck_ta - 1
    cpu2.mem[TV.LA_CB] = tuck_tb - 1
    cpu2.call(RUN_RESOLVE_ADDR, max_steps=200_000)
    cpu2.call(RUN_SCORE_ADDR, max_steps=3_000_000_000)
    t_i1 = _s16(cpu2.mem[D3.D_I1L], cpu2.mem[D3.D_I1H])
    t_l1 = _s16(cpu2.mem[D3.D_L1L], cpu2.mem[D3.D_L1H])
    t_b2 = _s16(cpu2.mem[D3.D_B2L], cpu2.mem[D3.D_B2H])
    t_ad = _s16(cpu2.mem[D3.D_ADL], cpu2.mem[D3.D_ADH])
    t_v1 = _s16(cpu2.mem[D3.D_V1L], cpu2.mem[D3.D_V1H])
    tuck_comp = {"imm1": t_i1, "leaf1": t_l1, "best2_raw": t_b2, "blend": t_v1 - t_i1 - t_ad,
                 "eh": t_ad, "total": t_v1}

    return match, tuck_comp, base_agrees
