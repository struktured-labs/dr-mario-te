#!/usr/bin/env python3
"""Assemble the depth-3 leaf eval (shape+buried+ext_readiness+setup+vrdy-pollution) and
validate EV_SCO cell-exact vs the leaf_d3 golden (non-virus-free boards). This is the eval
half of emit_search_d3; primitives already validated individually 200/200."""
import sys, random
HERE = "/home/struktured/projects/dr-mario-mods"
sys.path.insert(0, HERE + "/tests"); sys.path.insert(0, HERE)
import primitives as P
from patch_vs_cpu import Asm6502
import patch_vs_cpu
patch_vs_cpu.OPS.setdefault("CLD", 0xD8)
from py65_harness import Cpu
from test_depth2 import _rand_board
from test_pollution import emit_pollution
from test_readiness_ext import emit_readiness_ext, emit_walk
from test_vrdy import emit_vrdy
from nes_d3_golden import leaf_d3, USE_VRDY
from nes_d2_golden import _virus_count

P.BOARD = 0x0500; P.LIVE_BOARD = 0x0500; P.MARK = 0x0780
EV_POL_LO, EV_POL_HI = 0x611F, 0x6120


def emit_combine_d3(a):
    P.emit_combine(a)                              # SCO = everything EXCEPT pollution (reads EV_RDY,EV_VRDY)
    a.label("combine_d3")
    a.jsr("combine")
    # EV_SCO -= 6 * EV_POL   (reuse combine's cm_mul/cm_sub, EV_M input)
    a.ins16("LDA_abs", EV_POL_LO); a.ins16("STA_abs", P.EV_MLO)
    a.ins16("LDA_abs", EV_POL_HI); a.ins16("STA_abs", P.EV_MHI)
    a.ins("LDX_imm", 6); a.jsr("cm_mul"); a.jsr("cm_sub")
    a.ins("RTS")


def emit_leaf_score_d3(a):
    a.label("leaf_score_d3")
    a.jsr("shape")
    a.jsr("buried")
    a.jsr("readiness_ext")
    a.ins("LDA_zp", P.EO_LO); a.ins16("STA_abs", P.EV_RDY_LO)
    a.ins("LDA_zp", P.EO_HI); a.ins16("STA_abs", P.EV_RDY_HI)
    a.jsr("setup")
    a.ins("LDA_zp", P.EO_LO); a.ins16("STA_abs", P.EV_SET)
    a.jsr("vrdy")
    a.ins("LDA_zp", P.EO_LO); a.ins16("STA_abs", P.EV_VRDY_LO)
    a.ins("LDA_zp", P.EO_HI); a.ins16("STA_abs", P.EV_VRDY_HI)
    a.jsr("pollution")
    a.ins("LDA_zp", P.EO_LO); a.ins16("STA_abs", EV_POL_LO)
    a.ins("LDA_zp", P.EO_HI); a.ins16("STA_abs", EV_POL_HI)
    a.jsr("has_virus")
    a.jsr("combine_d3")
    a.ins("RTS")


def build():
    a = Asm6502(0x8000)
    emit_leaf_score_d3(a)
    P.emit_shape(a); P.emit_buried(a); P.emit_setup(a); P.emit_has_virus(a)
    emit_readiness_ext(a); emit_walk(a); emit_vrdy(a); emit_pollution(a)
    emit_combine_d3(a)
    return a.assemble(), a.labels


def s16(x):
    return x - 0x10000 if x >= 0x8000 else x


def main():
    global USE_VRDY
    import nes_d3_golden
    nes_d3_golden.USE_VRDY = True
    code, labels = build()
    sq = [i * i for i in range(17)]
    rng = random.Random(9); fails = 0; N = 200; done = 0
    for t in range(N):
        b = _rand_board(rng)
        if _virus_count(b) == 0:
            continue
        done += 1
        cpu = Cpu(); cpu.load(0x8000, code); cpu.set_board(b)
        for i in range(17):
            cpu.mem[P.SQ_LO_ADDR + i] = sq[i] & 0xFF; cpu.mem[P.SQ_HI_ADDR + i] = sq[i] >> 8
        cpu.call(0x8000 + labels["leaf_score_d3"], max_steps=6_000_000)
        got = s16(cpu.mem[P.EV_SCO_LO] | (cpu.mem[P.EV_SCO_HI] << 8))
        exp = leaf_d3(b)
        if got != exp:
            fails += 1
            if fails <= 6:
                print(f"  MISMATCH t={t}: 6502={got} golden={exp}")
    print(f"leaf_score_d3: {done-fails}/{done} match leaf_d3 golden  ({'PASS' if not fails else 'FAIL'})")
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
