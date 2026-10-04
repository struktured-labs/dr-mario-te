#!/usr/bin/env python3
"""Score the abort-stale Mesen runs with the fair_v1_replay metrics (tools/eval_fair_v1.py there: ==final / HYBRID
against the timeline actually replayed, G2 regret vs the python brain from the couch-forensics case values, reg-xT),
plus the PIPELINE columns: stale = new-pill edges that found the previous search still ARMED, waits = case pills whose
GO came later than the nominal settle GO (f1 after the edge), max/sum of those waits in frames.

  eval_abort.py [runs_dir] [--ref other_runs_dir]   (ref: check that re-runs of D1488/DV1 reproduce those landings)
"""
import json
import os
import sys

O = "/home/struktured/projects/dr_mario_rl/tmp/abort_stale"
F = "/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay"
sys.path.insert(0, os.path.join(O, "tools", "lateflip"))
sys.path.insert(0, os.path.join(O, "tools"))
from parse_lateflip import load  # noqa: E402
import pipe_stats  # noqa: E402

CF = "/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics/cases_g2_dist60_20261003.jsonl"
C = {json.loads(l)["p"]: json.loads(l) for l in open(CF)}
TL = {"1488": os.path.join(F, "timelines", "pubtrace_{g}_fw1488e158.jsonl"),
      "V1": os.path.join(F, "timelines", "pubtrace_{g}_fwa1ef31c8_fwlane.jsonl")}
ARMS = [("D1488", "D dbbb5007 + fw 1488e158", "1488"), ("A1488", "D+ABORT b1b57638 + fw 1488e158", "1488"),
        ("DV1", "D dbbb5007 + fw V1 a1ef31c8", "V1"), ("AV1", "D+ABORT b1b57638 + fw V1 a1ef31c8", "V1")]


def R_of(g, tl):
    return {json.loads(l)["p"]: json.loads(l) for l in open(TL[tl].format(g=g))}


def metrics(L, R, g):
    land = {p: L[p]["land"]["act"] for p in L if L[p]["land"] and p in R}
    o = dict(n=0, upload_ok=0, final=0, hybrid=0, python=0, silicon=0, late=0, frozen=0, scored=0, regret=0.0, xs=0,
             xr=0.0)
    for p in sorted(land):
        a, r = land[p], R[p]
        pubs = {x[3] for x in r["pubs"]} | {r["final"][2]}
        o["n"] += 1
        o["upload_ok"] += L[p]["upload"] == "MATCH"
        o["final"] += a == r["final"][2]
        o["hybrid"] += a not in pubs
        o["python"] += a == r["sim_action"]
        o["silicon"] += a == r["actual_action"]
        o["late"] += L[p]["late_retargets"] > 0
        o["frozen"] += bool(L[p]["frozen"])
        if g == "G2":
            v = C[p]["val"]
            if str(a) in v:
                d = v[str(C[p]["sim_action"])] - v[str(a)]
                o["scored"] += 1; o["regret"] += d
                tuckland = bool(r.get("tuck")) and r["tuck"][0] != 255 and a == r["final"][2]
                if not tuckland:
                    o["xs"] += 1; o["xr"] += d
    o["regret_mean"] = round(o["regret"] / o["scored"], 1) if o["scored"] else None
    o["xregret_mean"] = round(o["xr"] / o["xs"], 1) if o["xs"] else None
    return o, land


def pipe(path):
    r = pipe_stats.load(path)
    stale = [p for p, x in r.items() if x["stale"]]
    waits = {p: x["go"] - 1 for p, x in r.items() if x["stale"] and x["go"] is not None and x["go"] > 1}
    # (a GO later than f1 on a NON-stale edge is not a pipeline wait: e.g. G2 p102 on 1488, an injection on a frame
    #  where the ROM had not thrown yet -- the readiness guard holds the upload; reported separately)
    other = {p: x["go"] - 1 for p, x in r.items() if not x["stale"] and x["go"] is not None and x["go"] > 1}
    return dict(stale=len(stale), waits=len(waits), wmax=max(waits.values(), default=0), wsum=sum(waits.values()),
                gos=r, other=other)


def main():
    runs = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.path.join(O, "runs")
    ref = sys.argv[sys.argv.index("--ref") + 1] if "--ref" in sys.argv else None
    res, lands, P = {}, {}, {}
    for g in ("G2", "G3", "G4"):
        for tag, desc, tl in ARMS:
            path = os.path.join(runs, f"{g}_{tag}", f"lateflip_{g}_{tag}.log")
            if not os.path.exists(path) or "SUMMARY" not in open(path, errors="replace").read():
                print(f"{g} {tag}: missing/incomplete {path}"); continue
            L = load(path); R = R_of(g, tl)
            res[g, tag], lands[g, tag] = metrics(L, R, g)
            P[g, tag] = pipe(path)
    print(f"{'game':4s} {'arm':6s} | {'n':>3s} {'up==case':>8s} {'==final':>7s} {'HYBRID':>6s} {'refusals':>8s} "
          f"{'regret(sc)':>11s} {'reg-xT':>6s} | {'==python':>8s} {'==silicon':>9s} {'lateRT':>6s} | "
          f"{'stale':>5s} {'waits':>5s} {'wmax':>4s} {'wsum':>4s}")
    for g in ("G2", "G3", "G4"):
        for tag, desc, tl in ARMS:
            if (g, tag) not in res:
                continue
            m, q = res[g, tag], P[g, tag]
            rg = "-" if m["regret_mean"] is None else f"{m['regret_mean']} ({m['scored']})"
            rx = "-" if m["xregret_mean"] is None else f"{m['xregret_mean']}"
            print(f"{g:4s} {tag:6s} | {m['n']:3d} {m['upload_ok']:8d} {m['final']:7d} {m['hybrid']:6d} {m['frozen']:8d} "
                  f"{rg:>11s} {rx:>6s} | {m['python']:8d} {m['silicon']:9d} {m['late']:6d} | "
                  f"{q['stale']:5d} {q['waits']:5d} {q['wmax']:4d} {q['wsum']:4d}  [{desc}]")
    print()
    for g in ("G2", "G3", "G4"):
        for a, b in (("D1488", "A1488"), ("DV1", "AV1"), ("D1488", "AV1"), ("D1488", "DV1")):
            if (g, a) not in lands or (g, b) not in lands:
                continue
            A, B = lands[g, a], lands[g, b]
            com = sorted(set(A) & set(B))
            diff = [p for p in com if A[p] != B[p]]
            print(f"{g} landings differing {a} vs {b}: {len(diff)}/{len(com)} " + " ".join(f"p{p}:{A[p]}->{B[p]}" for p in diff))
    if ref:
        print()
        for g in ("G2", "G3", "G4"):
            for tag in ("D1488", "DV1"):
                path = os.path.join(ref, f"{g}_{tag}", f"lateflip_{g}_{tag}.log")
                if (g, tag) not in lands or not os.path.exists(path):
                    continue
                Lr = load(path)
                A = lands[g, tag]
                Br = {p: Lr[p]["land"]["act"] for p in Lr if Lr[p]["land"]}
                com = sorted(set(A) & set(Br))
                diff = [p for p in com if A[p] != Br[p]]
                print(f"REPRO {g} {tag} vs {ref.split('/')[-2]}: {len(diff)}/{len(com)} landings differ "
                      + " ".join(f"p{p}" for p in diff))
    # per-pill GO table for the stale edges (D vs A)
    print()
    for g in ("G2", "G3", "G4"):
        for fw, d, a in (("1488", "D1488", "A1488"), ("V1", "DV1", "AV1")):
            if (g, d) not in P or (g, a) not in P:
                continue
            gd, ga = P[g, d]["gos"], P[g, a]["gos"]
            st = sorted(p for p in gd if gd[p]["stale"] or (p in ga and ga[p]["stale"]))
            print(f"{g} {fw} stale-edge pills, GO frame after the edge D/A: " +
                  " ".join(f"p{p}:{gd[p]['go']}/{ga.get(p, {}).get('go')}" for p in st))
            print(f"{g} {fw} non-stale late GOs D: {P[g, d]['other']}  A: {P[g, a]['other']}")


if __name__ == "__main__":
    main()
