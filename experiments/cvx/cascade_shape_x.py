#!/usr/bin/env python3
"""STEER4 board-shape root terms on the shipping couch brain (fw540 + reach_fw_tap mask).
`_choose_d3_chain_s_shape` = a MECHANICAL COPY of cascade_reach_x._choose_d3_chain_s_masked (textual transform)
plus ONE added root line: `val += _shape_terms(...)`. With w_sv = w_sp = 0 it is action-identical to the masked
decider (selfcheck()).

Both terms are FIRMWARE-REALISABLE PROXIES. The copro firmware cannot read the resolved child board (the engine
exposes only result registers: RVV viruses cleared, RVC cells cleared, ...), but it holds the parent board (LIVE)
and the candidate (o4, col):
  (1) spawn-column virus priority: val += w_sv * nv   iff the placement's span meets cols 3..5 AND its upper cell
      lands at row <= r_hi (parent column tops).  nv = viruses cleared by the placement (= LEV_RVV).
  (2) spawn-lane height, ungated: val -= w_sp * max(0, spawn_h(parent + placed) - hs)   iff cells == 0 (= LEV_RVC
      == 0: nothing cleared, so the child IS parent + placed, the DRVETO argument); otherwise 0.
"""
from __future__ import annotations
import numpy as np
from numba import njit, int8, int32, int64, float64
from cascade_stranded_x import *                     # noqa
from cascade_stranded_x import _g_stranded47, StrandedChainD3Decider
from cascade_chain_x import (_leaf_chain, _imm_chain, _base_scan, _expected_third_chain, NBASE, NT)
from fast_sim_x import NCELL, _virus_count, _stable_desc
from fast_rtl_x import _VAR_OF_O4, _WIN_SHIP, _g_excav_ship, _g_hang_ship, _W_EXCAV_SHIP, _W_HANG_SHIP
from cascade_link_x import board_flat
import steer_model as SM


@njit(cache=True)
def _top(pcol, c):
    for r in range(16):
        if pcol[r * 8 + c] != 0:
            return r
    return 16


@njit(cache=True)
def _shape_terms(pcol, var, cl, nv, cells, w_sv, r_hi, w_sp, hs):
    if w_sv == 0 and w_sp == 0:
        return int64(0)
    vert = var >= 2
    if vert:
        bot = _top(pcol, cl) - 1
        up = bot - 1
        lo = cl; hi = cl
    else:
        bot = min(_top(pcol, cl), _top(pcol, cl + 1)) - 1
        up = bot
        lo = cl; hi = cl + 1
    out = int64(0)
    if w_sv != 0 and nv > 0 and hi >= 3 and lo <= 5 and up <= r_hi:
        out += int64(w_sv) * int64(nv)
    if w_sp != 0 and cells == 0:
        h = 0
        for c in (3, 4):
            t = _top(pcol, c)
            if lo <= c <= hi:
                if up < t:
                    t = up
            if 16 - t > h:
                h = 16 - t
        if h > hs:
            out -= int64(w_sp) * int64(h - hs)
    return out


@njit(cache=True)
def _choose_d3_chain_s_shape(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang,
                             w, fl, maxpass, w_chain, ws, allowed, w_sv, r_hi, w_sp, hs):
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
            val -= ws * _g_stranded47(c1, v1)
            val += _shape_terms(pcol, var, cl, nv, cells, w_sv, r_hi, w_sp, hs)
            if not have or val > best_val:
                best_val = val; best_act = var * 8 + cl; have = True
    return best_act



class ShapeReachDecider(StrandedChainD3Decider):
    """fw540 + reach_fw_tap mask (tap=P, rot_margin) + firmware-proxy shape terms."""

    def __init__(self, weights, flags, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, rot_margin=0,
                 w_sv=0, r_hi=9, w_sp=0, hs=10):
        super().__init__(weights, flags, topk2=topk2, maxpass=maxpass, w_chain=w_chain, ws=ws)
        self.tap, self.rot_margin = tap, rot_margin
        self.w_sv, self.r_hi, self.w_sp, self.hs = int(w_sv), int(r_hi), int(w_sp), int(hs)

    def mask(self, board, k):
        import reach_fw_tap as RT
        return np.asarray(RT.reach_mask_fw(board.color.tolist(), SM.table_threshold(k), tap=self.tap,
                                           rot_margin=self.rot_margin), dtype=np.int8)

    def choose(self, board, cur, nxt, k=0):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        a = _choose_d3_chain_s_shape(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2,
                                     self.w_excav, self.w_hang, self.w, self.fl, self.maxpass,
                                     self.w_chain, self.ws, self.mask(board, k),
                                     self.w_sv, self.r_hi, self.w_sp, self.hs)
        return None if a < 0 else int(a)


def selfcheck(n_games=2, seed0=36734):
    """Zero doses == the masked decider (cascade_reach_x) with the same mask, on real fw540 boards."""
    import gate_b as G, bursty_model as BM, vs_race as V, fast_rtl_x as FX, cascade_reach_x as R
    from drmario.faithful_game import Pill
    w, fl = FX.variant("winner")
    dec0 = ShapeReachDecider(w, fl)
    m = BM.fit_struktured_20260804(); boards = []
    base = V._decider("fw540")
    def choose(env, col, vir, ctx):
        boards.append((env.board.clone(), env.pills_placed, Pill(int(env.cur.a), int(env.cur.b)), Pill(int(env.nxt.a), int(env.nxt.b))))
        return base(env, col, vir, ctx)
    for s in range(n_games):
        G.play(seed0 + 2 * s, None, m, choose=choose)
    same = 0
    for b, k, c, nx in boards:
        col, vir = board_flat(b); lnk = np.ascontiguousarray(b.link, dtype=np.int8).reshape(-1)
        mk = dec0.mask(b, k)
        a1 = R._choose_d3_chain_s_masked(col, vir, lnk, c.a, c.b, nx.a, nx.b, 8, dec0.w_excav, dec0.w_hang,
                                         dec0.w, dec0.fl, 0, 540, 20, mk)
        same += int((None if a1 < 0 else int(a1)) == dec0.choose(b, c, nx, k))
    print(f"shape selfcheck: {same}/{len(boards)} identical to the masked decider at zero doses")
    return same == len(boards)


if __name__ == "__main__":
    import sys
    sys.exit(0 if selfcheck() else 1)
