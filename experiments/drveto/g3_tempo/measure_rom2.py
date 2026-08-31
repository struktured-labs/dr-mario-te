#!/usr/bin/env python3
"""G3 TIER-1 ROM half, part 2 (targeted follow-ups):
  E1p  pinned-speed W_slide for the cells the one-shot poke left dirty
  E6   P2-side spawn anatomy symmetry (ywrite head start on the P2 vars)
  E7   press-edge burn: a direction held from BEFORE pillFalling loses its
       press edge -> first move costs the full 16f DAS engage (Fix-B trap)
"""
import json, sys
import nespatch  # noqa: F401
from nes_py import NESEnv

ROM = "/home/struktured/projects/dr-mario-mods/drmario.nes"
R, L, D, U, ST, SEL = 0x80, 0x40, 0x20, 0x10, 0x08, 0x04
MODE, NBP = 0x46, 0x0727
P1 = dict(X=0x0305, Y=0x0306, NEXTACT=0x0317, SPDCNT=0x0312, SPDUPS=0x030A,
          SPDSET=0x030B, PILLS=0x0327, VLEFT=0x0324)
P2 = dict(X=0x0385, Y=0x0386, NEXTACT=0x0397)
FIELD1, FIELD2 = 0x0400, 0x0500
EU = [0x45,0x43,0x41,0x3F,0x3D,0x3B,0x39,0x37,0x35,0x33,0x31,0x2F,0x2D,0x2B,
      0x29,0x27,0x25,0x23,0x21,0x1F,0x1D,0x1B,0x19,0x17,0x15,0x13,0x12,0x11,
      0x10,0x0F,0x0E,0x0D,0x0C,0x0B,0x0A,0x09,0x09,0x08,0x08,0x07,0x07,0x06,
      0x06,0x05,0x05,0x05,0x05,0x05,0x05,0x05,0x05,0x05,0x05,0x05,0x05,0x04,
      0x04,0x04,0x04,0x04,0x03,0x03,0x03,0x03,0x03,0x02,0x02,0x02,0x02,0x02,
      0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x00]
BASE = {0: 0x0F, 1: 0x19, 2: 0x1F}

env = NESEnv(ROM); env.reset(); ram = env.ram
PIN = [1, 0]

def step(act=0, n=1):
    for _ in range(n):
        ram[P1["SPDSET"]], ram[P1["SPDUPS"]] = PIN
        env.step(int(act))

def nav():
    step(0, 240); assert ram[MODE] == 0
    step(SEL, 2); step(0, 10); assert ram[NBP] == 2
    step(ST, 2); step(0, 60); step(ST, 2); step(0, 120)
    for _ in range(600):
        if ram[MODE] == 4: return
        step(0, 1)
    raise RuntimeError("no mainLoop")

def paint(fo, viruses=((15, 0),)):
    for c in range(8):
        for r in range(16):
            ram[FIELD1 + r*8 + c] = ((r + c) % 3) | 0x40 if r >= fo[c] else 0xFF
    for (r, c) in viruses:
        ram[FIELD1 + r*8 + c] = ((r + c) % 3) | 0xD0
    ram[P1["VLEFT"]] = 9
    for i in range(128):
        ram[FIELD2 + i] = 0xFF
    ram[0x03A4] = 9

PLUG34 = [8, 8, 8, 1, 1, 8, 8, 8]
LEDGE4 = [13, 13, 13, 12, 1, 8, 8, 8]
NEUTRAL = [10, 10, 10, 16, 16, 10, 10, 10]

def between_pills_then_paint(fo):
    g = 0
    while ram[P1["NEXTACT"]] != 0 and g < 3000: step(0, 1); g += 1
    while ram[P1["NEXTACT"]] == 0 and g < 6000: step(0, 1); g += 1
    assert g < 6000
    paint(fo)

def trace(policy, pre_policy=None, max_frames=900):
    tr, g = [], 0
    while ram[P1["NEXTACT"]] != 0 and g < 3000:
        step(pre_policy(g) if pre_policy else 0, 1); g += 1
    assert g < 3000
    tr.append(dict(t=0, y=int(ram[P1["Y"]]), x=int(ram[P1["X"]]), sc=int(ram[P1["SPDCNT"]]), na=0))
    while g < 3000 + max_frames:
        g += 1
        step(policy(len(tr) - 1), 1)
        d = dict(t=len(tr), y=int(ram[P1["Y"]]), x=int(ram[P1["X"]]),
                 sc=int(ram[P1["SPDCNT"]]), na=int(ram[P1["NEXTACT"]]))
        tr.append(d)
        if d["na"] != 0: break
    return tr

out = {"E1p": [], "E6": [], "E7": []}
nav()

# E1p: pinned sweep, full grid incl. the dirty LOW cells
for setting in (1, 2, 0):
    for ups in (0, 5, 10, 15, 20, 25, 30, 40, 49):
        PIN[:] = [setting, ups]
        between_pills_then_paint(PLUG34)
        tr = trace(lambda t: 0)
        paint(NEUTRAL)
        idx = BASE[setting] + ups
        pred = EU[idx] + 1 if idx < len(EU) else 1
        out["E1p"].append(dict(setting=setting, ups=ups, idx=idx, pred=pred,
                               W=tr[-1]["t"], match=tr[-1]["t"] == pred))
        print(f"E1p s={setting} u={ups} idx={idx} pred={pred} W={tr[-1]['t']}", file=sys.stderr)
PIN[:] = [1, 0]

# E6: P2 spawn anatomy (P2 uninvolved w/ inputs; its field is empty)
seen = []
lastY, lastNA = int(ram[P2["Y"]]), int(ram[P2["NEXTACT"]])
ywf = None; f = 0
while len(seen) < 3 and f < 5000:
    step(0, 1); f += 1
    y, na = int(ram[P2["Y"]]), int(ram[P2["NEXTACT"]])
    if y >= 14 and lastY < 12 and ywf is None: ywf = f
    if na == 0 and lastNA != 0:
        seen.append(dict(ywrite_pre=(f - ywf) if ywf else None)); ywf = None
    lastY, lastNA = y, na
out["E6"] = seen
print("E6 p2 ywrite_pre:", seen, file=sys.stderr)

# E7: held-from-before-spawn burns the edge
for nm, pre in (("held_prespawn", lambda g: L), ("no_prehold", None)):
    between_pills_then_paint(LEDGE4)
    tr = trace(lambda t: L, pre_policy=pre)
    paint(NEUTRAL)
    moves = [d["t"] for i, d in enumerate(tr[1:], 1) if d["x"] != tr[i-1]["x"]]
    out["E7"].append(dict(mode=nm, edges=moves[:4], lock_t=tr[-1]["t"],
                          final_y=tr[-2]["y"] if len(tr) > 1 else None))
    print(f"E7 {nm} edges={moves[:4]} lock={tr[-1]['t']}", file=sys.stderr)

json.dump(out, open("rom_measurements2.json", "w"), indent=1,
          default=lambda o: bool(o))
print("wrote rom_measurements2.json", file=sys.stderr)
