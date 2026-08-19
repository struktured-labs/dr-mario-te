#!/usr/bin/env python3
"""Validation for tuck_bfs_6502.py (task #17 stage 4 6502 port).

Four levels, cheapest-first:
  1. tb_is_legal in isolation vs a direct python port of tuck_enum._legal_table.
  2. the full tuck_bfs routine vs proto_rowbfs.row_bfs (same algorithm,
     already proven equivalent to tuck_enum in proto_rowbfs.py) on random
     synthetic boards -- cheap, high volume, catches most bugs fast.
  3. the OFFICIAL bit-exact gate vs tuck_enum.enumerate(..., mode="free",
     union_straight_drops=False) directly (now including colours), on the
     200-board real-L11 corpus (tuck_bfs_corpus_200.json) -- this is the
     number the report cites. Also asserts no real board hits OUT_CAP.
  4. the capacity-64 depth-descending truncation policy itself, on a
     synthetic >64-candidate board the 200-board corpus can't exercise
     (its max was 56) -- overflow_board.json.

Run: python test_tuck_bfs_6502.py [--stage 1|2|3|4|all]
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


def reference_placements(grid, ca=1, cb=2):
    """The BFS's own reachable set (see reference_set) as raw tuck_enum
    placement dicts, still carrying col/row/orient/colors -- the form the
    capacity-policy simulation (expected_after_capacity) needs."""
    return [p for p in TE.enumerate(grid, ca, cb, mode="free",
                                     union_straight_drops=False)
            if p["reachable"]]


def reference_set(grid, ca=1, cb=2):
    """The canonical comparison target: the BFS's OWN reachable set, i.e.
    tuck_enum with union_straight_drops=False so it never adds the extra
    physically-unreachable straight-drop entries our pure-geometry BFS would
    never produce either. See tuck_bfs_6502.py's module docstring. Includes
    colours (tuck_enum's "colors" field) now that the port threads them
    through -- see stage 4."""
    return {(p["cells"], p["orient"], p["colors"])
            for p in reference_placements(grid, ca, cb)}


def expected_after_capacity(grid, ca=1, cb=2, cap=64):
    """Simulates the 6502 routine's OWN truncation policy (tb_emit_phase,
    descending row y, ascending x*4+o within a row, stop at `cap`) against
    the full reference set, so the overflow test (stage 4b) can assert the
    6502 output matches this EXACT selection, not just "some 64 of them"."""
    placements = reference_placements(grid, ca, cb)
    placements.sort(key=lambda p: (-p["row"], p["col"] * 4 + p["orient"]))
    kept = placements[:cap]
    return {(p["cells"], p["orient"], p["colors"]) for p in kept}


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
    """Returns (n, [(cells, orient, (ca, cb)), ...])."""
    n = cpu.zp(TB.BFS_OUTN)
    out = []
    for i in range(n):
        x = cpu.mem[TB.BFS_OUT_X + i]
        y = cpu.mem[TB.BFS_OUT_Y + i]
        o = cpu.mem[TB.BFS_OUT_O + i]
        ca = cpu.mem[TB.BFS_OUT_CA + i]
        cb = cpu.mem[TB.BFS_OUT_CB + i]
        cells = (y, x, y, x + 1) if _IS_H[o] else (y - 1, x, y, x)
        out.append((cells, o, (ca, cb)))
    return n, out


def call_bfs(cpu, addr, grid, ca, cb, max_steps=4_000_000):
    cpu.set_board(fb_to_nes(grid))
    cpu.set_zp(TB.PILL_A, ca)
    cpu.set_zp(TB.PILL_B, cb)
    return cpu.call(addr, max_steps=max_steps)


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
        ca, cb = 1, 2
        cyc = call_bfs(cpu, addr, grid, ca, cb)
        cyc_tot += cyc
        cyc_max = max(cyc_max, cyc)
        _, cand = read_candidates(cpu, a)
        got = set(cand)
        exp = reference_set(grid, ca, cb)
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
    call_bfs(cpu, addr, cave, 1, 2)
    _, cand = read_candidates(cpu, a)
    got_cells = {c for c, o, colors in cand}
    ok = all(cc in got_cells for cc in TE.CAVE_CELLS)
    exp = reference_set(cave, 1, 2)
    match = set(cand) == exp
    print(f"[stage2] cave board: CAVE_CELLS found={ok} full-set-match={match}")
    return ok and match


# ============================================================ stage 3 =====
def stage3_corpus_gate(corpus_path):
    """Bit-exact gate (cells+orient+colours) AND the capacity-64 "no real
    board overflows" check (deliverable 2a) in one pass: any board whose
    candidate count lands exactly at OUT_CAP is flagged for manual review,
    since plain set-equality can't distinguish "board has exactly 64
    candidates" from "board has >64 and got silently capacity-truncated"."""
    with open(corpus_path) as f:
        corpus = json.load(f)
    a = TB.build()
    code = a.assemble()
    addr = a.base + a.labels["tuck_bfs"]
    cpu = Cpu()
    cpu.load(a.base, code)
    bad = 0
    at_cap = 0
    cyc_list = []
    cand_counts = []
    for rec in corpus["boards"]:
        grid = rec["col"]
        ca, cb = rec["ca"], rec["cb"]
        cyc = call_bfs(cpu, addr, grid, ca, cb)
        cyc_list.append(cyc)
        n, cand = read_candidates(cpu, a)
        cand_counts.append(n)
        if n >= TB.OUT_CAP:
            at_cap += 1
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
    print(f"[stage3] BIT-EXACT GATE (cells+orient+colours): "
          f"{n - bad}/{n} boards match exactly")
    print(f"  cycles/board: min={cyc_list[0]} "
          f"median={cyc_list[len(cyc_list)//2]} max={cyc_list[-1]}")
    print(f"  candidates/board: min={cand_counts[0]} "
          f"median={cand_counts[len(cand_counts)//2]} max={cand_counts[-1]}  "
          f"(cap={TB.OUT_CAP}, boards at/over cap={at_cap})")
    print(f"  code size: {len(code)} bytes")
    return bad == 0 and at_cap == 0, {
        "n": n, "bad": bad, "cycles": cyc_list, "candidates": cand_counts,
        "code_bytes": len(code), "at_cap": at_cap}


# ============================================================ stage 4 =====
def stage4_overflow(overflow_path):
    """Synthetic board with >64 reachable candidates (found by sparse-random
    search over ~8000 boards, see tests/overflow_board.json's provenance in
    TUCK_BFS_PORT_REPORT.md) -- tests the depth-descending capacity policy
    itself, which the 200-board real corpus can't (its max was 56 < 64)."""
    with open(overflow_path) as f:
        grid = json.load(f)
    ca, cb = 1, 2
    full = reference_set(grid, ca, cb)
    print(f"[stage4] overflow board: {len(full)} reachable candidates "
          f"(cap={64 if TB.OUT_CAP == 64 else TB.OUT_CAP}) "
          f"-- {'OK, exceeds cap' if len(full) > TB.OUT_CAP else 'WARNING: does not exceed cap, test is not exercising truncation'}")

    a = TB.build()
    code = a.assemble()
    addr = a.base + a.labels["tuck_bfs"]
    cpu = Cpu()
    cpu.load(a.base, code)
    call_bfs(cpu, addr, grid, ca, cb)
    n, cand = read_candidates(cpu, a)
    got = set(cand)
    exp = expected_after_capacity(grid, ca, cb, cap=TB.OUT_CAP)

    at_cap = (n == TB.OUT_CAP)
    match = got == exp

    def anchor_row(cells, o):
        # H/RH: cells=(y,x,y,x+1) -> anchor y=cells[0]. V/RV: cells=(y-1,x,y,x)
        # -> anchor (bottom cell) y=cells[2].
        return cells[0] if _IS_H[o] else cells[2]

    # sanity: every kept candidate's row should be >= every dropped
    # candidate's row (depth-descending priority -- deep rows survive).
    dropped = full - got
    got_rows = {anchor_row(cells, o) for cells, o, colors in got}
    dropped_rows = {anchor_row(cells, o) for cells, o, colors in dropped}
    min_kept_row = min(got_rows) if got_rows else None
    max_dropped_row = max(dropped_rows) if dropped_rows else None
    priority_ok = (max_dropped_row is None or min_kept_row is None
                   or max_dropped_row <= min_kept_row)
    print(f"[stage4] n={n} at_cap={at_cap} exact-selection-match={match} "
          f"depth-priority-respected={priority_ok} "
          f"(dropped={len(dropped)}, min_kept_row={min_kept_row}, "
          f"max_dropped_row={max_dropped_row})")
    return at_cap and match and priority_ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all")
    ap.add_argument("--corpus", default=os.path.join(
        os.path.dirname(__file__), "tuck_bfs_corpus_200.json"))
    ap.add_argument("--overflow", default=os.path.join(
        os.path.dirname(__file__), "overflow_board.json"))
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
    if a.stage in ("4", "all"):
        if os.path.exists(a.overflow):
            ok &= stage4_overflow(a.overflow)
        else:
            print(f"[stage4] SKIPPED: overflow board not found at {a.overflow}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
