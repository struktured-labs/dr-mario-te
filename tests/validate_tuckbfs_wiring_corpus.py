#!/usr/bin/env python3
"""Same end-to-end wiring validation as validate_tuckbfs_wiring.py, but driven from the
real 200-board L11 corpus (which has real candidate density) instead of make_fewlegal's
sparse synthetic boards.

KNOWN ISSUE (not root-caused, flagged rather than silently shipped): running this script's
own multi-board `for` loop in-process shows every board completing suspiciously fast
(~10-20K steps) with BFS_OUTN/TS_CNT/TS_DROP all reading 0 -- looks like DONE gets set (or
read as already set) almost immediately, before the search+tuck flow has actually run.
Isolating EACH board in its OWN subprocess (e.g. a bash `for` loop invoking a one-board
inline script per iteration, exactly like validate_tuckbfs_wiring.py's own single-board
path) does NOT reproduce this -- cross-checked against tests/translate_ref.py's
independently-validated prediction for corpus board id=0 (0 CANDLIST entries, 30 dropped)
and matched exactly, plus BFS_OUTN/TS_CNT+TS_DROP accounting checked out correctly across
6+ boards run this way (ids 0,20,40,60,80,100 -- see TUCK_BFS_PORT_REPORT.md). Suspected:
some state (py65's ObservableMemory from attach_engine_emu, or a closure inside it) isn't
properly scoped per-Cpu-instance across repeated in-process calls. Until root-caused,
treat this script's own output with suspicion and prefer per-board subprocess isolation
for anything that matters."""
import sys
import os
import json
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
import nes_d3_golden as G3

EMPTY = 0xFF


def fb_to_nes(grid):
    """FB (0=empty,1..3=colour) -> NES tile bytes for the search's own board format
    (occupied = capsule tile $40|colour; matches export_real_boards.py's to_host)."""
    return [EMPTY if c == 0 else (0x40 | (c - 1)) for c in grid]


with open(os.path.join(ROOT, "tests", "tuck_bfs_corpus_200.json")) as f:
    corpus = json.load(f)["boards"]

n_try = int(sys.argv[1]) if len(sys.argv) > 1 else 10
max_steps = int(sys.argv[2]) if len(sys.argv) > 2 else 200_000_000

any_candlist = False
any_tuck_won = False
for rec in corpus[:n_try]:
    grid = rec["col"]
    board = fb_to_nes(grid)
    cA, cB = rec["ca"] - 1, rec["cb"] - 1   # decide_d3/build_image use 0-based colours
    nA, nB = rec["ca"] - 1, rec["cb"] - 1   # next-pill unknown in the snapshot; reuse cur

    img, clen, slen = B.build_image(board, cA, cB, nA, nB)
    cpu = Cpu()
    for addr, v in enumerate(img):
        cpu.mem[addr] = v
    cpu.set_board(board)
    attach_engine_emu(cpu)
    cpu.mem[S_CA] = cA; cpu.mem[S_CB] = cB
    cpu.mem[S_NA] = nA; cpu.mem[S_NB] = nB
    cpu.mem[B.DONE] = 0
    m = cpu.mpu
    m.pc = B.STUB
    m.sp = 0xFF
    steps = 0
    reached = False
    while steps < max_steps:
        m.step()
        steps += 1
        if cpu.mem[B.DONE] == 1:
            reached = True
            break
    ts_cnt = cpu.mem[0x61F6]
    ts_drop = cpu.mem[0x61F7]
    tuck_col = cpu.mem[B.TUCK_COL]
    tuck_row = cpu.mem[B.TUCK_ROW]
    best_o = cpu.mem[S_BEST_O]
    if ts_cnt > 0:
        any_candlist = True
    if tuck_col != 0xFF:
        any_tuck_won = True
    print(f"board id={rec.get('id')}: reached={reached} steps={steps/1e6:.2f}M "
          f"TS_CNT={ts_cnt} TS_DROP={ts_drop} TUCK_COL={tuck_col} TUCK_ROW={tuck_row} "
          f"S_BEST_O={best_o}")

print(f"\nany board with TS_CNT>0: {any_candlist}")
print(f"any board where a tuck actually won (TUCK_COL!=0xFF): {any_tuck_won}")
