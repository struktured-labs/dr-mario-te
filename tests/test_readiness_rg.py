#!/usr/bin/env python3
"""Validate 2-region split readiness == full g_readiness."""
import sys, os, random
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import primitives; primitives.BOARD = 0x0500
from py65_harness import Cpu
from patch_vs_cpu import Asm6502
from test_eval_terms import g_readiness, rand_board
BASE = 0x4000
def main():
    a = Asm6502(BASE); primitives.emit_readiness_resumable(a); code = a.assemble()
    cpu = Cpu(); cpu.load(BASE, code)
    for i in range(17): cpu.mem[primitives.SQ_LO_ADDR+i]=(i*i)&0xFF; cpu.mem[primitives.SQ_HI_ADDR+i]=(i*i)>>8
    addr = BASE + a.labels["readiness_rg"]; rng = random.Random(444); fails=0; n=500; cmax=0
    for t in range(n):
        b = rand_board(rng); cpu.set_board(b)
        cpu.mem[primitives.EV_RDY_LO]=0; cpu.mem[primitives.EV_RDY_HI]=0
        for st,en in [(0,43),(43,86),(86,128)]:
            cpu.mem[primitives.RD_START]=st; cpu.mem[primitives.RD_END]=en
            cmax=max(cmax,cpu.call(addr))
        got = cpu.mem[primitives.EV_RDY_LO] | (cpu.mem[primitives.EV_RDY_HI]<<8)
        exp = g_readiness(b)
        if got != exp:
            fails += 1
            if fails<=4: print(f"  t{t}: got={got} exp={exp}")
    print(f"readiness_rg(3 regions): {n-fails}/{n} match  per-region cyc_max={cmax}")
    sys.exit(1 if fails else 0)
if __name__=="__main__": main()
