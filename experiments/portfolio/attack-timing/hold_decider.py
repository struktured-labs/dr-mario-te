#!/usr/bin/env python3
"""attack-timing thread: does DELAYING a ready clear until the opponent is
"vulnerable" (tall stack) beat cashing it in immediately?

HYPOTHESIS (falsifiable): the champion (strand180_20 = chain180 root reward +
g_stranded ws=20, cascade_stranded_x.StrandedChainD3Decider on
fast_rtl_x.variant("winner")) is purely greedy about WHEN it fires an attack --
it never holds a completed clear waiting for a better moment. A decider that
holds a ready clear for up to K pills, but only while the opponent's stack is
BELOW a height threshold (i.e. holds until they're either tall or the budget
runs out), should beat the greedy champion in VS play if attack TIMING is a
real lever the champion is leaving on the table.

CHAMPION UNDER TEST: cascade_stranded_x.StrandedChainD3Decider(w_chain=180,
ws=20) on variant("winner") weights -- h2h_vs.py's "strand180_20" arm, the
"NES_stomper180s20" shipped-to-silicon decision path (memory:
dr-mario-eval47-stranded-win). This is the VS-aware root search; g_stranded is
applied identically inside the HOLD wrapper (the base decider is untouched,
only WHICH of its candidate actions gets played on a given pill is gated).

MECHANISM, reusing the sanctioned ROM-true attack rule (do NOT rewrite it):
  1. Ask the champion for its top action `a0` on the real board.
  2. Determine whether `a0` FIRES AN ATTACK using the exact same primitives
     `vs_harness.probe_placement` uses: `attack.lines_per_step` (destructive
     resolve on a board clone) -> `rom_attack_rule.combo_from_cascade` ->
     `rom_attack_rule.attack_size` >= `ATTACK_SIZE_MIN`. (probe_placement
     itself needs an `env` object for `_decode`; deciders only see `board`,
     so `_decode_local` below is a byte-identical copy of
     `FaithfulDrMarioEnv._decode`, not a reimplementation of the attack rule.)
  3. If `a0` does not attack, or the opponent's tallest column is already at
     or above `threshold`, or the hold budget for this streak is exhausted:
     CASH IN -- play `a0`.
  4. Otherwise HOLD: enumerate the up to 32 legal root actions using the
     champion's OWN leaf-scoring primitive (`cascade_chain_x._leaf_chain` on
     `fast_rtl_x.variant("winner")` weights -- literally the same call the
     champion's root loop makes for its first ply), keep only actions that do
     NOT attack, and play the one with the highest first-ply leaf value.  If
     no non-attacking legal action exists, cash in.

This is a GREEDY-ON-BOARD-QUALITY hold policy, not a full re-run of the d3
search for every hold candidate -- deliberately cheap, since this is the
cheapest test that could kill the hypothesis. If it wins, the follow-up would
score alternatives with the full d3 value instead of the first-ply leaf.
"""
from __future__ import annotations
import sys, os

ROOT = "/home/struktured/projects/dr_mario_rl"
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src", ROOT + "/tmp/vs_aware"):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np

import fast_rtl_x as F
from fast_sim_x import NCELL
import cascade_chain_x as C
from cascade_chain_x import _base_scan, _leaf_chain, NBASE, NT
from cascade_link_x import board_flat
import cascade_stranded_x as S
from attack import lines_per_step
from rom_attack_rule import combo_from_cascade, attack_size, ATTACK_SIZE_MIN

ORIENT_H, ORIENT_V = 0, 1


def _decode_local(cur, action, cols=8):
    """Byte-identical copy of FaithfulDrMarioEnv._decode -- deciders only see
    `board`/`cur`, not the env object probe_placement needs, so this lets the
    hold wrapper call the SAME rom_attack_rule pipeline probe_placement uses
    without threading an env reference through vs_harness's decider contract."""
    variant = action // cols
    col = action % cols
    if variant == 0:
        return ORIENT_H, col, type(cur)(cur.a, cur.b)
    elif variant == 1:
        return ORIENT_H, col, type(cur)(cur.b, cur.a)
    elif variant == 2:
        return ORIENT_V, col, type(cur)(cur.a, cur.b)
    else:
        return ORIENT_V, col, type(cur)(cur.b, cur.a)


def would_attack(board, cur, action):
    """ROM-true: would playing `action` now release garbage? Same call chain as
    vs_harness.probe_placement (lines_per_step -> combo_from_cascade ->
    attack_size >= ATTACK_SIZE_MIN), just decoded locally (see _decode_local)."""
    orient, col, pill = _decode_local(cur, action)
    b = board.clone()
    if not b.place_pill(pill, orient, col):
        return False, 0
    steps = lines_per_step(b)
    combo = combo_from_cascade(steps)
    size = attack_size(combo)
    return size >= ATTACK_SIZE_MIN, size


def best_nonattacking(board, cur, nxt, w, fl, exclude=None):
    """Rank the legal root actions that do NOT attack by the champion's own
    first-ply leaf value (cascade_chain_x._leaf_chain on the SAME weights).
    Returns None if every legal action attacks."""
    col, vir = board_flat(board)
    lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
    base1 = np.empty(NBASE, dtype=np.int64)
    _base_scan(col, vir, fl, base1)
    terms = np.empty(NT, dtype=np.int64)
    mask = np.empty(NCELL, dtype=np.int8)
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    l1 = np.empty(NCELL, dtype=np.int8)
    best_a, best_v = None, None
    for o4 in range(4):
        var = int(F._VAR_OF_O4[o4])
        for cl in range(8):
            ok, nv, cells, leaf1, ch1 = _leaf_chain(col, vir, lnk, base1, var, cl,
                                                     int(cur.a), int(cur.b), w, fl,
                                                     c1, v1, l1, mask, terms, 0, False)
            if ok == 0:
                continue
            action = var * 8 + cl
            if action == exclude:
                continue
            attacks, _ = would_attack(board, cur, action)
            if attacks:
                continue
            if best_v is None or leaf1 > best_v:
                best_v, best_a = leaf1, action
    return best_a


class HoldingDecider:
    """Wraps a champion decider (board,cur,nxt)->action with an
    opponent-height-gated hold: `choose(board, cur, nxt, opp_board)`."""

    def __init__(self, base, threshold, K):
        self.base = base
        self.threshold = threshold
        self.K = int(K)
        self._hold = 0
        self.w = np.asarray(F.variant("winner")[0], dtype=np.float64)
        self.fl = np.asarray(F.variant("winner")[1], dtype=np.int32)
        self.stats = {"held": 0, "cashed_vulnerable": 0, "cashed_forced": 0,
                      "cashed_no_attack": 0, "cashed_no_alt": 0}

    def choose(self, board, cur, nxt, opp_board):
        a0 = self.base.choose(board, cur, nxt)
        if a0 is None or self.K == 0:
            return a0
        attacks, _ = would_attack(board, cur, a0)
        if not attacks:
            self._hold = 0
            self.stats["cashed_no_attack"] += 1
            return a0
        opp_h = int(opp_board.column_heights().max())
        if opp_h >= self.threshold:
            self._hold = 0
            self.stats["cashed_vulnerable"] += 1
            return a0
        if self._hold >= self.K:
            self._hold = 0
            self.stats["cashed_forced"] += 1
            return a0
        alt = best_nonattacking(board, cur, nxt, self.w, self.fl, exclude=a0)
        if alt is None:
            self._hold = 0
            self.stats["cashed_no_alt"] += 1
            return a0
        self._hold += 1
        self.stats["held"] += 1
        return alt


def make_champion(topk2=8):
    """The champion under test: strand180_20 on variant('winner')."""
    w, fl = F.variant("winner")
    return S.StrandedChainD3Decider(w, fl, topk2=topk2, maxpass=0, w_chain=180, ws=20)


def make_holder(threshold, K, topk2=8):
    return HoldingDecider(make_champion(topk2=topk2), threshold, K)


if __name__ == "__main__":
    # smoke: does the wrapper ever actually hold on a random board sequence?
    import fast_rtl_x as FX
    FX.warmup_delta(topk2=8)
    C.warmup_chain(topk2=8)
    h = make_holder(threshold=10, K=2)
    print("built HoldingDecider ok:", h.threshold, h.K)
