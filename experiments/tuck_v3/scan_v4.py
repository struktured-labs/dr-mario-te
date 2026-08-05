#!/usr/bin/env python3
"""#17 scan_v4 (iteration 2): the CONVERGED tuck enumerator, python reference.

Structure: v4 = ref_tuck_scan_v3 emissions VERBATIM (v3 parity by
construction) + a STAIRCASE-corridor extension for the deep class v3's
adjacent-approach rule misses.

Iteration-1 lesson (coverage gate FAIL): a FLAT corridor at one row with a
lateral budget over-admits massively (13,810 extras = 2.7x the union) —
real motion DESCENDS while sliding (frames_per_row=12 ~= K=2 columns per
row), so the feasible path is a STAIRCASE. The extension walks it: from
entry column(-pair) s at trigger row r toward target c, path row advances
one row per K columns crossed; every step's cell(s) must be open, and the
arrival column must be open from the arrival row down to the rest row rf.

Output format serves the mirror scorer: {"cells", "colors"} (+ witness
fields). capacity=None; firmware capacity policy is a later step.
"""
from __future__ import annotations

import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
QA_TUCK = "/home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation"
for _p in (HERE, QA_TUCK):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tuck_scan_v3_ref import (ref_tuck_scan_v3, candidate_cells, occ, first_occ,
                              first_occ2, ROWS, COLS, H, V, RH, RV)

K = 2
FLIP = {H: 0, V: 1, RH: 1, RV: 0}


def _reach_rows_h(board):
    """Row-sweep reach masks for the HORIZONTAL pair geometry: bit c set in
    reach[r] = the pair anchored at c (cells (r,c),(r,c+1)) can be at row r
    via any interleaving of falls and <=K lateral moves per row descended.
    open[r] bit c = both cells open. Row 0 seeds from open sky."""
    open_m = [0] * ROWS
    for r in range(ROWS):
        m = 0
        for c in range(COLS - 1):
            if not occ(board, r, c) and not occ(board, r, c + 1):
                m |= 1 << c
        open_m[r] = m
    # support mask: pair at (r,c) is SUPPORTED if either cell below is occupied
    sup = [0] * ROWS
    for r in range(ROWS):
        m = 0
        for c in range(COLS - 1):
            below = (r + 1 >= ROWS) or occ(board, r + 1, c) or occ(board, r + 1, c + 1)
            if below:
                m |= 1 << c
        sup[r] = m
    reach = [0] * ROWS
    prev = open_m[0]                      # anything open at the top row is enterable
    for r in range(ROWS):
        cur = (prev & open_m[r]) if r > 0 else open_m[0]
        for _ in range(K):
            cur |= ((cur << 1) | (cur >> 1)) & open_m[r]
        # supported-slide fixpoint: while resting on support, lateral moves are
        # free (no descent consumed) -- dilate within open&sup until stable
        for _ in range(COLS):
            nxt = cur | (((cur << 1) | (cur >> 1)) & open_m[r] & sup[r])
            if nxt == cur:
                break
            cur = nxt
        reach[r] = cur
        prev = cur
    return reach


def _reach_rows_v(board):
    """Same sweep for the VERTICAL pair (cells (r-1,c),(r,c)); bit c in
    open[r] = both cells open (r >= 1)."""
    open_m = [0] * ROWS
    for r in range(1, ROWS):
        m = 0
        for c in range(COLS):
            if not occ(board, r, c) and not occ(board, r - 1, c):
                m |= 1 << c
        open_m[r] = m
    sup = [0] * ROWS
    for r in range(1, ROWS):
        m = 0
        for c in range(COLS):
            below = (r + 1 >= ROWS) or occ(board, r + 1, c)
            if below:
                m |= 1 << c
        sup[r] = m
    reach = [0] * ROWS
    prev = open_m[1] if ROWS > 1 else 0
    for r in range(1, ROWS):
        cur = (prev & open_m[r]) if r > 1 else open_m[1]
        for _ in range(K):
            cur |= ((cur << 1) | (cur >> 1)) & open_m[r]
        for _ in range(COLS):
            nxt = cur | (((cur << 1) | (cur >> 1)) & open_m[r] & sup[r])
            if nxt == cur:
                break
            cur = nxt
        reach[r] = cur
        prev = cur
    return reach


def scan_v4(board, ca, cb):
    out = []
    seen = set()

    def emit(cells, colors, vert):
        key = (cells, colors)
        if key in seen:
            return
        seen.add(key)
        out.append({"cells": cells, "colors": colors, "vert": vert})

    # ---- v3 parity: emit ref_tuck_scan_v3's candidates verbatim ----
    v3c, _dropped = ref_tuck_scan_v3(board, capacity=10 ** 9)
    for cnd in v3c:
        r0, c0, r1, c1 = candidate_cells(cnd["target"], cnd["rest"], cnd["orient"])
        fp = FLIP[cnd["orient"]]
        col0, col1 = (ca, cb) if fp == 0 else (cb, ca)
        emit((r0, c0, r1, c1), (col0, col1), cnd["orient"] in (V, RV))

    # ---- reach-mask extension: any rest position whose CELL is row-sweep
    # reachable and which lies below the straight-drop line ----
    rh = _reach_rows_h(board)
    for c in range(COLS - 1):
        fc = first_occ2(board, c, c + 1)
        if fc == 0:
            continue
        sd = fc - 1
        for rf in range(sd + 1, ROWS):
            if occ(board, rf, c) or occ(board, rf, c + 1):
                continue
            if rf + 1 < ROWS and not occ(board, rf + 1, c) and not occ(board, rf + 1, c + 1):
                continue                       # not at rest (would fall further)
            if rh[rf] & (1 << c):
                for colors in {(ca, cb), (cb, ca)}:
                    emit((rf, c, rf, c + 1), colors, False)

    rv = _reach_rows_v(board)
    for c in range(COLS):
        fc = first_occ(board, c)
        if fc == 0:
            continue
        sd = fc - 1
        for rf in range(sd + 1, ROWS):
            if occ(board, rf, c) or occ(board, rf - 1, c):
                continue
            if rf + 1 < ROWS and not occ(board, rf + 1, c):
                continue
            if rv[rf] & (1 << c):
                for colors in {(ca, cb), (cb, ca)}:
                    emit((rf - 1, c, rf, c), colors, True)

    return out
