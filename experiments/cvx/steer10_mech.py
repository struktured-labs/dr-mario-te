#!/usr/bin/env python3
"""STEER10 step 1: MECHANISM CHECK of the candidate rules (rules_steer10.py) on the BANKED couch cases, before any sim
game.

Games (per-AI-pill cases, observed boards / capsules / garbage, hidden-spawn tracker + repair, as banked):
  lulu 10/05 (couch_forensics/cases_ai_<g>_lulu_20261005.jsonl): her wins m1g2 (stall 7), m1g4 (16), m2g3 (13);
      the AI's wins m1g1, m1g3, m1g5, m2g1, m2g2, m2g4 (harm check)
  m5g2 10/04 (owner full clear; col 6/7 walled): steer10/mech/cases_ai_m5g2_fair_20261004.jsonl, generated with the
      same code path (m4g2_fair_20261004.cases, GAME=m5g2) -- cases_stall_m5g2 has no boards.

  replay  VARIANT GAME OUT   brain-only replays (g2_counterfactual_dist60_20261003.replay: the decider places every
          OBSERVED capsule by straight drop, the OBSERVED garbage dropped after the same pill, perfect execution) from
          the banked start grid (replay_<g>_lulu_20261005.jsonl p0s; m1g4 + replay_early; m5g2 every 5th pill).
          Outcome per start, as replaysum_lulu_20261005: AI-WIN (clears within the observed capsules, or alive when
          she topped out), AI-LOSS (tops out, or alive when she cleared), OPEN (capsules run out; games the AI won).
  decide  VARIANT OUT        on EVERY observed board: the variant's action vs the base brain's, the rule's activity,
          and whether the variant's landing still puts a cell where silicon's / the base brain's sealing cell went.

  NUMBA_CACHE_DIR=<fresh per variant> python steer10_mech.py replay A_vk12 m1g2 steer10/mech/rep_A_vk12_m1g2.jsonl
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CF = os.path.abspath(os.path.join(HERE, "..", "couch_forensics"))
MECH = os.path.join(HERE, "steer10", "mech")
sys.path.insert(0, HERE)
import rules_steer10 as R  # noqa: E402  (pins import paths)
sys.path.insert(0, CF)

LULU = ("m1g1", "m1g2", "m1g3", "m1g4", "m1g5", "m2g1", "m2g2", "m2g3", "m2g4")
GAMES = LULU + ("m5g2",)

# mechanism-check grid (anecdote-tuned on these boards: DECLARED). base == DIST60 (Leaf6FwDecider) exactly.
VARIANTS = {
    "base": dict(),
    "A_vk8": dict(vk=8), "A_vk12": dict(vk=12), "A_vk16": dict(vk=16), "A_vk12_W120": dict(vk=12, W=120),
    "AE_vk16": dict(tgt="edge", vk=16), "AE_vk48": dict(tgt="edge", vk=48),
    "AK_vk12_kdig3": dict(vk=12, kdig=3),
    "B_eseal150": dict(kind="eseal", P=150, vlo=12), "B_eseal400": dict(kind="eseal", P=400, vlo=12),
    "C_edig60_vk12": dict(kind="edig", P=60, vk_dig=12), "C_edig60_vk16": dict(kind="edig", P=60, vk_dig=16),
    "C_edig120_vk16": dict(kind="edig", P=120, vk_dig=16), "C_edig60_vk16_all": dict(kind="edig", P=60, vk_dig=16, cols_all=1),
    # batch 2 (added after batch 1's reach finding, before any sim game): family (d) EDGE REACH
    "D_reach60_h11": dict(kind="ereach", P=60, h0=11), "D_reach120_h11": dict(kind="ereach", P=120, h0=11),
    "D_reach120_h10": dict(kind="ereach", P=120, h0=10), "D_reach60_h12": dict(kind="ereach", P=60, h0=12),
    "D_reach250_h11": dict(kind="ereach", P=250, h0=11),
    # batch 3 (added after batches 1-2, before any sim game): the combination of the two families that act
    "AD_vk16_reach120_h11": dict(vk=16, kind="ereach", P=120, h0=11),
    "AD_vk16_reach60_h11": dict(vk=16, kind="ereach", P=60, h0=11),
}


def cases(game):
    p = (os.path.join(MECH, "cases_ai_m5g2_fair_20261004.jsonl") if game == "m5g2"
         else os.path.join(CF, f"cases_ai_{game}_lulu_20261005.jsonl"))
    return [json.loads(l) for l in open(p)]


def outcome_info(game):
    """(winner, how) of the real game: lulu games from summary_lulu_20261005.json; m5g2 = the owner cleared."""
    if game == "m5g2":
        return "owner", "cleared"
    S = {g["game"]: g for g in json.load(open(os.path.join(CF, "summary_lulu_20261005.json")))["games"]}[game]
    return S["winner"], S["how"]


def starts(game, Q):
    if game == "m5g2":
        return [q["p"] for q in Q][::5]
    files = [f"replay_{game}_lulu_20261005.jsonl"] + ([f"replay_early_{game}_lulu_20261005.jsonl"] if game == "m1g4" else [])
    out = sorted({json.loads(l)["p0"] for f in files for l in open(os.path.join(CF, f))})
    return out


def classify(end, winner, how):
    if end == "CLEAR":
        return "AI-WIN"
    if end in ("TOPOUT", "NOMOVE"):
        return "AI-LOSS"
    if how == "lulu topped out":
        return "AI-WIN"
    if winner in ("lulu", "owner") and how == "cleared":
        return "AI-LOSS"
    return "OPEN"


def replay_main(var, game, outp):
    import g2_counterfactual_dist60_20261003 as GC
    os.chdir(CF)
    dec = R.make(VARIANTS[var])
    Q = cases(game)
    idx = {q["p"]: i for i, q in enumerate(Q)}
    winner, how = outcome_info(game)
    with open(outp, "w") as fh:
        for p0 in starts(game, Q):
            dec.stats = {k: 0 for k in dec.stats}
            Rr = GC.replay(Q, dec, idx[p0])
            last = Rr[-1]
            rec = {"variant": var, "rule": VARIANTS[var], "game": game, "p0": p0, "end": last[1], "end_p": last[0],
                   "viruses_end": last[2], "max_h_end": max(last[3]), "class": classify(last[1], winner, how),
                   "stats": dict(dec.stats), "trace": [(p, s, v, max(h)) for (p, s, v, h) in Rr]}
            fh.write(json.dumps(rec) + "\n"); fh.flush()


def decide_main(var, outp):
    import analyze_g2 as A
    from drmario.faithful_game import Pill
    from endgame_dist60_20261003 import after, pose_of
    os.chdir(CF)
    dec = R.make(VARIANTS[var]); base = R.base_decider()
    with open(outp, "w") as fh:
        for game in GAMES:
            for q in cases(game):
                S = q["S"]
                b = A.board_from_strings(S["color"], S["virus"], S["link"])
                cur, nxt = Pill(*q["cur"]), Pill(*q["nxt"])
                dec.stats = {k: 0 for k in dec.stats}
                a = dec.choose(b.clone(), cur, nxt, q["p"])
                a0 = base.choose(b.clone(), cur, nxt, q["p"])
                st = dict(dec.stats)
                land = None
                if a is not None:
                    pz = pose_of(a, tuple(q["cur"]), b)
                    land = pz
                fh.write(json.dumps({"variant": var, "game": game, "p": q["p"], "vc": q["virus_count"], "a": a,
                                     "a_base": a0, "a_sil": q.get("actual_action"), "land": land,
                                     "sim_base_banked": q.get("sim_action"), "fired": st["fired"],
                                     "changed": st["changed"], "tgt_diff": st["tgt_diff"]}) + "\n")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "replay":
        replay_main(sys.argv[2], sys.argv[3], os.path.abspath(sys.argv[4]))
    elif mode == "decide":
        decide_main(sys.argv[2], os.path.abspath(sys.argv[3]))
