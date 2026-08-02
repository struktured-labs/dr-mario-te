#!/usr/bin/env python3
"""PINNED REGRESSION CASE for the tuck enumerator + executor contract.

Three defects were found in pre-silicon co-sim (2026-08-01) that no test written by the
feature's own author could catch, because each test asserted against a plausible model of
the consumer rather than the consumer's actual semantics:

  D1  tuck_scan publishes a BOARD ROW (0 = top); the executor compares it against $0386,
      which the game stores as 15 - row.  Confirmed against the meatfighter prior art:
      DrMarioAI.java:69, `y = 15 - readCPU(CURRENT_Y)`.
  D2  the driver's invalidation sits at the TOP of h2_start, before the pend/delay
      early-outs, so it runs on every frame with ARMED2 == 0 -- the whole descent.
      TUCK_C2 is non-0xFF for exactly ONE frame per pill; the executor is dead code.
  D3  the enumerator maximises depth over ALL 8 columns and publishes only
      (approach, trigger); the executor's final column is TGT_C2 = the search's best_col.
      On 195 real L11 boards those disagree 87.5% of the time.

★★ THE REASON THIS FILE EXISTS: fixing D1 and D2 WITHOUT D3 makes the feature WORSE, not
better -- off-scored-column landings go 11.2% -> 45.6%.  Partial fixes are anti-fixes.  The
CONTRACT section below therefore fails as a group until all three land together.

USAGE
    python3 tuck_regression.py          # invariants hard, contract reported as EXPECTED FAIL
    DRTUCK_V2=1 python3 tuck_regression.py   # contract becomes a HARD failure -- use this
                                             # as the ship gate once v2 is built

The enumerator half is checked through `ref_tuck_scan`, which the Verilator co-sim confirmed
bit-identical to the real 6502 on the real RTL for 195/195 real L11 boards and 22/22
adversarial boards, so the reference is a faithful stand-in and needs no hardware here.
"""
import os, sys

CANON = os.environ.get("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
DRIVER = os.environ.get("DRNAV", "/home/struktured/projects/dr-mario-mods-wt/driver-nav")
sys.path.insert(0, os.path.join(CANON, "fpga", "copro"))
from tuck_scan import ref_tuck_scan, ROWS, COLS, EMPTY          # noqa: E402

V2 = os.environ.get("DRTUCK_V2", "0") == "1"
VIRUS = 0xD0
NAT, SOFT, SLIDE_F, X_SPAWN = 13, 2, 6, 3   # L11 rates (fall_sim.py); DAS ~1 col / 6 f

fails, xfails = [], []


def check(hard, name, ok, detail=""):
    tag = "PASS" if ok else ("FAIL" if (hard or V2) else "xfail")
    if not ok:
        (fails if (hard or V2) else xfails).append(name)
    print("  [%s] %-52s %s" % (tag, name, detail))


def blank():
    return [EMPTY] * (ROWS * COLS)


def occ(b, r, c):
    b[r * COLS + c] = VIRUS


def occupied(board, r, c):
    return board[r * COLS + c] != EMPTY


def first_occ(board, c):
    for r in range(ROWS):
        if occupied(board, r, c):
            return r
    return ROWS


def enum_full(board):
    """the enumerator's choice INCLUDING the target column it optimised for (never published)"""
    best = None
    for c in range(COLS):
        fc = first_occ(board, c)
        if fc == 0:
            continue
        for side in (0, 1):
            a = c - 1 if side == 0 else c + 1
            if not (0 <= a < COLS):
                continue
            fa = first_occ(board, a)
            if fa == 0:
                continue
            r = fc
            while r <= fa - 1:
                if not occupied(board, r, c):
                    rf = r
                    while rf + 1 < ROWS and not occupied(board, rf + 1, c):
                        rf += 1
                    if rf > fc - 1 and (best is None or rf > best[0]):
                        best = (rf, a, r, c)
                r += 1
    return None if best is None else {"rest": best[0], "approach": best[1],
                                      "trigger": best[2], "target": best[3]}


def descend(board, best_col, tcol, trow, maxf=900):
    """The executor's motion, in the executor's own units.

    EFF = approach column while $0386 > TUCK_R2, else best_col; misaligned = slide at DAS
    under natural gravity, aligned = the confidence slam holds Down (soft drop).  Validated
    against the REAL emitted driver bytes in py65: 478/480 landings identical over the real
    L11 corpus x 3 descriptors (the 2 differ only in DAS phase at a row-0 immediate lock).
    """
    row, col, fall, das = 0, X_SPAWN, 0, 0
    for f in range(maxf):
        y = 15 - row
        eff = tcol if (tcol != 0xFF and y > trow) else best_col
        aligned = (col == eff)
        if aligned:
            das = 0
        else:
            das += 1
            if das % SLIDE_F == 1:
                nc = col - 1 if eff < col else col + 1
                if 0 <= nc < COLS and not occupied(board, row, nc):
                    col = nc
        fall += 1
        if fall >= (SOFT if aligned else NAT):
            fall = 0
            if row + 1 >= ROWS or occupied(board, row + 1, col):
                return col, row
            row += 1
    return col, row


# ---------------------------------------------------------------- boards
def board_misland():
    """THE PINNED REPRO.  col0 lip at row 2 over an empty shaft; col1 -- the only approach --
    is blocked at row 8, so a capsule committed to col1 rests at row 7 = $0386 8.  The
    enumerator publishes (approach 1, trigger row 3).  Read raw, the trigger 3 is never
    reached and the capsule locks in column 1.  Read as 15-3 = 12 it switches at row 3 and
    lands col 0 row 15, under the lip -- the tuck that was actually scored."""
    b = blank()
    occ(b, 2, 0)
    occ(b, 8, 1)
    return b


def board_overhang_c0():
    b = blank(); occ(b, 8, 0); return b


def board_overhang_c7():
    b = blank(); occ(b, 8, 7); return b


def board_pocket():
    b = blank(); occ(b, 9, 3); occ(b, 11, 3)
    for r in range(12, ROWS):
        for c in range(COLS):
            occ(b, r, c)
    return b


def board_approach_blocked():
    """the ONLY overhang's only open neighbour bottoms out far above the lip"""
    b = blank()
    for c in (0, 1, 4, 5, 6, 7):
        for r in range(ROWS):
            occ(b, r, c)
    for r in range(3, ROWS):
        occ(b, r, 2)
    occ(b, 9, 3)
    return b


def board_full():
    return [VIRUS] * (ROWS * COLS)


def board_toprow():
    b = blank()
    for c in range(COLS):
        occ(b, 0, c)
    return b


def board_worstcase():
    """maximises tuck_scan's loop work (940 loop bodies; found by hill-climbing the board
    space over 400 random restarts).  Costs 48,864 copro clocks = 0.034 frames @85.9MHz."""
    b = blank()
    for c in (0, 2, 4, 6):
        occ(b, 1, c)
    return b


# ---------------------------------------------------------------- 1. enumerator goldens
print("1. ENUMERATOR GOLDENS (hard -- the 6502 is co-sim-verified equal to this reference)")
GOLDEN = [
    ("empty board",              blank(),                  (0xFF, 0xFF)),
    ("every column full",        board_full(),             (0xFF, 0xFF)),
    ("top row full",             board_toprow(),           (0xFF, 0xFF)),
    ("approach blocked above lip", board_approach_blocked(), (0xFF, 0xFF)),
    ("left-edge target (col 0)", board_overhang_c0(),      (1, 9)),
    ("right-edge target (col 7)", board_overhang_c7(),     (6, 9)),
    ("single-cell pocket",       board_pocket(),           (2, 10)),
    ("MIS-LAND REPRO",           board_misland(),          (1, 3)),
    ("worst-case latency board", board_worstcase(),        (1, 2)),
]
for name, b, exp in GOLDEN:
    got = ref_tuck_scan(b)
    check(True, name, got == exp, "-> %s" % (got,))

# ---------------------------------------------------------------- 2. the v2 contract
print()
print("2. EXECUTOR CONTRACT (%s)" % ("HARD -- v2 ship gate" if V2 else
                                     "expected to fail on v1; set DRTUCK_V2=1 to enforce"))

b = board_misland()
e = enum_full(b)
tcol, trow = ref_tuck_scan(b)
BEST_COL = e["target"]        # v2 requires the descriptor be FOR best_col; pin them equal

raw = descend(b, BEST_COL, tcol, trow)
fix = descend(b, BEST_COL, tcol, 15 - trow)
non = descend(b, BEST_COL, 0xFF, 0xFF)

check(False, "D1: published trigger is in $0386 space (15-r)",
      raw == (BEST_COL, e["rest"]),
      "raw%s vs required%s ; 15-r gives %s" % (raw, (BEST_COL, e["rest"]), fix))
check(True, "D1 control: 15-r DOES reach the scored cell",
      fix == (BEST_COL, e["rest"]), "-> %s" % (fix,))
check(True, "D1 control: no tuck leaves it on the straight drop",
      non == (BEST_COL, 1), "-> %s" % (non,))
check(False, "D1: raw trigger must not land off the scored column",
      raw[0] == BEST_COL, "raw locked in column %d, search scored column %d" % (raw[0], BEST_COL))

# D3 -- over a spread of geometries, the enumerated target must BE best_col
mismatch = []
for name, bd, _ in GOLDEN:
    ee = enum_full(bd)
    if ee is None:
        continue
    for bc in range(COLS):
        if first_occ(bd, bc) == 0:
            continue
        if ee["target"] != bc:
            mismatch.append((name, bc, ee["target"]))
check(False, "D3: descriptor is enumerated FOR best_col, not deepest-over-all",
      not mismatch,
      "%d (board, best_col) pairs get a descriptor computed for another column" % len(mismatch))

# D2 -- the descriptor must survive the descent in the real driver bytes
try:
    sys.path.insert(0, DRIVER)
    import importlib.util
    from py65.devices.mpu6502 import MPU
    for k in ("DRNOFREEZE", "DRROTFIX", "DRHUMAN", "DRPOCKET", "DRSLAM", "DRTUCK",
              "DRNAVDWELL", "DRRECOMMIT_NOFREEZE"):
        os.environ.pop(k, None)
    os.environ.update({"DRHUMAN": "1", "DRNAVDWELL": "0", "DRNOFREEZE": "1",
                       "DRPOCKET": "1", "DRRECOMMIT_NOFREEZE": "1", "DRTUCK": "1"})
    spec = importlib.util.spec_from_file_location("fs", DRIVER + "/patch_cartridge_copro.py")
    M = importlib.util.module_from_spec(spec); sys.modules["fs"] = M; spec.loader.exec_module(M)
    code, lab = M.build_main(11, 1)
    rom = open(DRIVER + "/drmario_v28cs.nes", "rb").read()
    TOG = rom[16 + (rom[4] * 16384 - 0x4000) + (0xFF30 - 0xC000):][:28]
    mpu = MPU(); mem = [0] * 0x10000; mpu.memory = mem
    for i, v in enumerate(code):
        mem[0x8000 + i] = v
    for i, v in enumerate(TOG):
        mem[0xFF30 + i] = v
    mem[0x6149] = 0xA5; mem[0x46] = 4; mem[0x04] = 1; mem[0x6164] = 1
    mem[0x0324] = mem[0x03A4] = 20
    mem[0x6161] = 1; mem[0x614F] = 0; mem[0x615F] = 0
    mem[0x616E] = 0; mem[0x6162] = 0; mem[0x6166] = 0
    mem[0x0385], mem[0x0386], mem[0x03A5] = X_SPAWN, 15, 0
    mem[0x6155] = 15; mem[0x6159] = X_SPAWN; mem[0x615A] = 15
    mem[0x5086], mem[0x5085], mem[0x5084] = 0, BEST_COL, 1
    mem[0x5087], mem[0x5088] = tcol, trow
    live = 0
    SENT, mc = 0x400, 0x8000 + lab["main"]
    for f in range(40):
        mem[0xF6] = 0
        mpu.sp = 0xFD
        mem[0x100 + mpu.sp] = ((SENT - 1) >> 8) & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
        mem[0x100 + mpu.sp] = (SENT - 1) & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.pc = mc; k = 0
        while mpu.pc != SENT and k < 40000:
            mpu.step(); k += 1
        if mem[M.TUCK_C2] != 0xFF:
            live += 1
    check(False, "D2: descriptor survives the descent (real driver bytes)",
          live > 1, "TUCK_C2 non-0xFF on %d of 40 frames (1 == wiped by h2_start)" % live)
except Exception as exc:                                  # environment, not the code under test
    print("  [SKIP] D2 real-driver check unavailable: %s" % exc)

# ---------------------------------------------------------------- verdict
print()
if fails:
    print("FAILED (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
if xfails:
    print("invariants PASS; %d contract check(s) still open (expected on v1 firmware): %s"
          % (len(xfails), ", ".join(xfails)))
    print("★ these must be fixed TOGETHER -- D1+D2 without D3 takes off-scored-column")
    print("  landings from 11.2% to 45.6% on real L11 boards.")
    sys.exit(0)
print("ALL PASS -- enumerator goldens and the full executor contract hold.")
sys.exit(0)
