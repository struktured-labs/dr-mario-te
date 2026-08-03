#!/usr/bin/env python3
"""FINAL diagnostic (task #17 stage 3, team-lead directive after the 20-board
localization pinned leaf1 as the diverging component): re-run the offline root-action
A/B with the leaf swapped to fpga/copro/leaf_r47.py's RTL-faithful mirror
(leaf_vrdy12 -- W_VRDY=12, matching build_copro_d3.build_image()'s REAL shipped
override, NOT leaf_r47()'s own w_vrdy=24 default, which is the ORIGINAL R47 brain
before the R3->r47b5 retune documented in build_copro_d3.py's own comment), keeping
imm1/eh/DISC-blend arithmetic UNTOUCHED (the localization proved those already match
firmware almost exactly -- eh mean diff was +5/+6, imm1 matched exactly wherever both
sides scored a real placement).

This module provides a PARALLEL (not a modification of root_search.py, which the
theta sweep's own offline reference used and must stay untouched) implementation of
the same three-function chain (_expected_third_ship -> _ply2plus_value_ship_eh ->
_root_value -> choose_root_with_tucks), with every FX._leafv_ship(...) call replaced
by `_leaf_mirrored(...)`. Deliberately PURE PYTHON, not numba -- these functions call
leaf_r47.leaf_terms, which is itself pure python (dict-returning, ragged-list-based);
numba can't jit across that boundary without a much larger rewrite of leaf_r47.py
itself, which is the ALREADY-VALIDATED (100% cell-exact vs the pinned RTL corpus AND
live RTL, 5036/5036) ground-truth reference and must not be touched to chase speed.
"""
from __future__ import annotations

import os
import sys

ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
CANON = "/home/struktured/projects/dr-mario-canonical-wt"
for _p in (ROOT + "/tmp/combo_term", QA, QA + "/bitexact_gate",
           os.path.join(CANON, "fpga", "copro")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import fast_rtl_x as FX
from fast_sim_x import NCELL, _expand_core, _virus_count, _stable_desc
import root_search as RS
from common import arrays_to_nes
import leaf_r47 as LR

_WIN_SHIP = int(FX._WIN_SHIP)


def _leaf_mirrored(col, vir):
    """Same win-check-first contract as FX._leafv_ship: WIN_SHIP on a cleared board,
    else the RTL-faithful sco (leaf_vrdy12 == the REAL shipped W_VRDY=12 config, NOT
    leaf_r47()'s own w_vrdy=24 default -- see module docstring)."""
    if _virus_count(vir) == 0:
        return _WIN_SHIP
    board_nes = arrays_to_nes(col, vir)
    sco, _win = LR.leaf_vrdy12(board_nes)
    return int(sco)


def _expected_third_mirrored(b2c, b2v, na, nb, w):
    """Pure-python mirror of FX._expected_third_ship, leaf swapped."""
    if _virus_count(b2v) == 0:
        return _WIN_SHIP
    c3 = np.empty(NCELL, dtype=np.int8)
    v3 = np.empty(NCELL, dtype=np.int8)
    tot = 0
    for t in range(4):
        x, y = int(FX._THIRD_X[t]), int(FX._THIRD_Y[t])
        best3, have3 = 0, False
        for o4 in range(4):
            var = int(FX._VAR_OF_O4[o4])
            for col in range(8):
                ok, nv, cells = _expand_core(b2c, b2v, var, col, x, y, c3, v3)
                if ok == 0:
                    continue
                vv = (int(w[FX.R_WVIR]) * nv + int(w[FX.R_WCELLS]) * cells
                      + (int(w[FX.R_VBONUS]) if nv >= 2 else 0)
                      + _leaf_mirrored(c3, v3))
                if not have3 or vv > best3:
                    best3, have3 = vv, True
        tot += best3 if have3 else _leaf_mirrored(b2c, b2v)
    return tot // 4


def _components_mirrored(c1, v1, na, nb, topk2, w_excav, w_hang, w):
    """Pure-python mirror of component_localize._components / root_search._ply2plus_
    value_ship_eh, leaf swapped, returning the same 5-tuple
    (leaf1, best2_raw, blend, eh, total_rest)."""
    b2col = np.empty((32, NCELL), dtype=np.int8)
    b2vir = np.empty((32, NCELL), dtype=np.int8)
    keys2 = []
    imms2 = []
    s2c = np.empty(NCELL, dtype=np.int8)
    s2v = np.empty(NCELL, dtype=np.int8)
    m2 = 0
    for o42 in range(4):
        var2 = int(FX._VAR_OF_O4[o42])
        for col2 in range(8):
            ok2, nv2, cells2 = _expand_core(c1, v1, var2, col2, na, nb, s2c, s2v)
            if ok2 == 0:
                continue
            imm2 = (int(w[FX.R_WVIR]) * nv2 + int(w[FX.R_WCELLS]) * cells2
                    + (int(w[FX.R_VBONUS]) if nv2 >= 2 else 0))
            keys2.append(imm2 + _leaf_mirrored(s2c, s2v))
            imms2.append(imm2)
            b2col[m2] = s2c
            b2vir[m2] = s2v
            m2 += 1
    leaf1 = _leaf_mirrored(c1, v1)
    if m2 == 0:
        best2, blend = 0, leaf1
    else:
        order = sorted(range(m2), key=lambda i: -keys2[i])   # stable desc, matches
                                                                # _stable_desc's contract
        kk2 = m2 if topk2 <= 0 or topk2 > m2 else topk2
        best2, have2 = 0, False
        for s2 in range(kk2):
            k2 = order[s2]
            e2c, e2v = b2col[k2], b2vir[k2]
            if _virus_count(e2v) == 0:
                v2 = imms2[k2] + _WIN_SHIP
            else:
                v2 = imms2[k2] + _expected_third_mirrored(e2c, e2v, na, nb, w)
            if not have2 or v2 > best2:
                best2, have2 = v2, True
        blend = leaf1 + ((best2 - leaf1) >> 1)
    eh = w_excav * FX._g_excav_ship(c1, v1) + w_hang * FX._g_hang_ship(c1, v1)
    return leaf1, best2, blend, eh, blend + eh


def root_value_mirrored(col, vir, nv, cells, na, nb, topk2, w_excav, w_hang, w):
    assert _virus_count(vir) > 0 or True
    imm1 = (float(w[FX.R_WVIR]) * nv + float(w[FX.R_WCELLS]) * cells
            + (float(w[FX.R_VBONUS]) if nv >= 2 else 0.0))
    if _virus_count(vir) == 0:
        return imm1 + float(_WIN_SHIP)
    _, _, _, _, total_rest = _components_mirrored(col, vir, na, nb, topk2, w_excav, w_hang, w)
    return imm1 + float(total_rest)


def choose_root_with_tucks_mirrored(fb, cur, nxt, w, topk2=8,
                                     w_excav=FX._W_EXCAV_SHIP, w_hang=FX._W_HANG_SHIP,
                                     frames_per_row=12, exec_only=True, tuck_cands=None,
                                     theta=0.0):
    """Mirrors root_search.choose_root_with_tucks EXACTLY (same loops, same gate),
    with root_value_mirrored substituted for _root_value -- the SAME imm1/eh/DISC
    arithmetic, ONLY the leaf term is the RTL-faithful mirror."""
    col = np.frombuffer(bytes(fb.col), dtype=np.uint8).astype(np.int8)
    vir = np.frombuffer(bytes(fb.vir), dtype=np.uint8).astype(np.int8)
    ca, cb, na, nb = int(cur.a), int(cur.b), int(nxt.a), int(nxt.b)

    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_val, best = None, None

    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = root_value_mirrored(c1, v1, nv, cells, na, nb, topk2, w_excav, w_hang, w)
            if best_val is None or val > best_val:
                best_val = val
                best = {"kind": "base", "action": var * 8 + cc, "val": val}

    best_base_val = best_val
    if tuck_cands is None:
        tuck_cands = RS.tuck_root_candidates(fb, ca, cb, frames_per_row, exec_only)
    n_legal = 0
    for p in tuck_cands:
        r0, c0, r1, c1_ = p["cells"]
        col0, col1 = p["colors"]
        nv, cells = RS._expand_core_at(col, vir, r0, c0, r1, c1_, col0, col1, c1, v1)
        val = root_value_mirrored(c1, v1, nv, cells, na, nb, topk2, w_excav, w_hang, w)
        n_legal += 1
        if best_base_val is not None and val < best_base_val + theta:
            continue
        if best_val is None or val > best_val:
            best_val = val
            best = {"kind": "tuck", "placement": p, "ca": col0, "cb": col1, "val": val,
                    "margin": val - best_base_val if best_base_val is not None else None}

    best["n_tuck_cands"] = len(tuck_cands)
    best["n_tuck_legal"] = n_legal
    best["best_base_val"] = best_base_val
    return best
