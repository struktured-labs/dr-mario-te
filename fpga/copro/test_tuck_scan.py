#!/usr/bin/env python3
"""Prove the 6502 tuck enumerator agrees with its Python reference, cell-for-cell.

Runs the EMITTED BYTES in py65 over random and structured boards and compares the
published (TUCK_COL, TUCK_ROW) against ref_tuck_scan(). Also asserts the published
descriptor is genuinely EXECUTABLE: the executor's motion must actually land the capsule
deeper than a straight drop, or we would be steering it somewhere the search never scored.
"""
import os, sys, random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, ROOT)

import patch_vs_cpu
patch_vs_cpu.OPS.setdefault("SEI", 0x78)
patch_vs_cpu.OPS.setdefault("TXS", 0x9A)
from patch_vs_cpu import Asm6502
from py65.devices.mpu6502 import MPU
import primitives as P
from tuck_scan import (emit_tuck_scan, ref_tuck_scan, TUCK_COL, TUCK_ROW,
                       ROWS, COLS, EMPTY)

BASE = 0x8000
LIVE = 0x0500


def build():
    a = Asm6502(BASE)
    a.jsr("tuck_scan")
    a.ins("LDA_imm", 1); a.ins16("STA_abs", 0x61FE)     # done flag
    a.label("spin"); a.jmp("spin")
    emit_tuck_scan(a, live=LIVE)
    P.emit_first_occ(a)
    return a.assemble()


def run(code, board):
    m = MPU()
    for i, b in enumerate(code):
        m.memory[BASE + i] = b
    for i, v in enumerate(board):
        m.memory[LIVE + i] = v
    m.memory[TUCK_COL] = 0x5A          # poison, so a no-write is visible
    m.memory[TUCK_ROW] = 0xA5
    m.memory[0x61FE] = 0
    m.pc = BASE
    m.sp = 0xFF
    for _ in range(4_000_000):
        m.step()
        if m.memory[0x61FE] == 1:
            break
    else:
        raise RuntimeError("tuck_scan did not terminate")
    return m.memory[TUCK_COL], m.memory[TUCK_ROW]


def straight_rest(board, c):
    for r in range(ROWS):
        if board[r * COLS + c] != EMPTY:
            return r - 1
    return ROWS - 1


def executable(board, approach, trigger):
    """Does the executor's motion from (approach, trigger) actually reach deeper?

    Reproduces the executor: fall in `approach`, at row `trigger` move to a neighbouring
    column, fall. We accept either neighbour -- the driver takes the destination from
    best_col -- and require the rest to beat that column's straight drop.
    """
    occ = lambda r, c: board[r * COLS + c] != EMPTY
    fa = next((r for r in range(ROWS) if occ(r, approach)), ROWS)
    if trigger > fa - 1:
        return False, "trigger below what the approach column allows"
    for c in (approach - 1, approach + 1):
        if not (0 <= c < COLS) or occ(trigger, c):
            continue
        rf = trigger
        while rf < ROWS - 1 and not occ(rf + 1, c):
            rf += 1
        if rf > straight_rest(board, c):
            return True, ""
    return False, "no neighbour column is reached deeper than its straight drop"


def rand_board(rng, fill):
    b = [EMPTY] * (ROWS * COLS)
    for c in range(COLS):
        h = rng.randint(0, ROWS)
        for r in range(ROWS - h, ROWS):
            if rng.random() < fill:
                b[r * COLS + c] = rng.randint(1, 3)
    # punch overhangs so tucks actually exist
    for _ in range(rng.randint(0, 6)):
        c = rng.randrange(COLS)
        r = rng.randrange(1, ROWS)
        b[r * COLS + c] = EMPTY
        b[(r - 1) * COLS + c] = rng.randint(1, 3)
    return b


def main():
    code = build()
    print(f"tuck_scan emitted: {len(code)} B")
    rng = random.Random(20260731)
    boards = [[EMPTY] * (ROWS * COLS)]                    # empty board -> must be "no tuck"
    boards += [rand_board(rng, f) for f in (0.3,) * 200]
    boards += [rand_board(rng, f) for f in (0.6,) * 200]
    boards += [rand_board(rng, f) for f in (0.85,) * 200]

    mismatch = 0
    unexecutable = 0
    n_tuck = 0
    for i, b in enumerate(boards):
        got = run(code, b)
        exp = ref_tuck_scan(b)
        if got != exp:
            mismatch += 1
            if mismatch <= 3:
                print(f"  ✗ board {i}: 6502 {got} != ref {exp}")
        if got[0] != 0xFF:
            n_tuck += 1
            ok, why = executable(b, got[0], got[1])
            if not ok:
                unexecutable += 1
                if unexecutable <= 3:
                    print(f"  ✗ board {i}: published {got} is NOT executable -- {why}")

    print(f"\nboards            : {len(boards)}")
    print(f"published a tuck  : {n_tuck}")
    print(f"6502 vs reference : {len(boards)-mismatch}/{len(boards)} exact")
    print(f"executable check  : {n_tuck-unexecutable}/{n_tuck} genuinely reachable")
    if mismatch or unexecutable:
        print("\nTUCK SCAN: FAIL")
        return 1
    print("\nTUCK SCAN: PASS (6502 == reference, every published tuck is executable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
