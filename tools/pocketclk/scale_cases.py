#!/usr/bin/env python3
"""pocketclk lane: re-time a16mt case files (copro publish timelines from the Verilator co-sim at MiSTer's 85.909 MHz)
to another copro clock. The copro is a free-running 6502 + LeafEval on its own clock; the host only uploads the board,
pulses GO and polls the BRAM mailbox, and the NES CPU/PPU clock (21.477 MHz master) is the same on both cores. So every
copro event time since GO scales by f_mister / f_copro. Only sched.pubs[i][1] (frames since GO) and sched.done_f move;
answers, finals and tuck descriptors are unchanged.
Usage: scale_cases.py IN.lua OUT.lua [f_copro_MHz=54.66935836]"""
import re, sys
F_MISTER = 85.909088            # MiSTer emu PLL outclk_0 (rtl/pll/pll_0002.v), the co-sim reference
src, dst = sys.argv[1:3]
f = float(sys.argv[3]) if len(sys.argv) > 3 else 601.362942 / 11   # Pocket mf_pllbase VCO / C=11 (outclk_4)
k = F_MISTER / f
def pubs(m):
    return "pubs={" + re.sub(r"\{([0-9.]+),", lambda q: "{%.4f," % (float(q.group(1)) * k), m.group(1)) + "}"
n = [0, 0]
out = []
for ln in open(src):
    ln2 = re.sub(r"pubs=\{((?:\{[^{}]*\},?)*)\}", pubs, ln)
    ln2 = re.sub(r"done_f=([0-9.]+)", lambda q: "done_f=%.4f" % (float(q.group(1)) * k), ln2)
    n[0] += ln2 != ln; out.append(ln2)
open(dst, "w").writelines(out)
print(f"{src} -> {dst}: k={k:.5f}, {n[0]} case lines re-timed")
