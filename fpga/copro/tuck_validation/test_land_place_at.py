#!/usr/bin/env python3
"""land_place_at unit + integration test. Unit: writes the right cells with the right
tile-flag, sets Z_OFFA/Z_OFFB correctly, for both orientations. Integration: chained with
the REAL resolve_capped (primitives.py, unmodified) to confirm a tuck placement that
completes a 4-in-a-row actually clears -- proving land_place_at's output is consumable by
the existing resolve pipeline, not just structurally plausible in isolation.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER = os.environ.get("DRNAV", "/home/struktured/projects/dr-mario-mods-wt/driver-nav")
CANON = os.environ.get("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
sys.path.insert(0, HERE)
sys.path.insert(0, DRIVER)
sys.path.insert(0, os.path.join(CANON, "tests"))

from py65.devices.mpu6502 import MPU           # noqa: E402
from patch_vs_cpu import Asm6502                # noqa: E402
import patch_vs_cpu                             # noqa: E402
patch_vs_cpu.OPS.setdefault("CLD", 0xD8)

import primitives                               # noqa: E402
primitives.BOARD = 0x0500
primitives.LIVE_BOARD = 0x0500
from land_place_at import emit_land_place_at, cell_offsets, LA_OFFA, LA_OFFB, LA_CA, LA_CB  # noqa: E402

EMPTY = 0xFF
BASE = 0x8000
BOARD = 0x0500


def build():
    a = Asm6502(BASE)
    emit_land_place_at(a, board=BOARD)
    primitives.emit_resolve_capped(a)
    primitives.emit_find_clears(a)   # find_clears_targeted lives here
    primitives.emit_gravity(a)
    code = a.assemble()
    return code, a.labels


CODE, LABELS = build()


def run(board, offa, offb, ca, cb, call_label):
    mpu = MPU()
    mem = [0] * 0x10000
    mpu.memory = mem
    for i, v in enumerate(CODE):
        mem[BASE + i] = v
    for i, v in enumerate(board):
        mem[BOARD + i] = v
    mem[LA_OFFA] = offa
    mem[LA_OFFB] = offb
    mem[LA_CA] = ca
    mem[LA_CB] = cb
    SENT = 0x400
    mpu.sp = 0xFD
    mem[0x100 + mpu.sp] = ((SENT - 1) >> 8) & 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF
    mem[0x100 + mpu.sp] = (SENT - 1) & 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF
    mpu.pc = BASE + LABELS[call_label]
    k = 0
    while mpu.pc != SENT and k < 100000:
        mpu.step()
        k += 1
    assert mpu.pc == SENT, f"{call_label} did not return (pc={mpu.pc:#06x})"
    return mem


def test_unit():
    print("(1) UNIT -- land_place_at writes the right cells + Z_OFFA/Z_OFFB")
    fails = 0
    board = [EMPTY] * 128
    offa, offb, ca, cb = 10, 11, 1, 2
    mem = run(board, offa, offb, ca, cb, "land_place_at")
    ok = (mem[BOARD + offa] == (0x40 | ca) and mem[BOARD + offb] == (0x40 | cb)
          and mem[0xDC] == offa and mem[0xDE] == offb)
    print(f"  horizontal-style offsets: cell[{offa}]={mem[BOARD+offa]:#04x} "
          f"cell[{offb}]={mem[BOARD+offb]:#04x} Z_OFFA={mem[0xDC]} Z_OFFB={mem[0xDE]}  "
          f"{'OK' if ok else 'FAIL'}")
    if not ok:
        fails += 1

    # vertical-style offsets (offb = offa + 8), and confirm cells OUTSIDE the pair are
    # untouched (only 2 bytes of the 128-byte board should change)
    board2 = [3] * 128   # everything else filled with colour 3, to catch stray writes
    offa2, offb2 = 20, 28
    mem2 = run(board2, offa2, offb2, 0, 1, "land_place_at")
    untouched = all(mem2[BOARD + i] == 3 for i in range(128) if i not in (offa2, offb2))
    ok2 = (mem2[BOARD + offa2] == (0x40 | 0) and mem2[BOARD + offb2] == (0x40 | 1)
          and untouched)
    print(f"  vertical-style offsets, stray-write check: {'OK' if ok2 else 'FAIL'}")
    if not ok2:
        fails += 1
    return fails


def test_integration_clear_chained():
    print("\n(2) INTEGRATION -- land_place_at THEN resolve_capped (chained, as the real")
    print("    scoring loop will call them): a tuck that completes a 4-in-a-row clears")
    board = [EMPTY] * 128
    color = 1
    for c in range(3):
        board[5 * 8 + c] = color
    board[5 * 8 + 4] = 2
    offa, offb = 5 * 8 + 3, 5 * 8 + 4

    # build a combined image: land_place_at, then jsr resolve_capped, then RTS
    a = Asm6502(BASE)
    emit_land_place_at(a, board=BOARD)
    a.label("chained")
    a.jsr("land_place_at")
    a.jsr("resolve_capped")
    a.ins("RTS")
    primitives.emit_resolve_capped(a)
    primitives.emit_find_clears(a)
    primitives.emit_gravity(a)
    code = a.assemble()
    labels = a.labels

    mpu = MPU()
    mem = [0] * 0x10000
    mpu.memory = mem
    for i, v in enumerate(code):
        mem[BASE + i] = v
    for i, v in enumerate(board):
        mem[BOARD + i] = v
    mem[LA_OFFA] = offa
    mem[LA_OFFB] = offb
    mem[LA_CA] = color
    mem[LA_CB] = 2
    SENT = 0x400
    mpu.sp = 0xFD
    mem[0x100 + mpu.sp] = ((SENT - 1) >> 8) & 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF
    mem[0x100 + mpu.sp] = (SENT - 1) & 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF
    mpu.pc = BASE + labels["chained"]
    k = 0
    while mpu.pc != SENT and k < 100000:
        mpu.step()
        k += 1
    rv_cells, rv_vir = mem[0xE0], mem[0xE1]
    cleared = mem[BOARD + 5 * 8 + 0] == EMPTY   # the run's cells should be gone post-clear
    print(f"  RV_CELLS={rv_cells} RV_VIR={rv_vir} row-5-col-0 now empty: {cleared}")
    ok = rv_cells == 4 and cleared
    print(f"  {'OK' if ok else 'FAIL'} (expected RV_CELLS=4, a clean horizontal 4-run,"
          f" 0 viruses)")
    return 0 if ok else 1


def main():
    fails = test_unit()
    fails += test_integration_clear_chained()
    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILURES'} (code={len(CODE)}B)")
    return fails == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
