"""Summaries of cases_dist60_20261003.jsonl (endgame_dist60_20261003.py): per-virus endgame table, AI clears, sim
agreement, D trajectory, and the term decomposition of non-D-reducing choices.

Usage: python summary_dist60_20261003.py CASES.jsonl [--vk 4]
"""
from __future__ import annotations

import collections
import json
import sys

import numpy as np

NAMES = ("VIR", "CELLS", "VBON", "CHAIN", "LEAF", "HSV", "DIST", "WIN", "EXHANG", "STRAND", "SHAPE")


def load(p):
    return [json.loads(l) for l in open(p)]


def per_virus(R, game, vk=4):
    L = [q for q in R if q["game"] == game]
    out = []
    for n in range(vk, 0, -1):
        ph = [q for q in L if q["virus_count"] == n]
        if not ph:
            out.append({"n": n, "pills": 0})
            continue
        i0 = L.index(ph[0])
        nxt = next((q for q in L[i0:] if q["virus_count"] < n), None)
        t0 = ph[0]["t_spawn"]
        t1 = nxt["t_spawn"] if nxt is not None else (L[-1]["t_next_spawn"] or L[-1]["t_spawn"])
        span = [q for q in L[i0:] if (nxt is None or q["t_spawn"] < nxt["t_spawn"])]
        cl = [q for q in span if q["mech"] and q["mech"]["cells"] > 0]
        vcl = [q for q in cl if q["mech"]["viruses"] > 0]
        po = [q for q in cl if q["mech"]["viruses"] == 0]
        out.append({"n": n, "t0": t0, "secs": round(t1 - t0, 2), "pills": len(span),
                    "clears": len(cl), "virus_clears": len(vcl), "pill_only_clears": len(po),
                    "pill_only_cells": sum(q["mech"]["cells"] for q in po),
                    "multi_run": sum(1 for q in cl if q["mech"]["runs"] >= 2),
                    "cascades": sum(1 for q in cl if q["mech"]["chain"] >= 2),
                    "sent_volleys": sum(1 for q in cl if q["mech"]["sent"] > 0),
                    "sent_cells": sum(q["mech"]["sent"] for q in cl),
                    "recv_volleys": sum(1 for q in span if q["garbage_recv"]),
                    "recv_cells": sum(q["garbage_recv"] or 0 for q in span),
                    "D_seq": [q.get("D_before") for q in span],
                    "no_dred_pills": sum(1 for q in span if q.get("n_d_reducing") == 0),
                    "sealed_pills": sum(1 for q in span if q.get("D_before") == 16),
                    "dred_avail_not_taken": sum(1 for q in span if (q.get("n_d_reducing") or 0) > 0 and
                                                not (q.get("D_after_actual") is not None and
                                                     (q["D_after_actual"] < q["D_before"] or q["actual_clears_target"]))),
                    "finish_avail_not_taken": sum(1 for q in span if (q.get("n_finishing") or 0) > 0 and
                                                  not q.get("actual_clears_target"))})
    return out


def main(p, vk=4):
    R = load(p)
    print("=== per-virus endgame (AI = P2), from", vk, "viruses to 0 ===")
    for g in sorted(set(q["game"] for q in R)):
        rows = per_virus(R, g, vk)
        for r in rows:
            print(g, json.dumps({k: v for k, v in r.items() if k != "D_seq"}))
            print("    D before each pill:", r.get("D_seq"))
        tot_s = sum(r.get("secs", 0) for r in rows); tot_p = sum(r["pills"] for r in rows)
        print(f"{g} TOTAL {vk}->0: {tot_s:.1f} s, {tot_p} pills")
    print()
    print("=== agreement (pose match, straight drops only) ===")
    for lab, sel in (("all", lambda q: True), ("<=4 viruses", lambda q: q["virus_count"] <= 4),
                     (">4 viruses", lambda q: q["virus_count"] > 4)):
        S = [q for q in R if sel(q)]
        sd = [q for q in S if q["straight_drop"]]
        md = sum(q["match_dist_pose"] for q in sd); mo = sum(q["match_off_pose"] for q in sd)
        dd = sum(q["dist_differs_from_off"] for q in S)
        print(f"{lab}: n={len(S)} straight={len(sd)}  silicon==DIST60 {md}/{len(sd)} ({100*md/max(1,len(sd)):.0f}%)  "
              f"silicon==ANTIBODY {mo}/{len(sd)} ({100*mo/max(1,len(sd)):.0f}%)  DIST60 != ANTIBODY on {dd}/{len(S)}")
        if lab == "<=4 viruses":
            dis = [q for q in sd if q["dist_differs_from_off"]]
            print(f"   on the {len(dis)} DIST!=ANTIBODY straight-drop decisions: silicon==DIST {sum(q['match_dist_pose'] for q in dis)}, "
                  f"==ANTIBODY {sum(q['match_off_pose'] for q in dis)}")
            for q in dis:
                print(f"     {q['game']} p{q['p']} t{q['t_spawn']} D{q.get('D_before')} dist {q['dist_pose']} (D->{q.get('dist_choice_d_after')}) "
                      f"off {q['off_pose']} (D->{q.get('off_choice_d_after')}) silicon {q['actual']}")
    print()
    print("=== <=4-virus decisions: does the sim (DIST60) take a D-reducing move when one exists? ===")
    E = [q for q in R if q.get("D_before") is not None]
    have = [q for q in E if q["n_d_reducing"] > 0]
    took = [q for q in have if q["best_dred_action"] is not None and
            (q["dist_choice_d_after"] < q["D_before"] or q["dist_choice_clears_target"])]
    print(f"decisions {len(E)}; with >=1 D-reducing root move {len(have)}; DIST60 took one {len(took)}; "
          f"with a finishing move {sum(1 for q in E if q['n_finishing'] > 0)}, DIST60 finished "
          f"{sum(1 for q in E if q['n_finishing'] > 0 and q['dist_choice_clears_target'])}")
    print(f"no D-reducing root move at all: {sum(1 for q in E if q['n_d_reducing'] == 0)} "
          f"(of which target sealed D=16: {sum(1 for q in E if q['n_d_reducing'] == 0 and q['D_before'] == 16)})")
    miss = [q for q in have if q not in took]
    print(f"--- decomposition: chosen - best D-reducing, {len(miss)} decisions ---")
    acc = collections.defaultdict(list)
    for q in miss:
        d = {k: q["comp_chosen"][k] - q["comp_best_dred"][k] for k in NAMES}
        for k in NAMES:
            acc[k].append(d[k])
        top = sorted(d.items(), key=lambda kv: -kv[1])[:3]
        print(f"  {q['game']} p{q['p']} t{q['t_spawn']} nv{q['virus_count']} D{q['D_before']} cur{q['cur']} nxt{q['nxt']} "
              f"chosen {q['dist_pose']} (D->{q['dist_choice_d_after']}, mech {q['dist_choice_mech']['cells']}c/{q['dist_choice_mech']['chain']}ch) "
              f"vs {q['best_dred_pose']} (D->{q['best_dred_d_after']}) margin {q['val_chosen'] - q['val_best_dred']}: "
              + " ".join(f"{k}{v:+.0f}" for k, v in d.items() if abs(v) >= 1))
    if miss:
        print("  mean:", " ".join(f"{k}{np.mean(v):+.0f}" for k, v in acc.items() if abs(np.mean(v)) >= 0.5))
    # chain component inside chosen PVs in the endgame
    print()
    print("=== CHAIN/CELLS share of the chosen move's value (<=4 viruses), by whether a D-reducing move existed ===")
    for lab, S in (("D-reducing existed", have), ("none existed", [q for q in E if q["n_d_reducing"] == 0])):
        ch = [q["comp_chosen"]["CHAIN"] for q in S]; ce = [q["comp_chosen"]["CELLS"] for q in S]
        di = [q["comp_chosen"]["DIST"] for q in S]
        print(f"{lab}: n={len(S)}  PV CHAIN>0 in {sum(1 for x in ch if x > 0)}  mean CHAIN {np.mean(ch) if ch else 0:.0f}  "
              f"mean CELLS {np.mean(ce) if ce else 0:.0f}  mean DIST {np.mean(di) if di else 0:.0f}")


if __name__ == "__main__":
    vk = 4
    if "--vk" in sys.argv:
        vk = int(sys.argv[sys.argv.index("--vk") + 1])
    main(sys.argv[1], vk)
