#!/usr/bin/env python3
"""Prototype of the row-wise fixed-point BFS I intend to port to 6502.

KEY INSIGHT: in tuck_enum's free-mode move set (Left/Right/Down/Rotate), row
y only ever INCREASES (via Down) and Left/Right/Rotate keep y fixed. There is
no "Up" move. So the reachable set can be computed row-major: close each row
under L/R/rotate to a fixed point, then push Down into row y+1, and repeat --
provably equivalent to full BFS reachability, and it avoids ever needing an
index >255 (each row is only 32 states: x in 0..7, o in 0..3).
"""
import sys
sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/tmp/endgame")
sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/experiments")
import random
from fb import FB, ROWS, COLS, NCELL
import tuck_enum as TE

H, V, RH, RV = 0, 1, 2, 3
IS_H = (True, False, True, False)


def is_legal(grid, x, y, o):
    if IS_H[o]:
        if x > COLS - 2:
            return False
        return grid[y * COLS + x] == 0 and grid[y * COLS + x + 1] == 0
    else:
        if grid[y * COLS + x] != 0:
            return False
        return y == 0 or grid[(y - 1) * COLS + x] == 0


def row_bfs(grid, left_kick=True):
    SPAWN_X, SPAWN_Y, SPAWN_O = 3, 0, H
    visited = [[False] * 32 for _ in range(ROWS)]   # visited[y][x*4+o]

    if not is_legal(grid, SPAWN_X, SPAWN_Y, SPAWN_O):
        return set()
    visited[SPAWN_Y][SPAWN_X * 4 + SPAWN_O] = True

    for y in range(ROWS):
        row = visited[y]
        changed = True
        passes = 0
        while changed:
            changed = False
            passes += 1
            for s in range(32):
                if not row[s]:
                    continue
                x, o = s >> 2, s & 3
                # Left
                if x > 0 and is_legal(grid, x - 1, y, o):
                    s2 = (x - 1) * 4 + o
                    if not row[s2]:
                        row[s2] = True; changed = True
                # Right
                if x < COLS - 1 and is_legal(grid, x + 1, y, o):
                    s2 = (x + 1) * 4 + o
                    if not row[s2]:
                        row[s2] = True; changed = True
                # Rotations (all 3 other orientations; order irrelevant to the SET)
                for no in range(4):
                    if no == o:
                        continue
                    tx = x - 1 if (IS_H[no] and x == COLS - 1) else x
                    if is_legal(grid, tx, y, no):
                        s2 = tx * 4 + no
                        if not row[s2]:
                            row[s2] = True; changed = True
                    elif left_kick and IS_H[no] and tx >= 1:
                        if is_legal(grid, tx - 1, y, no):
                            s2 = (tx - 1) * 4 + no
                            if not row[s2]:
                                row[s2] = True; changed = True
            if passes > 40:
                raise RuntimeError("row fixed point did not converge in 40 passes")
        # down-propagate
        if y < ROWS - 1:
            for s in range(32):
                if not row[s]:
                    continue
                x, o = s >> 2, s & 3
                if is_legal(grid, x, y + 1, o):
                    visited[y + 1][x * 4 + o] = True

    out = set()
    for y in range(ROWS):
        for s in range(32):
            if not visited[y][s]:
                continue
            x, o = s >> 2, s & 3
            clipped = (not IS_H[o]) and y == 0
            if clipped:
                continue
            if IS_H[o]:
                rest = (y == ROWS - 1 or grid[(y + 1) * COLS + x] != 0
                        or grid[(y + 1) * COLS + x + 1] != 0)
            else:
                rest = (y == ROWS - 1 or grid[(y + 1) * COLS + x] != 0)
            if rest:
                cells = (y, x, y, x + 1) if IS_H[o] else (y - 1, x, y, x)
                out.add((cells, o))
    return out


def rand_board(rnd):
    grid = [0] * NCELL
    for c in range(COLS):
        h = rnd.randrange(0, ROWS + 1)
        for r in range(ROWS - h, ROWS):
            grid[r * COLS + c] = rnd.randint(1, 3)
    for _ in range(rnd.randrange(0, 16)):
        grid[rnd.randrange(1, ROWS) * COLS + rnd.randrange(0, COLS)] = 0
    grid[3] = 0
    grid[4] = 0
    return grid


def main():
    rnd = random.Random(20260804)
    n = 500
    mismatches = 0
    total_ref = total_mine = 0
    for i in range(n):
        grid = rand_board(rnd)
        ref = {(p["cells"], p["orient"]) for p in TE.enumerate(grid, 1, 2, mode="free",
                                                                 union_straight_drops=False)
               if p["reachable"]}
        mine = row_bfs(grid)
        total_ref += len(ref)
        total_mine += len(mine)
        if ref != mine:
            mismatches += 1
            if mismatches <= 3:
                print(f"MISMATCH board {i}: ref-only={sorted(ref-mine)[:5]} "
                      f"mine-only={sorted(mine-ref)[:5]}")
    print(f"boards={n} mismatches={mismatches} "
          f"mean_ref={total_ref/n:.2f} mean_mine={total_mine/n:.2f}")

    # cave board sanity (known-by-hand tucks)
    cave = TE._cave_board()
    ref = {(p["cells"], p["orient"]) for p in TE.enumerate(cave, 1, 2, mode="free",
                                                             union_straight_drops=False)
           if p["reachable"]}
    mine = row_bfs(cave)
    print("cave board match:", ref == mine, "CAVE_CELLS subset:",
          all(any(mc == cave_cell for mc, mo in mine) for cave_cell in TE.CAVE_CELLS))


if __name__ == "__main__":
    main()
