#!/usr/bin/env python3
"""STALL BREAKER (2026-09-25, owner #2): `_choose_d3_chain_dig` = a MECHANICAL COPY of
cascade_stranded_x._choose_d3_chain_s (the θ400 firmware brain: chain reward + ws stranded cost) with two
optional ROOT terms that the copro FIRMWARE could compute on its ~32 root candidates (no RTL change):
  val += dig_nv * nv                              (viruses cleared by this placement)
  val -= dig_sp * max(0, spawn_h(child) - dig_hs) (spawn-lane height after the placement, cols 3-4)
At dig_nv = dig_sp = 0 it must be action-identical to the stranded decider (selfcheck()).
StallBreakerDecider switches into DIG mode per pill when the bot has gone >= S placements without its
virus count dropping AND the current spawn lane is >= H rows; DIG mode may also change the chain dose
(firmware writes a_chw per search).
"""
from __future__ import annotations
import numpy as np
from numba import njit, int8, int32, int64, float64
from cascade_stranded_x import *                     # noqa  (helpers + imports the copy relies on)
from cascade_stranded_x import _g_stranded47, StrandedChainD3Decider
from cascade_chain_x import (_leaf_chain, _imm_chain, _base_scan, _expected_third_chain, NBASE, NT)
from fast_sim_x import NCELL, _virus_count, _stable_desc
from fast_rtl_x import _VAR_OF_O4, _WIN_SHIP, _g_excav_ship, _g_hang_ship, _W_EXCAV_SHIP, _W_HANG_SHIP
from cascade_link_x import board_flat


@njit(cache=True)
def _spawn_h(col):
    h = 0
    for c in (3, 4):
        for r in range(16):
            if col[r * 8 + c] != 0:
                if 16 - r > h:
                    h = 16 - r
                break
    return h


@njit(cache=True)
def _choose_d3_chain_dig(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang,
                       w, fl, maxpass, w_chain, ws, dig_sp, dig_hs, dig_nv):
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
            val -= ws * _g_stranded47(c1, v1)
            if dig_nv != 0:
                val += dig_nv * nv
            if dig_sp != 0:
                sh = _spawn_h(c1)
                if sh > dig_hs:
                    val -= dig_sp * (sh - dig_hs)
            if not have or val > best_val:
                best_val = val; best_act = var * 8 + cl; have = True
    return best_act






class StallBreakerDecider:
    def __init__(self, weights, flags, w_chain=540, ws=20, S=8, H=11, dig_chain=None,
                 dig_sp=0, dig_hs=10, dig_nv=0, topk2=8, maxpass=0):
        self.w = np.asarray(weights, dtype=np.float64); self.fl = np.asarray(flags, dtype=np.int32)
        self.w_chain, self.ws, self.S, self.H = int(w_chain), int(ws), int(S), int(H)
        self.dig_chain = self.w_chain if dig_chain is None else int(dig_chain)
        self.dig_sp, self.dig_hs, self.dig_nv = int(dig_sp), int(dig_hs), int(dig_nv)
        self.topk2, self.maxpass = int(topk2), int(maxpass)
        self.last_v = None; self.stall = 0; self.dig_pills = 0; self.pills = 0

    def choose(self, board, cur, nxt):
        v = int(board.virus_count())
        if self.last_v is not None:
            self.stall = 0 if v < self.last_v else self.stall + 1
        self.last_v = v
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        dig = self.stall >= self.S and _spawn_h(col) >= self.H
        self.pills += 1; self.dig_pills += int(dig)
        a = _choose_d3_chain_dig(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2,
                                 _W_EXCAV_SHIP, _W_HANG_SHIP, self.w, self.fl, self.maxpass,
                                 self.dig_chain if dig else self.w_chain, self.ws,
                                 self.dig_sp if dig else 0, self.dig_hs, self.dig_nv if dig else 0)
        return None if a < 0 else int(a)


def selfcheck(n=150, seed=11):
    """dig terms 0 => action-identical to StrandedChainD3Decider._choose_d3_chain_s; dig on => moves >=1."""
    import fast_rtl_x as X
    from cascade_stranded_x import _choose_d3_chain_s
    rng = np.random.default_rng(seed); w, fl = X.variant("winner")
    w = np.asarray(w, np.float64); fl = np.asarray(fl, np.int32)
    same = moved = 0
    for _ in range(n):
        col = np.zeros(128, np.int8); vir = np.zeros(128, np.int8)
        for i in range(48, 128):
            if rng.random() < 0.55:
                col[i] = rng.integers(1, 4); vir[i] = 1 if rng.random() < 0.4 else 0
        lnk = np.zeros(128, np.int8); ca, cb, na, nb = (int(x) for x in rng.integers(1, 4, 4))
        a0 = _choose_d3_chain_s(col, vir, lnk, ca, cb, na, nb, 8, _W_EXCAV_SHIP, _W_HANG_SHIP, w, fl, 0, 540, 20)
        a1 = _choose_d3_chain_dig(col, vir, lnk, ca, cb, na, nb, 8, _W_EXCAV_SHIP, _W_HANG_SHIP, w, fl, 0, 540, 20, 0, 10, 0)
        a2 = _choose_d3_chain_dig(col, vir, lnk, ca, cb, na, nb, 8, _W_EXCAV_SHIP, _W_HANG_SHIP, w, fl, 0, 540, 20, 400, 6, 300)
        same += int(a0 == a1); moved += int(a2 != a0)
    return same, moved, n
