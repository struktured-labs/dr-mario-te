#!/usr/bin/env python3
"""u8slam lane: where an early slam can cost a landing. Pills binned by how long after the FIRST publish the copro's final
answer becomes the standing answer (a tuck final only exists at DONE), with landed == final per cart.
Usage: late_finals.py RUNS FWTAG ARM[,ARM...]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A

runs, fw, arms = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
rows = []
for g in A.GAMES:
    C = A.cases(g, fw); TL, _ = A.load_timeline(g, fw, C)
    L = {a: A.parse(f"{runs}/{g}_{a}_{fw}_chain_garb/lateflip_{g}_{a}_{fw}_chain_garb.log")[0] for a in arms}
    for p in C:
        pubs = TL[p]["pubs"]; fin = C[p]["fin"]; tuck = C[p]["tuck"][0] != 255
        tfin = None
        for t, c, o, a in pubs:                             # the final action standing for good
            tfin = (t if tfin is None else tfin) if a == fin else None
        if tfin is None or tuck:
            tfin = C[p]["done_f"]
        first = pubs[0][0] if pubs else C[p]["done_f"]
        r = {a: A.pill_row(L[a][p], C[p], TL[p])["cls"] == "final" for a in arms if p in L[a] and "land" in L[a][p]}
        rows.append(dict(vc=C[p]["vc"], tuck=tuck, lag=tfin - first, **r))
print(f"# fw={fw}: landed == final by the lag of the final answer behind the first publish (frames)")
print(f"{'final arrives':32s} {'viruses':8s} {'n':>5s} {'tuck':>5s} " + " ".join(f"{a + ' ==final':>12s}" for a in arms))
for name, sel in (("with the first publish", lambda r: r["lag"] == 0), ("<= 4 f later", lambda r: 0 < r["lag"] <= 4),
                  ("4-16 f later", lambda r: 4 < r["lag"] <= 16), ("> 16 f later", lambda r: r["lag"] > 16)):
    for sn, ss in (("all", lambda r: True), (">= 10", lambda r: r["vc"] >= 10), ("< 10", lambda r: r["vc"] < 10)):
        rs = [r for r in rows if sel(r) and ss(r)]
        print(f"{name:32s} {sn:8s} {len(rs):5d} {sum(r['tuck'] for r in rs):5d} " +
              " ".join(f"{sum(r.get(a, False) for r in rs):12d}" for a in arms))
