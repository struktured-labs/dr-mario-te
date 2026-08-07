#!/usr/bin/env python3
"""Self-seal candidate metrics as numba kernels over the (col, vir) int8[128]
board convention shared by fast_sim_x / root_search / terms47:
row-major idx = r*8 + c, row 0 = TOP, col 0 = empty / 1..3 = colour,
vir 1/0 flag.  Same call shape as terms47.g_stranded so these can drop into
the same root-only eval slot.

Two nested definitions, narrow -> broad:

n_sealed(col, vir)
    NARROW, matches portfolio/endgame-policy/seal_probe.py exactly: a virus at
    (r,c), r>0, is SEALED when the cell directly above is occupied, non-virus,
    and a DIFFERENT colour.  This is the metric the round-1 report measured.
    It is a proxy, not a blocker: a sealed virus can still be cleared by a
    horizontal match in its own row, which this definition cannot see.

n_noopen(col, vir)
    BROAD -- the colour-REACHABILITY generalisation the triage asked for.  A
    virus at (r,c) of colour k is clearable only through some length-4 line
    (window) containing it.  A window is OPEN if every cell in it is empty or
    already colour k (virus or pill both count -- the ROM clears mixed
    virus/pill lines).  A window holding any occupied cell of a different
    colour is BLOCKED until that cell is excavated.  A virus with ZERO open
    windows has no surviving route at all: strictly stronger than "sealed",
    and it subsumes lateral burial, which the narrow definition misses.

Both are pure functions of the post-placement board, so they price a CANDIDATE
by diffing against the pre-placement board (new seals = created by this move).
"""
from __future__ import annotations

from numba import njit, int8, int64


@njit(int64(int8[:], int8[:]), cache=True)
def n_sealed(col, vir):
    """Count viruses whose cell directly above is occupied non-virus material
    of a different colour (round-1's SEAL definition)."""
    n = 0
    for r in range(1, 16):
        for c in range(8):
            i = r * 8 + c
            if vir[i] == 0:
                continue
            j = i - 8
            if col[j] != 0 and vir[j] == 0 and col[j] != col[i]:
                n += 1
    return n


@njit(int64(int8[:], int8[:]), cache=True)
def n_noopen(col, vir):
    """Count viruses with NO open length-4 window (colour-reachability dead)."""
    n = 0
    for r in range(16):
        for c in range(8):
            i = r * 8 + c
            if vir[i] == 0:
                continue
            k = col[i]
            open_found = False
            # horizontal windows containing (r,c)
            s0 = c - 3
            if s0 < 0:
                s0 = 0
            s1 = c
            if s1 > 4:
                s1 = 4
            for s in range(s0, s1 + 1):
                ok = True
                for d in range(4):
                    v = col[r * 8 + s + d]
                    if v != 0 and v != k:
                        ok = False
                        break
                if ok:
                    open_found = True
                    break
            if not open_found:
                # vertical windows containing (r,c)
                t0 = r - 3
                if t0 < 0:
                    t0 = 0
                t1 = r
                if t1 > 12:
                    t1 = 12
                for t in range(t0, t1 + 1):
                    ok = True
                    for d in range(4):
                        v = col[(t + d) * 8 + c]
                        if v != 0 and v != k:
                            ok = False
                            break
                    if ok:
                        open_found = True
                        break
            if not open_found:
                n += 1
    return n


def warmup():
    import numpy as np
    z = np.zeros(128, dtype=np.int8)
    n_sealed(z, z)
    n_noopen(z, z)
