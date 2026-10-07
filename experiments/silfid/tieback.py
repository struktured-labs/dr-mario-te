"""silfid: tie the silicon copro's measured behaviour (PUBLOG captures #1 + #2) back to the 77 residual 10/05 couch misses.
  tieback.py CAP1_COSIM.jsonl CAP2_COSIM.jsonl  -> tieback_20261007.txt
1. EARLY-DONE model: from the captures' (silicon DONE, Verilator DONE) pairs, conditional on the Verilator DONE time
   (+-5 f) and on the regime (capture #2's tall-endgame CELL for couch pills in the CELL, capture #1 otherwise), the
   probability that silicon's DONE lands before the couch pill's copro-final publish time. Summed over all 842 couch
   pills with >= 2 publications = the expected couch landings on an EARLIER answer (a silicon-only EARLIER-PUB), vs
   the 30 observed in the residual.
2. The couch's own DONE proxy: slam onset (silicon - Mesen replay of the co-sim timeline), residual vs agreeing pills."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import load


def slam_onset(seq):
    """== slam.py's detector (copied: importing slam.py runs its whole analysis)."""
    r = [(f, pose[1] + (1 if pose[0] == "V" else 0)) for f, pose in seq]
    for i in range(len(r) - 3):
        (f0, a), (f1, b), (f2, c), (f3, d) = r[i:i + 4]
        if f3 - f0 <= 4 and d - a >= 2 and f1 == f0 + 1 and f2 == f1 + 1 and f3 == f2 + 1:
            for k in range(i, i + 4):
                if r[k + 1][1] > r[k][1]:
                    return r[k + 1][0]
    return None

def rows(path):
    return [json.loads(l) for l in open(path) if l.strip()]
C1 = [r for r in rows(sys.argv[1]) if "done_dt" in r]
C2 = [r for r in rows(sys.argv[2]) if "done_dt" in r and r["seq"] < 1597]
CELL2 = [r for r in C2 if r["viruses"] <= 20 and r["maxh"] >= 14]
out = []
def P(*a):
    s = " ".join(str(x) for x in a); out.append(s); print(s)

def p_before(pool, D, tf):
    near = [r for r in pool if abs(r["cosim_done"][0] - D) <= 5.0] or pool
    return sum(r["done"]["t"] < tf for r in near) / len(near), len(near)

summ = json.load(open(os.path.join(HERE, "summary_silfid_20261006.json")))
res = {tuple(x) for x in summ["residual"]["pills"]}
MI = load.misses()
P(f"# tie-back: capture #1 {len(C1)} replayed pills with a DONE (early {sum(r['done_dt'] < -2 for r in C1)}), capture #2 "
  f"{len(C2)} (early {sum(r['done_dt'] < -2 for r in C2)}; CELL {len(CELL2)}, early {sum(r['done_dt'] < -2 for r in CELL2)})")
exp = 0.0; exp_res_cells = 0.0; n = 0
obs = []
for g in load.GAMES:
    PT = load.pubtrace(g)
    for p, pt in PT.items():
        pubs = pt.get("pubs") or []
        if len(pubs) < 2:
            continue
        tf = pubs[-1][0]
        incell = pt["vc"] <= 20 and max(pt["heights"]) >= 14
        pool = CELL2 if (incell and CELL2) else C1
        pb, _ = p_before(pool, pt["done_f"], tf)
        exp += pb; n += 1
        if (g, p) in res and MI[(g, p)]["label"] == "EARLIER-PUB":
            obs.append((g, p, round(tf, 1), round(pb, 3)))
P(f"1. expected couch landings on an earlier answer from silicon's early DONE: {exp:.1f} over {n} couch pills with >= 2 pubs")
P(f"   observed residual EARLIER-PUB: {len(obs)}; sum of their own P(silicon DONE before the final publish) = "
  f"{sum(x[3] for x in obs):.1f}")
P(f"   per pill (game, p, final-publish f, P): {sorted(obs, key=lambda x: -x[3])}")

# 2. slam onset proxy
out2 = collections.defaultdict(list)
FI = load.fidelity()
for g in load.GAMES:
    T, land, inj = load.mesen(g)
    Q = load.cases(g)
    for p, tr in T.items():
        q = Q.get(p)
        if not q:
            continue
        cur = tuple(q["cur"])
        ms = slam_onset([(d["f"], load.mpose(d, cur)) for d in tr])
        ss = slam_onset(sorted((f - 1, load.spose(s, cur)) for f, s in load.sil_frames(q).items()))
        if ms is None or ss is None:
            continue
        k = "resid" if (g, p) in res else ("agree" if FI[(g, p)]["mesen_fair_eq_sil"] else "other")
        out2[k].append((g, p, ss - ms, (MI.get((g, p)) or {}).get("label")))
P("2. slam onset (silicon - Mesen replay of the Verilator timeline, f; the cart slams at DONE):")
for k in ("agree", "resid"):
    d = [x[2] for x in out2[k]]
    P(f"   {k:6s} n {len(d):3d}: early (<= -3) {sum(x <= -3 for x in d):3d} ({100 * sum(x <= -3 for x in d) / len(d):4.1f}%), "
      f"late (>= +3) {sum(x >= 3 for x in d):3d} ({100 * sum(x >= 3 for x in d) / len(d):4.1f}%), within 2 f {sum(abs(x) <= 2 for x in d)}")
lab = collections.defaultdict(collections.Counter)
for g, p, d, l in out2["resid"]:
    lab[l]["early" if d <= -3 else "late" if d >= 3 else "same"] += 1
for l, c in sorted(lab.items()):
    P(f"   residual {l:14s} {dict(c)}")
open(os.path.join(HERE, "tieback_20261007.txt"), "w").write("\n".join(out) + "\n")
