#!/usr/bin/env python3
"""G3 TIER-1 ROM half, part 3: per-board-class geometry verification.
For each bank fo profile: does ONE held edge (correct direction, from t=0)
un-ledge the capsule and leave the throat (0,3)/(0,4) free at lock?  MED ups0
(W=20) so the edge always lands -- this isolates GEOMETRY from tempo."""
import json, sys
import nespatch  # noqa: F401
from nes_py import NESEnv

ROM = "/home/struktured/projects/dr-mario-mods/drmario.nes"
R, L, ST, SEL = 0x80, 0x40, 0x08, 0x04
MODE, NBP = 0x46, 0x0727
P1 = dict(X=0x0305, Y=0x0306, NEXTACT=0x0317, VLEFT=0x0324, SPDUPS=0x030A, SPDSET=0x030B)
FIELD1, FIELD2 = 0x0400, 0x0500

env = NESEnv(ROM); env.reset(); ram = env.ram

def step(act=0, n=1):
    for _ in range(n):
        ram[P1["SPDSET"]], ram[P1["SPDUPS"]] = 1, 0
        env.step(int(act))

def nav():
    step(0, 240); step(SEL, 2); step(0, 10); assert ram[NBP] == 2
    step(ST, 2); step(0, 60); step(ST, 2); step(0, 120)
    for _ in range(600):
        if ram[MODE] == 4: return
        step(0, 1)
    raise RuntimeError("no mainLoop")

def paint(fo):
    for c in range(8):
        for r in range(16):
            ram[FIELD1 + r*8 + c] = ((r + c) % 3) | 0x40 if r >= fo[c] else 0xFF
    ram[FIELD1 + 15*8] = (15 % 3) | 0xD0 if fo[0] <= 15 else ram[FIELD1 + 15*8]
    ram[P1["VLEFT"]] = 9
    for i in range(128):
        ram[FIELD2 + i] = 0xFF
    ram[0x03A4] = 9

NEUTRAL = [10, 10, 10, 16, 16, 10, 10, 10]

BANK = {
    "synth_L4f1":         ([13, 13, 13, 12, 1, 8, 8, 8], L),
    "synth_L3f1":         ([8, 8, 8, 1, 12, 13, 13, 13], R),
    "synth_L4f2":         ([13, 13, 13, 12, 2, 8, 8, 8], L),
    "synth_L3f2":         ([8, 8, 8, 2, 12, 13, 13, 13], R),
    "synth_L4f1_gateblk": ([13, 13, 0, 12, 1, 8, 8, 8], L),
    "synth_L4f1_gateblk_R": ([13, 13, 0, 12, 1, 8, 8, 8], R),
    "synth_B34f1":        ([10, 10, 10, 1, 1, 10, 10, 10], L),
    "synth_B34f2":        ([10, 10, 10, 2, 2, 10, 10, 10], L),
    "synth_none":         ([0, 0, 0, 1, 1, 0, 0, 0], L),
    "synth_L4f1_shallow": ([4, 4, 4, 3, 1, 8, 8, 8], L),
    "vetog1_archetype":   ([14, 12, 13, 12, 1, 1, 2, 2], L),
    "g3_shape":           ([13, 13, 12, 1, 3, 0, 7, 8], L),
}

out = []
nav()
for nm, (fo, act) in BANK.items():
    g = 0
    while ram[P1["NEXTACT"]] != 0 and g < 3000: step(0, 1); g += 1
    while ram[P1["NEXTACT"]] == 0 and g < 6000: step(0, 1); g += 1
    paint(fo)
    while ram[P1["NEXTACT"]] != 0 and g < 9000: step(0, 1); g += 1
    tr = []
    while g < 12000:
        g += 1
        step(act, 1)
        tr.append(dict(t=len(tr), y=int(ram[P1["Y"]]), x=int(ram[P1["X"]]),
                       na=int(ram[P1["NEXTACT"]])))
        if tr[-1]["na"] != 0: break
    tf = ram[FIELD1 + 3] == 0xFF and ram[FIELD1 + 4] == 0xFF
    fy = tr[-2]["y"] if len(tr) > 1 else None
    fx = tr[-2]["x"] if len(tr) > 1 else None
    paint(NEUTRAL)
    edges = [d["t"] for i, d in enumerate(tr[1:], 1) if d["x"] != tr[i-1]["x"]]
    one_edge_saves = bool(tf) and fy is not None and fy < 14 and len(edges) >= 1
    out.append(dict(name=nm, dir=("L" if act == L else "R"), edges=edges[:4],
                    lock_t=tr[-1]["t"], final_x=fx, final_y=fy,
                    throat_free=bool(tf)))
    print(f"{nm:22s} dir={'L' if act==L else 'R'} edges={edges[:3]} lock={tr[-1]['t']:4d} fx={fx} fy={fy} throat_free={tf}", file=sys.stderr)

json.dump(out, open("rom_geometry.json", "w"), indent=1, default=lambda o: bool(o))
print("wrote rom_geometry.json", file=sys.stderr)
