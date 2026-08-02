#!/usr/bin/env python3
"""VALUE-EQUIVALENCE DIFFERENTIAL GATE for the FULL depth-3 value (extends
test_tuck_score.py's imm1-only gate to D_V1L/D_V1H, i.e. through the duplicated ply-2
loop): construct a tuck candidate whose rest cells exactly equal a base ply-1 action's
resting placement, on a board open enough that the ply-2 exploration actually exercises
the top-K2=8 selection + expectimax path (D_TKC > 8, not the trivial D_TKC==0 shortcut --
the real risk is in the duplicated k_loop/mx/expectimax logic, so a test that never
reaches it would not be a meaningful gate).

PROMOTED TO EH_PLY1=True (the real, shipped config -- team-lead ruling, task #17 stage 3):
this now imports and tests fpga/copro/tuck_v3.py DIRECTLY (the canonical repo's real
integration, including the cp_live_cur fix) instead of the qa-harness scratch tuck_ply2_
score.py/tuck_score.py modules, which never got the eh add-on wired in at all (no D_ADL/
D_ADH parameters exist in their signatures -- confirmed before this rewrite, not assumed)
and would have silently diverged further from the real firmware every time canonical
tuck_v3.py changes. Testing the actual shipped module directly, with the actual shipped
config (EH_PLY1=True + the R47b5 nes_d3_golden overrides build_copro_d3.build_image() sets
unconditionally), is both simpler and closes the exact ship-config-vs-test-config gap that
let the missing cp_live_cur reset survive the original EH_PLY1=False stage-2 gates.

Ground truth: the REAL `search` routine (test_search_d3._emit_search_d3_engine, USE_ENGINE
=True, EH_PLY1=True) run via attach_engine_emu, with DEBUG_VAL1=True so every ply-1
candidate's (C1,O1,V1L,V1H) is dumped to DBG_RING -- scanned for the entry matching the
SAME (C1,O1) the tuck candidate's cells correspond to. This value now INCLUDES the base
search's own eh_terms add-on (W_EXCAV*excav + W_HANG*hang), so for the comparison to be
meaningful the test board must give a NONZERO eh credit to at least one of the two paths
(a board with zero excav/hang texture would pass trivially even if the eh wiring were
broken) -- both boards below place at least one virus adjacent to matching-colour terrain.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER = os.environ.get("DRNAV", "/home/struktured/projects/dr-mario-mods-wt/driver-nav")
CANON = os.environ.get("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
sys.path.insert(0, HERE)
sys.path.insert(0, DRIVER)
sys.path.insert(0, os.path.join(CANON, "tests"))
sys.path.insert(0, os.path.join(CANON, "fpga", "copro"))

from py65.devices.mpu6502 import MPU             # noqa: E402
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
import test_search_d3 as D3                        # noqa: E402
from nes_d2_golden import _landing                  # noqa: E402
import nes_d3_golden as G3                          # noqa: E402
import tuck_v3 as TV                                # noqa: E402

# same import-order hazard documented throughout this directory -- set AFTER all imports.
primitives.BOARD = 0x0700
primitives.LIVE_BOARD = 0x0700

EMPTY = 0xFF
BASE = 0x8000
CUR = 0x0700

# ---- ground-truth search config: the REAL shipped config (build_copro_d3.build_image's
# own overrides), full depth-3, small NPILLS/SHIFT so the differential run is fast,
# DEBUG_VAL1 on so per-candidate (C1,O1,V1L,V1H) is observable. ----
D3.USE_ENGINE = True
D3.DISC = False
D3.EH_PLY1 = True
D3.NPILLS, D3.SHIFT = 2, 1
D3.DEBUG_VAL1 = True
G3.W_EXCAV = 24
G3.HANG_DEPTH_PROP = True
G3.W_HANG_GAP = 20
G3.HANG_VIRUS_COL_ONLY = True

D3_CODE, D3_LABELS = D3.build()
RESOLVE_CAPPED_ADDR = BASE + D3_LABELS["resolve_capped"]
EXPECTIMAX_ADDR = BASE + D3_LABELS["expectimax"]
EH_TERMS_SCAN_ADDR = BASE + D3_LABELS["eh_terms_scan"]
CP_LIVE_CUR_ADDR = BASE + D3_LABELS["cp_live_cur"]


def build_tuck_score():
    """Assembled AFTER D3_CODE (at BASE+len(D3_CODE)), matching build_copro_d3.py's real
    layout -- cross-image JSRs use the raw addresses computed above."""
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
    tv.jsr(CP_LIVE_CUR_ADDR)          # same reset emit_tuck_root_extension now applies --
                                        # this test places the tuck's cells starting from
                                        # the ORIGINAL board, matching the real loop's
                                        # per-candidate contract, not an arbitrary CUR state.
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


TUCK_CODE, TUCK_LABELS = build_tuck_score()
COMBINED = bytes(D3_CODE) + bytes(TUCK_CODE)
RUN_RESOLVE_ADDR = BASE + len(D3_CODE) + TUCK_LABELS["run_resolve"]
RUN_SCORE_ADDR = BASE + len(D3_CODE) + TUCK_LABELS["run_score"]


def _blank():
    return [EMPTY] * 128


def run_base_search(board, ca0, cb0, na0, nb0, pillA, pillB):
    cpu = Cpu()
    cpu.load(BASE, COMBINED)
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    cpu.mem[D3.S_CA] = ca0
    cpu.mem[D3.S_CB] = cb0
    cpu.mem[D3.S_NA] = na0
    cpu.mem[D3.S_NB] = nb0
    for i in range(D3.NPILLS):
        cpu.mem[D3.PILLA + i] = pillA[i]
        cpu.mem[D3.PILLB + i] = pillB[i]
    cpu.call(BASE + D3_LABELS["search"], max_steps=3_000_000_000)
    ring = []
    for j1 in range(32):
        off = D3.DBG_RING + j1 * 8
        c1, o1 = cpu.mem[off + 0], cpu.mem[off + 1]
        v1l, v1h = cpu.mem[off + 2], cpu.mem[off + 3]
        ring.append((c1, o1, v1l | (v1h << 8) if v1h < 0x80 else v1l | (v1h << 8) - 0x10000))
    return ring, cpu.mem[D3.D_T1C]


def run_tuck_score(board, offa, offb, ta, tb, na0, nb0, pillA, pillB, ca0, cb0):
    # ONE cpu instance, ONE combined image -- exercises the SAME LIVE/CUR relationship the
    # real tuck_root_extension loop does (cp_live_cur resets CUR from LIVE before
    # land_place_at), by first running `search` (so CUR ends up in the same "dirtied by
    # the base search's own eh rebuilds" state the real pipeline leaves it in), THEN the
    # tuck's own resolve+score sequence -- matching build_copro_d3.py's real call order
    # (search returns, THEN tuck_v3's entry runs) rather than an isolated re-run that
    # skips exactly the interaction the cp_live_cur bug was hiding in.
    cpu = Cpu()
    cpu.load(BASE, COMBINED)
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    cpu.mem[D3.S_CA] = ca0
    cpu.mem[D3.S_CB] = cb0
    cpu.mem[D3.S_NA] = na0
    cpu.mem[D3.S_NB] = nb0
    for i in range(D3.NPILLS):
        cpu.mem[D3.PILLA + i] = pillA[i]
        cpu.mem[D3.PILLB + i] = pillB[i]
    cpu.call(BASE + D3_LABELS["search"], max_steps=3_000_000_000)

    cpu.mem[TV.LA_OFFA] = offa
    cpu.mem[TV.LA_OFFB] = offb
    cpu.mem[TV.LA_CA] = ta
    cpu.mem[TV.LA_CB] = tb
    cpu.call(RUN_RESOLVE_ADDR, max_steps=200000)
    imm1 = cpu.mem[TV.TI1L] | (cpu.mem[TV.TI1H] << 8)

    cpu.call(RUN_SCORE_ADDR, max_steps=3_000_000_000)
    v1l, v1h = cpu.mem[D3.D_V1L], cpu.mem[D3.D_V1H]
    v1 = v1l | (v1h << 8)
    if v1h >= 0x80:
        v1 -= 0x10000
    return v1, imm1, cpu.mem[D3.D_TKC], cpu.mem[D3.D_ADL] | (cpu.mem[D3.D_ADH] << 8)


def test_open_board_full_ply2():
    print("(1) OPEN BOARD + excavation texture -- full ply-2, vertical ply-1 candidate, EH_PLY1=True")
    board = _blank()
    # a buried virus under a same-colour pile-top in column 4 (classic excavation credit)
    # so the base search's own eh_terms add-on is NONZERO for this candidate -- a board
    # with zero eh texture would pass trivially even with the eh wiring broken.
    board[7 * 8 + 4] = 0x40 | 1
    board[8 * 8 + 4] = 0xD0 | 1
    ca0, cb0, na0, nb0 = 0, 1, 2, 0
    pillA, pillB = [1, 2], [0, 1]
    o1, c1 = 1, 2                       # vertical (o4=1), column 2 (clear of the texture)

    ring, t1c = run_base_search(board, ca0, cb0, na0, nb0, pillA, pillB)
    print(f"  base search: D_T1C={t1c}")
    match = [(j1, v1) for j1, (c1r, o1r, v1) in enumerate(ring) if c1r == c1 and o1r == o1]
    assert match, f"no DBG_RING entry found for (C1={c1},O1={o1}) among {ring}"
    j1, base_v1 = match[0]
    print(f"  base candidate (C1={c1},O1={o1}) found at D_J1={j1}: V1={base_v1}")

    orient = 0 if o1 < 2 else 1
    offa, offb = _landing(board, orient, c1)
    assert offa is not None, "landing failed on an open board -- test setup bug"
    ta, tb = (cb0, ca0) if (o1 & 1) else (ca0, cb0)
    tuck_v1, imm1, tkc, adl_adh = run_tuck_score(board, offa, offb, ta, tb, na0, nb0,
                                                  pillA, pillB, ca0, cb0)
    print(f"  tuck candidate (offa={offa},offb={offb},ta={ta},tb={tb}): "
          f"imm1={imm1} D_TKC={tkc} D_ADL/ADH={adl_adh} V1={tuck_v1}")

    ok = (tkc > 8) and (base_v1 == tuck_v1)
    print(f"  {'OK' if ok else 'FAIL'} -- D_TKC={tkc} > 8 (mx-selection exercised) AND "
          f"V1 bit-exact match (INCLUDING the eh add-on)")
    return 0 if ok else 1


def test_open_board_full_ply2_horizontal():
    print("\n(2) OPEN BOARD + excavation texture -- horizontal ply-1 candidate, EH_PLY1=True")
    board = _blank()
    board[7 * 8 + 4] = 0x40 | 2
    board[8 * 8 + 4] = 0xD0 | 2
    o1, c1 = 2, 0              # horizontal (o4=2, "H, A-left"), column 0
    ca0, cb0, na0, nb0 = 2, 0, 1, 1
    pillA, pillB = [0, 2], [2, 1]

    ring, t1c = run_base_search(board, ca0, cb0, na0, nb0, pillA, pillB)
    print(f"  base search: D_T1C={t1c}")
    match = [(j1, v1) for j1, (c1r, o1r, v1) in enumerate(ring) if c1r == c1 and o1r == o1]
    assert match, f"no DBG_RING entry found for (C1={c1},O1={o1}) among {ring}"
    j1, base_v1 = match[0]
    print(f"  base candidate (C1={c1},O1={o1}) found at D_J1={j1}: V1={base_v1}")

    orient = 0 if o1 < 2 else 1
    offa, offb = _landing(board, orient, c1)
    assert offa is not None, "landing failed -- test setup bug"
    ta, tb = (cb0, ca0) if (o1 & 1) else (ca0, cb0)
    tuck_v1, imm1, tkc, adl_adh = run_tuck_score(board, offa, offb, ta, tb, na0, nb0,
                                                  pillA, pillB, ca0, cb0)
    print(f"  tuck candidate (offa={offa},offb={offb},ta={ta},tb={tb}): "
          f"imm1={imm1} D_TKC={tkc} D_ADL/ADH={adl_adh} V1={tuck_v1}")

    ok = (tkc > 8) and (base_v1 == tuck_v1)
    print(f"  {'OK' if ok else 'FAIL'} -- D_TKC={tkc} > 8 (mx-selection exercised) AND "
          f"V1 bit-exact match (INCLUDING the eh add-on)")
    return 0 if ok else 1


def main():
    fails = test_open_board_full_ply2()
    fails += test_open_board_full_ply2_horizontal()
    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILURES'}")
    return fails == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
