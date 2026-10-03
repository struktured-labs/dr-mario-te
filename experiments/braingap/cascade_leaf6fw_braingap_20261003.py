#!/usr/bin/env python3
"""SILICON-FAITHFUL SIM BRAIN candidate (2026-10-03 brain-gap lane): cascade_leaf6_x's dist_target60 search
(Leaf6Decider) with the shipped firmware's ROOT-SEARCH semantics switchable in numba:

  sw_veto  DRVETO (a+): -20000 (16-bit saturating) on a non-clearing, non-winning root that plugs (0,3)/(0,4) while the
           root has viruses (test_search_d3.veto_plug / veto_val)
  sw_hang  R4 hang credit (eh_hcredit): 40 + 20*gap per hovering half whose gap-drop lands on its colour, ONLY in a
           column holding a virus  (python bridge: flat 40 per hovering half, any column)
  sw_ehb1  the eh terms scan the firmware's SOFT b1 = root + straight-drop placement + targeted cap-1 clear (rows and
           columns of the two placed cells) + ONE compact gravity (test_resolve.py_gravity: every non-virus cell drops,
           links ignored)  (python: the link-aware fixpoint child c1)
  sw_ehnp  no eh add-on when the next pill has no legal placement (the firmware JMPs to o_cand)
  sw_wrap  signed-16 arithmetic where LeafEval / the 6502 do it (sco incl. HSV + DIST, K keys, V3, E, B2-L1, V1)
  sw_order roots evaluated in descending Pass-0 key K = imm1 + score1 (tie-break = first max), not enumeration order
All switches 0 == cascade_leaf6_x._choose_d3_chain_s_leaf6 exactly (selfcheck). The mirror_braingap_20261003 pure
python search (validated per root against py65 of the real image) is the reference for the switch semantics.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from numba import njit, int8, int32, int64, float64

HERE = os.path.dirname(os.path.abspath(__file__))
CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
os.environ.setdefault("NUMBA_CACHE_DIR", "/home/struktured/projects/dr-mario-h16-wt/tmp/braingap/nbcache")
sys.path.insert(0, CVX)
import import_pin  # noqa: E402
import_pin.pin()
from fast_sim_x import ROWS, COLS, NCELL, _virus_count, _stable_desc, _resting  # noqa: E402
from fast_rtl_x import (_WIN_SHIP, _VAR_OF_O4, _THIRD_X, _THIRD_Y, NBASE, NT, T_NVIR, _leafv_ship, _base_scan,  # noqa: E402
                        _delta_terms, _combine_terms, _any_clear_lines, _g_excav_ship, _g_hang_ship)
from cascade_link_x import LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT, board_flat  # noqa: E402
from cascade_chain_x import _expand_chain  # noqa: E402
from cascade_stranded_x import _g_stranded47  # noqa: E402
from cascade_leaf5b_x import _x5  # noqa: E402
from cascade_leaf6_x import _x6, Leaf6Decider  # noqa: E402

VETO_PENALTY = 20000


@njit(cache=True, fastmath=False)
def _w16(x):
    y = x & 0xFFFF
    if y >= 0x8000:
        y -= 0x10000
    return y


@njit(cache=True, fastmath=False)
def _imm_w(nv, cells, ch, w_chain, wrap):
    if wrap and ch > 15:
        ch = 15
    v = int64(180) * nv + int64(10) * cells
    if ch > 1:
        v += int64(w_chain) * int64(ch - 1)
    return v


@njit(cache=True, fastmath=False)
def _leaf_chain6w(pcol, pvir, plnk, base, variant_, column, pa, pb, w, fl,
                  ccol, cvir, clnk, mask, terms, maxpass, want_board, w5, w6, wrap):
    """cascade_leaf6_x._leaf_chain6 + `wrap`: the HSV/DIST extras ride INSIDE the signed-16 combine (LeafEval)."""
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
        lv = _leafv_ship(ccol, cvir, w, fl)
        if _virus_count(cvir) != 0:
            lv += _x5(ccol, cvir, fl, w5) + _x6(ccol, cvir, w6)
            if wrap:
                lv = _w16(lv)
        return (1, nv, cells, lv, ch)
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
        lv = _combine_terms(terms, w) + _x5(ccol, cvir, fl, w5) + _x6(ccol, cvir, w6)
        return (1, 0, 0, _w16(lv) if wrap else lv, 0)
    pcol[i0] = col0; pcol[i1] = col1
    if base[T_NVIR] == 0:
        pcol[i0] = sv0; pcol[i1] = sv1
        return (1, 0, 0, int64(_WIN_SHIP), 0)
    _delta_terms(pcol, pvir, base, r0, c0, r1, c1, fl, terms)
    lv = _combine_terms(terms, w) + _x5(pcol, pvir, fl, w5) + _x6(pcol, pvir, w6)
    pcol[i0] = sv0; pcol[i1] = sv1
    return (1, 0, 0, _w16(lv) if wrap else lv, 0)


@njit(cache=True, fastmath=False)
def _expected_third_w(b2c, b2v, b2l, w, fl, base3, terms, tc, tv, tl, mask, maxpass, w_chain, w5, w6, wrap):
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
                ok, nv, cells, lv, ch = _leaf_chain6w(b2c, b2v, b2l, base3, var, cl, x, y, w, fl, tc, tv, tl, mask,
                                                      terms, maxpass, False, w5, w6, wrap)
                if ok == 0:
                    continue
                vv = _imm_w(nv, cells, ch, w_chain, wrap) + lv
                if wrap:
                    vv = _w16(vv)
                if not have3 or vv > best3:
                    best3 = vv; have3 = True
        if have3:
            tot += best3
        else:
            lv = _leafv_ship(b2c, b2v, w, fl) + _x5(b2c, b2v, fl, w5) + _x6(b2c, b2v, w6)
            tot += _w16(lv) if wrap else lv
    if wrap:
        return tot >> int64(2)
    return tot // int64(4)


@njit(cache=True, fastmath=False)
def _soft_b1(pcol, pvir, variant_, column, pa, pb, bc, bv):
    """Firmware eh_terms b1: root + the straight-drop pill, targeted cap-1 clear, ONE compact gravity."""
    for i in range(NCELL):
        bc[i] = pcol[i]; bv[i] = pvir[i]
    ok, r0, c0, r1, c1 = _resting(pcol, variant_, column)
    if ok == 0:
        return 0
    if variant_ == 0 or variant_ == 2:
        col0 = pa; col1 = pb
    else:
        col0 = pb; col1 = pa
    bc[r0 * COLS + c0] = col0; bc[r1 * COLS + c1] = col1
    bv[r0 * COLS + c0] = 0; bv[r1 * COLS + c1] = 0
    mark = np.zeros(NCELL, dtype=np.int8)
    for k in range(4):
        if k == 0:
            start = r0 * COLS; step = 1; cnt = COLS
        elif k == 1:
            start = c0; step = COLS; cnt = ROWS
        elif k == 2:
            start = r1 * COLS; step = 1; cnt = COLS
        else:
            start = c1; step = COLS; cnt = ROWS
        run = 0; rstart = start; mcol = -1; o = start
        for _q in range(cnt):
            x = bc[o]
            if x == 0:
                if run >= 4:
                    for j in range(run):
                        mark[rstart + j * step] = 1
                run = 0; mcol = -1
            elif x != mcol:
                if run >= 4:
                    for j in range(run):
                        mark[rstart + j * step] = 1
                mcol = x; rstart = o; run = 1
            else:
                run += 1
            o += step
        if run >= 4:
            for j in range(run):
                mark[rstart + j * step] = 1
    anyc = 0
    for i in range(NCELL):
        if mark[i]:
            bc[i] = 0; bv[i] = 0; anyc = 1
    if anyc:
        for c in range(COLS):
            dest = ROWS - 1
            for rd in range(ROWS - 1, -1, -1):
                off = rd * COLS + c
                if bc[off] == 0:
                    continue
                if bv[off]:
                    dest = rd - 1
                else:
                    doff = dest * COLS + c
                    if doff != off:
                        bc[doff] = bc[off]; bv[doff] = 0; bc[off] = 0; bv[off] = 0
                    dest -= 1
    return 1


@njit(cache=True, fastmath=False)
def _hang_r4(col, vir):
    tot = int64(0)
    for idx in range(120):
        x = col[idx]
        if x == 0 or vir[idx] or col[idx + 8] != 0:
            continue
        y = idx + 16
        while y < NCELL and col[y] == 0:
            y += 8
        if y >= NCELL or col[y] != x:
            continue
        c = idx % COLS
        hv = False
        for q in range(c, NCELL, COLS):
            if vir[q]:
                hv = True; break
        if not hv:
            continue
        gap = ((y - idx) >> 3) - 1
        tot += 40 + 20 * gap
    return tot


@njit(cache=True, fastmath=False)
def _veto_plug(pcol, var, cl):
    if pcol[3] != 0 or pcol[4] != 0:
        return True
    if var < 2:                                   # horizontal
        if cl < 2 or cl > 4:
            return False
        if pcol[cl] != 0 or pcol[cl + 1] != 0:
            return False
        return pcol[8 + cl] != 0 or pcol[9 + cl] != 0
    if cl != 3 and cl != 4:
        return False
    return pcol[cl] != 0 or pcol[8 + cl] != 0 or pcol[16 + cl] != 0


@njit(cache=True)
def _choose_fw(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang, w, fl, maxpass, w_chain, ws, allowed,
               w5, w6, sw_veto, sw_hang, sw_ehb1, sw_ehnp, sw_wrap, sw_order, out_val):
    """Returns the best action (var*8+col) or -1; out_val[a] = root value (or -2**40 if not evaluated)."""
    c1s = np.empty((32, NCELL), dtype=int8); v1s = np.empty((32, NCELL), dtype=int8); l1s = np.empty((32, NCELL), dtype=int8)
    acts = np.empty(32, dtype=np.int64); nvs = np.empty(32, dtype=np.int64); cellss = np.empty(32, dtype=np.int64)
    leaf1s = np.empty(32, dtype=np.int64); ch1s = np.empty(32, dtype=np.int64)
    keys1 = np.empty(32, dtype=float64); order1 = np.empty(32, dtype=int32)
    b2col = np.empty((32, NCELL), dtype=int8); b2vir = np.empty((32, NCELL), dtype=int8)
    b2lnk = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64); imms2 = np.empty(32, dtype=int64); wins2 = np.empty(32, dtype=int64)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8); s2v = np.empty(NCELL, dtype=int8); s2l = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8); e2v = np.empty(NCELL, dtype=int8); e2l = np.empty(NCELL, dtype=int8)
    tc = np.empty(NCELL, dtype=int8); tv = np.empty(NCELL, dtype=int8); tl = np.empty(NCELL, dtype=int8)
    mask = np.empty(NCELL, dtype=int8)
    sbc = np.empty(NCELL, dtype=int8); sbv = np.empty(NCELL, dtype=int8)
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8); l1 = np.empty(NCELL, dtype=int8)
    base1 = np.empty(NBASE, dtype=int64); base2 = np.empty(NBASE, dtype=int64)
    base3 = np.empty(NBASE, dtype=int64); terms = np.empty(NT, dtype=int64)
    for a in range(32):
        out_val[a] = -(int64(1) << 40)
    _base_scan(pcol, pvir, fl, base1)
    virf = _virus_count(pvir) > 0
    n1 = 0
    for o4 in range(4):                                       # Pass 0 (enumeration order)
        var = _VAR_OF_O4[o4]
        for cl in range(8):
            if allowed[var * 8 + cl] == 0:
                continue
            ok, nv, cells, leaf1, ch1 = _leaf_chain6w(pcol, pvir, plnk, base1, var, cl, ca, cb, w, fl, c1, v1, l1,
                                                     mask, terms, maxpass, True, w5, w6, sw_wrap)
            if ok == 0:
                continue
            for i in range(NCELL):
                c1s[n1, i] = c1[i]; v1s[n1, i] = v1[i]; l1s[n1, i] = l1[i]
            acts[n1] = var * 8 + cl; nvs[n1] = nv; cellss[n1] = cells; leaf1s[n1] = leaf1; ch1s[n1] = ch1
            k1 = _imm_w(nv, cells, ch1, w_chain, sw_wrap) + leaf1
            keys1[n1] = float64(_w16(k1) if sw_wrap else k1)
            n1 += 1
    if n1 == 0:
        return -1
    if sw_order:
        _stable_desc(keys1, n1, order1)
    else:
        for j in range(n1):
            order1[j] = j
    best_val = int64(0); best_act = -1; have = False
    for jj in range(n1):
        j = order1[jj]
        a = acts[j]; var = a // 8; cl = a % 8
        for i in range(NCELL):
            c1[i] = c1s[j, i]; v1[i] = v1s[j, i]; l1[i] = l1s[j, i]
        nv = nvs[j]; cells = cellss[j]; leaf1 = leaf1s[j]; ch1 = ch1s[j]
        imm1 = _imm_w(nv, cells, ch1, w_chain, sw_wrap)
        win1 = _virus_count(v1) == 0
        veto = sw_veto != 0 and (not win1) and cells == 0 and virf and _veto_plug(pcol, var, cl)
        if win1:
            val = imm1 + int64(_WIN_SHIP)
            if sw_wrap:
                val = _w16(val)
        else:
            # eh terms
            if sw_ehb1:
                _soft_b1(pcol, pvir, var, cl, ca, cb, sbc, sbv)
                ex = _g_excav_ship(sbc, sbv)
                hg = _hang_r4(sbc, sbv) if sw_hang else int64(w_hang) * _g_hang_ship(sbc, sbv)
            else:
                ex = _g_excav_ship(c1, v1)
                hg = _hang_r4(c1, v1) if sw_hang else int64(w_hang) * _g_hang_ship(c1, v1)
            eh = int64(w_excav) * ex + hg
            _base_scan(c1, v1, fl, base2)
            m2 = 0
            for o42 in range(4):
                var2 = _VAR_OF_O4[o42]
                for cl2 in range(8):
                    ok2, nv2, cells2, lv2, ch2 = _leaf_chain6w(c1, v1, l1, base2, var2, cl2, na, nb, w, fl,
                                                               s2c, s2v, s2l, mask, terms, maxpass, True, w5, w6,
                                                               sw_wrap)
                    if ok2 == 0:
                        continue
                    imm2 = _imm_w(nv2, cells2, ch2, w_chain, sw_wrap)
                    k2 = imm2 + lv2
                    keys2[m2] = float64(_w16(k2) if sw_wrap else k2)
                    imms2[m2] = imm2
                    for i in range(NCELL):
                        b2col[m2, i] = s2c[i]; b2vir[m2, i] = s2v[i]; b2lnk[m2, i] = s2l[i]
                    m2 += 1
            if m2 == 0:
                val = imm1 + leaf1
                if sw_wrap:
                    val = _w16(val)
                if sw_ehnp == 0:
                    val += eh
            else:
                _stable_desc(keys2, m2, order2)
                kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
                best2 = int64(0); have2 = False
                for s2 in range(kk2):
                    k2i = order2[s2]
                    for i in range(NCELL):
                        e2c[i] = b2col[k2i, i]; e2v[i] = b2vir[k2i, i]; e2l[i] = b2lnk[k2i, i]
                    if _virus_count(e2v) == 0:
                        v2 = imms2[k2i] + int64(_WIN_SHIP)
                    else:
                        v2 = imms2[k2i] + _expected_third_w(e2c, e2v, e2l, w, fl, base3, terms, tc, tv, tl, mask,
                                                            maxpass, w_chain, w5, w6, sw_wrap)
                    if sw_wrap:
                        v2 = _w16(v2)
                    if not have2 or v2 > best2:
                        best2 = v2; have2 = True
                if sw_wrap:
                    val = _w16(imm1 + leaf1 + (_w16(best2 - leaf1) >> int64(1)) + eh)
                else:
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1)) + eh
        val -= int64(ws) * _g_stranded47(c1, v1)
        if sw_wrap:
            val = _w16(val)
        if veto:
            t = val - VETO_PENALTY
            val = t if t >= -32768 else int64(-32767)
        out_val[a] = val
        if not have or val > best_val:
            best_val = val; best_act = a; have = True
    return best_act


class Leaf6FwDecider(Leaf6Decider):
    """Leaf6Decider (dist_target60 on ANTIBODY) with the firmware root-search switches (see module doc).
    sw = dict(veto, hang, ehb1, ehnp, wrap, order); all 0 == Leaf6Decider."""

    def __init__(self, weights, flags, sw=None, mask_fn=None, **kw):
        super().__init__(weights, flags, **kw)
        s = dict(veto=1, hang=1, ehb1=1, ehnp=1, wrap=1, order=1)
        if sw:
            s.update(sw)
        self.sw = s
        self.mask_fn = mask_fn
        self.vals = np.empty(32, dtype=np.int64)

    def choose(self, board, cur, nxt, k=0):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        allowed = self.mask(board, k) if self.mask_fn is None else self.mask_fn(board, k)
        w6 = self.w6_for(col, vir, cur, allowed, k)
        s = self.sw
        a = _choose_fw(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2, self.w_excav, self.w_hang, self.w,
                       self.fl, self.maxpass, self.w_chain, self.ws, allowed, self.w5, w6, int(s["veto"]),
                       int(s["hang"]), int(s["ehb1"]), int(s["ehnp"]), int(s["wrap"]), int(s["order"]), self.vals)
        return None if a < 0 else int(a)
