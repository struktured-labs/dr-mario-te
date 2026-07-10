#!/usr/bin/env python3
"""clear_readiness_ext 6502 primitive for the depth-3 endgame eval, validated cell-exact.
Per virus: run = contiguous same-color through it (each direction, stops at first non-same);
span = contiguous same-color-OR-empty (stops at first DIFFERENT color). A direction's run^2
counts only if its span >= 4 (the line can still reach 4). total += max(h-run^2 if h_ok,
v-run^2 if v_ok). Board 128B, virus=0xD0|col pill=0x40|col empty=0xFF."""
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
ET0, ET1, ET2, ET3, ET4, ET5, ET6 = P.ET0, P.ET1, P.ET2, P.ET3, P.ET4, P.ET5, P.ET6
SQ_LO, SQ_HI = P.SQ_LO_ADDR, P.SQ_HI_ADDR
# extra scratch (free zp above the primitives' 0xE2-0xEA)
WSTEP, WDIR, WBOUND, RE_HRUN, RE_HOK, RE_R, RE_C = 0xEB, 0xEC, 0xED, 0xEE, 0xEF, 0xF0, 0xF1


def _walk(b, idx, v, coord, cstep, cbound_lo, cbound_hi, istep):
    """returns (run, span) walking one direction until a different color / boundary."""
    run = span = 0
    pos, co, rf = idx, coord, 1
    while True:
        if cstep < 0 and co == cbound_lo:
            break
        if cstep > 0 and co == cbound_hi:
            break
        pos = (pos + istep) & 0xFF; co += cstep
        x = b[pos]
        if x == 0xFF:
            span += 1; rf = 0
        elif (x & 0x0F) == v:
            span += 1
            if rf:
                run += 1
        else:
            break
    return run, span


def py_readiness_ext(b):
    total = 0
    for idx in range(128):
        if (b[idx] & 0xF0) != 0xD0:
            continue
        v = b[idx] & 0x0F; r = idx >> 3; c = idx & 7
        lr, ls = _walk(b, idx, v, c, -1, 0, 7, -1)
        rr, rs = _walk(b, idx, v, c, +1, 0, 7, +1)
        hrun = 1 + lr + rr; hspan = 1 + ls + rs
        ur, us = _walk(b, idx, v, r, -1, 0, 15, -8)
        dr, ds = _walk(b, idx, v, r, +1, 0, 15, +8)
        vrun = 1 + ur + dr; vspan = 1 + us + ds
        hcand = hrun if hspan >= 4 else 0
        vcand = vrun if vspan >= 4 else 0
        best = max(hcand, vcand)
        total += best * best
    return total


def emit_walk(a):
    # in: ET5=WPOS ET6=WCOORD ET4=runflag WSTEP(idx signed) WDIR(0 dec/1 inc) WBOUND ; acc ET2=run ET3=span
    a.label("re_walk")
    a.label("rw_loop")
    a.ins("LDA_zp", WDIR); a.br("BNE", "rw_inc")
    a.ins("LDA_zp", ET6); a.br("BEQ", "rw_done"); a.jmp("rw_step")     # dec: stop at 0
    a.label("rw_inc")
    a.ins("LDA_zp", ET6); a.ins("CMP_zp", WBOUND); a.br("BEQ", "rw_done")
    a.label("rw_step")
    a.ins("LDA_zp", ET5); a.ins("CLC"); a.ins("ADC_zp", WSTEP); a.ins("STA_zp", ET5)
    a.ins("LDA_zp", WDIR); a.br("BEQ", "rw_cdec"); a.ins("INC_zp", ET6); a.jmp("rw_cell")
    a.label("rw_cdec"); a.ins("DEC_zp", ET6)
    a.label("rw_cell")
    a.ins("LDX_zp", ET5); a.ins16("LDA_absX", BOARD)
    a.ins("CMP_imm", EMPTY); a.br("BEQ", "rw_empty")
    a.ins("AND_imm", 0x0F); a.ins("CMP_zp", ET1); a.br("BEQ", "rw_same"); a.jmp("rw_done")
    a.label("rw_empty")
    a.ins("INC_zp", ET3); a.ins("LDA_imm", 0); a.ins("STA_zp", ET4); a.jmp("rw_loop")
    a.label("rw_same")
    a.ins("INC_zp", ET3); a.ins("LDA_zp", ET4); a.br("BEQ", "rw_loop"); a.ins("INC_zp", ET2); a.jmp("rw_loop")
    a.label("rw_done"); a.ins("RTS")


def _setup_dir(a, wstep, wdir, wbound, coord_src):
    a.ins("LDA_imm", wstep & 0xFF); a.ins("STA_zp", WSTEP)
    a.ins("LDA_imm", wdir); a.ins("STA_zp", WDIR)
    a.ins("LDA_imm", wbound); a.ins("STA_zp", WBOUND)
    a.ins("LDA_zp", ET0); a.ins("STA_zp", ET5)          # WPOS = idx
    a.ins("LDA_zp", coord_src); a.ins("STA_zp", ET6)     # WCOORD
    a.ins("LDA_imm", 1); a.ins("STA_zp", ET4)            # runflag
    a.jsr("re_walk")


def emit_readiness_ext(a):
    a.label("readiness_ext")
    a.ins("LDA_imm", 0); a.ins("STA_zp", EO_LO); a.ins("STA_zp", EO_HI); a.ins("STA_zp", ET0)
    a.label("re_cell")
    a.ins("LDX_zp", ET0); a.ins16("LDA_absX", BOARD); a.ins("AND_imm", 0xF0); a.ins("CMP_imm", 0xD0)
    a.br("BEQ", "re_isv"); a.jmp("re_next")
    a.label("re_isv")
    a.ins("LDX_zp", ET0); a.ins16("LDA_absX", BOARD); a.ins("AND_imm", 0x0F); a.ins("STA_zp", ET1)
    a.ins("LDA_zp", ET0); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("LSR_A"); a.ins("STA_zp", RE_R)
    a.ins("LDA_zp", ET0); a.ins("AND_imm", 7); a.ins("STA_zp", RE_C)
    # horizontal: run/span start 1
    a.ins("LDA_imm", 1); a.ins("STA_zp", ET2); a.ins("STA_zp", ET3)
    _setup_dir(a, 0xFF, 0, 7, RE_C)     # left
    _setup_dir(a, 0x01, 1, 7, RE_C)     # right
    a.ins("LDA_zp", ET2); a.ins("STA_zp", RE_HRUN)
    a.ins("LDA_imm", 0); a.ins("STA_zp", RE_HOK)
    a.ins("LDA_zp", ET3); a.ins("CMP_imm", 4); a.br("BCC", "re_hno"); a.ins("LDA_imm", 1); a.ins("STA_zp", RE_HOK)
    a.label("re_hno")
    # vertical
    a.ins("LDA_imm", 1); a.ins("STA_zp", ET2); a.ins("STA_zp", ET3)
    _setup_dir(a, 0xF8, 0, 15, RE_R)    # up (-8)
    _setup_dir(a, 0x08, 1, 15, RE_R)    # down (+8)
    # Vok in carry: span ET3 >= 4 ?
    a.ins("LDA_zp", ET3); a.ins("CMP_imm", 4); a.br("BCS", "re_vok")
    a.ins("LDA_imm", 0); a.ins("STA_zp", ET2)          # v not ok -> vcand run = 0
    a.label("re_vok")
    # hcand = RE_HOK ? RE_HRUN : 0  -> ET5
    a.ins("LDA_zp", RE_HOK); a.br("BNE", "re_huse"); a.ins("LDA_imm", 0); a.ins("STA_zp", ET5); a.jmp("re_bestcmp")
    a.label("re_huse"); a.ins("LDA_zp", RE_HRUN); a.ins("STA_zp", ET5)
    a.label("re_bestcmp")
    # best_run = max(ET5 hcand, ET2 vcand) -> X
    a.ins("LDA_zp", ET2); a.ins("CMP_zp", ET5); a.br("BCS", "re_useV"); a.ins("LDA_zp", ET5)
    a.label("re_useV"); a.ins("TAX")
    a.ins16("LDA_absX", SQ_LO); a.ins("CLC"); a.ins("ADC_zp", EO_LO); a.ins("STA_zp", EO_LO)
    a.ins16("LDA_absX", SQ_HI); a.ins("ADC_zp", EO_HI); a.ins("STA_zp", EO_HI)
    a.label("re_next")
    a.ins("INC_zp", ET0); a.ins("LDA_zp", ET0); a.ins("CMP_imm", 128); a.br("BEQ", "re_done"); a.jmp("re_cell")
    a.label("re_done"); a.ins("RTS")


def main():
    a = Asm6502(0x8000)
    emit_readiness_ext(a); emit_walk(a)
    code = a.assemble(); labels = a.labels
    # square table 0..16 at SQ_LO/HI
    sq = [i * i for i in range(17)]
    rng = random.Random(11); fails = 0; N = 200
    for t in range(N):
        b = _rand_board(rng)
        cpu = Cpu(); cpu.load(0x8000, code); cpu.set_board(b)
        for i in range(17):
            cpu.mem[SQ_LO + i] = sq[i] & 0xFF; cpu.mem[SQ_HI + i] = sq[i] >> 8
        cpu.call(0x8000 + labels["readiness_ext"], max_steps=4_000_000)
        got = cpu.mem[EO_LO] | (cpu.mem[EO_HI] << 8)
        exp = py_readiness_ext(b)
        if got != exp:
            fails += 1
            if fails <= 6:
                print(f"  MISMATCH t={t}: 6502={got} golden={exp}")
    print(f"readiness_ext: {N-fails}/{N} match golden  ({'PASS' if not fails else 'FAIL'})")
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
