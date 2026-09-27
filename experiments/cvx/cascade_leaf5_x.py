#!/usr/bin/env python3
"""STEER5 leaf-evaluator screen on the shipping couch brain (fw540 + reach_fw_tap mask, unified tap steering).

Three candidate LEAF term shapes, added to EVERY leaf value of the d3 chain search: clearing leaves
(`_leafv_ship` -> `_eval_rtl`), non-clearing leaves (the CMD-6/7 delta path `_combine_terms`), and the ply-3
fallback. With w5 == 0 the search is action-identical to the STEER4 baseline (selfcheck()).
  w5[0] BUR35  -W * sum over viruses v in cols 3..5 of #(NON-virus occupied cells above v in its column whose
               colour != v's colour)                              "spawn-column burial, colour-aware"
  w5[1] ACC35  +W * #(viruses in cols 3..5 that are ACCESSIBLE): every cell above v in its column is empty or v's
               colour, OR a side slot (r, c+-1) is empty, its column is empty above r, and it is supported
               ((r+1, c+-1) occupied or r = 15), so a straight drop lands beside v   "spawn-column accessibility"
  w5[2] RB35   -W * sum_{c in 3..5} c_bur(c), where c_bur is R_BURIED's own per-column count (colour-aware
               exemption + nearest-2 cap, the FL_* flags)         "R_BURIED rescaled only in cols 3-5"
The functions below are MECHANICAL COPIES (textual transform) of vendor/cascade_chain_x._leaf_chain /
_expected_third_chain and cascade_shape_x._choose_d3_chain_s_shape, with `_x5` added at the leaf values.
Extras are added after the base leaf's signed-16 wrap (in RTL they would sit inside the combine, before it).
"""
from __future__ import annotations
import numpy as np
from numba import njit, int8, int32, int64, float64
from fast_sim_x import ROWS, COLS, NCELL, _virus_count, _stable_desc, _resting
from fast_rtl_x import (R_WVIR, R_WCELLS, R_VBONUS, _WIN_SHIP, _VAR_OF_O4, _THIRD_X, _THIRD_Y,
                        _W_EXCAV_SHIP, _W_HANG_SHIP, NBASE, NT, T_NVIR, FL_COLOR_AWARE, FL_NEAREST2,
                        _leafv_ship, _base_scan, _delta_terms, _combine_terms, _any_clear_lines,
                        _g_excav_ship, _g_hang_ship)
from cascade_link_x import LINK_NONE, LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT, board_flat
from cascade_chain_x import _expand_chain, _imm_chain
from cascade_stranded_x import _g_stranded47
from cascade_shape_x import _shape_terms, ShapeReachDecider


@njit(cache=True, fastmath=False)
def _x5(col, vir, fl, w5):
    if w5[0] == 0 and w5[1] == 0 and w5[2] == 0:
        return int64(0)
    bur = 0; acc = 0; rb = 0
    color_aware = fl[FL_COLOR_AWARE]; nearest2 = fl[FL_NEAREST2]
    for c in range(3, 6):
        # R_BURIED's own column walk (for RB35)
        fillcnt = 0; curcol = 0; curlen = 0; vseen = 0
        for r in range(ROWS):
            idx = r * COLS + c
            cc = col[idx]
            if cc != 0:
                if vir[idx]:
                    same = (curcol == cc)
                    if (nearest2 == 0) or vseen < 2:
                        exempt = curlen if (color_aware and same) else 0
                        rb += fillcnt - exempt
                    vseen += 1
                    curcol = 0; curlen = 0
                    # BUR35 + ACC35 for this virus
                    nm = 0; clean = True
                    for q in range(r):
                        qc = col[q * COLS + c]
                        if qc != 0 and qc != cc:
                            clean = False
                            if not vir[q * COLS + c]:
                                nm += 1
                    bur += nm
                    ok = clean
                    if not ok:
                        for n in (c - 1, c + 1):
                            if n < 0 or n > 7:
                                continue
                            if col[r * COLS + n] != 0:
                                continue
                            open_above = True
                            for q in range(r):
                                if col[q * COLS + n] != 0:
                                    open_above = False
                                    break
                            if not open_above:
                                continue
                            if r == ROWS - 1 or col[(r + 1) * COLS + n] != 0:
                                ok = True
                                break
                    if ok:
                        acc += 1
                else:
                    if curcol == cc:
                        curlen += 1
                    else:
                        curcol = cc; curlen = 1
                fillcnt += 1
            else:
                curcol = 0; curlen = 0
    return int64(-w5[0] * bur + w5[1] * acc - w5[2] * rb)


@njit(cache=True, fastmath=False)
def _leaf_chain5(pcol, pvir, plnk, base, variant_, column, pa, pb, w, fl,
                 ccol, cvir, clnk, mask, terms, maxpass, want_board, w5):
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
        lv = _leafv_ship(ccol, cvir, w, fl)
        if _virus_count(cvir) != 0:
            lv += _x5(ccol, cvir, fl, w5)
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
        return (1, 0, 0, _combine_terms(terms, w) + _x5(ccol, cvir, fl, w5), 0)
    pcol[i0] = col0; pcol[i1] = col1
    if base[T_NVIR] == 0:
        pcol[i0] = sv0; pcol[i1] = sv1
        return (1, 0, 0, int64(_WIN_SHIP), 0)
    _delta_terms(pcol, pvir, base, r0, c0, r1, c1, fl, terms)
    val = _combine_terms(terms, w) + _x5(pcol, pvir, fl, w5)
    pcol[i0] = sv0; pcol[i1] = sv1
    return (1, 0, 0, val, 0)


@njit(cache=True, fastmath=False)
def _expected_third_chain5(b2c, b2v, b2l, w, fl, base3, terms, tc, tv, tl, mask,
                           maxpass, w_chain, w5):
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
                ok, nv, cells, lv, ch = _leaf_chain5(b2c, b2v, b2l, base3, var, cl, x, y,
                                                     w, fl, tc, tv, tl, mask, terms,
                                                     maxpass, False, w5)
                if ok == 0:
                    continue
                vv = _imm_chain(nv, cells, ch, w, w_chain) + lv
                if not have3 or vv > best3:
                    best3 = vv; have3 = True
        tot += best3 if have3 else (_leafv_ship(b2c, b2v, w, fl) + _x5(b2c, b2v, fl, w5))
    return tot // int64(4)


@njit(cache=True)
def _choose_d3_chain_s_leaf5(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang,
                             w, fl, maxpass, w_chain, ws, allowed, w_sv, r_hi, w_sp, hs, w5):
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
            if allowed[var * 8 + cl] == 0:
                continue
            ok, nv, cells, leaf1, ch1 = _leaf_chain5(pcol, pvir, plnk, base1, var, cl,
                                                    ca, cb, w, fl, c1, v1, l1, mask,
                                                    terms, maxpass, True, w5)
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
                        ok2, nv2, cells2, lv2, ch2 = _leaf_chain5(
                            c1, v1, l1, base2, var2, cl2, na, nb, w, fl,
                            s2c, s2v, s2l, mask, terms, maxpass, True, w5)
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
                            v2 = imms2[k2] + _expected_third_chain5(
                                e2c, e2v, e2l, w, fl, base3, terms, tc, tv, tl, mask,
                                maxpass, w_chain, w5)
                        if not have2 or v2 > best2:
                            best2 = v2; have2 = True
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                val += w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
            val -= ws * _g_stranded47(c1, v1)
            val += _shape_terms(pcol, var, cl, nv, cells, w_sv, r_hi, w_sp, hs)
            if not have or val > best_val:
                best_val = val; best_act = var * 8 + cl; have = True
    return best_act



class Leaf5ReachDecider(ShapeReachDecider):
    """STEER5: shipping baseline (reach_fw_tap mask, tap=2) + leaf term weights w5 = [BUR35, ACC35, RB35]."""

    def __init__(self, weights, flags, w5=(0, 0, 0), **kw):
        super().__init__(weights, flags, **kw)
        self.w5 = np.asarray(list(w5), dtype=np.int64)

    def choose(self, board, cur, nxt, k=0):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        a = _choose_d3_chain_s_leaf5(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2,
                                     self.w_excav, self.w_hang, self.w, self.fl, self.maxpass,
                                     self.w_chain, self.ws, self.mask(board, k),
                                     self.w_sv, self.r_hi, self.w_sp, self.hs, self.w5)
        return None if a < 0 else int(a)


def selfcheck(n_games=2, seed0=36734):
    """w5 == 0 == the STEER4 baseline decider on real boards."""
    import gate_b as G, bursty_model as BM, vs_race as V, fast_rtl_x as FX
    from drmario.faithful_game import Pill
    w, fl = FX.variant("winner")
    ref = ShapeReachDecider(w, fl, tap=2); d5 = Leaf5ReachDecider(w, fl, tap=2)
    m = BM.fit_struktured_20260804(); boards = []
    base = V._decider("fw540")
    def choose(env, col, vir, ctx):
        boards.append((env.board.clone(), env.pills_placed, Pill(int(env.cur.a), int(env.cur.b)), Pill(int(env.nxt.a), int(env.nxt.b))))
        return base(env, col, vir, ctx)
    for s in range(n_games):
        G.play(seed0 + 2 * s, None, m, choose=choose)
    same = sum(int(ref.choose(b, c, n, k) == d5.choose(b, c, n, k)) for b, k, c, n in boards)
    print(f"leaf5 selfcheck: {same}/{len(boards)} identical to the STEER4 baseline decider at w5 = 0")
    return same == len(boards)


if __name__ == "__main__":
    import sys
    sys.exit(0 if selfcheck() else 1)
