#!/usr/bin/env python3
"""End-to-end wiring validation for EMIT_TUCK_BFS: reset@$BF80 -> stub -> DONE, through
py65's RTL-engine emulation (attach_engine_emu), mirroring build_copro_d3.py's own main()
validation #2. Does not write any files (no .hex/.rbf touched)."""
import sys
import os
import importlib.util
import hashlib

HERE = "/home/struktured/projects/dr-mario-canonical-wt/fpga/copro"
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))

_spec = importlib.util.spec_from_file_location(
    "test_search_d3", os.path.join(ROOT, "tests", "test_search_d3.py"))
D3mod = importlib.util.module_from_spec(_spec)
sys.modules["test_search_d3"] = D3mod
_spec.loader.exec_module(D3mod)

import build_copro_d3 as B
assert B.D3 is D3mod
print(f"EMIT_TUCK_BFS={B.EMIT_TUCK_BFS} EMIT_TUCK_V3={B.EMIT_TUCK_V3}")

sys.path.insert(0, ROOT + "/tests")
from py65_harness import Cpu
from test_search_d3 import attach_engine_emu, S_BEST_C, S_BEST_O
from test_depth2 import S_CA, S_CB, S_NA, S_NB
sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src")
sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/tmp")
from drmario.faithful_game import FaithfulBoard
from xcheck_terms import faithful_to_nes
import nes_d3_golden as G3

import random
rng = random.Random(20260805)


def problem():
    fb = D3mod.make_fewlegal(rng, FaithfulBoard)
    ca, cb = rng.randint(1, 3), rng.randint(1, 3)
    na, nb = rng.randint(1, 3), rng.randint(1, 3)
    return list(faithful_to_nes(fb)), ca - 1, cb - 1, na - 1, nb - 1


b, cA, cB, nA, nB = problem()
img, clen, slen = B.build_image(b, cA, cB, nA, nB)
print(f"image built: search={clen}B stub={slen}B image_md5={hashlib.md5(bytes(img)).hexdigest()}")

cpu = Cpu()
for addr, v in enumerate(img):
    cpu.mem[addr] = v
cpu.set_board(b)
attach_engine_emu(cpu)
cpu.mem[S_CA] = cA
cpu.mem[S_CB] = cB
cpu.mem[S_NA] = nA
cpu.mem[S_NB] = nB
cpu.mem[B.DONE] = 0

m = cpu.mpu
m.pc = B.STUB
m.sp = 0xFF
MAX_STEPS = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000_000
steps = 0
reached = False
while steps < MAX_STEPS:
    m.step()
    steps += 1
    if cpu.mem[B.DONE] == 1:
        reached = True
        break

print(f"DONE reached={reached} after {steps/1e6:.1f}M steps")
if reached:
    best_c = cpu.mem[S_BEST_C]
    best_o = cpu.mem[S_BEST_O]
    tuck_col = cpu.mem[B.TUCK_COL]
    tuck_row = cpu.mem[B.TUCK_ROW]
    ts_cnt = cpu.mem[0x61F6]
    ts_drop = cpu.mem[0x61F7]
    print(f"S_BEST_C={best_c} S_BEST_O={best_o}")
    print(f"TUCK_COL={tuck_col} TUCK_ROW={tuck_row} "
          f"({'no tuck won' if tuck_col == 0xFF else 'a tuck won -- steering published'})")
    print(f"CANDLIST: TS_CNT={ts_cnt} TS_DROP={ts_drop}")
    exp = G3.decide_d3(b, cA, cB, nA, nB, topk1=D3mod.TOPK1, topk2=8, third=D3mod.THIRD)
    print(f"decide_d3 (base-only reference, no tuck knowledge): {exp}")
    ok = best_o != 0xFF
    print("SANE" if ok else "INSANE (no legal action found)")
else:
    print(f"DID NOT COMPLETE within {MAX_STEPS/1e6:.0f}M steps")
