"""Silicon-vs-sim execution categories (classify_g2 rules) for all four 10/03 match-1 games, sim = DIST60 at the true
pill index. Writes cases_cat_dist60_20261003.jsonl (game, p, t, heights, sim, actual, category, traj summary).
Usage: python categories_dist60_20261003.py"""
import json, collections
import analyze_g2 as A
import fast_rtl_x as FX
import cascade_chain_x as C
from cascade_leaf6_x import Leaf6Decider
from drmario.faithful_game import Pill
from endgame_dist60_20261003 import pose_of
from g2_tapout_dist60_20261003 import category, heights, pill_index as g2_pi

C.warmup_chain(topk2=8)
w, fl = FX.variant("winner")
dec = Leaf6Decider(w, fl, mode="dist_target", W=60, vk=4, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)


def games():
    ld = lambda f: [json.loads(l) for l in open(f)]
    G1 = ld("rawh_dist60_20261003_G1.jsonl"); G2 = ld("rawh_dist60_20261003_G2.jsonl")
    G3 = ld("rawh_dist60_20261003_G3.jsonl"); A4 = ld("rawh_dist60_20261003_G4a.jsonl"); B4 = ld("rawh_dist60_20261003_G4b.jsonl")
    yield "G1", [(r["k"] - 1, r) for r in G1 if r["k"] >= 1]
    yield "G2", [(g2_pi(r["k"]), r) for r in G2 if r["k"] not in (77, 78)]
    yield "G3", [(r["k"] - 1, r) for r in G3 if r["k"] >= 1]
    yield "G4", [(r["k"] - 1, r) for r in A4 if 1 <= r["k"] <= 53] + [(53 + r["k"], r) for r in B4]


rows = []
for g, L in games():
    for p, r in L:
        if r["landing"] is None or 0 in r["cur"] or 0 in r["nxt"] or p < 0:
            continue
        S = r["S"]; b = A.board_from_strings(S["color"], S["virus"], S["link"])
        cur, nxt = tuple(r["cur"]), tuple(r["nxt"])
        o, orow, ocol, ocl = r["landing"]; actual = [o, ocol, list(ocl), orow]
        act_a = next((a for a in range(32) if pose_of(a, cur, b) == actual), None)
        a = dec.choose(b.clone(), Pill(*cur), Pill(*nxt), p)
        sim = pose_of(a, cur, b)
        cat, det = category(sim, actual, act_a is not None, r["traj"], r["t_spawn"], S["color"])
        h = heights(S["color"])
        rows.append({"game": g, "p": p, "t_spawn": r["t_spawn"], "virus_count": S["virus"].count("1"), "heights": h,
                     "maxh": max(h), "lane": max(h[3], h[4]), "sim": sim, "actual": actual, "category": cat, "detail": det})
with open("cases_cat_dist60_20261003.jsonl", "w") as fh:
    for q in rows:
        fh.write(json.dumps(q) + "\n")
for g in ("G1", "G2", "G3", "G4"):
    R = [q for q in rows if q["game"] == g]
    c = collections.Counter(q["category"] for q in R)
    hi = [q for q in R if q["maxh"] >= 12]; lo = [q for q in R if q["maxh"] < 12]
    print(f"{g}: n={len(R)} {dict(c)}  MATCH {100*c['MATCH']/len(R):.0f}%  | maxh>=12: n={len(hi)} MATCH {sum(q['category']=='MATCH' for q in hi)} "
          f"LF {sum(q['category']=='LATE-FLIP' for q in hi)} | maxh<12: n={len(lo)} MATCH {sum(q['category']=='MATCH' for q in lo)} LF {sum(q['category']=='LATE-FLIP' for q in lo)}")
