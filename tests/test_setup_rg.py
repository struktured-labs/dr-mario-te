#!/usr/bin/env python3
"""Validate 4-region split setup == full g_setup."""
import sys, os, random
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import primitives; primitives.BOARD = 0x0500
from py65_harness import Cpu
from patch_vs_cpu import Asm6502
from test_eval_terms import g_setup, rand_board
BASE = 0x4000
def main():
    a = Asm6502(BASE); primitives.emit_setup(a); primitives.emit_setup_resumable(a); code = a.assemble()
    cpu = Cpu(); cpu.load(BASE, code)
    addr = BASE + a.labels["setup_rg"]; rng = random.Random(555); fails=0; n=500; cmax=0
    phases = [(1,0,8,8),(1,8,16,8),(8,0,4,16),(8,4,8,16)]  # rows0-7, rows8-15, cols0-3, cols4-7
    for t in range(n):
        b = rand_board(rng); cpu.set_board(b); cpu.mem[primitives.EV_SET]=0
        for st,ls,le,na in phases:
            cpu.mem[primitives.SU_STEP]=st; cpu.mem[primitives.SU_LSTART]=ls
            cpu.mem[primitives.SU_LEND]=le; cpu.mem[primitives.SU_NALONG]=na
            cmax=max(cmax,cpu.call(addr))
        got = cpu.mem[primitives.EV_SET]; exp = g_setup(b)
        if got != exp:
            fails+=1
            if fails<=4: print(f"  t{t}: got={got} exp={exp}")
    print(f"setup_rg(4 regions): {n-fails}/{n} match  per-region cyc_max={cmax}")
    sys.exit(1 if fails else 0)
if __name__=="__main__": main()
