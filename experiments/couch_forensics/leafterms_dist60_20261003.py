"""Which BASE-LEAF terms differ between the chosen move and the best finishing move, on the ROOT CHILD board
(full scan, weighted, signed as in _combine_terms), for every finishing move DIST60 declined (root viruses <= 4).
Usage: python leafterms_dist60_20261003.py CASES.jsonl [...]"""
import json, sys, collections
import numpy as np
import analyze_g2 as A
import decomp_dist60_20261003 as DC
import fast_rtl_x as FX
import cascade_chain_x as C
from fast_rtl_x import (NBASE, NT, T_MAXH, T_HOLES, T_TOPRISK, T_SPAWN, T_SETUP, T_MATCHED, T_BURIED, T_RDY, T_VRDY,
                        T_CROSS, T_POLL, R_MAXH, R_HOLES, R_TOPRISK, R_SPAWN, R_SETUP, R_MATCHED, R_BURIED, R_RDYEXT,
                        R_VRDY, R_CROSS, R_POLL, _base_scan)
from drmario.faithful_game import Pill
from endgame_dist60_20261003 import after, pose_of

TERMS = (("MAXH", T_MAXH, R_MAXH, -1), ("HOLES", T_HOLES, R_HOLES, -1), ("TOPRISK", T_TOPRISK, R_TOPRISK, -1),
         ("SPAWN", T_SPAWN, R_SPAWN, -1), ("SETUP", T_SETUP, R_SETUP, +1), ("MATCHED", T_MATCHED, R_MATCHED, +1),
         ("BURIED", T_BURIED, R_BURIED, -1), ("RDY", T_RDY, R_RDYEXT, +1), ("VRDY", T_VRDY, R_VRDY, +1),
         ("CROSS", T_CROSS, R_CROSS, +1), ("POLL", T_POLL, R_POLL, -1))
C.warmup_chain(topk2=8)
w, fl = FX.variant("winner")
dd = DC.DecompDecider(w, fl, mode="dist_target", W=60, vk=4, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)


def terms(b):
    col, vir = DC.board_flat(b)
    base = np.empty(NBASE, np.int64); _base_scan(col, vir, fl, base)
    return {n: s * w[r] * base[t] for n, t, r, s in TERMS}


rows = []
for p in sys.argv[1:]:
    rows += [json.loads(l) for l in open(p)]
acc = collections.defaultdict(list)
for q in rows:
    if q.get("D_before") is None or q["n_finishing"] == 0:
        continue
    S = q["S"]; b = A.board_from_strings(S["color"], S["virus"], S["link"])
    cur, nxt = tuple(q["cur"]), tuple(q["nxt"]); tr, tc, _ = q["target"]
    r = dd.analyse(b.clone(), Pill(*cur), Pill(*nxt), q["p"]); ch = r["best"]
    fins = [a for a in range(32) if r["ok"][a] and (lambda bb: bb is not None and not bb.is_virus[tr, tc])(after(b, pose_of(a, cur, b))[0])]
    if ch in fins:
        continue
    alt = max(fins, key=lambda a: r["val"][a])
    b1, _ = after(b, pose_of(ch, cur, b)); b2, _ = after(b, pose_of(alt, cur, b))
    if b1.virus_count() == 0 or b2.virus_count() == 0:
        continue
    t1, t2 = terms(b1), terms(b2)
    for k in t1:
        acc[k].append(t1[k] - t2[k])
n = len(next(iter(acc.values())))
print(f"declined finishes analysed: {n} (root-child leaf, chosen - finishing, weighted; enters the root value at 1/2)")
print("mean:  ", " ".join(f"{k}{np.mean(v):+.0f}" for k, v in acc.items() if abs(np.mean(v)) >= 0.5))
print("median:", " ".join(f"{k}{np.median(v):+.0f}" for k, v in acc.items() if abs(np.median(v)) >= 0.5))
print("share of cases where the term favours NOT finishing:", " ".join(f"{k}{np.mean(np.array(v) > 0):.0%}" for k, v in acc.items() if np.any(np.array(v) != 0)))
