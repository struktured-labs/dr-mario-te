#!/usr/bin/env python3
"""STEER9 (2026-10-04): "DON'T SEAL A LIVE COLUMN" rules on the SILICON-FAITHFUL brain (braingap Leaf6FwDecider).

Couch forensics 10/04 (couch_forensics/RESULT_FAIR_20261004.md, stall_fair_20261004.py): three couch stalls share one
cause -- viruses became unreachable as a line, and the brain has no term that values keeping access to a virus open.

ROUTE PREDICATE (one kernel, many call sites): a virus v is LIVE iff cascade_leaf6_x._vdist(kdig = 0, cap = 99) < 99,
i.e. at least one 4-window through v (horizontal or vertical) is completable by STRAIGHT DROPS without first clearing
any other cell: every other window cell is v's colour, or empty AND fillable from above (no overhang / cavity; for a
vertical window, nothing empty below v). Otherwise v is SEALED. (_vdist's own feasible costs are <= 3 * 16 = 48 < 99,
so `< 99` is exactly "a feasible route exists".)

ROOT-SIDE rules (firmware-implementable; evaluated per allowed root on the firmware's own SOFT b1 = root + straight-drop
pill + targeted cap-1 clear + one compact gravity, the board the 6502 already builds for the eh terms):
  kind 0  SEALV   n_new(a) = viruses LIVE on the root board and SEALED on b1(a) (a cleared virus is not counted)
  kind 1  SEALC   n_new(a) = virus COLUMNS whose TOP virus is LIVE on the root board and whose top virus on b1(a) is
                  SEALED (column-level access; the top virus may change if the root clears it)
  mode 0  PENALTY pen(a) = P * n_new(a), subtracted from the root value (16-bit saturating, as DRVETO)
  mode 1  VETO    pen(a) = P iff n_new(a) > 0 AND some allowed legal root has n_new == 0; else 0. With P = 20000 this
                  is DRVETO-strength: refuse a sealing root whenever an alternative keeps every live virus live.
                  Failure mode = status quo (every root seals -> no penalty).
LEAF rule (expensive in RTL; the mechanism comparison, not a ship candidate):
  wleaf   -wleaf * (number of SEALED viruses) at every leaf value of the d3 chain search (ply 1, 2, 3), all virus
          counts. Implemented as a mechanical copy of the braingap leaf/third/choose kernels with one extra term.

`_choose_fw_seal` is a MECHANICAL COPY of braingap `_choose_fw` with (1) the per-root `pen` applied after DRVETO and
(2) the no-penalty argmax tracked beside it (act0 = what the unmodified brain picks on the same board, used for the
activity counters: fired / changed). pen == 0 and wleaf == 0 is action- and value-identical to `_choose_fw`
(selfcheck below).
"""
from __future__ import annotations

import os
import sys

import numpy as np
from numba import njit, int8, int32, int64, float64

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "braingap"))
import import_pin  # noqa: E402
import_pin.pin()
from fast_sim_x import ROWS, COLS, NCELL, _virus_count, _stable_desc, _resting  # noqa: E402
from fast_rtl_x import (_WIN_SHIP, _VAR_OF_O4, _THIRD_X, _THIRD_Y, NBASE, NT, T_NVIR, _leafv_ship, _base_scan,  # noqa: E402
                        _delta_terms, _combine_terms, _any_clear_lines, _g_excav_ship, _g_hang_ship)
from cascade_link_x import LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT, board_flat  # noqa: E402
from cascade_chain_x import _expand_chain  # noqa: E402
from cascade_stranded_x import _g_stranded47  # noqa: E402
from cascade_leaf5b_x import _x5  # noqa: E402
from cascade_leaf6_x import _x6, _vdist  # noqa: E402
import cascade_leaf6fw_braingap_20261003 as FW  # noqa: E402
from cascade_leaf6fw_braingap_20261003 import (_w16, _imm_w, _soft_b1, _hang_r4, _veto_plug,  # noqa: E402
                                               VETO_PENALTY, Leaf6FwDecider)

RCAP = 99


# ------------------------------------------------------------------------------------------- route predicate
@njit(cache=True, fastmath=False)
def _tops(col, top):
    for c in range(COLS):
        t = ROWS
        for r in range(ROWS):
            if col[r * COLS + c] != 0:
                t = r; break
        top[c] = t


@njit(cache=True, fastmath=False)
def _routes(col, vir, out):
    """out[idx] = 1 LIVE virus, 0 SEALED virus, -1 not a virus."""
    top = np.empty(COLS, dtype=np.int64)
    _tops(col, top)
    for idx in range(NCELL):
        if vir[idx] != 0:
            out[idx] = 1 if _vdist(col, vir, top, idx // COLS, idx % COLS, RCAP, 0) < RCAP else 0
        else:
            out[idx] = -1


@njit(cache=True, fastmath=False)
def _n_sealed(col, vir):
    top = np.empty(COLS, dtype=np.int64)
    _tops(col, top)
    n = 0
    for idx in range(NCELL):
        if vir[idx] != 0 and _vdist(col, vir, top, idx // COLS, idx % COLS, RCAP, 0) >= RCAP:
            n += 1
    return n


@njit(cache=True, fastmath=False)
def _top_virus_row(vir, c):
    for r in range(ROWS):
        if vir[r * COLS + c] != 0:
            return r
    return -1


@njit(cache=True, fastmath=False)
def _n_new(pcol, pvir, r0, bc, bv, r1, kind):
    _routes(bc, bv, r1)
    n = 0
    if kind == 0:
        for idx in range(NCELL):
            if r0[idx] == 1 and r1[idx] == 0:
                n += 1
    else:
        for c in range(COLS):
            t0 = _top_virus_row(pvir, c)
            t1 = _top_virus_row(bv, c)
            if t0 < 0 or t1 < 0:
                continue
            if r0[t0 * COLS + c] == 1 and r1[t1 * COLS + c] == 0:
                n += 1
    return n


@njit(cache=True, fastmath=False)
def _seal_pen(pcol, pvir, ca, cb, allowed, kind, mode, P, pen, nnew):
    """Per allowed legal root a: nnew[a] (newly sealed, see module doc; -1 = not evaluated) and pen[a]."""
    r0 = np.empty(NCELL, dtype=np.int64); r1 = np.empty(NCELL, dtype=np.int64)
    sbc = np.empty(NCELL, dtype=int8); sbv = np.empty(NCELL, dtype=int8)
    _routes(pcol, pvir, r0)
    anyzero = False
    for a in range(32):
        pen[a] = 0; nnew[a] = -1
        if allowed[a] == 0:
            continue
        if _soft_b1(pcol, pvir, a // 8, a % 8, ca, cb, sbc, sbv) == 0:
            continue
        n = _n_new(pcol, pvir, r0, sbc, sbv, r1, kind)
        nnew[a] = n
        if n == 0:
            anyzero = True
    for a in range(32):
        if nnew[a] > 0:
            if mode == 0:
                pen[a] = int64(P) * nnew[a]
            elif anyzero:
                pen[a] = int64(P)


# ------------------------------------------------------------------- leaf kernels (copies + the wleaf term)
@njit(cache=True, fastmath=False)
def _leaf_chain6s(pcol, pvir, plnk, base, variant_, column, pa, pb, w, fl,
                  ccol, cvir, clnk, mask, terms, maxpass, want_board, w5, w6, wrap, wleaf):
    """braingap _leaf_chain6w + `- wleaf * sealed(leaf board)` beside _x5/_x6 (wleaf == 0: identical)."""
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
            if wleaf != 0:
                lv -= int64(wleaf) * _n_sealed(ccol, cvir)
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
        if wleaf != 0:
            lv -= int64(wleaf) * _n_sealed(ccol, cvir)
        return (1, 0, 0, _w16(lv) if wrap else lv, 0)
    pcol[i0] = col0; pcol[i1] = col1
    if base[T_NVIR] == 0:
        pcol[i0] = sv0; pcol[i1] = sv1
        return (1, 0, 0, int64(_WIN_SHIP), 0)
    _delta_terms(pcol, pvir, base, r0, c0, r1, c1, fl, terms)
    lv = _combine_terms(terms, w) + _x5(pcol, pvir, fl, w5) + _x6(pcol, pvir, w6)
    if wleaf != 0:
        lv -= int64(wleaf) * _n_sealed(pcol, pvir)
    pcol[i0] = sv0; pcol[i1] = sv1
    return (1, 0, 0, _w16(lv) if wrap else lv, 0)


@njit(cache=True, fastmath=False)
def _expected_third_s(b2c, b2v, b2l, w, fl, base3, terms, tc, tv, tl, mask, maxpass, w_chain, w5, w6, wrap, wleaf):
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
                ok, nv, cells, lv, ch = _leaf_chain6s(b2c, b2v, b2l, base3, var, cl, x, y, w, fl, tc, tv, tl, mask,
                                                      terms, maxpass, False, w5, w6, wrap, wleaf)
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
            if wleaf != 0:
                lv -= int64(wleaf) * _n_sealed(b2c, b2v)
            tot += _w16(lv) if wrap else lv
    if wrap:
        return tot >> int64(2)
    return tot // int64(4)


@njit(cache=True)
def _choose_fw_seal(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang, w, fl, maxpass, w_chain, ws, allowed,
                    w5, w6, sw_veto, sw_hang, sw_ehb1, sw_ehnp, sw_wrap, sw_order, out_val, pen, wleaf, out_act0):
    """MECHANICAL COPY of braingap _choose_fw + pen[a] (after DRVETO, same saturation) + the leaf term wleaf.
    out_act0[0] = the argmax WITHOUT pen (same evaluation order / tie-break), for the activity counters."""
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
    out_act0[0] = -1
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
            ok, nv, cells, leaf1, ch1 = _leaf_chain6s(pcol, pvir, plnk, base1, var, cl, ca, cb, w, fl, c1, v1, l1,
                                                      mask, terms, maxpass, True, w5, w6, sw_wrap, wleaf)
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
    best_val0 = int64(0); best_act0 = -1; have0 = False
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
                    ok2, nv2, cells2, lv2, ch2 = _leaf_chain6s(c1, v1, l1, base2, var2, cl2, na, nb, w, fl,
                                                               s2c, s2v, s2l, mask, terms, maxpass, True, w5, w6,
                                                               sw_wrap, wleaf)
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
                        v2 = imms2[k2i] + _expected_third_s(e2c, e2v, e2l, w, fl, base3, terms, tc, tv, tl, mask,
                                                            maxpass, w_chain, w5, w6, sw_wrap, wleaf)
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
        val0 = val
        if pen[a] != 0:                                       # STEER9 root-side seal penalty (DRVETO saturation)
            t = val - pen[a]
            if sw_wrap:
                val = t if t >= -32768 else int64(-32767)
            else:
                val = t
        out_val[a] = val
        if not have or val > best_val:
            best_val = val; best_act = a; have = True
        if not have0 or val0 > best_val0:
            best_val0 = val0; best_act0 = a; have0 = True
    out_act0[0] = best_act0
    return best_act


class SealFwDecider(Leaf6FwDecider):
    """Leaf6FwDecider + a STEER9 seal rule. seal = dict(kind=0|1, mode=0|1, P=int, wleaf=int).
    Activity counters (rule 26): dec (decisions), fired (some allowed root carried pen > 0), changed (the chosen root
    differs from the no-penalty argmax on the same board = what the unmodified brain picks), plus leaf_active."""

    def __init__(self, weights, flags, seal=None, **kw):
        super().__init__(weights, flags, **kw)
        s = dict(kind=0, mode=0, P=0, wleaf=0)
        if seal:
            s.update(seal)
        self.seal = s
        self.pen = np.zeros(32, dtype=np.int64)
        self.nnew = np.full(32, -1, dtype=np.int64)
        self.act0 = np.full(1, -1, dtype=np.int64)
        self.stats = dict(dec=0, fired=0, changed=0)

    def choose(self, board, cur, nxt, k=0):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        allowed = self.mask(board, k) if self.mask_fn is None else self.mask_fn(board, k)
        w6 = self.w6_for(col, vir, cur, allowed, k)
        s = self.sw; q = self.seal
        if q["P"] != 0:
            _seal_pen(col, vir, cur.a, cur.b, allowed, int(q["kind"]), int(q["mode"]), int(q["P"]), self.pen, self.nnew)
        else:
            self.pen[:] = 0; self.nnew[:] = -1
        a = _choose_fw_seal(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2, self.w_excav, self.w_hang, self.w,
                            self.fl, self.maxpass, self.w_chain, self.ws, allowed, self.w5, w6, int(s["veto"]),
                            int(s["hang"]), int(s["ehb1"]), int(s["ehnp"]), int(s["wrap"]), int(s["order"]), self.vals,
                            self.pen, int(q["wleaf"]), self.act0)
        self.stats["dec"] += 1
        self.stats["fired"] += int(bool((self.pen > 0).any()))
        self.stats["changed"] += int(a >= 0 and int(self.act0[0]) != a)
        return None if a < 0 else int(a)


def selfcheck(boards, w, fl, kw):
    """pen == 0, wleaf == 0: action AND every root value identical to braingap Leaf6FwDecider (all switches on)."""
    ref = Leaf6FwDecider(w, fl, sw=None, **kw)
    me = SealFwDecider(w, fl, sw=None, seal=dict(P=0, wleaf=0), **kw)
    same_a = same_v = 0
    for b, k, c, n in boards:
        a0 = ref.choose(b, c, n, k); v0 = ref.vals.copy()
        a1 = me.choose(b, c, n, k); v1 = me.vals.copy()
        same_a += int(a0 == a1); same_v += int(np.array_equal(v0, v1))
        assert me.act0[0] == (-1 if a1 is None else a1)
    return same_a, same_v, len(boards)
