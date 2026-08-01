#!/usr/bin/env python3
"""Regression test: every knob a sweep can set MUST actually reach the weight vector.

WHY THIS EXISTS. On 2026-07-31 the name->index mapping lived in two copies. `sweep_knobs`
grew vbonus/cross/wvir; `h2h_vs._mk` did not. So the L20 vbonus holdout built a "candidate"
that was byte-identical to the reference and dutifully reported 50.0% / "NOT CONFIRMED" for
a weight set it had never tested. No exception, no warning -- an unknown key was simply
ignored, and the wrong answer was the plausible-looking one.

Two independent guards, because the failure was silent in both directions:
  1. every key in every sweep GRID resolves to a distinct weight index and changes it;
  2. a candidate differing in that key actually CHANGES PLAY on real boards -- the end-to-end
     property the holdout depends on. An index that exists but is inert fails here.
"""
from __future__ import annotations
import sys, os

ROOT = "/home/struktured/projects/dr_mario_rl"
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
from h2h_vs import WINNER, idx_map, _mk
import sweep_knobs
import sweep_attack


def all_grid_keys():
    keys = {}
    for g in (sweep_knobs.GRID, sweep_attack.GRID):
        for k, vals in g.items():
            keys.setdefault(k, []).extend(vals)
    return keys


def test_mapping():
    import fast_rtl_x as F
    m = idx_map()
    bad = []
    for k in all_grid_keys():
        if k not in m:
            bad.append(f"{k}: NOT IN idx_map -- would be SILENTLY IGNORED")
    if len(set(m.values())) != len(m):
        bad.append("idx_map has duplicate indices")
    return bad


def test_weight_changes():
    """Setting a knob must change exactly one entry of the weight vector."""
    import fast_rtl_x as F
    base = _mk(dict(WINNER))
    bad = []
    for k, vals in all_grid_keys().items():
        v = next((x for x in vals if x != WINNER.get(k)), None)
        if v is None:
            continue
        cand = dict(WINNER); cand[k] = v
        d = _mk(cand)
        diff = np.nonzero(np.asarray(d.w) != np.asarray(base.w))[0]
        if len(diff) != 1:
            bad.append(f"{k}={v}: changed {len(diff)} weight entries, expected 1")
    return bad


def test_play_changes():
    """End-to-end: the knob must change ACTUAL PLAY on real boards, not just a number in
    an array. This is the property the holdout silently lacked."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    import fast_rtl_x as F
    F.warmup_delta(topk2=8)

    def acts(dec, seed, level, n=60):
        env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
        env.reset()
        NesPillSource(seed=seed).attach(env)
        env.cur = env._rand_pill(); env.nxt = env._rand_pill()
        out = []
        for _ in range(n):
            a = dec.choose(env.board, env.cur, env.nxt)
            if a is None:
                break
            out.append(int(a))
            _, _, term, trunc, _ = env.step(int(a))
            if term or trunc:
                break
        return out

    base = _mk(dict(WINNER))
    bad = []
    for k, vals in all_grid_keys().items():
        v = max(vals, key=lambda x: abs(x - WINNER.get(k, 0)))
        if v == WINNER.get(k):
            continue
        cand = dict(WINNER); cand[k] = v
        d = _mk(cand)
        # Count how many of a wider sample the knob moves. A knob can be correctly WIRED
        # (weight-vector test passes) and still almost never change a decision -- that is a
        # real property worth reporting, and it is NOT the same failure as an unwired knob.
        n_games = 0; n_moved = 0
        for lvl in (11, 20):
            for s in range(400, 420):
                n_games += 1
                if acts(d, s, lvl) != acts(base, s, lvl):
                    n_moved += 1
        rate = n_moved / n_games
        if n_moved == 0:
            bad.append(f"{k}={v}: play IDENTICAL on {n_games} games -- INERT")
        else:
            print(f"      {k}={v}: moves play in {n_moved}/{n_games} games ({rate:.0%})")
    return bad


if __name__ == "__main__":
    fails = []
    for name, fn in (("mapping", test_mapping),
                     ("weight-vector", test_weight_changes),
                     ("play-changes", test_play_changes)):
        bad = fn()
        print(f"  {name:<14} {'PASS' if not bad else 'FAIL'}")
        for b in bad:
            print(f"      {b}")
        fails += bad
    print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILURES'}")
    raise SystemExit(1 if fails else 0)
