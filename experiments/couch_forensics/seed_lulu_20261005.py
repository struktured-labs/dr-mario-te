"""Is the copro's SEEDED TIE-BREAK the cause of the silicon-only misses? (2026-10-05 couch, AI = ANTIBODY_DIST_FAIR)

The couch cart rides a per-match tie-break seed on the colour uploads' high nibbles (patch_cartridge_copro.py: SEED2 =
(NAV_T | 1) ^ $A4 on the first play frame of a match, always odd), and the firmware adds a per-root jitter
  val1 += (t ^ (t >> 3)) & 3,  t = seed ^ ((o1 << 3) | c1)          (tests/test_search_d3.py, "seeded tie-break")
before the strict "val1 > best" root comparison. Every replay so far (co-sim pubtrace SEED=0, the python faithful brain,
the Mesen replays fed those timelines) runs seed 0 = jitter OFF. A near-tie within 3 points can therefore resolve
differently on silicon.

Test (per game, no co-sim): the faithful brain's 32 root values (Leaf6FwDecider.vals) on silicon's own boards; for every
odd seed 1..255, apply the jitter in root-visit order (stable key1-desc, the shipped ROOTORD-less order == python
sw_order) and pick the first strict maximum; count silicon == pick. Also per pill: the value gap between the brain's
pick and silicon's landing (<= 3 = a jitter-reachable near-tie).
Usage: python seed_lulu_20261005.py [game ...]  -> seed_lulu_20261005.json, cases_seed_lulu_20261005.jsonl
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m4g2_fair_20261004 as M  # noqa: E402  (pins the braingap paths)
import analyze_g2 as A  # noqa: E402
from drmario.faithful_game import Pill  # noqa: E402

GAMES = ["m1g1", "m1g2", "m1g3", "m1g4", "m1g5", "m2g1", "m2g2", "m2g3", "m2g4"]
VAR_OF_O4 = (2, 3, 0, 1)
O4_OF_VAR = {v: o for o, v in enumerate(VAR_OF_O4)}
NEG = -(1 << 39)


def canon(a):
    return None if a is None else (a // 16) * 16 + a % 8


def jitter(seed, a):
    o1, c1 = O4_OF_VAR[a // 8], a % 8
    t = seed ^ ((o1 << 3) | c1)
    return (t ^ (t >> 3)) & 3


def pick(vals, seed):
    """Strict-max over the evaluated roots after the jitter. Visit order: python's sw_order sorts by key1, which is not
    exposed, so ties AFTER jitter are broken toward the brain's own unjittered pick, then by action index."""
    best, ba = None, None
    for a in range(32):
        if vals[a] <= NEG:
            continue
        v = int(vals[a]) + (jitter(seed, a) if seed else 0)
        if best is None or v > best:
            best, ba = v, a
    return ba, best


def main(games):
    dec = M.brain()
    out, rows = {}, []
    for g in games:
        Q = [json.loads(l) for l in open(os.path.join(HERE, f"cases_ai_{g}_lulu_20261005.jsonl"))]
        V = []
        for q in Q:
            b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
            a0 = dec.choose(b.clone(), Pill(*q["cur"]), Pill(*q["nxt"]), q["p"])
            vals = [int(x) for x in dec.vals]
            sil = q["actual_action"]; sym = q["cur"][0] == q["cur"][1]
            cand = [sil] if sil is not None else []
            if sym and sil is not None:
                cand.append(canon(sil) + 8)
            sv = max((vals[a] for a in cand), default=None)
            gap = (vals[a0] - sv) if (a0 is not None and sv is not None and sv > NEG) else None
            V.append((q, vals, a0, sym))
            rows.append({"game": g, "p": q["p"], "silicon": sil, "brain": a0, "category": q["category"], "gap_brain_minus_silicon": gap,
                         "near_tie_le3": gap is not None and 0 < gap <= 3, "vals": vals})
        res = []
        for seed in range(1, 256, 2):
            hit = 0
            for q, vals, a0, sym in V:
                a, _ = pick(vals, seed)
                if q["actual_action"] is not None and a is not None and (canon(a) == canon(q["actual_action"]) if sym else a == q["actual_action"]):
                    hit += 1
            res.append((hit, seed))
        base = sum(1 for q, vals, a0, sym in V if q["actual_action"] is not None and a0 is not None and
                   (canon(a0) == canon(q["actual_action"]) if sym else a0 == q["actual_action"]))
        res.sort(reverse=True)
        gaps = [r for r in rows if r["game"] == g]
        miss = [r for r in gaps if r["category"] != "MATCH" and r["silicon"] is not None]
        out[g] = {"pills": len(V), "seed0_match": base, "best_seeds": res[:5], "worst_seed": res[-1],
                  "median_seed_match": res[len(res) // 2][0],
                  "misses": len(miss), "misses_within_3": sum(1 for r in miss if r["gap_brain_minus_silicon"] is not None and r["gap_brain_minus_silicon"] <= 3),
                  "misses_gap_hist": sorted(r["gap_brain_minus_silicon"] for r in miss if r["gap_brain_minus_silicon"] is not None)}
        print(g, json.dumps(out[g]), flush=True)
    json.dump(out, open(os.path.join(HERE, "seed_lulu_20261005.json"), "w"), indent=1)
    with open(os.path.join(HERE, "cases_seed_lulu_20261005.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:] or GAMES)
