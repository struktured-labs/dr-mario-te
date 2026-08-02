#!/usr/bin/env python3
"""VALUE-EQUIVALENCE DIFFERENTIAL GATE for the FULL depth-3 value (extends
test_tuck_score.py's imm1-only gate to D_V1L/D_V1H, i.e. through the duplicated ply-2
loop in tuck_ply2_score.py): construct a tuck candidate whose rest cells exactly equal a
base ply-1 action's resting placement, on a board open enough that the ply-2 exploration
actually exercises the top-K2=8 selection + expectimax path (D_TKC==32, not the trivial
D_TKC==0 shortcut -- the real risk is in the duplicated k_loop/mx/expectimax logic, so a
test that never reaches it would not be a meaningful gate).

Ground truth: the REAL `search` routine (test_search_d3._emit_search_d3_engine, USE_ENGINE
=True) run via attach_engine_emu, with DEBUG_VAL1=True so every ply-1 candidate's
(C1,O1,V1L,V1H) is dumped to DBG_RING -- scanned for the entry matching the SAME (C1,O1)
the tuck candidate's cells correspond to. DISC=False, EH_PLY1=False for this first cut
(matches tuck_ply2_score.py's own documented scope -- EH_PLY1 integration is a separate,
already-flagged deferred item).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER = os.environ.get("DRNAV", "/home/struktured/projects/dr-mario-mods-wt/driver-nav")
CANON = os.environ.get("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
sys.path.insert(0, HERE)
sys.path.insert(0, DRIVER)
sys.path.insert(0, os.path.join(CANON, "tests"))

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
from land_place_at import emit_land_place_at, cell_offsets, LA_OFFA, LA_OFFB, LA_CA, LA_CB  # noqa: E402
from tuck_score import emit_tuck_imm1, emit_slot0_inject, TI1L, TI1H  # noqa: E402
from tuck_ply2_score import emit_tuck_ply2_score   # noqa: E402
from py65_harness import Cpu                       # noqa: E402
import test_search_d3 as D3                        # noqa: E402
from nes_d2_golden import _landing                  # noqa: E402

# same import-order hazard documented in test_tuck_score.py -- set AFTER all imports.
primitives.BOARD = 0x0700
primitives.LIVE_BOARD = 0x0700

EMPTY = 0xFF
BASE = 0x8000
CUR = 0x0700

# ---- ground-truth search config: full depth-3, DISC/EH_PLY1 off (matches tuck_ply2_score's
# documented scope), small NPILLS/SHIFT so the differential run is fast, DEBUG_VAL1 on so
# per-candidate (C1,O1,V1L,V1H) is observable. ----
D3.USE_ENGINE = True
D3.DISC = False
D3.EH_PLY1 = False
D3.NPILLS, D3.SHIFT = 2, 1
D3.DEBUG_VAL1 = True

D3_CODE, D3_LABELS = D3.build()


def build_tuck_resolve():
    a = Asm6502(BASE)
    emit_land_place_at(a, board=CUR)
    primitives.emit_resolve_capped(a)
    primitives.emit_find_clears(a)
    primitives.emit_gravity(a)
    emit_tuck_imm1(a)
    a.label("resolve_full")
    a.jsr("land_place_at")
    a.jsr("resolve_capped")
    a.jsr("tuck_imm1")
    a.ins("RTS")
    code = a.assemble()
    return code, a.labels


def build_tuck_score():
    a = Asm6502(BASE)
    emit_slot0_inject(a, board=CUR, dest_slot=2, leaf1_lo=D3.D_L1L, leaf1_hi=D3.D_L1H)
    emit_tuck_ply2_score(
        a,
        D_C2=D3.D_C2, D_O2=D3.D_O2, D_TKC=D3.D_TKC, D_J=D3.D_J,
        D_MKL=D3.D_MKL, D_MKH=D3.D_MKH, D_MI=D3.D_MI, D_B2L=D3.D_B2L, D_B2H=D3.D_B2H,
        D_I1L=D3.D_I1L, D_I1H=D3.D_I1H, D_I2L=D3.D_I2L, D_I2H=D3.D_I2H,
        D_L1L=D3.D_L1L, D_L1H=D3.D_L1H, D_V1L=D3.D_V1L, D_V1H=D3.D_V1H,
        D_V3L=D3.D_V3L, D_V3H=D3.D_V3H, D_EL=D3.D_EL, D_EH=D3.D_EH,
        S_NA=D3.S_NA, S_NB=D3.S_NB,
        TK_KL=D3.TK_KL, TK_KH=D3.TK_KH, TK_O=D3.TK_O, TK_C=D3.TK_C,
        TK_IL=D3.TK_IL, TK_IH=D3.TK_IH,
        LEV_LEGAL=D3.LEV_LEGAL, LEV_IMM=D3.LEV_IMM, LEV_WIN_R=D3.LEV_WIN_R,
        LEV_CMD=D3.LEV_CMD,
        WIN=D3.WIN, DISC=D3.DISC,
        _e_copy=D3._e_copy, _e_node=D3._e_node, _e_score=D3._e_score, _e_poll=D3._e_poll,
    )
    D3._emit_expectimax_engine(a)     # so tuck_ply2_score's k_ex JSR resolves
    a.label("tuck_full")
    a.jsr("tuck_slot0_inject")
    a.jsr("tuck_ply2_score")
    a.ins("RTS")
    code = a.assemble()
    return code, a.labels


TUCK_A_CODE, TUCK_A_LABELS = build_tuck_resolve()
TUCK_B_CODE, TUCK_B_LABELS = build_tuck_score()


def _blank():
    return [EMPTY] * 128


def run_base_search(board, ca0, cb0, na0, nb0, pillA, pillB):
    cpu = Cpu()
    cpu.load(BASE, D3_CODE)
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


def run_tuck_score(board, offa, offb, ta, tb, na0, nb0, pillA, pillB):
    # ---- phase A: resolve (plain Cpu) ----
    cpu_a = Cpu()
    cpu_a.load(BASE, TUCK_A_CODE)
    for i, v in enumerate(board):
        cpu_a.mem[CUR + i] = v
    cpu_a.mem[LA_OFFA] = offa
    cpu_a.mem[LA_OFFB] = offb
    cpu_a.mem[LA_CA] = ta
    cpu_a.mem[LA_CB] = tb
    cpu_a.call(BASE + TUCK_A_LABELS["resolve_full"], max_steps=200000)
    imm1 = cpu_a.mem[TI1L] | (cpu_a.mem[TI1H] << 8)
    resolved_board = [cpu_a.mem[CUR + i] for i in range(128)]

    # ---- phase B: inject + duplicate ply-2 score (Cpu with attach_engine_emu) ----
    cpu_b = Cpu()
    cpu_b.load(BASE, TUCK_B_CODE)
    D3.attach_engine_emu(cpu_b)
    for i, v in enumerate(resolved_board):
        cpu_b.mem[CUR + i] = v
    cpu_b.mem[D3.S_NA] = na0
    cpu_b.mem[D3.S_NB] = nb0
    for i in range(D3.NPILLS):
        cpu_b.mem[D3.PILLA + i] = pillA[i]
        cpu_b.mem[D3.PILLB + i] = pillB[i]
    cpu_b.mem[D3.D_I1L] = imm1 & 0xFF
    cpu_b.mem[D3.D_I1H] = (imm1 >> 8) & 0xFF
    cpu_b.call(BASE + TUCK_B_LABELS["tuck_full"], max_steps=3_000_000_000)
    v1l, v1h = cpu_b.mem[D3.D_V1L], cpu_b.mem[D3.D_V1H]
    v1 = v1l | (v1h << 8)
    if v1h >= 0x80:
        v1 -= 0x10000
    return v1, imm1, cpu_b.mem[D3.D_TKC]


def test_open_board_full_ply2():
    print("(1) OPEN BOARD -- full ply-2 (D_TKC should be 32), vertical ply-1 candidate")
    board = _blank()
    # a lone virus, far from column 4 and unreachable by a 2-cell pill placement (top-left
    # corner) -- keeps virus_count > 0 after every candidate placement tested here, so the
    # WIN short-circuit (both paths trivially agree at V1=imm1+WIN, never touching ply-2)
    # does NOT fire and the ply-2/expectimax loop actually runs, which is the point of
    # this test.
    board[0 * 8 + 0] = 0xD0
    o1, c1 = 1, 4                       # vertical (o4=1), column 4
    ca0, cb0, na0, nb0 = 0, 1, 2, 0
    pillA, pillB = [1, 2], [0, 1]

    ring, t1c = run_base_search(board, ca0, cb0, na0, nb0, pillA, pillB)
    print(f"  base search: D_T1C={t1c} (the lone virus tile blocks a few of the 32 raw "
          f"ply-1 actions, so <32 legal is expected and NOT a bug)")
    match = [(j1, v1) for j1, (c1r, o1r, v1) in enumerate(ring) if c1r == c1 and o1r == o1]
    assert match, f"no DBG_RING entry found for (C1={c1},O1={o1}) among {ring}"
    j1, base_v1 = match[0]
    print(f"  base candidate (C1={c1},O1={o1}) found at D_J1={j1}: V1={base_v1}")

    orient = 0 if o1 < 2 else 1
    offa, offb = _landing(board, orient, c1)
    assert offa is not None, "landing failed on an open board -- test setup bug"
    ta, tb = (cb0, ca0) if (o1 & 1) else (ca0, cb0)
    tuck_v1, imm1, tkc = run_tuck_score(board, offa, offb, ta, tb, na0, nb0, pillA, pillB)
    print(f"  tuck candidate (offa={offa},offb={offb},ta={ta},tb={tb}): "
          f"imm1={imm1} D_TKC={tkc} V1={tuck_v1}")

    # D_TKC > 8 confirms the top-K2=8 mx-selection loop actually had to select among more
    # candidates than it keeps (the real risk surface -- a test where D_TKC<=8 would never
    # exercise the "evict the current min" branch of the mx loop). The real assertion is
    # V1 bit-exact equality against the ground-truth base search.
    ok = (tkc > 8) and (base_v1 == tuck_v1)
    print(f"  {'OK' if ok else 'FAIL'} -- D_TKC={tkc} > 8 (mx-selection exercised) AND "
          f"V1 bit-exact match")
    return 0 if ok else 1


def test_open_board_full_ply2_horizontal():
    print("\n(2) OPEN BOARD -- horizontal ply-1 candidate, different column, different pills")
    board = _blank()
    board[0 * 8 + 7] = 0xD2   # virus colour 2, top-right corner this time
    o1, c1 = 2, 1              # horizontal (o4=2, "H, A-left"), column 1
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
    tuck_v1, imm1, tkc = run_tuck_score(board, offa, offb, ta, tb, na0, nb0, pillA, pillB)
    print(f"  tuck candidate (offa={offa},offb={offb},ta={ta},tb={tb}): "
          f"imm1={imm1} D_TKC={tkc} V1={tuck_v1}")

    ok = (tkc > 8) and (base_v1 == tuck_v1)
    print(f"  {'OK' if ok else 'FAIL'} -- D_TKC={tkc} > 8 (mx-selection exercised) AND "
          f"V1 bit-exact match")
    return 0 if ok else 1


def main():
    fails = test_open_board_full_ply2()
    fails += test_open_board_full_ply2_horizontal()
    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILURES'}")
    return fails == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
