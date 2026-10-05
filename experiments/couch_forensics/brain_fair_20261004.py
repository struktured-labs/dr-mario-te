"""2026-10-04 couch, every game: the AI seat vs the SILICON-FAITHFUL brain (braingap Leaf6FwDecider, all firmware
switches on; dist_target60, w_chain 540, ws 20, tap 2, reach mask at the true pill index).

  (1) per pill: brain choice, classify_g2 category (MATCH / LATE-FLIP / SHORT-LANDING / TUCK / OTHER / PROPH-ESCAPE),
      hybrid proxy (silicon orientation == brain's at a different column, or brain's column at a different
      orientation, on a straight-drop miss) -> cases_fair_20261004_brain.jsonl
  (2) OPENING counterfactual: from the game's first pill, the brain alone places the observed capsule sequence by
      straight drop (perfect execution, NO garbage: an opening-only probe) for the pills silicon placed in its first
      60 s / 120 s, and counts the attacks it would have sent (ROM comboCounter, fair_20261004.count_runs). Same
      layout + same capsules for both, so per game "silicon sends - brain sends" separates the build's execution
      from the layout/capsule luck.

The brain models fw 1488e158's main search (FAIR). FAIR2's fw c51d2e21 (V11) = 1488 + TUCKREACH + TUCKLIVE + ROOTORD
(+ LEFLUSH, an RTL-state fix): the main search is the same, tucks and root order differ. So for FAIR2 the brain is an
approximation on tuck boards (the M4 G2 co-sim, cosim_m4g2_fair_20261004.jsonl, is the exact V11 answer there).

Usage: python brain_fair_20261004.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "braingap")))
import rtlengine_braingap_20261003 as E  # noqa: E402,F401
sys.path.insert(0, E.CVX)
sys.path.insert(0, HERE)
os.chdir(HERE)
import analyze_g2 as A  # noqa: E402
import cascade_leaf6fw_braingap_20261003 as F  # noqa: E402
from drmario.faithful_game import Pill  # noqa: E402
from endgame_dist60_20261003 import after, pose_of, summ  # noqa: E402
from g2_tapout_dist60_20261003 import category  # noqa: E402
import fair_20261004 as FA  # noqa: E402


def brain():
    import fast_rtl_x as FX
    import cascade_chain_x as C
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    return F.Leaf6FwDecider(w, fl, sw=None, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, mode="dist_target", W=60, vk=4)


def load(g):
    t_round, t_end, final = FA.window(g)
    R = [json.loads(l) for l in open(os.path.join(FA.SCAN, f"rawh_{g}_p2.jsonl"))]
    R = [r for r in R if 0 not in r["cur"] and 0 not in r["nxt"] and t_round <= r["t_spawn"] <= t_end]
    for p, r in enumerate(R):
        r["p"] = p
    fixes = FA.repair(R)
    return R, fixes


def main():
    dec = brain()
    rows, summ_rows = [], []
    for g, build, m, gi, rec, log in FA.GAMES:
        R, fixes = load(g)
        L = [r for r in R if r["landing"] is not None]
        t0 = R[0]["t_spawn"]
        cats = Counter()
        for r in L:
            S = r["S"]; b = A.board_from_strings(S["color"], S["virus"], S["link"])
            cur, nxt = tuple(r["cur"]), tuple(r["nxt"])
            o, orow, ocol, ocl = r["landing"]
            actual = [o, ocol, list(ocl), orow]
            act_a = next((a for a in range(32) if pose_of(a, cur, b) == actual), None)
            a_sim = dec.choose(b.clone(), Pill(*cur), Pill(*nxt), r["p"])
            sim = pose_of(a_sim, cur, b) if a_sim is not None else None
            if r.get("landing_repaired") or not r["traj"]:
                cat, det = ("NOTRAJ", {}) if sim != actual else ("MATCH", {})
            else:
                cat, det = category(sim, actual, act_a is not None, r["traj"], r["t_spawn"], S["color"]) if sim else ("NOMOVE", {})
            hyb = bool(sim and act_a is not None and cat not in ("MATCH",) and
                       ((sim[0] == actual[0] and sim[1] != actual[1]) or (sim[0] != actual[0] and sim[1] == actual[1])))
            h = FA.heights(FA.grid(S["color"]))
            cats[cat] += 1
            rows.append({"game": g, "build": build, "p": r["p"], "t_rel": round(r["t_spawn"] - t0, 3), "virus_count": r["virus_count"],
                         "maxh": max(h), "actual": actual, "actual_action": act_a, "sim": sim, "sim_action": a_sim,
                         "category": cat, "detail": det, "hybrid_proxy": hyb})
        # opening counterfactual: brain alone on the observed capsules, no garbage
        out = {}
        for w in (30, 60, 120):
            n_pills = sum(1 for r in R if r["t_spawn"] - t0 <= w)
            b = A.board_from_strings(R[0]["S"]["color"], R[0]["S"]["virus"], R[0]["S"]["link"])
            sent_v = sent_c = 0; v0 = int(b.is_virus.sum()); alive = True
            for r in R[:n_pills]:
                if b.spawn_blocked():
                    alive = False; break
                a = dec.choose(b.clone(), Pill(*r["cur"]), Pill(*r["nxt"]), r["p"])
                if a is None:
                    alive = False; break
                bb, st = after(b, pose_of(a, tuple(r["cur"]), b))
                if bb is None:
                    alive = False; break
                b = bb
                s = summ(st)["sent"]
                sent_v += s > 0; sent_c += s
                if b.virus_count() == 0:
                    break
            out[str(w)] = {"pills": n_pills, "brain_sent_volleys": sent_v, "brain_sent_cells": sent_c,
                           "brain_viruses_cleared": v0 - int(b.is_virus.sum()), "alive": alive}
        n = sum(cats.values())
        summ_rows.append({"game": g, "build": build, "n": n, "categories": dict(cats),
                          "match_pct": round(100 * cats["MATCH"] / max(n, 1), 1),
                          "late_flip": cats["LATE-FLIP"], "hybrid_proxy": sum(1 for q in rows if q["game"] == g and q["hybrid_proxy"]),
                          "repairs": len(fixes), "opening_brain_only": out})
        print(g, build, json.dumps(summ_rows[-1]), flush=True)
    with open(os.path.join(HERE, "cases_fair_20261004_brain.jsonl"), "w") as fh:
        for q in rows:
            fh.write(json.dumps(q) + "\n")
    json.dump(summ_rows, open(os.path.join(HERE, "brain_fair_20261004.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
