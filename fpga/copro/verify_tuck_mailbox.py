#!/usr/bin/env python3
"""Prove the TUCK mailbox is wired and never garbage.

Two independent things have to hold, and neither was true before 64ea9ad:

 1. RTL: CoproDrMario.xlate() must map cart $5087/$5088 to DISTINCT copro cells. It used
    to map both to `default` = $68FE, so the driver's executor read ONE byte for BOTH
    fields. Checked here by parsing the .sv -- if someone drops the case arms, this fails.

 2. FIRMWARE: the stub must initialise $6139/$613A. Wiring the RTL turned these from a
    fixed scratch cell into real copro RAM, so an uninitialised pair would make a DRTUCK=1
    driver steer to a RANDOM column. Checked here by running the actual reset->DONE flow
    in py65 on the emitted ROM and reading the cells back.

Run: <venv>/bin/python verify_tuck_mailbox.py
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, ROOT)

TUCK_COL, TUCK_ROW = 0x6139, 0x613A
CART_TCOL, CART_TROW = 0x5087, 0x5088
fails = []


def check_rtl():
    """Parse xlate() and confirm $5087/$5088 land on distinct, expected cells."""
    sv = open(os.path.join(HERE, "CoproDrMario.sv")).read()
    body = sv[sv.index("function [11:0] xlate"):]
    body = body[:body.index("endfunction")]
    arms = dict((int(h, 16), int(v, 16))
                for h, v in re.findall(r"7'h([0-9A-Fa-f]{2}):\s*xlate\s*=\s*12'h([0-9A-Fa-f]{3})", body))
    print("  xlate arms:", {hex(k): hex(v) for k, v in sorted(arms.items())})
    for cart, copro, name in ((CART_TCOL, TUCK_COL, "W_TCOL"), (CART_TROW, TUCK_ROW, "W_TROW")):
        off = cart & 0x7F                      # the case runs on a[6:0] with a[7] set
        want = 0x800 | (copro & 0xFF)          # fold: $61XX -> 12'h8XX
        got = arms.get(off)
        if got is None:
            fails.append(f"RTL: cart ${cart:04X} ({name}) has NO case arm -> falls to default/scratch")
        elif got != want:
            fails.append(f"RTL: cart ${cart:04X} ({name}) maps to 12'h{got:03X}, expected 12'h{want:03X}")
        else:
            print(f"  ✅ cart ${cart:04X} {name:6s} -> copro ${copro:04X} (12'h{got:03X})")
    if arms.get(CART_TCOL & 0x7F) == arms.get(CART_TROW & 0x7F):
        fails.append("RTL: W_TCOL and W_TROW map to the SAME cell -- this was the original bug")


def check_firmware():
    """Run the real reset->DONE flow and read the descriptor back out of copro RAM."""
    import build_copro_d3 as B
    from py65_harness import Cpu
    import test_search_d3 as D3

    # Same shape build_copro_d3's own hardware-path check uses.
    board = [B.EMPTY] * 128
    img, _clen, _slen = B.build_image(board, 1, 2, 3, 1)

    cpu = Cpu()
    for a, v in enumerate(img):
        cpu.mem[a] = v
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    cpu.mem[B.S_CA], cpu.mem[B.S_CB] = 1, 2
    cpu.mem[B.S_NA], cpu.mem[B.S_NB] = 3, 1
    cpu.mem[B.DONE] = 0
    # POISON the descriptor: if the stub fails to write it we must SEE the poison,
    # otherwise a zeroed RAM would let this pass by luck.
    cpu.mem[TUCK_COL] = 0x5A
    cpu.mem[TUCK_ROW] = 0xA5

    m = cpu.mpu
    m.pc = B.STUB
    m.sp = 0xFF
    steps = 0
    reached = False
    while steps < B.MAX_STEPS:
        m.step(); steps += 1
        if cpu.mem[B.DONE] == 1:
            reached = True
            break
    if not reached:
        fails.append("firmware: never reached DONE")
        return
    tc, tr = cpu.mem[TUCK_COL], cpu.mem[TUCK_ROW]
    print(f"  after reset->DONE: $6139={tc:#04x} $613A={tr:#04x} (poisoned 0x5a/0xa5)")
    if tc == 0x5A or tr == 0xA5:
        fails.append("firmware: stub did NOT initialise the descriptor -- poison survived, "
                     "so a DRTUCK=1 driver would read stale copro RAM")
    elif (tc, tr) != (0xFF, 0xFF):
        fails.append(f"firmware: descriptor is {tc:#04x}/{tr:#04x}, expected 0xFF/0xFF (no tuck)")
    else:
        print("  ✅ stub initialises both bytes to 0xFF (= no tuck), poison overwritten")


print("=== TUCK MAILBOX WIRING ===")
check_rtl()
print("=== FIRMWARE INITIALISATION ===")
try:
    check_firmware()
except Exception as e:
    fails.append(f"firmware check errored: {type(e).__name__}: {e}")

print()
if fails:
    for f in fails:
        print("  ✗", f)
    sys.exit(1)
print("TUCK MAILBOX: PASS (distinct RTL mapping + firmware never leaves it garbage)")
