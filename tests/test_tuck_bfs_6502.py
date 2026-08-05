#!/usr/bin/env python3
"""Validation for tuck_bfs_6502.py (task #17 stage 4 6502 port).

Three levels, cheapest-first:
  1. tb_is_legal in isolation vs a direct python port of tuck_enum._legal_table.
  2. the full tuck_bfs routine vs proto_rowbfs.row_bfs (same algorithm,
     already proven equivalent to tuck_enum in proto_rowbfs.py) on random
     synthetic boards -- cheap, high volume, catches most bugs fast.
  3. the OFFICIAL bit-exact gate vs tuck_enum.enumerate(..., mode="free",
     union_straight_drops=False) directly, on the 200-board real-L11 corpus
     (tuck_bfs_corpus_200.json) -- this is the number the report cites.

Run: python test_tuck_bfs_6502.py [--stage 1|2|3|all]
"""
import sys
import os
import json
import random
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from py65_harness import Cpu
import tuck_bfs_6502 as TB

sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/tmp/endgame")
sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/experiments")
from fb import ROWS, COLS, NCELL   # noqa: E402
import tuck_enum as TE             # noqa: E402

EMPTY = 0xFF
_IS_H = (True, False, True, False)


# ------------------------------------------------------- board conversion --
def fb_to_nes(grid):
    """FB convention (0=empty, 1..3=colour) -> NES tile bytes (EMPTY=$FF,
    occupied = colour byte, low nibble only matters for occupancy tests)."""
    return [EMPTY if c == 0 else c for c in grid]


def rand_board(rnd, empty_bias=False):
    grid = [0] * NCELL
    for c in range(COLS):
        h = rnd.randrange(0, 6) if empty_bias else rnd.randrange(0, ROWS + 1)
        for r in range(ROWS - h, ROWS):
            grid[r * COLS + c] = rnd.randint(1, 3)
    for _ in range(rnd.randrange(0, 20)):
        grid[rnd.randrange(1, ROWS) * COLS + rnd.randrange(0, COLS)] = 0
    grid[3] = 0
    grid[4] = 0
    return grid


def py_is_legal(grid, x, y, o):
    if _IS_H[o]:
        if x > COLS - 2:
            return False
        return grid[y * COLS + x] == 0 and grid[y * COLS + x + 1] == 0
    if grid[y * COLS + x] != 0:
        return False
    return y == 0 or grid[(y - 1) * COLS + x] == 0


def reference_set(grid, ca=1, cb=2):
    """The canonical comparison target: the BFS's OWN reachable set, i.e.
    tuck_enum with union_straight_drops=False so it never adds the extra
    physically-unreachable straight-drop entries our pure-geometry BFS would
    never produce either. See tuck_bfs_6502.py's module docstring."""
    return {(p["cells"], p["orient"])
            for p in TE.enumerate(grid, ca, cb, mode="free",
                                   union_straight_drops=False)
            if p["reachable"]}


# ============================================================ stage 1 =====
def stage1_is_legal(n=400, seed=1):
    a = TB.build()
    code = a.assemble()
    addr = a.base + a.labels["tb_is_legal"]
    cpu = Cpu()
    cpu.load(a.base, code)
    rnd = random.Random(seed)
    bad = 0
    checked = 0
    for i in range(n):
        grid = rand_board(rnd, empty_bias=(i % 3 == 0))
        cpu.set_board(fb_to_nes(grid))
        for _ in range(20):
            x = rnd.randrange(0, COLS)
            y = rnd.randrange(0, ROWS)
            o = rnd.randrange(0, 4)
            cpu.set_zp(TB.IL_X, x)
            cpu.set_zp(TB.IL_Y, y)
            cpu.set_zp(TB.IL_O, o)
            cpu.call(addr)
            got = cpu.mpu.a
            exp = 1 if py_is_legal(grid, x, y, o) else 0
            checked += 1
            if got != exp:
                bad += 1
                if bad <= 5:
                    print(f"  MISMATCH board={i} x={x} y={y} o={o} "
                          f"got={got} exp={exp}")
    print(f"[stage1] tb_is_legal: {checked} checks, {bad} mismatches")
    return bad == 0


# ============================================================ stage 2 =====
def read_candidates(cpu, a):
    n = cpu.zp(TB.BFS_OUTN)
    out = []
    for i in range(n):
        x = cpu.mem[TB.BFS_OUT_X + i]
        y = cpu.mem[TB.BFS_OUT_Y + i]
        o = cpu.mem[TB.BFS_OUT_O + i]
        cells = (y, x, y, x + 1) if _IS_H[o] else (y - 1, x, y, x)
        out.append((cells, o))
    return n, out


def stage2_random_boards(n=500, seed=2):
    a = TB.build()
    code = a.assemble()
    addr = a.base + a.labels["tuck_bfs"]
    cpu = Cpu()
    cpu.load(a.base, code)
    rnd = random.Random(seed)
    bad = 0
    cyc_max = 0
    cyc_tot = 0
    for i in range(n):
        grid = rand_board(rnd, empty_bias=(i % 3 == 0))
        cpu.set_board(fb_to_nes(grid))
        cyc = cpu.call(addr, max_steps=4_000_000)
        cyc_tot += cyc
        cyc_max = max(cyc_max, cyc)
        _, cand = read_candidates(cpu, a)
        got = set(cand)
        exp = reference_set(grid)
        if got != exp:
            bad += 1
            if bad <= 3:
                print(f"  MISMATCH board={i}: ref-only={sorted(exp - got)[:5]} "
                      f"got-only={sorted(got - exp)[:5]}")
    print(f"[stage2] tuck_bfs vs tuck_enum (random boards): "
          f"{n - bad}/{n} match, cycles max={cyc_max} avg={cyc_tot // n}")
    return bad == 0


def stage2_cave_board():
    a = TB.build()
    code = a.assemble()
    addr = a.base + a.labels["tuck_bfs"]
    cpu = Cpu()
    cpu.load(a.base, code)
    cave = TE._cave_board()
    cpu.set_board(fb_to_nes(cave))
    cpu.call(addr, max_steps=4_000_000)
    _, cand = read_candidates(cpu, a)
    got_cells = {c for c, o in cand}
    ok = all(cc in got_cells for cc in TE.CAVE_CELLS)
    exp = reference_set(cave)
    match = set(cand) == exp
    print(f"[stage2] cave board: CAVE_CELLS found={ok} full-set-match={match}")
    return ok and match


# ============================================================ stage 3 =====
def stage3_corpus_gate(corpus_path):
    with open(corpus_path) as f:
        corpus = json.load(f)
    a = TB.build()
    code = a.assemble()
    addr = a.base + a.labels["tuck_bfs"]
    cpu = Cpu()
    cpu.load(a.base, code)
    bad = 0
    cyc_list = []
    cand_counts = []
    for rec in corpus["boards"]:
        grid = rec["col"]
        ca, cb = rec["ca"], rec["cb"]
        cpu.set_board(fb_to_nes(grid))
        cyc = cpu.call(addr, max_steps=4_000_000)
        cyc_list.append(cyc)
        n, cand = read_candidates(cpu, a)
        cand_counts.append(n)
        got = set(cand)
        exp = reference_set(grid, ca, cb)
        if got != exp:
            bad += 1
            if bad <= 5:
                print(f"  MISMATCH board id={rec.get('id')}: "
                      f"ref-only={sorted(exp - got)[:5]} "
                      f"got-only={sorted(got - exp)[:5]}")
    n = len(corpus["boards"])
    cyc_list.sort()
    cand_counts.sort()
    print(f"[stage3] BIT-EXACT GATE: {n - bad}/{n} boards match exactly")
    print(f"  cycles/board: min={cyc_list[0]} "
          f"median={cyc_list[len(cyc_list)//2]} max={cyc_list[-1]}")
    print(f"  candidates/board: min={cand_counts[0]} "
          f"median={cand_counts[len(cand_counts)//2]} max={cand_counts[-1]}")
    print(f"  code size: {len(code)} bytes")
    return bad == 0, {"n": n, "bad": bad, "cycles": cyc_list,
                       "candidates": cand_counts, "code_bytes": len(code)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all")
    ap.add_argument("--corpus", default=os.path.join(
        os.path.dirname(__file__), "tuck_bfs_corpus_200.json"))
    a = ap.parse_args()
    ok = True
    if a.stage in ("1", "all"):
        ok &= stage1_is_legal()
    if a.stage in ("2", "all"):
        ok &= stage2_cave_board()
        ok &= stage2_random_boards()
    if a.stage in ("3", "all"):
        if os.path.exists(a.corpus):
            good, _ = stage3_corpus_gate(a.corpus)
            ok &= good
        else:
            print(f"[stage3] SKIPPED: corpus not found at {a.corpus}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
