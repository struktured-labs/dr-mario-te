"""Per-root-action TERM DECOMPOSITION of the ANTIBODY_DIST (dist_target60) depth-3 chain search.

`_root_comps` is a MECHANICAL COPY of cascade_leaf6_x._choose_d3_chain_s_leaf6 that, instead of returning only the
argmax, returns for EVERY root action:
  val[a]      the exact int64 root value the search compares (== the original's, checked by selfcheck())
  comp[a, :]  that value split into additive components along the search's own principal variation:
                0 VIR    imm  w[R_WVIR] * viruses cleared          (all plies, PV-weighted)
                1 CELLS  imm  w[R_WCELLS] * cells cleared
                2 VBON   imm  w[R_VBONUS] (0 in winner)
                3 CHAIN  imm  w_chain * (chain - 1)                CHAIN540
                4 LEAF   base leaf (_leafv_ship / _combine_terms: maxh, holes, setup, matched, rdy, ...)
                5 HSV    x5 (HSV512)
                6 DIST   x6 (-60 * D(target))
                7 WIN    the win constant (30000) on a leaf/ply that clears the board
                8 EXHANG root ply-1 excavation/hang: 24*g_excav + 40*g_hang (g_excav credits min(run,3)^2 for a
                         same-colour non-virus run on top of a buried virus: +96 for a 2-stack on a D=1 virus)
                9 STRAND -ws * stranded
               10 SHAPE  root shape terms (0 in ANTIBODY)
              sum(comp) == val up to the search's integer rounding (>>1 and //4), |err| <= 2.
  pv2[a]      the ply-2 action on the PV (-1 if none), pv2imm[a, 0:4] its imm parts (vir, cells, vbon, chain)
The decomposition is the PV's: the root value is linear in the leaf components given the search's max choices, so
"which terms made chosen > alternative" = comp[chosen] - comp[alt], term by term.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from numba import njit, int8, int32, int64, float64

CVX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cvx")
sys.path.insert(0, os.path.abspath(CVX))
import import_pin  # noqa: E402

import_pin.pin()
from fast_sim_x import ROWS, COLS, NCELL, _virus_count, _stable_desc, _resting  # noqa: E402
from fast_rtl_x import (R_WVIR, R_WCELLS, R_VBONUS, _WIN_SHIP, _VAR_OF_O4, _THIRD_X, _THIRD_Y,  # noqa: E402
                        NBASE, NT, T_NVIR, _leafv_ship, _base_scan, _delta_terms, _combine_terms,
                        _any_clear_lines, _g_excav_ship, _g_hang_ship)
from cascade_link_x import LINK_RIGHT, LINK_LEFT, LINK_DOWN, LINK_UP, board_flat  # noqa: E402
from cascade_chain_x import _expand_chain  # noqa: E402
from cascade_stranded_x import _g_stranded47  # noqa: E402
from cascade_shape_x import _shape_terms  # noqa: E402
from cascade_leaf5b_x import _x5  # noqa: E402
from cascade_leaf6_x import _x6, _choose_d3_chain_s_leaf6, Leaf6Decider  # noqa: E402

NC = 11
NAMES = ("VIR", "CELLS", "VBON", "CHAIN", "LEAF", "HSV", "DIST", "WIN", "EXHANG", "STRAND", "SHAPE")


@njit(cache=True, fastmath=False)
def _leaf_c(pcol, pvir, plnk, base, variant_, column, pa, pb, w, fl,
            ccol, cvir, clnk, mask, terms, maxpass, want_board, w5, w6, lc):
    """_leaf_chain6 with the leaf split into lc[4]=LEAF, lc[5]=HSV, lc[6]=DIST, lc[7]=WIN. Returns (ok, nv, cells,
    lv, ch) exactly as _leaf_chain6 (lv = sum of lc)."""
    for i in range(NC):
        lc[i] = 0.0
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
            lc[4] = float64(lv)
            a5 = _x5(ccol, cvir, fl, w5); a6 = _x6(ccol, cvir, w6)
            lc[5] = float64(a5); lc[6] = float64(a6)
            lv += a5 + a6
        else:
            lc[7] = float64(lv)
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
            lc[7] = float64(_WIN_SHIP)
            return (1, 0, 0, int64(_WIN_SHIP), 0)
        _delta_terms(ccol, cvir, base, r0, c0, r1, c1, fl, terms)
        b = _combine_terms(terms, w); a5 = _x5(ccol, cvir, fl, w5); a6 = _x6(ccol, cvir, w6)
        lc[4] = float64(b); lc[5] = float64(a5); lc[6] = float64(a6)
        return (1, 0, 0, b + a5 + a6, 0)
    pcol[i0] = col0; pcol[i1] = col1
    if base[T_NVIR] == 0:
        pcol[i0] = sv0; pcol[i1] = sv1
        lc[7] = float64(_WIN_SHIP)
        return (1, 0, 0, int64(_WIN_SHIP), 0)
    _delta_terms(pcol, pvir, base, r0, c0, r1, c1, fl, terms)
    b = _combine_terms(terms, w); a5 = _x5(pcol, pvir, fl, w5); a6 = _x6(pcol, pvir, w6)
    lc[4] = float64(b); lc[5] = float64(a5); lc[6] = float64(a6)
    pcol[i0] = sv0; pcol[i1] = sv1
    return (1, 0, 0, b + a5 + a6, 0)


@njit(cache=True, fastmath=False)
def _imm_c(nv, cells, ch, w, w_chain, ic):
    ic[0] = float64(int64(w[R_WVIR]) * nv)
    ic[1] = float64(int64(w[R_WCELLS]) * cells)
    ic[2] = float64(int64(w[R_VBONUS])) if nv >= 2 else 0.0
    ic[3] = float64(int64(w_chain) * int64(ch - 1)) if ch > 1 else 0.0
    v = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells
    if nv >= 2:
        v += int64(w[R_VBONUS])
    if ch > 1:
        v += int64(w_chain) * int64(ch - 1)
    return v


@njit(cache=True, fastmath=False)
def _third_c(b2c, b2v, b2l, w, fl, base3, terms, tc, tv, tl, mask, maxpass, w_chain, w5, w6, out):
    """_expected_third_chain6 with components: out = mean over the 4 thirds of the best third's (imm + leaf) parts."""
    for i in range(NC):
        out[i] = 0.0
    if _virus_count(b2v) == 0:
        out[7] = float64(_WIN_SHIP)
        return int64(_WIN_SHIP)
    _base_scan(b2c, b2v, fl, base3)
    lc = np.zeros(NC, dtype=float64); ic = np.zeros(NC, dtype=float64)
    bestc = np.zeros(NC, dtype=float64)
    tot = int64(0)
    for t in range(4):
        x = _THIRD_X[t]; y = _THIRD_Y[t]
        best3 = int64(0); have3 = False
        for o4 in range(4):
            var = _VAR_OF_O4[o4]
            for cl in range(8):
                ok, nv, cells, lv, ch = _leaf_c(b2c, b2v, b2l, base3, var, cl, x, y,
                                                w, fl, tc, tv, tl, mask, terms, maxpass, False, w5, w6, lc)
                if ok == 0:
                    continue
                vv = _imm_c(nv, cells, ch, w, w_chain, ic) + lv
                if not have3 or vv > best3:
                    best3 = vv; have3 = True
                    for i in range(NC):
                        bestc[i] = lc[i]
                    for i in range(4):
                        bestc[i] = ic[i]
        if have3:
            tot += best3
            for i in range(NC):
                out[i] += bestc[i] / 4.0
        else:
            b = _leafv_ship(b2c, b2v, w, fl); a5 = _x5(b2c, b2v, fl, w5); a6 = _x6(b2c, b2v, w6)
            tot += b + a5 + a6
            out[4] += float64(b) / 4.0; out[5] += float64(a5) / 4.0; out[6] += float64(a6) / 4.0
    return tot // int64(4)


@njit(cache=True)
def _root_comps(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang,
                w, fl, maxpass, w_chain, ws, allowed, w_sv, r_hi, w_sp, hs, w5, w6,
                out_val, out_ok, out_comp, out_pv2, out_pv2imm):
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8)
    l1 = np.empty(NCELL, dtype=int8)
    b2col = np.empty((32, NCELL), dtype=int8); b2vir = np.empty((32, NCELL), dtype=int8)
    b2lnk = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64); imms2 = np.empty(32, dtype=int64)
    acts2 = np.empty(32, dtype=int64)
    comp2 = np.zeros((32, NC), dtype=float64)       # imm2 parts per ply-2 candidate (cols 0..3)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8); s2v = np.empty(NCELL, dtype=int8)
    s2l = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8); e2v = np.empty(NCELL, dtype=int8)
    e2l = np.empty(NCELL, dtype=int8)
    tc = np.empty(NCELL, dtype=int8); tv = np.empty(NCELL, dtype=int8)
    tl = np.empty(NCELL, dtype=int8); mask = np.empty(NCELL, dtype=int8)
    base1 = np.empty(NBASE, dtype=int64); base2 = np.empty(NBASE, dtype=int64)
    base3 = np.empty(NBASE, dtype=int64); terms = np.empty(NT, dtype=int64)
    lc1 = np.zeros(NC, dtype=float64); ic1 = np.zeros(NC, dtype=float64)
    lc2 = np.zeros(NC, dtype=float64); ic2 = np.zeros(NC, dtype=float64)
    e3 = np.zeros(NC, dtype=float64); best2c = np.zeros(NC, dtype=float64)
    _base_scan(pcol, pvir, fl, base1)
    for a in range(32):
        out_ok[a] = 0; out_val[a] = 0; out_pv2[a] = -1
        for i in range(NC):
            out_comp[a, i] = 0.0
        for i in range(4):
            out_pv2imm[a, i] = 0.0
    for o4 in range(4):
        var = _VAR_OF_O4[o4]
        for cl in range(8):
            if allowed[var * 8 + cl] == 0:
                continue
            ok, nv, cells, leaf1, ch1 = _leaf_c(pcol, pvir, plnk, base1, var, cl,
                                               ca, cb, w, fl, c1, v1, l1, mask,
                                               terms, maxpass, True, w5, w6, lc1)
            if ok == 0:
                continue
            a = var * 8 + cl
            imm1 = _imm_c(nv, cells, ch1, w, w_chain, ic1)
            for i in range(4):
                out_comp[a, i] = ic1[i]
            if _virus_count(v1) == 0:
                val = imm1 + int64(_WIN_SHIP)
                out_comp[a, 7] += float64(_WIN_SHIP)
            else:
                _base_scan(c1, v1, fl, base2)
                m2 = 0
                for o42 in range(4):
                    var2 = _VAR_OF_O4[o42]
                    for cl2 in range(8):
                        ok2, nv2, cells2, lv2, ch2 = _leaf_c(
                            c1, v1, l1, base2, var2, cl2, na, nb, w, fl,
                            s2c, s2v, s2l, mask, terms, maxpass, True, w5, w6, lc2)
                        if ok2 == 0:
                            continue
                        imm2 = _imm_c(nv2, cells2, ch2, w, w_chain, ic2)
                        keys2[m2] = float64(imm2 + lv2)
                        imms2[m2] = imm2
                        acts2[m2] = var2 * 8 + cl2
                        for i in range(4):
                            comp2[m2, i] = ic2[i]
                        for i in range(NCELL):
                            b2col[m2, i] = s2c[i]; b2vir[m2, i] = s2v[i]; b2lnk[m2, i] = s2l[i]
                        m2 += 1
                if m2 == 0:
                    val = imm1 + leaf1
                    for i in range(NC):
                        out_comp[a, i] += lc1[i]
                else:
                    _stable_desc(keys2, m2, order2)
                    kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
                    best2 = int64(0); have2 = False; bk = -1
                    for s2 in range(kk2):
                        k2 = order2[s2]
                        for i in range(NCELL):
                            e2c[i] = b2col[k2, i]; e2v[i] = b2vir[k2, i]; e2l[i] = b2lnk[k2, i]
                        if _virus_count(e2v) == 0:
                            v2 = imms2[k2] + int64(_WIN_SHIP)
                            for i in range(NC):
                                e3[i] = 0.0
                            e3[7] = float64(_WIN_SHIP)
                        else:
                            v2 = imms2[k2] + _third_c(e2c, e2v, e2l, w, fl, base3, terms, tc, tv, tl, mask,
                                                      maxpass, w_chain, w5, w6, e3)
                        if not have2 or v2 > best2:
                            best2 = v2; have2 = True; bk = k2
                            for i in range(NC):
                                best2c[i] = e3[i]
                            for i in range(4):
                                best2c[i] += comp2[k2, i]
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                    for i in range(NC):
                        out_comp[a, i] += lc1[i] + (best2c[i] - lc1[i]) / 2.0
                    out_pv2[a] = acts2[bk]
                    for i in range(4):
                        out_pv2imm[a, i] = comp2[bk, i]
                eh = w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
                val += eh
                out_comp[a, 8] += float64(eh)
            st = ws * _g_stranded47(c1, v1)
            val -= st
            out_comp[a, 9] -= float64(st)
            sh = _shape_terms(pcol, var, cl, nv, cells, w_sv, r_hi, w_sp, hs)
            val += sh
            out_comp[a, 10] += float64(sh)
            out_val[a] = val; out_ok[a] = 1


class DecompDecider(Leaf6Decider):
    """Leaf6Decider that also exposes per-root-action values and PV term components."""

    def analyse(self, board, cur, nxt, k=0, w6_override=None, w_chain=None, w5=None):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        allowed = self.mask(board, k)
        w6 = self.w6_for(col, vir, cur, allowed, k) if w6_override is None else w6_override
        val = np.zeros(32, np.int64); ok = np.zeros(32, np.int64); comp = np.zeros((32, NC))
        pv2 = np.zeros(32, np.int64); pv2imm = np.zeros((32, 4))
        _root_comps(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2, self.w_excav, self.w_hang, self.w, self.fl,
                    self.maxpass, self.w_chain if w_chain is None else w_chain, self.ws, allowed,
                    self.w_sv, self.r_hi, self.w_sp, self.hs, self.w5 if w5 is None else np.asarray(w5, np.int64), w6,
                    val, ok, comp, pv2, pv2imm)
        best = -1
        for o4 in range(4):                     # the original's iteration order: o4 -> var, then column
            var = int(_VAR_OF_O4[o4])
            for c in range(8):
                a = var * 8 + c
                if ok[a] and (best < 0 or val[a] > val[best]):
                    best = a
        return {"w6": w6, "allowed": allowed, "val": val, "ok": ok, "comp": comp, "pv2": pv2, "pv2imm": pv2imm,
                "best": best}


def selfcheck(n_games=2, seed0=36734):
    """(1) argmax of _root_comps == Leaf6Decider.choose (dist_target60 and off) on real gate-(b) boards, endgame-heavy;
    (2) sum of components == root value within rounding."""
    import gate_b as G, bursty_model as BM, vs_race as V, fast_rtl_x as FX
    from drmario.faithful_game import Pill
    w, fl = FX.variant("winner")
    kw = dict(topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)
    m = BM.fit_struktured_20260804(); boards = []
    base = V._decider("fw540")

    def choose(env, col, vir, ctx):
        boards.append((env.board.clone(), env.pills_placed, Pill(int(env.cur.a), int(env.cur.b)),
                       Pill(int(env.nxt.a), int(env.nxt.b))))
        return base(env, col, vir, ctx)
    for s in range(n_games):
        G.play(seed0 + 2 * s, None, m, choose=choose)
    boards = [b for b in boards if b[0].virus_count() <= 8] + boards[::10]
    ok_all = True
    for mode in ("dist_target", "off"):
        ref = Leaf6Decider(w, fl, mode=mode, W=60, **kw); dd = DecompDecider(w, fl, mode=mode, W=60, **kw)
        same = 0; maxerr = 0.0
        for b, k, c, n in boards:
            a_ref = ref.choose(b.clone(), c, n, k)
            r = dd.analyse(b.clone(), c, n, k)
            same += int(a_ref == r["best"])
            for a in range(32):
                if r["ok"][a]:
                    maxerr = max(maxerr, abs(r["comp"][a].sum() - r["val"][a]))
        print(f"decomp selfcheck [{mode}]: argmax {same}/{len(boards)} == Leaf6Decider.choose; "
              f"max |sum(comp) - val| = {maxerr:.2f}")
        ok_all &= same == len(boards) and maxerr <= 2.5
    return ok_all


if __name__ == "__main__":
    sys.exit(0 if selfcheck() else 1)
