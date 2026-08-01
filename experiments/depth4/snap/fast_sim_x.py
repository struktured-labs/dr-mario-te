#!/usr/bin/env python3
"""Numba fast mirror of the reference cart_d2_golden brain (compact gravity +
targeted cap-1 resolve + rich/rich_full eval + depth-1/2/3 search).

DESIGN: the reference env (FaithfulDrMarioEnv) is the profiled bottleneck's
COMPLEMENT -- env.step is ~0.2% of runtime; the SEARCH (`choose`) is ~100%.  So
we replace ONLY the brain here and keep the exact reference env for the game
loop, which makes every game trajectory bit-exact by construction: the fast
brain just has to return the SAME action as the reference brain on each board.

Bit-exactness: all float math is done in float64 in the identical left-to-right
order as the reference so argmax / topK sorts / tie-breaks match to the last ULP
(fastmath is OFF).  The eval weight vector is data (see W_* indices) so the same
compiled code serves the reference r47 and weekend brains AND the optimizer's
candidate vectors -- and swapping in the rtl-spec verified LeafEval mirror is a
one-function change (`_eval`).

RECONSTRUCTION NOTICE: the eval mirrored here is cart_d2_golden's rich_full,
which is the WEEKEND-era reconstruction, NOT the shipped R47 RTL (no verified
matched-cover term, config flags not modelled).  Every optimizer result built on
this module is reconstruction-based until `_eval` is swapped for the verified
mirror.
"""
from __future__ import annotations
import numpy as np
from numba import njit, int8, int32, float64

ROWS = 16
COLS = 8
NCELL = ROWS * COLS  # 128

# ---- weight-vector layout (float64[:]) --------------------------------------
W_BIAS = 0
W_VIR = 1
W_HEIGHT = 2      # WH   (subtract)
W_HOLES = 3       # WHO  (subtract)
W_TOPRISK = 4     # WTR  (subtract)
W_SPAWN = 5       # W_SPAWN (subtract)
W_SETUP = 6       # W_SETUP (add)
W_BURIED = 7      # W_BURIED (subtract)
W_READY = 8       # W_READY (add)
W_VRDY = 9        # W_VRDY (add)
W_WINBONUS = 10
W_DUALH = 11      # dual-horiz bonus (rig=0)
NW = 12

# reference rig r47 (rich_full) and weekend weight vectors -----------------
def weights_r47() -> np.ndarray:
    w = np.zeros(NW, dtype=np.float64)
    w[W_BIAS] = 500.0
    w[W_VIR] = 18.0
    w[W_HEIGHT] = 1.2
    w[W_HOLES] = 2.5
    w[W_TOPRISK] = 9.0
    w[W_SPAWN] = 15.0
    w[W_SETUP] = 4.0
    w[W_BURIED] = 3.0
    w[W_READY] = 0.4
    w[W_VRDY] = 1.2
    w[W_WINBONUS] = 100000.0
    w[W_DUALH] = 0.0
    return w


def weights_weekend() -> np.ndarray:
    w = weights_r47()
    w[W_SPAWN] = 0.0
    w[W_SETUP] = 0.0
    w[W_VRDY] = 0.0
    return w


# ============================================================ numba kernels
@njit(int32(int8[:], int32), cache=True, fastmath=False)
def _top_occ(col, c):
    for r in range(ROWS):
        if col[r * COLS + c] != 0:
            return r
    return ROWS


@njit(cache=True, fastmath=False)
def _resting(col, variant, column):
    """Return (ok, r0, c0, r1, c1) for a drop.  variant: 0/1=H, 2/3=V."""
    if variant < 2:  # horizontal, cells (r,column),(r,column+1)
        if column < 0 or column + 1 >= COLS:
            return (0, 0, 0, 0, 0)
        t0 = _top_occ(col, column)
        t1 = _top_occ(col, column + 1)
        r = (t0 if t0 < t1 else t1) - 1
        if r < 0:
            return (0, 0, 0, 0, 0)
        return (1, r, column, r, column + 1)
    else:  # vertical, top/bottom in `column`
        if column < 0 or column >= COLS:
            return (0, 0, 0, 0, 0)
        bottom = _top_occ(col, column) - 1
        top = bottom - 1
        if top < 0:
            return (0, 0, 0, 0, 0)
        return (1, top, column, bottom, column)


@njit(cache=True, fastmath=False)
def _compact_gravity(col, vir):
    """Column-compact gravity: non-virus cells fall, viruses anchor."""
    for c in range(COLS):
        write = ROWS - 1
        for r in range(ROWS - 1, -1, -1):
            idx = r * COLS + c
            if vir[idx]:
                write = r - 1
            elif col[idx] != 0:
                v = col[idx]
                col[idx] = 0
                widx = write * COLS + c
                col[widx] = v
                vir[widx] = 0
                write -= 1


@njit(cache=True, fastmath=False)
def _targeted_resolve(col, vir, r0, c0, r1, c1):
    """One targeted find-clears + apply + compact gravity (cap-1). Returns
    (cells_cleared, viruses_cleared)."""
    mask = np.zeros(NCELL, dtype=int8)
    # dedup rows / cols of the two placed cells
    rows_set = (r0, r1) if r0 != r1 else (r0, r0)
    cols_set = (c0, c1) if c0 != c1 else (c0, c0)
    # rows
    seen_r0 = False
    for k in range(2):
        rr = rows_set[k]
        if k == 1 and rr == rows_set[0]:
            continue
        i = 0
        while i < COLS:
            v = col[rr * COLS + i]
            if v == 0:
                i += 1
                continue
            j = i
            while j < COLS and col[rr * COLS + j] == v:
                j += 1
            if j - i >= 4:
                for k2 in range(i, j):
                    mask[rr * COLS + k2] = 1
            i = j
    # cols
    for k in range(2):
        cc = cols_set[k]
        if k == 1 and cc == cols_set[0]:
            continue
        i = 0
        while i < ROWS:
            v = col[i * COLS + cc]
            if v == 0:
                i += 1
                continue
            j = i
            while j < ROWS and col[j * COLS + cc] == v:
                j += 1
            if j - i >= 4:
                for k2 in range(i, j):
                    mask[k2 * COLS + cc] = 1
            i = j
    n = 0
    nv = 0
    for idx in range(NCELL):
        if mask[idx]:
            n += 1
            if vir[idx]:
                nv += 1
            col[idx] = 0
            vir[idx] = 0
    if n == 0:
        return (0, 0)
    _compact_gravity(col, vir)
    return (n, nv)


@njit(cache=True, fastmath=False)
def _expand_core(pcol, pvir, variant, column, pa, pb, ccol, cvir):
    """Eval-INDEPENDENT board mechanics: clone parent -> ccol/cvir, place the pill
    (variant,column) with base colors (pa,pb), cap-1 resolve. Returns (ok, nv,
    cells). Shared by the reconstruction and RTL-leaf search paths."""
    ok, r0, c0, r1, c1 = _resting(pcol, variant, column)
    if ok == 0:
        return (0, 0, 0)
    for i in range(NCELL):
        ccol[i] = pcol[i]
        cvir[i] = pvir[i]
    if variant == 0 or variant == 2:   # a-first (H a,b) / (V a-top)
        col0 = pa; col1 = pb
    else:                              # b-first (H b,a) / (V b-top)
        col0 = pb; col1 = pa
    ccol[r0 * COLS + c0] = col0
    ccol[r1 * COLS + c1] = col1
    cvir[r0 * COLS + c0] = 0
    cvir[r1 * COLS + c1] = 0
    cells, nv = _targeted_resolve(ccol, cvir, r0, c0, r1, c1)
    return (1, nv, cells)


@njit(cache=True, fastmath=False)
def _expand(pcol, pvir, variant, column, pa, pb, ccol, cvir, w):
    """Reconstruction expand: (ok, imm) with imm = w_vir*vir + cells."""
    ok, nv, cells = _expand_core(pcol, pvir, variant, column, pa, pb, ccol, cvir)
    if ok == 0:
        return (0, 0.0)
    return (1, w[W_VIR] * nv + cells)


@njit(cache=True, fastmath=False)
def _virus_count(vir):
    s = 0
    for i in range(NCELL):
        if vir[i]:
            s += 1
    return s


@njit(cache=True, fastmath=False)
def _setup_runs(col, vir):
    count = 0
    # rows
    for r in range(ROWS):
        base = r * COLS
        for i in range(0, COLS - 2):
            c0 = col[base + i]
            if c0 == 0:
                continue
            if col[base + i + 1] != c0 or col[base + i + 2] != c0:
                continue
            touch = vir[base + i] or vir[base + i + 1] or vir[base + i + 2]
            ends = False
            if i >= 1 and vir[base + i - 1] and col[base + i - 1] == c0:
                ends = True
            if i + 3 < COLS and vir[base + i + 3] and col[base + i + 3] == c0:
                ends = True
            if touch or ends:
                count += 1
    # cols
    for c in range(COLS):
        for i in range(0, ROWS - 2):
            c0 = col[i * COLS + c]
            if c0 == 0:
                continue
            if col[(i + 1) * COLS + c] != c0 or col[(i + 2) * COLS + c] != c0:
                continue
            touch = vir[i * COLS + c] or vir[(i + 1) * COLS + c] or vir[(i + 2) * COLS + c]
            ends = False
            if i >= 1 and vir[(i - 1) * COLS + c] and col[(i - 1) * COLS + c] == c0:
                ends = True
            if i + 3 < ROWS and vir[(i + 3) * COLS + c] and col[(i + 3) * COLS + c] == c0:
                ends = True
            if touch or ends:
                count += 1
    return count


@njit(cache=True, fastmath=False)
def _clear_readiness(col, vir):
    total = 0.0
    for r in range(ROWS):
        for c in range(COLS):
            if not vir[r * COLS + c]:
                continue
            color = col[r * COLS + c]
            hr = 1
            cc = c - 1
            while cc >= 0 and col[r * COLS + cc] == color:
                hr += 1; cc -= 1
            cc = c + 1
            while cc < COLS and col[r * COLS + cc] == color:
                hr += 1; cc += 1
            vr = 1
            rr = r - 1
            while rr >= 0 and col[rr * COLS + c] == color:
                vr += 1; rr -= 1
            rr = r + 1
            while rr < ROWS and col[rr * COLS + c] == color:
                vr += 1; rr += 1
            m = hr if hr > vr else vr
            total += float(m * m)
    return total


@njit(cache=True, fastmath=False)
def _vertical_readiness(col, vir):
    total = 0.0
    for r in range(ROWS):
        for c in range(COLS):
            if not vir[r * COLS + c]:
                continue
            color = col[r * COLS + c]
            vr = 1
            rr = r - 1
            while rr >= 0 and col[rr * COLS + c] == color:
                vr += 1; rr -= 1
            rr = r + 1
            while rr < ROWS and col[rr * COLS + c] == color:
                vr += 1; rr += 1
            total += float(vr * vr)
    return total


@njit(cache=True, fastmath=False)
def _buried(col, vir):
    total = 0
    for c in range(COLS):
        for r in range(ROWS):
            if vir[r * COLS + c]:
                for rr in range(r):
                    if col[rr * COLS + c] != 0:
                        total += 1
    return total


@njit(cache=True, fastmath=False)
def _shape_terms(col):
    maxh = 0
    holes = 0
    for c in range(COLS):
        top = ROWS
        for r in range(ROWS):
            if col[r * COLS + c] != 0:
                top = r
                break
        if top == ROWS:
            continue
        h = ROWS - top
        if h > maxh:
            maxh = h
        for r in range(top, ROWS):
            if col[r * COLS + c] == 0:
                holes += 1
    toprisk = 0
    for r in range(3):
        for c in range(COLS):
            if col[r * COLS + c] != 0:
                toprisk += 1
    spawn = 0
    for r in range(4):
        for c in range(3, 5):
            if col[r * COLS + c] != 0:
                spawn += 1
    return (maxh, holes, toprisk, spawn)


@njit(float64(int8[:], int8[:], float64[:]), cache=True, fastmath=False)
def _eval(col, vir, w):
    """board_shape_score for rich/rich_full (weekend = w_spawn=w_setup=w_vrdy=0)."""
    if _virus_count(vir) == 0:
        return w[W_BIAS] + w[W_WINBONUS]
    maxh, holes, toprisk, spawn = _shape_terms(col)
    setup = _setup_runs(col, vir)
    buried = _buried(col, vir)
    ready = _clear_readiness(col, vir)
    vready = _vertical_readiness(col, vir)
    return (w[W_BIAS] - w[W_HEIGHT] * maxh - w[W_HOLES] * holes
            - w[W_TOPRISK] * toprisk - w[W_SPAWN] * spawn
            + w[W_SETUP] * setup - w[W_BURIED] * buried
            + w[W_READY] * ready + w[W_VRDY] * vready)


@njit(cache=True, fastmath=False)
def _dualh(variant, w):
    # DUAL_HORIZ_BONUS only when action<16 (variant 0/1) AND pill.a!=pill.b; rig=0.
    if w[W_DUALH] == 0.0:
        return 0.0
    return w[W_DUALH] if variant < 2 else 0.0


@njit(cache=True, fastmath=False)
def _stable_desc(keys, m, order):
    """Fill order[0:m] with indices 0..m-1 sorted by keys descending, STABLE
    (equal keys keep ascending original index) -- matches Python list.sort(
    key=..., reverse=True)."""
    for i in range(m):
        order[i] = i
    # insertion sort, stable, descending
    for i in range(1, m):
        v = order[i]
        kv = keys[v]
        j = i - 1
        while j >= 0 and keys[order[j]] < kv:
            order[j + 1] = order[j]
            j -= 1
        order[j + 1] = v


# ------------------------------------------------------------------ depth-1
@njit(cache=True, fastmath=False)
def _choose_d1(pcol, pvir, ca, cb, w):
    """Shallow single-ply argmax key = imm1 + dualh + eval(b1)."""
    ccol = np.empty(NCELL, dtype=int8)
    cvir = np.empty(NCELL, dtype=int8)
    best_key = -1e300
    best_a = -1
    have = False
    for a in range(32):
        variant = a // 8
        column = a % 8
        ok, imm = _expand(pcol, pvir, variant, column, ca, cb, ccol, cvir, w)
        if ok == 0:
            continue
        key = imm + _dualh(variant, w) + _eval(ccol, cvir, w)
        if not have or key > best_key:
            best_key = key
            best_a = a
            have = True
    return best_a


# ------------------------------------------------------------------ depth-2
@njit(cache=True, fastmath=False)
def _choose_d2(pcol, pvir, ca, cb, na, nb, topk, w):
    b1col = np.empty((32, NCELL), dtype=int8)
    b1vir = np.empty((32, NCELL), dtype=int8)
    keys = np.empty(32, dtype=float64)
    imms = np.empty(32, dtype=float64)
    acts = np.empty(32, dtype=int32)
    tmpc = np.empty(NCELL, dtype=int8)
    tmpv = np.empty(NCELL, dtype=int8)
    m = 0
    for a in range(32):
        variant = a // 8
        column = a % 8
        ok, imm = _expand(pcol, pvir, variant, column, ca, cb, tmpc, tmpv, w)
        if ok == 0:
            continue
        e1 = _eval(tmpc, tmpv, w)
        bonus1 = _dualh(variant, w)
        keys[m] = imm + bonus1 + e1
        imms[m] = imm + bonus1
        acts[m] = a
        for i in range(NCELL):
            b1col[m, i] = tmpc[i]
            b1vir[m, i] = tmpv[i]
        m += 1
    if m == 0:
        return -1
    order = np.empty(32, dtype=int32)
    _stable_desc(keys, m, order)
    kk = m if topk <= 0 or topk > m else topk
    b2c = np.empty(NCELL, dtype=int8)
    b2v = np.empty(NCELL, dtype=int8)
    c1 = np.empty(NCELL, dtype=int8)
    v1 = np.empty(NCELL, dtype=int8)
    best_val = -1e300
    best_a = acts[order[0]]
    for s in range(kk):
        k = order[s]
        imm1 = imms[k]
        a0 = acts[k]
        for i in range(NCELL):
            c1[i] = b1col[k, i]
            v1[i] = b1vir[k, i]
        if _virus_count(v1) == 0:
            val = imm1 + w[W_WINBONUS]
        else:
            best2 = -1e300
            have2 = False
            for a2 in range(32):
                variant2 = a2 // 8
                column2 = a2 % 8
                ok2, imm2 = _expand(c1, v1, variant2, column2, na, nb, b2c, b2v, w)
                if ok2 == 0:
                    continue
                v2 = imm2 + _dualh(variant2, w) + _eval(b2c, b2v, w)
                if not have2 or v2 > best2:
                    best2 = v2
                    have2 = True
            val = imm1 + (best2 if have2 else _eval(c1, v1, w))
        if val > best_val:
            best_val = val
            best_a = a0
    return best_a


# ------------------------------------------------------------------ depth-3
@njit(cache=True, fastmath=False)
def _expected_third(b2c, b2v, w):
    if _virus_count(b2v) == 0:
        return w[W_WINBONUS]
    c3 = np.empty(NCELL, dtype=int8)
    v3 = np.empty(NCELL, dtype=int8)
    tot = 0.0
    for x in range(3):
        for y in range(3):
            best3 = -1e300
            have3 = False
            for a3 in range(32):
                variant3 = a3 // 8
                column3 = a3 % 8
                ok3, imm3 = _expand(b2c, b2v, variant3, column3, x, y, c3, v3, w)
                if ok3 == 0:
                    continue
                vv = imm3 + _eval(c3, v3, w)
                if not have3 or vv > best3:
                    best3 = vv
                    have3 = True
            tot += best3 if have3 else _eval(b2c, b2v, w)
    return tot / 9.0


@njit(cache=True, fastmath=False)
def _choose_d3(pcol, pvir, ca, cb, na, nb, topk, topk2, w):
    b1col = np.empty((32, NCELL), dtype=int8)
    b1vir = np.empty((32, NCELL), dtype=int8)
    keys = np.empty(32, dtype=float64)
    imms = np.empty(32, dtype=float64)
    acts = np.empty(32, dtype=int32)
    tmpc = np.empty(NCELL, dtype=int8)
    tmpv = np.empty(NCELL, dtype=int8)
    m = 0
    for a in range(32):
        variant = a // 8
        column = a % 8
        ok, imm = _expand(pcol, pvir, variant, column, ca, cb, tmpc, tmpv, w)
        if ok == 0:
            continue
        e1 = _eval(tmpc, tmpv, w)
        bonus1 = _dualh(variant, w)
        keys[m] = imm + bonus1 + e1
        imms[m] = imm + bonus1
        acts[m] = a
        for i in range(NCELL):
            b1col[m, i] = tmpc[i]
            b1vir[m, i] = tmpv[i]
        m += 1
    if m == 0:
        return -1
    order = np.empty(32, dtype=int32)
    _stable_desc(keys, m, order)
    kk = m if topk <= 0 or topk > m else topk

    c1 = np.empty(NCELL, dtype=int8)
    v1 = np.empty(NCELL, dtype=int8)
    # second-ply storage for topk2 prune
    b2col = np.empty((32, NCELL), dtype=int8)
    b2vir = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64)
    imms2 = np.empty(32, dtype=float64)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8)
    s2v = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8)
    e2v = np.empty(NCELL, dtype=int8)

    best_val = -1e300
    best_a = acts[order[0]]
    for s in range(kk):
        k = order[s]
        imm1 = imms[k]
        a0 = acts[k]
        for i in range(NCELL):
            c1[i] = b1col[k, i]
            v1[i] = b1vir[k, i]
        if _virus_count(v1) == 0:
            val = imm1 + w[W_WINBONUS]
        else:
            m2 = 0
            for a2 in range(32):
                variant2 = a2 // 8
                column2 = a2 % 8
                ok2, imm2 = _expand(c1, v1, variant2, column2, na, nb, s2c, s2v, w)
                if ok2 == 0:
                    continue
                keys2[m2] = imm2 + _dualh(variant2, w) + _eval(s2c, s2v, w)
                imms2[m2] = imm2
                for i in range(NCELL):
                    b2col[m2, i] = s2c[i]
                    b2vir[m2, i] = s2v[i]
                m2 += 1
            if m2 == 0:
                val = imm1 + _eval(c1, v1, w)
            else:
                _stable_desc(keys2, m2, order2)
                kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
                best2 = -1e300
                have2 = False
                for s2 in range(kk2):
                    k2 = order2[s2]
                    for i in range(NCELL):
                        e2c[i] = b2col[k2, i]
                        e2v[i] = b2vir[k2, i]
                    v2 = imms2[k2] + _expected_third(e2c, e2v, w)
                    if not have2 or v2 > best2:
                        best2 = v2
                        have2 = True
                val = imm1 + best2
        if val > best_val:
            best_val = val
            best_a = a0
    return best_a


# ============================================================ python wrappers
def board_flat(board):
    """Extract flat int8 color + is_virus (length-128) from a FaithfulBoard."""
    col = np.ascontiguousarray(board.color, dtype=np.int8).reshape(-1)
    vir = board.is_virus.reshape(-1).astype(np.int8)
    return col, vir


class FastDecider:
    """Drop-in for cart_d2_golden.CartDepth2 / CartDepth3.  depth in {1,2,3}."""

    def __init__(self, weights, depth=2, topk=0, topk2=3):
        self.w = np.asarray(weights, dtype=np.float64)
        self.depth = depth
        self.topk = int(topk)
        self.topk2 = int(topk2)

    def choose(self, board, cur, nxt):
        col, vir = board_flat(board)
        if self.depth == 1:
            a = _choose_d1(col, vir, cur.a, cur.b, self.w)
        elif self.depth == 2:
            a = _choose_d2(col, vir, cur.a, cur.b, nxt.a, nxt.b, self.topk, self.w)
        else:
            a = _choose_d3(col, vir, cur.a, cur.b, nxt.a, nxt.b, self.topk, self.topk2, self.w)
        return None if a < 0 else int(a)


def warmup(depth=3):
    """Trigger JIT compilation on a trivial board (so timing excludes compile)."""
    b_col = np.zeros(NCELL, dtype=np.int8)
    b_vir = np.zeros(NCELL, dtype=np.int8)
    w = weights_r47()
    _choose_d1(b_col, b_vir, 1, 2, w)
    _choose_d2(b_col, b_vir, 1, 2, 1, 2, 0, w)
    if depth >= 3:
        _choose_d3(b_col, b_vir, 1, 2, 1, 2, 4, 3, w)
