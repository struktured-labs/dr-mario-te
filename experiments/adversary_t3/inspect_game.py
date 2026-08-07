#!/usr/bin/env python3
"""Replay one seed with a per-decision trace, for the "what does the winning
adversary actually do differently" writeup. Prints, per adversary placement:
own board cells/maxh, opponent maxh at decision time, cells cleared this
placement (0 = a "hold"), and whether a release fired this placement.

Usage: inspect_game.py --seed 6013 --vec 191 22 -76 194 50 [--champ-kind champ]
"""
from __future__ import annotations
import sys, os, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/tmp/vs_aware",
           ROOT + "/.claude/worktrees/faithful-sim/src", QA, QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import vs_harness as H
from adversary_search import AdversaryD3Decider
from vs_run import champion_decider, pre_strand20_champion, warmup_all
import fast_rtl_x as FX


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--vec", type=int, nargs=5, required=True)
    ap.add_argument("--champ-kind", choices=("champ", "pre20"), default="champ")
    ap.add_argument("--adv-side", type=int, choices=(0, 1), default=1,
                    help="which side the adversary plays (0=P0/first, 1=P1/second)")
    ap.add_argument("--level", type=int, default=11)
    a = ap.parse_args()

    warmup_all()
    w, fl = FX.variant("winner")
    adv = AdversaryD3Decider.from_vector(tuple(a.vec), w, fl, topk2=8)
    champ = champion_decider() if a.champ_kind == "champ" else pre_strand20_champion()

    trace = []

    def hook(who, e, opp_board, action, took):
        is_adv = (who == a.adv_side)
        opp_maxh = int(opp_board.column_heights().max())
        own_maxh = int(e.board.column_heights().max())
        cells_before = int((e.board.color != 0).sum())
        trace.append({"who": who, "is_adv": is_adv, "opp_maxh": opp_maxh,
                      "own_maxh": own_maxh, "cells_before": cells_before,
                      "took": took, "action": action})
        return None

    dec_adv = lambda b, c, n, opp: adv.choose(b, c, n, opp)
    dec_champ = H.blind(champ)
    a0, a1 = (dec_adv, dec_champ) if a.adv_side == 0 else (dec_champ, dec_adv)
    r = H.play_match(a.seed, a0, a1, level=a.level, max_pills=300, hook=hook, garbage=True)

    print(f"seed={a.seed} vec={a.vec} adv_side={a.adv_side} champ_kind={a.champ_kind}")
    print(f"result: winner={r['winner']} reason={r['reason']} virus={r['virus']} "
          f"pills={r['pills']} attacks={r['attacks']}")
    print(f"{'ply':>4} {'who':>4} {'own_maxh':>8} {'opp_maxh':>8} {'took':>5}")
    for i, t in enumerate(trace):
        if t["is_adv"]:
            print(f"{i:>4} {'ADV':>4} {t['own_maxh']:>8} {t['opp_maxh']:>8} {t['took']:>5}")
    champ_side = 1 - a.adv_side
    print(f"\nchampion (side {champ_side}) final virus={r['virus'][champ_side]}  "
          f"adversary final virus={r['virus'][a.adv_side]}")


if __name__ == "__main__":
    main()
