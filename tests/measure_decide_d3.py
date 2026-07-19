#!/usr/bin/env python3
"""SMOKING-GUN test: measure decide_d3's OWN clear rate in the faithful env. decide_d3 is
the EXACT function the copro implements (cell-exact 30/30). The 93.8% was measured on
CartDepth3; decide_d3 only agreed with it ~80%. If decide_d3 clears ~93% too, the hardware
gap is steering/mechanics. If decide_d3 walls, the copro never ran the 93.8% config and the
bug is in the golden/config -- a pure-sim explanation for hardware 0%."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src")
sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/tmp")
import nes_d3_golden as G3
from drmario.faithful_env import FaithfulDrMarioEnv
from xcheck_terms import faithful_to_nes

# copro deploy config
G3.USE_VRDY = True
THIRD = [(0, 1), (1, 2), (2, 0), (1, 1)]   # 4-pill (deployed)
TOPK1, TOPK2 = 32, 8

# orient4 (decide_d3) -> faithful action variant: {0:V a-top,1:V b-top,2:H a-left,3:H b-left}
#   faithful variants: 0=H a-b, 1=H b-a, 2=V a-b, 3=V b-a
O4_TO_VAR = {0: 2, 1: 3, 2: 0, 3: 1}


def play(seed, max_pills):
    env = FaithfulDrMarioEnv(level=11, seed=seed, max_pills=max_pills)
    env.reset(); start = env._start_viruses
    done, info, steps = False, {}, 0
    while not done and steps < max_pills:
        nes = faithful_to_nes(env.board)
        cA, cB = env.cur.a - 1, env.cur.b - 1   # faithful color 1..3 -> NES 0..2 (matches faithful_to_nes)
        nA, nB = env.nxt.a - 1, env.nxt.b - 1
        key = G3.decide_d3(list(nes), cA, cB, nA, nB, topk1=TOPK1, topk2=TOPK2, third=THIRD)
        if key is None:
            break
        col, o4 = key
        action = O4_TO_VAR[o4] * 8 + col
        _, _, term, trunc, info = env.step(int(action))
        done = term or trunc; steps += 1
    won = bool(info.get("won", env.board.virus_count() == 0))
    return won, env.board.virus_count(), start


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    seed0 = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    wins = 0; lefts = []
    for s in range(seed0, seed0 + n):
        won, left, start = play(s, 400)
        wins += int(won); lefts.append(left)
        print(f"  seed {s}: {'CLEAR' if won else 'topout'} (viruses-left={left})", flush=True)
    print(f"decide_d3 (copro's exact fn) FULL-CLEAR = {wins}/{n} = {100*wins//n}%  "
          f"avg-left = {sum(lefts)/len(lefts):.1f}", flush=True)


if __name__ == "__main__":
    main()
