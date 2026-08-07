#!/usr/bin/env python3
"""Tier-3 VS harness: champion (P2's shipped decide path, strand180_20) vs an
opponent policy, scored on the CHAMPION'S DEATH RATE -- not win rate. This is the
one new thing this program needs beyond what already exists: everything else is
reused wholesale.

REUSE, NOT REBUILD: the match loop is `vs_harness.play_match`
(/home/struktured/projects/dr_mario_rl/tmp/vs_aware/vs_harness.py), the SAME
ROM-true garbage-channel match loop h2h_vs.py uses -- side-swap seed pairing,
comboCounter-summed-across-cascade attack rule, gravity-before-resolve garbage
drop, receiver timing, all inherited unmodified. No second match loop is written
here (the project has been burned by exactly that fragmentation before: memory
dr-mario-rom-attack-rule / vs_harness.py's own docstring, "five mechanics bugs
survived simultaneously because ... each kept a private copy of this loop").
`experiments/adversary/` (Tier 1/2's directory) did not exist yet at the time
this was written -- if `adversary_harness.py` appears there later, diff it
against this file rather than assuming divergence.

DEATH, precisely (not "loss"): a player who loses a match by their OPPONENT
achieving a "clear" first was simply outraced -- their own board was never
threatened. A player who loses via "topout" (board overflow) or "no-move" (no
legal placement, effectively the same failure) was KILLED. The adversary's
fitness is the champion's KILL rate, and "stall" (draw, both hit the pill cap)
counts as neither a death nor survival-by-victory -- it is dropped from the
death-rate denominator's numerator but stays in n.
"""
from __future__ import annotations

import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/tmp/vs_aware",
           ROOT + "/.claude/worktrees/faithful-sim/src", QA, QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import vs_harness as H
from cascade_stranded_x import StrandedChainD3Decider
from cascade_chain_x import ChainRewardD3Decider
from adversary_search import AdversaryD3Decider, warmup_adv
import fast_rtl_x as FX
from fast_sim_x import FastDecider, weights_r47


def champion_decider(topk2=8):
    """The shipped strand180_20 VS decider, pinned by value. See adversary_search.py
    module docstring for the h2h_vs.py "strand180_20" / silicon cross-reference."""
    w, fl = FX.variant("winner")
    return StrandedChainD3Decider(w, fl, topk2=topk2, maxpass=0, w_chain=180, ws=20)


def pre_strand20_champion(topk2=8):
    """The champion's OWN lineage one step back: chain180, no stranded term at all
    (ws=0 -- NOT StrandedChainD3Decider with ws=0, which is the same decider family;
    using ChainRewardD3Decider directly is the literal pre-#47 shipped Combo Stomper,
    memory dr-mario-stomper-shipped-silicon). Used for the transfer test."""
    w, fl = FX.variant("winner")
    return ChainRewardD3Decider(w, fl, topk2=topk2, maxpass=0, w_chain=180)


def native_d1_opponent():
    """Offline-sim stand-in for the CvC cart's DRP1NATIVE (a deliberately-slow, NOT
    opponent-aware, native 6502 depth-1 AI -- memory/personality doc: 'intentionally
    artless ... the warm-up dummy'). fast_sim_x.FastDecider(depth=1) is the closest
    offline equivalent: same POLICY CLASS (blind depth-1 argmax, legacy weight
    vector), not literal 6502 -- see the honesty note in ADVERSARY_T3.md about
    offline-sim vs RTL disagreement before calling anything about DRP1NATIVE from
    this number alone."""
    return FastDecider(weights_r47(), depth=1)


def warmup_all(topk2=8):
    warmup_adv(topk2=topk2)
    import cascade_chain_x as C
    C.warmup_chain(topk2=topk2)


def _outcome(r, champ_side):
    """Extract champion-centric metrics from one vs_harness.play_match() result."""
    other = 1 - champ_side
    win = r["winner"]
    reason = r["reason"]
    stall = (win < 0)
    champ_won = (not stall) and win == champ_side
    champ_lost = (not stall) and win == other
    champ_died = champ_lost and reason in ("topout", "no-move")
    outraced = champ_lost and reason == "clear"
    vc, vo = r["virus"][champ_side], r["virus"][other]
    dies_ahead = champ_died and (vc < vo)
    pills_to_clear = r["pills"][champ_side] if (champ_won and reason == "clear") else None
    return {
        "stall": stall, "champ_won": champ_won, "champ_lost": champ_lost,
        "champ_died": champ_died, "outraced": outraced, "dies_ahead": dies_ahead,
        "reason": reason, "virus_champ": vc, "virus_opp": vo,
        "pills_champ": r["pills"][champ_side], "pills_opp": r["pills"][other],
        "pills_to_clear": pills_to_clear,
        "atk_sent_champ": r["attacks"][other], "atk_sent_opp": r["attacks"][champ_side],
    }


def play_seed(seed, champ_dec, opp_dec, level=11, max_pills=300, garbage=True):
    """One seed, played BOTH ways (champion as P0 then as P1) -- side-swap pairing,
    same discipline as h2h_vs.py. Returns the champion-centric metrics AVERAGED
    (booleans -> fraction in {0, 0.5, 1}) across the two matches of this seed, which
    is the unit of statistical analysis (the two matches of a seed are not
    independent -- see h2h_vs.py's module docstring)."""
    def _wrap(dec):
        if getattr(dec, "_opponent_aware", False):
            return lambda b, c, n, opp: dec.choose(b, c, n, opp)
        return H.blind(dec)

    dec_champ = _wrap(champ_dec)
    dec_opp = _wrap(opp_dec)

    r0 = H.play_match(seed, dec_champ, dec_opp, level=level, max_pills=max_pills,
                      garbage=garbage)
    o0 = _outcome(r0, champ_side=0)
    r1 = H.play_match(seed, dec_opp, dec_champ, level=level, max_pills=max_pills,
                      garbage=garbage)
    o1 = _outcome(r1, champ_side=1)

    def avg(key):
        a, b = o0[key], o1[key]
        if isinstance(a, bool):
            return (int(a) + int(b)) / 2.0
        return (a + b) / 2.0

    ptc = [x for x in (o0["pills_to_clear"], o1["pills_to_clear"]) if x is not None]
    return {
        "seed": seed,
        "champ_died": avg("champ_died"), "champ_won": avg("champ_won"),
        "stall": avg("stall"), "outraced": avg("outraced"),
        "dies_ahead": avg("dies_ahead"),
        "pills_to_clear": (sum(ptc) / len(ptc)) if ptc else None,
        "atk_sent_champ": avg("atk_sent_champ"), "atk_sent_opp": avg("atk_sent_opp"),
        "raw": [o0, o1],
    }


# AdversaryD3Decider is inherently opponent-aware; mark it so play_seed doesn't blind it.
AdversaryD3Decider._opponent_aware = True


if __name__ == "__main__":
    import time
    warmup_all()
    champ = champion_decider()
    adv = AdversaryD3Decider.from_vector((180, 20, 0, 0, 0), *FX.variant("winner"))
    t0 = time.time()
    rows = [play_seed(s, champ, adv) for s in range(400, 403)]
    dt = time.time() - t0
    for r in rows:
        print(f"seed={r['seed']} died={r['champ_died']:.1f} won={r['champ_won']:.1f} "
              f"stall={r['stall']:.1f} outraced={r['outraced']:.1f} "
              f"dies_ahead={r['dies_ahead']:.1f} ptc={r['pills_to_clear']}")
    print(f"{dt:.1f}s for {len(rows)} seeds x2 matches = {dt/len(rows)/2:.2f}s/match")
