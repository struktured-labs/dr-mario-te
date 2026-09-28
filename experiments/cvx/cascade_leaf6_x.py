#!/usr/bin/env python3
"""STEER6 phase 3: "BUILD TOWARD A CLEAR" leaf candidates on ANTIBODY (cascade_leaf5b_x at w5 = HSV512).

One more leaf extra, `_x6(col, vir, w6)`, added next to `_x5` at every leaf value of the d3 chain search (clearing
leaves, non-clearing delta leaves, the ply-3 fallback). With w6 == 0 the search is action-identical to ANTIBODY
(selfcheck). The functions `_leaf_chain6` / `_expected_third_chain6` / `_choose_d3_chain_s_leaf6` are MECHANICAL
COPIES of the leaf5b ones (textual transform: rename, thread `w6`, add `+ _x6(...)` beside each `_x5(...)`).

Per-virus CLEARING DISTANCE D(v) on a board (min over routes, capped at CAP):
  horizontal window of 4 through v:  same colour -> 0 · empty and reachable from above (row < column top) ->
      1 + (empty cells between it and the column's stack = its SUPPORT GAP) · wrong colour or an empty cavity under
      an overhang -> route infeasible
  vertical window of 4 through v:    same colour -> 0 · empty above v and above the column top -> 1 · wrong colour,
      a cavity, or an empty cell below v -> infeasible
It is graded (each support cell built lowers it by 1) and takes the MIN over routes, so covering v from above costs
nothing while a horizontal route remains (not a burial price). Straight drops only: cavities are infeasible (tucks
are not modelled).

w6 (int64[6]):
  [0] W_DIST   -W * sum over scoped viruses of min(D(v), CAP)
  [1] CAP
  [2] TGT      -1 = every virus in the leaf board; else r*8+c of ONE firmware-chosen target (its D, or 0 once gone)
  [3] W_ROWSUP +W * sum over scoped viruses of max over feasible horizontal windows of (#same-colour + #empty cells
               with support gap 0)   (candidate b: support that has reached the target row)
  [4] SCOPE    0 = every virus; 1 = only the HSV region (cols 3..5, rows < 9): gives HSV512 a HOW-gradient
  [5] KDIG     0 = blocked routes infeasible; >0 = graded dig cost per blocking cell (walled-in viruses)
The GATES (which decisions get a non-zero w6) live in Leaf6Decider (root-side = firmware-side state).
"""
from __future__ import annotations
import numpy as np
from numba import njit, int8, int32, int64, float64
from fast_sim_x import ROWS, COLS, NCELL, _virus_count, _stable_desc, _resting, _expand_core
from fast_rtl_x import (R_WVIR, R_WCELLS, R_VBONUS, _WIN_SHIP, _VAR_OF_O4, _THIRD_X, _THIRD_Y,
                        _W_EXCAV_SHIP, _W_HANG_SHIP, NBASE, NT, T_NVIR, FL_COLOR_AWARE, FL_NEAREST2,
                        _leafv_ship, _base_scan, _delta_terms, _combine_terms, _any_clear_lines,
                        _g_excav_ship, _g_hang_ship)
from cascade_link_x import LINK_NONE, LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT, board_flat
from cascade_chain_x import _expand_chain, _imm_chain
from cascade_stranded_x import _g_stranded47
from cascade_shape_x import _shape_terms
from cascade_leaf5b_x import _x5, Leaf5ReachDecider

INF = 99


@njit(cache=True, fastmath=False)
def _vdist(col, vir, top, vr, vc, cap, kdig):
    """min over routes of the cell cost to line v up (see module doc). kdig = 0: blocked routes are infeasible;
    kdig > 0: a wrong-colour cell in the route costs kdig (it must be cleared first) and an empty cavity under an
    overhang costs 1 + kdig * (occupied cells above it) -- the graded DIG version for walled-in viruses."""
    vcol = col[vr * COLS + vc]
    best = cap
    for s in range(max(0, vc - 3), min(vc, 4) + 1):            # horizontal windows
        cost = 0; ok = True
        for c in range(s, s + 4):
            if c == vc:
                continue
            x = col[vr * COLS + c]
            if x == vcol:
                continue
            if x != 0:
                if kdig == 0:
                    ok = False; break
                cost += kdig
            elif vr >= top[c]:
                if kdig == 0:
                    ok = False; break
                above = 0
                for q in range(vr):
                    if col[q * COLS + c] != 0:
                        above += 1
                cost += 1 + kdig * above
            else:
                cost += 1 + (top[c] - 1 - vr)
        if ok and cost < best:
            best = cost
    for s in range(max(0, vr - 3), min(vr, 12) + 1):            # vertical windows
        cost = 0; ok = True
        for r in range(s, s + 4):
            if r == vr:
                continue
            x = col[r * COLS + vc]
            if x == vcol:
                continue
            if r > vr and x == 0:
                ok = False; break                                  # empty below the virus: unreachable
            if x != 0:
                if kdig == 0:
                    ok = False; break
                cost += kdig
            elif r >= top[vc]:
                if kdig == 0:
                    ok = False; break
                cost += 1 + kdig
            else:
                cost += 1
        if ok and cost < best:
            best = cost
    return best


@njit(cache=True, fastmath=False)
def _vrowsup(col, top, vr, vc):
    vcol = col[vr * COLS + vc]
    best = 0
    for s in range(max(0, vc - 3), min(vc, 4) + 1):
        sc = 0; ok = True
        for c in range(s, s + 4):
            if c == vc:
                continue
            x = col[vr * COLS + c]
            if x == vcol:
                sc += 1; continue
            if x != 0 or vr >= top[c]:
                ok = False; break
            if top[c] - 1 - vr == 0:
                sc += 1
        if ok and sc > best:
            best = sc
    return best


@njit(cache=True, fastmath=False)
def _x6(col, vir, w6):
    if w6[0] == 0 and w6[3] == 0:
        return int64(0)
    top = np.empty(COLS, dtype=np.int64)
    for c in range(COLS):
        t = ROWS
        for r in range(ROWS):
            if col[r * COLS + c] != 0:
                t = r; break
        top[c] = t
    dsum = 0; rsum = 0
    if w6[2] >= 0:
        idx = w6[2]
        if vir[idx] != 0:
            dsum = _vdist(col, vir, top, idx // COLS, idx % COLS, w6[1], w6[5])
            rsum = _vrowsup(col, top, idx // COLS, idx % COLS)
    else:
        for idx in range(NCELL):
            if vir[idx] != 0:
                if w6[4] == 1 and (idx % COLS < 3 or idx % COLS > 5 or idx // COLS >= 9):
                    continue
                if w6[0] != 0:
                    dsum += _vdist(col, vir, top, idx // COLS, idx % COLS, w6[1], w6[5])
                if w6[3] != 0:
                    rsum += _vrowsup(col, top, idx // COLS, idx % COLS)
    return int64(-w6[0] * dsum + w6[3] * rsum)


@njit(cache=True, fastmath=False)
def _root_clear_exists(pcol, pvir, ca, cb, allowed):
    """Does any ALLOWED root candidate clear a virus (the search's own cap-1 expand)? The firmware sees exactly this
    at the root (nv of each root child), so a stall counter built on it is firmware-realisable."""
    ccol = np.empty(NCELL, dtype=int8); cvir = np.empty(NCELL, dtype=int8)
    for a in range(32):
        if allowed[a] == 0:
            continue
        ok, nv, cells = _expand_core(pcol, pvir, a // 8, a % 8, ca, cb, ccol, cvir)
        if ok != 0 and nv > 0:
            return True
    return False


@njit(cache=True, fastmath=False)
def _root_dists(pcol, pvir, cap, out, kdig):
    top = np.empty(COLS, dtype=np.int64)
    for c in range(COLS):
        t = ROWS
        for r in range(ROWS):
            if pcol[r * COLS + c] != 0:
                t = r; break
        top[c] = t
    for idx in range(NCELL):
        out[idx] = _vdist(pcol, pvir, top, idx // COLS, idx % COLS, cap, kdig) if pvir[idx] != 0 else -1


@njit(cache=True, fastmath=False)
def _leaf_chain6(pcol, pvir, plnk, base, variant_, column, pa, pb, w, fl,
                 ccol, cvir, clnk, mask, terms, maxpass, want_board, w5, w6):
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
            lv += _x5(ccol, cvir, fl, w5) + _x6(ccol, cvir, w6)
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
        return (1, 0, 0, _combine_terms(terms, w) + _x5(ccol, cvir, fl, w5) + _x6(ccol, cvir, w6), 0)
    pcol[i0] = col0; pcol[i1] = col1
    if base[T_NVIR] == 0:
        pcol[i0] = sv0; pcol[i1] = sv1
        return (1, 0, 0, int64(_WIN_SHIP), 0)
    _delta_terms(pcol, pvir, base, r0, c0, r1, c1, fl, terms)
    val = _combine_terms(terms, w) + _x5(pcol, pvir, fl, w5) + _x6(pcol, pvir, w6)
    pcol[i0] = sv0; pcol[i1] = sv1
    return (1, 0, 0, val, 0)


@njit(cache=True, fastmath=False)
def _expected_third_chain6(b2c, b2v, b2l, w, fl, base3, terms, tc, tv, tl, mask,
                           maxpass, w_chain, w5, w6):
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
                ok, nv, cells, lv, ch = _leaf_chain6(b2c, b2v, b2l, base3, var, cl, x, y,
                                                     w, fl, tc, tv, tl, mask, terms,
                                                     maxpass, False, w5, w6)
                if ok == 0:
                    continue
                vv = _imm_chain(nv, cells, ch, w, w_chain) + lv
                if not have3 or vv > best3:
                    best3 = vv; have3 = True
        tot += best3 if have3 else (_leafv_ship(b2c, b2v, w, fl) + _x5(b2c, b2v, fl, w5) + _x6(b2c, b2v, w6))
    return tot // int64(4)


@njit(cache=True)
def _choose_d3_chain_s_leaf6(pcol, pvir, plnk, ca, cb, na, nb, topk2, w_excav, w_hang,
                             w, fl, maxpass, w_chain, ws, allowed, w_sv, r_hi, w_sp, hs, w5, w6):
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
            ok, nv, cells, leaf1, ch1 = _leaf_chain6(pcol, pvir, plnk, base1, var, cl,
                                                    ca, cb, w, fl, c1, v1, l1, mask,
                                                    terms, maxpass, True, w5, w6)
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
                        ok2, nv2, cells2, lv2, ch2 = _leaf_chain6(
                            c1, v1, l1, base2, var2, cl2, na, nb, w, fl,
                            s2c, s2v, s2l, mask, terms, maxpass, True, w5, w6)
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
                            v2 = imms2[k2] + _expected_third_chain6(
                                e2c, e2v, e2l, w, fl, base3, terms, tc, tv, tl, mask,
                                maxpass, w_chain, w5, w6)
                        if not have2 or v2 > best2:
                            best2 = v2; have2 = True
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                val += w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
            val -= ws * _g_stranded47(c1, v1)
            val += _shape_terms(pcol, var, cl, nv, cells, w_sv, r_hi, w_sp, hs)
            if not have or val > best_val:
                best_val = val; best_act = var * 8 + cl; have = True
    return best_act





class Leaf6Decider(Leaf5ReachDecider):
    """ANTIBODY + a STEER6 leaf extra, switched on per decision by a ROOT gate (firmware-side state):
      mode "dist_end"      (a) W_DIST on every virus while the ROOT virus count <= vk
      mode "rowsup_end"    (b) W_ROWSUP on every virus while the root virus count <= vk
      mode "dist_stall"    (c) W_DIST on every virus once `stall` consecutive decisions had no clearing root move
      mode "dist_hsv"      (e) W_DIST on the HSV-region viruses only (cols 3..5, rows < 9), always on: the HOW for HSV
      mode "dist_target"   (d) W_DIST on ONE target: the root virus with the smallest D (ties: lowest index) while
                           root vcount <= vk; firmware picks it once per decision and hands the leaf (row, col)
      mode "off"           ANTIBODY exactly
    The gate uses the ROOT board so a clear inside the search never toggles the term (no penalty for clearing)."""

    def __init__(self, weights, flags, mode="off", W=0, cap=16, vk=4, stall=4, kdig=0, **kw):
        kw.setdefault("w5", (0, 0, 0, 512))
        super().__init__(weights, flags, **kw)
        self.mode, self.W, self.cap, self.vk, self.stall_n, self.kdig = mode, int(W), int(cap), int(vk), int(stall), int(kdig)
        self.stall = 0; self.last_k = -1
        self.active = 0; self.decisions = 0
        self._d = np.empty(NCELL, dtype=np.int64)

    def w6_for(self, col, vir, cur, allowed, k):
        if k == 0 or k < self.last_k:
            self.stall = 0
        self.last_k = k
        clr = _root_clear_exists(col, vir, cur.a, cur.b, allowed)
        self.stall = 0 if clr else self.stall + 1
        w6 = np.zeros(6, dtype=np.int64); w6[1] = self.cap; w6[2] = -1; w6[5] = self.kdig
        nv = int(vir.sum())
        if self.mode == "dist_end" and nv <= self.vk:
            w6[0] = self.W
        elif self.mode == "rowsup_end" and nv <= self.vk:
            w6[3] = self.W
        elif self.mode == "dist_stall" and self.stall >= self.stall_n:
            w6[0] = self.W
        elif self.mode == "dist_hsv":
            w6[0] = self.W; w6[4] = 1
        elif self.mode == "dist_target" and nv <= self.vk:
            _root_dists(col, vir, self.cap, self._d, self.kdig)
            best = -1
            for i in range(NCELL):
                if self._d[i] >= 0 and (best < 0 or self._d[i] < self._d[best]):
                    best = i
            if best >= 0:
                w6[0] = self.W; w6[2] = best
        self.decisions += 1
        self.active += int(w6[0] != 0 or w6[3] != 0)
        return w6

    def choose(self, board, cur, nxt, k=0):
        col, vir = board_flat(board)
        lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
        allowed = self.mask(board, k)
        w6 = self.w6_for(col, vir, cur, allowed, k)
        a = _choose_d3_chain_s_leaf6(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2,
                                     self.w_excav, self.w_hang, self.w, self.fl, self.maxpass,
                                     self.w_chain, self.ws, allowed,
                                     self.w_sv, self.r_hi, self.w_sp, self.hs, self.w5, w6)
        return None if a < 0 else int(a)


def selfcheck(n_games=2, seed0=36734):
    """mode off (w6 == 0) == ANTIBODY (Leaf5ReachDecider, HSV512) on real boards; and every mode at W=0 too."""
    import gate_b as G, bursty_model as BM, vs_race as V, fast_rtl_x as FX
    from drmario.faithful_game import Pill
    w, fl = FX.variant("winner")
    kw = dict(topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)
    ref = Leaf5ReachDecider(w, fl, w5=(0, 0, 0, 512), **kw)
    ds = [Leaf6Decider(w, fl, mode=m, W=0, **kw) for m in ("off", "dist_end", "dist_stall", "dist_target", "rowsup_end")]
    m = BM.fit_struktured_20260804(); boards = []
    base = V._decider("fw540")
    def choose(env, col, vir, ctx):
        boards.append((env.board.clone(), env.pills_placed, Pill(int(env.cur.a), int(env.cur.b)), Pill(int(env.nxt.a), int(env.nxt.b))))
        return base(env, col, vir, ctx)
    for s in range(n_games):
        G.play(seed0 + 2 * s, None, m, choose=choose)
    ok = True
    for d in ds:
        same = sum(int(ref.choose(b, c, n, k) == d.choose(b, c, n, k)) for b, k, c, n in boards)
        print(f"leaf6 selfcheck [{d.mode}, W=0]: {same}/{len(boards)} identical to ANTIBODY")
        ok &= same == len(boards)
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if selfcheck() else 1)
