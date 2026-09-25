#!/usr/bin/env python3
"""GATE for the cart side (DRREACHTX): the emitted nibble code, run under py65 for every (speed 0..2, speedUps 0..63),
produces exactly reach_6502.pack_nibbles, and the firmware decode (thr_from_nibbles) of the resulting mailbox bytes
equals the ROM speed table; the NB high nibble is never 0 (the old-cart marker). Also locates the emitted sequences
in a built cart: the nA and nB nibble blocks must each appear exactly `expect` times (handle() P2 + DRPRESTART)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "fpga", "copro"))
sys.path.append("/home/struktured/projects/dr-mario-mods/tests"); sys.path.append("/home/struktured/projects/dr-mario-mods")
os.chdir(ROOT)
import reach_6502 as RC
from py65_harness import Cpu
import patch_cartridge_copro as PC


def emitted(is_na):
    a = PC.Asm6502(0x8000) if hasattr(PC, "Asm6502") else None
    from patch_vs_cpu import Asm6502
    a = Asm6502(0x8000)
    PC._emit_reachtx_nibble(a, is_na); a.ins("RTS")
    return a.assemble()


def main():
    code_a, code_b = emitted(True), emitted(False)
    bad = 0; zero_marker = 0
    for sp in range(3):
        for su in range(64):
            outs = []
            for code in (code_a, code_b):
                cpu = Cpu(); cpu.load(0x8000, code)
                cpu.mem[0x038A], cpu.mem[0x038B] = su, sp
                cpu.call(0x8000, max_steps=1000)
                outs.append(cpu.mem[PC.TMPSEED])
            want = RC.pack_nibbles(sp, su)
            bad += int(tuple(outs) != want)
            zero_marker += int((outs[1] >> 4) == 0)
            if su <= 49:
                na, nb = outs[0] | 2, outs[1] | 1
                bad += int(RC.thr_from_nibbles(na, nb) != RC.SPEED_TABLE[min(80, RC.SPEED_BASE[sp] + su)])
    print(f"nibble code: {len(code_a) - 1}+{len(code_b) - 1} B; mismatches vs pack_nibbles/decode {bad}; NB-high zero {zero_marker}")
    ok = bad == 0 and zero_marker == 0
    if len(sys.argv) > 1:
        rom = open(sys.argv[1], "rb").read(); expect = int(sys.argv[2])
        ca, cb = code_a[:-1], code_b[:-1]
        na = sum(1 for i in range(len(rom)) if rom[i:i + len(ca)] == ca)
        nb = sum(1 for i in range(len(rom)) if rom[i:i + len(cb)] == cb)
        print(f"{sys.argv[1]}: nA block x{na}, nB block x{nb} (expect {expect} each)")
        ok &= na == expect and nb == expect
    print("GATE_REACHTX", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
