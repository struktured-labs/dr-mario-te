"""#26 -- INSTANT-DOUBLE credit on top of the chain-reward search.

`cascade_chain_x` with one extra quantity threaded through: LINES CLEARED IN ROUND 1.
`w_dbl` adds a flat bonus to a placement's immediate reward when the FIRST resolve round
clears two or more separate lines -- the "instant double" the user has watched the shipped
core decline three times, always mid-bottle.

WHY LINES AND NOT CELLS. The probe classifies a double as `cells >= 8 and chain == 1`,
which is a serviceable proxy for grading a handful of hand-built positions but is wrong in
both directions as a reward: a single full-width row of 8 is ONE line and would be paid,
while two lines crossing at a shared cell clear 7 and would not. This counts maximal runs
of >= 4 directly, which is also the definition the RTL would implement.

WHAT IT IS NOT. It does not reward cascades -- `w_chain` already does that, and the two are
deliberately separable so the h2h can attribute an effect to one or the other. A cascade
that clears the same cells over two rounds gets w_chain and NOT w_dbl, which is exactly the
distinction the pricing sweep found to matter: small doses of a per-cell weight convert
singles into CASCADES (nothing abandoned, not the user's complaint) while only ~100-scale
pressure converts them into DOUBLES.

★ w_dbl=0 MUST reproduce cascade_chain_x exactly. `cascade_dbl_selfcheck.py` asserts that
over a real seed corpus before any ladder is allowed to run. The failure this guards against
is a reward threaded into the root but not into the third ply (or vice versa): the arm would
still play well, still look plausible, and be answering a different question than its label.
"""
from __future__ import annotations
import numpy as np
from numba import njit, int8, int32, int64, float64

from fast_sim_x import ROWS, COLS, NCELL, _virus_count, _stable_desc, _resting

from fast_rtl_x import (
    R_WVIR, R_WCELLS, R_VBONUS, _WIN_SHIP,
    _VAR_OF_O4, _THIRD_X, _THIRD_Y, _W_EXCAV_SHIP, _W_HANG_SHIP,
    NBASE, NT, T_NVIR,
    _leafv_ship, _base_scan, _delta_terms, _combine_terms, _any_clear_lines,
    _g_excav_ship, _g_hang_ship,
    weights_rtl_r47, flags_r47, board_flat,
)
from cascade_link_x import (
    LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT, _resolve_linked,
)


@njit(cache=True, fastmath=False)
def _count_lines(col):
    """Number of MAXIMAL runs of >= 4 same-colour cells, rows then columns.

    This is 'lines', the quantity the game clears as a unit -- not cells. Counted on the
    board as placed, BEFORE any resolve, so it is round-1 only by construction rather than
    by remembering to stop.
    """
    n = 0
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
                n += 1
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
                n += 1
            i = j
    return n


@njit(cache=True, fastmath=False)
def _expand_dbl(pcol, pvir, plnk, variant_, column, pa, pb,
                ccol, cvir, clnk, mask, maxpass):
    """`_expand_chain` + the round-1 line count, taken before the resolve runs."""
    ok, r0, c0, r1, c1 = _resting(pcol, variant_, column)
    if ok == 0:
        return (0, 0, 0, 0, 0)
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
    ln1 = _count_lines(ccol)                       # BEFORE resolve == round 1
    cells, nv, ch = _resolve_linked(ccol, cvir, clnk, mask, maxpass)
    return (1, nv, cells, ch, ln1)


@njit(cache=True, fastmath=False)
def _leaf_dbl(pcol, pvir, plnk, base, variant_, column, pa, pb, w, fl,
              ccol, cvir, clnk, mask, terms, maxpass, want_board):
    """`_leaf_chain` returning round-1 lines as well. Non-clearing leaves have 0 lines and
    take the untouched delta path."""
    ok, r0, c0, r1, c1 = _resting(pcol, variant_, column)
    if ok == 0:
        return (0, 0, 0, int64(0), 0, 0)
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
        _o, nv, cells, ch, ln1 = _expand_dbl(pcol, pvir, plnk, variant_, column, pa, pb,
                                             ccol, cvir, clnk, mask, maxpass)
        return (1, nv, cells, _leafv_ship(ccol, cvir, w, fl), ch, ln1)
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
            return (1, 0, 0, int64(_WIN_SHIP), 0, 0)
        _delta_terms(ccol, cvir, base, r0, c0, r1, c1, fl, terms)
        return (1, 0, 0, _combine_terms(terms, w), 0, 0)
    pcol[i0] = col0; pcol[i1] = col1
    if base[T_NVIR] == 0:
        pcol[i0] = sv0; pcol[i1] = sv1
        return (1, 0, 0, int64(_WIN_SHIP), 0, 0)
    _delta_terms(pcol, pvir, base, r0, c0, r1, c1, fl, terms)
    val = _combine_terms(terms, w)
    pcol[i0] = sv0; pcol[i1] = sv1
    return (1, 0, 0, val, 0, 0)


@njit(cache=True, fastmath=False)
def _imm_dbl(nv, cells, ch, ln1, w, w_chain, w_dbl):
    """Immediate reward with BOTH cascade and instant-double terms.

    w_chain pays rounds after the first (a cascade); w_dbl pays two-or-more lines IN the
    first (a double). A move can earn both -- an instant double that then cascades is
    genuinely both things -- and at w_dbl=0 this is `_imm_chain` exactly.
    """
    v = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells
    if nv >= 2:
        v += int64(w[R_VBONUS])
    if ch > 1:
        v += int64(w_chain) * int64(ch - 1)
    if ln1 >= 2:
        v += int64(w_dbl)
    return v


@njit(cache=True, fastmath=False)
def _expected_third_dbl(b2c, b2v, b2l, w, fl, base3, terms, tc, tv, tl, mask,
                        maxpass, w_chain, w_dbl):
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
                ok, nv, cells, lv, ch, ln1 = _leaf_dbl(b2c, b2v, b2l, base3, var, cl, x, y,
                                                       w, fl, tc, tv, tl, mask, terms,
                                                       maxpass, False)
                if ok == 0:
                    continue
                vv = _imm_dbl(nv, cells, ch, ln1, w, w_chain, w_dbl) + lv
                if not have3 or vv > best3:
                    best3 = vv; have3 = True
        tot += best3 if have3 else _leafv_ship(b2c, b2v, w, fl)
    return tot // int64(4)


@njit(int64(int8[:], int8[:], int8[:], int64, int64, int64, int64, int64, int64, int64,
            float64[:], int32[:], int64, int64, int64), cache=True, fastmath=False)
def _choose_d3_dbl(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang,
                   w, fl, maxpass, w_chain, w_dbl):
    """`_choose_d3_chain` with w_dbl folded into EVERY imm -- root, ply 2 and ply 3.
    At w_dbl=0 this must return the identical action."""
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
            ok, nv, cells, leaf1, ch1, ln1 = _leaf_dbl(pcol, pvir, plnk, base1, var, cl,
                                                       ca, cb, w, fl, c1, v1, l1, mask,
                                                       terms, maxpass, True)
            if ok == 0:
                continue
            imm1 = _imm_dbl(nv, cells, ch1, ln1, w, w_chain, w_dbl)
            if _virus_count(v1) == 0:
                val = imm1 + int64(_WIN_SHIP)
            else:
                _base_scan(c1, v1, fl, base2)
                m2 = 0
                for o42 in range(4):
                    var2 = _VAR_OF_O4[o42]
                    for cl2 in range(8):
                        ok2, nv2, cells2, lv2, ch2, ln2 = _leaf_dbl(
                            c1, v1, l1, base2, var2, cl2, na, nb, w, fl,
                            s2c, s2v, s2l, mask, terms, maxpass, True)
                        if ok2 == 0:
                            continue
                        imm2 = _imm_dbl(nv2, cells2, ch2, ln2, w, w_chain, w_dbl)
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
                            v2 = imms2[k2] + _expected_third_dbl(
                                e2c, e2v, e2l, w, fl, base3, terms, tc, tv, tl, mask,
                                maxpass, w_chain, w_dbl)
                        if not have2 or v2 > best2:
                            best2 = v2; have2 = True
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                val += w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
            if not have or val > best_val:
                best_val = val; best_act = var * 8 + cl; have = True
    return best_act


class DblRewardD3Decider:
    """Link-faithful fixpoint depth-3 with chain-depth AND instant-double rewards.
    w_dbl=0 reproduces cascade_chain_x.ChainRewardD3Decider exactly."""

    def __init__(self, weights, flags, topk2=8, maxpass=0, w_chain=0, w_dbl=0,
                 w_excav=_W_EXCAV_SHIP, w_hang=_W_HANG_SHIP):
        self.w = np.asarray(weights, dtype=np.float64)
        self.fl = np.asarray(flags, dtype=np.int32)
        self.topk2 = int(topk2)
        self.maxpass = int(maxpass)
        self.w_chain = int(w_chain)
        self.w_dbl = int(w_dbl)
        self.w_excav = int(w_excav)
        self.w_hang = int(w_hang)

    def choose(self, board, cur, nxt):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        a = _choose_d3_dbl(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2,
                           self.w_excav, self.w_hang, self.w, self.fl,
                           self.maxpass, self.w_chain, self.w_dbl)
        return None if a < 0 else int(a)


def warmup_dbl(topk2=8):
    bc = np.zeros(NCELL, dtype=np.int8); bv = np.zeros(NCELL, dtype=np.int8)
    bl = np.zeros(NCELL, dtype=np.int8)
    w = weights_rtl_r47(); fl = flags_r47()
    _choose_d3_dbl(bc, bv, bl, 1, 2, 1, 2, topk2,
                   _W_EXCAV_SHIP, _W_HANG_SHIP, w, fl, 0, 0, 0)
