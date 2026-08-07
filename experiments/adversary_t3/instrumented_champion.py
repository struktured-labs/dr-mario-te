#!/usr/bin/env python3
"""Instrumented champion decider: mechanical copy of
cascade_stranded_x._choose_d3_chain_s that returns the FULL candidate list
(every legal (o4,cl) with its val and resulting spawn-lane height) instead of
just the argmax action. Built for the risk-neutral-vs-outplayed kill
classification the team lead asked for: to tell whether the champion CHOSE a
risky line when a safer one was available, we need to see every option it
actually considered, not just the one it took.

selfcheck() proves the argmax over the returned candidate list exactly
reproduces StrandedChainD3Decider.choose() -- i.e. this sees exactly what the
champion saw, nothing more, nothing less.
"""
from __future__ import annotations

import sys
import os
import numpy as np
from numba import njit, int8, int32, int64, float64

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fast_sim_x import NCELL, _virus_count, _stable_desc
from cascade_chain_x import (_leaf_chain, _imm_chain, _base_scan,
                              _expected_third_chain, NBASE, NT)
from fast_rtl_x import (_VAR_OF_O4, _WIN_SHIP, _W_EXCAV_SHIP, _W_HANG_SHIP, variant,
                         _g_excav_ship, _g_hang_ship)
from cascade_link_x import board_flat
from cascade_stranded_x import _g_stranded47, StrandedChainD3Decider


@njit(cache=True, fastmath=False)
def _all_candidates_d3_chain_s(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang,
                               w, fl, maxpass, w_chain, ws,
                               out_act, out_val, out_spawnh, out_maxh, out_cells):
    """Mechanical copy of cascade_stranded_x._choose_d3_chain_s's root loop,
    but writing EVERY legal candidate's (action, val, resulting spawn-lane
    height, resulting max height, cells-cleared) into the out_* arrays
    (length 32, pre-allocated by caller) instead of tracking only the argmax.
    Returns the count of legal candidates written (<=32)."""
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
    n_out = 0
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
            # ---- record this candidate's resulting board's risk features ----
            spawnh = int64(0); maxh = int64(0)
            for c in range(8):
                h = int64(0)
                for r in range(16):
                    if c1[r * 8 + c] != 0:
                        h = 16 - r
                        break
                if c == 3 or c == 4:
                    if h > spawnh:
                        spawnh = h
                if h > maxh:
                    maxh = h
            out_act[n_out] = var * 8 + cl
            out_val[n_out] = val
            out_spawnh[n_out] = spawnh
            out_maxh[n_out] = maxh
            out_cells[n_out] = cells
            n_out += 1
    return n_out


def all_candidates(board, cur, nxt, w=None, fl=None, w_chain=180, ws=20, topk2=8,
                   w_excav=_W_EXCAV_SHIP, w_hang=_W_HANG_SHIP):
    """Python-friendly wrapper. Returns a list of dicts, one per legal candidate,
    sorted by val descending (index 0 = what the champion actually chooses)."""
    if w is None or fl is None:
        w, fl = variant("winner")
        w = np.asarray(w, dtype=np.float64); fl = np.asarray(fl, dtype=np.int32)
    col, vir = board_flat(board)
    lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
    out_act = np.empty(32, dtype=np.int64); out_val = np.empty(32, dtype=np.int64)
    out_spawnh = np.empty(32, dtype=np.int64); out_maxh = np.empty(32, dtype=np.int64)
    out_cells = np.empty(32, dtype=np.int64)
    n = _all_candidates_d3_chain_s(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, topk2,
                                    w_excav, w_hang, w, fl, 0, w_chain, ws,
                                    out_act, out_val, out_spawnh, out_maxh, out_cells)
    cands = [{"action": int(out_act[i]), "val": int(out_val[i]),
              "spawnh": int(out_spawnh[i]), "maxh": int(out_maxh[i]),
              "cells": int(out_cells[i])} for i in range(n)]
    cands.sort(key=lambda c: -c["val"])
    return cands


def selfcheck(n=100, seed=11):
    """all_candidates()[0]['action'] must equal StrandedChainD3Decider.choose()
    on the same board, for every trial -- proves this sees exactly what the
    champion's own argmax sees."""
    import numpy as np
    from drmario.faithful_game import FaithfulBoard, Pill, ORIENT_H, ORIENT_V

    w, fl = variant("winner")
    w = np.asarray(w, dtype=np.float64); fl = np.asarray(fl, dtype=np.int32)
    champ = StrandedChainD3Decider(w, fl, topk2=8, maxpass=0, w_chain=180, ws=20)
    rng = np.random.default_rng(seed)
    mism = 0
    for t in range(n):
        b = FaithfulBoard(16, 8, rng=rng)
        b.place_viruses(int(rng.integers(4, 40)))
        for _ in range(int(rng.integers(0, 20))):
            o = ORIENT_H if rng.random() < 0.5 else ORIENT_V
            c = int(rng.integers(0, 8))
            p = Pill(int(rng.integers(1, 4)), int(rng.integers(1, 4)))
            if b.place_pill(p, o, c):
                b.resolve()
        cur = Pill(int(rng.integers(1, 4)), int(rng.integers(1, 4)))
        nxt = Pill(int(rng.integers(1, 4)), int(rng.integers(1, 4)))
        a_champ = champ.choose(b, cur, nxt)
        cands = all_candidates(b, cur, nxt, w, fl)
        a_inst = cands[0]["action"] if cands else None
        if a_champ != a_inst:
            mism += 1
    assert mism == 0, f"{mism}/{n} mismatches between champion argmax and all_candidates()[0]"
    return n


if __name__ == "__main__":
    n = selfcheck()
    print(f"selfcheck OK: {n}/{n} boards, all_candidates()[0] == StrandedChainD3Decider.choose()")
