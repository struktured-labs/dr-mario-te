#!/usr/bin/env python3
"""What does a winning tier-3 tuck actually BUY, per placement?

Single-process and cheap on purpose (it runs alongside the paired game runs
without competing for the 6-worker budget). Walks real L11 decisions under the
shipped base32 decider and, at every decision where a tier-3 tuck would win the
theta gate, records what the search thinks it gained:

  margin      tuck value minus the best base value, in eval units. This is the
              number the firmware's theta gate compares against.
  depth gain  rows the tuck lands below the straight drop that the drop-mode
              cart would perform instead. The physical size of the maneuver.
  geometry    horizontal vs vertical -- the co-sim asked whether divergent
              picks are systematically horizontal.

The point of collecting this next to the game-level result: if the search
prices tucks highly per placement but the games do not improve, the gap
between those two facts IS the washout, quantified at the decision level
rather than inferred.

Usage: tuck_profile.py [--games 30] [--theta 150]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS = os.path.dirname(HERE)
EVAL47 = os.path.join(EXPERIMENTS, "eval47")
for _p in (HERE, EXPERIMENTS, EVAL47):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import exec_model as EM      # noqa: E402
import run_2x2 as R2         # noqa: E402
import reach_root as RR      # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=30)
    ap.add_argument("--theta", type=float, default=R2.FIRMWARE_THETA)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    RR._lazy()
    import fast_sim_x as FS
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    L = RR._lazy()
    FB, RS = L["FB"], L["RS"]

    margins, gains, orients, decisions, wins = [], [], Counter(), 0, 0
    for g in range(a.games):
        env = FaithfulDrMarioEnv(level=a.level, seed=g, max_pills=300)
        env.reset()
        NesPillSource(seed=g).attach(env)
        env.cur = env._rand_pill()
        env.nxt = env._rand_pill()
        for _ in range(300):
            if env.board.virus_count() == 0:
                break
            fb = FB.from_board(env.board)
            col, vir = RS.board_flat_from_fb(fb)
            ca, cb = int(env.cur.a), int(env.cur.b)
            na, nb = int(env.nxt.a), int(env.nxt.b)
            pick, base_action = R2.choose_with_base(fb, col, vir, ca, cb, na, nb,
                                                    "t3", a.theta)
            decisions += 1
            if pick["kind"] == "tuck":
                wins += 1
                p = pick["placement"]
                margins.append(float(pick["margin"]))
                r0, c0, r1, c1 = p["cells"]
                anchor = max(r0, r1) if c0 == c1 else r0
                dact = EM.tier3_drop_action(p)
                ok, dr0, dc0, dr1, dc1 = FS._resting(col, dact // 8, dact % 8)
                if ok:
                    danchor = max(dr0, dr1) if dc0 == dc1 else dr0
                    gains.append(anchor - danchor)
                orients["H" if r0 == r1 else "V"] += 1
            # advance the game on the SHIPPED policy so the board distribution
            # is today's silicon's, not a tuck-arm's
            _, _, term, trunc, _ = env.step(int(base_action))
            if term or trunc:
                break

    print(f"=== tier-3 winning-tuck profile, L{a.level}, {a.games} games, "
          f"theta={a.theta:g} ===")
    print(f"decisions {decisions}   tuck wins {wins} ({wins / max(1, decisions):.1%} "
          f"of decisions, {wins / a.games:.2f} per game)")
    if margins:
        print(f"margin over best base (eval units): median {st.median(margins):.0f}  "
              f"mean {st.mean(margins):.0f}  max {max(margins):.0f}")
    if gains:
        print(f"depth gain vs the drop-mode landing (rows): median "
              f"{st.median(gains):.1f}  mean {st.mean(gains):.2f}  max {max(gains)}  "
              f"(zero-gain {sum(1 for x in gains if x <= 0)}/{len(gains)})")
    print(f"geometry: {dict(orients)}")
    if a.out:
        with open(a.out, "w") as fh:
            json.dump({"decisions": decisions, "wins": wins, "margins": margins,
                       "gains": gains, "orients": dict(orients),
                       "theta": a.theta, "games": a.games}, fh)
        print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
