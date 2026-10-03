"""Finishing moves the DIST60 sim declined (root viruses <= 4): decompose chosen vs the best FINISHING root move, and
check whether the chosen move's own PV finishes the target at ply 2 (a DEFERRAL: 'I can finish next pill').
Usage: python procrast_dist60_20261003.py CASES.jsonl [...]"""
import json, sys, collections
import numpy as np
import analyze_g2 as A
import decomp_dist60_20261003 as DC
import fast_rtl_x as FX
import cascade_chain_x as C
from drmario.faithful_game import Pill
from endgame_dist60_20261003 import after, pose_of

C.warmup_chain(topk2=8)
w, fl = FX.variant("winner")
dd = DC.DecompDecider(w, fl, mode="dist_target", W=60, vk=4, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)
rows = []
for p in sys.argv[1:]:
    rows += [json.loads(l) for l in open(p)]
E = [q for q in rows if q.get("D_before") is not None and q["n_finishing"] > 0]
acc = collections.defaultdict(list); nde = 0; nmiss = 0; top_ct = collections.Counter()
for q in E:
    S = q["S"]; b = A.board_from_strings(S["color"], S["virus"], S["link"])
    cur, nxt = tuple(q["cur"]), tuple(q["nxt"]); tr, tc, _ = q["target"]
    r = dd.analyse(b.clone(), Pill(*cur), Pill(*nxt), q["p"])
    ch = r["best"]
    fins = []
    for a in range(32):
        if r["ok"][a]:
            bb, _ = after(b, pose_of(a, cur, b))
            if bb is not None and not bb.is_virus[tr, tc]:
                fins.append(a)
    if ch in fins:
        continue
    nmiss += 1
    alt = max(fins, key=lambda a: r["val"][a])
    b1, _ = after(b, pose_of(ch, cur, b))
    pv2 = int(r["pv2"][ch]); defer = False
    if pv2 >= 0:
        b2, _ = after(b1, pose_of(pv2, nxt, b1))
        defer = b2 is not None and not b2.is_virus[tr, tc]
    nde += int(defer)
    d = r["comp"][ch] - r["comp"][alt]
    for i, k in enumerate(DC.NAMES):
        acc[k].append(d[i])
    pos = {k: d[i] for i, k in enumerate(DC.NAMES) if d[i] > 0}
    top_ct[max(pos, key=pos.get) if pos else "-"] += 1
    print(f"{q['game']} p{q['p']} nv{q['virus_count']} D{q['D_before']} chosen {pose_of(ch, cur, b)} vs finish {pose_of(alt, cur, b)} "
          f"margin {int(r['val'][ch] - r['val'][alt])} defer(PV finishes at ply2)={defer}: "
          + " ".join(f"{k}{d[i]:+.0f}" for i, k in enumerate(DC.NAMES) if abs(d[i]) >= 1))
print(f"\nfinishing available {len(E)}; DIST60 declined {nmiss}; of those the PV finishes at ply 2 (deferral) {nde}")
print("mean chosen - best finish:", " ".join(f"{k}{np.mean(v):+.0f}" for k, v in acc.items() if abs(np.mean(v)) >= 0.5))
print("median:", " ".join(f"{k}{np.median(v):+.0f}" for k, v in acc.items() if abs(np.median(v)) >= 0.5))
print("largest positive term per declined finish:", dict(top_ct))
