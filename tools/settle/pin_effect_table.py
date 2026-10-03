#!/usr/bin/env python3
"""How much does a cart's settle pin hold P2's capsule, per gravity threshold? (historical note for the owner)

For every speed setting (LOW/MED/HI) and speedUps value, one mid-round P2 spawn on an empty board is run twice in the
ROM-rule world of tests/test_gravity_fidelity.py: (A) with the REAL emitted driver hooked twice per frame (IR captured
from the emitter under the cart's flag set; the copro never answers, so the driver takes no action and the only thing
that can move the timing is a store into game RAM), and (B) the unmodified game, same pads (none). Reported: the
frame of the capsule's first natural 1-row drop after the spawn in A and B, the difference (frames held), and the same
in rows (frames / (thr + 1)), plus how many rows the capsule had fallen 12 frames after the spawn.
  pin_effect_table.py [arm ...]        (arms from test_gravity_fidelity.ARMS; default couch_464a4b75 couch_fair)
"""
import os, sys, random
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import test_gravity_fidelity as G
from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory


def first_drop(ir, sp, su, hooked, frames=200):
    base = G.fresh_mem(1)
    if hooked:
        for u in ir["units"].values():
            b = bytes.fromhex(u["bytes"]); base[u["base"]:u["base"] + len(b)] = list(b)
    mem = ObservableMemory(subject=base)
    never = lambda addr: {0x84: 0, 0x85: 0, 0x86: 0xFF, 0x87: 0xFF, 0x88: 0}.get(addr - 0x5200)
    mem.subscribe_to_read(range(0x5284, 0x5289), never)
    mpu = MPU(memory=mem)
    entry = ir["units"]["main"]["base"] + ir["units"]["main"]["labels"]["main"]
    w = G.World(random.Random(1), base)
    for i in range(128):
        base[G.BOARD + i] = 0xFF                           # empty board: no ledge, no PROPH
    base[G.SP], base[G.SU] = sp, su
    base[G.Y2] = 5; base[G.NA] = 6; w.throw_in = 0           # previous pill locked low; sendPill next frame
    hook_lasty = base[G.Y2]
    base[0x6155] = hook_lasty                              # LASTY2: the driver has seen the old pill
    spawn_f = drop_f = None
    rows12 = None

    def hook():
        mpu.sp = 0xFD; r = 0x3000 - 1
        base[0x1FE] = r & 0xFF; base[0x1FF] = (r >> 8) & 0xFF; mpu.pc = entry; base[0x3000] = 0xEA
        while mpu.pc != 0x3000:
            mpu.step()
    for f in range(frames):
        base[0x43] = f & 0xFF
        if hooked:
            for _ in (1, 2):
                base[0xF6] = 0; base[0xF5] = 0; hook()
            base[0xF6] = 0; base[0xF8] = 0                 # whatever the driver asked for: no buttons reach the game
        w.step(f, 0, 0)
        if spawn_f is None and base[G.NA] == 3:
            spawn_f = f
        if spawn_f is not None and f - spawn_f == 12:
            rows12 = 15 - base[G.Y2]
        if spawn_f is not None and drop_f is None and base[G.Y2] < 15:
            drop_f = f
        if drop_f is not None and rows12 is not None:
            break
    return drop_f - spawn_f, rows12


def main():
    arms = sys.argv[1:] or ["couch_464a4b75", "couch_fair"]
    irs = {a: G.capture(G.ARMS[a][0], G.ARMS[a][1], a)[0] for a in arms}
    print(f"{'speed':5s} {'spu':>3s} {'thr':>3s} | {'unmod drop':>10s} | " +
          " | ".join(f"{a + ' drop':>20s} {'held f':>6s} {'held rows':>9s}" for a in arms))
    for sp, sname in ((0, "LOW"), (1, "MED"), (2, "HI")):
        for su in (0, 5, 10, 20, 30, 40, 49):
            thr = G.SPEED_TABLE[min(80, G.SPEED_BASE[sp] + su)]
            b, _ = first_drop(irs[arms[0]], sp, su, hooked=False)
            row = f"{sname:5s} {su:3d} {thr:3d} | {b:10d} | "
            cells = []
            for a in arms:
                d, _ = first_drop(irs[a], sp, su, hooked=True)
                cells.append(f"{d:20d} {d - b:6d} {(d - b) / (thr + 1):9.2f}")
            print(row + " | ".join(cells))


if __name__ == "__main__":
    main()
