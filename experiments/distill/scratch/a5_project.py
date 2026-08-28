"""A5 projection: yield + cost, per stratum, computed (not asserted).
Cost model coefficients are fitted here from the base bank in the same run
that uses them (R25: numbers computed by shared code get checked)."""
import glob, gzip, json, os, binascii
import numpy as np
OUT = "/home/struktured/projects/dr-mario-distill-wt/experiments/distill/out/labels_m1"
W = 30
def held(s): return binascii.crc32(str(s).encode()) % 4 == 0
def fire(st, H):
    return (max(H[3], H[4]) >= 13) if st == "L20" else (max(H[2:6]) >= 12)

print(f"{'stratum':>6} | {'topout':>6} {'adj':>6} {'nondeg':>7} {'held':>6} "
      f"{'held-dang':>9} | {'core-h':>7} {'wall@14w':>8}")
for st in ("L20", "L11M"):
    S=[];F=[];P=[]; late=[]; topo=[]
    for f in sorted(glob.glob(os.path.join(OUT, st, "seed_*.json.gz"))):
        r = json.load(gzip.open(f, "rt"))
        if r["smoke"]: continue
        S.append(r["secs"]); F.append(r["counters"]["tribunal_forks"])
        n = r["game"]["n_plies"]; P.append(n)
        for a in r["adjudications"]:
            if "trigger" in a["classes"] and a["ply"] >= n - W:
                late.append((a["champ_s2"]<=3, a["degenerate"], a["n_cands"], a["n_short"]))
        if r["game"]["res"] == "topout":
            k = sum(1 for p,H in enumerate(r["heights_trace"]) if p>=max(0,n-W) and fire(st,H))
            topo.append((k, n, held(r["seed"])))
    S,F,P = map(np.array,(S,F,P))
    A = np.column_stack([np.ones(len(S)),F,P]); c,*_ = np.linalg.lstsq(A,S,rcond=None)
    L = np.array(late,float); nd = L[L[:,1]==0]
    deg_rate = L[:,1].mean(); dang_rate = nd[:,0].mean()
    fpa = 2*L[:,2].mean() + 6*L[:,3].mean()
    T = np.array(topo,float)
    adj = T[:,0].sum(); nondeg = adj*(1-deg_rate)
    h_adj = T[T[:,2]==1][:,0].sum(); h_nondeg = h_adj*(1-deg_rate)
    h_dang = h_nondeg*dang_rate
    forks = adj*fpa
    core_h = (forks*c[1] + len(T)*c[0] + T[:,1].sum()*c[2]) / 3600
    print(f"{st:>6} | {len(T):6d} {adj:6.0f} {nondeg:7.0f} {h_nondeg:6.0f} "
          f"{h_dang:9.0f} | {core_h:7.1f} {core_h/14:7.1f}h")
    print(f"        deg={deg_rate:.3f} danger|nondeg={dang_rate:.3f} "
          f"forks/adj={fpa:.1f} forks={forks:,.0f} "
          f"cost= {c[0]:.0f} + {c[1]:.3f}*forks + {c[2]:.3f}*plies")
