#!/usr/bin/env python3
"""THE HOLE POKER -- deep adversarial search against a deterministic, shallow
champion.

STRUCTURAL INSIGHT (the reason this is tractable at all).  The champion is
deterministic and depth-3.  Its reply to any position is a computable function.
So an adversary with unbounded think time does NOT face a minimax game -- it
faces a SINGLE-AGENT PLANNING PROBLEM in which the champion is an oracle.  We
branch only on the adversary's own choices and compute the champion's forced
reply exactly at every node.

SOLO MODE.  The adversary owns the pill stream.  State = (board, cur_pill);
the adversary's move is the pill that enters the "next" slot, which is both the
lookahead the champion sees now AND the pill it must place next turn (the
adversary is committed -- it cannot bluff a lookahead it will not deliver).
Goal = the champion tops out.

WHAT MAKES IT FAST: an ADMISSIBLE lower bound.  A topout needs row 0 of column
3 or 4 occupied; a no-legal-move needs every column filled to row <=1.  A single
placement adds at most 2 cells to one column, and clears/gravity only ever RAISE
the top-occupied row.  So

    h(state) = ceil((min(top_occ[3], top_occ[4]) - 1) / 2)

is a true lower bound on the number of remaining placements before any death
condition can hold.  IDA* with this h prunes without spending a single oracle
call on the pruned subtree -- and because the champion actively avoids stacking
the spawn columns, most branches die on the bound immediately.  That is what
buys depth 8-12 on a 56 ms oracle.

MINIMALITY IS EXACT.  IDA* deepens by 1, so the first kill found is the SHORTEST
killing sequence: that length IS the depth of the hole.
"""
from __future__ import annotations

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import champion as CH  # noqa: E402

# The adversary's alphabet. (a,b) and (b,a) are the same physical capsule -- the
# champion can rotate freely, so var0/var1 (and var2/var3) cover both readings.
# Verified board-equivalent in verify_pill_symmetry() below.
PILLS6 = [(1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3)]
PILLS9 = [(a, b) for a in (1, 2, 3) for b in (1, 2, 3)]

DEAD_TOPOUT = "topout"
DEAD_NOMOVE = "nomove"


# ------------------------------------------------------------------ heuristic
def spawn_top(b):
    """min top-occupied row across the two spawn columns (16 = both empty)."""
    return min(b.top_occupied_row(3), b.top_occupied_row(4))


def h_lower_bound(b):
    """Admissible: minimum placements before ANY death condition can hold."""
    t = spawn_top(b)
    if t <= 1:
        return 0
    return (t - 1 + 1) // 2   # ceil((t-1)/2)


def state_key(b, cur):
    return (CH.board_key(b), cur)


# ------------------------------------------------------------------- stepping
def step(b, cur, nxt):
    """One ply: champion replies to (b, cur, nxt), we apply it.
    Returns (child_board, action, status) with status in
    {None (alive), 'topout', 'nomove', 'clear'}."""
    col, vir = CH.board_to_flat(b)
    a = CH.champion_move(col, vir, cur[0], cur[1], nxt[0], nxt[1])
    if a is None:
        return (None, None, DEAD_NOMOVE)
    nb = b.clone()
    ok, _cl, _vc, _ch = CH.apply_action(nb, a, cur[0], cur[1])
    if not ok:
        return (None, a, DEAD_NOMOVE)
    if nb.virus_count() == 0:
        return (nb, a, "clear")
    if nb.spawn_blocked():
        return (nb, a, DEAD_TOPOUT)
    return (nb, a, None)


# ---------------------------------------------------------------- solo poker
class Budget(Exception):
    pass


class SoloPoker:
    """Shortest killing pill sequence from (board, cur) via IDA*."""

    def __init__(self, board, cur, alphabet=PILLS6, max_oracle=400_000,
                 order_heuristic=True, log=None):
        self.b0 = board
        self.cur0 = cur
        self.alphabet = alphabet
        self.max_oracle = max_oracle
        self.order_heuristic = order_heuristic
        self.log = log or (lambda *a: None)
        self.calls = 0
        self.nodes = 0
        self.pruned_h = 0
        self.clears = 0
        self.tt = {}          # state_key -> deepest remaining proven safe

    def _children(self, b, cur):
        """(nxt, child_board, action, status) for each adversary pill."""
        out = []
        for n in self.alphabet:
            self.calls += 1
            if self.calls > self.max_oracle:
                raise Budget()
            nb, a, st = step(b, cur, n)
            out.append((n, nb, a, st))
        return out

    def _dfs(self, b, cur, remaining, path):
        """Return killing path (list of (pill, action)) or None."""
        self.nodes += 1
        if remaining <= 0:
            return None
        if h_lower_bound(b) > remaining:
            self.pruned_h += 1
            return None
        k = state_key(b, cur)
        seen = self.tt.get(k, -1)
        if seen >= remaining:
            return None

        kids = self._children(b, cur)
        # order: most spawn-column pressure first (pure move ordering, does not
        # change the result -- IDA* still returns a shortest kill)
        if self.order_heuristic:
            def rank(it):
                _n, nb, _a, st = it
                if st in (DEAD_TOPOUT, DEAD_NOMOVE):
                    return -99
                if st == "clear" or nb is None:
                    return 99
                return spawn_top(nb)
            kids = sorted(kids, key=rank)

        for n, nb, a, st in kids:
            if st in (DEAD_TOPOUT, DEAD_NOMOVE):
                return path + [(n, a, st)]
            if st == "clear":
                self.clears += 1
                continue
            r = self._dfs(nb, n, remaining - 1, path + [(n, a, None)])
            if r is not None:
                return r
        self.tt[k] = remaining
        return None

    def search(self, max_depth=10, min_depth=None):
        """IDA*: the first depth at which a kill exists is the hole depth.
        Returns dict(depth=..., line=[...]) or dict(depth=None, ...)."""
        lo = max(1, h_lower_bound(self.b0)) if min_depth is None else min_depth
        t0 = time.time()
        for d in range(lo, max_depth + 1):
            self.tt.clear()
            try:
                r = self._dfs(self.b0, self.cur0, d, [])
            except Budget:
                return {"depth": None, "line": None, "exhausted": False,
                        "budget_hit": True, "searched_to": d - 1,
                        "calls": self.calls, "nodes": self.nodes,
                        "pruned_h": self.pruned_h, "secs": time.time() - t0}
            self.log(f"    K={d}: {'KILL' if r else 'safe'}  "
                     f"calls={self.calls} nodes={self.nodes} "
                     f"pruned={self.pruned_h} {time.time()-t0:.0f}s")
            if r is not None:
                return {"depth": d, "line": r, "exhausted": True,
                        "budget_hit": False, "searched_to": d,
                        "calls": self.calls, "nodes": self.nodes,
                        "pruned_h": self.pruned_h, "secs": time.time() - t0}
        return {"depth": None, "line": None, "exhausted": True,
                "budget_hit": False, "searched_to": max_depth,
                "calls": self.calls, "nodes": self.nodes,
                "pruned_h": self.pruned_h, "secs": time.time() - t0}


# ------------------------------------------------------------- beam (upper bd)
def beam_kill(board, cur, width=40, max_depth=60, alphabet=PILLS6, log=None):
    """UPPER bound on the hole depth: greedy beam over adversary pill choices,
    scored by spawn-column pressure. IDA* proves 'no kill shallower than K';
    this finds an actual killing line at SOME depth, which is the other half of
    the bracket. Not minimal -- deliberately so; it is cheap (width*6*depth
    oracle calls) where exhaustive search is not."""
    log = log or (lambda *a: None)
    frontier = [(board, cur, [])]
    seen = set()
    calls = 0
    for d in range(max_depth):
        nxt_frontier = []
        for b, c, path in frontier:
            for n in alphabet:
                calls += 1
                nb, a, st = step(b, c, n)
                if st in (DEAD_TOPOUT, DEAD_NOMOVE):
                    return {"depth": d + 1, "line": path + [(n, a, st)],
                            "calls": calls, "width": width}
                if st == "clear" or nb is None:
                    continue
                k = (CH.board_key(nb), n)
                if k in seen:
                    continue
                seen.add(k)
                nxt_frontier.append((nb, n, path + [(n, a, None)]))
        if not nxt_frontier:
            return {"depth": None, "line": None, "calls": calls,
                    "width": width, "reason": "frontier empty (all lines clear)"}
        # DIVERSITY SPLIT. The two adversarial objectives peak at different
        # times: "raise the spawn columns" only separates states near the end,
        # while "bury the board" is what makes that possible in the first place.
        # A beam ranked on either one alone is easy for the champion to walk
        # away from, and a weak adversary makes a weak negative claim. So we
        # take half the beam on each ranking.
        half = max(1, width // 2)
        by_spawn = sorted(nxt_frontier,
                          key=lambda t: (spawn_top(t[0]),
                                         -int((t[0].color != 0).sum())))
        by_fill = sorted(nxt_frontier,
                         key=lambda t: (-int((t[0].color != 0).sum()),
                                        spawn_top(t[0])))
        picked, seen_pick = [], set()
        for src in (by_spawn[:half], by_fill[:width - half]):
            for t in src:
                kk = (CH.board_key(t[0]), t[1])
                if kk not in seen_pick:
                    seen_pick.add(kk)
                    picked.append(t)
        frontier = picked[:width]
        if d % 5 == 0:
            log(f"    beam d={d + 1} best_spawn_top={spawn_top(frontier[0][0])} "
                f"calls={calls}")
    return {"depth": None, "line": None, "calls": calls, "width": width,
            "reason": f"no kill within {max_depth}"}


# --------------------------------------------------------- survivability side
def survivable_fraction(board, cur, K, alphabet=PILLS6, max_oracle=200_000):
    """Of all alphabet^K pill sequences of length K, what fraction leave the
    champion ALIVE?  This is the counterfactual the hole claim needs: a hole is
    only a hole if a DIFFERENT sequence of the same length was survivable.
    Returns (n_total, n_killed, n_cleared, truncated)."""
    tot = kil = clr = 0
    trunc = [False]
    calls = [0]

    def rec(b, cur, d):
        nonlocal tot, kil, clr
        if trunc[0]:
            return
        if d == 0:
            tot += 1
            return
        for n in alphabet:
            calls[0] += 1
            if calls[0] > max_oracle:
                trunc[0] = True
                return
            nb, _a, st = step(b, cur, n)
            if st in (DEAD_TOPOUT, DEAD_NOMOVE):
                tot += 1
                kil += 1
                continue
            if st == "clear":
                tot += 1
                clr += 1
                continue
            rec(nb, n, d - 1)

    rec(board, cur, K)
    return tot, kil, clr, trunc[0]


# ------------------------------------------------------------- sanity harness
def verify_pill_symmetry(n_boards=40, level=11):
    """Is (a,b) the same capsule as (b,a) for the champion?  We test the thing
    that matters -- the RESULTING BOARD -- not the action encoding (which
    legitimately differs by a variant-parity bit, and is arbitrary on ties)."""
    import numpy as np
    bad_cur = bad_nxt = tot = 0
    for s in range(n_boards):
        b = CH.new_board(level, s)
        # walk it forward a bit so boards are non-trivial
        from drmario.faithful_env import FaithfulDrMarioEnv
        from nes_pills import NesPillSource
        env = FaithfulDrMarioEnv(level=level, seed=s, max_pills=60)
        env.reset(); NesPillSource(seed=s).attach(env)
        stream = [(int(p.a), int(p.b)) for p in (env._rand_pill() for _ in range(70))]
        for i in range(25):
            col, vir = CH.board_to_flat(b)
            a = CH.champion_move(col, vir, *stream[i], *stream[i + 1])
            if a is None:
                break
            CH.apply_action(b, a, *stream[i])
            if b.virus_count() == 0 or b.spawn_blocked():
                break
        for cur in [(1, 2), (2, 3), (1, 3)]:
            for nxt in [(1, 2), (2, 3), (3, 3)]:
                tot += 1
                b1, _, s1 = step(b, cur, nxt)
                b2, _, s2 = step(b, (cur[1], cur[0]), nxt)
                if (s1 != s2) or (b1 is None) != (b2 is None) or \
                   (b1 is not None and CH.board_key(b1) != CH.board_key(b2)):
                    bad_cur += 1
                b3, _, s3 = step(b, cur, (nxt[1], nxt[0]))
                if (s1 != s3) or (b1 is None) != (b3 is None) or \
                   (b1 is not None and CH.board_key(b1) != CH.board_key(b3)):
                    bad_nxt += 1
    return {"tested": tot, "cur_swap_differs": bad_cur, "nxt_swap_differs": bad_nxt}


def verify_heuristic(n=200, level=11):
    """The bound must never overestimate. We falsify it directly: walk real
    trajectories and assert h(state_t) <= (true plies remaining to any death).
    Any violation makes every 'no kill within K' claim void."""
    viol = 0
    checked = 0
    for s in range(n):
        b = CH.new_board(level, s)
        from drmario.faithful_env import FaithfulDrMarioEnv
        from nes_pills import NesPillSource
        env = FaithfulDrMarioEnv(level=level, seed=s, max_pills=300)
        env.reset(); NesPillSource(seed=s).attach(env)
        stream = [(int(p.a), int(p.b)) for p in (env._rand_pill() for _ in range(310))]
        hs, died_at = [], None
        for i in range(300):
            hs.append(h_lower_bound(b))
            col, vir = CH.board_to_flat(b)
            a = CH.champion_move(col, vir, *stream[i], *stream[i + 1])
            if a is None:
                died_at = i; break
            CH.apply_action(b, a, *stream[i])
            if b.virus_count() == 0:
                break
            if b.spawn_blocked():
                died_at = i + 1; break
        if died_at is None:
            continue
        for i, hv in enumerate(hs[:died_at]):
            checked += 1
            if hv > died_at - i:
                viol += 1
    return {"checked": checked, "violations": viol}
