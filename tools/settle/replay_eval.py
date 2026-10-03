#!/usr/bin/env python3
"""DRSETTLE on the banked couch copro timelines (G2/G3/G4 10/03, fw 1488e158): the real cart in Mesen
(tools/lateflip/run_lateflip.sh + lateflip_probe.lua), 464a4b75 vs the fair settle cart. The copro timeline is relative
to GO, so the fair cart sees every publish 6 frames earlier relative to the spawn, under gravity that also starts 5
frames earlier (no pin): the end-to-end answer frame as silicon would produce it.
Metrics as experiments/lateflip (h16 policy_eval*.py): landing == the copro FINAL answer; HYBRID = the landing is none
of the copro's published candidates; == python brain; == silicon; G2 python-evaluator regret vs the python brain's own
pick (couch_forensics `val`, over landings the python brain scores); landings that differ between the two carts.
  replay_eval.py LOGDIR TAG_A TAG_B          (logs at LOGDIR/<G>_<TAG>/lateflip_<G>_<TAG>.log)
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "lateflip"))
from parse_lateflip import load
CF = "/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics/cases_g2_dist60_20261003.jsonl"


def metrics(land, R, C=None, cases=None):
    ps = sorted(land)
    tall = {p for p in ps if R[p]["heights"] and max(R[p]["heights"]) >= 12}
    out = dict(n=len(ps), final=0, hybrid=0, python=0, silicon=0, scored=0, regret=0.0, tall_n=len(tall), tall_hybrid=0,
               upload_ok=0, late=0, frozen=0)
    for p in ps:
        a, r = land[p], R[p]
        pubs = {x[3] for x in r["pubs"]} | {r["final"][2]}
        out["final"] += a == r["final"][2]
        h = a not in pubs
        out["hybrid"] += h
        out["tall_hybrid"] += h and p in tall
        out["python"] += a == r["sim_action"]
        out["silicon"] += a == r["actual_action"]
        if C is not None:
            v = C[p]["val"]
            if str(a) in v:
                out["scored"] += 1; out["regret"] += v[str(C[p]["sim_action"])] - v[str(a)]
        if cases is not None:
            out["upload_ok"] += cases[p]["upload"] == "MATCH"
            out["late"] += cases[p]["late_retargets"] > 0
            out["frozen"] += cases[p]["frozen"]
    out["regret_mean"] = round(out["regret"] / max(1, out["scored"]), 1) if C is not None else None
    return out


def main():
    d, ta, tb = sys.argv[1], sys.argv[2], sys.argv[3]
    C = {json.loads(l)["p"]: json.loads(l) for l in open(CF)}
    for g in ("G2", "G3", "G4"):
        R = {json.loads(l)["p"]: json.loads(l) for l in open(os.path.join(ROOT, "experiments", "lateflip",
                                                                          f"pubtrace_{g}_fw1488e158.jsonl"))}
        res = {}
        lands = {}
        for t in (ta, tb):
            path = os.path.join(d, f"{g}_{t}", f"lateflip_{g}_{t}.log")
            if not os.path.exists(path):
                print(f"{g} {t}: missing {path}"); continue
            L = load(path)
            land = {p: L[p]["land"]["act"] for p in L if L[p]["land"]}
            lands[t] = land
            res[t] = metrics(land, R, C if g == "G2" else None, L)
        print(f"== {g}: {len(R)} placements")
        for t, m in res.items():
            print(f"  {t:6s} n={m['n']:3d} upload==case {m['upload_ok']:3d} ==final {m['final']:3d} HYBRID {m['hybrid']:2d} "
                  f"==python {m['python']:3d} ==silicon {m['silicon']:3d} late-retarget pills {m['late']:3d} frozen {m['frozen']:2d}"
                  + (f" | python regret/scored {m['regret_mean']} (scored {m['scored']})" if m["regret_mean"] is not None else "")
                  + f" | tall n {m['tall_n']} hybrid {m['tall_hybrid']}")
        if len(lands) == 2:
            A, B = lands[ta], lands[tb]
            common = sorted(set(A) & set(B))
            diff = [p for p in common if A[p] != B[p]]
            print(f"  landings differing {ta} vs {tb}: {len(diff)}/{len(common)} " + " ".join(
                f"p{p}:{A[p]}->{B[p]}" for p in diff))


if __name__ == "__main__":
    main()
