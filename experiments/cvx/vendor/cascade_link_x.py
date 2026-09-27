#!/usr/bin/env python3
"""LINK-AWARE leaf resolution -- the control that separates "cascading pays" from
"link-free gravity over-predicts cascades".

WHY THIS EXISTS.  `cascade_x` resolves leaves to fixpoint using the search's own
`_compact_gravity`, which drops every non-virus cell independently.  The engine drops
linked BODIES.  Measured on 1,704 real clearing placements (cascade_gravity_gap.py):

    placements whose cascade gains cells   model 24.06%   engine 7.22%
    extra cells from cascading             model 2,451    engine   542   = 4.52x
    extra viruses from cascading           model   401    engine   125   = 3.21x
    of the chains the model sees, only 30.0% are chains the engine delivers

So a compact-gravity fixpoint chases phantom chains 70% of the time.  A negative A/B on
`cascade_x` would therefore be ambiguous: cascading might be worthless, or the physics
model might be.  This module removes the ambiguity by carrying the link nibble through
the search and resolving with the engine's own body gravity.

    maxpass=1  link gravity, one round   -- the correct-physics BASELINE
    maxpass=0  link gravity, fixpoint    -- the correct-physics CASCADE arm

(maxpass=1 here is NOT the shipped path: shipped uses compact gravity even on pass 1.
It is the right baseline for isolating the cascade effect, and the compact-vs-link
pass-1 difference is a pre-existing modelling gap this lane did not introduce.)

PORTABILITY, CORRECTED.  The NES playfield byte is `high nibble = link direction, low
nibble = colour` (MECHANICS_NES.md), and `fast_rtl_x._decode_nes` already READS that
byte -- it just discards everything but the `$D` virus test.  So the link data reaches
the copro's input; it is the 3-bit internal cell encoding that throws it away.  A
link-aware port is an encoding-width problem (3 -> ~6 bits per cell, plus every eval
walk), not a missing-information problem.  The 6502 firmware path has the nibble
already.

The eval itself never sees links, so `_leafv_ship` and the whole delta machinery are
imported unchanged; only the mechanics differ.
"""
from __future__ import annotations
import numpy as np
from numba import njit, int8, int32, int64, float64

from fast_sim_x import ROWS, COLS, NCELL, _virus_count, _stable_desc, _resting

import fast_rtl_x as X
from fast_rtl_x import (
    R_WVIR, R_WCELLS, R_VBONUS, _WIN_SHIP,
    _VAR_OF_O4, _THIRD_X, _THIRD_Y, _W_EXCAV_SHIP, _W_HANG_SHIP,
    NBASE, NT, T_NVIR,
    _leafv_ship, _base_scan, _delta_terms, _combine_terms, _any_clear_lines,
    _g_excav_ship, _g_hang_ship,
    weights_rtl_r47, flags_r47, variant, board_flat,
)

LINK_NONE = 0
LINK_UP = 1
LINK_DOWN = 2
LINK_LEFT = 3
LINK_RIGHT = 4
# row/col deltas indexed by link code (0 unused)
_LDR = np.array([0, -1, 1, 0, 0], dtype=np.int64)
_LDC = np.array([0, 0, 0, -1, 1], dtype=np.int64)


# ------------------------------------------------------------------- mechanics
@njit(cache=True, fastmath=False)
def _apply_clear_linked(col, vir, lnk, mask):
    """`FaithfulBoard._apply_clear`: break links from SURVIVING partners that point into
    a cleared cell, then blank the cleared cells.  Returns viruses cleared."""
    nv = 0
    for idx in range(NCELL):
        if mask[idx] == 0:
            continue
        if vir[idx]:
            nv += 1
        lk = lnk[idx]
        if lk != LINK_NONE:
            r = idx // COLS; c = idx % COLS
            pr = r + _LDR[lk]; pc = c + _LDC[lk]
            if 0 <= pr < ROWS and 0 <= pc < COLS:
                pidx = pr * COLS + pc
                if mask[pidx] == 0:            # partner survives -> un-link it
                    lnk[pidx] = LINK_NONE
    for idx in range(NCELL):
        if mask[idx]:
            col[idx] = 0
            vir[idx] = 0
            lnk[idx] = LINK_NONE
    return nv


@njit(cache=True, fastmath=False)
def _link_gravity(col, vir, lnk):
    """`FaithfulBoard._apply_gravity`: repeatedly drop every unsupported rigid body
    (a single cell, or a linked pair), lowest bodies first, until nothing moves.

    Body enumeration order and the lowest-first stable sort are mirrored exactly,
    because which body moves first decides whether the one above it can follow in the
    same pass."""
    b0 = np.empty(NCELL, dtype=int64)
    b1 = np.empty(NCELL, dtype=int64)
    keys = np.empty(NCELL, dtype=float64)
    order = np.empty(NCELL, dtype=int32)
    seen = np.empty(NCELL, dtype=int8)
    while True:
        for i in range(NCELL):
            seen[i] = 0
        nb = 0
        for r in range(ROWS):                       # engine scan order: row, then col
            for c in range(COLS):
                idx = r * COLS + c
                if col[idx] == 0 or vir[idx] or seen[idx]:
                    continue
                lk = lnk[idx]
                if lk == LINK_NONE:
                    seen[idx] = 1
                    b0[nb] = idx; b1[nb] = -1
                    keys[nb] = float64(r)
                    nb += 1
                else:
                    pr = r + _LDR[lk]; pc = c + _LDC[lk]
                    ok = 0 <= pr < ROWS and 0 <= pc < COLS
                    pidx = pr * COLS + pc if ok else -1
                    if ok and seen[pidx] == 0:
                        seen[idx] = 1; seen[pidx] = 1
                        b0[nb] = idx; b1[nb] = pidx
                        keys[nb] = float64(r if r > pr else pr)
                        nb += 1
                    else:                            # dangling link -> treat as single
                        seen[idx] = 1
                        b0[nb] = idx; b1[nb] = -1
                        keys[nb] = float64(r)
                        nb += 1
        if nb == 0:
            break
        _stable_desc(keys, nb, order)                # lowest cells first, stable
        moved = False
        for s in range(nb):
            k = order[s]
            k0 = b0[k]; k1 = b1[k]
            # can this body fall?
            fall = True
            for t in range(2):
                kk = k0 if t == 0 else k1
                if kk < 0:
                    continue
                if kk // COLS + 1 >= ROWS:
                    fall = False
                    break
                nk = kk + COLS
                if nk != k0 and nk != k1 and col[nk] != 0:
                    fall = False
                    break
            if not fall:
                continue
            c0v = col[k0]; v0v = vir[k0]; l0v = lnk[k0]
            col[k0] = 0; vir[k0] = 0; lnk[k0] = LINK_NONE
            if k1 >= 0:
                c1v = col[k1]; v1v = vir[k1]; l1v = lnk[k1]
                col[k1] = 0; vir[k1] = 0; lnk[k1] = LINK_NONE
            col[k0 + COLS] = c0v; vir[k0 + COLS] = v0v; lnk[k0 + COLS] = l0v
            if k1 >= 0:
                col[k1 + COLS] = c1v; vir[k1 + COLS] = v1v; lnk[k1 + COLS] = l1v
            moved = True
        if not moved:
            break


@njit(cache=True, fastmath=False)
def _find_clears_mask(col, mask):
    """Full-board maximal runs >= 4, rows and columns, into `mask`.  Returns cell count."""
    for i in range(NCELL):
        mask[i] = 0
    for r in range(ROWS):
        i = 0
        while i < COLS:
            v = col[r * COLS + i]
            if v == 0:
                i += 1
                continue
            j = i
            while j < COLS and col[r * COLS + j] == v:
                j += 1
            if j - i >= 4:
                for k in range(i, j):
                    mask[r * COLS + k] = 1
            i = j
    for c in range(COLS):
        i = 0
        while i < ROWS:
            v = col[i * COLS + c]
            if v == 0:
                i += 1
                continue
            j = i
            while j < ROWS and col[j * COLS + c] == v:
                j += 1
            if j - i >= 4:
                for k in range(i, j):
                    mask[k * COLS + c] = 1
            i = j
    n = 0
    for i in range(NCELL):
        if mask[i]:
            n += 1
    return n


@njit(cache=True, fastmath=False)
def _resolve_linked(col, vir, lnk, mask, maxpass):
    """`FaithfulBoard.resolve` with a round cap.  maxpass<=0 = fixpoint.
    Returns (cells, viruses, chain)."""
    cells = 0
    nv = 0
    chain = 0
    while maxpass <= 0 or chain < maxpass:
        n = _find_clears_mask(col, mask)
        if n == 0:
            break
        chain += 1
        cells += n
        nv += _apply_clear_linked(col, vir, lnk, mask)
        _link_gravity(col, vir, lnk)
    return (cells, nv, chain)


@njit(cache=True, fastmath=False)
def _expand_linked(pcol, pvir, plnk, variant_, column, pa, pb,
                   ccol, cvir, clnk, mask, maxpass):
    """Clone parent, place the pill WITH ITS LINK, resolve under body gravity."""
    ok, r0, c0, r1, c1 = _resting(pcol, variant_, column)
    if ok == 0:
        return (0, 0, 0)
    for i in range(NCELL):
        ccol[i] = pcol[i]; cvir[i] = pvir[i]; clnk[i] = plnk[i]
    if variant_ == 0 or variant_ == 2:
        col0 = pa; col1 = pb
    else:
        col0 = pb; col1 = pa
    i0 = r0 * COLS + c0
    i1 = r1 * COLS + c1
    ccol[i0] = col0; ccol[i1] = col1
    cvir[i0] = 0; cvir[i1] = 0
    if variant_ < 2:                       # horizontal: (r,c) and (r,c+1)
        clnk[i0] = LINK_RIGHT; clnk[i1] = LINK_LEFT
    else:                                  # vertical: r0 = top, r1 = bottom
        clnk[i0] = LINK_DOWN; clnk[i1] = LINK_UP
    cells, nv, _ch = _resolve_linked(ccol, cvir, clnk, mask, maxpass)
    return (1, nv, cells)


# --------------------------------------------------- link-aware depth-3 (ship-shaped)
@njit(cache=True, fastmath=False)
def _leaf_linked(pcol, pvir, plnk, base, variant_, column, pa, pb, w, fl,
                 ccol, cvir, clnk, mask, terms, maxpass, want_board):
    """Leaf value + optional child board.  The NON-clearing case still uses the delta
    (links cannot change a leaf score -- the eval never reads them), so the delta
    machinery is reused verbatim and only clearing leaves pay the link-gravity cost."""
    ok, r0, c0, r1, c1 = _resting(pcol, variant_, column)
    if ok == 0:
        return (0, 0, 0, int64(0))
    if variant_ == 0 or variant_ == 2:
        col0 = pa; col1 = pb
    else:
        col0 = pb; col1 = pa
    i0 = r0 * COLS + c0
    i1 = r1 * COLS + c1
    # cheap existence test on a scratch copy of the two cells
    sv0 = pcol[i0]; sv1 = pcol[i1]
    pcol[i0] = col0; pcol[i1] = col1
    clearing = _any_clear_lines(pcol, r0, c0, r1, c1)
    pcol[i0] = sv0; pcol[i1] = sv1
    if clearing:
        _o, nv, cells = _expand_linked(pcol, pvir, plnk, variant_, column, pa, pb,
                                       ccol, cvir, clnk, mask, maxpass)
        return (1, nv, cells, _leafv_ship(ccol, cvir, w, fl))
    if want_board:
        for i in range(NCELL):
            ccol[i] = pcol[i]; cvir[i] = pvir[i]; clnk[i] = plnk[i]
        ccol[i0] = col0; ccol[i1] = col1
        cvir[i0] = 0; cvir[i1] = 0
        if variant_ < 2:
            clnk[i0] = LINK_RIGHT; clnk[i1] = LINK_LEFT
        else:
            clnk[i0] = LINK_DOWN; clnk[i1] = LINK_UP
        if base[T_NVIR] == 0:
            return (1, 0, 0, int64(_WIN_SHIP))
        _delta_terms(ccol, cvir, base, r0, c0, r1, c1, fl, terms)
        return (1, 0, 0, _combine_terms(terms, w))
    # value only: place in place, delta, restore
    pcol[i0] = col0; pcol[i1] = col1
    if base[T_NVIR] == 0:
        pcol[i0] = sv0; pcol[i1] = sv1
        return (1, 0, 0, int64(_WIN_SHIP))
    _delta_terms(pcol, pvir, base, r0, c0, r1, c1, fl, terms)
    val = _combine_terms(terms, w)
    pcol[i0] = sv0; pcol[i1] = sv1
    return (1, 0, 0, val)


@njit(cache=True, fastmath=False)
def _expected_third_linked(b2c, b2v, b2l, w, fl, base3, terms, tc, tv, tl, mask, maxpass):
    if _virus_count(b2v) == 0:
        return int64(_WIN_SHIP)
    _base_scan(b2c, b2v, fl, base3)
    tot = int64(0)
    for t in range(4):
        x = _THIRD_X[t]; y = _THIRD_Y[t]
        best3 = int64(0); have3 = False
        for o4 in range(4):
            var = _VAR_OF_O4[o4]
            for cl in range(8):
                ok, nv, cells, lv = _leaf_linked(b2c, b2v, b2l, base3, var, cl, x, y,
                                                 w, fl, tc, tv, tl, mask, terms,
                                                 maxpass, False)
                if ok == 0:
                    continue
                vv = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells \
                     + (int64(w[R_VBONUS]) if nv >= 2 else int64(0)) + lv
                if not have3 or vv > best3:
                    best3 = vv; have3 = True
        tot += best3 if have3 else _leafv_ship(b2c, b2v, w, fl)
    return tot // int64(4)


@njit(int64(int8[:], int8[:], int8[:], int64, int64, int64, int64, int64, int64, int64,
            float64[:], int32[:], int64), cache=True, fastmath=False)
def _choose_d3_linked(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang,
                      w, fl, maxpass):
    """Line-for-line `_choose_d3_ship_eh_delta` with link-carrying, body-gravity
    mechanics.  Enumeration order, tie-breaks, topk2 sort, DISC_SHIFT and the eh add-on
    are unchanged."""
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8)
    l1 = np.empty(NCELL, dtype=int8)
    b2col = np.empty((32, NCELL), dtype=int8); b2vir = np.empty((32, NCELL), dtype=int8)
    b2lnk = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64); imms2 = np.empty(32, dtype=int64)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8); s2v = np.empty(NCELL, dtype=int8)
    s2l = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8); e2v = np.empty(NCELL, dtype=int8)
    e2l = np.empty(NCELL, dtype=int8)
    tc = np.empty(NCELL, dtype=int8); tv = np.empty(NCELL, dtype=int8)
    tl = np.empty(NCELL, dtype=int8); mask = np.empty(NCELL, dtype=int8)
    base1 = np.empty(NBASE, dtype=int64); base2 = np.empty(NBASE, dtype=int64)
    base3 = np.empty(NBASE, dtype=int64); terms = np.empty(NT, dtype=int64)
    _base_scan(pcol, pvir, fl, base1)
    best_val = int64(0); best_act = -1; have = False
    for o4 in range(4):
        var = _VAR_OF_O4[o4]
        for cl in range(8):
            ok, nv, cells, leaf1 = _leaf_linked(pcol, pvir, plnk, base1, var, cl, ca, cb,
                                                w, fl, c1, v1, l1, mask, terms,
                                                maxpass, True)
            if ok == 0:
                continue
            imm1 = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells + (int64(w[R_VBONUS]) if nv >= 2 else int64(0))
            if _virus_count(v1) == 0:
                val = imm1 + int64(_WIN_SHIP)
            else:
                _base_scan(c1, v1, fl, base2)
                m2 = 0
                for o42 in range(4):
                    var2 = _VAR_OF_O4[o42]
                    for cl2 in range(8):
                        ok2, nv2, cells2, lv2 = _leaf_linked(c1, v1, l1, base2, var2, cl2,
                                                             na, nb, w, fl, s2c, s2v, s2l,
                                                             mask, terms, maxpass, True)
                        if ok2 == 0:
                            continue
                        imm2 = int64(w[R_WVIR]) * nv2 + int64(w[R_WCELLS]) * cells2 + (int64(w[R_VBONUS]) if nv2 >= 2 else int64(0))
                        keys2[m2] = float64(imm2 + lv2)
                        imms2[m2] = imm2
                        for i in range(NCELL):
                            b2col[m2, i] = s2c[i]; b2vir[m2, i] = s2v[i]; b2lnk[m2, i] = s2l[i]
                        m2 += 1
                if m2 == 0:
                    val = imm1 + leaf1
                else:
                    _stable_desc(keys2, m2, order2)
                    kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
                    best2 = int64(0); have2 = False
                    for s2 in range(kk2):
                        k2 = order2[s2]
                        for i in range(NCELL):
                            e2c[i] = b2col[k2, i]; e2v[i] = b2vir[k2, i]; e2l[i] = b2lnk[k2, i]
                        if _virus_count(e2v) == 0:
                            v2 = imms2[k2] + int64(_WIN_SHIP)
                        else:
                            v2 = imms2[k2] + _expected_third_linked(e2c, e2v, e2l, w, fl,
                                                                    base3, terms, tc, tv, tl,
                                                                    mask, maxpass)
                        if not have2 or v2 > best2:
                            best2 = v2; have2 = True
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                val += w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
            if not have or val > best_val:
                best_val = val; best_act = var * 8 + cl; have = True
    return best_act


class LinkedD3Decider:
    """Depth-3 with link-carrying, body-gravity leaf resolution.  Needs the board's
    LINK plane, so `choose` reads `board.link` (the env always has it)."""

    def __init__(self, weights, flags, topk2=8, maxpass=1,
                 w_excav=_W_EXCAV_SHIP, w_hang=_W_HANG_SHIP):
        self.w = np.asarray(weights, dtype=np.float64)
        self.fl = np.asarray(flags, dtype=np.int32)
        self.topk2 = int(topk2)
        self.maxpass = int(maxpass)
        self.w_excav = int(w_excav)
        self.w_hang = int(w_hang)

    def choose(self, board, cur, nxt):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        a = _choose_d3_linked(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2,
                              self.w_excav, self.w_hang, self.w, self.fl, self.maxpass)
        return None if a < 0 else int(a)


def warmup_linked(topk2=8):
    bc = np.zeros(NCELL, dtype=np.int8); bv = np.zeros(NCELL, dtype=np.int8)
    bl = np.zeros(NCELL, dtype=np.int8)
    w = weights_rtl_r47(); fl = flags_r47()
    base = np.empty(NBASE, dtype=np.int64); terms = np.empty(NT, dtype=np.int64)
    tc = np.empty(NCELL, dtype=np.int8); tv = np.empty(NCELL, dtype=np.int8)
    tl = np.empty(NCELL, dtype=np.int8); mask = np.empty(NCELL, dtype=np.int8)
    _base_scan(bc, bv, fl, base)
    for mp in (1, 0):
        _expand_linked(bc, bv, bl, 2, 3, 1, 2, tc, tv, tl, mask, mp)
        _leaf_linked(bc, bv, bl, base, 2, 3, 1, 2, w, fl, tc, tv, tl, mask, terms, mp, True)
        _leaf_linked(bc, bv, bl, base, 2, 3, 1, 2, w, fl, tc, tv, tl, mask, terms, mp, False)
        _expected_third_linked(bc, bv, bl, w, fl, base, terms, tc, tv, tl, mask, mp)
        _choose_d3_linked(bc, bv, bl, 1, 2, 1, 2, topk2,
                          int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl, mp)
