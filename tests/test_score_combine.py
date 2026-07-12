#!/usr/bin/env python3
"""6502 `combine`: weighted sum of the 6 eval terms into a signed 16-bit leaf
score, with a WIN sentinel. Integer weights are the planner floats x10 (exact):
  score = 5000 - 12*maxh - 25*holes - 45*toprisk + 40*setup - 30*buried + 4*readiness
  (immediate 180*vir + 10*cells is added at the SEARCH level, not here.)
virus_count==0 -> WIN sentinel 0xFFFF (dominates). Validated over random term
tuples vs the Python golden (mod 2^16, since 6502 is two's-complement 16-bit).
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from py65_harness import Cpu
from patch_vs_cpu import Asm6502

BASE = 0x4000
# inputs
MH, HO, TR, SET = 0xD0, 0xD1, 0xD2, 0xD3
BUR_LO, BUR_HI, RDY_LO, RDY_HI = 0xD4, 0xD5, 0xD6, 0xD7
VIRFLAG = 0xD8
# outputs / scratch
SCO_LO, SCO_HI = 0xD9, 0xDA
MLO, MHI, PROD_LO, PROD_HI = 0xDB, 0xDC, 0xDD, 0xDE
BIAS = 5000
WIN = 0xFFFF


def golden(mh, ho, tr, setv, bur, rdy, virflag):
    if virflag == 0:
        return WIN
    s = BIAS - 12 * mh - 25 * ho - 45 * tr + 40 * setv - 30 * bur + 4 * rdy
    return s & 0xFFFF


def build():
    a = Asm6502(BASE)
    a.label("combine")
    a.ins("LDA_zp", VIRFLAG); a.br("BNE", "cg")
    a.ins("LDA_imm", 0xFF); a.ins("STA_zp", SCO_LO); a.ins("STA_zp", SCO_HI); a.ins("RTS")
    a.label("cg")
    a.ins("LDA_imm", BIAS & 0xFF); a.ins("STA_zp", SCO_LO)
    a.ins("LDA_imm", (BIAS >> 8) & 0xFF); a.ins("STA_zp", SCO_HI)

    def term8(src, k, sub):
        a.ins("LDA_zp", src); a.ins("STA_zp", MLO); a.ins("LDA_imm", 0); a.ins("STA_zp", MHI)
        a.ins("LDX_imm", k); a.jsr("mul"); a.jsr("sco_sub" if sub else "sco_add")

    def term16(lo, hi, k, sub):
        a.ins("LDA_zp", lo); a.ins("STA_zp", MLO); a.ins("LDA_zp", hi); a.ins("STA_zp", MHI)
        a.ins("LDX_imm", k); a.jsr("mul"); a.jsr("sco_sub" if sub else "sco_add")

    term8(MH, 12, True)
    term8(HO, 25, True)
    term8(TR, 45, True)
    term8(SET, 40, False)
    term16(BUR_LO, BUR_HI, 30, True)
    term16(RDY_LO, RDY_HI, 4, False)
    a.ins("RTS")

    # mul: PROD = M16 * X (X=k>=1)
    a.label("mul")
    a.ins("LDA_imm", 0); a.ins("STA_zp", PROD_LO); a.ins("STA_zp", PROD_HI)
    a.label("mul_lp")
    a.ins("LDA_zp", PROD_LO); a.ins("CLC"); a.ins("ADC_zp", MLO); a.ins("STA_zp", PROD_LO)
    a.ins("LDA_zp", PROD_HI); a.ins("ADC_zp", MHI); a.ins("STA_zp", PROD_HI)
    a.ins("DEX"); a.br("BNE", "mul_lp")
    a.ins("RTS")
    # sco += / -= PROD
    a.label("sco_add")
    a.ins("LDA_zp", SCO_LO); a.ins("CLC"); a.ins("ADC_zp", PROD_LO); a.ins("STA_zp", SCO_LO)
    a.ins("LDA_zp", SCO_HI); a.ins("ADC_zp", PROD_HI); a.ins("STA_zp", SCO_HI); a.ins("RTS")
    a.label("sco_sub")
    a.ins("LDA_zp", SCO_LO); a.ins("SEC"); a.ins("SBC_zp", PROD_LO); a.ins("STA_zp", SCO_LO)
    a.ins("LDA_zp", SCO_HI); a.ins("SBC_zp", PROD_HI); a.ins("STA_zp", SCO_HI); a.ins("RTS")
    return a.assemble(), a.labels


def main():
    code, labels = build()
    cpu = Cpu(); cpu.load(BASE, code)
    addr = BASE + labels["combine"]
    rng = random.Random(7)
    fails = 0; n = 2000
    for _ in range(n):
        mh = rng.randint(0, 16); ho = rng.randint(0, 120); tr = rng.randint(0, 24)
        setv = rng.randint(0, 50); bur = rng.randint(0, 720); rdy = rng.randint(0, 768)
        vf = rng.randint(0, 1)
        cpu.set_zp(MH, mh); cpu.set_zp(HO, ho); cpu.set_zp(TR, tr); cpu.set_zp(SET, setv)
        cpu.set_zp(BUR_LO, bur & 0xFF); cpu.set_zp(BUR_HI, bur >> 8)
        cpu.set_zp(RDY_LO, rdy & 0xFF); cpu.set_zp(RDY_HI, rdy >> 8)
        cpu.set_zp(VIRFLAG, vf)
        cpu.call(addr)
        got = cpu.zp(SCO_LO) | (cpu.zp(SCO_HI) << 8)
        exp = golden(mh, ho, tr, setv, bur, rdy, vf)
        if got != exp:
            fails += 1
            if fails <= 5:
                print(f"  MISMATCH mh{mh} ho{ho} tr{tr} set{setv} bur{bur} rdy{rdy} vf{vf}: got={got} exp={exp}")
    print(f"combine: {n - fails}/{n} match  size={len(code)}B")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
