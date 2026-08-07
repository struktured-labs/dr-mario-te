#!/usr/bin/env python3
"""Kill classification, per the team lead's DMUU framing: for each known
champion death, was the champion OUTPLAYED (no good option existed) or did it
CHOOSE a risk-neutral (higher-expected-value) line when a materially SAFER
line was available among its own near-best candidates?

METHOD: replay each death game with `instrumented_champion.all_candidates()`
recording the FULL candidate list (every legal action, its val, and its
resulting spawn-lane headroom -- spawn_blocked() = row0 cols {3,4} occupied,
so spawn-lane height is the direct topout-proximity metric) at every champion
decision. Look at the LAST N champion decisions before the topout (the "ruin
boundary" the framing describes) and ask, among the TOP-K candidates by the
champion's own val ranking: does any candidate ranked 2..K have LOWER
(safer) spawn-lane height than the #1 (chosen) candidate?

  - YES, and the value gap is small relative to the spread -> RISK-NEUTRAL
    CHOICE: the champion had a materially safer, nearly-as-good option and
    took the higher-EV one anyway. This is the interesting category -- it is
    evidence for objective mis-specification (maximizing expected progress
    instead of P(win)), not for an eval-weight gap.
  - NO safer option existed in the top-K -> OUTPLAYED: every near-best
    option carried similar risk. This is a "correct choice, bad luck /
    genuine skill gap" case, not evidence for the DMUU hypothesis.

K defaults to 8 (topk2, the same top-K the champion's OWN ply-2 pruning
already uses -- a threshold already meaningful to this codebase, not
invented for this analysis).

HONESTY: this runs on the ONLY concrete champion-death games this session's
compute produced (2 from the off-policy rollout corpus + up to 1 from the
evolutionary search's training seeds, if found). n=2-3 is an illustration of
the method, not a statistically powered claim about the split's true
proportion -- say so in the report, don't round it up.
"""
from __future__ import annotations

import sys
import os
import json

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
from vs_run import champion_decider, warmup_all
import fast_rtl_x as FX
from instrumented_champion import all_candidates

TOPK = 8          # same cutoff the champion's own ply-2 pruning uses
LOOKBACK = 40      # classify the last N champion decisions before topout -- widened
                   # from 3, then 15: both showed spawn-lane height already
                   # stuck at 12-15 for the ENTIRE window with no escape in
                   # the champion's own top-K. Widened further to see how far
                   # back the "still had options" period actually extends.


def replay_and_classify(seed, adv_vec, adv_side_guess=None, level=11, max_pills=300):
    """Try both side assignments if adv_side_guess is None; return the first
    that produces a champion topout/no-move death, plus the classification."""
    warmup_all()
    w, fl = FX.variant("winner")
    champ = champion_decider()
    adv = AdversaryD3Decider.from_vector(adv_vec, w, fl, topk2=8)
    adv._opponent_aware = True

    sides = [adv_side_guess] if adv_side_guess is not None else [0, 1]
    for adv_side in sides:
        champ_side = 1 - adv_side
        decisions = []   # per champion decision: (ply, board_snapshot_info)

        def hook(who, e, opp_board, action, took):
            if who != champ_side or action is None:
                return None
            cands = all_candidates(e.board, e.cur, e.nxt, w, fl)
            decisions.append({"action": action, "cands": cands,
                              "own_maxh_before": int(e.board.column_heights().max())})
            return None

        # Both closures already take vs_harness's native 4-arg (board,cur,nxt,opp)
        # signature -- champ's just ignores opp -- so neither needs H.blind().
        dec_champ = lambda b, c, n, opp: champ.choose(b, c, n)
        dec_adv = lambda b, c, n, opp: adv.choose(b, c, n, opp)
        a0, a1 = (dec_champ, dec_adv) if champ_side == 0 else (dec_adv, dec_champ)

        r = H.play_match(seed, a0, a1, level=level, max_pills=max_pills, hook=hook,
                         garbage=True)
        champ_died = (r["winner"] == adv_side) and (r["reason"] in ("topout", "no-move"))
        if champ_died:
            return {"seed": seed, "adv_side": adv_side, "champ_side": champ_side,
                    "result": r, "decisions": decisions}
    return None


def classify_game(rec):
    """Classify the last LOOKBACK champion decisions before its death.

    TWO-TIER classification, because the top-K-only check conflates two very
    different situations: "every option was risky" and "a safe option
    existed but scored so far below the champion's own near-best band that a
    pure risk-neutral ranking would never reach it." Checked separately:

      NO_ESCAPE      -- no candidate among ALL legal placements (not just the
                         top-K) has lower spawn-lane height than the chosen
                         one. Physically boxed in -- outplayed, full stop.
      CHEAP_RISK_NEUTRAL -- a safer candidate exists WITHIN the champion's own
                         top-K (its near-optimal band) -- the champion
                         declined a nearly-as-good, safer move for a better one.
      EXPENSIVE_RISK_NEUTRAL -- a safer candidate exists somewhere in the
                         FULL candidate set, but outside the top-K -- an
                         escape existed, priced by the champion's own eval as
                         costly, and a purely risk-neutral argmax will never
                         take it regardless of the cost. This is the sharpest
                         evidence for the DMUU framing: the champion isn't
                         choosing between "safe" and "a bit more value", it's
                         choosing between "safe at a real cost" and "unsafe
                         for the best score" -- exactly what a hard survival
                         floor (CVaR-style) would override and a pure
                         expected-value maximizer never will.
    """
    decisions = rec["decisions"]
    out = []
    tail = decisions[-LOOKBACK:] if len(decisions) >= LOOKBACK else decisions
    for i, d in enumerate(tail):
        cands = d["cands"]   # already sorted by val descending
        chosen = cands[0]
        topk = cands[:TOPK]
        ply_idx = len(decisions) - len(tail) + i

        all_safer = [c for c in cands[1:] if c["spawnh"] < chosen["spawnh"]]
        if not all_safer:
            out.append({"ply": ply_idx, "classification": "no_escape",
                        "chosen_spawnh": chosen["spawnh"], "n_candidates": len(cands),
                        "note": "no legal placement had lower spawn-lane height"})
            continue

        best_safe_overall = min(all_safer, key=lambda c: c["spawnh"])
        rank_of_safest = cands.index(best_safe_overall)
        val_gap = chosen["val"] - best_safe_overall["val"]
        val_range = cands[0]["val"] - cands[-1]["val"] if len(cands) > 1 else 1
        val_gap_frac = val_gap / val_range if val_range else 0.0
        tier = "cheap_risk_neutral" if rank_of_safest < TOPK else "expensive_risk_neutral"
        out.append({
            "ply": ply_idx, "classification": tier,
            "chosen_spawnh": chosen["spawnh"], "safer_spawnh": best_safe_overall["spawnh"],
            "headroom_gained": chosen["spawnh"] - best_safe_overall["spawnh"],
            "chosen_val": chosen["val"], "safer_val": best_safe_overall["val"],
            "safer_rank": rank_of_safest, "n_candidates": len(cands),
            "val_gap": val_gap, "val_gap_frac_of_full_range": round(val_gap_frac, 3),
        })
    return out


def main():
    cases = [
        {"tag": "rollout_death_1", "seed": 42165, "vec": (247, 21, -25, 192, 38)},
        {"tag": "rollout_death_2", "seed": 42357, "vec": (215, 28, -29, 232, 37)},
        {"tag": "evosearch_death_5005", "seed": 5005, "vec": (234, 20, -31, 233, 37)},
        {"tag": "evosearch_death_5012", "seed": 5012, "vec": (234, 20, -31, 233, 37)},
    ]
    all_results = {}
    for case in cases:
        print(f"\n=== {case['tag']}: seed={case['seed']} adv_vec={case['vec']} ===",
              flush=True)
        rec = replay_and_classify(case["seed"], case["vec"])
        if rec is None:
            print(f"  COULD NOT REPRODUCE the death on replay (both side assignments "
                  f"survived) -- dropping this case", flush=True)
            continue
        cls = classify_game(rec)
        print(f"  champion died as side {rec['champ_side']}, reason={rec['result']['reason']}, "
              f"{len(rec['decisions'])} champion decisions total", flush=True)
        for c in cls:
            print(f"  ply {c['ply']}: {c['classification']} -- {c}", flush=True)
        all_results[case["tag"]] = {
            "seed": case["seed"], "vec": case["vec"], "adv_side": rec["adv_side"],
            "champ_side": rec["champ_side"], "reason": rec["result"]["reason"],
            "n_decisions": len(rec["decisions"]), "classification": cls,
        }

    out_path = os.path.join(HERE, "kill_classification_result.json")
    with open(out_path, "w") as fh:
        json.dump(all_results, fh, indent=2)
    print(f"\nwrote {out_path}")

    from collections import Counter
    counts = Counter(c["classification"] for r in all_results.values()
                     for c in r["classification"])
    n_total = sum(counts.values())
    print(f"\nTOTAL across {len(all_results)} games, last {LOOKBACK} champion decisions "
          f"each (n={n_total} decisions -- illustration of method, not a powered estimate):")
    for k in ("expensive_risk_neutral", "cheap_risk_neutral", "no_escape"):
        print(f"  {k}: {counts.get(k, 0)}")


if __name__ == "__main__":
    main()
