#!/usr/bin/env python3
"""Explicit offline mirror of the deployed base policy's R4 root semantics.

This module deliberately leaves ``fast_rtl_x.FastShipD3DeciderEH`` unchanged: that class
is the legacy flat-hang policy behind historical corpora and the running Hetzner arm.
Callers that mean deployed firmware semantics must opt into this named path.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from numba import int8, int64, njit

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
for path in (os.path.join(REPO, "experiments", "eval47"),
             os.path.join(REPO, "experiments", "depth4", "snap"),
             os.path.join(REPO, "experiments", "tuck_v3"),
             "/home/struktured/projects/dr_mario_rl/tmp/combo_term",
             "/home/struktured/projects/dr_mario_rl/tmp/endgame",
             "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src"):
    if path not in sys.path:
        sys.path.insert(0, path)

import fast_rtl_x as FX  # noqa: E402
import root_search as RS  # noqa: E402
from fast_sim_x import NCELL, _expand_core, _virus_count, board_flat  # noqa: E402

SEMANTICS = "firmware_r4"
W_EXCAV = 24
W_HANG_BASE = 40
W_HANG_GAP = 20


@njit(int64(int8[:], int8[:]), cache=True, fastmath=False)
def hang_credit_r4(col, vir):
    """R4 weighted credit, already in score units (not a feature count)."""
    total = int64(0)
    for r in range(15):
        for c in range(8):
            idx = r * 8 + c
            if col[idx] == 0 or vir[idx] or col[(r + 1) * 8 + c] != 0:
                continue
            rr = r + 2
            while rr < 16 and col[rr * 8 + c] == 0:
                rr += 1
            if rr >= 16 or col[rr * 8 + c] != col[idx]:
                continue
            has_virus = False
            for vr in range(16):
                if vir[vr * 8 + c]:
                    has_virus = True
                    break
            if has_virus:
                total += W_HANG_BASE + W_HANG_GAP * (rr - r - 1)
    return total


def root_value(col, vir, nv, cells, na, nb, w, fl, topk2=8):
    """One resolved root candidate under the deployed R4 scorer."""
    imm1 = (float(w[FX.R_WVIR]) * nv + float(w[FX.R_WCELLS]) * cells
            + (float(w[FX.R_VBONUS]) if nv >= 2 else 0.0))
    if _virus_count(vir) == 0:
        return imm1 + float(FX._WIN_SHIP)
    # Reuse the proven historical search machinery with its flat hang coefficient
    # explicitly zero, then add the R4 score exactly once.
    rest = RS._ply2plus_value_ship_eh(
        col, vir, int64(na), int64(nb), int64(topk2), int64(W_EXCAV), int64(0), w, fl)
    return imm1 + float(rest) + float(hang_credit_r4(col, vir))


def candidate_values(col, vir, ca, cb, na, nb, w, fl, *, topk2=8, wt=0, ws=20):
    """All 32 root-slot values; NaN marks an illegal straight drop."""
    if wt:
        import pressure_rig as PR
        from terms47 import g_tower
    if ws:
        from terms47 import g_stranded
    vals = np.full(32, np.nan)
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = root_value(c1, v1, nv, cells, na, nb, w, fl, topk2)
            if wt:
                val -= wt * g_tower(c1, v1, PR.H0)
            if ws:
                val -= ws * g_stranded(c1, v1)
            vals[var * 8 + cc] = val
    return vals


def choose_from_values(vals, order=None):
    if order is None:
        order = np.array([v * 8 + c for v in (2, 3, 0, 1) for c in range(8)])
    if not np.isfinite(vals).any():
        return None
    return int(order[np.nanargmax(vals[order])])


class FirmwareR4Decider:
    """Board-in fast decider for explicit deployed R4 base-policy simulations."""

    semantics = SEMANTICS

    def __init__(self, weights, flags, topk2=8, wt=0, ws=20):
        self.w = np.asarray(weights, dtype=np.float64)
        self.fl = np.asarray(flags, dtype=np.int32)
        self.topk2 = int(topk2)
        self.wt = int(wt)
        self.ws = int(ws)

    def values(self, board, cur, nxt):
        col, vir = board_flat(board)
        return candidate_values(col, vir, int(cur.a), int(cur.b), int(nxt.a), int(nxt.b),
                                self.w, self.fl, topk2=self.topk2,
                                wt=self.wt, ws=self.ws)

    def choose(self, board, cur, nxt):
        return choose_from_values(self.values(board, cur, nxt))
