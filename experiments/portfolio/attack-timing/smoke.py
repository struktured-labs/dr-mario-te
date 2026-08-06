#!/usr/bin/env python3
"""One real match: holder (threshold=10, K=2) vs plain champion. Confirms the
wrapper actually holds sometimes and the match completes without error."""
from __future__ import annotations
import sys, os, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src", ROOT + "/tmp/vs_aware"):
    if p not in sys.path:
        sys.path.insert(0, p)

import fast_rtl_x as F
import cascade_chain_x as C
import vs_harness as H
from hold_decider import make_champion, make_holder

F.warmup_delta(topk2=8)
C.warmup_chain(topk2=8)

holder = make_holder(threshold=10, K=2)
champ = make_champion()

f_hold = lambda b, c, n, opp: holder.choose(b, c, n, opp)
f_champ = H.blind_obj = None  # placeholder


class _B:
    def __init__(self, fn):
        self._fn = fn

    def choose(self, b, c, n):
        return self._fn(b, c, n)


f_champ2 = H.blind(_B(lambda b, c, n: champ.choose(b, c, n)))

t0 = time.time()
r = H.play_match(seed=400, dec0=f_hold, dec1=f_champ2, level=11, max_pills=300,
                 nes_pills=True, garbage=True)
dt = time.time() - t0
print("match result:", {k: r[k] for k in ("seed", "winner", "reason", "margin", "pills", "attacks")})
print("holder stats:", holder.stats)
print(f"wall: {dt:.2f}s")
