#!/usr/bin/env python3
"""Compact hand-built feature set for the off-policy learned adversary's value
model: P(champion dies within N pills | state, candidate action). Per team-lead's
spec: board heights, holes, spawn-lane congestion, garbage-in-flight, opponent
virus count -- plus a couple of extras this project's own conventions make free
(chain depth of the candidate clear, own virus count, since the adversary has to
survive on its OWN virus-filled board too, not just attack).

ONE HONEST GAP, stated once here rather than re-discovered later: "garbage in
flight" (the exact size of an attack banked and about to land) is NOT observable
by any decider in vs_harness.play_match by construction -- deciders see
(board, cur, nxt, opp_board) only, never the internal `store[]` accumulator
(vs_harness.py's play_match loop). That matches the real ROM: a player gets no
advance readout of the exact incoming attack size, only the fact of having
attacked before. So "garbage in flight" here is approximated by two RUNNING
COUNTERS the decider itself maintains across a game (own attacks sent so far,
own attacks received so far) -- observable-in-principle context, not omniscient
lookahead. See RunningAttackCounters below.

Board convention throughout: int8[128] col/vir, row-major idx=r*8+c, row 0 = top,
colours 1-based, exactly root_search.board_flat_from_fb / fast_rtl_x.board_flat.
"""
from __future__ import annotations

import numpy as np
from numba import njit, int8, int64

ROWS, COLS, NCELL = 16, 8, 128

FEATURE_NAMES = [
    "own_maxh", "own_avgh", "own_spawnh", "own_holes", "own_virus",
    "own_cells_cleared", "own_chain_depth",
    "opp_maxh", "opp_avgh", "opp_spawnh", "opp_holes", "opp_virus",
    "atk_sent_running", "atk_recv_running", "ply_frac",
]
N_FEATURES = len(FEATURE_NAMES)


@njit(cache=True)
def _col_stats(col):
    """(maxh, avgh, spawnh, holes) for one board. height = cells above the floor
    in that column (16 - topmost-occupied-row), 0 for an empty column. A hole is
    an EMPTY cell strictly below the topmost occupied cell in its column (the
    standard Tetris-stack definition) -- independent of virus/pill distinction,
    since an empty cell under ANY material is equally unreachable from above."""
    heights = np.zeros(COLS, dtype=int64)
    holes = int64(0)
    for c in range(COLS):
        top = ROWS
        for r in range(ROWS):
            if col[r * COLS + c] != 0:
                top = r
                break
        heights[c] = ROWS - top
        if top < ROWS:
            for r in range(top + 1, ROWS):
                if col[r * COLS + c] == 0:
                    holes += 1
    maxh = int64(0)
    tot = int64(0)
    for c in range(COLS):
        if heights[c] > maxh:
            maxh = heights[c]
        tot += heights[c]
    avgh = tot / COLS
    spawnh = heights[3] if heights[3] > heights[4] else heights[4]
    return maxh, avgh, spawnh, holes


@njit(int64(int8[:]), cache=True)
def _virus_count(vir):
    n = int64(0)
    for i in range(NCELL):
        if vir[i] != 0:
            n += 1
    return n


def extract(own_col, own_vir, opp_col, opp_vir, cells_cleared, chain_depth,
            atk_sent_running, atk_recv_running, ply, max_ply=300):
    """One feature row (np.float64[N_FEATURES]) -- see FEATURE_NAMES for order.
    own_* is the ADVERSARY's own resulting board (post-candidate-placement);
    opp_* is the CHAMPION's board at decision time (pre-move, the only opponent
    information actually available -- see module docstring)."""
    own_maxh, own_avgh, own_spawnh, own_holes = _col_stats(own_col)
    opp_maxh, opp_avgh, opp_spawnh, opp_holes = _col_stats(opp_col)
    own_v = _virus_count(own_vir)
    opp_v = _virus_count(opp_vir)
    return np.array([
        own_maxh, own_avgh, own_spawnh, own_holes, own_v,
        cells_cleared, chain_depth,
        opp_maxh, opp_avgh, opp_spawnh, opp_holes, opp_v,
        atk_sent_running, atk_recv_running, ply / max_ply,
    ], dtype=np.float64)


class RunningAttackCounters:
    """Per-decider, per-game state: how many attacks THIS side has sent/received
    so far. Reset at the start of every match. This is the observable-in-principle
    proxy for "garbage in flight" -- see module docstring for why the exact
    pending amount cannot be used."""
    __slots__ = ("sent", "received")

    def __init__(self):
        self.sent = 0
        self.received = 0

    def reset(self):
        self.sent = 0
        self.received = 0

    def note_attack_sent(self):
        self.sent += 1

    def note_attack_received(self):
        self.received += 1
