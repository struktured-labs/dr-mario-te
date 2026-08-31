#!/usr/bin/env python3
"""fo=2 window: capsule spawns, falls one row at the first gravity tick, rests at
row1, locks at the second -> W_eff = 2*(table+1)?  MEASURE."""
import sys, json
import nespatch  # noqa: F401
from nes_py import NESEnv
ROM = "/home/struktured/projects/dr-mario-mods/drmario.nes"
R, L, ST, SEL = 0x80, 0x40, 0x08, 0x04
MODE, NBP = 0x46, 0x0727
P1 = dict(X=0x0305, Y=0x0306, NEXTACT=0x0317, VLEFT=0x0324, SPDUPS=0x030A, SPDSET=0x030B)
env = NESEnv(ROM); env.reset(); ram = env.ram
PIN = [1, 0]
def step(act=0, n=1):
    for _ in range(n):
        ram[P1["SPDSET"]], ram[P1["SPDUPS"]] = PIN
        env.step(int(act))
def nav():
    step(0, 240); step(SEL, 2); step(0, 10); assert ram[NBP] == 2
    step(ST, 2); step(0, 60); step(ST, 2); step(0, 120)
    for _ in range(600):
        if ram[MODE] == 4: return
        step(0, 1)
def paint(fo):
    for c in range(8):
        for r in range(16):
            ram[0x0400 + r*8 + c] = ((r + c) % 3) | 0x40 if r >= fo[c] else 0xFF
    ram[P1["VLEFT"]] = 9
    for i in range(128): ram[0x0500 + i] = 0xFF
    ram[0x03A4] = 9
NEUTRAL = [10, 10, 10, 16, 16, 10, 10, 10]
out = []
nav()
for fo, ups, nm in (([8,8,8,2,2,8,8,8], 0, "fo2_ups0"), ([8,8,8,2,2,8,8,8], 10, "fo2_ups10"),
                    ([8,8,8,2,4,8,8,8], 10, "fo2_fo4_ups10"), ([8,8,8,1,1,8,8,8], 10, "fo1_ups10_ctl")):
    PIN[:] = [1, ups]
    g = 0
    while ram[P1["NEXTACT"]] != 0 and g < 3000: step(0, 1); g += 1
    while ram[P1["NEXTACT"]] == 0 and g < 6000: step(0, 1); g += 1
    paint(fo)
    while ram[P1["NEXTACT"]] != 0 and g < 9000: step(0, 1); g += 1
    tr = []
    while g < 12000:
        g += 1; step(0, 1)
        tr.append(dict(t=len(tr), y=int(ram[P1["Y"]]), na=int(ram[P1["NEXTACT"]])))
        if tr[-1]["na"] != 0: break
    paint(NEUTRAL)
    ys = [d["y"] for d in tr]
    out.append(dict(name=nm, ups=ups, lock_t=tr[-1]["t"], y_drops=[t for t in range(1, len(ys)) if ys[t] != ys[t-1]]))
    print(nm, "ups", ups, "lock_t", tr[-1]["t"], "drops at", out[-1]["y_drops"], file=sys.stderr)
json.dump(out, open("rom_fo2.json", "w"), indent=1, default=lambda o: bool(o))
