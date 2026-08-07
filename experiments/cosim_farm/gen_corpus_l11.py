#!/usr/bin/env python3
"""Generate a hostdata.txt corpus of REAL L11 gameplay boards.

The stock gen_corpus.py emits synthetic random boards. CANDIDATE_TIER3.md sec 10 found
those are the EASY case: py65-vs-RTL agreement was 50% on synthetic boards but 13.3% on
real L11 ones. A gate that only ever sees synthetic boards is therefore gated on the
wrong distribution, so the agreement gate runs on these instead.

Boards come from the faithful sim at L11 with the real NES capsule stream, advanced by a
random number of random LEGAL placements -- mid-game structure (overhangs, buried
viruses, uneven columns), not noise. The expected-move columns in the output are dummies:
gate_agree.py compares the two binaries against EACH OTHER, never against an oracle.

Usage: gen_corpus_l11.py <n> <out.txt> [--seed S] [--level L]
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RL = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, RL + "/.claude/worktrees/faithful-sim/src", QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cosim import board_to_nes  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=20260806)
    ap.add_argument("--level", type=int, default=11)
    a = ap.parse_args()

    import random
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource

    rng = random.Random(a.seed)
    cases = []
    gs = 0
    while len(cases) < a.n:
        gs += 1
        env = FaithfulDrMarioEnv(level=a.level, seed=a.seed + gs, max_pills=300)
        env.reset()
        NesPillSource(seed=a.seed + gs).attach(env)
        env.cur = env._rand_pill()
        env.nxt = env._rand_pill()
        depth = rng.randint(0, 45)
        alive = True
        for _ in range(depth):
            m = env.action_masks()
            legal = np.flatnonzero(m)
            if legal.size == 0:
                alive = False
                break
            _, _, term, trunc, _ = env.step(int(rng.choice(legal)))
            if term or trunc:
                alive = False
                break
        if not alive or env.board.virus_count() == 0:
            continue
        # hostdata cA/cB/nA/nB are 0-BASED colour ids, matching the copro mailbox and
        # sim_mister.cpp's own field convention (fpga/copro/gen_corpus.py draws
        # rng.randint(0, 2)). The faithful sim's Pill colours are 1..3, hence the -1.
        cases.append((board_to_nes(env.board),
                      int(env.cur.a) - 1, int(env.cur.b) - 1,
                      int(env.nxt.a) - 1, int(env.nxt.b) - 1))

    with open(a.out, "w") as fh:
        fh.write("%d\n" % len(cases))
        for board, cA, cB, nA, nB in cases:
            fh.write("%d %d %d %d 0 0\n" % (cA, cB, nA, nB))
            for r in range(16):
                fh.write(" ".join("%02x" % board[r * 8 + c] for c in range(8)) + "\n")
    print(f"wrote {len(cases)} real-L{a.level} boards to {a.out}")


if __name__ == "__main__":
    main()
