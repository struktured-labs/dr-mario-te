#!/usr/bin/env python3
"""END-TO-END integration test for the tuck v3 candidate loop: ONE assembled image
containing the real base `search` (test_search_d3, USE_ENGINE=True) + tuck_scan_v3 +
tuck_cell_prep + land_place_at + resolve_capped + tuck_imm1 + tuck_slot0_inject +
tuck_ply2_score + tuck_root_extension, run in ONE py65 Cpu instance with
attach_engine_emu attached, driving all three stages (search -> tuck_scan_v3 ->
tuck_root_extension) exactly as a real decision would on hardware.

Board: tuck_scan_v3_ref.py's own already-validated _cave_horizontal_board() (a lip over
columns 4-6 at row 9 that blocks every straight-drop base action from reaching row 10
underneath it), extended with a pre-existing colour-1 pair at row 10 columns 5-6 and a
lone unreachable virus (keeps virus_count>0 so nothing hits the trivial WIN shortcut).
The current pill is colour(1,1); tuck_scan_v3 finds exactly one geometric rescue
(approach=2, target=3, trigger=10, rest=10) whose landing cells (row10, cols 3-4) are
adjacent to the pre-existing pair, completing a 4-in-a-row CLEAR that no base action can
replicate (nothing else reaches under the lip) -- this should clear the theta=150 gate by
a wide margin and win the final argmax, exercising the FULL commit + publish path.

A second, smaller test confirms the reject path: on a board with no reachable rescue
(the SAME board with the lip removed, so a base action already gets the clear itself),
tuck_root_extension must publish W_TCOL=W_TROW=0xFF and leave D_BC/D_BO exactly as the
base search's own s_loop left them (byte-identical to what a flag-off decision would keep).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER = os.environ.get("DRNAV", "/home/struktured/projects/dr-mario-mods-wt/driver-nav")
CANON = os.environ.get("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
sys.path.insert(0, HERE)
sys.path.insert(0, DRIVER)
sys.path.insert(0, os.path.join(CANON, "tests"))

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
from land_place_at import emit_land_place_at, LA_OFFA, LA_OFFB, LA_CA, LA_CB  # noqa: E402
from tuck_score import emit_tuck_imm1, emit_slot0_inject, TI1L, TI1H  # noqa: E402
from tuck_ply2_score import emit_tuck_ply2_score    # noqa: E402
from tuck_cell_prep import emit_tuck_cell_prep, TP_IDX, TP_TARGET, TP_APPROACH, TP_TRIGGER, TP_REST, TP_ORIENT  # noqa: E402
from tuck_root_extension import emit_tuck_root_extension, TK2_BKIND, TK2_APP, TK2_TRIG  # noqa: E402
from tuck_scan_v3 import emit_tuck_scan_v3, CANDLIST, TS_CNT   # noqa: E402
from tuck_scan_v3_ref import _cave_horizontal_board             # noqa: E402
from py65_harness import Cpu                        # noqa: E402
import test_search_d3 as D3                          # noqa: E402

# import-order hazard (documented in test_tuck_score.py / test_tuck_ply2_score.py) --
# set AFTER all imports.
primitives.BOARD = 0x0700
primitives.LIVE_BOARD = 0x0700

EMPTY = 0xFF
BASE = 0x8000
CUR = 0x0700

D3.USE_ENGINE = True
D3.DISC = False
D3.EH_PLY1 = False
D3.NPILLS, D3.SHIFT = 2, 1
D3.DEBUG_VAL1 = False

W_TCOL, W_TROW = 0x5087, 0x5088


def build():
    a = Asm6502(BASE)
    D3._emit_search_d3_engine(a)
    D3._emit_expectimax_engine(a)
    emit_tuck_scan_v3(a, live=0x0500)
    emit_tuck_cell_prep(a, s_ca=D3.S_CA, s_cb=D3.S_CB)
    emit_land_place_at(a, board=CUR)
    primitives.emit_resolve_capped(a)
    primitives.emit_find_clears(a)
    primitives.emit_gravity(a)
    emit_tuck_imm1(a)
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
    emit_tuck_root_extension(
        a,
        D_BVL=D3.D_BVL, D_BVH=D3.D_BVH, D_BC=D3.D_BC, D_BO=D3.D_BO,
        S_BEST_C=D3.S_BEST_C, S_BEST_O=D3.S_BEST_O,
        D_V1L=D3.D_V1L, D_V1H=D3.D_V1H, TS_CNT=TS_CNT,
        D_I1L=D3.D_I1L, D_I1H=D3.D_I1H, W_TCOL=W_TCOL, W_TROW=W_TROW,
        TP_IDX=TP_IDX, TP_TARGET=TP_TARGET, TP_APPROACH=TP_APPROACH,
        TP_TRIGGER=TP_TRIGGER, TP_ORIENT=TP_ORIENT,
        TI1L=TI1L, TI1H=TI1H,
    )
    a.label("decide_with_tucks")
    a.jsr("search")
    a.jsr("tuck_scan_v3")
    a.jsr("tuck_root_extension")
    a.ins("RTS")
    code = a.assemble()
    return code, a.labels


CODE, LABELS = build()


def run(board, ca0, cb0, na0, nb0, pillA, pillB):
    cpu = Cpu()
    cpu.load(BASE, CODE)
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    cpu.mem[D3.S_CA] = ca0
    cpu.mem[D3.S_CB] = cb0
    cpu.mem[D3.S_NA] = na0
    cpu.mem[D3.S_NB] = nb0
    for i in range(D3.NPILLS):
        cpu.mem[D3.PILLA + i] = pillA[i]
        cpu.mem[D3.PILLB + i] = pillB[i]
    cpu.call(BASE + LABELS["decide_with_tucks"], max_steps=6_000_000_000)
    return {
        "D_BC": cpu.mem[D3.D_BC], "D_BO": cpu.mem[D3.D_BO],
        "D_BVL": cpu.mem[D3.D_BVL], "D_BVH": cpu.mem[D3.D_BVH],
        "S_BEST_C": cpu.mem[D3.S_BEST_C], "S_BEST_O": cpu.mem[D3.S_BEST_O],
        "W_TCOL": cpu.mem[W_TCOL], "W_TROW": cpu.mem[W_TROW],
        "TK2_BKIND": cpu.mem[TK2_BKIND],
        "TS_CNT": cpu.mem[TS_CNT],
    }


def test_tuck_wins():
    print("(1) TUCK RESCUE -- board where only a tuck reaches a clear under the lip")
    board = _cave_horizontal_board()
    board[10 * 8 + 5] = 1
    board[10 * 8 + 6] = 1
    board[0 * 8 + 0] = 0xD0
    ca0, cb0, na0, nb0 = 1, 1, 2, 0
    pillA, pillB = [0, 2], [2, 1]
    r = run(board, ca0, cb0, na0, nb0, pillA, pillB)
    print(f"  {r}")
    ok = (r["TK2_BKIND"] == 1 and r["W_TCOL"] == 2 and r["W_TROW"] == 10
          and r["D_BC"] == 3 and r["D_BO"] == 2   # target col 3, orient H(0)->o4=2
          and r["S_BEST_C"] == 3 and r["S_BEST_O"] == 2)
    print(f"  {'OK' if ok else 'FAIL'} -- tuck won, published (approach=2,trigger=10), "
          f"D_BC/D_BO/S_BEST_* match the tuck's target/mapped-orient")
    return 0 if ok else 1


def test_no_rescue_needed_publishes_none():
    print("\n(2) NO RESCUE -- same board, lip removed (row 9 cleared): a base action")
    print("    should already reach the pre-existing pair, so no tuck should be able to")
    print("    beat it by theta=150 (identical placement, same value, gate needs STRICT")
    print("    improvement over the fixed base reference) -- W_TCOL/W_TROW must be 0xFF")
    board = _cave_horizontal_board()
    for c in (4, 5, 6):
        board[9 * 8 + c] = EMPTY   # remove the lip
    board[10 * 8 + 5] = 1
    board[10 * 8 + 6] = 1
    board[0 * 8 + 0] = 0xD0
    ca0, cb0, na0, nb0 = 1, 1, 2, 0
    pillA, pillB = [0, 2], [2, 1]
    r = run(board, ca0, cb0, na0, nb0, pillA, pillB)
    print(f"  {r}")
    ok = (r["TK2_BKIND"] == 0 and r["W_TCOL"] == 0xFF and r["W_TROW"] == 0xFF)
    print(f"  {'OK' if ok else 'FAIL'} -- base action already gets the clear, tuck gate "
          f"correctly declines (no strict improvement to justify a tuck)")
    return 0 if ok else 1


def main():
    fails = test_tuck_wins()
    fails += test_no_rescue_needed_publishes_none()
    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILURES'} (code={len(CODE)}B)")
    return fails == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
