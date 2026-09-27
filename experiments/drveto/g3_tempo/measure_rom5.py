#!/usr/bin/env python3
"""E8/E9: PULSED lateral presses (dir,0,dir,0,...) -- each raw appearance with
held==0 is a fresh press edge, velocity resets, move lands same/next frame.
If cadence ~1 col / 2 frames, the 2-edge classes (B34, g3-shape) become
escapable inside the DEATH-REGIME window (W=10), which held-DAS cannot do."""
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

def run_case(nm, fo, ups, policy):
    PIN[:] = [1, ups]
    g = 0
    while ram[P1["NEXTACT"]] != 0 and g < 3000: step(0, 1); g += 1
    while ram[P1["NEXTACT"]] == 0 and g < 6000: step(0, 1); g += 1
    paint(fo)
    while ram[P1["NEXTACT"]] != 0 and g < 9000: step(0, 1); g += 1
    tr = []
    while g < 12000:
        g += 1; step(policy(len(tr)), 1)
        tr.append(dict(t=len(tr), y=int(ram[P1["Y"]]), x=int(ram[P1["X"]]),
                       na=int(ram[P1["NEXTACT"]])))
        if tr[-1]["na"] != 0: break
    tf = ram[0x0403] == 0xFF and ram[0x0404] == 0xFF
    fy = tr[-2]["y"] if len(tr) > 1 else None
    edges = [d["t"] for i, d in enumerate(tr[1:], 1) if d["x"] != tr[i-1]["x"]]
    paint(NEUTRAL)
    res = dict(name=nm, ups=ups, edges=edges[:6], lock_t=tr[-1]["t"],
               final_y=fy, throat_free=bool(tf),
               escaped=bool(tf) and fy is not None and fy < 14)
    print(f"{nm:26s} ups={ups:2d} edges={edges[:5]} lock={tr[-1]['t']:4d} fy={fy} esc={res['escaped']}", file=sys.stderr)
    return res

pulse = lambda t: L if t % 2 == 0 else 0
hold = lambda t: L
out = []
nav()
out.append(run_case("pulse_ledge_ups0",  [13,13,13,12,1,8,8,8], 0, pulse))
out.append(run_case("pulse_B34f1_ups0",  [10,10,10,1,1,10,10,10], 0, pulse))
out.append(run_case("pulse_B34f1_ups10", [10,10,10,1,1,10,10,10], 10, pulse))
out.append(run_case("hold_B34f1_ups10",  [10,10,10,1,1,10,10,10], 10, hold))
out.append(run_case("pulse_g3shape_ups5", [13,13,12,1,3,0,7,8], 5, pulse))
out.append(run_case("pulse_g3shape_ups10",[13,13,12,1,3,0,7,8], 10, pulse))
out.append(run_case("hold_g3shape_ups10", [13,13,12,1,3,0,7,8], 10, hold))
out.append(run_case("pulse_g2shape_ups10",[3,8,8,2,4,0,0,2], 10, pulse))
out.append(run_case("pulse_far_traverse_ups0", [13,13,13,12,1,8,8,8], 0,
                    pulse))  # cadence read on the long walk
json.dump(out, open("rom_pulse.json", "w"), indent=1, default=lambda o: bool(o))
print("wrote rom_pulse.json", file=sys.stderr)
