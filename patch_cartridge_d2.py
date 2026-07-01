#!/usr/bin/env python3
"""Build the DEPTH-2 cartridge AI (drmario_cart_d2.nes).

Reuses the validated patch_cartridge.py pattern but with the resumable DEPTH-2 search
(tests/test_resumable.py, 8/8 vs atomic, <=8k/phase, cart-safe shadows):
  - PRG unit-1 ($8000): the resumable depth-2 slicer (dispatch/step/arm/eval), ~3.2KB,
    + the readiness square tables at $BF00. All boards/state in $6000 PRG-RAM (CUR=$6000,
    WORK1=$6080, MARK=$6100, EV/state/shadows $6110+). LIVE board read from $0500.
  - FIXED bank: NEW wrapper at $FF54 (ARMED gate: hold+freeze while searching, act when
    done -> rotate $03A5 to $DA (4 states), move $0385 to $DD). Reached via the v28cs
    blob's JMP $FF54 in play mode (0x37CF -> $FB00 blob preserved -> P2 leveling intact).
  - Inline MMC1 bank-switch around the dispatch (like the validated banktest).

SLOW: ~11000 steps/pill (~100s/pill). Run live via Mesen fast-forward; proves the goal.
Start ROM: drmario_v28cs.nes (2-bank). Output: drmario_cart_d2.nes (4-bank).
"""
import sys
sys.path.insert(0, "tests")
import primitives
import test_depth2, test_resumable, test_resumable_incr
from patch_vs_cpu import Asm6502
from expand_prg import expand

V28CS = "drmario_v28cs.nes"
OUT = "drmario_cart_d2.nes"
UNIT1_CPU = 0x8000
WRAP_CPU = 0xFF54
WRAP_FILE = 0x4010 + (WRAP_CPU - 0xC000)
PRG_REG = 0xFFF0
ARMED = 0x6143             # wrapper reads: !=0 searching (hold), ==0 done (act)
GRAV = 0x0392              # P2 gravity counter (pin to freeze while searching)
SQ_LO_ADDR, SQ_HI_ADDR = 0xBF00, 0xBF11   # square tables in unit-1 ROM
SQUARES = [(i * i) & 0xFF for i in range(17)]
SQUARES_HI = [(i * i) >> 8 for i in range(17)]


def _sel(a, value):
    a.ins("LDA_imm", value)
    for i in range(5):
        a.ins("STA_abs", PRG_REG & 0xFF, (PRG_REG >> 8) & 0xFF)
        if i < 4:
            a.ins("LSR_A")


def build_wrapper(dispatch_cpu):
    """Self-contained hook at $FF54 (reached via blob JMP $FF54 in play mode). Gate ->
    inline bank-switch around dispatch (edge+arm+step in unit-1) -> $DF update -> ARMED
    gate: hold (freeze gravity + clear input) while searching, else act (rotate->$DA,
    move->$DD)."""
    w = Asm6502(WRAP_CPU)
    w.ins("LDA_abs", 0x46, 0x00); w.ins("CMP_imm", 0x04); w.br("BNE", "nw_skip")
    w.ins("LDA_zp", 0x04); w.br("BEQ", "nw_skip")
    _sel(w, 2)
    w.jsr(dispatch_cpu)
    _sel(w, 0)
    w.ins("LDA_abs", 0x86, 0x03); w.ins("STA_zp", 0xDF)        # $DF = P2y (after dispatch read old)
    w.ins("LDA_abs", ARMED & 0xFF, (ARMED >> 8) & 0xFF); w.br("BEQ", "nw_act")  # ARMED==0 -> act
    # hold: freeze gravity + clear move/rotate
    w.ins("LDA_imm", 0x00); w.ins("STA_abs", GRAV & 0xFF, (GRAV >> 8) & 0xFF)
    w.ins("STA_zp", 0xF6); w.ins("STA_zp", 0xF8)
    w.label("nw_skip")
    w.ins("RTS")
    w.label("nw_act")
    # rotate $03A5 toward $DA (edge-triggered A=CCW; presses one rotation/frame until match)
    w.ins("LDA_abs", 0xA5, 0x03); w.ins("CMP_zp", 0xDA); w.br("BEQ", "nw_mv")
    w.ins("LDA_imm", 0x00); w.ins("STA_zp", 0xF8)
    w.ins("LDA_imm", 0x80); w.ins("STA_zp", 0xF6); w.ins("RTS")
    # move toward $DD, drop when aligned
    w.label("nw_mv")
    w.ins("LDA_abs", 0x85, 0x03); w.ins("CMP_zp", 0xDD); w.br("BEQ", "nw_dn")
    w.ins("LDY_imm", 0x01); w.br("BCC", "nw_st")
    w.ins("LDY_imm", 0x02); w.jmp("nw_st")
    w.label("nw_dn"); w.ins("LDY_imm", 0x04)
    w.label("nw_st"); w.ins("STY_zp", 0xF6); w.ins("RTS")
    return w.assemble()


def main():
    # 1) INCREMENTAL resumable depth-2 slicer for unit-1, cart RAM config + ROM square tables.
    #    DROP_SETUP=True: setup term hurts L11 clear-rate (+4.6pp dropping it) and is ~33% slower;
    #    base eval (shape+buried+readiness) computed once per first-ply + a cheap per-leaf DELTA.
    #    Delta RAM lives at $6160-$61C1 (above mark/S_*/machine state; PRG-RAM is ours to $7FFF).
    test_resumable_incr.DROP_SETUP = True
    slicer, labels = test_resumable_incr.build_resumable_incr(
        base=UNIT1_CPU, cur=0x6000, work1=0x6080, live=0x0500, mark=0x6100,
        sq_lo=SQ_LO_ADDR, sq_hi=SQ_HI_ADDR)
    dispatch_cpu = UNIT1_CPU + labels["dispatch"]
    print(f"slicer: {len(slicer)} B at unit-1 ${UNIT1_CPU:04X}; dispatch=${dispatch_cpu:04X}")
    assert len(slicer) <= (SQ_LO_ADDR - UNIT1_CPU), "slicer overlaps the square tables"

    # 2) build the 16KB unit-1 bank: slicer at $8000, square tables at $BF00
    bank = bytearray(b"\x00" * 0x4000)
    bank[0:len(slicer)] = slicer
    toff = SQ_LO_ADDR - UNIT1_CPU
    bank[toff:toff + 17] = bytes(SQUARES)
    bank[toff + 17:toff + 34] = bytes(SQUARES_HI)

    # 3) wrapper (fixed bank)
    wrap = build_wrapper(dispatch_cpu)
    print(f"wrapper: {len(wrap)} B at ${WRAP_CPU:04X}")
    assert WRAP_CPU + len(wrap) <= 0xFFD2, "wrapper overflows the dead-v17 window"

    # 4) patch v28cs, expand to 4 banks with the depth-2 bank in unit-1
    rom = bytearray(open(V28CS, "rb").read())
    assert rom[4] == 2
    rom[WRAP_FILE:WRAP_FILE + len(wrap)] = wrap
    HOOK_FILE = 0x37CF
    assert rom[HOOK_FILE] == 0x4C and rom[HOOK_FILE + 1] == 0x00 and rom[HOOK_FILE + 2] == 0xFB, \
        "expected v28cs hook JMP $FB00 at 0x37CF"
    print("hook 0x37CF: JMP $FB00 (blob -> JMP $FF54 in play mode; preserved)")
    tmp = OUT + ".2bank"; open(tmp, "wb").write(rom)
    expand(tmp, OUT, new_bank_bytes=bytes(bank))
    import os; os.remove(tmp)
    print(f"wrote {OUT} (4-bank DEPTH-2 cartridge AI)")


if __name__ == "__main__":
    main()
