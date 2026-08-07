#!/usr/bin/env python3
"""diagnose_seed.py -- ply-by-ply trace of one game, to identify WHY a seed
produced a degenerate-looking result instead of guessing at it.

Written for census seed 1: 300 plies, 299 of them the same action (17), 0 of 48
viruses cleared, and a near-empty final board. Two very different explanations
fit that summary and they call for opposite responses:

  (a) HARNESS ARTIFACT -- e.g. the pill stream degenerates and hands out the
      same capsule forever, or placements silently fail to advance the board.
      Then the row is not a game result and must be excluded from failure counts.
  (b) REAL POLICY PATHOLOGY -- the champion places a same-colour vertical pill,
      stacks four, clears its own pills, and returns to the same board state.
      A genuine no-progress cycle: every placement "succeeds", the board really
      does return to where it started, and no virus is ever touched. That is a
      REAL and serious failure, not an artifact, and on silicon it is a hang.

`env.step` already rules out one popular guess: an illegal placement returns
`terminated=True` immediately (`if not placed: ... terminated = True`), so a
"decider keeps picking an unexecutable move" loop would end at ply 1, not run
300 plies with pills_placed=300.

Logs per ply: the pill colours, the chosen action, whether pills_placed
advanced, what cleared, virus count, occupancy, and a board hash so a repeating
state is visible as a repeating hash.

Usage: diagnose_seed.py 1 [--plies 40]
"""
from __future__ import annotations

import sys
import hashlib
import argparse
from collections import Counter

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
sys.path.insert(0, QA + "/adversary")
import adversary_harness as AH  # noqa: E402


def board_hash(board):
    return hashlib.sha256(
        board.color.tobytes() + board.is_virus.tobytes() + board.link.tobytes()
    ).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seed", type=int)
    ap.add_argument("--plies", type=int, default=40)
    a = ap.parse_args()

    L = AH._lazy()
    RR, FaithfulDrMarioEnv, NesPillSource, FB, RS = (
        L["RR"], L["FaithfulDrMarioEnv"], L["NesPillSource"], L["FB"], L["RS"])

    env = FaithfulDrMarioEnv(level=AH.LEVEL, seed=a.seed, max_pills=300)
    env.reset()
    NesPillSource(seed=a.seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    print(f"seed {a.seed}  level {AH.LEVEL}  start viruses={env.board.virus_count()}")
    print(f"{'ply':>4} {'pill':>6} {'next':>6} {'act':>4} {'var':>3} {'col':>3} "
          f"{'pills':>5} {'vir':>4} {'occ':>4} {'boardhash':>12}  note")

    hashes, actions, pills_seen = Counter(), Counter(), Counter()
    prev_pills = 0
    for i in range(a.plies):
        if env.board.virus_count() == 0:
            print("  cleared")
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        act = RR.choose_base32(col, vir, ca, cb, na, nb, ws=AH.WS)["action"]
        if act is None:
            print(f"{i:>4}  no legal action -> topout")
            break

        occ_before = int((env.board.color != 0).sum())
        _, _, term, trunc, info = env.step(int(act))
        occ_after = int((env.board.color != 0).sum())
        h = board_hash(env.board)

        hashes[h] += 1
        actions[act] += 1
        pills_seen[(ca, cb)] += 1

        note = []
        if env.pills_placed == prev_pills:
            note.append("PILL DID NOT ADVANCE")
        if occ_after < occ_before:
            note.append(f"cleared {occ_before + 2 - occ_after} cells")
        if hashes[h] > 1:
            note.append(f"BOARD STATE REPEAT #{hashes[h]}")
        prev_pills = env.pills_placed

        print(f"{i:>4} {ca}{cb:<5} {na}{nb:<5} {act:>4} {act // 8:>3} {act % 8:>3} "
              f"{env.pills_placed:>5} {int(env.board.virus_count()):>4} "
              f"{occ_after:>4} {h:>12}  {'; '.join(note)}")

        if term or trunc:
            print(f"  terminated={term} truncated={trunc} info={info}")
            break

    print(f"\naction histogram : {actions.most_common(5)}")
    print(f"pill (a,b) histogram: {pills_seen.most_common(5)}")
    print(f"distinct board states: {len(hashes)} over {sum(hashes.values())} plies")
    print(f"most repeated state  : {hashes.most_common(3)}")


if __name__ == "__main__":
    main()
