#!/usr/bin/env python3
"""Candidate-valued offline mirror of the deployed v8 base policy.

Unlike the historical compact oracle path, this carries pill links, resolves every searched
placement to fixpoint, rewards cascade depth, and uses R4 hang semantics.  It intentionally
does not include the independent tuck extension.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from numba import int8, int32, int64, float64, njit

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
PATHS = (
    os.path.join(REPO, "experiments", "depth4", "snap"),
    os.path.join(REPO, "experiments", "eval47"),
    "/home/struktured/projects/dr_mario_rl/tmp/combo_term",
    "/home/struktured/projects/dr_mario_rl/tmp/endgame",
    "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src",
)
for path in reversed(PATHS):
    if path not in sys.path:
        sys.path.insert(0, path)

import fast_rtl_x as FX  # noqa: E402  load the pinned local mirror first
import cascade_chain_x as CH  # noqa: E402
import cascade_link_x as CL  # noqa: E402
import cascade_stranded_x as CS  # noqa: E402
from fast_sim_x import NCELL, _stable_desc, _virus_count  # noqa: E402

SEMANTICS = "firmware_v8"
W_EXCAV = 24
W_HANG = 40
W_HANG_GAP = 20
W_CHAIN = 180
WS = 20
TOPK2 = 8
CHAMP_ORDER = np.array([v * 8 + c for v in (2, 3, 0, 1) for c in range(8)],
                       dtype=np.int64)


@njit(int64(int8[:], int8[:]), cache=True, fastmath=False)
def hang_credit_r4(col, vir):
    total = int64(0)
    for r in range(15):
        for c in range(8):
            i = r * 8 + c
            if col[i] == 0 or vir[i] or col[(r + 1) * 8 + c] != 0:
                continue
            rr = r + 2
            while rr < 16 and col[rr * 8 + c] == 0:
                rr += 1
            if rr >= 16 or col[rr * 8 + c] != col[i]:
                continue
            has_virus = False
            for vr in range(16):
                if vir[vr * 8 + c]:
                    has_virus = True
                    break
            if has_virus:
                total += W_HANG + W_HANG_GAP * (rr - r - 1)
    return total


@njit(cache=True, fastmath=False)
def _soft_cap1_child(pcol, pvir, variant, column, pa, pb, ccol, cvir, mask):
    """Replay one root through the 6502 EH helper's deliberately old mechanics.

    Clears are cap-one.  Its `gravity` primitive treats every non-virus byte as an independent
    cell; link/body identity is not consulted.  Parents presented to the policy are stable, so a
    global first-clear mask equals the helper's targeted placed-row/column scan.
    """
    ok, r0, c0, r1, c1 = CL._resting(pcol, variant, column)
    if ok == 0:
        return 0
    for i in range(NCELL):
        ccol[i] = pcol[i]
        cvir[i] = pvir[i]
    if variant == 0 or variant == 2:
        col0 = pa; col1 = pb
    else:
        col0 = pb; col1 = pa
    i0 = r0 * 8 + c0; i1 = r1 * 8 + c1
    ccol[i0] = col0; ccol[i1] = col1
    cvir[i0] = 0; cvir[i1] = 0
    nclear = CL._find_clears_mask(ccol, mask)
    if nclear:
        for i in range(NCELL):
            if mask[i]:
                ccol[i] = 0; cvir[i] = 0
        for c in range(8):
            dest = 15
            for read in range(15, -1, -1):
                i = read * 8 + c
                if ccol[i] == 0:
                    continue
                if cvir[i]:
                    dest = read - 1
                else:
                    di = dest * 8 + c
                    if di != i:
                        ccol[di] = ccol[i]; cvir[di] = 0
                        ccol[i] = 0; cvir[i] = 0
                    dest -= 1
    return 1


@njit(float64[:](int8[:], int8[:], int8[:], int64, int64, int64, int64,
                  float64[:], int32[:], int64, int64, int64), cache=True, fastmath=False)
def _candidate_values(pcol, pvir, plnk, ca, cb, na, nb, w, fl, hang_mode,
                      eh_mode, eh_on_no_ply2):
    """Mechanical candidate-valued form of cascade_stranded_x's shipped search.

    hang_mode=0 preserves that module's legacy flat hang; hang_mode=1 swaps only the
    root hang credit to R4.  All other mechanics and arithmetic are shared imports.
    """
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
    base1 = np.empty(CH.NBASE, dtype=int64); base2 = np.empty(CH.NBASE, dtype=int64)
    base3 = np.empty(CH.NBASE, dtype=int64); terms = np.empty(CH.NT, dtype=int64)
    vals = np.empty(32, dtype=float64)
    for i in range(32):
        vals[i] = np.nan
    CH._base_scan(pcol, pvir, fl, base1)
    for o4 in range(4):
        var = FX._VAR_OF_O4[o4]
        for cl in range(8):
            ok, nv, cells, leaf1, ch1 = CH._leaf_chain(
                pcol, pvir, plnk, base1, var, cl, ca, cb, w, fl,
                c1, v1, l1, mask, terms, 0, True)
            if ok == 0:
                continue
            imm1 = CH._imm_chain(nv, cells, ch1, w, W_CHAIN)
            if _virus_count(v1) == 0:
                val = imm1 + int64(FX._WIN_SHIP)
            else:
                if eh_mode == 0:
                    _soft_cap1_child(pcol, pvir, var, cl, ca, cb, e2c, e2v, mask)
                    eh_excav = FX._g_excav_ship(e2c, e2v)
                    if hang_mode == 1:
                        eh_hang = hang_credit_r4(e2c, e2v)
                    else:
                        eh_hang = W_HANG * FX._g_hang_ship(e2c, e2v)
                elif eh_mode == 2:
                    CL._expand_linked(pcol, pvir, plnk, var, cl, ca, cb,
                                      e2c, e2v, e2l, mask, 1)
                    eh_excav = FX._g_excav_ship(e2c, e2v)
                    if hang_mode == 1:
                        eh_hang = hang_credit_r4(e2c, e2v)
                    else:
                        eh_hang = W_HANG * FX._g_hang_ship(e2c, e2v)
                else:
                    eh_excav = FX._g_excav_ship(c1, v1)
                    if hang_mode == 1:
                        eh_hang = hang_credit_r4(c1, v1)
                    else:
                        eh_hang = W_HANG * FX._g_hang_ship(c1, v1)
                eh_value = W_EXCAV * eh_excav + eh_hang
                CH._base_scan(c1, v1, fl, base2)
                m2 = 0
                for o42 in range(4):
                    var2 = FX._VAR_OF_O4[o42]
                    for cl2 in range(8):
                        ok2, nv2, cells2, lv2, ch2 = CH._leaf_chain(
                            c1, v1, l1, base2, var2, cl2, na, nb, w, fl,
                            s2c, s2v, s2l, mask, terms, 0, True)
                        if ok2 == 0:
                            continue
                        imm2 = CH._imm_chain(nv2, cells2, ch2, w, W_CHAIN)
                        keys2[m2] = float64(imm2 + lv2)
                        imms2[m2] = imm2
                        for i in range(NCELL):
                            b2col[m2, i] = s2c[i]
                            b2vir[m2, i] = s2v[i]
                            b2lnk[m2, i] = s2l[i]
                        m2 += 1
                if m2 == 0:
                    val = imm1 + leaf1
                    if eh_on_no_ply2 == 1:
                        val += eh_value
                else:
                    _stable_desc(keys2, m2, order2)
                    kk2 = m2 if TOPK2 > m2 else TOPK2
                    best2 = int64(0); have2 = False
                    for s2 in range(kk2):
                        k2 = order2[s2]
                        for i in range(NCELL):
                            e2c[i] = b2col[k2, i]
                            e2v[i] = b2vir[k2, i]
                            e2l[i] = b2lnk[k2, i]
                        if _virus_count(e2v) == 0:
                            v2 = imms2[k2] + int64(FX._WIN_SHIP)
                        else:
                            v2 = imms2[k2] + CH._expected_third_chain(
                                e2c, e2v, e2l, w, fl, base3, terms,
                                tc, tv, tl, mask, 0, W_CHAIN)
                        if not have2 or v2 > best2:
                            best2 = v2; have2 = True
                    val = imm1 + leaf1 + ((best2 - leaf1) >> int64(1))
                    val += eh_value
            val -= WS * CS._g_stranded47(c1, v1)
            vals[var * 8 + cl] = float64(val)
    return vals


@njit(cache=True, fastmath=False)
def _no_ply2_eh_deltas(pcol, pvir, plnk, ca, cb, na, nb, w, fl):
    """Cheap exact delta of the deliberately-wrong `eh_on_no_ply2` mutant.

    It resolves each real root once, but legality of the next pill needs only `_resting`; no
    second/third-ply value is required.  Nonzero entries are exactly the candidates on which that
    mutant differs from the shipped policy.
    """
    out = np.zeros(32, dtype=np.float64)
    c1 = np.empty(NCELL, dtype=int8); v1 = np.empty(NCELL, dtype=int8)
    l1 = np.empty(NCELL, dtype=int8); mask = np.empty(NCELL, dtype=int8)
    ec = np.empty(NCELL, dtype=int8); ev = np.empty(NCELL, dtype=int8)
    base1 = np.empty(CH.NBASE, dtype=int64); terms = np.empty(CH.NT, dtype=int64)
    CH._base_scan(pcol, pvir, fl, base1)
    for o4 in range(4):
        var = FX._VAR_OF_O4[o4]
        for cl in range(8):
            ok, _nv, _cells, _leaf1, _ch1 = CH._leaf_chain(
                pcol, pvir, plnk, base1, var, cl, ca, cb, w, fl,
                c1, v1, l1, mask, terms, 0, True)
            if ok == 0 or _virus_count(v1) == 0:
                continue
            have2 = False
            for o42 in range(4):
                var2 = FX._VAR_OF_O4[o42]
                for cl2 in range(8):
                    ok2, _r0, _c0, _r1, _c1 = CL._resting(c1, var2, cl2)
                    if ok2:
                        have2 = True
                        break
                if have2:
                    break
            if not have2:
                _soft_cap1_child(pcol, pvir, var, cl, ca, cb, ec, ev, mask)
                out[var * 8 + cl] = (W_EXCAV * FX._g_excav_ship(ec, ev)
                                           + hang_credit_r4(ec, ev))
    return out


def candidate_values(col, vir, lnk, ca, cb, na, nb, w, fl, *, r4=True,
                     full_child_eh=False, linked_replay_eh=False, eh_on_no_ply2=False):
    if full_child_eh and linked_replay_eh:
        raise ValueError("select at most one deliberately-wrong EH board")
    eh_mode = 1 if full_child_eh else (2 if linked_replay_eh else 0)
    return _candidate_values(np.ascontiguousarray(col, dtype=np.int8),
                             np.ascontiguousarray(vir, dtype=np.int8),
                             np.ascontiguousarray(lnk, dtype=np.int8),
                             int(ca), int(cb), int(na), int(nb),
                             np.asarray(w, dtype=np.float64), np.asarray(fl, dtype=np.int32),
                             1 if r4 else 0, eh_mode, 1 if eh_on_no_ply2 else 0)


def no_ply2_eh_deltas(col, vir, lnk, ca, cb, na, nb, w, fl):
    return _no_ply2_eh_deltas(np.ascontiguousarray(col, dtype=np.int8),
                              np.ascontiguousarray(vir, dtype=np.int8),
                              np.ascontiguousarray(lnk, dtype=np.int8),
                              int(ca), int(cb), int(na), int(nb),
                              np.asarray(w, dtype=np.float64), np.asarray(fl, dtype=np.int32))


def choose_from_values(vals, order=CHAMP_ORDER):
    if not np.isfinite(vals).any():
        return None
    return int(order[np.nanargmax(vals[order])])


def tie_jitter(action, tie_seed):
    """The deployed 6502's 0..3 root jitter for one action and match seed."""
    action = int(action)
    var, col = action // 8, action % 8
    o4 = int(FX._VAR_OF_O4[var])
    t = (int(tie_seed) & 0xFF) ^ ((o4 << 3) | col)
    return (t ^ (t >> 3)) & 3


def jittered_values(vals, tie_seed):
    out = np.asarray(vals, dtype=np.float64).copy()
    if int(tie_seed) & 0xFF:
        for action in range(32):
            if np.isfinite(out[action]):
                out[action] += tie_jitter(action, tie_seed)
    return out


def choose_seeded(vals, tie_seed, order=CHAMP_ORDER):
    return choose_from_values(jittered_values(vals, tie_seed), order)


def board_planes(board):
    col, vir = CL.board_flat(board)
    lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
    return col, vir, lnk


class FirmwareV8Decider:
    semantics = SEMANTICS

    def __init__(self, weights, flags):
        self.w = np.asarray(weights, dtype=np.float64)
        self.fl = np.asarray(flags, dtype=np.int32)

    def values(self, board, cur, nxt):
        col, vir, lnk = board_planes(board)
        return candidate_values(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b,
                                self.w, self.fl, r4=True)

    def choose(self, board, cur, nxt):
        return choose_from_values(self.values(board, cur, nxt))
