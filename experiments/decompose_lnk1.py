#!/usr/bin/env python3
"""WHY does lnk1 win in VS? Two channels, and a win rate cannot tell them apart.

lnk1 does two things at once in cascade-search's solo data: it raises the ROM attack rate
(+7%) AND it takes clear rate 96.7% -> 100.0% (12 discordant pairs, all one way -- it stops
topping out). In VS both cash out as wins, so attributing the +10 points to "it attacks
more" would be exactly the kind of story that sounds mechanistic and is unfalsified.

THE DECOMPOSITION. Every match ends for a reason, and the reason names the channel:
  * candidate LOSES by `topout`  -> a ROBUSTNESS failure the arm was supposed to fix
  * candidate LOSES by `clear`   -> the opponent simply cleared first: a SPEED loss
  * candidate WINS by `clear`    -> it out-raced, or garbage broke the opponent
If lnk1's gain is robustness, its topout LOSSES should collapse toward zero while its
clear-losses stay put. If the gain is attacking, opponent TOPOUTS should rise instead.
Those predictions are different, so this is a real test rather than a re-description.

Reads the per-match JSONL from `h2h_vs.py --out`.
"""
from __future__ import annotations
import sys, os, json, collections


def main(path, label=None):
    label = label or os.path.basename(path).split('_')[0]
    rows = [json.loads(l) for l in open(path) if l.strip()]
    n = len(rows)
    won = [r for r in rows if r["win"] == 1.0]
    lost = [r for r in rows if r["win"] == 0.0]
    drew = [r for r in rows if r["win"] == 0.5]

    print(f"{label} vs winner — LOSS/WIN DECOMPOSITION BY TERMINAL REASON  ({n} matches)")
    print(f"  won {len(won)}  lost {len(lost)}  drew {len(drew)}"
          f"   -> {sum(r['win'] for r in rows)/n:.1%}\n")

    def tab(rs, hdr):
        c = collections.Counter(r["reason"] for r in rs)
        tot = sum(c.values()) or 1
        print(f"  {hdr} ({tot}):")
        for k, v in c.most_common():
            print(f"      {k:<10} {v:5d}  {v/tot:5.1%}")
        return c

    cw = tab(won, f"{label} WINS by")
    cl = tab(lost, f"{label} LOSSES by")

    print("\n  ★ THE ATTRIBUTION:")
    # A loss with reason 'topout' means the LOSER topped out -> that is lnk1 self-topping.
    self_top = cl.get("topout", 0) + cl.get("no-move", 0)
    outraced = cl.get("clear", 0)
    print(f"      {label} lost by SELF-TOPOUT/no-move : {self_top:5d}"
          f"   <- robustness channel")
    print(f"      {label} lost by OPPONENT CLEARING   : {outraced:5d}"
          f"   <- speed channel")
    opp_top = cw.get("topout", 0) + cw.get("no-move", 0)
    print(f"      {label} won by OPPONENT TOPPING OUT : {opp_top:5d}"
          f"   <- garbage/attack channel")
    print(f"      {label} won by CLEARING FIRST       : {cw.get('clear', 0):5d}")

    print("\n  attacks sent: lnk1 %.2f vs winner %.2f"
          % (sum(r["atk_cand"] for r in rows) / n, sum(r["atk_ref"] for r in rows) / n))
    print(f"  mean pills ({label}): %.1f" % (sum(r["pills_cand"] for r in rows) / n))

    print("\n  ⚠⚠ THIS TABLE UNDER-COUNTS GARBAGE BY CONSTRUCTION. It classifies by TERMINAL"
          "\n  EVENT, so it only sees garbage that BURIES someone. Garbage that merely SLOWS an"
          "\n  opponent still ends the match with reason='clear' and is scored as a SPEED win."
          "\n  DEMONSTRATED: chain180 reads 98.4% wins-by-clearing here, yet its edge collapses"
          "\n  70.9% -> 54.0% when garbage is switched OFF. The garbage ON/OFF ABLATION, not"
          "\n  this table, is the estimator for garbage's role. (cascade-search's correction.)"
          "\n\n  READ IT THIS WAY: if the win came from ROBUSTNESS, self-topout losses are"
          "\n  near zero. If it came from ATTACKING, opponent-topout wins dominate. If"
          "\n  neither, lnk1 is simply out-clearing and the channel is SPEED — in which"
          "\n  case the VS win is the SOLO improvement showing through, not a VS effect.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         "/home/struktured/projects/dr-mario-qa-wt/tmp/selfplay/lnk1_permatch.jsonl")
