#!/usr/bin/env python3
"""color_pollution 6502 primitive for the depth-3 endgame eval, validated cell-exact vs
the faithful golden. For each virus: count non-virus non-empty cells in its row+column
whose color (low nibble) differs from the virus color. Board = 128B ($0500), row-major,
virus=0xD0|col, pill=0x40|col, empty=0xFF."""
import sys, random
HERE = "/home/struktured/projects/dr-mario-mods"
sys.path.insert(0, HERE + "/tests"); sys.path.insert(0, HERE)
import primitives as P
from patch_vs_cpu import Asm6502
import patch_vs_cpu
patch_vs_cpu.OPS.setdefault("CLD", 0xD8)
from py65_harness import Cpu, P2_BOARD, EMPTY as HEMPTY
from test_depth2 import _rand_board

BOARD = 0x0500
EMPTY = 0xFF
EO_LO, EO_HI = P.EO_LO, P.EO_HI
ET0, ET1, ET2, ET3, ET4, ET5 = P.ET0, P.ET1, P.ET2, P.ET3, P.ET4, P.ET5


def py_pollution(b):
    total = 0
    for idx in range(128):
        if (b[idx] & 0xF0) != 0xD0:
            continue
        v = b[idx] & 0x0F; r = idx >> 3; c = idx & 7
        for cc in range(8):
            if cc == c:
                continue
            cell = b[r * 8 + cc]
            if cell == 0xFF or (cell & 0xF0) == 0xD0:
                continue
            if (cell & 0x0F) != v:
                total += 1
        for rr in range(16):
            if rr == r:
                continue
            cell = b[rr * 8 + c]
            if cell == 0xFF or (cell & 0xF0) == 0xD0:
                continue
            if (cell & 0x0F) != v:
                total += 1
    return total


def emit_pollution(a):
    a.label("pollution")
    a.ins("LDA_imm", 0); a.ins("STA_zp", EO_LO); a.ins("STA_zp", EO_HI); a.ins("STA_zp", ET0)
    a.label("pol_cell")
    a.ins("LDX_zp", ET0); a.ins16("LDA_absX", BOARD)
    a.ins("AND_imm", 0xF0); a.ins("CMP_imm", 0xD0); a.br("BEQ", "pol_isv"); a.jmp("pol_next")
    a.label("pol_isv")
    a.ins("LDX_zp", ET0); a.ins16("LDA_absX", BOARD); a.ins("AND_imm", 0x0F); a.ins("STA_zp", ET1)  # v_color
    a.ins("LDA_zp", ET0); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("STA_zp", ET2)      # r
    a.ins("LDA_zp", ET0); a.ins("AND_imm", 7); a.ins("STA_zp", ET3)                                  # c
    # row_base = idx - c -> ET4
    a.ins("LDA_zp", ET0); a.ins("SEC"); a.ins("SBC_zp", ET3); a.ins("STA_zp", ET4)
    a.ins("LDX_imm", 0)                                                                              # X = cc
    a.label("pol_row")
    a.ins("CPX_zp", ET3); a.br("BEQ", "pol_rnext")
    a.ins("TXA"); a.ins("CLC"); a.ins("ADC_zp", ET4); a.ins("TAY")
    a.ins16("LDA_absY", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "pol_rnext")
    a.ins("STA_zp", ET5)
    a.ins("AND_imm", 0xF0); a.ins("CMP_imm", 0xD0); a.br("BEQ", "pol_rnext")
    a.ins("LDA_zp", ET5); a.ins("AND_imm", 0x0F); a.ins("CMP_zp", ET1); a.br("BEQ", "pol_rnext")
    a.jsr("pol_inc")
    a.label("pol_rnext")
    a.ins("INX"); a.ins("CPX_imm", 8); a.br("BNE", "pol_row")
    a.ins("LDX_imm", 0)                                                                              # X = rr
    a.label("pol_col")
    a.ins("CPX_zp", ET2); a.br("BEQ", "pol_cnext")
    a.ins("TXA"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("ASL_A"); a.ins("CLC"); a.ins("ADC_zp", ET3); a.ins("TAY")
    a.ins16("LDA_absY", BOARD); a.ins("CMP_imm", EMPTY); a.br("BEQ", "pol_cnext")
    a.ins("STA_zp", ET5)
    a.ins("AND_imm", 0xF0); a.ins("CMP_imm", 0xD0); a.br("BEQ", "pol_cnext")
    a.ins("LDA_zp", ET5); a.ins("AND_imm", 0x0F); a.ins("CMP_zp", ET1); a.br("BEQ", "pol_cnext")
    a.jsr("pol_inc")
    a.label("pol_cnext")
    a.ins("INX"); a.ins("CPX_imm", 16); a.br("BNE", "pol_col")
    a.label("pol_next")
    a.ins("INC_zp", ET0); a.ins("LDA_zp", ET0); a.ins("CMP_imm", 128); a.br("BEQ", "pol_done"); a.jmp("pol_cell")
    a.label("pol_done"); a.ins("RTS")
    a.label("pol_inc")
    a.ins("INC_zp", EO_LO); a.br("BNE", "pol_inc_d"); a.ins("INC_zp", EO_HI)
    a.label("pol_inc_d"); a.ins("RTS")


def main():
    a = Asm6502(0x8000)
    emit_pollution(a)
    code = a.assemble(); labels = a.labels
    rng = random.Random(7); fails = 0; N = 200
    for t in range(N):
        b = _rand_board(rng)
        cpu = Cpu(); cpu.load(0x8000, code); cpu.set_board(b)
        cpu.call(0x8000 + labels["pollution"], max_steps=2_000_000)
        got = cpu.mem[EO_LO] | (cpu.mem[EO_HI] << 8)
        exp = py_pollution(b)
        if got != exp:
            fails += 1
            if fails <= 5:
                print(f"  MISMATCH t={t}: 6502={got} golden={exp}")
    print(f"pollution: {N-fails}/{N} match golden  ({'PASS' if not fails else 'FAIL'})")
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
