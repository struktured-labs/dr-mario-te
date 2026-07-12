#!/usr/bin/env python3
"""vertical_clear_readiness 6502 primitive (needed: dropping vrdy cost the clear-rate).
Per virus: same-color contiguous run DOWN its column (up+down), accumulate run^2. 128B board."""
import sys, random
HERE = "/home/struktured/projects/dr-mario-mods"
sys.path.insert(0, HERE + "/tests"); sys.path.insert(0, HERE)
import primitives as P
from patch_vs_cpu import Asm6502
from py65_harness import Cpu
from test_depth2 import _rand_board

BOARD = 0x0500
EMPTY = 0xFF
EO_LO, EO_HI = P.EO_LO, P.EO_HI
ET0, ET1, ET2, ET4, ET5 = P.ET0, P.ET1, P.ET2, P.ET4, P.ET5
SQ_LO, SQ_HI = P.SQ_LO_ADDR, P.SQ_HI_ADDR


def py_vrdy(b):
    total = 0
    for idx in range(128):
        if (b[idx] & 0xF0) != 0xD0:
            continue
        v = b[idx] & 0x0F; r = idx >> 3; c = idx & 7
        run = 1; rr = r - 1
        while rr >= 0 and b[rr * 8 + c] != 0xFF and (b[rr * 8 + c] & 0x0F) == v:
            run += 1; rr -= 1
        rr = r + 1
        while rr < 16 and b[rr * 8 + c] != 0xFF and (b[rr * 8 + c] & 0x0F) == v:
            run += 1; rr += 1
        total += run * run
    return total


def emit_vrdy(a):
    a.label("vrdy")
    a.ins("LDA_imm", 0); a.ins("STA_zp", EO_LO); a.ins("STA_zp", EO_HI); a.ins("STA_zp", ET0)
    a.label("vr_cell")
    a.ins("LDX_zp", ET0); a.ins16("LDA_absX", BOARD); a.ins("AND_imm", 0xF0); a.ins("CMP_imm", 0xD0)
    a.br("BEQ", "vr_isv"); a.jmp("vr_next")
    a.label("vr_isv")
    a.ins("LDX_zp", ET0); a.ins16("LDA_absX", BOARD); a.ins("AND_imm", 0x0F); a.ins("STA_zp", ET1)
    a.ins("LDA_imm", 1); a.ins("STA_zp", ET2)                 # run
    # up
    a.ins("LDA_zp", ET0); a.ins("STA_zp", ET4)                # pos
    a.ins("LDA_zp", ET0); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("STA_zp", ET5)  # r
    a.label("vr_up")
    a.ins("LDA_zp", ET5); a.br("BEQ", "vr_upd")
    a.ins("DEC_zp", ET5); a.ins("LDA_zp", ET4); a.ins("SEC"); a.ins("SBC_imm", 8); a.ins("STA_zp", ET4)
    a.ins("LDX_zp", ET4); a.ins16("LDA_absX", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "vr_upd")
    a.ins("AND_imm", 0x0F); a.ins("CMP_zp", ET1); a.br("BNE", "vr_upd")
    a.ins("INC_zp", ET2); a.jmp("vr_up")
    a.label("vr_upd")
    # down
    a.ins("LDA_zp", ET0); a.ins("STA_zp", ET4)
    a.ins("LDA_zp", ET0); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("STA_zp", ET5)
    a.label("vr_dn")
    a.ins("LDA_zp", ET5); a.ins("CMP_imm", 15); a.br("BEQ", "vr_dnd")
    a.ins("INC_zp", ET5); a.ins("LDA_zp", ET4); a.ins("CLC"); a.ins("ADC_imm", 8); a.ins("STA_zp", ET4)
    a.ins("LDX_zp", ET4); a.ins16("LDA_absX", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "vr_dnd")
    a.ins("AND_imm", 0x0F); a.ins("CMP_zp", ET1); a.br("BNE", "vr_dnd")
    a.ins("INC_zp", ET2); a.jmp("vr_dn")
    a.label("vr_dnd")
    a.ins("LDX_zp", ET2)
    a.ins16("LDA_absX", SQ_LO); a.ins("CLC"); a.ins("ADC_zp", EO_LO); a.ins("STA_zp", EO_LO)
    a.ins16("LDA_absX", SQ_HI); a.ins("ADC_zp", EO_HI); a.ins("STA_zp", EO_HI)
    a.label("vr_next")
    a.ins("INC_zp", ET0); a.ins("LDA_zp", ET0); a.ins("CMP_imm", 128); a.br("BEQ", "vr_done"); a.jmp("vr_cell")
    a.label("vr_done"); a.ins("RTS")


def main():
    a = Asm6502(0x8000); emit_vrdy(a); code = a.assemble(); labels = a.labels
    sq = [i * i for i in range(17)]
    rng = random.Random(5); fails = 0; N = 200
    for t in range(N):
        b = _rand_board(rng); cpu = Cpu(); cpu.load(0x8000, code); cpu.set_board(b)
        for i in range(17):
            cpu.mem[SQ_LO + i] = sq[i] & 0xFF; cpu.mem[SQ_HI + i] = sq[i] >> 8
        cpu.call(0x8000 + labels["vrdy"], max_steps=2_000_000)
        got = cpu.mem[EO_LO] | (cpu.mem[EO_HI] << 8); exp = py_vrdy(b)
        if got != exp:
            fails += 1
            if fails <= 5:
                print(f"  MISMATCH t={t}: 6502={got} golden={exp}")
    print(f"vrdy: {N-fails}/{N} match golden  ({'PASS' if not fails else 'FAIL'})")
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
