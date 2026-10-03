"""Counterfactual brains on the banked couch endgame positions (cases_*dist60_20261003.jsonl, root viruses <= 4):
how often does each candidate fix take a D-reducing / finishing root move when one exists, and how many decisions
does it change vs DIST60? Variants are root-gated (firmware-side): chain weight / W chosen from the ROOT virus count.
Usage: python variants_dist60_20261003.py CASES.jsonl [CASES2.jsonl ...]"""
import json, sys
import numpy as np
import analyze_g2 as A
import decomp_dist60_20261003 as DC
import fast_rtl_x as FX
import cascade_chain_x as C
from drmario.faithful_game import Pill
from endgame_dist60_20261003 import after, pose_of, d_of

C.warmup_chain(topk2=8)
w, fl = FX.variant("winner")
kw = dict(topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)
VARS = {  # name: (W, chain when root nv <= k, k, excav/hang off when root nv <= k)
    "DIST60": (60, 540, 0, False),
    "chain0@<=4": (60, 0, 4, False), "chain0@<=2": (60, 0, 2, False), "chain0@<=1": (60, 0, 1, False),
    "chain180@<=4": (60, 180, 4, False),
    "W120": (120, 540, 0, False), "W180": (180, 540, 0, False),
    "W180+chain0@<=4": (180, 0, 4, False),
    "exh0@<=4": (60, 540, 4, True), "exh0+chain0@<=4": (60, 0, 4, True), "W180+exh0@<=4": (180, 540, 4, True),
    "W180+exh0+chain0@<=4": (180, 0, 4, True),
}
decs = {n: DC.DecompDecider(w, fl, mode="dist_target", W=v[0], vk=4, **kw) for n, v in VARS.items()}
rows = []
for p in sys.argv[1:]:
    rows += [json.loads(l) for l in open(p)]
E = [q for q in rows if q.get("D_before") is not None]
stat = {n: dict(dred_have=0, dred_took=0, fin_have=0, fin_took=0, differs=0, n=0) for n in VARS}
for q in E:
    S = q["S"]; b = A.board_from_strings(S["color"], S["virus"], S["link"])
    cur, nxt = tuple(q["cur"]), tuple(q["nxt"]); tr, tc, _ = q["target"]; tgt = tr * 8 + tc
    nv = q["virus_count"]
    base = None
    for n, (W, ch, k, exh) in VARS.items():
        wc = ch if nv <= k else 540
        dd = decs[n]
        if exh and nv <= k:
            dd.w_excav, dd.w_hang = 0, 0
        else:
            dd.w_excav, dd.w_hang = 24, 40
        r = dd.analyse(b.clone(), Pill(*cur), Pill(*nxt), q["p"], w_chain=wc)
        a = r["best"]
        if n == "DIST60":
            base = a
        bb, st = after(b, pose_of(a, cur, b))
        dred = d_of(bb, tgt) < q["D_before"] or not bb.is_virus[tr, tc]
        fin = not bb.is_virus[tr, tc]
        s = stat[n]; s["n"] += 1; s["differs"] += int(a != base)
        if q["n_d_reducing"] > 0:
            s["dred_have"] += 1; s["dred_took"] += int(dred)
        if q["n_finishing"] > 0:
            s["fin_have"] += 1; s["fin_took"] += int(fin)
for n, s in stat.items():
    print(f"{n:18s} n={s['n']} differs-from-DIST60 {s['differs']:3d}  takes D-reducing {s['dred_took']}/{s['dred_have']}  "
          f"finishes {s['fin_took']}/{s['fin_have']}")
