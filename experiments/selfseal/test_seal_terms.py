#!/usr/bin/env python3
"""Correctness gate for seal_terms.n_sealed / n_noopen on hand-built boards.
Board: int8[128], idx = r*8+c, row 0 = TOP, col 0=empty 1..3=colour, vir 0/1."""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from seal_terms import n_sealed, n_noopen

FAILED = []


def board():
    return np.zeros(128, dtype=np.int8), np.zeros(128, dtype=np.int8)


def put(col, vir, r, c, colour, virus=False):
    col[r * 8 + c] = colour
    vir[r * 8 + c] = 1 if virus else 0


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got}, want {want}")
    if not ok:
        FAILED.append(name)


print("=== n_sealed ===")
c, v = board()
put(c, v, 5, 0, 1, virus=True)
put(c, v, 4, 0, 2)
check("wrong-colour pill directly above a virus = sealed", n_sealed(c, v), 1)

c, v = board()
put(c, v, 5, 0, 1, virus=True)
put(c, v, 4, 0, 1)
check("SAME-colour pill above = not sealed", n_sealed(c, v), 0)

c, v = board()
put(c, v, 5, 0, 1, virus=True)
put(c, v, 4, 0, 2, virus=True)
check("a VIRUS above is not sealing material", n_sealed(c, v), 0)

c, v = board()
put(c, v, 0, 3, 1, virus=True)
check("virus in row 0 can never be sealed", n_sealed(c, v), 0)

c, v = board()
put(c, v, 5, 0, 1, virus=True)
check("nothing above = not sealed", n_sealed(c, v), 0)

print("\n=== n_noopen ===")
c, v = board()
put(c, v, 8, 4, 1, virus=True)
check("lone virus on an empty board has open windows", n_noopen(c, v), 0)

# bottom-row virus, whole row blocked by a foreign colour, column clear above
c, v = board()
put(c, v, 15, 0, 1, virus=True)
for cc in range(1, 8):
    put(c, v, 15, cc, 2)
check("row blocked but column open = still reachable", n_noopen(c, v), 0)

# ... now block the column above it too
for rr in range(12, 15):
    put(c, v, rr, 0, 2)
check("row AND column blocked = no open window", n_noopen(c, v), 1)

# same-colour blockers do not block
c, v = board()
put(c, v, 15, 0, 1, virus=True)
for cc in range(1, 8):
    put(c, v, 15, cc, 1)
for rr in range(12, 15):
    put(c, v, rr, 0, 1)
check("same-colour neighbours never block", n_noopen(c, v), 0)

# a virus needs 4 cells of room: col 0 row 15 with rows 13,14 foreign and
# row 12 foreign leaves no vertical window, and the row is foreign too
c, v = board()
put(c, v, 15, 3, 1, virus=True)
for cc in (0, 1, 2, 4, 5, 6, 7):
    put(c, v, 15, cc, 2)
for rr in range(12, 15):
    put(c, v, rr, 3, 2)
check("mid-row virus fully walled = no open window", n_noopen(c, v), 1)

# two dead viruses count twice
c2 = c.copy(); v2 = v.copy()
put(c2, v2, 14, 7, 3, virus=True)
for rr in range(11, 14):
    put(c2, v2, rr, 7, 2)
put(c2, v2, 14, 4, 2); put(c2, v2, 14, 5, 2); put(c2, v2, 14, 6, 2)
check("two dead viruses count 2", n_noopen(c2, v2), 2)

# a sealed virus is NOT automatically no-open (the row can still clear it) --
# this is the distinction the whole investigation turns on
c, v = board()
put(c, v, 15, 2, 1, virus=True)
put(c, v, 14, 2, 2)          # sealed from directly above
check("sealed-from-above virus IS sealed", n_sealed(c, v), 1)
check("... but its row is still open, so NOT no-open", n_noopen(c, v), 0)

print()
if FAILED:
    print(f"*** {len(FAILED)} FAILURES: {FAILED}")
    sys.exit(1)
print("ALL CHECKS PASSED")
