"""Separate base-play cost from per-fork cost by regressing secs on forks."""
import glob, gzip, json, os
import numpy as np
OUT = "/home/struktured/projects/dr-mario-distill-wt/experiments/distill/out/labels_m1"
for stratum in ("L20", "L11M"):
    S, F, P = [], [], []
    for f in sorted(glob.glob(os.path.join(OUT, stratum, "seed_*.json.gz"))):
        r = json.load(gzip.open(f, "rt"))
        if r["smoke"]: continue
        S.append(r["secs"]); F.append(r["counters"]["tribunal_forks"])
        P.append(r["game"]["n_plies"])
    S, F, P = map(np.array, (S, F, P))
    A = np.column_stack([np.ones(len(S)), F, P])
    coef, *_ = np.linalg.lstsq(A, S, rcond=None)
    pred = A @ coef
    print(f"{stratum}: secs = {coef[0]:.1f} + {coef[1]:.4f}*forks + "
          f"{coef[2]:.4f}*plies   R2={1-((S-pred)**2).sum()/((S-S.mean())**2).sum():.3f}")
    print(f"   n={len(S)} mean secs={S.mean():.0f} mean forks={F.mean():.0f} "
          f"mean plies={P.mean():.0f}")
