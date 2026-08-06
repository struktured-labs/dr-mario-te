#!/usr/bin/env python3
"""The champion as an ORACLE: a pure, memoized function
    champion_move(board_key, cur_pill, next_pill) -> action

This is the shipped strand20 decide path, byte-for-byte the same computation as
eval47/ab47.py::_choose_base with (wt=0, ws=20):
  leaf   = fast_rtl_x.variant("winner")
  root   = RS._root_value(..., topk2=8, W_EXCAV_SHIP, W_HANG_SHIP)
  minus  = 20 * terms47.g_stranded(child_col, child_vir)   [root-only, ply-1]

WHY AN ORACLE.  The champion is deterministic and depth-3.  Its reply to any
(board, cur, next) is therefore a computable function, not a strategic choice.
An adversary with unbounded think time faces a SINGLE-AGENT planning problem,
branching only on its own moves, with the champion's reply computed exactly at
each node.  That makes depth 8-12 tractable.

STATE TRANSITION.  The champion's own leaf uses cap-1 compact gravity (that is
what the RTL does, and we must mirror it to reproduce its CHOICE).  But the
world advances on the LINK-FAITHFUL board (drmario.faithful_game), which has
real cascades and body-wise gravity -- that is what the game does.  Keeping the
two distinct is deliberate: the gap between them is one of the things the
champion can be wrong about.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/eval47", QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

ROWS, COLS, NCELL = 16, 8, 128
WS_STRANDED = 20          # shipped strand20 dose
WT_TOWER = 0
H0 = 8

_W = {}                   # lazily-initialised champion weights
_MEMO = {}                # (board_key, ca, cb, na, nb) -> action
_STATS = {"calls": 0, "hits": 0}


def init_champion():
    """Load + JIT-warm the champion. Safe to call repeatedly; must be called in
    every worker process (numba state is per-process)."""
    if _W:
        return
    import fast_rtl_x as FX
    from terms47 import g_tower, g_stranded
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    z = np.zeros(NCELL, dtype=np.int8)
    g_tower(z, z, H0)
    g_stranded(z, z)
    _W["w"], _W["fl"] = w, fl


# ------------------------------------------------------------------ the oracle
def _choose_base_raw(col, vir, ca, cb, na, nb):
    """EXACT copy of eval47/ab47.py::_choose_base with wt=0, ws=WS_STRANDED.
    Returns (action, child_col, child_vir, best_val) or (None, ...) if no legal
    placement exists at all."""
    import fast_rtl_x as FX
    import root_search as RS
    from fast_sim_x import _expand_core
    from terms47 import g_stranded

    w, fl = _W["w"], _W["fl"]
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_val = best_a = best_c1 = best_v1 = None
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(COLS):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            val -= WS_STRANDED * g_stranded(c1, v1)
            if best_val is None or val > best_val:
                best_val, best_a = val, var * 8 + cc
                best_c1, best_v1 = c1.copy(), v1.copy()
    return best_a, best_c1, best_v1, best_val


def champion_move(col, vir, ca, cb, na, nb):
    """Memoized champion reply. col/vir are int8[128] (row-major, 1-based
    colours). Returns the action int (var*8 + column) or None."""
    key = (col.tobytes(), vir.tobytes(), ca, cb, na, nb)
    _STATS["calls"] += 1
    hit = _MEMO.get(key, _MISS)
    if hit is not _MISS:
        _STATS["hits"] += 1
        return hit
    a, _c1, _v1, _val = _choose_base_raw(col, vir, ca, cb, na, nb)
    _MEMO[key] = a
    return a


_MISS = object()


def memo_stats():
    c, h = _STATS["calls"], _STATS["hits"]
    return {"calls": c, "hits": h, "hit_rate": (h / c if c else 0.0),
            "entries": len(_MEMO)}


def memo_clear():
    _MEMO.clear()
    _STATS.update(calls=0, hits=0)


# ------------------------------------------------------- world state (faithful)
def board_to_flat(b):
    """FaithfulBoard -> (col int8[128], vir int8[128]) as the champion sees it."""
    col = b.color.reshape(-1).astype(np.int8)
    vir = b.is_virus.reshape(-1).astype(np.int8)
    return col, vir


def board_key(b):
    """Hashable identity of a faithful board INCLUDING links (links change the
    physics of the next cascade, so two boards with equal colours but different
    links are genuinely different states)."""
    return (b.color.tobytes(), b.is_virus.tobytes(), b.link.tobytes())


def apply_action(b, action, ca, cb):
    """Apply an action to a FaithfulBoard IN PLACE (link-faithful, cascading).
    Returns (ok, cleared, viruses_cleared, chain)."""
    from drmario.faithful_game import Pill, ORIENT_H, ORIENT_V
    var, cc = action // COLS, action % COLS
    # ab47/_expand_core variant space: FX._VAR_OF_O4 maps o4 -> var.
    # var 0/1 = HORIZONTAL (a-first / b-first), var 2/3 = VERTICAL.
    if var == 0:
        orient, pill = ORIENT_H, Pill(ca, cb)
    elif var == 1:
        orient, pill = ORIENT_H, Pill(cb, ca)
    elif var == 2:
        orient, pill = ORIENT_V, Pill(ca, cb)
    else:
        orient, pill = ORIENT_V, Pill(cb, ca)
    if not b.place_pill(pill, orient, cc):
        return (False, 0, 0, 0)
    cleared, vir_cleared, chain = b.resolve()
    return (True, cleared, vir_cleared, chain)


def legal_actions(b, ca, cb):
    """Actions with a resting position on the faithful board."""
    from drmario.faithful_game import Pill, ORIENT_H, ORIENT_V
    out = []
    for var in range(4):
        if var == 0:
            orient, pill = ORIENT_H, Pill(ca, cb)
        elif var == 1:
            orient, pill = ORIENT_H, Pill(cb, ca)
        elif var == 2:
            orient, pill = ORIENT_V, Pill(ca, cb)
        else:
            orient, pill = ORIENT_V, Pill(cb, ca)
        for cc in range(COLS):
            if b.resting_position(pill, orient, cc) is not None:
                out.append(var * COLS + cc)
    return out


def new_board(level, seed):
    """A fresh level board, identical to what FaithfulDrMarioEnv.reset builds."""
    from drmario.faithful_game import FaithfulBoard
    b = FaithfulBoard(ROWS, COLS, rng=np.random.default_rng(seed))
    b.place_viruses(level)
    return b


def board_from_flat(col, vir, link=None):
    """(col, vir[, link]) flat arrays -> FaithfulBoard. When link is omitted the
    links are INFERRED as all-singletons, which is the conservative reading of a
    recovered/observed board (we cannot see links on a screenshot)."""
    from drmario.faithful_game import FaithfulBoard
    b = FaithfulBoard(ROWS, COLS, rng=np.random.default_rng(0))
    b.color = np.asarray(col, dtype=np.int8).reshape(ROWS, COLS).copy()
    b.is_virus = np.asarray(vir, dtype=bool).reshape(ROWS, COLS).copy()
    if link is None:
        b.link = np.zeros((ROWS, COLS), dtype=np.int8)
    else:
        b.link = np.asarray(link, dtype=np.int8).reshape(ROWS, COLS).copy()
    return b


def ascii_board(b):
    return b.ascii()


PILLS = [(a, c) for a in (1, 2, 3) for c in (1, 2, 3)]   # 9 unordered-ish pills
