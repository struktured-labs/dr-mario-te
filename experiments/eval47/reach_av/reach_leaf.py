#!/usr/bin/env python3
"""A_v -- the VERTICAL-half REACH correction to the champion leaf's `rdy_ext` term.

THE DEFECT
----------
`fast_rtl_x._eval_rtl`'s per-virus loop measures, for each virus, how much room
there is around it for a 4-in-a-row window.  Both the horizontal and the vertical
span walks extend through any cell that is EMPTY **or** the virus's own colour:

    while vspan_lo != 0 and ((col[(vspan_lo-1)*COLS+vc] == 0) or col[...] == vcol):
        vspan_lo -= 1

An empty cell is treated as "I can put my colour there later".  Physically that is
only true if a capsule half can ARRIVE there.  With no tuck executor on the cart
(DRTUCK absent from the probe cart manifest), the only way a half lands in cell
(r, c) is a straight drop down column c -- which requires NO occupied cell above it
in that column.  Every empty cell at or below the column's top occupied row is a
HOLE: unfillable, forever, by the shipped executor.  The eval nonetheless counts it
toward the >=4 span and so credits `rdy_ext` for virus-clearing windows no pill can
complete.

A_v corrects the VERTICAL half only.  That is deliberate:

  * the vertical span walk stays inside ONE column, so the reach predicate
    ("row r is fillable iff r < top_occupied_row(c)") is COLUMN-LOCAL.  The delta-eval
    engine memoises per-column and per-virus (`_vterms_v` depends only on column vc);
    A_v keeps that dependency, so the delta engine and the bit-exactness gates stay
    structurally valid.
  * the horizontal walk crosses columns and would need a per-column reach vector --
    a different, larger change.  Out of scope this pass.

Consequences of A_v, stated so they can be checked rather than assumed:
  * DOWNWARD (below the virus): every empty cell is below the column's top occupied
    row (the virus itself is occupied), so it is ALWAYS unreachable.  A_v blocks the
    downward empty extension entirely.  Same-colour occupied cells still extend it.
  * UPWARD: empty cells extend the span only while they sit strictly above the
    column's first occupied row -- i.e. only into genuinely open sky.

PROVENANCE / SAFETY
-------------------
Nothing in the shipped kernel is edited.  `_eval_rx` is a verbatim copy of
`fast_rtl_x._eval_rtl` plus (a) a per-column top-occupied-row scan folded into the
existing column walk and (b) the guard above, gated on a `reach` argument.  With
`reach == 0` the arithmetic is the untouched original, and `av_gate.py` proves that
VALUE-EXACTLY against the real `_eval_rtl` -- and proves the flag is not inert by
requiring divergence at `reach == 1`.

`kernel_hash()` returns the sha256 of THIS file plus the shipped `fast_rtl_x.py`, so
every result row can record the code path that produced it.
"""
from __future__ import annotations

import hashlib
import os
import sys

ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src",
           QA, QA + "/tuck_v3", QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
from numba import njit, int8, int32, int64, float64

import fast_rtl_x as FX
from fast_sim_x import ROWS, COLS, NCELL, _expand_core, _virus_count, _stable_desc

# ---- constants lifted from the shipped kernel (bound, never re-typed) -------
R_BIAS, R_MAXH, R_HOLES = FX.R_BIAS, FX.R_MAXH, FX.R_HOLES
R_TOPRISK, R_SPAWN, R_SETUP = FX.R_TOPRISK, FX.R_SPAWN, FX.R_SETUP
R_MATCHED, R_BURIED, R_RDYEXT = FX.R_MATCHED, FX.R_BURIED, FX.R_RDYEXT
R_VRDY, R_POLL, R_CROSS = FX.R_VRDY, FX.R_POLL, FX.R_CROSS
R_WVIR, R_WCELLS, R_VBONUS = FX.R_WVIR, FX.R_WCELLS, FX.R_VBONUS
FL_COLOR_AWARE, FL_NEAREST2, FL_MATCHED = FX.FL_COLOR_AWARE, FX.FL_NEAREST2, FX.FL_MATCHED
_WIN_SHIP = FX._WIN_SHIP
_VAR_OF_O4 = FX._VAR_OF_O4
_THIRD_X = FX._THIRD_X
_THIRD_Y = FX._THIRD_Y

# top-occupied row per column is packed 5 bits/column into one int64 so the hot
# leaf stays allocation-free (values are 0..16, 8 columns -> 40 bits).
_TOP_BITS = 5
_TOP_MASK = (1 << _TOP_BITS) - 1


# ============================================================ A_v leaf kernel
@njit(int64(int8[:], int8[:], float64[:], int32[:], int64), cache=True, fastmath=False)
def _eval_rx(col, vir, w, fl, reach):
    """`fast_rtl_x._eval_rtl` with the A_v vertical-reach guard behind `reach`.

    reach == 0 -> arithmetic identical to _eval_rtl (proved by av_gate.py).
    reach != 0 -> vertical span empties count only where a straight drop can land."""
    maxh = 0; holes = 0; toprisk = 0; spawn = 0
    buried = 0; matched = 0
    color_aware = fl[FL_COLOR_AWARE]
    nearest2 = fl[FL_NEAREST2]
    matched_on = fl[FL_MATCHED]
    topocc = int64(0)          # packed first-occupied row per column
    # ---- column walk: shape + buried + matched (+ top-occupied row) ----
    for c in range(COLS):
        seen = False; fillcnt = 0; curcol = 0; curlen = 0; vseen = 0
        first_r = ROWS
        for r in range(ROWS):
            idx = r * COLS + c
            cc = col[idx]
            if cc != 0:
                if not seen:
                    seen = True
                    first_r = r
                    h = ROWS - r
                    if h > maxh:
                        maxh = h
                if vir[idx]:
                    same = (curcol == cc)
                    if matched_on and same:
                        matched += 1
                    if (nearest2 == 0) or vseen < 2:
                        exempt = curlen if (color_aware and same) else 0
                        buried += fillcnt - exempt
                    vseen += 1
                    curcol = 0; curlen = 0
                else:
                    if curcol == cc:
                        curlen += 1
                    else:
                        curcol = cc; curlen = 1
                fillcnt += 1
                if r < 3:
                    toprisk += 1
                if r < 4 and (c == 3 or c == 4):
                    spawn += 1
            else:
                if seen:
                    holes += 1
                curcol = 0; curlen = 0
        topocc |= int64(first_r) << int64(_TOP_BITS * c)
    # ---- per-virus: rdy_ext, vrdy, pollution ----
    rdy_ext = 0; vrdy = 0; pollution = 0; cross = 0
    for vr in range(ROWS):
        for vc in range(COLS):
            if not vir[vr * COLS + vc]:
                continue
            vcol = col[vr * COLS + vc]
            # horizontal run + span  (UNTOUCHED -- A_v is the vertical half only)
            run_h = 1; p = vc
            while p != 0 and col[vr * COLS + (p - 1)] == vcol:
                run_h += 1; p -= 1
            span_lo = p
            while span_lo != 0 and ((col[vr * COLS + (span_lo - 1)] == 0) or col[vr * COLS + (span_lo - 1)] == vcol):
                span_lo -= 1
            p = vc
            while p != 7 and col[vr * COLS + (p + 1)] == vcol:
                run_h += 1; p += 1
            span_hi = p
            while span_hi != 7 and ((col[vr * COLS + (span_hi + 1)] == 0) or col[vr * COLS + (span_hi + 1)] == vcol):
                span_hi += 1
            # vertical run + span  (A_v applies here)
            top_c = (topocc >> int64(_TOP_BITS * vc)) & int64(_TOP_MASK)
            run_v = 1; p = vr
            while p != 0 and col[(p - 1) * COLS + vc] == vcol:
                run_v += 1; p -= 1
            vspan_lo = p
            while vspan_lo != 0:
                nb = col[(vspan_lo - 1) * COLS + vc]
                if nb == vcol:
                    vspan_lo -= 1
                    continue
                if nb == 0:
                    # A_v: an empty cell is fillable by a straight drop only while
                    # nothing is occupied above it in this column.
                    if reach != 0 and (vspan_lo - 1) >= top_c:
                        break
                    vspan_lo -= 1
                    continue
                break
            p = vr
            while p != 15 and col[(p + 1) * COLS + vc] == vcol:
                run_v += 1; p += 1
            vspan_hi = p
            while vspan_hi != 15:
                nb = col[(vspan_hi + 1) * COLS + vc]
                if nb == vcol:
                    vspan_hi += 1
                    continue
                if nb == 0:
                    # below the virus every empty row is >= top_c by construction,
                    # so under A_v this branch always blocks.
                    if reach != 0 and (vspan_hi + 1) >= top_c:
                        break
                    vspan_hi += 1
                    continue
                break
            hq = run_h * run_h if (span_hi - span_lo + 1) >= 4 else 0
            vq = run_v * run_v if (vspan_hi - vspan_lo + 1) >= 4 else 0
            rdy_ext += hq if hq > vq else vq
            if run_h >= 2 and run_v >= 2:
                cross += hq if hq < vq else vq
            vrdy += run_v * run_v
            for pc in range(COLS):
                if pc != vc and col[vr * COLS + pc] != 0 and not vir[vr * COLS + pc] and col[vr * COLS + pc] != vcol:
                    pollution += 1
            for pr in range(ROWS):
                if pr != vr and col[pr * COLS + vc] != 0 and not vir[pr * COLS + vc] and col[pr * COLS + vc] != vcol:
                    pollution += 1
    # ---- setup: 3-in-a-row touching same-color virus ----
    setup = 0
    for wr in range(ROWS):
        for wc in range(6):
            c0 = col[wr * COLS + wc]
            if c0 != 0 and col[wr * COLS + wc + 1] == c0 and col[wr * COLS + wc + 2] == c0:
                t = ((vir[wr * COLS + wc] and col[wr * COLS + wc] == c0)
                     or (vir[wr * COLS + wc + 1] and col[wr * COLS + wc + 1] == c0)
                     or (vir[wr * COLS + wc + 2] and col[wr * COLS + wc + 2] == c0))
                if not t and wc != 0 and vir[wr * COLS + wc - 1] and col[wr * COLS + wc - 1] == c0:
                    t = True
                if not t and wc < 5 and vir[wr * COLS + wc + 3] and col[wr * COLS + wc + 3] == c0:
                    t = True
                if t:
                    setup += 1
    for wc in range(COLS):
        for wr in range(14):
            c0 = col[wr * COLS + wc]
            if c0 != 0 and col[(wr + 1) * COLS + wc] == c0 and col[(wr + 2) * COLS + wc] == c0:
                t = ((vir[wr * COLS + wc] and col[wr * COLS + wc] == c0)
                     or (vir[(wr + 1) * COLS + wc] and col[(wr + 1) * COLS + wc] == c0)
                     or (vir[(wr + 2) * COLS + wc] and col[(wr + 2) * COLS + wc] == c0))
                if not t and wr != 0 and vir[(wr - 1) * COLS + wc] and col[(wr - 1) * COLS + wc] == c0:
                    t = True
                if not t and wr < 13 and vir[(wr + 3) * COLS + wc] and col[(wr + 3) * COLS + wc] == c0:
                    t = True
                if t:
                    setup += 1
    # ---- combine (signed 16-bit wrap) ----
    s = (int64(w[R_BIAS])
         - int64(w[R_MAXH]) * maxh
         - int64(w[R_HOLES]) * holes
         - int64(w[R_TOPRISK]) * toprisk
         - int64(w[R_SPAWN]) * spawn
         + int64(w[R_SETUP]) * setup
         + int64(w[R_MATCHED]) * matched
         - int64(w[R_BURIED]) * buried
         + int64(w[R_RDYEXT]) * rdy_ext
         + int64(w[R_VRDY]) * vrdy
         + int64(w[R_CROSS]) * cross
         - int64(w[R_POLL]) * pollution)
    s = s & 0xFFFF
    if s >= 0x8000:
        s -= 0x10000
    return s


@njit(int64[:](int8[:], int8[:], int64), cache=True, fastmath=False)
def _rdyext_only(col, vir, reach):
    """(rdy_ext, vrdy, cross, n_virus) for term-mass auditing.  Same walks as
    _eval_rx; no weights, so the audit cannot be confounded by a dose."""
    topocc = int64(0)
    for c in range(COLS):
        first_r = ROWS
        for r in range(ROWS):
            if col[r * COLS + c] != 0:
                first_r = r
                break
        topocc |= int64(first_r) << int64(_TOP_BITS * c)
    out = np.zeros(4, dtype=int64)
    for vr in range(ROWS):
        for vc in range(COLS):
            if not vir[vr * COLS + vc]:
                continue
            vcol = col[vr * COLS + vc]
            run_h = 1; p = vc
            while p != 0 and col[vr * COLS + (p - 1)] == vcol:
                run_h += 1; p -= 1
            span_lo = p
            while span_lo != 0 and ((col[vr * COLS + (span_lo - 1)] == 0) or col[vr * COLS + (span_lo - 1)] == vcol):
                span_lo -= 1
            p = vc
            while p != 7 and col[vr * COLS + (p + 1)] == vcol:
                run_h += 1; p += 1
            span_hi = p
            while span_hi != 7 and ((col[vr * COLS + (span_hi + 1)] == 0) or col[vr * COLS + (span_hi + 1)] == vcol):
                span_hi += 1
            top_c = (topocc >> int64(_TOP_BITS * vc)) & int64(_TOP_MASK)
            run_v = 1; p = vr
            while p != 0 and col[(p - 1) * COLS + vc] == vcol:
                run_v += 1; p -= 1
            vspan_lo = p
            while vspan_lo != 0:
                nb = col[(vspan_lo - 1) * COLS + vc]
                if nb == vcol:
                    vspan_lo -= 1
                    continue
                if nb == 0:
                    if reach != 0 and (vspan_lo - 1) >= top_c:
                        break
                    vspan_lo -= 1
                    continue
                break
            p = vr
            while p != 15 and col[(p + 1) * COLS + vc] == vcol:
                run_v += 1; p += 1
            vspan_hi = p
            while vspan_hi != 15:
                nb = col[(vspan_hi + 1) * COLS + vc]
                if nb == vcol:
                    vspan_hi += 1
                    continue
                if nb == 0:
                    if reach != 0 and (vspan_hi + 1) >= top_c:
                        break
                    vspan_hi += 1
                    continue
                break
            hq = run_h * run_h if (span_hi - span_lo + 1) >= 4 else 0
            vq = run_v * run_v if (vspan_hi - vspan_lo + 1) >= 4 else 0
            out[0] += hq if hq > vq else vq
            out[1] += run_v * run_v
            if run_h >= 2 and run_v >= 2:
                out[2] += hq if hq < vq else vq
            out[3] += 1
    return out


# ================================================= the depth-3 chain, threaded
@njit(int64(int8[:], int8[:], float64[:], int32[:], int64), cache=True, fastmath=False)
def _leafv_rx(col, vir, w, fl, reach):
    """Mirror of FX._leafv_ship."""
    if _virus_count(vir) == 0:
        return int64(_WIN_SHIP)
    return _eval_rx(col, vir, w, fl, reach)


@njit(int64(int8[:], int8[:], float64[:], int32[:], int64), cache=True, fastmath=False)
def _expected_third_rx(b2c, b2v, w, fl, reach):
    """Mirror of FX._expected_third_ship: 4-pill stratified expectimax, integer mean."""
    if _virus_count(b2v) == 0:
        return int64(_WIN_SHIP)
    c3 = np.empty(NCELL, dtype=int8); v3 = np.empty(NCELL, dtype=int8)
    tot = int64(0)
    for t in range(4):
        x = _THIRD_X[t]; y = _THIRD_Y[t]
        best3 = int64(0); have3 = False
        for o4 in range(4):
            var = _VAR_OF_O4[o4]
            for cl in range(8):
                ok, nv, cells = _expand_core(b2c, b2v, var, cl, x, y, c3, v3)
                if ok == 0:
                    continue
                vv = (int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells
                      + (int64(w[R_VBONUS]) if nv >= 2 else int64(0))
                      + _leafv_rx(c3, v3, w, fl, reach))
                if not have3 or vv > best3:
                    best3 = vv; have3 = True
        tot += best3 if have3 else _leafv_rx(b2c, b2v, w, fl, reach)
    return tot // int64(4)


@njit(int64(int8[:], int8[:], int64, int64, int64, int64, int64, float64[:], int32[:], int64),
      cache=True, fastmath=False)
def _ply2plus_rx(c1, v1, na, nb, topk2, w_excav, w_hang, w, fl, reach):
    """Mirror of root_search._ply2plus_value_ship_eh (itself a verbatim copy of the
    inner body of FX._choose_d3_ship_eh)."""
    b2col = np.empty((32, NCELL), dtype=int8)
    b2vir = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64)
    imms2 = np.empty(32, dtype=int64)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8)
    s2v = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8)
    e2v = np.empty(NCELL, dtype=int8)
    m2 = 0
    for o42 in range(4):
        var2 = _VAR_OF_O4[o42]
        for col2 in range(8):
            ok2, nv2, cells2 = _expand_core(c1, v1, var2, col2, na, nb, s2c, s2v)
            if ok2 == 0:
                continue
            imm2 = (int64(w[R_WVIR]) * nv2 + int64(w[R_WCELLS]) * cells2
                    + (int64(w[R_VBONUS]) if nv2 >= 2 else int64(0)))
            keys2[m2] = float64(imm2 + _leafv_rx(s2c, s2v, w, fl, reach))
            imms2[m2] = imm2
            for i in range(NCELL):
                b2col[m2, i] = s2c[i]
                b2vir[m2, i] = s2v[i]
            m2 += 1
    if m2 == 0:
        val_rest = _leafv_rx(c1, v1, w, fl, reach)
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
            if _virus_count(e2v) == 0:
                v2 = imms2[k2] + int64(_WIN_SHIP)
            else:
                v2 = imms2[k2] + _expected_third_rx(e2c, e2v, w, fl, reach)
            if not have2 or v2 > best2:
                best2 = v2
                have2 = True
        leaf1 = _leafv_rx(c1, v1, w, fl, reach)
        val_rest = leaf1 + ((best2 - leaf1) >> int64(1))
    val_rest += w_excav * FX._g_excav_ship(c1, v1) + w_hang * FX._g_hang_ship(c1, v1)
    return val_rest


def _root_value_rx(col, vir, nv, cells, na, nb, topk2, w_excav, w_hang, w, fl, reach):
    """Mirror of root_search._root_value."""
    imm1 = (float(w[R_WVIR]) * nv + float(w[R_WCELLS]) * cells
            + (float(w[R_VBONUS]) if nv >= 2 else 0.0))
    if _virus_count(vir) == 0:
        return imm1 + float(_WIN_SHIP)
    return imm1 + float(_ply2plus_rx(col, vir, int64(na), int64(nb), int64(topk2),
                                     int64(w_excav), int64(w_hang), w, fl, int64(reach)))


H0 = 8   # g_tower height threshold; matches pressure_rig.H0


def choose_base_rx(col, vir, ca, cb, na, nb, w, fl, wt, ws, reach):
    """Mirror of pressure_rig._choose_base / ab47._choose_base with `reach` threaded.
    Returns (action, resolved_ply1_board)."""
    from terms47 import g_tower, g_stranded
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_val, best_a, best_c1 = None, None, None
    for o4 in range(4):
        var = int(_VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = _root_value_rx(c1, v1, nv, cells, na, nb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl, reach)
            if wt:
                val -= wt * g_tower(c1, v1, H0)
            if ws:
                val -= ws * g_stranded(c1, v1)
            if best_val is None or val > best_val:
                best_val, best_a, best_c1 = val, var * 8 + cc, c1.copy()
    return best_a, best_c1


def warmup(reach_values=(0, 1)):
    """Pay every jit compile up front so worker timings are clean."""
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    z = np.zeros(NCELL, dtype=np.int8)
    z[15 * COLS + 0] = 1
    zv = np.zeros(NCELL, dtype=np.int8)
    zv[15 * COLS + 0] = 1
    for rc in reach_values:
        _eval_rx(z, zv, w, fl, int64(rc))
        _rdyext_only(z, zv, int64(rc))
        _leafv_rx(z, zv, w, fl, int64(rc))
        _expected_third_rx(z, zv, w, fl, int64(rc))
        _ply2plus_rx(z, zv, int64(1), int64(2), int64(8),
                     int64(FX._W_EXCAV_SHIP), int64(FX._W_HANG_SHIP), w, fl, int64(rc))
    from terms47 import g_tower, g_stranded
    g_tower(z, zv, H0)
    g_stranded(z, zv)


# ------------------------------------------------------------------ provenance
def kernel_hash():
    """sha256 over (this file, the shipped fast_rtl_x.py, root_search.py).  Every
    result row records this so a number can always be traced to its code path."""
    h = hashlib.sha256()
    for path in (os.path.abspath(__file__),
                 os.path.join(ROOT, "tmp/combo_term/fast_rtl_x.py"),
                 os.path.join(QA, "tuck_v3/root_search.py")):
        with open(path, "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()[:16]


def arm_stamp(reach, w_rdyext, wt, ws):
    return {"reach": int(reach), "w_rdyext": float(w_rdyext), "wt": int(wt),
            "ws": int(ws), "kernel_hash": kernel_hash()}


def weights_for(w_rdyext):
    """champion 'winner' weights with R_RDYEXT overridden."""
    w, fl = FX.variant("winner")
    w[R_RDYEXT] = float(w_rdyext)
    return w, fl


if __name__ == "__main__":
    warmup()
    print("kernel_hash:", kernel_hash())
    w, fl = FX.variant("winner")
    print("champion w_rdyext:", w[R_RDYEXT], " w_cross:", w[R_CROSS])
