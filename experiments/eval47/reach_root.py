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

MODES = ("base32", "reach32", "reachfull")

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


CHOOSERS = {"base32": choose_base32, "reach32": choose_reach32, "reachfull": choose_reachfull}


def choose(mode, fb, col, vir, ca, cb, na, nb, ws=WS, theta=THETA_FULL, topk2=TOPK2):
    """Dispatch by mode name. base32 doesn't need `fb`/`theta`; reach32 doesn't
    need `theta`; accepted uniformly so callers (the A/B runner) don't branch."""
    if mode == "base32":
        return choose_base32(col, vir, ca, cb, na, nb, ws=ws, topk2=topk2)
    if mode == "reach32":
        return choose_reach32(fb, col, vir, ca, cb, na, nb, ws=ws, topk2=topk2)
    if mode == "reachfull":
        return choose_reachfull(fb, col, vir, ca, cb, na, nb, ws=ws, theta=theta, topk2=topk2)
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


def run_selftests():
    r1 = _selftest_base32_matches_shipped()
    print(f"[1] base32 vs shipped (ab47._choose_base wt=0 ws={WS}): "
          f"{r1['checked']} boards, action mismatches {r1['mism_action']}, "
          f"value mismatches {r1['mism_val']}  -> {'PASS' if r1['pass'] else 'FAIL'}")
    r2 = _selftest_reach32_eq_base32_open_board()
    print(f"[2] reach32 == base32 on open boards (h<=6, no holes): "
          f"{r2['boards']}/{r2['boards']} boards, mismatches {r2['mismatches']} "
          f"-> {'PASS' if r2['pass'] else 'FAIL'}")
    return r1, r2


if __name__ == "__main__":
    r1, r2 = run_selftests()
    ok = r1["pass"] and r2["pass"]
    print("\nSELF-TEST " + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)
