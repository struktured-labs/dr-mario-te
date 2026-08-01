#!/usr/bin/env python3
"""Run the REAL DRTUCK=1 driver bytes against a board and report WHERE THE CAPSULE LANDS.

The enumerator publishes a trigger row in BOARD-ROW units (0 = top, 15 = floor).  The
executor compares it against $0386, which the game stores as 15 - row (confirmed by
meatfighter's DrMarioAI: `y = 15 - readCPU(CURRENT_Y)`).  This harness runs the shipped
driver over a real board under three descriptors -- none / as-published / row-converted --
and reports the landing column against the search's best_col.

Physics: single-cell capsule (the granularity the enumerator itself assumes), L11 rates
from fall_sim.py -- 13 f/row natural, 2 f/row soft-drop, DAS ~1 col / 6 f, spawn col 3.
"""
import os, sys, importlib.util
from py65.devices.mpu6502 import MPU

REPO = "/home/struktured/projects/dr-mario-mods-wt/driver-nav"
DRVDIR = "/tmp/claude-1000/-home-struktured-projects-dr-mario-rl/02493363-c6af-4da9-9c47-58ceef8174b6/scratchpad/tuck/driverfix"
for k in ("DRNOFREEZE", "DRROTFIX", "DRHUMAN", "DRPOCKET", "DRSLAM", "DRNAVFIX", "DRTRACE",
          "DRPROBE", "DRNAV_V4", "DRNAV_HOLD", "DRTUCK", "DRNAVDWELL", "DRRECOMMIT_NOFREEZE"):
    os.environ.pop(k, None)
# shipped cart flags (tools/verify_recommit.py) + the tuck executor
os.environ.update({"DRHUMAN": "1", "DRNAVDWELL": "0", "DRNOFREEZE": "1",
                   "DRPOCKET": "1", "DRRECOMMIT_NOFREEZE": "1", "DRTUCK": "1"})
sys.path.insert(0, REPO)
spec = importlib.util.spec_from_file_location("fs", DRVDIR + "/patch_cartridge_copro.py")
m = importlib.util.module_from_spec(spec); sys.modules["fs"] = m; spec.loader.exec_module(m)
assert m.TUCK, "DRTUCK did not take"
code, lab = m.build_main(11, 1)
rom = open(REPO + "/drmario_v28cs.nes", "rb").read()
prg = rom[4] * 16384
TOG = rom[16 + (prg - 0x4000) + (0xFF30 - 0xC000):][:28]

PX2, PY2, ORI2 = 0x0385, 0x0386, 0x03A5
F6, F8 = 0xF6, 0xF8
ARMED2, MATCH, MAGIC = 0x6161, 0x6164, 0x6149
MODE, Z04 = 0x46, 0x04
VC1, VC2 = 0x0324, 0x03A4
W_DONE, W_COL, W_OR, W_TCOL, W_TROW = 0x5084, 0x5085, 0x5086, 0x5087, 0x5088
TGT_C2, TGT_O2, ROT_DONE2 = 0x6152, 0x6153, 0x616E
WDOG2, WDOGH2 = 0x6162, 0x6166
PEND2, DELAY2, LASTY2 = 0x614F, 0x615F, 0x6155
STK2, STKX2, STKY2 = 0x615B, 0x6159, 0x615A
TUCK_C2, TUCK_R2, EFF_C2 = m.TUCK_C2, m.TUCK_R2, m.EFF_C2
GAMEMAP = {0: 3, 1: 1, 2: 0, 3: 2}
NAT, SOFT, SLIDE_F, X_SPAWN = 13, 2, 6, 3
ROWS, COLS, EMPTY = 16, 8, 0xFF


def occupied(board, r, c):
    return board[r * COLS + c] != EMPTY


def sim(board, best_col, best_orient_raw, tcol, trow, maxf=900, persist=False):
    """tcol/trow = descriptor as the driver will read it.  Returns (landing_col, frames, why).

    persist=True re-asserts TUCK_C2/TUCK_R2 every frame, modelling a driver in which the
    h2_start invalidation does NOT wipe the descriptor during the descent.  With persist
    False the real emitted code is run unmodified.
    """
    mpu = MPU(); mem = [0] * 0x10000; mpu.memory = mem
    for i, b in enumerate(code):
        mem[0x8000 + i] = b
    for i, b in enumerate(TOG):
        mem[0xFF30 + i] = b
    mem[MAGIC] = 0xA5; mem[MODE] = 4; mem[Z04] = 1; mem[MATCH] = 1
    mem[VC1] = 20; mem[VC2] = 20
    mem[ARMED2] = 1; mem[PEND2] = 0; mem[DELAY2] = 0
    mem[ROT_DONE2] = 0; mem[WDOG2] = 0; mem[WDOGH2] = 0
    X, Y, O = X_SPAWN, 15, 0
    mem[PX2] = X; mem[PY2] = Y; mem[ORI2] = O
    mem[LASTY2] = Y; mem[STKX2] = X; mem[STKY2] = Y
    # copro result is already published (we are studying the descent, not the latency)
    mem[W_OR] = best_orient_raw; mem[W_COL] = best_col; mem[W_DONE] = 1
    mem[W_TCOL] = tcol; mem[W_TROW] = trow
    O_tgt = GAMEMAP[best_orient_raw]
    fall = 0; das = 0; SENT = 0x400; mc = 0x8000 + lab["main"]
    tuck_live = 0
    for f in range(maxf):
        mem[F6] = 0
        if persist:
            mem[TUCK_C2] = tcol; mem[TUCK_R2] = trow
        mpu.sp = 0xFD; r = SENT - 1
        mem[0x100 + mpu.sp] = (r >> 8) & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
        mem[0x100 + mpu.sp] = r & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.pc = mc; k = 0
        while mpu.pc != SENT and k < 40000:
            mpu.step(); k += 1
        b = mem[F6]
        if mem[TUCK_C2] != 0xFF:
            tuck_live += 1
        if b & 0x80:
            O = (O + 1) & 3
        row = 15 - Y
        if b & 0x02:
            das += 1
            if das % SLIDE_F == 1 and X > 0 and not occupied(board, row, X - 1):
                X -= 1
        elif b & 0x01:
            das += 1
            if das % SLIDE_F == 1 and X < COLS - 1 and not occupied(board, row, X + 1):
                X += 1
        else:
            das = 0
        period = SOFT if (b & 0x04) else NAT
        fall += 1
        if fall >= period:
            fall = 0
            nrow = row + 1
            if nrow >= ROWS or occupied(board, nrow, X):
                return X, f, "locked", tuck_live, row
            Y -= 1
        mem[PX2] = X; mem[PY2] = Y; mem[ORI2] = O
    return X, maxf, "timeout", tuck_live, 15 - Y
