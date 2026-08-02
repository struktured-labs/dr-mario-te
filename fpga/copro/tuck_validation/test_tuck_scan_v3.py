#!/usr/bin/env python3
"""6502 vs python reference for tuck_scan_v3 -- "the 6502 must agree with this cell-for-
cell" (tuck_scan.py's own standing rule for v1, applied here to v3).

Assembles emit_tuck_scan_v3 in isolation (no search, no driver), pokes a test board into
`live`, runs it in py65, reads back the candidate list + count + drop counter, and diffs
against tuck_scan_v3_ref.ref_tuck_scan_v3 -- same board, same insertion-order contract.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER = os.environ.get("DRNAV", "/home/struktured/projects/dr-mario-mods-wt/driver-nav")
CANON = os.environ.get("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
sys.path.insert(0, HERE)
sys.path.insert(0, DRIVER)
sys.path.insert(0, CANON)
sys.path.insert(0, os.path.join(CANON, "fpga", "copro"))

from py65.devices.mpu6502 import MPU          # noqa: E402
from patch_vs_cpu import Asm6502               # noqa: E402
import patch_vs_cpu                            # noqa: E402
patch_vs_cpu.OPS.setdefault("CLD", 0xD8)

from tuck_scan import ROWS, COLS, EMPTY        # noqa: E402
from tuck_scan_v3 import emit_tuck_scan_v3, CANDLIST, CAPACITY, TS_CNT, TS_DROP  # noqa: E402
from tuck_scan_v3_ref import ref_tuck_scan_v3  # noqa: E402

BASE = 0x8000
LIVE = 0x0500


def build():
    a = Asm6502(BASE)
    emit_tuck_scan_v3(a, live=LIVE)
    code = a.assemble()
    return code, a.labels


CODE, LABELS = build()


def run_v3(board):
    mpu = MPU()
    mem = [0] * 0x10000
    mpu.memory = mem
    for i, v in enumerate(CODE):
        mem[BASE + i] = v
    for i, v in enumerate(board):
        mem[LIVE + i] = v
    SENT = 0x400
    mpu.sp = 0xFD
    mem[0x100 + mpu.sp] = ((SENT - 1) >> 8) & 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF
    mem[0x100 + mpu.sp] = (SENT - 1) & 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF
    mpu.pc = BASE + LABELS["tuck_scan_v3"]
    k = 0
    while mpu.pc != SENT and k < 200000:
        mpu.step()
        k += 1
    assert mpu.pc == SENT, f"routine did not return in 200000 steps (pc={mpu.pc:#06x})"
    cnt = mem[TS_CNT]
    drop = mem[TS_DROP]
    cands = []
    for i in range(cnt):
        base = CANDLIST + i * 5
        cands.append({"target": mem[base], "approach": mem[base + 1],
                      "trigger": mem[base + 2], "rest": mem[base + 3],
                      "orient": mem[base + 4]})
    return cands, drop


def _blank():
    return [EMPTY] * (ROWS * COLS)


def _mark(b, r, c, v=1):
    b[r * COLS + c] = v


def _board_overhang_c0():
    b = _blank(); _mark(b, 8, 0); return b


def _board_pocket():
    b = _blank(); _mark(b, 9, 3); _mark(b, 11, 3)
    for r in range(12, ROWS):
        for c in range(COLS):
            _mark(b, r, c)
    return b


def _board_misland():
    b = _blank(); _mark(b, 2, 0); _mark(b, 8, 1); return b


def _board_worstcase():
    b = _blank()
    for c in (0, 2, 4, 6):
        _mark(b, 1, c)
    return b


def _board_two_deep():
    b = _blank()
    b[6 * COLS + 0] = 1
    for r in range(9, ROWS):
        b[r * COLS + 0] = 2
    return b


def _cave_horizontal_board():
    b = _blank()
    for c in (4, 5, 6):
        _mark(b, 9, c)
    for c in range(COLS):
        _mark(b, 11, c, 2)
        for r in (12, 13, 14, 15):
            _mark(b, r, c, 3)
    return b


def main():
    boards = [
        ("empty", _blank()),
        ("overhang c0", _board_overhang_c0()),
        ("pocket", _board_pocket()),
        ("mis-land", _board_misland()),
        ("worst-case", _board_worstcase()),
        ("two-deep pocket", _board_two_deep()),
        ("cave horizontal", _cave_horizontal_board()),
    ]
    import random
    rnd = random.Random(20260802)
    for i in range(60):
        b = [EMPTY] * (ROWS * COLS)
        for c in range(COLS):
            h = rnd.randrange(0, ROWS + 1)
            for r in range(ROWS - h, ROWS):
                b[r * COLS + c] = rnd.randint(1, 3)
        for _ in range(rnd.randrange(0, 16)):
            b[rnd.randrange(1, ROWS) * COLS + rnd.randrange(0, COLS)] = EMPTY
        boards.append((f"random-{i}", b))

    fails = 0
    for name, board in boards:
        got, got_drop = run_v3(board)
        exp, exp_drop = ref_tuck_scan_v3(board, capacity=CAPACITY)
        ok = got == exp and got_drop == exp_drop
        tag = "PASS" if ok else "FAIL"
        print(f"  [{tag}] {name:<20} 6502: {len(got)} cands, drop={got_drop}   "
              f"ref: {len(exp)} cands, drop={exp_drop}")
        if not ok:
            fails += 1
            for i, (g, e) in enumerate(zip(got, exp)):
                if g != e:
                    print(f"      first diff at index {i}: 6502={g} ref={e}")
                    break
            if len(got) != len(exp):
                print(f"      length mismatch: 6502={len(got)} ref={len(exp)}")

    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILURES'} "
          f"({len(boards)} boards, code={len(CODE)}B)")
    return fails == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
