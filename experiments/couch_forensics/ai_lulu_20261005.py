"""2026-10-05 couch, the AI seat (ANTIBODY_DIST_FAIR = cart dbbb5007 + rbf 318607aa, fw 1488e158) in all 9 games vs dr. lulu.

Per game, from the banked per-pill cases (cases_ai_<game>_lulu_20261005.jsonl: silicon landing vs the SILICON-FAITHFUL
brain Leaf6FwDecider, classify_g2 category), the Verilator co-sim publish timeline of the shipped copro on silicon's own
boards (pubtrace_<game>_lulu_20261005.jsonl), and the chained + silicon-garbage Mesen replays of the REAL carts
(execfid_probe.lua; dbbb5007 = FAIR as played, 5b3d8183 = FAIRPLUS = + DRLGPRESTART + DRDISTROW=2):

  fidelity   silicon == faithful brain; every miss gets ONE label, first match wins:
               TUCK          silicon not a straight drop
               PREV-TARGET   after a garbage window, silicon replayed the PREVIOUS pill's (col, orient) and that is
                             neither the brain nor the copro final (execfid prevtarget.py census, verbatim)
               CLAMP-SLAM    the FAIR Mesen replay lands where silicon did AND logs a DISTGATE clamp-slam on it
                             (execfid clampslam.py)
               LATE-FLIP     classify_g2: held the brain's target >= 4 frames, then flipped
               SHORT-LANDING classify_g2: stopped short of the brain's column, toward it, same orientation
               HYBRID        co-sim: silicon is none of the copro's published candidates nor its final
               COPRO!=BRAIN  silicon == the co-sim copro final, which differs from the python faithful brain
                             (a brain-model residual, not an execution miss)
               EARLIER-PUB   silicon == an earlier copro publish (late answer not taken: LATEGUARD / no time)
               OTHER
  co-sim     m4g2_fair_20261004.cosim categories (FINAL / AT-GATE / OTHER-PUB / HYBRID / TUCK)
  replay     Mesen FAIR vs FAIRPLUS: landing == silicon / == copro final / hybrid (report.py's definition)
  prevtgt    pills after a garbage window, previous-target executions on silicon; Mesen FAIR reproduces; FAIRPLUS lands
             the copro final
  stalls     runs of >= 10 consecutive AI placements at one virus count (time, pills)
Writes cases_ai_fidelity_lulu_20261005.jsonl (one row per AI pill) + ai_lulu_20261005.json; prints the tables.
Usage: python ai_lulu_20261005.py [game ...]
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
XF = os.path.abspath(os.path.join(HERE, "..", "execfid"))
sys.path.insert(0, XF)
import report as XR  # noqa: E402  (execfid: landings())
import prevtarget as PT  # noqa: E402  (paths hook only; the census below handles same-colour aliasing)
import clampslam as CS  # noqa: E402

FX = "/home/struktured/projects/dr_mario_rl/tmp/lulu_20261005/fx"
RUNS = os.path.join(FX, "execfid", "runs")
GAMES = ["m1g1", "m1g2", "m1g3", "m1g4", "m1g5", "m2g1", "m2g2", "m2g3", "m2g4"]


def cases_path(g):
    return os.path.join(HERE, f"cases_ai_{g}_lulu_20261005.jsonl")


def pub_path(g):
    p = os.path.join(HERE, f"pubtrace_{g}_lulu_20261005.jsonl")
    return p if os.path.exists(p) else os.path.join(FX, "timelines", f"pubtrace_{g}_lulu_20261005.jsonl")


PT.paths = lambda g: (cases_path(g), pub_path(g))


def canon(a):
    """A same-colour capsule has two action indices per pose: a and a+8 (H 0-7 == 8-15, V 16-23 == 24-31; checked with
    endgame_dist60.pose_of). The tracker reports the low one; the copro / Mesen may report either."""
    return None if a is None else (a // 16) * 16 + a % 8


def same(a, b, sym):
    if a is None or b is None:
        return a is b
    return canon(a) == canon(b) if sym else a == b


def census(g, Q, T):
    """execfid prevtarget.census, with same-colour aliasing handled: after a garbage window (the previous AI pill
    received garbage), silicon == the previous pill's target (same action index; canonical when either capsule is
    same-colour) and != the brain and != the copro final. (The verbatim census compares raw indices, so it misses a
    previous-target execution of a YY/RR/BB capsule whose stored index is the other alias, e.g. 10/05 M1 G4 p61.)"""
    import timing as TM
    qi = {q["p"]: q for q in Q}
    rows = []
    for q in Q:
        prev = qi.get(q["p"] - 1)
        if prev is None or prev.get("actual_action") is None or q.get("actual_action") is None:
            continue
        sym = q["cur"][0] == q["cur"][1] or prev["cur"][0] == prev["cur"][1]
        symq = q["cur"][0] == q["cur"][1]
        garb = (prev.get("garbage_recv") or 0) > 0
        fin = T[q["p"]]["final"][2] if q["p"] in T else None
        s_ = TM.sil_events(q)
        same_prev = same(q["actual_action"], prev["actual_action"], sym)
        bug = garb and same_prev and not same(q["actual_action"], fin, symq) and not same(q["actual_action"], q.get("sim_action"), symq)
        rows.append(dict(game=g, p=q["p"], garb=garb, same_prev=same_prev, prev_target=bug, sil=q["actual_action"],
                         prev=prev["actual_action"], brain=q.get("sim_action"), final=fin, sym=symq,
                         lat1=s_ and s_["lat1"], drop1=s_ and s_["drop1"],
                         interval=round((q["t_spawn"] - prev["t_spawn"]) * 60)))
    return rows


def run_log(g, cart):
    tag = f"lulu1005_{g}_{cart}_chain_garb"
    p = os.path.join(RUNS, tag, f"lateflip_{tag}.log")
    if os.path.exists(p) and any(l.startswith("SUMMARY") for l in open(p, errors="replace")):
        return p
    return None


def cosim_cat(q, t):
    sym = q["cur"][0] == q["cur"][1]
    sil = q["actual_action"]; fin = t["final"][2]
    pubs = [x[3] for x in t["pubs"]]
    gate = [x for x in t["pubs"] if x[0] <= 6.0]
    at_gate = gate[-1][3] if gate else None
    if sil is None:
        return "TUCK"
    if same(sil, fin, sym):
        return "FINAL"
    if at_gate is not None and same(sil, at_gate, sym):
        return "AT-GATE"
    if any(same(sil, x, sym) for x in pubs):
        return "OTHER-PUB"
    return "HYBRID"


def landings(log, pub, Q):
    """report.landings with same-colour aliasing: act/fin/sil compared canonically for YY/RR/BB capsules."""
    L = XR.landings(log, pub)
    T = {t["p"]: t for t in map(json.loads, open(pub))}
    qi = {q["p"]: q for q in Q}
    for p, v in L.items():
        sym = p in qi and qi[p]["cur"][0] == qi[p]["cur"][1]
        sil = None if v["sil"] in ("-1", "None") else int(v["sil"])
        v["eq_sil"] = same(v["act"], sil, sym)
        v["eq_fin"] = same(v["act"], v["fin"], sym)
        v["hyb"] = p in T and not v["eq_fin"] and not any(same(v["act"], x[3], sym) for x in T[p]["pubs"])
    return L


def game(g):
    Q = [json.loads(l) for l in open(cases_path(g))]
    T = {t["p"]: t for t in map(json.loads, open(pub_path(g)))} if os.path.exists(pub_path(g)) else {}
    prev_rows = census(g, Q, T)
    bug = [r for r in prev_rows if r["prev_target"]]
    bugp = {r["p"] for r in bug}
    logD, logP = run_log(g, "D"), run_log(g, "P")
    LD = landings(logD, pub_path(g), Q) if logD else {}
    LP = landings(logP, pub_path(g), Q) if logP else {}
    clamps = {r["p"]: r for r in CS.scan(logD) if r["ev"]} if logD else {}
    rows = []
    for q in Q:
        p = q["p"]; t = T.get(p)
        cc = cosim_cat(q, t) if t else None
        fin = t["final"][2] if t else None
        if q["category"] == "MATCH":
            lab = "MATCH"
        elif q["actual_action"] is None:
            lab = "TUCK"
        elif p in bugp:
            lab = "PREV-TARGET"
        elif p in clamps and LD.get(p, {}).get("eq_sil"):
            lab = "CLAMP-SLAM"
        elif q["category"] == "LATE-FLIP":
            lab = "LATE-FLIP"
        elif q["category"] == "SHORT-LANDING":
            lab = "SHORT-LANDING"
        elif cc == "HYBRID":
            lab = "HYBRID"
        elif cc == "FINAL":
            lab = "COPRO!=BRAIN"
        elif cc in ("AT-GATE", "OTHER-PUB"):
            lab = "EARLIER-PUB"
        else:
            lab = "OTHER"
        rows.append({"game": g, "p": p, "t_rel": q["t_rel"], "virus_count": q["virus_count"], "maxh": q["maxh"],
                     "category_brain": q["category"], "label": lab, "cosim": cc, "silicon": q["actual_action"], "cur": q["cur"],
                     "brain": q["sim_action"], "copro_final": fin,
                     "brain_eq_final": same(q["sim_action"], fin, q["cur"][0] == q["cur"][1]) if t else None,
                     "garbage_recv": q["garbage_recv"], "prev_target": p in bugp,
                     "mesen_fair": LD.get(p, {}).get("act"), "mesen_fair_eq_sil": LD.get(p, {}).get("eq_sil"),
                     "mesen_fair_eq_final": LD.get(p, {}).get("eq_fin"), "mesen_fair_hybrid": LD.get(p, {}).get("hyb"),
                     "mesen_fairplus": LP.get(p, {}).get("act"), "mesen_fairplus_eq_final": LP.get(p, {}).get("eq_fin"),
                     "mesen_fairplus_hybrid": LP.get(p, {}).get("hyb"),
                     "clamp_fair": (clamps[p]["ev"] if p in clamps else None)})
    # every silicon miss vs the faithful brain, banked with what a dedicated lane needs (board, capsules, silicon
    # trajectory, the co-sim publish timeline, Mesen FAIR / FAIRPLUS / delayed-answer landings). silicon_only = the FAIR
    # Mesen replay of the SAME cart does not land where silicon did (None = no Mesen run for this game).
    delays = {}
    for d in (2, 5, 10):
        tag = f"lulu1005_{g}_D_delay{d}_chain_garb"
        lp = os.path.join(RUNS, tag, f"lateflip_{tag}.log"); dp = os.path.join(FX, "timelines", f"delay{d}_{g}.jsonl")
        if os.path.exists(lp) and any(l.startswith("SUMMARY") for l in open(lp, errors="replace")):
            delays[d] = landings(lp, dp, Q)
    qi = {q["p"]: q for q in Q}
    misses = []
    for r in rows:
        if r["label"] == "MATCH":
            continue
        q = qi[r["p"]]; t = T.get(r["p"])
        misses.append({**{k: r[k] for k in ("game", "p", "t_rel", "virus_count", "maxh", "label", "category_brain", "cosim",
                                             "silicon", "brain", "copro_final", "garbage_recv", "prev_target")},
                       "t_spawn": q["t_spawn"], "S": q["S"], "cur": q["cur"], "nxt": q["nxt"], "actual": q["actual"], "sim": q["sim"],
                       "after_garbage_window": bool(qi.get(r["p"] - 1, {}).get("garbage_recv")),
                       "silicon_traj": q["traj"], "pubs": t["pubs"] if t else None, "done_f": t["done_f"] if t else None,
                       "tuck": t.get("tuck") if t else None, "upload": t["upload"] if t else None,
                       "mesen_fair": r["mesen_fair"], "mesen_fair_eq_sil": r["mesen_fair_eq_sil"],
                       "mesen_fairplus": r["mesen_fairplus"], "mesen_fairplus_eq_final": r["mesen_fairplus_eq_final"],
                       "mesen_fair_delayed": {str(d): {"act": L.get(r["p"], {}).get("act"), "eq_sil": L.get(r["p"], {}).get("eq_sil")}
                                              for d, L in delays.items()} or None,
                       "silicon_only": (None if not LD or r["p"] not in LD or q["actual_action"] is None else not LD[r["p"]]["eq_sil"])})
    n = len(rows)
    lab = Counter(r["label"] for r in rows)
    cos = Counter(r["cosim"] for r in rows if r["cosim"])
    G = [r for r in prev_rows if r["garb"]]
    stalls = []; i = 0
    while i < n:
        j = i
        while j + 1 < n and rows[j + 1]["virus_count"] == rows[i]["virus_count"]:
            j += 1
        if j - i + 1 >= 10:
            t_to = rows[j + 1]["t_rel"] if j + 1 < n else rows[j]["t_rel"]
            stalls.append({"p_from": rows[i]["p"], "p_to": rows[j]["p"], "pills": j - i + 1, "viruses": rows[i]["virus_count"],
                           "t_from": rows[i]["t_rel"], "seconds": round(t_to - rows[i]["t_rel"], 1),
                           "silicon_eq_brain": sum(1 for r in rows[i:j + 1] if r["label"] == "MATCH"),
                           "ends_game": j + 1 >= n})
        i = j + 1

    def rep(L):
        if not L:
            return None
        return {"n": len(L), "eq_silicon": sum(bool(v["eq_sil"]) for v in L.values()),
                "eq_final": sum(bool(v["eq_fin"]) for v in L.values()), "hybrid": sum(bool(v["hyb"]) for v in L.values())}
    summ = {"game": g, "pills": n, "silicon_eq_brain": lab["MATCH"], "pct": round(100 * lab["MATCH"] / n, 1),
            "labels": dict(lab), "cosim": dict(cos),
            "copro_final_eq_brain": sum(1 for r in rows if r["brain_eq_final"]), "with_cosim": sum(1 for r in rows if r["cosim"]),
            "after_garbage_pills": len(G), "prev_target": len(bug),
            "prev_target_mesen_fair_reproduces": sum(1 for r in bug if LD.get(r["p"], {}).get("eq_sil")),
            "prev_target_fairplus_lands_final": sum(1 for r in bug if LP.get(r["p"], {}).get("eq_fin")),
            "clamp_slams_fair_mesen": len(clamps),
            "replay_fair": rep(LD), "replay_fairplus": rep(LP), "stalls": stalls,
            "misses": len(misses), "silicon_only_misses": sum(1 for m in misses if m["silicon_only"]),
            "silicon_only_by_label": dict(Counter(m["label"] for m in misses if m["silicon_only"])),
            "mesen_reproduced_misses": sum(1 for m in misses if m["silicon_only"] is False)}
    return summ, rows, misses


def main(games):
    out, allrows, allmiss = [], [], []
    for g in games:
        if not os.path.exists(cases_path(g)):
            continue
        s, rows, misses = game(g)
        out.append(s); allrows += rows; allmiss += misses
        print(f"{g}: pills {s['pills']} silicon==brain {s['silicon_eq_brain']} ({s['pct']}%) labels {s['labels']}")
        print(f"     co-sim {s['cosim']} copro final==brain {s['copro_final_eq_brain']}/{s['with_cosim']} | after-garbage {s['after_garbage_pills']}"
              f" prev-target {s['prev_target']} (Mesen FAIR reproduces {s['prev_target_mesen_fair_reproduces']}, FAIRPLUS lands final "
              f"{s['prev_target_fairplus_lands_final']}) | clamp-slams {s['clamp_slams_fair_mesen']}")
        print(f"     replay FAIR {s['replay_fair']}  FAIRPLUS {s['replay_fairplus']} | misses {s['misses']}: silicon-only "
              f"{s['silicon_only_misses']} {s['silicon_only_by_label']}, Mesen-reproduced {s['mesen_reproduced_misses']}")
        for st in s["stalls"]:
            print(f"     stall {st}")
    tot = Counter()
    for s in out:
        for k in ("pills", "silicon_eq_brain", "after_garbage_pills", "prev_target", "clamp_slams_fair_mesen", "misses",
                  "silicon_only_misses", "mesen_reproduced_misses"):
            tot[k] += s[k]
        for arm in ("replay_fair", "replay_fairplus"):
            if s[arm]:
                for k, v in s[arm].items():
                    tot[f"{arm}_{k}"] += v
        for k, v in s["labels"].items():
            tot[f"label_{k}"] += v
    print("TOTAL", dict(tot))
    with open(os.path.join(HERE, "cases_ai_fidelity_lulu_20261005.jsonl"), "w") as fh:
        for r in allrows:
            fh.write(json.dumps(r) + "\n")
    with open(os.path.join(HERE, "cases_ai_misses_lulu_20261005.jsonl"), "w") as fh:
        for r in allmiss:
            fh.write(json.dumps(r) + "\n")
    json.dump({"games": out, "total": dict(tot)}, open(os.path.join(HERE, "ai_lulu_20261005.json"), "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1:] or GAMES)
