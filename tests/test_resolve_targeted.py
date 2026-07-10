#!/usr/bin/env python3
"""Validate the NEW python targeted-resolve golden (_cap1_targeted in nes_d3_golden)
cell-exact vs the 6502 resolve_capped (find_clears_targeted + one gravity, no cascade).
Random boards + random legal placements; compares full board bytes + RV_CELLS/RV_VIR."""
import sys, random
HERE = "/home/struktured/projects/dr-mario-mods"
sys.path.insert(0, HERE + "/tests"); sys.path.insert(0, HERE)
import primitives as P
from patch_vs_cpu import Asm6502
from py65_harness import Cpu
from test_depth2 import _rand_board, emit_landplace, PO, PC, PCA, PCB
from nes_d2_golden import _landing, _place
from nes_d3_golden import _cap1_targeted

BOARD = 0x0500


def build():
    P.BOARD = BOARD; P.LIVE_BOARD = BOARD; P.MARK = 0x0780
    a = Asm6502(0x8000)
    a.label("go")
    a.jsr("land_place"); a.ins("CMP_imm", 1); a.br("BEQ", "leg"); a.ins("RTS")
    a.label("leg"); a.jsr("resolve_capped"); a.ins("RTS")
    emit_landplace(a)
    P.emit_first_occ(a); P.emit_find_clears(a); P.emit_gravity(a)
    P.emit_resolve_capped(a)
    return a.assemble(), a.labels


def main():
    code, labels = build()
    rng = random.Random(31); fails = 0; done = 0; N = 300
    for t in range(N):
        b = _rand_board(rng)
        o4 = rng.randint(0, 3); col = rng.randint(0, 7)
        orient = 0 if o4 < 2 else 1
        land = _landing(b, orient, col)
        if land is None:
            continue
        done += 1
        offa, offb = land
        ca, cb = rng.randint(0, 2), rng.randint(0, 2)
        ta, tb = (cb, ca) if (o4 & 1) else (ca, cb)
        # python golden
        gb = _place(b, offa, offb, ta, tb)
        gc, gv = _cap1_targeted(gb, offa, offb)
        # 6502
        cpu = Cpu(); cpu.load(0x8000, code); cpu.set_board(b)
        cpu.mem[PO] = o4; cpu.mem[PC] = col; cpu.mem[PCA] = ca; cpu.mem[PCB] = cb
        cpu.call(0x8000 + labels["go"], max_steps=3_000_000)
        eb = [cpu.mem[BOARD + i] for i in range(128)]
        ec, ev = cpu.mem[P.RV_CELLS], cpu.mem[P.RV_VIR]
        if eb != gb or (ec, ev) != (gc, gv):
            fails += 1
            if fails <= 5:
                bad = [i for i in range(128) if eb[i] != gb[i]][:8]
                print(f"  MISMATCH t={t} o4={o4} col={col}: rv 6502=({ec},{ev}) py=({gc},{gv}) cells{bad}")
    print(f"resolve_capped vs _cap1_targeted: {done-fails}/{done} match  ({'PASS' if not fails else 'FAIL'})")
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
