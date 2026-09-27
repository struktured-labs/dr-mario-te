#!/usr/bin/env python3
"""G3 tier-1 exploration: boot drmario.nes in nes_py, navigate to a 2P VS game,
and dump per-frame state so the measurement rig can anchor on real transitions."""
import sys
import nespatch  # noqa: F401  numpy-2 shim, must precede NESEnv use
import numpy as np
from nes_py import NESEnv

ROM = "/home/struktured/projects/dr-mario-mods/drmario.nes"
# nes_py controller bits
R, L, D, U, ST, SEL, B, A = 0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01

env = NESEnv(ROM)
env.reset()
ram = env.ram

def step(act=0, n=1, watch=None):
    for _ in range(n):
        env.step(act)
    if watch:
        print(watch, {k: hex(ram[a]) for k, a in watch.items()})

W = {"mode": 0x46, "nbP": 0x0727, "lvlP1": 0x0316, "next": 0x0317}
step(0, 240)   # boot + title fade-in
print("after boot: mode", hex(ram[0x46]), "nbP", ram[0x0727])
step(ST, 2); step(0, 60)
print("after START: mode", hex(ram[0x46]), "nbP", ram[0x0727])
# game select screen? toggle with SELECT, watch nbPlayers
for i in range(3):
    step(SEL, 2); step(0, 30)
    print(f"after SELECT x{i+1}: mode", hex(ram[0x46]), "nbP", ram[0x0727])
step(ST, 2); step(0, 90)
print("after START2: mode", hex(ram[0x46]), "nbP", ram[0x0727],
      "p1lvl", ram[0x0316], "p2lvl", ram[0x0396])
# options screen -> start game
step(ST, 2); step(0, 60)
print("after START3: mode", hex(ram[0x46]), "nbP", ram[0x0727])
for i in range(12):
    step(0, 30)
    print(f"+{(i+1)*30}f: mode", hex(ram[0x46]), "nextAct p1", hex(ram[0x0317]),
          "p1Y", ram[0x0306], "p1X", ram[0x0305], "pills", ram[0x0327],
          "vl1", ram[0x0324], "vl2", ram[0x03A4])
