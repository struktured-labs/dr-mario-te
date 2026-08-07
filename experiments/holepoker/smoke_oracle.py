#!/usr/bin/env python3
"""GATE 0: the oracle must reproduce the shipped champion exactly.

Test the DEFECT, not the fix: we do not assert "champion_move returns something".
We play whole games two ways and demand identical trajectories:
  A) eval47/ab47.py's own play loop (env.step, _choose_base with wt=0 ws=20)
  B) our champion_move + faithful-board apply_action
If our oracle or our world-step differ from the shipped rig by one placement,
this prints a MISMATCH with the pill index, and everything downstream is void.
"""
from __future__ import annotations
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np
import champion as CH


def play_reference(seed, level=11, max_pills=300):
    """ab47.py's loop, verbatim in structure."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS
    sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47")
    import ab47

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    w, fl = CH._W["w"], CH._W["fl"]
    acts, res = [], "stall"
    for _ in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"; break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        a, _c1 = ab47._choose_base(col, vir, int(env.cur.a), int(env.cur.b),
                                   int(env.nxt.a), int(env.nxt.b), w, fl,
                                   0, CH.WS_STRANDED)
        if a is None:
            break
        acts.append(int(a))
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"; break
        if trunc:
            break
    return acts, res, env.pills_placed


def play_oracle(seed, level=11, max_pills=300):
    """Our own loop: faithful board + memoized champion_move + a REPLAYED pill
    stream (same NES stream, but pulled by us, not by the env)."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource

    # pull the identical pill stream by running an env we never step
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    stream = [(int(p.a), int(p.b)) for p in (env._rand_pill() for _ in range(max_pills + 4))]

    b = CH.new_board(level, seed)
    acts, res = [], "stall"
    i = 0
    for _ in range(max_pills):
        if b.virus_count() == 0:
            res = "clear"; break
        col, vir = CH.board_to_flat(b)
        ca, cb = stream[i]
        na, nb = stream[i + 1]
        a = CH.champion_move(col, vir, ca, cb, na, nb)
        if a is None:
            break
        acts.append(int(a))
        ok, _cl, _vc, _ch = CH.apply_action(b, a, ca, cb)
        if not ok:
            res = "illegal"; break
        i += 1
        if b.virus_count() == 0:
            res = "clear"; break
        if b.spawn_blocked():
            res = "topout"; break
    return acts, res, i


def main():
    CH.init_champion()
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    bad = 0
    for s in range(n):
        ra, rr, rp = play_reference(s)
        oa, orr, op = play_oracle(s)
        same = (ra == oa) and (rr == orr)
        if not same:
            bad += 1
            k = next((j for j in range(min(len(ra), len(oa))) if ra[j] != oa[j]),
                     min(len(ra), len(oa)))
            print(f"MISMATCH seed={s}: ref({rr},{rp},{len(ra)}a) vs "
                  f"oracle({orr},{op},{len(oa)}a) first-diff at pill {k}: "
                  f"{ra[k] if k < len(ra) else None} vs {oa[k] if k < len(oa) else None}")
        else:
            print(f"  seed={s:3d} OK  {rr:8s} pills={rp:3d} acts={len(ra)}")
    print(f"\nmemo: {CH.memo_stats()}")
    print("GATE 0:", "PASS" if bad == 0 else f"FAIL ({bad}/{n} mismatched)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
