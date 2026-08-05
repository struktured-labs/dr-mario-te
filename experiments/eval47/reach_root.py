#!/usr/bin/env python3
"""Task: reachable-root enumeration modes for the #17-unified tuck study.

The shipped decider (`eval47/ab47.py::_choose_base`, strand20 config: winner
weights + ws=20 root-only `terms47.g_stranded`) enumerates exactly 32 root
actions -- every (variant, col) STRAIGHT DROP `fast_sim_x._expand_core` can
place -- and never asks whether a pill can actually GET there. `tuck_enum.py`
proved two things about that set on real boards: (1) 2.70% of those 32
straight drops are physically unreachable (a column filled to row 0 walls off
what's behind it -- the shipped search doesn't know this), and (2) the BFS
reachable set is usually LARGER than 32 -- true tucks the search never
considers at all.

Three root-candidate-enumeration modes, same root value (`root_search.
_root_value` minus `ws * terms47.g_stranded`, i.e. exactly the shipped
strand20 arithmetic) on every candidate:

  base32    -- status quo. All 32 (col, orient) straight drops via
               `fast_sim_x._expand_core`, no reachability filter. Reproduces
               `ab47.py::_choose_base(wt=0, ws=20)` bit-for-bit -- see
               `_selftest_base32_matches_shipped()`.

  reach32   -- the pure fix. Same 32 candidates, FILTERED to those whose
               (col, orient) rest cells appear in `tuck_enum.enumerate(...,
               mode="free")`'s BFS-reachable set (`reachable=True`). Strictly
               a subset of base32's candidate list; on boards with no
               overhangs and no column walled off to row 0 the two subsets
               are identical (nothing to filter) -- see
               `_selftest_reach32_eq_base32_open_board()`.

  reachfull -- the #17-unified set. ALL BFS reachable rests (straight drops
               AND tuck-class landings) as root candidates, scored with the
               identical root value. Tuck-class candidates (is_tuck=True) are
               additionally gated by the tuck_v3 ship pattern (`root_search.
               choose_root_with_tucks`'s margin gate, reused not reinvented):
               a tuck may only win if its value beats the best base32
               candidate's value by >= THETA_FULL (250, the tuck_v3 ship
               config's theta -- see mirrored_leaf.choose_root_with_tucks_
               mirrored for the same pattern under the RTL-mirror leaf).

All three share `_lazy()`'s single numba-warmed (w, fl) = `fast_rtl_x.variant
("winner")` and the same `WS` dose, so a value computed by one mode for a
candidate also present in another mode's set is bit-identical.

Board/candidate conventions (house rules, verified empirically below, not
just asserted): row-major idx = r*8+c, colors 1-based (0=empty); o4 in
{0,1}=VERT {2,3}=HORIZ, variant = o4 XOR 2 (`fast_rtl_x._VAR_OF_O4`);
`tuck_enum.py`'s orientation ring (H=0,V=1,RH=2,RV=3) maps onto the same
32-action `variant` space via `ROT_TO_VARIANT=(0,3,1,2)` -- so a TE placement
dict's own "variant"/"col" fields address the SAME (var, cc) slot `_expand_
core` does. Confirmed by construction: on 20 random boards x 2 pills, all 512
`_expand_core`-legal (var, cc) pairs were found in TE's straight-drop lookup,
0 misses.
"""
from __future__ import annotations

import sys
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np

WS = 20                # shipped strand20 dose: ab47.py::_choose_base(wt=0, ws=20)
THETA_FULL = 250.0     # reachfull's tuck-class margin gate, tuck_v3 ship config
                        # (root_search.choose_root_with_tucks' own `theta` pattern)
TOPK2 = 8
FRAMES_PER_ROW = 12    # unused by mode="free" (gravity-mode only); kept for callers
                        # that want to switch reach32/reachfull to mode="gravity"

# ---- DRDISTGATE time-budget constants (task #60 ITERATION 2 extension) -----
# SOURCE OF TRUTH: dr-mario-mods-wt/driver-nav/patch_cartridge_copro.py's own
# DIST_DASEDGE/DIST_GRAVROW module-level constants -- NOT CART_FIX_REPORT.md
# section 7's prose, which quotes the FIRST, unmeasured guess (32 hooks/edge,
# 26 hooks/row, inherited from a stale "NAV_T=5*/frame" assumption). THE SAME
# FILE was updated the SAME DAY (2026-08-05, task #49 follow-on) with
# silicon-measured replacements, confirmed live here (not re-typed from the
# report): DAS is ~2.7x faster than the stale guess (12 vs 32 hooks/edge) and
# gravity is somewhat slower (30 vs 26 hooks/row) -- both push the same
# direction (more time budget per row of remaining fall). Using the report's
# 32/26 pair would materially UNDER-state how much column-travel a given fall
# height affords. Env-overridable (DRDIST_DASEDGE/DRDIST_GRAVROW), matching
# the driver's own override pattern, in case a sensitivity re-run against the
# stale pair is ever wanted.
DIST_DASEDGE = int(os.environ.get("DRDIST_DASEDGE", "12"))   # hooks / DAS column-edge
DIST_GRAVROW = int(os.environ.get("DRDIST_GRAVROW", "30"))   # hooks / gravity row
SPAWN_COLS = (3, 4)    # tuck_enum.SPAWN_X and its capsule partner cell


def _edges_from_spawn(target_col):
    """DAS column-edges from the nearest spawn half to `target_col` -- same
    convention as tmp_logs/m3case.py's `edges_from_spawn`."""
    return min(abs(target_col - SPAWN_COLS[0]), abs(target_col - SPAWN_COLS[1]))


def _dist_table_budget_edges(fall_rows):
    """DIST_TABLE[Y] verbatim (patch_cartridge_copro.py, CART_FIX_REPORT.md
    section 7): 0 if Y<=0 else max(1, min(7, floor(Y * DIST_GRAVROW /
    DIST_DASEDGE))) -- the floor-at-1-while-any-clearance-remains rule is
    section 7.2's own bug fix (a plain floor() can retreat to 0 budget while
    Y is still > 0), reproduced here, not reinvented."""
    if fall_rows is None or fall_rows <= 0:
        return 0
    return max(1, min(7, (fall_rows * DIST_GRAVROW) // DIST_DASEDGE))


def _within_time_budget(target_row, target_col):
    """hooks_needed(edges to target_col) <= hooks_available(fall height to
    target_row). `target_row` is the candidate's own resting row (FB/tuck_enum
    convention: row 0 = top = spawn row, row 15 = floor -- see tuck_enum.py's
    module docstring), so `target_row - SPAWN_Y(=0)` IS the spawn-time fall
    height of that column region: how many rows of gravity clearance remain
    between spawn and the row this candidate locks at. Comparing edges instead
    of raw hooks is equivalent (hooks_available is always an exact multiple of
    DIST_DASEDGE) and avoids re-deriving the multiply twice."""
    return _edges_from_spawn(target_col) <= _dist_table_budget_edges(target_row)


MODES = ("base32", "reach32", "reachfull", "reach32t", "reachfull2", "reachfull2t")

_L = {}


def _lazy():
    """Import + numba-warm everything on first use. Idempotent -- safe to call
    from every choose_* function and from a ProcessPoolExecutor initializer."""
    if _L:
        return _L
    import fast_rtl_x as FX
    import fast_sim_x as FS
    import root_search as RS
    import tuck_enum as TE
    from fb import FB
    from terms47 import g_stranded

    FX.warmup_ship_eh(topk2=TOPK2)
    w, fl = FX.variant("winner")
    z = np.zeros(FS.NCELL, dtype=np.int8)
    g_stranded(z, z)   # jit warmup so play() never pays compile time
    _L.update(FX=FX, FS=FS, RS=RS, TE=TE, FB=FB, g_stranded=g_stranded, w=w, fl=fl)
    return _L


# --------------------------------------------------------------------------- base32
def choose_base32(col, vir, ca, cb, na, nb, ws=WS, topk2=TOPK2):
    """All 32 (variant, col) straight drops, no reachability filter. Reproduces
    ab47.py::_choose_base(wt=0, ws=20) bit-for-bit (see selftest)."""
    L = _lazy()
    FX, FS, RS, g_stranded = L["FX"], L["FS"], L["RS"], L["g_stranded"]
    w, fl = L["w"], L["fl"]

    c1 = np.empty(FS.NCELL, dtype=np.int8)
    v1 = np.empty(FS.NCELL, dtype=np.int8)
    best_val, best_a = None, None
    n_legal = 0
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = FS._expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            n_legal += 1
            val = RS._root_value(c1, v1, nv, cells, na, nb, topk2,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            val -= ws * g_stranded(c1, v1)
            if best_val is None or val > best_val:
                best_val, best_a = val, var * 8 + cc
    return {"kind": "base", "action": best_a, "val": best_val, "n_base_legal": n_legal}


# -------------------------------------------------------------------------- reach32
def _te_straight_lookup(fb, ca, cb):
    """{(variant, col): TE placement dict} for the <=32 non-tuck entries of
    tuck_enum.enumerate(mode="free", union_straight_drops=True). `reachable`
    on these entries tells us which of the 32 FB.resting rests the BFS
    actually PROVES reachable from spawn (vs. unioned-in but walled off --
    see tuck_enum.py's module docstring, SUPERSET section)."""
    L = _lazy()
    TE = L["TE"]
    out = {}
    for p in TE.enumerate(fb, ca, cb, mode="free", union_straight_drops=True):
        if p["is_tuck"]:
            continue
        out[(p["variant"], p["col"])] = p
    return out


def choose_reach32(fb, col, vir, ca, cb, na, nb, ws=WS, topk2=TOPK2):
    """base32's 32 candidates, filtered to the BFS-reachable subset. Falls
    back to the unfiltered base32 choice on the (should-not-happen-in-play,
    spawn-legal-implies-something-reachable) edge case where the filter
    empties the set entirely, so the runner never has to special-case a
    None action."""
    L = _lazy()
    FX, FS, RS, g_stranded = L["FX"], L["FS"], L["RS"], L["g_stranded"]
    w, fl = L["w"], L["fl"]

    lookup = _te_straight_lookup(fb, ca, cb)
    c1 = np.empty(FS.NCELL, dtype=np.int8)
    v1 = np.empty(FS.NCELL, dtype=np.int8)
    best_val, best_a = None, None
    n_base_legal = n_reach = 0
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = FS._expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            n_base_legal += 1
            p = lookup.get((var, cc))
            if p is None or not p["reachable"]:
                continue
            n_reach += 1
            val = RS._root_value(c1, v1, nv, cells, na, nb, topk2,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            val -= ws * g_stranded(c1, v1)
            if best_val is None or val > best_val:
                best_val, best_a = val, var * 8 + cc

    if best_a is None:
        out = choose_base32(col, vir, ca, cb, na, nb, ws=ws, topk2=topk2)
        out["fallback_unreachable"] = True
        out["n_base_legal"] = n_base_legal
        out["n_reach"] = n_reach
        return out
    return {"kind": "base", "action": best_a, "val": best_val,
            "n_base_legal": n_base_legal, "n_reach": n_reach,
            "fallback_unreachable": False}


# ------------------------------------------------------------------------ reachfull
def choose_reachfull(fb, col, vir, ca, cb, na, nb, ws=WS, theta=THETA_FULL,
                     topk2=TOPK2):
    """ALL BFS-reachable rests (straight AND tuck-class) as root candidates,
    same root value as base32/reach32. Tuck-class candidates are gated by the
    tuck_v3 ship pattern: a tuck only wins if it beats the best of the 32 base
    candidates (each scored with the SAME ws-adjusted value) by >= theta --
    root_search.choose_root_with_tucks' own margin gate, reused verbatim in
    shape (not import, since this eval also carries the strand20 g_stranded
    term that RS.choose_root_with_tucks does not apply)."""
    L = _lazy()
    FX, FS, RS, TE, g_stranded = L["FX"], L["FS"], L["RS"], L["TE"], L["g_stranded"]
    w, fl = L["w"], L["fl"]

    c1 = np.empty(FS.NCELL, dtype=np.int8)
    v1 = np.empty(FS.NCELL, dtype=np.int8)
    best_val, best = None, None
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = FS._expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, topk2,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            val -= ws * g_stranded(c1, v1)
            if best_val is None or val > best_val:
                best_val = val
                best = {"kind": "base", "action": var * 8 + cc, "val": val}
    best_base_val = best_val

    tuck_cands = [p for p in TE.enumerate(fb, ca, cb, mode="free")
                  if p["is_tuck"] and p["reachable"]]
    n_legal = 0
    for p in tuck_cands:
        r0, c0, r1, c1_ = p["cells"]
        col0, col1 = p["colors"]
        nv, cells = RS._expand_core_at(col, vir, r0, c0, r1, c1_, col0, col1, c1, v1)
        val = RS._root_value(c1, v1, nv, cells, na, nb, topk2,
                             FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
        val -= ws * g_stranded(c1, v1)
        n_legal += 1
        if best_base_val is not None and val < best_base_val + theta:
            continue                      # THE MARGIN GATE, same shape as
                                           # root_search.choose_root_with_tucks
        if best_val is None or val > best_val:
            best_val = val
            best = {"kind": "tuck", "placement": p, "ca": col0, "cb": col1, "val": val,
                    "margin": val - best_base_val if best_base_val is not None else None}

    best["n_tuck_cands"] = len(tuck_cands)
    best["n_tuck_legal"] = n_legal
    best["best_base_val"] = best_base_val
    return best


# ============================================================================
# ITERATION 2 (REACH_ROOT_VERDICT.md "## ITERATION 2", task #60): the
# prescribed fix (reachfull2) + the time-budget extension (reach32t,
# reachfull2t). `choose_base32`/`choose_reach32`/`choose_reachfull` above are
# left byte-for-byte UNTOUCHED so the pre-fix arms (already characterized in
# REACH_ROOT_CLEAN/BURSTY/M3CASE.md) stay exactly reproducible for the
# before/after comparison this iteration's acceptance check needs.
# ============================================================================
def _scored_base_candidates(fb, col, vir, ca, cb, na, nb, ws, topk2):
    """All <=32 legal straight-drop candidates, each scored with the shared
    root value and tagged with its TE reachability + resting (row, col)
    geometry. One enumeration pass serves reach32t and reachfull2/reachfull2t's
    base branch -- `choose_base32` and (pre-fix) `choose_reachfull` keep their
    own original loops untouched (see module note above), so this is new code,
    not a refactor of anything already characterized."""
    L = _lazy()
    FX, FS, RS, g_stranded = L["FX"], L["FS"], L["RS"], L["g_stranded"]
    w, fl = L["w"], L["fl"]
    lookup = _te_straight_lookup(fb, ca, cb)
    c1 = np.empty(FS.NCELL, dtype=np.int8)
    v1 = np.empty(FS.NCELL, dtype=np.int8)
    out = []
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = FS._expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, topk2,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            val -= ws * g_stranded(c1, v1)
            p = lookup.get((var, cc))
            reachable = bool(p is not None and p["reachable"])
            row = p["row"] if p is not None else None
            within_budget = bool(reachable and row is not None
                                 and _within_time_budget(row, cc))
            out.append({"action": var * 8 + cc, "val": val, "reachable": reachable,
                        "row": row, "col": cc, "within_budget": within_budget})
    return out


def _tuck_branch_pick(fb, col, vir, ca, cb, na, nb, ws, theta, topk2,
                      best_base_val, best_out):
    """The theta-gated tuck-candidate scoring loop, factored out so
    `choose_reachfull2` and `choose_reachfull2t` share ONE copy instead of
    duplicating eval arithmetic three times (a correctness risk this task
    can't afford) -- same shape as `choose_reachfull`'s own inline loop,
    which is left untouched, not imported from here."""
    L = _lazy()
    TE, g_stranded, RS, FX = L["TE"], L["g_stranded"], L["RS"], L["FX"]
    w, fl = L["w"], L["fl"]
    c1 = np.empty(L["FS"].NCELL, dtype=np.int8)
    v1 = np.empty(L["FS"].NCELL, dtype=np.int8)
    tuck_cands = [p for p in TE.enumerate(fb, ca, cb, mode="free")
                  if p["is_tuck"] and p["reachable"]]
    n_legal = 0
    best_val, best_pick = best_base_val, best_out
    for p in tuck_cands:
        r0, c0, r1, c1_ = p["cells"]
        col0, col1 = p["colors"]
        nv, cells = RS._expand_core_at(col, vir, r0, c0, r1, c1_, col0, col1, c1, v1)
        val = RS._root_value(c1, v1, nv, cells, na, nb, topk2,
                             FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
        val -= ws * g_stranded(c1, v1)
        n_legal += 1
        if val < best_base_val + theta:
            continue                      # THE MARGIN GATE, same shape as
                                           # root_search.choose_root_with_tucks
        if best_val is None or val > best_val:
            best_val = val
            best_pick = {"kind": "tuck", "placement": p, "ca": col0, "cb": col1,
                        "val": val, "margin": val - best_base_val}
    best_pick["n_tuck_cands"] = len(tuck_cands)
    best_pick["n_tuck_legal"] = n_legal
    best_pick["best_base_val"] = best_base_val
    return best_pick


# --------------------------------------------------------------------- reachfull2
def choose_reachfull2(fb, col, vir, ca, cb, na, nb, ws=WS, theta=THETA_FULL,
                      topk2=TOPK2):
    """THE PRESCRIBED FIX (REACH_ROOT_VERDICT.md #4.1). `choose_reachfull`'s
    base-candidate loop is unfiltered and silently inherits `base32`'s
    physically-unreachable argmax (M3CASE.md finding 4: 4/6 death-board
    commits). This is `choose_reachfull` with the SAME tuck branch (identical
    theta-margin logic, factored into `_tuck_branch_pick`) but a base branch
    reachability-filtered exactly like `reach32` -- i.e. reach32's
    filtered-32 UNION the BFS tuck-reachable set, per the verdict's own
    recommendation. 2-tier fallback, same convention as `choose_reach32`:
    reachable candidates preferred; if the filter empties the set entirely
    (should-not-happen in play), fall back to the unfiltered best."""
    cands = _scored_base_candidates(fb, col, vir, ca, cb, na, nb, ws, topk2)
    reach_cands = [c for c in cands if c["reachable"]]
    n_base_legal, n_reach = len(cands), len(reach_cands)
    pool = reach_cands if reach_cands else cands
    fallback_unreachable = not bool(reach_cands)

    best = max(pool, key=lambda c: c["val"])
    best_base_val = best["val"]
    best_out = {"kind": "base", "action": best["action"], "val": best_base_val}

    best_pick = _tuck_branch_pick(fb, col, vir, ca, cb, na, nb, ws, theta, topk2,
                                  best_base_val, best_out)
    best_pick["n_base_legal"] = n_base_legal
    best_pick["n_reach"] = n_reach
    best_pick["fallback_unreachable"] = fallback_unreachable
    return best_pick


# --------------------------------------------------------------------- reach32t
def choose_reach32t(fb, col, vir, ca, cb, na, nb, ws=WS, topk2=TOPK2):
    """reach32, additionally filtered by the DRDISTGATE time budget
    (extension, REACH_ROOT_VERDICT.md ITERATION 2 point 2): a candidate
    survives only if hooks_needed(edges to its column) <= hooks_available
    (the DIST_TABLE budget implied by its own resting row, i.e. the
    spawn-time fall height of that column region -- see `_within_time_
    budget`). 3-tier fallback, each tier a strict superset of the next, so
    this NEVER chooses a placement reach32 itself would reject as
    BFS-unreachable:
      1. reachable AND within the time budget (preferred)
      2. reachable, but the time budget is empty for every reachable
         candidate -- falls back to reach32's own choice, ignoring timing
      3. nothing reachable at all (should-not-happen in play) -- falls back
         to unfiltered base32, same convention as `choose_reach32`
    """
    cands = _scored_base_candidates(fb, col, vir, ca, cb, na, nb, ws, topk2)
    reach_cands = [c for c in cands if c["reachable"]]
    timed_cands = [c for c in reach_cands if c["within_budget"]]
    n_base_legal, n_reach = len(cands), len(reach_cands)
    n_within_budget = len(timed_cands)

    if timed_cands:
        best = max(timed_cands, key=lambda c: c["val"])
        return {"kind": "base", "action": best["action"], "val": best["val"],
                "n_base_legal": n_base_legal, "n_reach": n_reach,
                "n_within_budget": n_within_budget,
                "fallback_time": False, "fallback_unreachable": False}
    if reach_cands:
        best = max(reach_cands, key=lambda c: c["val"])
        return {"kind": "base", "action": best["action"], "val": best["val"],
                "n_base_legal": n_base_legal, "n_reach": n_reach,
                "n_within_budget": n_within_budget,
                "fallback_time": True, "fallback_unreachable": False}
    out = choose_base32(col, vir, ca, cb, na, nb, ws=ws, topk2=topk2)
    out["n_base_legal"] = n_base_legal
    out["n_reach"] = n_reach
    out["n_within_budget"] = n_within_budget
    out["fallback_time"] = True
    out["fallback_unreachable"] = True
    return out


# ------------------------------------------------------------------- reachfull2t
def choose_reachfull2t(fb, col, vir, ca, cb, na, nb, ws=WS, theta=THETA_FULL,
                       topk2=TOPK2):
    """reachfull2, with its base branch ALSO intersected with the DRDISTGATE
    time budget ("reachfullt" in the task's naming, ITERATION 2 point 2).
    Scoped to the base branch only, per the task's own prescription: tuck
    candidates execute through a different mechanism (the shipped single-
    switch DRTUCK executor, not a multi-edge DAS traverse), and this
    arithmetic is specifically about DAS column-edge travel time, so it is
    not re-applied to the tuck branch here. Same 3-tier base-branch fallback
    as `choose_reach32t`."""
    cands = _scored_base_candidates(fb, col, vir, ca, cb, na, nb, ws, topk2)
    reach_cands = [c for c in cands if c["reachable"]]
    timed_cands = [c for c in reach_cands if c["within_budget"]]
    n_base_legal, n_reach = len(cands), len(reach_cands)
    n_within_budget = len(timed_cands)

    if timed_cands:
        pool, fallback_time, fallback_unreachable = timed_cands, False, False
    elif reach_cands:
        pool, fallback_time, fallback_unreachable = reach_cands, True, False
    else:
        pool, fallback_time, fallback_unreachable = cands, True, True

    best = max(pool, key=lambda c: c["val"])
    best_base_val = best["val"]
    best_out = {"kind": "base", "action": best["action"], "val": best_base_val}

    best_pick = _tuck_branch_pick(fb, col, vir, ca, cb, na, nb, ws, theta, topk2,
                                  best_base_val, best_out)
    best_pick["n_base_legal"] = n_base_legal
    best_pick["n_reach"] = n_reach
    best_pick["n_within_budget"] = n_within_budget
    best_pick["fallback_time"] = fallback_time
    best_pick["fallback_unreachable"] = fallback_unreachable
    return best_pick


CHOOSERS = {"base32": choose_base32, "reach32": choose_reach32, "reachfull": choose_reachfull,
            "reach32t": choose_reach32t, "reachfull2": choose_reachfull2,
            "reachfull2t": choose_reachfull2t}


def choose(mode, fb, col, vir, ca, cb, na, nb, ws=WS, theta=THETA_FULL, topk2=TOPK2):
    """Dispatch by mode name. base32 doesn't need `fb`/`theta`; reach32/
    reach32t don't need `theta`; accepted uniformly so callers (the A/B
    runner) don't branch."""
    if mode == "base32":
        return choose_base32(col, vir, ca, cb, na, nb, ws=ws, topk2=topk2)
    if mode == "reach32":
        return choose_reach32(fb, col, vir, ca, cb, na, nb, ws=ws, topk2=topk2)
    if mode == "reachfull":
        return choose_reachfull(fb, col, vir, ca, cb, na, nb, ws=ws, theta=theta, topk2=topk2)
    if mode == "reach32t":
        return choose_reach32t(fb, col, vir, ca, cb, na, nb, ws=ws, topk2=topk2)
    if mode == "reachfull2":
        return choose_reachfull2(fb, col, vir, ca, cb, na, nb, ws=ws, theta=theta, topk2=topk2)
    if mode == "reachfull2t":
        return choose_reachfull2t(fb, col, vir, ca, cb, na, nb, ws=ws, theta=theta, topk2=topk2)
    raise ValueError(f"unknown mode {mode!r}, want one of {MODES}")


# ============================================================================
# selftests
# ============================================================================
def _rand_board(rnd, max_height=16, holes=True):
    """Column-height (+ optional punched holes) random board, spawn cols
    forced clear. Same generator shape as root_search.equivalence_selftest /
    tuck_enum._rand_board."""
    L = _lazy()
    NCELL = L["FS"].NCELL
    grid = [0] * NCELL
    for c in range(8):
        h = rnd.randrange(0, max_height + 1)
        for r in range(16 - h, 16):
            grid[r * 8 + c] = rnd.randint(1, 3)
    if holes:
        for _ in range(rnd.randrange(0, 16)):
            grid[rnd.randrange(1, 16) * 8 + rnd.randrange(0, 8)] = 0
    grid[3] = grid[4] = 0
    return grid


def _selftest_base32_matches_shipped(n_games=8, samples_per_game=25, seed=20260805):
    """base32 must reproduce ab47.py::_choose_base(wt=0, ws=20) bit-for-bit.
    Boards are genuine L11 boards: real FaithfulDrMarioEnv(level=11) games,
    driven by the REFERENCE (ab47._choose_base) decisions so the trajectory
    is independent of this file's code -- only the offline re-decision on
    each snapshot is compared. Collects up to n_games*samples_per_game board
    snapshots (target 200 at the default 8x25)."""
    sys.path.insert(0, HERE) if HERE not in sys.path else None
    import ab47
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    L = _lazy()
    FB, RS = L["FB"], L["RS"]
    w, fl = L["w"], L["fl"]

    mism_action = mism_val = checked = 0
    for seed_i in range(n_games):
        env = FaithfulDrMarioEnv(level=11, seed=seed * 1000 + seed_i, max_pills=300)
        env.reset()
        NesPillSource(seed=seed * 1000 + seed_i).attach(env)
        env.cur = env._rand_pill()
        env.nxt = env._rand_pill()
        n_taken = 0
        for _ in range(300):
            if n_taken >= samples_per_game:
                break
            fb = FB.from_board(env.board)
            if env.board.virus_count() == 0:
                break
            col, vir = RS.board_flat_from_fb(fb)
            ca, cb, na, nb = int(env.cur.a), int(env.cur.b), int(env.nxt.a), int(env.nxt.b)

            ref_a, ref_c1 = ab47._choose_base(col, vir, ca, cb, na, nb, w, fl, 0, WS)
            mine = choose_base32(col, vir, ca, cb, na, nb, ws=WS)
            checked += 1
            n_taken += 1
            if ref_a is None or mine["action"] != ref_a:
                mism_action += 1
            else:
                # value cross-check: re-derive ref's value the same way ab47 would
                var, cc = ref_a // 8, ref_a % 8
                from fast_sim_x import _expand_core, NCELL
                import numpy as _np
                c1r = _np.empty(NCELL, dtype=_np.int8)
                v1r = _np.empty(NCELL, dtype=_np.int8)
                ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1r, v1r)
                ref_val = RS._root_value(c1r, v1r, nv, cells, na, nb, TOPK2,
                                         L["FX"]._W_EXCAV_SHIP, L["FX"]._W_HANG_SHIP, w, fl)
                ref_val -= WS * L["g_stranded"](c1r, v1r)
                if abs(float(ref_val) - float(mine["val"])) > 1e-6:
                    mism_val += 1

            if ref_a is None:
                break
            _, _, term, trunc, info = env.step(int(ref_a))
            if term or trunc:
                break
    ok = checked > 0 and mism_action == 0 and mism_val == 0
    return {"name": "base32_matches_shipped", "checked": checked,
            "mism_action": mism_action, "mism_val": mism_val, "pass": ok}


def _selftest_reach32_eq_base32_open_board(n_boards=50, seed=20260805):
    """On early-game boards (max column height <= 6, NO holes -- so nothing
    can overhang anything and no column can be filled to row 0) reach32 must
    equal base32 EXACTLY: every straight drop is trivially BFS-reachable when
    there is nothing to wall it off, so the reachability filter removes
    nothing and the two argmaxes (same candidate order, same tie-break) must
    coincide action-for-action."""
    L = _lazy()
    FB = L["FB"]
    rnd = random.Random(seed)
    mism = 0
    checked = 0
    for _ in range(n_boards):
        grid = _rand_board(rnd, max_height=6, holes=False)
        fb = FB(grid)
        col, vir = L["RS"].board_flat_from_fb(fb)
        ca, cb = rnd.randint(1, 3), rnd.randint(1, 3)
        na, nb = rnd.randint(1, 3), rnd.randint(1, 3)
        b = choose_base32(col, vir, ca, cb, na, nb, ws=WS)
        r = choose_reach32(fb, col, vir, ca, cb, na, nb, ws=WS)
        checked += 1
        if b["action"] != r["action"] or r.get("n_base_legal") != r.get("n_reach"):
            mism += 1
    ok = checked == n_boards and mism == 0
    return {"name": "reach32_eq_base32_open_board", "boards": checked,
            "mismatches": mism, "pass": ok}


def _selftest_reachfull2_eq_reachfull_open_board(n_boards=50, seed=20260805):
    """On the same open boards `_selftest_reach32_eq_base32_open_board` uses
    (h<=6, no holes -- nothing to wall off), reachfull2 must equal (pre-fix)
    reachfull EXACTLY: the reachability filter added to reachfull2's base
    branch removes nothing when nothing is unreachable, so the fix must be a
    no-op here -- a regression check that it doesn't perturb behaviour off
    the board shape it targets."""
    L = _lazy()
    FB = L["FB"]
    rnd = random.Random(seed)
    mism = 0
    checked = 0
    for _ in range(n_boards):
        grid = _rand_board(rnd, max_height=6, holes=False)
        fb = FB(grid)
        col, vir = L["RS"].board_flat_from_fb(fb)
        ca, cb = rnd.randint(1, 3), rnd.randint(1, 3)
        na, nb = rnd.randint(1, 3), rnd.randint(1, 3)
        a = choose_reachfull(fb, col, vir, ca, cb, na, nb, ws=WS)
        b = choose_reachfull2(fb, col, vir, ca, cb, na, nb, ws=WS)
        checked += 1
        a_key = (a["kind"], a.get("action"), a["placement"]["cells"] if a["kind"] == "tuck" else None)
        b_key = (b["kind"], b.get("action"), b["placement"]["cells"] if b["kind"] == "tuck" else None)
        if a_key != b_key or abs(a["val"] - b["val"]) > 1e-6:
            mism += 1
    ok = checked == n_boards and mism == 0
    return {"name": "reachfull2_eq_reachfull_open_board", "boards": checked,
            "mismatches": mism, "pass": ok}


def _selftest_reachfull2_never_unreachable_base(n_boards=1200, seed=20260805, want_cases=20):
    """THE DEFECT TEST (house rule: simulate the fault, assert the outcome,
    not just the guard). Sweeps high, holed random boards (the M3 board
    shape -- clean-board selftests never exercise this path by construction)
    until >= `want_cases` boards are found where base32's OWN argmax is
    BFS-unreachable -- the exact defect REACH_ROOT_M3CASE.md caught
    (pre-fix) reachfull silently inheriting on 4/6 real death-board commits.
    On every such board, reachfull2 must NOT pick an unreachable base
    placement: either it picks a tuck, or its base pick's (var, col) is
    itself BFS-reachable."""
    L = _lazy()
    FB = L["FB"]
    rnd = random.Random(seed)
    cases = bad = tries = 0
    while cases < want_cases and tries < n_boards:
        tries += 1
        grid = _rand_board(rnd, max_height=16, holes=True)
        fb = FB(grid)
        col, vir = L["RS"].board_flat_from_fb(fb)
        ca, cb = rnd.randint(1, 3), rnd.randint(1, 3)
        na, nb = rnd.randint(1, 3), rnd.randint(1, 3)
        b32 = choose_base32(col, vir, ca, cb, na, nb, ws=WS)
        if b32["action"] is None:
            continue
        var, cc = b32["action"] // 8, b32["action"] % 8
        lookup = _te_straight_lookup(fb, ca, cb)
        p = lookup.get((var, cc))
        if bool(p is not None and p["reachable"]):
            continue          # not a defect-triggering board; base32 was fine here
        cases += 1
        rf2 = choose_reachfull2(fb, col, vir, ca, cb, na, nb, ws=WS)
        if rf2["kind"] == "tuck":
            continue          # fine: didn't pick a base placement at all
        rvar, rcc = rf2["action"] // 8, rf2["action"] % 8
        rp = lookup.get((rvar, rcc))
        if not bool(rp is not None and rp["reachable"]):
            bad += 1
    ok = cases > 0 and bad == 0
    return {"name": "reachfull2_never_unreachable_base", "boards_tried": tries,
            "unreachable_argmax_cases": cases, "bad": bad, "pass": ok}


def _selftest_dist_table_matches_driver():
    """Cross-check `_dist_table_budget_edges`/DIST_DASEDGE/DIST_GRAVROW
    against the ACTUAL driver artifact (dr-mario-mods-wt/driver-nav/
    patch_cartridge_copro.py), loaded live by file path -- a byte comparison
    against the same DIST_TABLE object CART_FIX_REPORT.md section 7 and
    tests/test_task49_distgate.py both test, not a re-typed formula. Also
    catches silent drift from the STALE 32/26 pair CART_FIX_REPORT.md
    section 7's prose quotes (superseded the same day by a silicon
    remeasurement -- see this file's DIST_DASEDGE/DIST_GRAVROW comment)."""
    driver_dir = "/home/struktured/projects/dr-mario-mods-wt/driver-nav"
    driver_path = os.path.join(driver_dir, "patch_cartridge_copro.py")
    try:
        import importlib.util
        if driver_dir not in sys.path:   # patch_cartridge_copro.py imports a
            sys.path.insert(0, driver_dir)   # sibling module (patch_vs_cpu)
        spec = importlib.util.spec_from_file_location(
            "_patch_cartridge_copro_distcheck", driver_path)
        PC = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(PC)
    except Exception as e:  # pragma: no cover -- environment-dependent, not a logic bug
        return {"name": "dist_table_matches_driver", "skipped": True,
                "reason": str(e), "pass": True}

    mism = []
    if int(PC.DIST_DASEDGE) != DIST_DASEDGE or int(PC.DIST_GRAVROW) != DIST_GRAVROW:
        mism.append(("constants", (int(PC.DIST_DASEDGE), int(PC.DIST_GRAVROW)),
                    (DIST_DASEDGE, DIST_GRAVROW)))
    for y in range(PC.DIST_TABLE_LEN):
        want, got = PC.DIST_TABLE[y], _dist_table_budget_edges(y)
        if want != got:
            mism.append((y, want, got))
    ok = not mism
    return {"name": "dist_table_matches_driver", "skipped": False,
            "driver_constants": (int(PC.DIST_DASEDGE), int(PC.DIST_GRAVROW)),
            "table_len": PC.DIST_TABLE_LEN, "mismatches": mism, "pass": ok}


def run_selftests():
    r1 = _selftest_base32_matches_shipped()
    print(f"[1] base32 vs shipped (ab47._choose_base wt=0 ws={WS}): "
          f"{r1['checked']} boards, action mismatches {r1['mism_action']}, "
          f"value mismatches {r1['mism_val']}  -> {'PASS' if r1['pass'] else 'FAIL'}")
    r2 = _selftest_reach32_eq_base32_open_board()
    print(f"[2] reach32 == base32 on open boards (h<=6, no holes): "
          f"{r2['boards']}/{r2['boards']} boards, mismatches {r2['mismatches']} "
          f"-> {'PASS' if r2['pass'] else 'FAIL'}")
    r3 = _selftest_reachfull2_eq_reachfull_open_board()
    print(f"[3] reachfull2 == reachfull on open boards (h<=6, no holes): "
          f"{r3['boards']}/{r3['boards']} boards, mismatches {r3['mismatches']} "
          f"-> {'PASS' if r3['pass'] else 'FAIL'}")
    r4 = _selftest_reachfull2_never_unreachable_base()
    print(f"[4] DEFECT TEST: reachfull2 never inherits an unreachable base32 argmax: "
          f"{r4['unreachable_argmax_cases']} unreachable-argmax cases found in "
          f"{r4['boards_tried']} boards tried, bad={r4['bad']} "
          f"-> {'PASS' if r4['pass'] else 'FAIL'}")
    r5 = _selftest_dist_table_matches_driver()
    if r5["skipped"]:
        print(f"[5] DIST_TABLE vs live driver artifact: SKIPPED ({r5['reason']})")
    else:
        print(f"[5] DIST_TABLE vs live driver artifact "
              f"(DIST_DASEDGE={r5['driver_constants'][0]}, DIST_GRAVROW={r5['driver_constants'][1]}): "
              f"{r5['table_len']} entries, mismatches {len(r5['mismatches'])} "
              f"-> {'PASS' if r5['pass'] else 'FAIL'}")
    return r1, r2, r3, r4, r5


if __name__ == "__main__":
    r1, r2, r3, r4, r5 = run_selftests()
    ok = r1["pass"] and r2["pass"] and r3["pass"] and r4["pass"] and r5["pass"]
    print("\nSELF-TEST " + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)
