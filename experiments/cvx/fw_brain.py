"""Offline decider for the brain that actually ships.

Shipped recipe (θ400, not changed here): winner leaf, DRCHAIN=180, DRSTRAND=20,
depth-3, topk2=8, fixpoint cascades, no tucks, no veto. DRCHAIN=540 is a
candidate, not the default.

The September leaf screens imported `cascade_chain_x` / `cascade_stranded_x`
from a tree that is not in this repo. What is in the repo is:

* `cascade_dbl_x.py` — the chain-reward depth-3 loop, plus an instant-double
  term that is defined to be chain-reward exactly when that term is 0.
* `experiments/eval47/cascade_stranded_x.py.tracked` — that loop with one extra
  root subtraction, `val -= ws * stranded_halves`.
* `experiments/vendor/fb.py` — link-faithful fixpoint resolve, written to match
  `FaithfulBoard`.

`FirmwareBrain` is that contract: the dbl loop with the double-bonus forced
off, the stranded subtraction at the root only, and resolve taken from `fb.py`.
It does not write firmware, RTL, or the leaf coefficients in `fast_rtl_x`.
"""
from __future__ import annotations

import numpy as np
from numba import njit, int8, int32, int64, float64

from fast_sim_x import NCELL, COLS, _resting, _virus_count, _stable_desc, board_flat
from fast_rtl_x import (
    R_WVIR, R_WCELLS, R_VBONUS, _WIN_SHIP, _VAR_OF_O4, _THIRD_X, _THIRD_Y,
    _W_EXCAV_SHIP, _W_HANG_SHIP, NBASE, NT, T_NVIR, _leafv_ship, _base_scan,
    _delta_terms, _combine_terms, _any_clear_lines, _g_excav_ship, _g_hang_ship,
    variant,
)

# Link codes. Same integers as drmario.faithful_game and vendor/fb.py.
LINK_NONE = 0
LINK_UP = 1
LINK_DOWN = 2
LINK_LEFT = 3
LINK_RIGHT = 4

# Shipped θ400. Do not retune these to make a screen look better.
SHIP_LEAF = "winner"
SHIP_CHAIN = 180
SHIP_STRAND = 20
SHIP_TOPK2 = 8


@njit(cache=True, fastmath=False)
def _find_clears(col, mask):
    for i in range(NCELL):
        mask[i] = 0
    for r in range(16):
        c = 0
        base = r * COLS
        while c < COLS:
            v = col[base + c]
            if v == 0:
                c += 1
                continue
            c2 = c
            while c2 < COLS and col[base + c2] == v:
                c2 += 1
            if c2 - c >= 4:
                for k in range(c, c2):
                    mask[base + k] = 1
            c = c2
    for c in range(COLS):
        r = 0
        while r < 16:
            v = col[r * COLS + c]
            if v == 0:
                r += 1
                continue
            r2 = r
            while r2 < 16 and col[r2 * COLS + c] == v:
                r2 += 1
            if r2 - r >= 4:
                for k in range(r, r2):
                    mask[k * COLS + c] = 1
            r = r2
    n = 0
    for i in range(NCELL):
        n += mask[i]
    return n


@njit(cache=True, fastmath=False)
def _apply_clear(col, vir, lnk, mask):
    nv = 0
    for i in range(NCELL):
        if mask[i] == 0:
            continue
        if vir[i] != 0:
            nv += 1
        lk = lnk[i]
        if lk != LINK_NONE:
            if lk == LINK_UP:
                dr, dc = -1, 0
            elif lk == LINK_DOWN:
                dr, dc = 1, 0
            elif lk == LINK_LEFT:
                dr, dc = 0, -1
            else:
                dr, dc = 0, 1
            r = i // COLS
            c = i - r * COLS
            pr = r + dr
            pc = c + dc
            if 0 <= pr < 16 and 0 <= pc < COLS:
                j = pr * COLS + pc
                if mask[j] == 0:
                    lnk[j] = LINK_NONE
    for i in range(NCELL):
        if mask[i] != 0:
            col[i] = 0
            vir[i] = 0
            lnk[i] = LINK_NONE
    return nv


@njit(cache=True, fastmath=False)
def _can_fall(col, i, j):
    for t in range(2):
        k = i if t == 0 else j
        if k < 0:
            continue
        npos = k + COLS
        if npos >= NCELL:
            return False
        if npos != i and npos != j and col[npos] != 0:
            return False
    return True


@njit(cache=True, fastmath=False)
def _move_down(col, vir, lnk, i, j):
    n = 1 if j < 0 else 2
    ks = np.empty(2, dtype=np.int32)
    cvs = np.empty(2, dtype=np.int8)
    vvs = np.empty(2, dtype=np.int8)
    lvs = np.empty(2, dtype=np.int8)
    ks[0] = i
    cvs[0] = col[i]
    vvs[0] = vir[i]
    lvs[0] = lnk[i]
    if j >= 0:
        ks[1] = j
        cvs[1] = col[j]
        vvs[1] = vir[j]
        lvs[1] = lnk[j]
    for t in range(n):
        k = ks[t]
        col[k] = 0
        vir[k] = 0
        lnk[k] = LINK_NONE
    for t in range(n):
        npos = ks[t] + COLS
        col[npos] = cvs[t]
        vir[npos] = vvs[t]
        lnk[npos] = lvs[t]


@njit(cache=True, fastmath=False)
def _apply_gravity(col, vir, lnk):
    b0 = np.empty(NCELL, dtype=np.int32)
    b1 = np.empty(NCELL, dtype=np.int32)
    seen = np.empty(NCELL, dtype=np.int8)
    for _pass in range(64):
        for i in range(NCELL):
            seen[i] = 0
        n = 0
        for i in range(NCELL):
            if col[i] == 0 or vir[i] != 0 or seen[i] != 0:
                continue
            lk = lnk[i]
            if lk == LINK_NONE:
                seen[i] = 1
                b0[n] = i
                b1[n] = -1
                n += 1
                continue
            if lk == LINK_UP:
                dr, dc = -1, 0
            elif lk == LINK_DOWN:
                dr, dc = 1, 0
            elif lk == LINK_LEFT:
                dr, dc = 0, -1
            else:
                dr, dc = 0, 1
            r = i // COLS
            c = i - r * COLS
            pr = r + dr
            pc = c + dc
            if 0 <= pr < 16 and 0 <= pc < COLS and seen[pr * COLS + pc] == 0:
                j = pr * COLS + pc
                seen[i] = 1
                seen[j] = 1
                b0[n] = i
                b1[n] = j
                n += 1
            else:
                seen[i] = 1
                b0[n] = i
                b1[n] = -1
                n += 1
        # Stable, bottom-first. Equal row keys keep enumeration order.
        for i in range(1, n):
            kb0 = b0[i]
            kb1 = b1[i]
            key = kb0 // COLS
            if kb1 > kb0:
                key = kb1 // COLS
            j = i
            while j > 0:
                pb0 = b0[j - 1]
                pb1 = b1[j - 1]
                pkey = pb0 // COLS
                if pb1 > pb0:
                    pkey = pb1 // COLS
                if pkey >= key:
                    break
                b0[j] = pb0
                b1[j] = pb1
                j -= 1
            b0[j] = kb0
            b1[j] = kb1
        moved = False
        for i in range(n):
            if _can_fall(col, b0[i], b1[i]):
                _move_down(col, vir, lnk, b0[i], b1[i])
                moved = True
        if not moved:
            return
    return


@njit(cache=True, fastmath=False)
def _resolve_linked(col, vir, lnk, mask, maxpass):
    """Fixpoint when maxpass <= 0. maxpass == 1 is one clear round (cap-1)."""
    cells = 0
    nv = 0
    chain = 0
    while True:
        n = _find_clears(col, mask)
        if n == 0:
            break
        if maxpass > 0 and chain >= maxpass:
            break
        chain += 1
        cells += n
        nv += _apply_clear(col, vir, lnk, mask)
        _apply_gravity(col, vir, lnk)
    return cells, nv, chain


@njit(cache=True, fastmath=False)
def _g_stranded(col, vir):
    """Non-virus cells with no orthogonal neighbour of the same colour."""
    n = 0
    for r in range(16):
        for c in range(8):
            i = r * 8 + c
            if col[i] == 0 or vir[i] != 0:
                continue
            k = col[i]
            ok = False
            if r > 0 and col[i - 8] == k:
                ok = True
            elif r < 15 and col[i + 8] == k:
                ok = True
            elif c > 0 and col[i - 1] == k:
                ok = True
            elif c < 7 and col[i + 1] == k:
                ok = True
            if not ok:
                n += 1
    return n


@njit(cache=True, fastmath=False)
def _expand_chain(pcol, pvir, plnk, variant_, column, pa, pb, ccol, cvir, clnk, mask, maxpass):
    ok, r0, c0, r1, c1 = _resting(pcol, variant_, column)
    if ok == 0:
        return (0, 0, 0, 0)
    for i in range(NCELL):
        ccol[i] = pcol[i]
        cvir[i] = pvir[i]
        clnk[i] = plnk[i]
    if variant_ == 0 or variant_ == 2:
        col0 = pa
        col1 = pb
    else:
        col0 = pb
        col1 = pa
    i0 = r0 * COLS + c0
    i1 = r1 * COLS + c1
    ccol[i0] = col0
    ccol[i1] = col1
    cvir[i0] = 0
    cvir[i1] = 0
    if variant_ < 2:
        clnk[i0] = LINK_RIGHT
        clnk[i1] = LINK_LEFT
    else:
        clnk[i0] = LINK_DOWN
        clnk[i1] = LINK_UP
    cells, nv, ch = _resolve_linked(ccol, cvir, clnk, mask, maxpass)
    return (1, nv, cells, ch)


@njit(cache=True, fastmath=False)
def _leaf_chain(pcol, pvir, plnk, base, variant_, column, pa, pb, w, fl,
                ccol, cvir, clnk, mask, terms, maxpass, want_board):
    ok, r0, c0, r1, c1 = _resting(pcol, variant_, column)
    if ok == 0:
        return (0, 0, 0, int64(0), 0)
    if variant_ == 0 or variant_ == 2:
        col0 = pa
        col1 = pb
    else:
        col0 = pb
        col1 = pa
    i0 = r0 * COLS + c0
    i1 = r1 * COLS + c1
    sv0 = pcol[i0]
    sv1 = pcol[i1]
    pcol[i0] = col0
    pcol[i1] = col1
    clearing = _any_clear_lines(pcol, r0, c0, r1, c1)
    pcol[i0] = sv0
    pcol[i1] = sv1
    if clearing:
        _o, nv, cells, ch = _expand_chain(pcol, pvir, plnk, variant_, column, pa, pb,
                                          ccol, cvir, clnk, mask, maxpass)
        return (1, nv, cells, _leafv_ship(ccol, cvir, w, fl), ch)
    if want_board:
        for i in range(NCELL):
            ccol[i] = pcol[i]
            cvir[i] = pvir[i]
            clnk[i] = plnk[i]
        ccol[i0] = col0
        ccol[i1] = col1
        cvir[i0] = 0
        cvir[i1] = 0
        if variant_ < 2:
            clnk[i0] = LINK_RIGHT
            clnk[i1] = LINK_LEFT
        else:
            clnk[i0] = LINK_DOWN
            clnk[i1] = LINK_UP
        if base[T_NVIR] == 0:
            return (1, 0, 0, int64(_WIN_SHIP), 0)
        _delta_terms(ccol, cvir, base, r0, c0, r1, c1, fl, terms)
        return (1, 0, 0, _combine_terms(terms, w), 0)
    pcol[i0] = col0
    pcol[i1] = col1
    if base[T_NVIR] == 0:
        pcol[i0] = sv0
        pcol[i1] = sv1
        return (1, 0, 0, int64(_WIN_SHIP), 0)
    _delta_terms(pcol, pvir, base, r0, c0, r1, c1, fl, terms)
    val = _combine_terms(terms, w)
    pcol[i0] = sv0
    pcol[i1] = sv1
    return (1, 0, 0, val, 0)


@njit(cache=True, fastmath=False)
def _imm_chain(nv, cells, ch, w, w_chain):
    v = int64(w[R_WVIR]) * int64(nv) + int64(w[R_WCELLS]) * int64(cells)
    if nv >= 2:
        v += int64(w[R_VBONUS])
    if ch > 1:
        v += int64(w_chain) * int64(ch - 1)
    return v


@njit(cache=True, fastmath=False)
def _expected_third_chain(b2c, b2v, b2l, w, fl, base3, terms, tc, tv, tl, mask, maxpass, w_chain):
    if _virus_count(b2v) == 0:
        return int64(_WIN_SHIP)
    _base_scan(b2c, b2v, fl, base3)
    tot = int64(0)
    for t in range(4):
        x = _THIRD_X[t]
        y = _THIRD_Y[t]
        best3 = int64(0)
        have3 = False
        for o4 in range(4):
            var = _VAR_OF_O4[o4]
            for cl in range(8):
                ok, nv, cells, lv, ch = _leaf_chain(
                    b2c, b2v, b2l, base3, var, cl, x, y, w, fl, tc, tv, tl, mask,
                    terms, maxpass, False)
                if ok == 0:
                    continue
                vv = _imm_chain(nv, cells, ch, w, w_chain) + lv
                if not have3 or vv > best3:
                    best3 = vv
                    have3 = True
        tot += best3 if have3 else _leafv_ship(b2c, b2v, w, fl)
    return tot // int64(4)


@njit(int64(int8[:], int8[:], int8[:], int64, int64, int64, int64, int64, int64, int64,
            float64[:], int32[:], int64, int64, int64), cache=True, fastmath=False)
def _choose_d3(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang,
               w, fl, maxpass, w_chain, ws):
    c1 = np.empty(NCELL, dtype=int8)
    v1 = np.empty(NCELL, dtype=int8)
    l1 = np.empty(NCELL, dtype=int8)
    b2col = np.empty((32, NCELL), dtype=int8)
    b2vir = np.empty((32, NCELL), dtype=int8)
    b2lnk = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64)
    imms2 = np.empty(32, dtype=int64)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8)
    s2v = np.empty(NCELL, dtype=int8)
    s2l = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8)
    e2v = np.empty(NCELL, dtype=int8)
    e2l = np.empty(NCELL, dtype=int8)
    tc = np.empty(NCELL, dtype=int8)
    tv = np.empty(NCELL, dtype=int8)
    tl = np.empty(NCELL, dtype=int8)
    mask = np.empty(NCELL, dtype=int8)
    base1 = np.empty(NBASE, dtype=int64)
    base2 = np.empty(NBASE, dtype=int64)
    base3 = np.empty(NBASE, dtype=int64)
    terms = np.empty(NT, dtype=int64)
    _base_scan(pcol, pvir, fl, base1)
    best_val = int64(0)
    best_act = -1
    have = False
    for o4 in range(4):
        var = _VAR_OF_O4[o4]
        for cl in range(8):
            ok, nv, cells, leaf1, ch1 = _leaf_chain(
                pcol, pvir, plnk, base1, var, cl, ca, cb, w, fl, c1, v1, l1, mask,
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
                            b2col[m2, i] = s2c[i]
                            b2vir[m2, i] = s2v[i]
                            b2lnk[m2, i] = s2l[i]
                        m2 += 1
                if m2 == 0:
                    val = imm1 + leaf1
                else:
                    _stable_desc(keys2, m2, order2)
                    kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
                    best2 = int64(0)
                    have2 = False
                    for s2 in range(kk2):
                        k2 = order2[s2]
                        for i in range(NCELL):
                            e2c[i] = b2col[k2, i]
                            e2v[i] = b2vir[k2, i]
                            e2l[i] = b2lnk[k2, i]
                        if _virus_count(e2v) == 0:
                            v2 = imms2[k2] + int64(_WIN_SHIP)
                        else:
                            v2 = imms2[k2] + _expected_third_chain(
                                e2c, e2v, e2l, w, fl, base3, terms, tc, tv, tl, mask,
                                maxpass, w_chain)
                        if not have2 or v2 > best2:
                            best2 = v2
                            have2 = True
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                val += int64(w_excav) * _g_excav_ship(c1, v1) + int64(w_hang) * _g_hang_ship(c1, v1)
            val -= int64(ws) * _g_stranded(c1, v1)
            if not have or val > best_val:
                best_val = val
                best_act = var * 8 + cl
                have = True
    return best_act


class FirmwareBrain:
    """Depth-3 decider under the shipped θ400 search contract.

    `leaf` selects a weight vector already defined in `fast_rtl_x.variant`.
    The shipped leaf is `winner`. `winholes80` is the holes leaf on the same
    search (DRCHAIN and DRSTRAND unchanged). Chain and strand doses other
    than 180 and 20 are not the shipped brain.
    """

    def __init__(self, leaf=SHIP_LEAF, chain=SHIP_CHAIN, strand=SHIP_STRAND, topk2=SHIP_TOPK2):
        w, fl = variant(leaf)
        self.leaf = leaf
        self.chain = int(chain)
        self.strand = int(strand)
        self.topk2 = int(topk2)
        self.w = np.asarray(w, dtype=np.float64)
        self.fl = np.asarray(fl, dtype=np.int32)
        self.w_excav = int(_W_EXCAV_SHIP)
        self.w_hang = int(_W_HANG_SHIP)

    @property
    def theta400_search(self):
        return self.chain == SHIP_CHAIN and self.strand == SHIP_STRAND

    @property
    def shipped(self):
        return self.theta400_search and self.leaf == SHIP_LEAF

    def choose(self, board, cur, nxt):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        a = _choose_d3(
            col, vir, lnk, int(cur.a), int(cur.b), int(nxt.a), int(nxt.b),
            self.topk2, self.w_excav, self.w_hang, self.w, self.fl,
            0, self.chain, self.strand)
        return None if a < 0 else int(a)

    def warmup(self):
        zc = np.zeros(NCELL, dtype=np.int8)
        zv = np.zeros(NCELL, dtype=np.int8)
        zl = np.zeros(NCELL, dtype=np.int8)
        _choose_d3(zc, zv, zl, 1, 2, 1, 2, self.topk2, self.w_excav, self.w_hang,
                   self.w, self.fl, 0, self.chain, self.strand)


def resolve_selfcheck(n=40, seed=11):
    """Cell-exact against fb.FB.resolve, including the (cells, viruses, chain) triple."""
    import random
    from fb import FB

    rng = random.Random(seed)
    bad = 0
    checked = 0
    for _ in range(n):
        fb = FB()
        for c in range(8):
            h = rng.randrange(0, 6)
            for r in range(16 - h, 16):
                if rng.random() < 0.3:
                    fb.col[r * 8 + c] = rng.randint(1, 3)
                    fb.vir[r * 8 + c] = 1
        for _step in range(8):
            orient = 0 if rng.random() < 0.5 else 1
            col = rng.randrange(8)
            rest = fb.resting(orient, col)
            if rest is None:
                continue
            r0, c0, r1, c1 = rest
            fb.place_at(r0, c0, rng.randint(1, 3), r1, c1, rng.randint(1, 3))
        src = FB(fb.col, fb.vir, fb.lnk)
        col = np.array(src.col, dtype=np.int8)
        vir = np.array(src.vir, dtype=np.int8)
        lnk = np.array(src.lnk, dtype=np.int8)
        mask = np.empty(NCELL, dtype=np.int8)
        got = _resolve_linked(col, vir, lnk, mask, 0)
        ref_board = FB(src.col, src.vir, src.lnk)
        ref = ref_board.resolve()
        checked += 1
        cells_ok = list(col) == ref_board.col and list(map(int, vir)) == list(map(int, ref_board.vir)) \
            and list(map(int, lnk)) == list(map(int, ref_board.lnk))
        if not cells_ok or tuple(int(x) for x in got) != tuple(int(x) for x in ref):
            bad += 1
    return bad, checked
