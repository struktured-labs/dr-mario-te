#!/usr/bin/env python3
"""PLAN EXPOSURE (STEER1 post-hoc realistic pre-hold): `_choose_d3_chain_s_plan` = a MECHANICAL COPY of
cascade_stranded_x._choose_d3_chain_s (textual transform) that ALSO returns the chosen root's best PLY-2 action
(the brain's plan for the NEXT pill, computed now: before the new preview is known and before any garbage
from this placement lands). Returns root*64 + (ply2+1); ply2 = -1 when no ply-2 search ran. The root action
must be identical to the stranded decider (selfcheck()). This is exactly what a firmware change could
publish into the mailbox for the cart to pre-hold toward.
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


@njit(cache=True)
def _choose_d3_chain_s_plan(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang,
                       w, fl, maxpass, w_chain, ws):
    """`cascade_link_x._choose_d3_linked` with the chain bonus folded into every imm.
    At w_chain=0 this must return the identical action."""
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8)
    l1 = np.empty(NCELL, dtype=int8)
    b2col = np.empty((32, NCELL), dtype=int8); b2vir = np.empty((32, NCELL), dtype=int8)
    b2lnk = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64); imms2 = np.empty(32, dtype=int64)
    order2 = np.empty(32, dtype=int32)
    acts2 = np.empty(32, dtype=int64)
    s2c = np.empty(NCELL, dtype=int8); s2v = np.empty(NCELL, dtype=int8)
    s2l = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8); e2v = np.empty(NCELL, dtype=int8)
    e2l = np.empty(NCELL, dtype=int8)
    tc = np.empty(NCELL, dtype=int8); tv = np.empty(NCELL, dtype=int8)
    tl = np.empty(NCELL, dtype=int8); mask = np.empty(NCELL, dtype=int8)
    base1 = np.empty(NBASE, dtype=int64); base2 = np.empty(NBASE, dtype=int64)
    base3 = np.empty(NBASE, dtype=int64); terms = np.empty(NT, dtype=int64)
    _base_scan(pcol, pvir, fl, base1)
    best_val = int64(0); best_act = -1; have = False; best_ply2 = int64(-1)
    for o4 in range(4):
        var = _VAR_OF_O4[o4]
        for cl in range(8):
            ok, nv, cells, leaf1, ch1 = _leaf_chain(pcol, pvir, plnk, base1, var, cl,
                                                    ca, cb, w, fl, c1, v1, l1, mask,
                                                    terms, maxpass, True)
            if ok == 0:
                continue
            imm1 = _imm_chain(nv, cells, ch1, w, w_chain)
            ba2 = int64(-1)
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
                        acts2[m2] = var2 * 8 + cl2
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
                            best2 = v2; have2 = True; ba2 = acts2[k2]
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                val += w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
            val -= ws * _g_stranded47(c1, v1)
            if not have or val > best_val:
                best_val = val; best_act = var * 8 + cl; have = True; best_ply2 = ba2
    if best_act < 0:
        return int64(-1)
    return best_act * 64 + (best_ply2 + 1)



class PlanDecider(StrandedChainD3Decider):
    """choose() -> root action (identical to the stranded decider); self.plan = the ply-2 action for the next pill."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.plan = -1

    def choose(self, board, cur, nxt):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        r = _choose_d3_chain_s_plan(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2,
                                    self.w_excav, self.w_hang, self.w, self.fl,
                                    self.maxpass, self.w_chain, self.ws)
        if r < 0:
            self.plan = -1
            return None
        self.plan = int(r % 64) - 1
        return int(r // 64)


def selfcheck(n_games=2, seed0=36734):
    import gate_b as G, bursty_model as BM, vs_race as V, fast_rtl_x as FX
    from drmario.faithful_game import Pill
    w, fl = FX.variant("winner")
    ref = StrandedChainD3Decider(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20)
    pd = PlanDecider(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20)
    m = BM.fit_struktured_20260804(); boards = []
    base = V._decider("fw540")
    def choose(env, col, vir, ctx):
        boards.append((env.board.clone(), Pill(int(env.cur.a), int(env.cur.b)), Pill(int(env.nxt.a), int(env.nxt.b))))
        return base(env, col, vir, ctx)
    for s in range(n_games):
        G.play(seed0 + 2 * s, None, m, choose=choose)
    same = sum(int(ref.choose(b, c, n) == pd.choose(b, c, n)) for b, c, n in boards)
    print(f"plan selfcheck: root {same}/{len(boards)} identical to the stranded decider")
    return same == len(boards)


if __name__ == "__main__":
    import sys
    sys.exit(0 if selfcheck() else 1)
