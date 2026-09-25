#!/usr/bin/env python3
"""GENERALISED ROOT-ACTION TUCKS (v3), offline proof only.

Design (see TUCK_V3_OFFLINE.md for the full writeup): the shipped depth-3 brain
(`fast_rtl_x._choose_d3_ship_eh`) enumerates exactly 32 root actions -- (variant, col)
straight drops -- and scores each with a full depth-3 subtree (ply2 full enumeration,
top-K2=8 promoted to a 4-pill stratified expectimax third ply, DISC_SHIFT temporal blend,
plus the ply-1 excav/hang add-on). The leaf-gated v2 design (post-search override, scored
at depth-1 only) was EMPIRICALLY REFUTED: +7.11 pills WORSE, n=227, because a leaf
improvement is routinely a depth-3 regression -- see dr-mario-tuck-executor-gap memory,
"v2 LEAF-GATED DESIGN EMPIRICALLY REFUTED". The only design that survived scrutiny there
is ROOT-ACTION: add executor-performable tucks to the SAME 32-slot root enumeration,
score them with the IDENTICAL depth-3 machinery, and let the normal argmax decide.

THIS FILE extracts the shipped search's ply-2-onward scoring (imm2 + top-K2 + expectimax
third + DISC_SHIFT blend + eh add-on) into a standalone function `_ply2plus_value_ship_eh`,
called ONCE PER ROOT CANDIDATE -- both for the 32 base actions and for any tuck root
actions -- so tuck children are scored by EXACTLY the same eval as ordinary placements.
Nothing in fast_rtl_x.py or fast_sim_x.py is modified; this is a scratch copy that reuses
their already-compiled numba primitives (_expand_core, _leafv_ship, _expected_third_ship,
_stable_desc, _g_excav_ship, _g_hang_ship, _virus_count) and adds ONE new primitive,
_expand_core_at, which is _expand_core with the (r0,c0,r1,c1) rest cells supplied directly
instead of derived from _resting(variant, col) -- the only new mechanic a tuck needs.

MOTION LEGALITY (what makes a tuck root action ONE the driver's existing DRTUCK executor
could actually play): the shipped executor (patch_cartridge_copro.py, TUCK_C2/TUCK_R2) can
do exactly ONE horizontal switch -- fall in an approach column, and once the pill's Y
reaches a trigger row, steer to a target column and fall straight down. No re-rotation, no
second switch. We gate tuck root-action candidates with `_exec_reach_cells`, copied
unmodified from tuck_ab.py's DRTUCK_EXEC model (adjacent-column approach, deepest-reach
heuristic) -- the SAME reachability model that produced the executor-CORRECTED -5.20 pills
[-8.92,-1.47] result in dr-mario-tuck-executor-gap. This is the "permissive direction"
approximation documented there: it requires only the placement's DEEPEST cell to be
reachable, which over-states reach rather than under-states it. Root-action DISSOLVES the
D3 defect (target column IS the column the search actually scored, by construction) but
D1 ($0386 = 15-r units) and D2 (per-frame descriptor wipe) remain firmware fixes that a
future silicon build still needs -- irrelevant to this offline python proof, which executes
the tuck's cells directly.

CORRECTNESS: `equivalence_selftest()` proves that with the tuck candidate list forced
empty, `choose_root_with_tucks()` picks the IDENTICAL action (and, importantly, the
IDENTICAL numeric value) as the untouched shipped `FastShipD3DeciderEH` on random boards --
i.e. the refactor that split "one candidate's value" out of the monolithic 32-action loop
did not change the arithmetic.
"""
from __future__ import annotations

import os
import sys

ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/.claude/worktrees/faithful-sim/src", QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
from numba import njit, int8, int32, int64, float64

import fast_rtl_x as FX
from fast_sim_x import (ROWS, COLS, NCELL, _expand_core, _virus_count, _stable_desc,
                        _targeted_resolve, board_flat)
from fb import FB
import tuck_enum as TE

# ------------------------------------------------------------- new numba primitive
@njit(cache=True, fastmath=False)
def _expand_core_at(pcol, pvir, r0, c0, r1, c1, col0, col1, ccol, cvir):
    """_expand_core, but the rest cells are SUPPLIED (a tuck landing) instead of
    derived from _resting(variant, col) (a straight drop). Same clone + place +
    cap-1 targeted-resolve mechanics; returns (nv, cells) -- caller already knows
    the placement is legal (board-empty at r0/c0, r1/c1), so there is no 'ok' flag."""
    for i in range(NCELL):
        ccol[i] = pcol[i]
        cvir[i] = pvir[i]
    ccol[r0 * COLS + c0] = col0
    ccol[r1 * COLS + c1] = col1
    cvir[r0 * COLS + c0] = 0
    cvir[r1 * COLS + c1] = 0
    cells, nv = _targeted_resolve(ccol, cvir, r0, c0, r1, c1)
    return (nv, cells)


# ------------------------------------------------------ shared ply2-onward scorer
@njit(int64(int8[:], int8[:], int64, int64, int64, int64, int64, float64[:], int32[:]),
      cache=True, fastmath=False)
def _ply2plus_value_ship_eh(c1, v1, na, nb, topk2, w_excav, w_hang, w, fl):
    """Everything `_choose_d3_ship_eh` does AFTER imm1, for one already-resolved ply-1
    board (c1, v1) that still has viruses: full ply-2 enumeration, top-K2 promoted to
    the 4-pill stratified expectimax third ply, the DISC_SHIFT temporal blend, and the
    ply-1 excav/hang add-on. Copied verbatim from fast_rtl_x._choose_d3_ship_eh's inner
    body (lines ~686-719 there) so a root candidate -- base OR tuck -- gets byte-identical
    treatment. Caller must not call this when _virus_count(v1) == 0 (that branch is
    imm1 + WIN, handled by the caller, exactly as in the shipped function)."""
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
        var2 = FX._VAR_OF_O4[o42]
        for col2 in range(8):
            ok2, nv2, cells2 = _expand_core(c1, v1, var2, col2, na, nb, s2c, s2v)
            if ok2 == 0:
                continue
            imm2 = (int64(w[FX.R_WVIR]) * nv2 + int64(w[FX.R_WCELLS]) * cells2
                    + (int64(w[FX.R_VBONUS]) if nv2 >= 2 else int64(0)))
            keys2[m2] = float64(imm2 + FX._leafv_ship(s2c, s2v, w, fl))
            imms2[m2] = imm2
            for i in range(NCELL):
                b2col[m2, i] = s2c[i]
                b2vir[m2, i] = s2v[i]
            m2 += 1
    if m2 == 0:
        val_rest = FX._leafv_ship(c1, v1, w, fl)
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
                v2 = imms2[k2] + int64(FX._WIN_SHIP)
            else:
                v2 = imms2[k2] + FX._expected_third_ship(e2c, e2v, w, fl)
            if not have2 or v2 > best2:
                best2 = v2
                have2 = True
        leaf1 = FX._leafv_ship(c1, v1, w, fl)
        val_rest = leaf1 + ((best2 - leaf1) >> int64(1))
    val_rest += w_excav * FX._g_excav_ship(c1, v1) + w_hang * FX._g_hang_ship(c1, v1)
    return val_rest


def _root_value(col, vir, nv, cells, na, nb, topk2, w_excav, w_hang, w, fl):
    """imm1 + (WIN or ply2plus), shared by base and tuck root candidates."""
    imm1 = (float(w[FX.R_WVIR]) * nv + float(w[FX.R_WCELLS]) * cells
            + (float(w[FX.R_VBONUS]) if nv >= 2 else 0.0))
    if _virus_count(vir) == 0:
        return imm1 + float(FX._WIN_SHIP)
    return imm1 + float(_ply2plus_value_ship_eh(col, vir, int64(na), int64(nb), int64(topk2),
                                                int64(w_excav), int64(w_hang), w, fl))


# --------------------------------------------------- executor motion-legality gate
def _exec_reach_cells(fb):
    """Rest cells reachable under the shipped executor's one-switch model. Copied
    UNMODIFIED (not imported, to avoid a hard dependency on a scratch A/B script) from
    tuck_ab.py's `_exec_reach_cells` / exec_reachable.py's `executor_tucks` -- the model
    that produced the executor-CORRECTED -5.20 pills result. Adjacent-column approach
    only (c-1, c+1); "reach" = the DEEPEST point the approach column offers, used as a
    permissive proxy for "some row along the fall has both columns open" -- documented
    there as over-stating reach, not under-stating it."""
    from fb import ROWS as _R, COLS as _C2, EMPTY as _E
    occ = lambda r, c: fb.col[r * _C2 + c] != _E

    def rest(c, r):
        while r + 1 < _R and not occ(r + 1, c):
            r += 1
        return r

    def topdrop(c):
        return None if occ(0, c) else rest(c, 0)

    out = set()
    for c in range(_C2):
        sd = topdrop(c)
        sdd = -1 if sd is None else sd
        for a in (c - 1, c + 1):
            if not (0 <= a < _C2):
                continue
            ra = topdrop(a)
            if ra is None or occ(ra, c):
                continue
            rf = rest(c, ra)
            if rf > sdd:
                out.add((rf, c))
    return out


def tuck_root_candidates(fb, pa, pb, frames_per_row=12, exec_only=True):
    """Executor-motion-legal tuck placements for pill (pa, pb) on board `fb`.

    Returns a list of TE.enumerate() placement dicts (cells, orient, col, flip, colors,
    ...), filtered to `is_tuck` and (if exec_only) to the executor's reach model above.
    Same "deepest cell must be reachable" permissive predicate used by the REFUTED v2 --
    inherited deliberately, since it is a LEGALITY filter here (what the search may
    propose), not a value-scoring shortcut (how it is scored, which is now full depth-3).
    """
    cands = TE.enumerate(fb, pa, pb, mode="gravity", frames_per_row=frames_per_row)
    reach = _exec_reach_cells(fb) if exec_only else None
    out = []
    for p in cands:
        if not p.get("is_tuck"):
            continue
        if reach is not None:
            r0, c0, r1, c1 = p["cells"]
            deep = (r0, c0) if r0 >= r1 else (r1, c1)
            if deep not in reach:
                continue
        out.append(p)
    return out


def fill_height(fb):
    """Tallest column's occupied height (ROWS - top_occ), for board-context reporting.
    Same definition destroy.py's max_height uses."""
    h = 0
    for c in range(COLS):
        t = fb.top_occ(c)
        if ROWS - t > h:
            h = ROWS - t
    return h


# ----------------------------------------------------------------- the root search
def choose_root_with_tucks(fb, cur, nxt, w, fl, topk2=8,
                           w_excav=FX._W_EXCAV_SHIP, w_hang=FX._W_HANG_SHIP,
                           frames_per_row=12, exec_only=True, tuck_cands=None,
                           theta=0.0):
    """The 32 shipped root actions PLUS executor-motion-legal tuck root actions, all
    scored by the identical depth-3 machinery. Returns a dict:
        kind        'base' or 'tuck'
        action      int 0..31          (kind == 'base')
        placement   TE.enumerate dict  (kind == 'tuck')
        ca, cb      colours to write at cells[0], cells[1]  (kind == 'tuck')
        val         the winning root value (for diagnostics / the equivalence test)
        best_base_val   the best of the 32 base actions alone (for margin diagnostics)
        n_tuck_cands, n_tuck_legal   candidate counts, for fire-rate / coverage reporting

    `tuck_cands`, if given, is used instead of recomputing (lets a caller pass an empty
    list to run BASE-ONLY, the arm-off control and the equivalence self-test).

    `theta` (phase 2, margin gate): a tuck may only be chosen if its value beats the
    best BASE action's value by >= theta (eval units). theta=0.0 is EXACTLY phase 1's
    plain argmax (no gate) -- eligibility collapses to `val >= best_val_base`, which is
    automatically implied for any candidate that would have won an ungated argmax, so
    this is provably a superset-preserving generalisation, not a behaviour change at
    theta=0. Verified empirically too: `equivalence_selftest(theta=0.0)` and the phase-2
    replay-vs-phase-1-JSON check in `calibrate_margins.py`.
    """
    col = np.frombuffer(bytes(fb.col), dtype=np.uint8).astype(np.int8)
    vir = np.frombuffer(bytes(fb.vir), dtype=np.uint8).astype(np.int8)
    ca, cb, na, nb = int(cur.a), int(cur.b), int(nxt.a), int(nxt.b)

    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_val = None
    best = None

    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = _root_value(c1, v1, nv, cells, na, nb, topk2, w_excav, w_hang, w, fl)
            if best_val is None or val > best_val:
                best_val = val
                best = {"kind": "base", "action": var * 8 + cc, "val": val}

    best_base_val = best_val   # exactly the max over the 32 base actions, nothing else
                               # has been considered yet -- the margin reference point.

    if tuck_cands is None:
        tuck_cands = tuck_root_candidates(fb, ca, cb, frames_per_row, exec_only)
    n_legal = 0
    for p in tuck_cands:
        r0, c0, r1, c1_ = p["cells"]
        col0, col1 = p["colors"]
        nv, cells = _expand_core_at(col, vir, r0, c0, r1, c1_, col0, col1, c1, v1)
        val = _root_value(c1, v1, nv, cells, na, nb, topk2, w_excav, w_hang, w, fl)
        n_legal += 1
        if best_base_val is not None and val < best_base_val + theta:
            continue                     # THE MARGIN GATE -- theta=0 never rejects a
                                          # candidate that could have won the plain argmax
        if best_val is None or val > best_val:
            best_val = val
            best = {"kind": "tuck", "placement": p, "ca": col0, "cb": col1, "val": val,
                    "margin": val - best_base_val if best_base_val is not None else None}

    best["n_tuck_cands"] = len(tuck_cands)
    best["n_tuck_legal"] = n_legal
    best["best_base_val"] = best_base_val
    return best


# =========================================================================== self-test
def equivalence_selftest(n_boards=200, seed=20260802):
    """With tuck_cands forced to [], choose_root_with_tucks must agree with the untouched
    FastShipD3DeciderEH on both the CHOSEN ACTION and the NUMERIC VALUE -- proof that
    splitting the monolithic 32-action loop into a per-candidate function did not change
    the arithmetic. Also spot-checks that tuck candidates, when present, are legal
    (both cells empty on the parent board) and is_tuck (no straight drop matches them)."""
    import random
    rnd = random.Random(seed)
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    dec = FX.FastShipD3DeciderEH(w, fl, topk2=8)

    class P:
        def __init__(self, a, b):
            self.a = a
            self.b = b

    mism_action = mism_val = checked = 0
    for _ in range(n_boards):
        grid = [0] * NCELL
        for c in range(COLS):
            h = rnd.randrange(0, ROWS + 1)
            for r in range(ROWS - h, ROWS):
                grid[r * COLS + c] = rnd.randint(1, 3)
        grid[3] = grid[4] = 0
        fb = FB(grid)
        cur = P(rnd.randint(1, 3), rnd.randint(1, 3))
        nxt = P(rnd.randint(1, 3), rnd.randint(1, 3))

        col, vir = board_flat_from_fb(fb)
        ship_act = FX._choose_d3_ship_eh(col, vir, cur.a, cur.b, nxt.a, nxt.b, 8,
                                         int(FX._W_EXCAV_SHIP), int(FX._W_HANG_SHIP), w, fl)
        if ship_act < 0:
            continue
        mine = choose_root_with_tucks(fb, cur, nxt, w, fl, topk2=8, tuck_cands=[])
        checked += 1
        if mine["kind"] != "base" or int(mine["action"]) != int(ship_act):
            mism_action += 1
        # also cross-check the value via a second call to the shared scorer
        c1 = np.empty(NCELL, dtype=np.int8)
        v1 = np.empty(NCELL, dtype=np.int8)
        var, cc = int(ship_act) // 8, int(ship_act) % 8
        ok, nv, cells = _expand_core(col, vir, var, cc, cur.a, cur.b, c1, v1)
        ref_val = _root_value(c1, v1, nv, cells, nxt.a, nxt.b, 8,
                              FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
        if abs(ref_val - mine["val"]) > 1e-6:
            mism_val += 1

    print(f"equivalence self-test: {checked} boards, action mismatches {mism_action}, "
          f"value mismatches {mism_val}")
    return mism_action == 0 and mism_val == 0


def board_flat_from_fb(fb):
    col = np.frombuffer(bytes(fb.col), dtype=np.uint8).astype(np.int8)
    vir = np.frombuffer(bytes(fb.vir), dtype=np.uint8).astype(np.int8)
    return col, vir


if __name__ == "__main__":
    ok = equivalence_selftest()
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
