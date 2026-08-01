#!/usr/bin/env python3
"""RTL-FAITHFUL numba leaf: a bit-exact port of fpga/copro/leaf_r47.py
(LeafEval.sv S_DONE2), which is itself validated 100% cell-exact vs the live RTL
(5036/5036, tb_leafeval). This makes the coefficient optimizer RTL-SOLID rather
than reconstruction-only.

S_DONE2 combine (signed-16 wrap):
  sco = 5000 -12maxh -20holes -90toprisk -150spawn +60setup +matched60
        -30buried +12rdy_ext +24vrdy -6pollution
Flags (shipped R47 config): buried_color_aware, buried_nearest2_cap, matched_cover;
w_vrdy=24 (weekend/candidate-a = 12).

BOUNDARY / HONESTY: the LEAF here is RTL-verified (score-exact vs leaf_r47.py, see
test_rtl_leaf.py). The SEARCH it sits in (compact gravity, targeted cap-1 resolve,
depth-2/3 topK pruning, and the per-move imm = w_vir*virus + w_cells*cells reward)
is the cart_d2_golden RECONSTRUCTION of build_copro_d3 -- absolute clear rates are
model-based, but the imm scale is held identical across A/B arms so eval-WEIGHT
deltas are imm-invariant (the same logic the eval-A/B memo used).
"""
from __future__ import annotations
import numpy as np
from numba import njit, int8, int32, int64, float64

from fast_sim_x import (ROWS, COLS, NCELL, _expand_core, _virus_count, _stable_desc,
                        _resting, _targeted_resolve)

# ---- RTL weight-vector layout (float64[:], integer-valued) ------------------
R_BIAS = 0
R_MAXH = 1
R_HOLES = 2
R_TOPRISK = 3
R_SPAWN = 4
R_SETUP = 5
R_MATCHED = 6      # per-matched-virus bonus (RTL +60)
R_BURIED = 7
R_RDYEXT = 8
R_VRDY = 9
R_POLL = 10
R_WVIR = 11        # imm: per-virus-cleared reward (reconstruction search)
R_WCELLS = 12      # imm: per-cell-cleared reward
R_WINBONUS = 13
R_CROSS = 14       # COMBO-CREDIT (new): per-virus min(hq,vq), the axis rdy_ext discards
R_VBONUS = 15      # SIMULTANEITY bonus (new): flat extra imm when a placement clears
                   # >=2 viruses at once.  Super-linear, so it rewards the combo
                   # itself rather than just raising the price of every virus.
NRW = 16

# flags int32[3]
FL_COLOR_AWARE = 0
FL_NEAREST2 = 1
FL_MATCHED = 2


def weights_rtl_r47():
    w = np.zeros(NRW, dtype=np.float64)
    w[R_BIAS] = 5000.0
    w[R_MAXH] = 12.0
    w[R_HOLES] = 20.0
    w[R_TOPRISK] = 90.0
    w[R_SPAWN] = 150.0
    w[R_SETUP] = 60.0
    w[R_MATCHED] = 60.0
    w[R_BURIED] = 30.0
    w[R_RDYEXT] = 12.0
    w[R_VRDY] = 24.0
    w[R_POLL] = 6.0
    w[R_WVIR] = 180.0     # reconstruction imm (10x cart's 18 to match 5000-base leaf)
    w[R_WCELLS] = 10.0
    w[R_WINBONUS] = 1.0e6
    return w


def flags_r47():
    return np.array([1, 1, 1], dtype=np.int32)  # color_aware, nearest2, matched


# ---- named A/B variants (single-term / structural deltas from shipped R47) ----
def variant(name):
    w = weights_rtl_r47(); fl = flags_r47()
    if name == "r47":
        pass
    elif name == "vrdy12":                 # candidate (a): W_VRDY 24 -> 12
        w[R_VRDY] = 12.0
    elif name == "weekend_burial":         # candidate (b): drop R7b cap + R1 exemption
        fl[FL_COLOR_AWARE] = 0; fl[FL_NEAREST2] = 0
    elif name == "combined":               # both reverts
        w[R_VRDY] = 12.0
        fl[FL_COLOR_AWARE] = 0; fl[FL_NEAREST2] = 0
    elif name == "winner":                 # coef-opt2 validated 5-constant reweight
        # SHIPS over vrdy12: faster + cheaper (21 set-bits vs 30, removes all 3 cost
        # outliers). FLAGS UNCHANGED from r47 -- this is a pure coefficient change, NOT
        # a burial-rework revert. Single source of truth for the inline copy in
        # defense_leaf_ehd3.py and task #55's RTL apply.
        w[R_VRDY] = 8.0; w[R_BURIED] = 48.0; w[R_RDYEXT] = 8.0
        w[R_SETUP] = 32.0; w[R_MATCHED] = 48.0
    elif name.startswith("cross"):
        # combo-credit arm: shipped r47 + W_CROSS=<n>.  "cross0" MUST be bit-identical
        # to "r47" -- that equality is the lockstep gate for this whole snapshot.
        w[R_CROSS] = float(name[5:])
    elif name.startswith("wincross"):
        # combo credit stacked on the coef-opt 5-constant winner
        w[R_VRDY] = 8.0; w[R_BURIED] = 48.0; w[R_RDYEXT] = 8.0
        w[R_SETUP] = 32.0; w[R_MATCHED] = 48.0
        w[R_CROSS] = float(name[8:])
    elif name.startswith("wvir"):
        # raise the per-virus IMMEDIATE reward so cashing a setup covers the
        # readiness structure it destroys.  "wvir180" == shipped.
        w[R_WVIR] = float(name[4:])
    elif name.startswith("vbonus"):
        # SUPER-LINEAR: flat extra imm for clearing >=2 viruses in one placement.
        # Rewards simultaneity itself rather than raising the price of every virus.
        w[R_VBONUS] = float(name[6:])
    elif name.startswith("winwvir"):
        # winner + raised per-virus immediate reward.  Attacks clear DENSITY directly:
        # makes virus-clears out-compete the junk-clears that make up most of our
        # clears today.  One firmware constant (the cart's 18, scaled 10x here).
        w[R_VRDY] = 8.0; w[R_BURIED] = 48.0; w[R_RDYEXT] = 8.0
        w[R_SETUP] = 32.0; w[R_MATCHED] = 48.0
        w[R_WVIR] = float(name[7:])
    elif name.startswith("winvbonus"):
        w[R_VRDY] = 8.0; w[R_BURIED] = 48.0; w[R_RDYEXT] = 8.0
        w[R_SETUP] = 32.0; w[R_MATCHED] = 48.0
        w[R_VBONUS] = float(name[9:])
    else:
        raise ValueError(name)
    return w, fl


# ============================================================ RTL leaf kernel
@njit(int64(int8[:], int8[:], float64[:], int32[:]), cache=True, fastmath=False)
def _eval_rtl(col, vir, w, fl):
    """S_DONE2 sco (signed-16 wrap) for a non-win board. Port of leaf_r47.leaf_terms
    + _combine on (color 0..3, is_virus) flat arrays."""
    maxh = 0; holes = 0; toprisk = 0; spawn = 0
    buried = 0; matched = 0
    color_aware = fl[FL_COLOR_AWARE]
    nearest2 = fl[FL_NEAREST2]
    matched_on = fl[FL_MATCHED]
    # ---- column walk: shape + buried + matched ----
    for c in range(COLS):
        seen = False; fillcnt = 0; curcol = 0; curlen = 0; vseen = 0
        for r in range(ROWS):
            idx = r * COLS + c
            cc = col[idx]
            if cc != 0:
                if not seen:
                    seen = True
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
    # ---- per-virus: rdy_ext, vrdy, pollution ----
    rdy_ext = 0; vrdy = 0; pollution = 0; cross = 0
    for vr in range(ROWS):
        for vc in range(COLS):
            if not vir[vr * COLS + vc]:
                continue
            vcol = col[vr * COLS + vc]
            # horizontal run + span
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
            # vertical run + span
            run_v = 1; p = vr
            while p != 0 and col[(p - 1) * COLS + vc] == vcol:
                run_v += 1; p -= 1
            vspan_lo = p
            while vspan_lo != 0 and ((col[(vspan_lo - 1) * COLS + vc] == 0) or col[(vspan_lo - 1) * COLS + vc] == vcol):
                vspan_lo -= 1
            p = vr
            while p != 15 and col[(p + 1) * COLS + vc] == vcol:
                run_v += 1; p += 1
            vspan_hi = p
            while vspan_hi != 15 and ((col[(vspan_hi + 1) * COLS + vc] == 0) or col[(vspan_hi + 1) * COLS + vc] == vcol):
                vspan_hi += 1
            hq = run_h * run_h if (span_hi - span_lo + 1) >= 4 else 0
            vq = run_v * run_v if (vspan_hi - vspan_lo + 1) >= 4 else 0
            rdy_ext += hq if hq > vq else vq
            # COMBO CREDIT: rdy_ext keeps max(hq,vq) and DISCARDS the other axis. A virus
            # completable on BOTH axes is a one-pill simultaneous double-line -- the VS
            # garbage rule -- yet scores identically to a single-axis virus. `cross`
            # recovers the discarded half. Gated on both runs >= 2 so a bare isolated
            # virus (run_h=run_v=1) contributes 0 and the term cannot become a flat
            # per-virus bonus that would fight the incentive to clear.
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


@njit(float64(int8[:], int8[:], float64[:], int32[:]), cache=True, fastmath=False)
def _leaf_rtl(col, vir, w, fl):
    """Leaf value for the search: WIN_BONUS on a virus-free board, else the sco."""
    if _virus_count(vir) == 0:
        return w[R_WINBONUS]
    return float64(_eval_rtl(col, vir, w, fl))


# ============================================================ RTL search
@njit(cache=True, fastmath=False)
def _imm_rtl(nv, cells, w):
    return w[R_WVIR] * nv + w[R_WCELLS] * cells


@njit(cache=True, fastmath=False)
def _choose_d1_rtl(pcol, pvir, ca, cb, w, fl):
    ccol = np.empty(NCELL, dtype=int8); cvir = np.empty(NCELL, dtype=int8)
    best_key = -1e300; best_a = -1; have = False
    for a in range(32):
        variant = a // 8; column = a % 8
        ok, nv, cells = _expand_core(pcol, pvir, variant, column, ca, cb, ccol, cvir)
        if ok == 0:
            continue
        key = _imm_rtl(nv, cells, w) + _leaf_rtl(ccol, cvir, w, fl)
        if not have or key > best_key:
            best_key = key; best_a = a; have = True
    return best_a


@njit(cache=True, fastmath=False)
def _choose_d2_rtl(pcol, pvir, ca, cb, na, nb, topk, w, fl):
    b1col = np.empty((32, NCELL), dtype=int8); b1vir = np.empty((32, NCELL), dtype=int8)
    keys = np.empty(32, dtype=float64); imms = np.empty(32, dtype=float64)
    acts = np.empty(32, dtype=int32)
    tmpc = np.empty(NCELL, dtype=int8); tmpv = np.empty(NCELL, dtype=int8)
    m = 0
    for a in range(32):
        variant = a // 8; column = a % 8
        ok, nv, cells = _expand_core(pcol, pvir, variant, column, ca, cb, tmpc, tmpv)
        if ok == 0:
            continue
        imm = _imm_rtl(nv, cells, w)
        keys[m] = imm + _leaf_rtl(tmpc, tmpv, w, fl)
        imms[m] = imm
        acts[m] = a
        for i in range(NCELL):
            b1col[m, i] = tmpc[i]; b1vir[m, i] = tmpv[i]
        m += 1
    if m == 0:
        return -1
    order = np.empty(32, dtype=int32)
    _stable_desc(keys, m, order)
    kk = m if topk <= 0 or topk > m else topk
    b2c = np.empty(NCELL, dtype=int8); b2v = np.empty(NCELL, dtype=int8)
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8)
    best_val = -1e300; best_a = acts[order[0]]
    for s in range(kk):
        k = order[s]; imm1 = imms[k]; a0 = acts[k]
        for i in range(NCELL):
            c1[i] = b1col[k, i]; v1[i] = b1vir[k, i]
        if _virus_count(v1) == 0:
            val = imm1 + w[R_WINBONUS]
        else:
            best2 = -1e300; have2 = False
            for a2 in range(32):
                variant2 = a2 // 8; column2 = a2 % 8
                ok2, nv2, cells2 = _expand_core(c1, v1, variant2, column2, na, nb, b2c, b2v)
                if ok2 == 0:
                    continue
                v2 = _imm_rtl(nv2, cells2, w) + _leaf_rtl(b2c, b2v, w, fl)
                if not have2 or v2 > best2:
                    best2 = v2; have2 = True
            val = imm1 + (best2 if have2 else _leaf_rtl(c1, v1, w, fl))
        if val > best_val:
            best_val = val; best_a = a0
    return best_a


@njit(cache=True, fastmath=False)
def _expected_third_rtl(b2c, b2v, w, fl):
    if _virus_count(b2v) == 0:
        return w[R_WINBONUS]
    c3 = np.empty(NCELL, dtype=int8); v3 = np.empty(NCELL, dtype=int8)
    tot = 0.0
    for x in range(3):
        for y in range(3):
            best3 = -1e300; have3 = False
            for a3 in range(32):
                variant3 = a3 // 8; column3 = a3 % 8
                ok3, nv3, cells3 = _expand_core(b2c, b2v, variant3, column3, x, y, c3, v3)
                if ok3 == 0:
                    continue
                vv = _imm_rtl(nv3, cells3, w) + _leaf_rtl(c3, v3, w, fl)
                if not have3 or vv > best3:
                    best3 = vv; have3 = True
            tot += best3 if have3 else _leaf_rtl(b2c, b2v, w, fl)
    return tot / 9.0


@njit(cache=True, fastmath=False)
def _choose_d3_rtl(pcol, pvir, ca, cb, na, nb, topk, topk2, w, fl):
    b1col = np.empty((32, NCELL), dtype=int8); b1vir = np.empty((32, NCELL), dtype=int8)
    keys = np.empty(32, dtype=float64); imms = np.empty(32, dtype=float64)
    acts = np.empty(32, dtype=int32)
    tmpc = np.empty(NCELL, dtype=int8); tmpv = np.empty(NCELL, dtype=int8)
    m = 0
    for a in range(32):
        variant = a // 8; column = a % 8
        ok, nv, cells = _expand_core(pcol, pvir, variant, column, ca, cb, tmpc, tmpv)
        if ok == 0:
            continue
        imm = _imm_rtl(nv, cells, w)
        keys[m] = imm + _leaf_rtl(tmpc, tmpv, w, fl)
        imms[m] = imm
        acts[m] = a
        for i in range(NCELL):
            b1col[m, i] = tmpc[i]; b1vir[m, i] = tmpv[i]
        m += 1
    if m == 0:
        return -1
    order = np.empty(32, dtype=int32)
    _stable_desc(keys, m, order)
    kk = m if topk <= 0 or topk > m else topk
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8)
    b2col = np.empty((32, NCELL), dtype=int8); b2vir = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64); imms2 = np.empty(32, dtype=float64)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8); s2v = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8); e2v = np.empty(NCELL, dtype=int8)
    best_val = -1e300; best_a = acts[order[0]]
    for s in range(kk):
        k = order[s]; imm1 = imms[k]; a0 = acts[k]
        for i in range(NCELL):
            c1[i] = b1col[k, i]; v1[i] = b1vir[k, i]
        if _virus_count(v1) == 0:
            val = imm1 + w[R_WINBONUS]
        else:
            m2 = 0
            for a2 in range(32):
                variant2 = a2 // 8; column2 = a2 % 8
                ok2, nv2, cells2 = _expand_core(c1, v1, variant2, column2, na, nb, s2c, s2v)
                if ok2 == 0:
                    continue
                keys2[m2] = _imm_rtl(nv2, cells2, w) + _leaf_rtl(s2c, s2v, w, fl)
                imms2[m2] = _imm_rtl(nv2, cells2, w)
                for i in range(NCELL):
                    b2col[m2, i] = s2c[i]; b2vir[m2, i] = s2v[i]
                m2 += 1
            if m2 == 0:
                val = imm1 + _leaf_rtl(c1, v1, w, fl)
            else:
                _stable_desc(keys2, m2, order2)
                kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
                best2 = -1e300; have2 = False
                for s2 in range(kk2):
                    k2 = order2[s2]
                    for i in range(NCELL):
                        e2c[i] = b2col[k2, i]; e2v[i] = b2vir[k2, i]
                    v2 = imms2[k2] + _expected_third_rtl(e2c, e2v, w, fl)
                    if not have2 or v2 > best2:
                        best2 = v2; have2 = True
                val = imm1 + best2
        if val > best_val:
            best_val = val; best_a = a0
    return best_a


# ============================================================ wrappers
from fast_sim_x import board_flat


class FastRTLDecider:
    def __init__(self, weights, flags, depth=2, topk=0, topk2=3):
        self.w = np.asarray(weights, dtype=np.float64)
        self.fl = np.asarray(flags, dtype=np.int32)
        self.depth = depth; self.topk = int(topk); self.topk2 = int(topk2)

    def choose(self, board, cur, nxt):
        col, vir = board_flat(board)
        if self.depth == 1:
            a = _choose_d1_rtl(col, vir, cur.a, cur.b, self.w, self.fl)
        elif self.depth == 2:
            a = _choose_d2_rtl(col, vir, cur.a, cur.b, nxt.a, nxt.b, self.topk, self.w, self.fl)
        else:
            a = _choose_d3_rtl(col, vir, cur.a, cur.b, nxt.a, nxt.b, self.topk, self.topk2, self.w, self.fl)
        return None if a < 0 else int(a)


def warmup_rtl(depth=3):
    bc = np.zeros(NCELL, dtype=np.int8); bv = np.zeros(NCELL, dtype=np.int8)
    w = weights_rtl_r47(); fl = flags_r47()
    _eval_rtl(bc, bv, w, fl)
    _choose_d1_rtl(bc, bv, 1, 2, w, fl)
    _choose_d2_rtl(bc, bv, 1, 2, 1, 2, 0, w, fl)
    if depth >= 3:
        _choose_d3_rtl(bc, bv, 1, 2, 1, 2, 4, 3, w, fl)


# ==================================================================================
# SHIP-FAITHFUL depth-3: a numba mirror of nes_d3_golden.decide_d3 under the
# build_copro_d3 deploy config (the CELL-EXACT python mirror of the shipped 6502
# search). Differences from the reconstruction _choose_d3_rtl above, per rtl-spec:
#   - imm = 180*vir + 10*cells (already the R47 weights)
#   - WIN = 30000 (not 1e6)
#   - FULL ply1 (no topk1 prune, no sort -> enumeration order), topk2 = 8 (ply2)
#   - expectimax over the 4-pill STRATIFIED THIRD subset, integer mean (tot // 4)
#   - DISC_SHIFT=1 temporal-discount blend: val = imm1 + leaf1 + ((best2-leaf1)>>1)
#   - enumeration in _placements4 order (o4-major: 0=V A-top,1=V B-top,2=H A-left,
#     3=H B-left), col 0..7 inner; strictly-greater keep-first tie-break
#   - eh_terms (ply-1 excav+hang root add-on) OMITTED -- held out IDENTICALLY across
#     A/B arms, so the eval-weight delta is unbiased (rtl-spec). Validate this port
#     against decide_d3 with EXCAV_HANG_PLY1=False.
# All integer arithmetic (int64) to match the 6502's >>1 / //4 exactly.
# ==================================================================================
_VAR_OF_O4 = np.array([2, 3, 0, 1], dtype=np.int64)   # _placements4 o4 -> my variant
_THIRD_X = np.array([1, 2, 3, 2], dtype=np.int64)     # golden THIRD x (0,1,2,1) + 1
_THIRD_Y = np.array([2, 3, 1, 2], dtype=np.int64)     # golden THIRD y (1,2,0,1) + 1
_WIN_SHIP = 30000


@njit(int64(int8[:], int8[:], float64[:], int32[:]), cache=True, fastmath=False)
def _leafv_ship(col, vir, w, fl):
    if _virus_count(vir) == 0:
        return int64(_WIN_SHIP)
    return _eval_rtl(col, vir, w, fl)


@njit(int64(int8[:], int8[:], float64[:], int32[:]), cache=True, fastmath=False)
def _expected_third_ship(b2c, b2v, w, fl):
    """4-pill stratified expectimax; integer mean (tot // 4). Win -> 30000."""
    if _virus_count(b2v) == 0:
        return int64(_WIN_SHIP)
    c3 = np.empty(NCELL, dtype=int8); v3 = np.empty(NCELL, dtype=int8)
    tot = int64(0)
    for t in range(4):
        x = _THIRD_X[t]; y = _THIRD_Y[t]
        best3 = int64(0); have3 = False
        for o4 in range(4):
            var = _VAR_OF_O4[o4]
            for col in range(8):
                ok, nv, cells = _expand_core(b2c, b2v, var, col, x, y, c3, v3)
                if ok == 0:
                    continue
                vv = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells + (int64(w[R_VBONUS]) if nv >= 2 else int64(0)) + _leafv_ship(c3, v3, w, fl)
                if not have3 or vv > best3:
                    best3 = vv; have3 = True
        tot += best3 if have3 else _leafv_ship(b2c, b2v, w, fl)
    return tot // int64(4)


@njit(int64(int8[:], int8[:], int64, int64, int64, int64, int64, float64[:], int32[:]),
      cache=True, fastmath=False)
def _choose_d3_ship(pcol, pvir, ca, cb, na, nb, topk2, w, fl):
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8)
    b2col = np.empty((32, NCELL), dtype=int8); b2vir = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64); imms2 = np.empty(32, dtype=int64)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8); s2v = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8); e2v = np.empty(NCELL, dtype=int8)
    best_val = int64(0); best_act = -1; have = False
    for o4 in range(4):                       # ply1 in _placements4 order, FULL (no prune)
        var = _VAR_OF_O4[o4]
        for col in range(8):
            ok, nv, cells = _expand_core(pcol, pvir, var, col, ca, cb, c1, v1)
            if ok == 0:
                continue
            imm1 = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells + (int64(w[R_VBONUS]) if nv >= 2 else int64(0))
            if _virus_count(v1) == 0:
                val = imm1 + int64(_WIN_SHIP)
            else:
                m2 = 0
                for o42 in range(4):          # ply2 in _placements4 order
                    var2 = _VAR_OF_O4[o42]
                    for col2 in range(8):
                        ok2, nv2, cells2 = _expand_core(c1, v1, var2, col2, na, nb, s2c, s2v)
                        if ok2 == 0:
                            continue
                        imm2 = int64(w[R_WVIR]) * nv2 + int64(w[R_WCELLS]) * cells2 + (int64(w[R_VBONUS]) if nv2 >= 2 else int64(0))
                        keys2[m2] = float64(imm2 + _leafv_ship(s2c, s2v, w, fl))
                        imms2[m2] = imm2
                        for i in range(NCELL):
                            b2col[m2, i] = s2c[i]; b2vir[m2, i] = s2v[i]
                        m2 += 1
                if m2 == 0:
                    val = imm1 + _leafv_ship(c1, v1, w, fl)
                else:
                    _stable_desc(keys2, m2, order2)     # stable desc == decide_d3 sort
                    kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
                    best2 = int64(0); have2 = False
                    for s2 in range(kk2):
                        k2 = order2[s2]
                        for i in range(NCELL):
                            e2c[i] = b2col[k2, i]; e2v[i] = b2vir[k2, i]
                        if _virus_count(e2v) == 0:
                            v2 = imms2[k2] + int64(_WIN_SHIP)
                        else:
                            v2 = imms2[k2] + _expected_third_ship(e2c, e2v, w, fl)
                        if not have2 or v2 > best2:
                            best2 = v2; have2 = True
                    leaf1 = _leafv_ship(c1, v1, w, fl)     # b1 has viruses here
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
            if not have or val > best_val:                 # strictly-greater keep-first
                best_val = val; best_act = var * 8 + col; have = True
    return best_act


class FastShipD3Decider:
    """decide_d3-faithful depth-3 decider (eh omitted, identical across A/B arms)."""
    def __init__(self, weights, flags, topk2=8):
        self.w = np.asarray(weights, dtype=np.float64)
        self.fl = np.asarray(flags, dtype=np.int32)
        self.topk2 = int(topk2)

    def choose(self, board, cur, nxt):
        col, vir = board_flat(board)
        a = _choose_d3_ship(col, vir, cur.a, cur.b, nxt.a, nxt.b, self.topk2, self.w, self.fl)
        return None if a < 0 else int(a)


def warmup_ship(topk2=8):
    bc = np.zeros(NCELL, dtype=np.int8); bv = np.zeros(NCELL, dtype=np.int8)
    w = weights_rtl_r47(); fl = flags_r47()
    _choose_d3_ship(bc, bv, 1, 2, 1, 2, topk2, w, fl)


# ==================================================================================
# SHIP-FAITHFUL depth-3 WITH the eh_terms ply-1 root add-on (EXCAV_HANG_PLY1=True).
# This is the ACTUAL deployed brain (the eh-OFF _choose_d3_ship above drops this term
# because it's held out identically across the eval A/B arms). Requested by te-ingame-
# logo for the cadence study, whose reference bridge is decide_d3 + leaf_r47 at the
# build_copro_d3 deploy config.
#
# decide_d3 eh add-on (nes_d3_golden.py:266), applied ONLY when the resolved ply-1
# board b1 still has viruses, AFTER the DISC_SHIFT blend, NOT on a ply-1 win:
#     val += W_EXCAV * g_excav(b1) + W_HANG * g_hang(b1)
# Deploy values in build_copro_d3.build_image: W_EXCAV=24, W_HANG=40 (the module
# default -- build sets W_HANG_GAP=20/HANG_DEPTH_PROP/HANG_VIRUS_COL_ONLY but the
# golden's g_hang/g_excav are the BASE forms and read none of those R4 symbols, so the
# PYTHON bridge uses base g_hang*40, NOT the R4-refined hang -- see caveat to caller).
# g_excav = nes_d3_golden.g_excav (base, min(run,3)**2); g_hang = nes_d3_golden.g_hang.
# ==================================================================================
@njit(int64(int8[:], int8[:]), cache=True, fastmath=False)
def _g_excav_ship(col, vir):
    """Excavation readiness (nes_d3_golden.g_excav): per column, credit min(run,3)**2
    of the same-color non-virus run at the TOP of a pile that covers a buried virus."""
    total = int64(0)
    for c in range(COLS):
        r = 0
        while r < ROWS and col[r * COLS + c] == 0:
            r += 1
        if r >= ROWS:
            continue
        vr = -1
        for rr in range(r + 1, ROWS):
            if vir[rr * COLS + c]:
                vr = rr
                break
        if vr < 0:
            continue
        if vir[r * COLS + c]:                 # top of pile is itself a virus: not excavation
            continue
        top_color = col[r * COLS + c]
        run = 1
        rr = r + 1
        while rr < vr and col[rr * COLS + c] != 0 and col[rr * COLS + c] == top_color \
                and not vir[rr * COLS + c]:
            run += 1
            rr += 1
        m = run if run < 3 else 3
        total += int64(m * m)
    return total


@njit(int64(int8[:], int8[:]), cache=True, fastmath=False)
def _g_hang_ship(col, vir):
    """Hanging-half potential (nes_d3_golden.g_hang): an occupied non-virus cell with
    EMPTY directly below whose gap-drop lands on a matching color -> +1."""
    total = int64(0)
    for r in range(ROWS - 1):
        for c in range(COLS):
            idx = r * COLS + c
            if col[idx] == 0 or vir[idx]:
                continue
            if col[(r + 1) * COLS + c] != 0:  # not hovering
                continue
            rr = r + 2
            while rr < ROWS and col[rr * COLS + c] == 0:
                rr += 1
            if rr < ROWS and col[rr * COLS + c] == col[idx]:
                total += 1
    return total


@njit(int64(int8[:], int8[:], int64, int64, int64, int64, int64, int64, int64,
            float64[:], int32[:]), cache=True, fastmath=False)
def _choose_d3_ship_eh(pcol, pvir, ca, cb, na, nb, topk2, w_excav, w_hang, w, fl):
    """_choose_d3_ship + the ply-1 eh_terms root add-on (EXCAV_HANG_PLY1=True)."""
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8)
    b2col = np.empty((32, NCELL), dtype=int8); b2vir = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64); imms2 = np.empty(32, dtype=int64)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8); s2v = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8); e2v = np.empty(NCELL, dtype=int8)
    best_val = int64(0); best_act = -1; have = False
    for o4 in range(4):                       # ply1 in _placements4 order, FULL (no prune)
        var = _VAR_OF_O4[o4]
        for col in range(8):
            ok, nv, cells = _expand_core(pcol, pvir, var, col, ca, cb, c1, v1)
            if ok == 0:
                continue
            imm1 = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells + (int64(w[R_VBONUS]) if nv >= 2 else int64(0))
            if _virus_count(v1) == 0:
                val = imm1 + int64(_WIN_SHIP)     # ply-1 win: NO eh add-on (golden else-branch)
            else:
                m2 = 0
                for o42 in range(4):          # ply2 in _placements4 order
                    var2 = _VAR_OF_O4[o42]
                    for col2 in range(8):
                        ok2, nv2, cells2 = _expand_core(c1, v1, var2, col2, na, nb, s2c, s2v)
                        if ok2 == 0:
                            continue
                        imm2 = int64(w[R_WVIR]) * nv2 + int64(w[R_WCELLS]) * cells2 + (int64(w[R_VBONUS]) if nv2 >= 2 else int64(0))
                        keys2[m2] = float64(imm2 + _leafv_ship(s2c, s2v, w, fl))
                        imms2[m2] = imm2
                        for i in range(NCELL):
                            b2col[m2, i] = s2c[i]; b2vir[m2, i] = s2v[i]
                        m2 += 1
                if m2 == 0:
                    val = imm1 + _leafv_ship(c1, v1, w, fl)
                else:
                    _stable_desc(keys2, m2, order2)
                    kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
                    best2 = int64(0); have2 = False
                    for s2 in range(kk2):
                        k2 = order2[s2]
                        for i in range(NCELL):
                            e2c[i] = b2col[k2, i]; e2v[i] = b2vir[k2, i]
                        if _virus_count(e2v) == 0:
                            v2 = imms2[k2] + int64(_WIN_SHIP)
                        else:
                            v2 = imms2[k2] + _expected_third_ship(e2c, e2v, w, fl)
                        if not have2 or v2 > best2:
                            best2 = v2; have2 = True
                    leaf1 = _leafv_ship(c1, v1, w, fl)     # b1 has viruses here
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                # eh add-on applies to BOTH m2==0 and m2>0 (golden decide_d3:265 is
                # at the 'if not second' indent, inside the virus!=0 branch)
                val += w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
            if not have or val > best_val:                 # strictly-greater keep-first
                best_val = val; best_act = var * 8 + col; have = True
    return best_act


# ---- deploy constants for the eh path (build_copro_d3.build_image) ----------------
_W_EXCAV_SHIP = 24
_W_HANG_SHIP = 40          # golden module default; NOT R4-refined in the python bridge


def _decode_nes(nes):
    """NES tile bytes -> (col int8[128], vir int8[128]). $FF empty, hi-nibble $D virus,
    low-nibble color 0..2 -> faithful 1-based col (0=empty). Row-major 8x16 (idx=r*8+c)."""
    col = np.zeros(NCELL, dtype=np.int8); vir = np.zeros(NCELL, dtype=np.int8)
    for i in range(NCELL):
        v = int(nes[i]) & 0xFF
        if v == 0xFF:
            continue
        col[i] = (v & 0x0F) + 1
        if (v & 0xF0) == 0xD0:
            vir[i] = 1
    return col, vir


def decide_ship_d3(board128, pA, pB, nA, nB, w_vrdy, topk2=8):
    """Ship-faithful depth-3 decision, bit-exact to nes_d3_golden.decide_d3 + leaf_r47
    at the build_copro_d3 DEPLOY config (topk1=full, topk2=8, THIRD 4-pill //4,
    DISC_SHIFT=1, EXCAV_HANG_PLY1=True with W_EXCAV=24/W_HANG=40 base g_hang, imm
    180/10, WIN=30000, seed=0). Returns (col 0..7, orient4 0..3) in _placements4
    convention, or None if no legal placement.

    board128 : NES tile bytes (len 128), $FF empty / hi-nibble $D virus / low-nibble color.
    pA,pB,nA,nB : CURRENT + NEXT pill colors as NES low-nibble values 0..2 (the same
                  convention decide_d3 takes -- i.e. faithful color minus 1).
    w_vrdy   : 24 (shipped r47b4 cart) or 12 (r47b5_c11_pad in flight). Only this leaf
               coefficient differs between the two arms; all other R47 refinements fixed.
    """
    col, vir = _decode_nes(board128)
    w = weights_rtl_r47(); fl = flags_r47()
    w[R_VRDY] = float(w_vrdy)
    a = _choose_d3_ship_eh(col, vir, int(pA) + 1, int(pB) + 1, int(nA) + 1, int(nB) + 1,
                           int(topk2), int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
    if a < 0:
        return None
    var = a // 8
    return int(a % 8), int(_VAR_OF_O4[var])   # (col, o4); _VAR_OF_O4 is self-inverse


_RTL_IDX = {"vrdy": R_VRDY, "buried": R_BURIED, "rdyext": R_RDYEXT,
            "setup": R_SETUP, "matched": R_MATCHED}


def decide_ship_d3_wdict(board128, pA, pB, nA, nB, rtl, topk2=8):
    """Same ship-faithful depth-3 decision as decide_ship_d3, but overrides ALL FIVE
    tunable S_DONE2 leaf coefficients {vrdy,buried,rdyext,setup,matched} from the `rtl`
    dict (the coef-opt2 grid space), not just w_vrdy. Every other refinement, the eh
    ply-1 add-on, and the build_copro_d3 DEPLOY config are held at r47 -- identical code
    path to decide_ship_d3 -- so this IS the shipped depth-3 search with a swapped weight
    vector. Returns (col 0..7, orient4 0..3) in _placements4 convention
    (== nes_d3_golden.decide_d3), or None. `rtl` values are RTL integer coefficients;
    pill colors are NES low-nibble 0..2 (faithful minus 1). matched is applied as
    w[R_MATCHED]*matched_count, i.e. combine_w's w['matched']*(matched60//60)."""
    col, vir = _decode_nes(board128)
    w = weights_rtl_r47(); fl = flags_r47()
    for t, idx in _RTL_IDX.items():
        w[idx] = float(rtl[t])
    a = _choose_d3_ship_eh(col, vir, int(pA) + 1, int(pB) + 1, int(nA) + 1, int(nB) + 1,
                           int(topk2), int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
    if a < 0:
        return None
    return int(a % 8), int(_VAR_OF_O4[a // 8])   # (col, o4); _VAR_OF_O4 self-inverse


def warmup_ship_eh(topk2=8):
    bc = np.zeros(NCELL, dtype=np.int8); bv = np.zeros(NCELL, dtype=np.int8)
    w = weights_rtl_r47(); fl = flags_r47()
    _g_excav_ship(bc, bv); _g_hang_ship(bc, bv)
    _choose_d3_ship_eh(bc, bv, 1, 2, 1, 2, topk2,
                       int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)


class FastShipD3DeciderEH:
    """The ACTUAL deployed depth-3 brain: _choose_d3_ship + the ply-1 eh_terms root
    add-on (EXCAV_HANG_PLY1=True, W_EXCAV=24, base-g_hang*40). Board-in decider for
    full-game runs -- the tempo coefficient search (task #46) evaluates candidates
    with THIS, so the search sees the real ship brain (eh held fixed across candidates,
    only the leaf weight vector `weights` varies). Mirrors FastShipD3Decider but eh-ON."""
    def __init__(self, weights, flags, topk2=8, w_excav=_W_EXCAV_SHIP, w_hang=_W_HANG_SHIP):
        self.w = np.asarray(weights, dtype=np.float64)
        self.fl = np.asarray(flags, dtype=np.int32)
        self.topk2 = int(topk2)
        self.w_excav = int(w_excav)
        self.w_hang = int(w_hang)

    def choose(self, board, cur, nxt):
        col, vir = board_flat(board)
        a = _choose_d3_ship_eh(col, vir, cur.a, cur.b, nxt.a, nxt.b, self.topk2,
                               self.w_excav, self.w_hang, self.w, self.fl)
        return None if a < 0 else int(a)


# ==================================================================================
# INCREMENTAL DELTA EVALUATION -- a python/numba mirror of LeafEval.sv's CMD-6 BASE /
# CMD-7 DELTA engine (the same design the cart measures at 6.1x/leaf).
#
# IDEA: a leaf eval is a sum of PER-COLUMN, PER-VIRUS and PER-WINDOW contributions.
# A pill placement touches exactly 2 cells, so on a NON-CLEARING placement only
#   - the 1-2 placed COLUMNS       (maxh/holes/toprisk/spawn/buried/matched)
#   - the viruses in the placed cells' ROWS and COLUMNS  (rdy_ext/vrdy/cross)
#   - the 3-in-a-row windows containing a placed cell    (setup)
#   - the viruses in the placed cells' rows/cols         (pollution, closed form)
# can change.  So: scan the PARENT once (_base_scan), then per child subtract the
# stale local contribution and add the new one.  Everything else is carried over.
#
# THE CLEARING CASE IS NOT DELTA'D.  A clear triggers gravity, which can move cells in
# every column, so the closed form does not hold.  LeafEval.sv handles this by raising
# `dv_fallback` in S_APPLY (`if (anyclear ...) dv_fallback <= 1`) and having the host
# re-issue a full NODE; we mirror that exactly -- clearing placements fall through to
# `_expand_core` + `_eval_rtl`.  That keeps the result bit-exact by construction on the
# hard case and delta-fast on the ~85% of placements that clear nothing.
#
# BIT-EXACTNESS: the delta produces the same TERM VECTOR as a full rescan (verified
# term-by-term, not just on the combined score), and the combine is the identical
# signed-16 wrap expression as `_eval_rtl`.  See delta_fuzz.py.
# ==================================================================================
T_MAXH = 0
T_HOLES = 1
T_TOPRISK = 2
T_SPAWN = 3
T_SETUP = 4
T_MATCHED = 5
T_BURIED = 6
T_RDY = 7
T_VRDY = 8
T_CROSS = 9
T_POLL = 10
T_NVIR = 11        # virus count (LeafEval's base_anyvir, kept as a count)
NT = 12

# The base vector carries more than LeafEval's base_* scalars: it MEMOISES the parent's
# per-column and per-virus contributions.  That is the difference between "rescan the
# placed column on the parent to get the old value" (what the RTL's S_DUNPL phase does,
# because a 128x3 table costs BRAM it does not have) and "look the old value up" -- it
# deletes the entire OLD phase of the delta, which measured as its dominant cost.
CT_H = 0; CT_HOLES = 1; CT_TR = 2; CT_SP = 3; CT_BUR = 4; CT_MAT = 5
NCT = 6
# Per virus we memoise the RAW row/column measurements rather than the 3 combined
# contributions: a placement touches a virus's ROW xor its COLUMN and never both (the
# line intersections are exactly the two placed cells, which are not viruses), so the
# untouched axis can be read back instead of re-walked.
VT_RUNH = 0; VT_HQ = 1; VT_RUNV = 2; VT_VQ = 3
NVT = 4
BASE_COL = NT                      # + c*NCT + k      per-column terms
BASE_VIR = NT + COLS * NCT         # + idx*NVT + k    per-virus terms (valid at virus cells)
NBASE = NT + COLS * NCT + NCELL * NVT


@njit(cache=True, fastmath=False, inline='always')
def _colwalk_terms(col, vir, c, color_aware, nearest2, matched_on):
    """ONE column of _eval_rtl's column walk -- the per-column decomposition of
    (height, holes, toprisk, spawn, buried, matched).  height = 16 - top_occ_row,
    0 for an empty column (LeafEval's colh[]).  Line-for-line the body of the
    `for c in range(COLS)` loop in _eval_rtl."""
    seen = False; fillcnt = 0; curcol = 0; curlen = 0; vseen = 0
    h = 0; holes = 0; toprisk = 0; spawn = 0; buried = 0; matched = 0
    for r in range(ROWS):
        idx = r * COLS + c
        cc = col[idx]
        if cc != 0:
            if not seen:
                seen = True
                h = ROWS - r
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
    return (h, holes, toprisk, spawn, buried, matched)


@njit(cache=True, fastmath=False, inline='always')
def _vterms_h(col, vr, vc):
    """ONE virus's ROW measurements: (run_h, hq).  Depends only on row vr."""
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
    hq = run_h * run_h if (span_hi - span_lo + 1) >= 4 else 0
    return (run_h, hq)


@njit(cache=True, fastmath=False, inline='always')
def _vterms_v(col, vr, vc):
    """ONE virus's COLUMN measurements: (run_v, vq).  Depends only on column vc."""
    vcol = col[vr * COLS + vc]
    run_v = 1; p = vr
    while p != 0 and col[(p - 1) * COLS + vc] == vcol:
        run_v += 1; p -= 1
    vspan_lo = p
    while vspan_lo != 0 and ((col[(vspan_lo - 1) * COLS + vc] == 0) or col[(vspan_lo - 1) * COLS + vc] == vcol):
        vspan_lo -= 1
    p = vr
    while p != 15 and col[(p + 1) * COLS + vc] == vcol:
        run_v += 1; p += 1
    vspan_hi = p
    while vspan_hi != 15 and ((col[(vspan_hi + 1) * COLS + vc] == 0) or col[(vspan_hi + 1) * COLS + vc] == vcol):
        vspan_hi += 1
    vq = run_v * run_v if (vspan_hi - vspan_lo + 1) >= 4 else 0
    return (run_v, vq)


@njit(cache=True, fastmath=False, inline='always')
def _vcombine(run_h, hq, run_v, vq):
    """(rdy_ext, vrdy, cross) contributions from one virus's raw measurements --
    the tail of _eval_rtl's per-virus body."""
    mx = hq if hq > vq else vq
    cr = 0
    if run_h >= 2 and run_v >= 2:
        cr = hq if hq < vq else vq
    return (mx, run_v * run_v, cr)


@njit(cache=True, fastmath=False)
def _vterms(col, vr, vc):
    """ONE virus's (rdy_ext, vrdy, cross) contributions.  Body of _eval_rtl's per-virus
    loop minus pollution (which needs `vir`)."""
    run_h, hq = _vterms_h(col, vr, vc)
    run_v, vq = _vterms_v(col, vr, vc)
    return _vcombine(run_h, hq, run_v, vq)


@njit(cache=True, fastmath=False)
def _vpoll(col, vir, vr, vc):
    """ONE virus's pollution contribution (its row then its column)."""
    vcol = col[vr * COLS + vc]
    pol = 0
    for pc in range(COLS):
        if pc != vc and col[vr * COLS + pc] != 0 and not vir[vr * COLS + pc] and col[vr * COLS + pc] != vcol:
            pol += 1
    for pr in range(ROWS):
        if pr != vr and col[pr * COLS + vc] != 0 and not vir[pr * COLS + vc] and col[pr * COLS + vc] != vcol:
            pol += 1
    return pol


@njit(cache=True, fastmath=False, inline='always')
def _seth_win(col, vir, wr, wc):
    """ONE horizontal setup window (row wr, cols wc..wc+2). 0 or 1."""
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
            return 1
    return 0


@njit(cache=True, fastmath=False, inline='always')
def _setv_win(col, vir, wr, wc):
    """ONE vertical setup window (col wc, rows wr..wr+2). 0 or 1."""
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
            return 1
    return 0


@njit(cache=True, fastmath=False)
def _base_scan(col, vir, fl, base):
    """CMD-6 BASE: full scan of the PARENT board -> term totals in base[0:NT], PLUS the
    per-column and per-virus decomposition the delta subtracts.  Written monolithically
    (not via the helpers above) so it costs the same as _eval_rtl itself -- the base is
    paid once per parent and amortised over its children, so its constant matters.

    The totals are the identical accumulators as _eval_rtl; only the bookkeeping is new.
    Enforced by the fuzz: _combine_terms(_base_scan(b), w) == _eval_rtl(b, w)."""
    color_aware = fl[FL_COLOR_AWARE]
    nearest2 = fl[FL_NEAREST2]
    matched_on = fl[FL_MATCHED]
    maxh = 0; holes = 0; toprisk = 0; spawn = 0
    buried = 0; matched = 0
    # ---- column walk: shape + buried + matched (per column, memoised) ----
    for c in range(COLS):
        seen = False; fillcnt = 0; curcol = 0; curlen = 0; vseen = 0
        c_h = 0; c_holes = 0; c_tr = 0; c_sp = 0; c_bur = 0; c_mat = 0
        for r in range(ROWS):
            idx = r * COLS + c
            cc = col[idx]
            if cc != 0:
                if not seen:
                    seen = True
                    c_h = ROWS - r
                if vir[idx]:
                    same = (curcol == cc)
                    if matched_on and same:
                        c_mat += 1
                    if (nearest2 == 0) or vseen < 2:
                        exempt = curlen if (color_aware and same) else 0
                        c_bur += fillcnt - exempt
                    vseen += 1
                    curcol = 0; curlen = 0
                else:
                    if curcol == cc:
                        curlen += 1
                    else:
                        curcol = cc; curlen = 1
                fillcnt += 1
                if r < 3:
                    c_tr += 1
                if r < 4 and (c == 3 or c == 4):
                    c_sp += 1
            else:
                if seen:
                    c_holes += 1
                curcol = 0; curlen = 0
        b = BASE_COL + c * NCT
        base[b + CT_H] = c_h; base[b + CT_HOLES] = c_holes; base[b + CT_TR] = c_tr
        base[b + CT_SP] = c_sp; base[b + CT_BUR] = c_bur; base[b + CT_MAT] = c_mat
        if c_h > maxh:
            maxh = c_h
        holes += c_holes; toprisk += c_tr; spawn += c_sp; buried += c_bur; matched += c_mat
    # ---- per-virus: rdy_ext, vrdy, cross, pollution (per virus, memoised) ----
    rdy = 0; vrdy = 0; cross = 0; pollution = 0; nvir = 0
    for vr in range(ROWS):
        for vc in range(COLS):
            vidx = vr * COLS + vc
            if not vir[vidx]:
                continue
            nvir += 1
            run_h, hq = _vterms_h(col, vr, vc)
            run_v, vq = _vterms_v(col, vr, vc)
            mx, vsq, cr = _vcombine(run_h, hq, run_v, vq)
            rdy += mx; vrdy += vsq; cross += cr
            vb = BASE_VIR + vidx * NVT
            base[vb + VT_RUNH] = run_h; base[vb + VT_HQ] = hq
            base[vb + VT_RUNV] = run_v; base[vb + VT_VQ] = vq
            vcol = col[vidx]
            for pc in range(COLS):
                if pc != vc and col[vr * COLS + pc] != 0 and not vir[vr * COLS + pc] and col[vr * COLS + pc] != vcol:
                    pollution += 1
            for pr in range(ROWS):
                if pr != vr and col[pr * COLS + vc] != 0 and not vir[pr * COLS + vc] and col[pr * COLS + vc] != vcol:
                    pollution += 1
    # ---- setup (written out, not via _seth_win/_setv_win: 208 windows per scan, and
    # the base's constant is exactly what the amortisation over children is charged) ----
    setup = 0
    for wr in range(ROWS):
        for wc in range(6):
            s0 = col[wr * COLS + wc]
            if s0 != 0 and col[wr * COLS + wc + 1] == s0 and col[wr * COLS + wc + 2] == s0:
                t = ((vir[wr * COLS + wc] and col[wr * COLS + wc] == s0)
                     or (vir[wr * COLS + wc + 1] and col[wr * COLS + wc + 1] == s0)
                     or (vir[wr * COLS + wc + 2] and col[wr * COLS + wc + 2] == s0))
                if not t and wc != 0 and vir[wr * COLS + wc - 1] and col[wr * COLS + wc - 1] == s0:
                    t = True
                if not t and wc < 5 and vir[wr * COLS + wc + 3] and col[wr * COLS + wc + 3] == s0:
                    t = True
                if t:
                    setup += 1
    for wc in range(COLS):
        for wr in range(14):
            s0 = col[wr * COLS + wc]
            if s0 != 0 and col[(wr + 1) * COLS + wc] == s0 and col[(wr + 2) * COLS + wc] == s0:
                t = ((vir[wr * COLS + wc] and col[wr * COLS + wc] == s0)
                     or (vir[(wr + 1) * COLS + wc] and col[(wr + 1) * COLS + wc] == s0)
                     or (vir[(wr + 2) * COLS + wc] and col[(wr + 2) * COLS + wc] == s0))
                if not t and wr != 0 and vir[(wr - 1) * COLS + wc] and col[(wr - 1) * COLS + wc] == s0:
                    t = True
                if not t and wr < 13 and vir[(wr + 3) * COLS + wc] and col[(wr + 3) * COLS + wc] == s0:
                    t = True
                if t:
                    setup += 1
    base[T_MAXH] = maxh; base[T_HOLES] = holes; base[T_TOPRISK] = toprisk
    base[T_SPAWN] = spawn; base[T_SETUP] = setup; base[T_MATCHED] = matched
    base[T_BURIED] = buried; base[T_RDY] = rdy; base[T_VRDY] = vrdy
    base[T_CROSS] = cross; base[T_POLL] = pollution; base[T_NVIR] = nvir


@njit(int64(int64[:], float64[:]), cache=True, fastmath=False)
def _combine_terms(t, w):
    """S_DONE2 combine from a term vector -- the identical expression (and identical
    signed-16 wrap) as the tail of _eval_rtl."""
    s = (int64(w[R_BIAS])
         - int64(w[R_MAXH]) * t[T_MAXH]
         - int64(w[R_HOLES]) * t[T_HOLES]
         - int64(w[R_TOPRISK]) * t[T_TOPRISK]
         - int64(w[R_SPAWN]) * t[T_SPAWN]
         + int64(w[R_SETUP]) * t[T_SETUP]
         + int64(w[R_MATCHED]) * t[T_MATCHED]
         - int64(w[R_BURIED]) * t[T_BURIED]
         + int64(w[R_RDYEXT]) * t[T_RDY]
         + int64(w[R_VRDY]) * t[T_VRDY]
         + int64(w[R_CROSS]) * t[T_CROSS]
         - int64(w[R_POLL]) * t[T_POLL])
    s = s & 0xFFFF
    if s >= 0x8000:
        s -= 0x10000
    return s


@njit(cache=True, fastmath=False)
def _rescore_lines(col, vir, r0, c0, r1, c1):
    """(rdy, vrdy, cross) summed over every virus in the placed cells' rows and columns
    -- LeafEval's S_DRV sweep with the same dedup.  The line intersections are exactly
    the two placed cells, which are never viruses (on the child they hold the pill; on
    the parent they are empty), so no virus is double-counted.  Kept for the fuzz's
    independent cross-check; the hot path uses _rescore_delta."""
    rdy = 0; vrdy = 0; cross = 0
    for pc in range(COLS):
        if vir[r0 * COLS + pc]:
            mx, vsq, cr = _vterms(col, r0, pc)
            rdy += mx; vrdy += vsq; cross += cr
    if r1 != r0:
        for pc in range(COLS):
            if vir[r1 * COLS + pc]:
                mx, vsq, cr = _vterms(col, r1, pc)
                rdy += mx; vrdy += vsq; cross += cr
    for pr in range(ROWS):
        if vir[pr * COLS + c0]:
            mx, vsq, cr = _vterms(col, pr, c0)
            rdy += mx; vrdy += vsq; cross += cr
    if c1 != c0:
        for pr in range(ROWS):
            if vir[pr * COLS + c1]:
                mx, vsq, cr = _vterms(col, pr, c1)
                rdy += mx; vrdy += vsq; cross += cr
    return (rdy, vrdy, cross)


@njit(cache=True, fastmath=False, inline='always')
def _rescore_row(col, vir, base, vr):
    """Delta over the viruses in a PLACED ROW.  Their columns hold no placed cell, so
    (run_v, vq) are re-read from the memo and only the row walk is redone."""
    drdy = 0; dvrdy = 0; dcross = 0
    for pc in range(COLS):
        vidx = vr * COLS + pc
        if vir[vidx]:
            vb = BASE_VIR + vidx * NVT
            run_v = base[vb + VT_RUNV]; vq = base[vb + VT_VQ]
            run_h, hq = _vterms_h(col, vr, pc)
            mx, vsq, cr = _vcombine(run_h, hq, run_v, vq)
            omx, ovsq, ocr = _vcombine(base[vb + VT_RUNH], base[vb + VT_HQ], run_v, vq)
            drdy += mx - omx; dvrdy += vsq - ovsq; dcross += cr - ocr
    return (drdy, dvrdy, dcross)


@njit(cache=True, fastmath=False, inline='always')
def _rescore_col(col, vir, base, vc):
    """Delta over the viruses in a PLACED COLUMN.  Their rows hold no placed cell, so
    (run_h, hq) are re-read from the memo and only the column walk is redone."""
    drdy = 0; dvrdy = 0; dcross = 0
    for pr in range(ROWS):
        vidx = pr * COLS + vc
        if vir[vidx]:
            vb = BASE_VIR + vidx * NVT
            run_h = base[vb + VT_RUNH]; hq = base[vb + VT_HQ]
            run_v, vq = _vterms_v(col, pr, vc)
            mx, vsq, cr = _vcombine(run_h, hq, run_v, vq)
            omx, ovsq, ocr = _vcombine(run_h, hq, base[vb + VT_RUNV], base[vb + VT_VQ])
            drdy += mx - omx; dvrdy += vsq - ovsq; dcross += cr - ocr
    return (drdy, dvrdy, dcross)


@njit(cache=True, fastmath=False)
def _rescore_delta(col, vir, base, r0, c0, r1, c1):
    """(d_rdy, d_vrdy, d_cross) over the S_DRV lines: score each affected virus on the
    CHILD and subtract its memoised PARENT value.  Viruses cannot appear or vanish on a
    non-clearing placement, so the affected set is the same on both boards, and the
    row/column split above means each virus costs ONE axis walk, not two boards x two
    axes as LeafEval's old/new phases do."""
    drdy, dvrdy, dcross = _rescore_row(col, vir, base, r0)
    if r1 != r0:
        a, b, c = _rescore_row(col, vir, base, r1)
        drdy += a; dvrdy += b; dcross += c
    a, b, c = _rescore_col(col, vir, base, c0)
    drdy += a; dvrdy += b; dcross += c
    if c1 != c0:
        a, b, c = _rescore_col(col, vir, base, c1)
        drdy += a; dvrdy += b; dcross += c
    return (drdy, dvrdy, dcross)


@njit(cache=True, fastmath=False)
def _setup_local(col, vir, r0, c0, r1, c1):
    """Setup windows that contain a placed cell -- LeafEval's S_DSETH/S_DSETV cursors.
    A window's value also reads the two EXTENSION cells (wc-1 / wc+3), but that test
    requires a VIRUS there and a placed cell is never a virus (and was empty before),
    so windows whose 3-run misses both placed cells cannot change."""
    rlo = r0 if r0 < r1 else r1
    rhi = r1 if r1 > r0 else r0
    clo = c0 if c0 < c1 else c1
    chi = c1 if c1 > c0 else c0
    s = 0
    ws = clo - 2
    if ws < 0:
        ws = 0
    we = chi if chi < 5 else 5
    for wc in range(ws, we + 1):
        s += _seth_win(col, vir, r0, wc)
    if r1 != r0:
        for wc in range(ws, we + 1):
            s += _seth_win(col, vir, r1, wc)
    vs = rlo - 2
    if vs < 0:
        vs = 0
    ve = rhi if rhi < 13 else 13
    for wr in range(vs, ve + 1):
        s += _setv_win(col, vir, wr, c0)
    if c1 != c0:
        for wr in range(vs, ve + 1):
            s += _setv_win(col, vir, wr, c1)
    return s


@njit(cache=True, fastmath=False)
def _setup_local_child(col, vir, r0, c0, r1, c1):
    """_setup_local specialised to the CHILD of a non-clearing placement.

    VERTICAL WINDOWS ARE PRUNED to wr in [min(r0,r1), max(r0,r1)].  A drop always lands
    on top of its column(s) -- `_resting` picks r = top_occ - 1 -- so every cell STRICTLY
    ABOVE r0 in the placed columns is empty.  A window at wr < r0 therefore spans an
    empty cell in that column and fails the `c0 != 0 and col[+1]==c0 and col[+2]==c0`
    run test.  The horizontal windows keep the full range: a placed ROW can have
    occupied cells either side from other columns' piles.
    (Cross-checked against the unpruned _setup_local over the whole fuzz corpus.)"""
    clo = c0 if c0 < c1 else c1
    chi = c1 if c1 > c0 else c0
    s = 0
    ws = clo - 2
    if ws < 0:
        ws = 0
    we = chi if chi < 5 else 5
    for wc in range(ws, we + 1):
        s += _seth_win(col, vir, r0, wc)
    if r1 != r0:
        for wc in range(ws, we + 1):
            s += _seth_win(col, vir, r1, wc)
    rlo = r0 if r0 < r1 else r1
    rhi = r1 if r1 > r0 else r0
    ve = rhi if rhi < 13 else 13
    for wr in range(rlo, ve + 1):
        s += _setv_win(col, vir, wr, c0)
    if c1 != c0:
        for wr in range(rlo, ve + 1):
            s += _setv_win(col, vir, wr, c1)
    return s


@njit(cache=True, fastmath=False)
def _delta_terms(col, vir, base, r0, c0, r1, c1, fl, out):
    """CMD-7 DELTA combine: `col`/`vir` hold the CHILD board -- the pill placed at
    (r0,c0)/(r1,c1) with NOTHING cleared.  Fills `out` with the child's full term
    vector.  READ-ONLY in `col`/`vir`.

    Every "old local" value is a lookup into the base's memoised per-column / per-virus
    tables, so unlike LeafEval's S_DUNPL this never re-walks the parent.  The one term
    with no old value to subtract is `setup`, and it does not need one:

      SETUP'S OLD PHASE IS IDENTICALLY ZERO.  The windows the delta visits are exactly
      those whose 3-run contains a placed cell (that is the definition of the S_DSETH /
      S_DSETV cursor ranges).  On the PARENT every placed cell is EMPTY, so each such
      window has col==0 somewhere in its 3-run and fails the `c0 != 0 and col[+1]==c0
      and col[+2]==c0` test.  Hence od_set == 0 for every window in range, always.
      (Asserted over the whole fuzz corpus, not assumed -- see delta_fuzz.py's
      "old-phase setup nonzero" counter.)"""
    color_aware = fl[FL_COLOR_AWARE]
    nearest2 = fl[FL_NEAREST2]
    matched_on = fl[FL_MATCHED]
    i0 = r0 * COLS + c0
    i1 = r1 * COLS + c1
    pa = col[i0]
    pb = col[i1]
    two_cols = (c1 != c0)

    # ---- pollution delta, closed form (S_DNEW/S_DPOL): each placed non-virus cell
    # pollutes every differently-coloured virus in its row and in its column.
    dpol = 0
    for pc in range(COLS):
        j = r0 * COLS + pc
        if vir[j] and col[j] != pa:
            dpol += 1
    for pr in range(ROWS):
        j = pr * COLS + c0
        if vir[j] and col[j] != pa:
            dpol += 1
    for pc in range(COLS):
        j = r1 * COLS + pc
        if vir[j] and col[j] != pb:
            dpol += 1
    for pr in range(ROWS):
        j = pr * COLS + c1
        if vir[j] and col[j] != pb:
            dpol += 1

    # ---- placed column(s): rescan on the child, subtract the memoised parent column --
    nh0, nho0, ntr0, nsp0, nbur0, nmat0 = _colwalk_terms(col, vir, c0, color_aware, nearest2, matched_on)
    b0 = BASE_COL + c0 * NCT
    dholes = nho0 - base[b0 + CT_HOLES]
    dtr = ntr0 - base[b0 + CT_TR]
    dsp = nsp0 - base[b0 + CT_SP]
    dbur = nbur0 - base[b0 + CT_BUR]
    dmat = nmat0 - base[b0 + CT_MAT]
    mh = base[T_MAXH]
    if nh0 > mh:
        mh = nh0
    if two_cols:
        nh1, nho1, ntr1, nsp1, nbur1, nmat1 = _colwalk_terms(col, vir, c1, color_aware, nearest2, matched_on)
        b1 = BASE_COL + c1 * NCT
        dholes += nho1 - base[b1 + CT_HOLES]
        dtr += ntr1 - base[b1 + CT_TR]
        dsp += nsp1 - base[b1 + CT_SP]
        dbur += nbur1 - base[b1 + CT_BUR]
        dmat += nmat1 - base[b1 + CT_MAT]
        if nh1 > mh:
            mh = nh1

    drdy, dvrdy, dcross = _rescore_delta(col, vir, base, r0, c0, r1, c1)
    nset = _setup_local_child(col, vir, r0, c0, r1, c1)   # old phase == 0, see docstring

    out[T_MAXH] = mh
    out[T_HOLES] = base[T_HOLES] + dholes
    out[T_TOPRISK] = base[T_TOPRISK] + dtr
    out[T_SPAWN] = base[T_SPAWN] + dsp
    out[T_SETUP] = base[T_SETUP] + nset
    out[T_MATCHED] = base[T_MATCHED] + dmat
    out[T_BURIED] = base[T_BURIED] + dbur
    out[T_RDY] = base[T_RDY] + drdy
    out[T_VRDY] = base[T_VRDY] + dvrdy
    out[T_CROSS] = base[T_CROSS] + dcross
    out[T_POLL] = base[T_POLL] + dpol
    out[T_NVIR] = base[T_NVIR]


@njit(cache=True, fastmath=False)
def _any_clear_lines(col, r0, c0, r1, c1):
    """Does the placement complete a run >= 4 on any of its 4 targeted lines?  The
    existence test only -- cheaper than _targeted_resolve's 128-cell mask + sweep, and
    it is all the delta path needs to decide fall back vs. delta."""
    for k in range(2):
        if k == 1 and r1 == r0:
            continue
        rr = r0 if k == 0 else r1
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
                return True
            i = j
    for k in range(2):
        if k == 1 and c1 == c0:
            continue
        cc = c0 if k == 0 else c1
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
                return True
            i = j
    return False


@njit(cache=True, fastmath=False)
def _expand_leaf_delta(pcol, pvir, base, variant, column, pa, pb, ccol, cvir, w, fl, terms):
    """_expand_core + ship leaf value in one pass, delta'd when nothing clears.
    Returns (ok, nv, cells, leafval); ccol/cvir always hold the resolved child board
    (this is the ply-1/ply-2 entry point, which needs the board to recurse).
    `base` must be _base_scan of (pcol,pvir)."""
    ok, r0, c0, r1, c1 = _resting(pcol, variant, column)
    if ok == 0:
        return (0, 0, 0, int64(0))
    for i in range(NCELL):
        ccol[i] = pcol[i]
        cvir[i] = pvir[i]
    if variant == 0 or variant == 2:
        col0 = pa; col1 = pb
    else:
        col0 = pb; col1 = pa
    ccol[r0 * COLS + c0] = col0
    ccol[r1 * COLS + c1] = col1
    cvir[r0 * COLS + c0] = 0
    cvir[r1 * COLS + c1] = 0
    if _any_clear_lines(ccol, r0, c0, r1, c1):
        cells, nv = _targeted_resolve(ccol, cvir, r0, c0, r1, c1)
        return (1, nv, cells, _leafv_ship(ccol, cvir, w, fl))
    if base[T_NVIR] == 0:
        return (1, 0, 0, int64(_WIN_SHIP))
    _delta_terms(ccol, cvir, base, r0, c0, r1, c1, fl, terms)
    return (1, 0, 0, _combine_terms(terms, w))


@njit(cache=True, fastmath=False)
def _leaf_delta_noboard(pcol, pvir, base, variant, column, pa, pb, w, fl, tc, tv, terms):
    """Leaf VALUE only, no child board -- the ply-3 entry point.  Skips the 128-cell
    clone entirely on the non-clearing path by placing into `pcol` in place and
    restoring it (pcol is byte-identical on exit, verified in the fuzz).  tc/tv are
    scratch used only on the clearing fallback.  Returns (ok, nv, cells, leafval)."""
    ok, r0, c0, r1, c1 = _resting(pcol, variant, column)
    if ok == 0:
        return (0, 0, 0, int64(0))
    if variant == 0 or variant == 2:
        col0 = pa; col1 = pb
    else:
        col0 = pb; col1 = pa
    i0 = r0 * COLS + c0
    i1 = r1 * COLS + c1
    pcol[i0] = col0
    pcol[i1] = col1
    if _any_clear_lines(pcol, r0, c0, r1, c1):
        pcol[i0] = 0
        pcol[i1] = 0
        _ok2, nv, cells = _expand_core(pcol, pvir, variant, column, pa, pb, tc, tv)
        return (1, nv, cells, _leafv_ship(tc, tv, w, fl))
    if base[T_NVIR] == 0:
        pcol[i0] = 0
        pcol[i1] = 0
        return (1, 0, 0, int64(_WIN_SHIP))
    _delta_terms(pcol, pvir, base, r0, c0, r1, c1, fl, terms)
    val = _combine_terms(terms, w)
    pcol[i0] = 0
    pcol[i1] = 0
    return (1, 0, 0, val)


# ---------------- delta-accelerated ship-faithful depth-3 (identical decisions) -----
# Structurally line-for-line _choose_d3_ship_eh / _expected_third_ship; the ONLY change
# is HOW each leaf value is obtained (base+delta vs full rescan).  Enumeration order,
# tie-breaks, the topk2 stable sort, the DISC_SHIFT blend and the eh add-on are byte
# identical, so the chosen action must match -- asserted in the fuzz.
@njit(int64(int8[:], int8[:], float64[:], int32[:], int64[:], int64[:], int8[:], int8[:]),
      cache=True, fastmath=False)
def _expected_third_ship_delta(b2c, b2v, w, fl, base3, terms, tc, tv):
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
                ok, nv, cells, lv = _leaf_delta_noboard(b2c, b2v, base3, var, cl, x, y,
                                                        w, fl, tc, tv, terms)
                if ok == 0:
                    continue
                vv = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells \
                     + (int64(w[R_VBONUS]) if nv >= 2 else int64(0)) + lv
                if not have3 or vv > best3:
                    best3 = vv; have3 = True
        tot += best3 if have3 else _leafv_ship(b2c, b2v, w, fl)
    return tot // int64(4)


@njit(int64(int8[:], int8[:], int64, int64, int64, int64, int64, int64, int64,
            float64[:], int32[:]), cache=True, fastmath=False)
def _choose_d3_ship_eh_delta(pcol, pvir, ca, cb, na, nb, topk2, w_excav, w_hang, w, fl):
    """Delta-accelerated mirror of _choose_d3_ship_eh.  Must return the SAME action."""
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8)
    b2col = np.empty((32, NCELL), dtype=int8); b2vir = np.empty((32, NCELL), dtype=int8)
    keys2 = np.empty(32, dtype=float64); imms2 = np.empty(32, dtype=int64)
    order2 = np.empty(32, dtype=int32)
    s2c = np.empty(NCELL, dtype=int8); s2v = np.empty(NCELL, dtype=int8)
    e2c = np.empty(NCELL, dtype=int8); e2v = np.empty(NCELL, dtype=int8)
    tc = np.empty(NCELL, dtype=int8); tv = np.empty(NCELL, dtype=int8)
    base1 = np.empty(NBASE, dtype=int64); base2 = np.empty(NBASE, dtype=int64)
    base3 = np.empty(NBASE, dtype=int64); terms = np.empty(NT, dtype=int64)
    _base_scan(pcol, pvir, fl, base1)
    best_val = int64(0); best_act = -1; have = False
    for o4 in range(4):
        var = _VAR_OF_O4[o4]
        for cl in range(8):
            ok, nv, cells, leaf1 = _expand_leaf_delta(pcol, pvir, base1, var, cl, ca, cb,
                                                      c1, v1, w, fl, terms)
            if ok == 0:
                continue
            imm1 = int64(w[R_WVIR]) * nv + int64(w[R_WCELLS]) * cells + (int64(w[R_VBONUS]) if nv >= 2 else int64(0))
            if _virus_count(v1) == 0:
                val = imm1 + int64(_WIN_SHIP)
            else:
                _base_scan(c1, v1, fl, base2)
                m2 = 0
                for o42 in range(4):
                    var2 = _VAR_OF_O4[o42]
                    for cl2 in range(8):
                        ok2, nv2, cells2, lv2 = _expand_leaf_delta(c1, v1, base2, var2, cl2,
                                                                   na, nb, s2c, s2v, w, fl, terms)
                        if ok2 == 0:
                            continue
                        imm2 = int64(w[R_WVIR]) * nv2 + int64(w[R_WCELLS]) * cells2 + (int64(w[R_VBONUS]) if nv2 >= 2 else int64(0))
                        keys2[m2] = float64(imm2 + lv2)
                        imms2[m2] = imm2
                        for i in range(NCELL):
                            b2col[m2, i] = s2c[i]; b2vir[m2, i] = s2v[i]
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
                            e2c[i] = b2col[k2, i]; e2v[i] = b2vir[k2, i]
                        if _virus_count(e2v) == 0:
                            v2 = imms2[k2] + int64(_WIN_SHIP)
                        else:
                            v2 = imms2[k2] + _expected_third_ship_delta(e2c, e2v, w, fl, base3, terms, tc, tv)
                        if not have2 or v2 > best2:
                            best2 = v2; have2 = True
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                val += w_excav * _g_excav_ship(c1, v1) + w_hang * _g_hang_ship(c1, v1)
            if not have or val > best_val:
                best_val = val; best_act = var * 8 + cl; have = True
    return best_act


class FastShipD3DeciderEHDelta:
    """FastShipD3DeciderEH with the incremental leaf.  Same class contract, same
    decisions (fuzz-verified); the only difference is speed."""
    def __init__(self, weights, flags, topk2=8, w_excav=_W_EXCAV_SHIP, w_hang=_W_HANG_SHIP):
        self.w = np.asarray(weights, dtype=np.float64)
        self.fl = np.asarray(flags, dtype=np.int32)
        self.topk2 = int(topk2)
        self.w_excav = int(w_excav)
        self.w_hang = int(w_hang)

    def choose(self, board, cur, nxt):
        col, vir = board_flat(board)
        a = _choose_d3_ship_eh_delta(col, vir, cur.a, cur.b, nxt.a, nxt.b, self.topk2,
                                     self.w_excav, self.w_hang, self.w, self.fl)
        return None if a < 0 else int(a)


def decide_ship_d3_delta(board128, pA, pB, nA, nB, w_vrdy, topk2=8):
    """decide_ship_d3 backed by the incremental leaf.  Same result, ~2-3x faster."""
    col, vir = _decode_nes(board128)
    w = weights_rtl_r47(); fl = flags_r47()
    w[R_VRDY] = float(w_vrdy)
    a = _choose_d3_ship_eh_delta(col, vir, int(pA) + 1, int(pB) + 1, int(nA) + 1, int(nB) + 1,
                                 int(topk2), int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
    if a < 0:
        return None
    return int(a % 8), int(_VAR_OF_O4[a // 8])


def decide_ship_d3_wdict_delta(board128, pA, pB, nA, nB, rtl, topk2=8):
    """decide_ship_d3_wdict backed by the incremental leaf -- the coefficient-search
    entry point, where the speedup compounds over the whole grid."""
    col, vir = _decode_nes(board128)
    w = weights_rtl_r47(); fl = flags_r47()
    for t, idx in _RTL_IDX.items():
        w[idx] = float(rtl[t])
    a = _choose_d3_ship_eh_delta(col, vir, int(pA) + 1, int(pB) + 1, int(nA) + 1, int(nB) + 1,
                                 int(topk2), int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
    if a < 0:
        return None
    return int(a % 8), int(_VAR_OF_O4[a // 8])


def warmup_delta(topk2=8):
    bc = np.zeros(NCELL, dtype=np.int8); bv = np.zeros(NCELL, dtype=np.int8)
    w = weights_rtl_r47(); fl = flags_r47()
    base = np.empty(NBASE, dtype=np.int64); terms = np.empty(NT, dtype=np.int64)
    tc = np.empty(NCELL, dtype=np.int8); tv = np.empty(NCELL, dtype=np.int8)
    _base_scan(bc, bv, fl, base)
    _combine_terms(base, w)
    _expand_leaf_delta(bc, bv, base, 2, 3, 1, 2, tc, tv, w, fl, terms)
    _leaf_delta_noboard(bc, bv, base, 2, 3, 1, 2, w, fl, tc, tv, terms)
    _expected_third_ship_delta(bc, bv, w, fl, base, terms, tc, tv)
    _choose_d3_ship_eh_delta(bc, bv, 1, 2, 1, 2, topk2,
                             int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)


# ---- regime-gated variant (task #32 pattern, transferred to the RTL leaf) ----
# PRE-REGISTERED (see accept_criteria_regime.md). Per-regime weights = the WINNER base
# scaled by task #32's multiplicative regime scales {setup, buried, ready} and SNAPPED to
# the RTL grid {4,6,8,12,16,24,32,48,60}. matched/vrdy held at winner (task #32 had no
# scale for them); "shape" (maxh/holes/toprisk) is a FIXED structural term in the RTL leaf
# so its regime scale CANNOT be applied -- a documented limitation of the transfer.
#   OPEN vc>32 : setup 32*0.50=16, buried 48*0.75=36->snap 32, rdyext 8*1.0 =8
#   MID  8<vc<=32: setup 32*0.75=24, buried 48*0.75=36->snap 32, rdyext 8*1.5=12
#   END  vc<=8 : setup 32*1.50=48, buried 48*0.50=24,          rdyext 8*1.0 =8
def variant_regime():
    """Return {'open':(w,fl),'mid':(w,fl),'end':(w,fl)} -- the pre-registered regime dicts."""
    def _w(setup, buried, rdyext):
        w, fl = variant("winner")            # winner base: setup32 matched48 buried48 rdyext8 vrdy8
        w[R_SETUP] = float(setup); w[R_BURIED] = float(buried); w[R_RDYEXT] = float(rdyext)
        return w, fl
    return {"open": _w(16, 32, 8),
            "mid":  _w(24, 32, 12),
            "end":  _w(48, 24, 8)}


class RegimeD3DeciderEH:
    """Regime-gated depth-3 ship brain: selects the per-regime leaf weights by the ROOT
    board's virus count (OPEN vc>32 / MID 8<vc<=32 / END vc<=8), then delegates to the
    SAME validated FastShipD3DeciderEH.choose kernel. Root-gating (regime chosen once per
    decision, not per search leaf) is BOTH the RTL-cheapest shippable form (select constants
    once by the current virus count the copro already holds) AND a close approximation to
    per-leaf gating within a depth-3 window (leaf vc stays within a few of root vc). Zero
    njit change -> the validated search is untouched."""
    def __init__(self, regime=None, topk2=8):
        rg = regime if regime is not None else variant_regime()
        self.d = {k: FastShipD3DeciderEH(w, fl, topk2=topk2) for k, (w, fl) in rg.items()}

    def choose(self, board, cur, nxt):
        _c, vir = board_flat(board)
        vc = _virus_count(vir)
        key = "open" if vc > 32 else ("mid" if vc > 8 else "end")
        return self.d[key].choose(board, cur, nxt)
