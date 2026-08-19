#!/usr/bin/env python3
"""Arm-D bug hunt: does the executor land the pill where the descriptor implies?

Arm D (s20t3 firmware + descriptor honoured) is catastrophic in RTL while the independent
fast-sim lane has it as the BEST arm. Before that contradiction is published, this
separates the two explanations, which need different responses:

  (a) MY EXECUTION IS WRONG  -- apply_tuck lands the pill somewhere the search did not
      score, so arm D never tests what it claims to.
  (b) THE ROOT CHOICE IS BAD -- the pill lands exactly where the firmware intended and the
      intention is poor, i.e. tier-3 lets tucks win the argmax too often.

Checks per executed tuck, all decidable from the board + the published descriptor:
  * cells_empty     the two target cells were free before writing (else we overwrote)
  * deeper          rest > straight-drop rest, i.e. it is a REAL tuck not a no-op
  * rest_is_deepest falling further from `rest` is blocked, i.e. `rest` is the true
                    resting row and not a mid-air stop
  * depth_gain      how many rows deeper than a plain drop

`rest` is recovered by falling from the published trigger row. That IS the inverse of the
firmware's own derivation -- translate_ref's `_phase2_ok` accepts a descriptor only when
`rf == rest and rf > sd` for exactly this fall -- so agreement here means the executor
reproduces the scored placement.

Also records what the SHIPPED firmware (s20b) would have chosen on the identical board, to
size how far tier-3's root choice moves.

Usage: trace_armd.py [--seed N] [--max-pills N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RL = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, RL + "/.claude/worktrees/faithful-sim/src", QA, QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cosim import Cosim, board_to_nes, VAR_OF_O4  # noqa: E402
import game as G  # noqa: E402

BUILD = os.environ.get("COSIM_FARM_BUILD", os.path.join(HERE, "build"))
FARM_BIN = os.path.join(BUILD, "obj_farm", "farm_vsim")
FW = "/mnt/data/drmario_cosim/fw"


def straight_drop_row(color, col, ring):
    """Deepest anchor row a PLAIN drop reaches -- the baseline a tuck must beat."""
    return G.fall_from(color, col, ring, 0 if G.RING_IS_H[ring] else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--out", default="/mnt/data/drmario_cosim/results/trace_armd.json")
    a = ap.parse_args()

    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    import run_bursty_v1_1_validity as V11
    from bursty_model import inject_bursty_garbage

    model = V11.build_v1_1()
    model.meta = {k: v for k, v in model.meta.items() if k != "raw_events"}

    env = FaithfulDrMarioEnv(level=11, seed=a.seed, max_pills=a.max_pills)
    env.reset()
    NesPillSource(seed=a.seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    tucks, drops = [], 0
    bad = []
    res = "stall"

    with Cosim(FARM_BIN, os.path.join(FW, "s20t3")) as cs_d, \
         Cosim(FARM_BIN, os.path.join(FW, "s20b")) as cs_a:
        print(f"arm D fw={cs_d.fw_md5[:8]}   shipped-champ fw={cs_a.fw_md5[:8]}", flush=True)
        for _ in range(a.max_pills):
            if env.board.virus_count() == 0:
                res = "clear"; break
            b128 = board_to_nes(env.board)
            ca, cb = int(env.cur.a), int(env.cur.b)
            na, nb = int(env.nxt.a), int(env.nxt.b)
            d = cs_d.decide(b128, ca - 1, cb - 1, na - 1, nb - 1)
            ref = cs_a.decide(b128, ca - 1, cb - 1, na - 1, nb - 1)   # what s20b would do
            col, o4, tcol, trow = d["col"], d["o4"], d["tcol"], d["trow"]
            occ_before = int(np.count_nonzero(env.board.color))

            if tcol != G.NO_TUCK:
                ring = G.RING_OF_O4[o4]
                rest = G.fall_from(env.board.color, col, ring, trow)
                sd = straight_drop_row(env.board.color, col, ring)
                rec = {"ply": env.pills_placed, "col": col, "o4": o4, "ring": ring,
                       "tcol": tcol, "trow": trow, "rest": rest, "straight_drop": sd,
                       "s20b_would": [ref["col"], ref["o4"]],
                       "same_as_s20b": [col, o4] == [ref["col"], ref["o4"]]}
                if rest is None:
                    rec["verdict"] = "INCOHERENT(fell back to drop)"
                    bad.append(rec); tucks.append(rec)
                else:
                    (r0, c0), (r1, c1) = G.cells_of(ring, col, rest)
                    rec["cells"] = [[r0, c0], [r1, c1]]
                    rec["cells_empty"] = bool(env.board.color[r0, c0] == 0
                                              and env.board.color[r1, c1] == 0)
                    rec["rest_is_deepest"] = G.fall_from(env.board.color, col, ring,
                                                         rest) == rest
                    rec["deeper"] = (sd is not None and rest > sd)
                    rec["depth_gain"] = (rest - sd) if sd is not None else None
                    ok = rec["cells_empty"] and rec["rest_is_deepest"]
                    rec["verdict"] = "OK" if ok else "EXECUTOR-BUG"
                    if not ok:
                        bad.append(rec)
                    tucks.append(rec)
                    G.apply_tuck(env.board, ring, col, rest, ca, cb)
                    env.board.resolve()
                    env.pills_placed += 1
                    if env.board.virus_count() == 0:
                        res = "clear"; break
                    if env.board.spawn_blocked():
                        res = "topout"; break
                    env.cur = env.nxt; env.nxt = env._rand_pill()
                    if not env.action_masks().any():
                        res = "topout"; break
                    goto_pressure = True
            else:
                goto_pressure = False

            if tcol == G.NO_TUCK or (tucks and tucks[-1].get("rest") is None):
                drops += 1
                action = VAR_OF_O4[o4] * 8 + col
                orient, acol, pill = env._decode(action)
                if env.board.resting_position(pill, orient, acol) is None:
                    res = "topout"; break
                _, _, term, trunc, info = env.step(int(action))
                if term:
                    res = "clear" if info["won"] else "topout"; break
                if trunc:
                    break

            if env.pills_placed >= 25:
                occ_after = int(np.count_nonzero(env.board.color))
                cs = max(0, occ_before + 2 - occ_after)
                if cs > 0:
                    inject_bursty_garbage(env.board, model, a.seed, env.pills_placed, cs)
                if env.board.virus_count() == 0:
                    res = "clear"; break
                if env.board.spawn_blocked():
                    res = "topout"; break
            del goto_pressure

    n = len(tucks)
    real = [t for t in tucks if t.get("deeper")]
    noop = [t for t in tucks if t.get("deeper") is False]
    moved = [t for t in tucks if not t.get("same_as_s20b", True)]
    print(f"\nseed {a.seed}: {res}, pills={env.pills_placed}, "
          f"cleared={48 - env.board.virus_count()}/48")
    print(f"  tucks executed      : {n}  ({n / max(1, env.pills_placed):.0%} of placements)")
    print(f"  EXECUTOR BUGS       : {len(bad)}")
    print(f"  real tucks (deeper) : {len(real)}   mean depth gain "
          f"{(sum(t['depth_gain'] for t in real) / len(real)) if real else 0:.2f} rows")
    print(f"  NO-OP tucks (= drop): {len(noop)}")
    print(f"  tuck plies where s20b would have chosen differently: {len(moved)}/{n}")
    if bad:
        print("\n  first bugs:")
        for t in bad[:5]:
            print("   ", t)
    json.dump({"seed": a.seed, "result": res, "pills": env.pills_placed,
               "cleared": 48 - env.board.virus_count(),
               "n_tucks": n, "n_bugs": len(bad), "n_real": len(real),
               "n_noop": len(noop), "n_moved_vs_s20b": len(moved),
               "tucks": tucks}, open(a.out, "w"), indent=1)
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
