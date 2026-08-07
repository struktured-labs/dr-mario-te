#!/usr/bin/env python3
"""Board features for the Mode-A / Mode-B point-of-no-return characterisation.

Board convention: int8[128] col/vir, row-major idx=r*8+c, row 0 = TOP, colours
1-based, vir 1/0 -- the root_search.board_flat_from_fb / fast_rtl_x world.

Everything here is a PURE FUNCTION OF THE BOARD, computable by a decider at
decision time. No lookahead, no game history -- the point is to ask whether a
positional feature could in principle see Mode-B doom ~30 plies out.
"""
from __future__ import annotations

import numpy as np

ROWS, COLS, NCELL = 16, 8, 128

FEATURES = [
    "virus_count", "buried_virus", "occ_cells",
    "max_h", "avg_h", "spawn_h", "spawn_headroom", "height_var",
    "holes", "stranded", "sealed", "noopen",
    "pollution_dead_colour", "virus_ready", "virus_isolated",
]


def col_heights(col):
    h = np.zeros(COLS, dtype=np.int64)
    for c in range(COLS):
        for r in range(ROWS):
            if col[r * COLS + c] != 0:
                h[c] = ROWS - r
                break
    return h


def n_holes(col):
    n = 0
    for c in range(COLS):
        top = ROWS
        for r in range(ROWS):
            if col[r * COLS + c] != 0:
                top = r
                break
        for r in range(top + 1, ROWS):
            if col[r * COLS + c] == 0:
                n += 1
    return n


def buried_virus(col, vir):
    """Viruses with at least one occupied cell somewhere above them."""
    n = 0
    for i in range(NCELL):
        if not vir[i]:
            continue
        r, c = divmod(i, 8)
        for rr in range(r):
            if col[rr * COLS + c] != 0:
                n += 1
                break
    return n


def pollution_dead_colour(col, vir):
    """Non-virus cells whose colour has NO remaining virus of that colour.
    Such material can never participate in a virus clear -- it is pure ballast,
    and unlike `stranded` it stays counted even when it has same-colour
    neighbours (a big monochrome raft of a dead colour is the worst case)."""
    live = set(int(col[i]) for i in range(NCELL) if vir[i])
    n = 0
    for i in range(NCELL):
        if col[i] != 0 and not vir[i] and int(col[i]) not in live:
            n += 1
    return n


def virus_ready_isolated(col, vir):
    """(ready, isolated): viruses WITH / WITHOUT a same-colour orthogonal
    neighbour. `isolated` is a virus nothing is yet building toward."""
    ready = iso = 0
    for i in range(NCELL):
        if not vir[i]:
            continue
        r, c = divmod(i, 8)
        k = col[i]
        hit = False
        if r > 0 and col[i - 8] == k:
            hit = True
        elif r < 15 and col[i + 8] == k:
            hit = True
        elif c > 0 and col[i - 1] == k:
            hit = True
        elif c < 7 and col[i + 1] == k:
            hit = True
        if hit:
            ready += 1
        else:
            iso += 1
    return ready, iso


def extract(col, vir):
    """-> dict of FEATURES. col/vir are int8[128] numpy arrays."""
    from terms47 import g_stranded
    from seal_terms import n_sealed, n_noopen

    h = col_heights(col)
    vc = int(sum(1 for i in range(NCELL) if vir[i]))
    occ = int(sum(1 for i in range(NCELL) if col[i] != 0))
    spawn_h = int(max(h[3], h[4]))
    ready, iso = virus_ready_isolated(col, vir)
    return {
        "virus_count": vc,
        "buried_virus": buried_virus(col, vir),
        "occ_cells": occ,
        "max_h": int(h.max()),
        "avg_h": float(h.mean()),
        "spawn_h": spawn_h,
        "spawn_headroom": 16 - spawn_h,
        "height_var": float(h.var()),
        "holes": n_holes(col),
        "stranded": int(g_stranded(col, vir)),
        "sealed": int(n_sealed(col, vir)),
        "noopen": int(n_noopen(col, vir)),
        "pollution_dead_colour": pollution_dead_colour(col, vir),
        "virus_ready": ready,
        "virus_isolated": iso,
    }
