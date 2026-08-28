import glob, gzip, json, os, binascii
import numpy as np
OUT = "/home/struktured/projects/dr-mario-distill-wt/experiments/distill/out/labels_m1"
W = 30
def held(s): return binascii.crc32(str(s).encode()) % 4 == 0
for stratum in ("L20", "L11M"):
    tot_forks = tot_adj = 0; secs = []
    late = []   # (danger, degenerate, n_cands, n_short, held)
    keys = set()
    for f in sorted(glob.glob(os.path.join(OUT, stratum, "seed_*.json.gz"))):
        r = json.load(gzip.open(f, "rt")); 
        if r["smoke"]: continue
        keys |= set(r.keys())
        tot_forks += r["counters"]["tribunal_forks"]; tot_adj += len(r["adjudications"])
        if "secs" in r: secs.append(r["secs"])
        n = r["game"]["n_plies"]
        for a in r["adjudications"]:
            if "trigger" in a["classes"] and a["ply"] >= n - W:
                late.append((a["champ_s2"] <= 3, a["degenerate"], a["n_cands"],
                             a["n_short"], held(r["seed"])))
    L = np.array(late, float)
    print(f"== {stratum}: banked adj={tot_adj} tribunal_forks={tot_forks} "
          f"forks/adj={tot_forks/max(tot_adj,1):.1f}  record keys={sorted(keys)}")
    if len(L):
        deg = L[:,1].mean()
        nd = L[L[:,1]==0]
        print(f"   LATE-trigger banked states n={len(L)}: degenerate={deg:.3f} "
              f"n_cands mean={L[:,2].mean():.1f} n_short mean={L[:,3].mean():.1f} "
              f"forks/adj={2*L[:,2].mean()+6*L[:,3].mean():.1f}")
        print(f"   non-degenerate late: n={len(nd)} danger={nd[:,0].mean():.3f} "
              f"held-share={nd[:,4].mean():.3f}")
    if secs: print(f"   secs/game mean={np.mean(secs):.1f}")
