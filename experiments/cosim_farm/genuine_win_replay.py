#!/usr/bin/env python3
"""Can ANY placement genuinely win on the boards my debug firmware called wins?

The firmware scored 16 of 30 boards as WIN (D_V1 = D_I1 + 30000). This replays those
boards in the faithful sim and asks the same question the search's sentinel claims to
answer: after applying a placement and resolving, is `virus_count() == 0`?

DELIBERATELY STRONGER THAN "replay the published placement". It enumerates the WHOLE
root action space -- every legal drop (4 orientations x 8 columns) and every reachable
tuck rest (the same `fall_from` the executor uses, over all rings, columns and trigger
rows) -- and reports the BEST achievable outcome. If the best placement on a board
cannot reach zero viruses, then no particular published placement can either, so this
subsumes the narrower check without needing the descriptor bytes back off the co-sim.

It is also independent of the fix: nothing here consults the firmware's own win flag,
which is what makes it a check rather than a restatement.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src")

from cosim import read_hostdata  # noqa: E402
from transfer_check import nes_to_board  # noqa: E402
from game import RING_OF_O4, apply_tuck, cells_of, fall_from  # noqa: E402

CORPUS = "/mnt/data/drmario_cosim/gate/hostdata_l11_hz30.txt"
READOUT = "/mnt/data/drmario_cosim/results/gate_readout_hz30.json"
OUT = "/mnt/data/drmario_cosim/results/genuine_win_replay.json"
ROWS, COLS = 16, 8


def best_over_actions(nes, ca, cb):
    """(min viruses left over the whole root action space, n_actions_tried).

    ONE enumeration, in ring space only. A plain drop is `fall_from` with a trigger row
    above the stack, so sweeping (ring, column, trigger row) covers drops and tucks
    together -- which also avoids converting between the o4/orient/ring conventions,
    the kind of silent space-mismatch this lane has already been bitten by twice.
    """
    best, tried = None, 0
    for ring in range(4):
        for col in range(COLS):
            seen = set()
            for trow in range(ROWS):
                b0 = nes_to_board(nes)
                rest = fall_from(b0.color, col, ring, trow)
                if rest is None or rest in seen:
                    continue
                seen.add(rest)
                try:
                    cells_of(ring, col, rest)
                except Exception:
                    continue
                b = nes_to_board(nes)
                try:
                    apply_tuck(b, ring, col, rest, ca, cb)
                except Exception:
                    continue
                b.resolve()
                tried += 1
                v = int(b.virus_count())
                best = v if best is None else min(best, v)

    return best, tried


def main():
    cases = read_hostdata(CORPUS)
    boards = json.load(open(READOUT))["boards"]

    rows, wins = [], 0
    print(f"{'brd':>3} {'fw_said':>8} {'viruses_in':>11} {'best_left':>10} "
          f"{'actions':>8} {'genuine_win':>12}")
    for c, b in zip(cases, boards):
        if not b["published"]:
            continue
        # corpus colours are 0-based (fed straight to Cosim.decide); the sim wants 1..3
        left, tried = best_over_actions(c["board"], c["cA"] + 1, c["cB"] + 1)
        vin = sum(1 for x in c["board"] if (x & 0xF0) == 0xD0)
        win = (left == 0)
        wins += win
        rows.append({"i": b["i"], "viruses_in": vin, "best_left": left,
                     "actions_tried": tried, "genuine_win": win,
                     "fw_max_all": b["max_all"]})
        print(f"{b['i']:>3} {'WIN':>8} {vin:>11} {str(left):>10} {tried:>8} "
              f"{str(win):>12}")

    n = len(rows)
    lefts = [r["best_left"] for r in rows if r["best_left"] is not None]
    print(f"\n{wins} of {n} genuinely reach virus_count == 0")
    if lefts:
        print(f"best achievable viruses left over the WHOLE action space: "
              f"min={min(lefts)} median={sorted(lefts)[len(lefts)//2]} max={max(lefts)}")
    print(f"actions enumerated per board: {min(r['actions_tried'] for r in rows)}"
          f"..{max(r['actions_tried'] for r in rows)}")
    json.dump({"n": n, "genuine_wins": wins, "rows": rows}, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
