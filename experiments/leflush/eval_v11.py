#!/usr/bin/env python3
"""Score the DRLEFLUSH Mesen replays with the abort-stale lane's metrics (tmp/abort_stale/tools/eval_abort.py, itself
fair_v1_replay's eval_fair_v1): ==final / HYBRID against the timeline actually replayed, G2 regret vs the python brain
(couch-forensics case values), reg-xT, ==python / ==silicon / lateRT, and the pipeline columns (stale edges, GO waits).
Rows: AV1 = abort cart b1b57638 + fw V1 a1ef31c8 (the lane's banked runs, its banked timelines) and every
<game>_<tag> run under tmp/v11/mesen/runs with its own case timeline (tmp/v11/mesen/cases/cases_<game>_<tl>.jsonl).
  eval_v11.py TAG:TL [TAG:TL ...]      e.g. AV11:V11  (run dir <game>_AV11, timeline cases_<game>_V11.jsonl)"""
import json
import os
import sys

sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/tmp/abort_stale/tools")
import eval_abort as E  # noqa: E402

V = "/home/struktured/projects/dr_mario_rl/tmp/v11/mesen"


def main():
    arms = [("AV1", "D+ABORT b1b57638 + fw V1 a1ef31c8 (abort-stale lane run)",
             os.path.join(E.O, "runs", "{g}_AV1", "lateflip_{g}_AV1.log"), E.TL["V1"])]
    for spec in sys.argv[1:]:
        tag, tl = spec.split(":")
        arms.append((tag, f"D+ABORT b1b57638 + fw {tl}", os.path.join(V, "runs", "{g}_" + tag, "lateflip_{g}_" + tag + ".log"),
                     os.path.join(V, "cases", "cases_{g}_" + tl + ".jsonl")))
    res, lands, P = {}, {}, {}
    for g in ("G2", "G3", "G4"):
        for tag, desc, logf, tlf in arms:
            path = logf.format(g=g)
            if not os.path.exists(path) or "SUMMARY" not in open(path, errors="replace").read():
                print(f"{g} {tag}: missing/incomplete {path}"); continue
            L = E.load(path)
            R = {json.loads(l)["p"]: json.loads(l) for l in open(tlf.format(g=g))}
            res[g, tag], lands[g, tag] = E.metrics(L, R, g)
            P[g, tag] = E.pipe(path)
    print(f"{'game':4s} {'arm':6s} | {'n':>3s} {'up==case':>8s} {'==final':>7s} {'HYBRID':>6s} {'refusals':>8s} "
          f"{'regret(sc)':>11s} {'reg-xT':>6s} | {'==python':>8s} {'==silicon':>9s} {'lateRT':>6s} | "
          f"{'stale':>5s} {'waits':>5s} {'wmax':>4s} {'wsum':>4s}")
    for g in ("G2", "G3", "G4"):
        for tag, desc, _, _ in arms:
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
        for tag, _, _, _ in arms[1:]:
            if (g, "AV1") not in lands or (g, tag) not in lands:
                continue
            A, B = lands[g, "AV1"], lands[g, tag]
            com = sorted(set(A) & set(B))
            diff = [p for p in com if A[p] != B[p]]
            print(f"{g} landings differing AV1 vs {tag}: {len(diff)}/{len(com)} " + " ".join(f"p{p}:{A[p]}->{B[p]}" for p in diff))
            ga, gb = P[g, "AV1"]["gos"], P[g, tag]["gos"]
            dgo = [p for p in sorted(set(ga) & set(gb)) if ga[p]["go"] != gb[p]["go"] or ga[p]["stale"] != gb[p]["stale"]]
            print(f"{g} GO frame / stale-edge differences AV1 vs {tag}: {len(dgo)} " +
                  " ".join(f"p{p}:{ga[p]['go']}/{gb[p]['go']}" for p in dgo[:20]))


if __name__ == "__main__":
    main()
