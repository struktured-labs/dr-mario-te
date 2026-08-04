#!/usr/bin/env python3
"""Task #47: the two candidate eval terms for the abandoned-material blind spot,
as numba kernels over the int8[128] (col, vir) board convention (root_search /
fast_sim_x world: col 0=empty 1..3=colour, vir 0/1, row-major r*8+c, row 0 = TOP).

Design per the task spec (user's accounting insight, 2026-08-03):

g_tower  -- HEIGHT-CONSUMPTION price. The eval prices what a placement COVERS
  (buried48) but not what it CONSUMES: remaining column height is the scarce
  resource, and the spawn lane (cols 3-4) is the scarcest. Charges each
  NON-VIRUS cell sitting above height H0 a superlinear fee (h-H0)^2, doubled in
  the spawn lane. Virus cells are never charged (the given field is not the
  AI's debt). Superlinearity makes the disposal funnel self-limiting: the
  second brick on a tower costs more than the first.

g_stranded -- STRANDED-HALF count. A non-virus cell with NO same-colour
  orthogonal neighbour is dead weight: it can never participate in a match
  without first being excavated or having material added purely to rescue it.
  Counts such cells. (Deliberately colour-blind to viruses-as-neighbours being
  targets: a pill half TOUCHING a same-colour virus is exactly NOT stranded --
  the neighbour check includes virus cells, so that case is already excluded.)

Both are POST-PLACEMENT board features (same call convention as the eh terms
g_excav/g_hang): score = _root_value(...) - wt*g_tower - ws*g_stranded, applied
at ply-1 like the existing eh blend. NEGATIVE contribution = a cost, matching
the task's "one new cost term, no new rewards" shape.
"""
from __future__ import annotations

from numba import njit, int8, int64


@njit(int64(int8[:], int8[:], int64), cache=True)
def g_tower(col, vir, h0):
    """Sum over non-virus occupied cells above height h0 of (h-h0)^2, x2 for
    spawn-lane columns 3-4. Height h = 16 - row (row 0 = top, so a cell in row
    r sits h=16-r rows above the floor)."""
    pen = 0
    for c in range(8):
        mult = 2 if (c == 3 or c == 4) else 1
        for r in range(16):
            i = r * 8 + c
            if col[i] != 0 and vir[i] == 0:
                h = 16 - r
                if h > h0:
                    d = h - h0
                    pen += d * d * mult
    return pen


@njit(int64(int8[:], int8[:]), cache=True)
def g_stranded(col, vir):
    """Count of non-virus occupied cells with no same-colour orthogonal
    neighbour (virus or pill). Such a half can never match without excavation
    or rescue material."""
    n = 0
    for r in range(16):
        for c in range(8):
            i = r * 8 + c
            if col[i] == 0 or vir[i] != 0:
                continue
            k = col[i]
            ok = False
            if r > 0 and col[i - 8] == k:
                ok = True
            elif r < 15 and col[i + 8] == k:
                ok = True
            elif c > 0 and col[i - 1] == k:
                ok = True
            elif c < 7 and col[i + 1] == k:
                ok = True
            if not ok:
                n += 1
    return n
