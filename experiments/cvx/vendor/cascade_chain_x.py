#!/usr/bin/env python3
"""CHAIN-REWARD knob on link-faithful fixpoint physics — the cascade lever nobody has
ever actually pulled.

WHY IT DOESN'T EXIST YET.  The immediate-reward terms are w_vir (180/virus), w_cells
(10/cell) and vbonus (flat, on nv>=2 VIRUSES, and 0.0 in the shipped `winner` arm).  None
of them can see chain DEPTH.  selfplay-opt's sweep of R_CROSS and R_VBONUS therefore
tested SIMULTANEITY levers, while ~90% of ROM-rule attacks are cascade-formed (measured
independently on both rigs).  So the cascade lever is untested, not refuted.

THE KNOB.  `w_chain` adds `w_chain * (chain - 1)` to a placement's immediate reward, where
`chain` is the number of clear rounds the leaf's fixpoint resolve actually performed.  It
is a separate SCALAR ARGUMENT, deliberately NOT a new slot in the weight vector: that
keeps `fast_rtl_x`'s layout, every other lane's weight dict, and the bit-exactness gate
completely untouched.  w_chain=0 must reproduce `cascade_link_x` exactly (asserted in
cascade_chain_selfcheck).

WHAT THIS IS FOR, AND THE PRIOR AGAINST IT.  My INTEND-vs-REALIZE instrument shows the
search declines chains DELIBERATELY once it can see them accurately (intends 4.62% under
correct physics vs 5.78% at cap-1, phantom=0 by construction).  A chain reward pushes
against an informed preference.  And the fixpoint arm it sits on already measures -18% on
the ROM attack rate.  So the honest expectation is that this knob either fails to move
intent, or moves it and costs board quality.  It is worth measuring on the CHEAP intent
instrument before anyone spends h2h matches — which is exactly what selfplay-opt proposed.

Scale reference for the sweep: one extra chain step clears ~5 cells ~= 50 imm; one virus
= 180.  So {0, 60, 180, 360, 720} spans "less than a virus" to "several viruses".
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
import cascade_link_x as L
from cascade_link_x import (
    LINK_NONE, LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT,
    _resolve_linked, _link_gravity, _apply_clear_linked, _find_clears_mask,
)


@njit(cache=True, fastmath=False)
def _expand_chain(pcol, pvir, plnk, variant_, column, pa, pb,
                  ccol, cvir, clnk, mask, maxpass):
    """`cascade_link_x._expand_linked` but also returning the CHAIN DEPTH, which the
    original computes and throws away."""
    ok, r0, c0, r1, c1 = _resting(pcol, variant_, column)
    if ok == 0:
        return (0, 0, 0, 0)
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
    if variant_ < 2:
        clnk[i0] = LINK_RIGHT; clnk[i1] = LINK_LEFT
    else:
        clnk[i0] = LINK_DOWN; clnk[i1] = LINK_UP
    cells, nv, ch = _resolve_linked(ccol, cvir, clnk, mask, maxpass)
    return (1, nv, cells, ch)


@njit(cache=True, fastmath=False)
def _leaf_chain(pcol, pvir, plnk, base, variant_, column, pa, pb, w, fl,
                ccol, cvir, clnk, mask, terms, maxpass, want_board):
    """Leaf value + child board + CHAIN DEPTH.  Non-clearing leaves have chain 0 and take
    the untouched delta path, exactly as in cascade_link_x."""
    ok, r0, c0, r1, c1 = _resting(pcol, variant_, column)
    if ok == 0:
        return (0, 0, 0, int64(0), 0)
    if variant_ == 0 or variant_ == 2:
        col0 = pa; col1 = pb
    else:
        col0 = pb; col1 = pa
    i0 = r0 * COLS + c0
    i1 = r1 * COLS + c1
    sv0 = pcol[i0]; sv1 = pcol[i1]
    pcol[i0] = col0; pcol[i1] = col1
    clearing = _any_clear_lines(pcol, r0, c0, r1, c1)
    pcol[i0] = sv0; pcol[i1] = sv1
    if clearing:
        _o, nv, cells, ch = _expand_chain(pcol, pvir, plnk, variant_, column, pa, pb,
                                          ccol, cvir, clnk, mask, maxpass)
        return (1, nv, cells, _leafv_ship(ccol, cvir, w, fl), ch)
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
            return (1, 0, 0, int64(_WIN_SHIP), 0)
        _delta_terms(ccol, cvir, base, r0, c0, r1, c1, fl, terms)
        return (1, 0, 0, _combine_terms(terms, w), 0)
    pcol[i0] = col0; pcol[i1] = col1
    if base[T_NVIR] == 0:
        pcol[i0] = sv0; pcol[i1] = sv1
        return (1, 0, 0, int64(_WIN_SHIP), 0)
    _delta_terms(pcol, pvir, base, r0, c0, r1, c1, fl, terms)
    val = _combine_terms(terms, w)
    pcol[i0] = sv0; pcol[i1] = sv1
    return (1, 0, 0, val, 0)


@njit(cache=True, fastmath=False)
def _imm_chain(nv, cells, ch, w, w_chain):
    """Immediate reward with the chain bonus.  chain<=1 contributes nothing, so w_chain
    rewards only ACTUAL cascades, never a plain clear."""
    v = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells
    if nv >= 2:
        v += int64(w[R_VBONUS])
    if ch > 1:
        v += int64(w_chain) * int64(ch - 1)
    return v


@njit(cache=True, fastmath=False)
def _expected_third_chain(b2c, b2v, b2l, w, fl, base3, terms, tc, tv, tl, mask,
                          maxpass, w_chain):
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
                ok, nv, cells, lv, ch = _leaf_chain(b2c, b2v, b2l, base3, var, cl, x, y,
                                                    w, fl, tc, tv, tl, mask, terms,
                                                    maxpass, False)
                if ok == 0:
                    continue
                vv = _imm_chain(nv, cells, ch, w, w_chain) + lv
                if not have3 or vv > best3:
                    best3 = vv; have3 = True
        tot += best3 if have3 else _leafv_ship(b2c, b2v, w, fl)
    return tot // int64(4)


@njit(int64(int8[:], int8[:], int8[:], int64, int64, int64, int64, int64, int64, int64,
            float64[:], int32[:], int64, int64), cache=True, fastmath=False)
def _choose_d3_chain(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang,
                     w, fl, maxpass, w_chain):
    """`cascade_link_x._choose_d3_linked` with the chain bonus folded into every imm.
    At w_chain=0 this must return the identical action."""
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
            ok, nv, cells, leaf1, ch1 = _leaf_chain(pcol, pvir, plnk, base1, var, cl,
                                                    ca, cb, w, fl, c1, v1, l1, mask,
                                                    terms, maxpass, True)
            if ok == 0:
                continue
            imm1 = _imm_chain(nv, cells, ch1, w, w_chain)
            if _virus_count(v1) == 0:
                val = imm1 + int64(_WIN_SHIP)
            else:
                _base_scan(c1, v1, fl, base2)
                m2 = 0
                for o42 in range(4):
                    var2 = _VAR_OF_O4[o42]
                    for cl2 in range(8):
                        ok2, nv2, cells2, lv2, ch2 = _leaf_chain(
                            c1, v1, l1, base2, var2, cl2, na, nb, w, fl,
                            s2c, s2v, s2l, mask, terms, maxpass, True)
                        if ok2 == 0:
                            continue
                        imm2 = _imm_chain(nv2, cells2, ch2, w, w_chain)
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
                            v2 = imms2[k2] + _expected_third_chain(
                                e2c, e2v, e2l, w, fl, base3, terms, tc, tv, tl, mask,
                                maxpass, w_chain)
                        if not have2 or v2 > best2:
                            best2 = v2; have2 = True
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                val += w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
            if not have or val > best_val:
                best_val = val; best_act = var * 8 + cl; have = True
    return best_act


class ChainRewardD3Decider:
    """Link-faithful fixpoint depth-3 with an explicit chain-depth reward.
    w_chain=0 reproduces cascade_link_x.LinkedD3Decider exactly."""

    def __init__(self, weights, flags, topk2=8, maxpass=0, w_chain=0,
                 w_excav=_W_EXCAV_SHIP, w_hang=_W_HANG_SHIP):
        self.w = np.asarray(weights, dtype=np.float64)
        self.fl = np.asarray(flags, dtype=np.int32)
        self.topk2 = int(topk2)
        self.maxpass = int(maxpass)
        self.w_chain = int(w_chain)
        self.w_excav = int(w_excav)
        self.w_hang = int(w_hang)

    def choose(self, board, cur, nxt):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        a = _choose_d3_chain(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2,
                             self.w_excav, self.w_hang, self.w, self.fl,
                             self.maxpass, self.w_chain)
        return None if a < 0 else int(a)


def warmup_chain(topk2=8):
    bc = np.zeros(NCELL, dtype=np.int8); bv = np.zeros(NCELL, dtype=np.int8)
    bl = np.zeros(NCELL, dtype=np.int8)
    w = weights_rtl_r47(); fl = flags_r47()
    base = np.empty(NBASE, dtype=np.int64); terms = np.empty(NT, dtype=np.int64)
    tc = np.empty(NCELL, dtype=np.int8); tv = np.empty(NCELL, dtype=np.int8)
    tl = np.empty(NCELL, dtype=np.int8); mask = np.empty(NCELL, dtype=np.int8)
    _base_scan(bc, bv, fl, base)
    for wc in (0, 180):
        _expand_chain(bc, bv, bl, 2, 3, 1, 2, tc, tv, tl, mask, 0)
        _leaf_chain(bc, bv, bl, base, 2, 3, 1, 2, w, fl, tc, tv, tl, mask, terms, 0, True)
        _leaf_chain(bc, bv, bl, base, 2, 3, 1, 2, w, fl, tc, tv, tl, mask, terms, 0, False)
        _expected_third_chain(bc, bv, bl, w, fl, base, terms, tc, tv, tl, mask, 0, wc)
        _choose_d3_chain(bc, bv, bl, 1, 2, 1, 2, topk2,
                         int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl, 0, wc)
