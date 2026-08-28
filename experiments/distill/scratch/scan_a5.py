"""Offline A5 yield projection from banked height traces. No compute."""
import glob, gzip, json, os, binascii, sys
import numpy as np

OUT = "/home/struktured/projects/dr-mario-distill-wt/experiments/distill/out/labels_m1"
WINDOW = 30

def held(seed): return binascii.crc32(str(seed).encode()) % 4 == 0

def fire(stratum, H):
    if stratum == "L20": return max(H[3], H[4]) >= 13
    return max(H[2:6]) >= 12

for stratum in ("L20", "L11M"):
    files = sorted(glob.glob(os.path.join(OUT, stratum, "seed_*.json.gz")))
    ngames = ntop = 0
    bf_plies = []          # per topout game: trigger plies in final WINDOW
    bf_held = []           # same, held-out games only
    base_states = base_danger = base_held_danger = 0
    dang_by_ply_frac = []  # (is_danger, ply/n_plies) for trigger-class states
    late_trig = late_trig_danger = 0
    for f in files:
        r = json.load(gzip.open(f, "rt"))
        if r["smoke"]: continue
        ngames += 1
        n = r["game"]["n_plies"]
        for a in r["adjudications"]:
            if a["degenerate"]: continue
            base_states += 1
            d = a["champ_s2"] <= 3
            base_danger += d
            if held(r["seed"]): base_held_danger += d
            if "trigger" in a["classes"]:
                dang_by_ply_frac.append((d, a["ply"]/max(n,1)))
                if a["ply"] >= n - WINDOW:
                    late_trig += 1; late_trig_danger += d
        if r["game"]["res"] != "topout": continue
        ntop += 1
        ws = max(0, n - WINDOW)
        k = sum(1 for p, H in enumerate(r["heights_trace"])
                if p >= ws and fire(stratum, H))
        bf_plies.append(k)
        if held(r["seed"]): bf_held.append(k)
    bp = np.array(bf_plies); bh = np.array(bf_held)
    print(f"== {stratum}: games={ngames} topouts={ntop} "
          f"({ntop/max(ngames,1):.1%})")
    print(f"   base bank (non-degenerate): states={base_states} "
          f"danger={base_danger} held-danger={base_held_danger}")
    print(f"   A5 backfill trigger-plies in final {WINDOW}: "
          f"total={bp.sum()} mean={bp.mean():.1f}/game "
          f"p10/p50/p90={np.percentile(bp,10):.0f}/{np.percentile(bp,50):.0f}"
          f"/{np.percentile(bp,90):.0f} zero-games={(bp==0).sum()}")
    print(f"   A5 held-out share: games={len(bh)} plies={bh.sum()} "
          f"({bh.sum()/max(bp.sum(),1):.1%})")
    if late_trig:
        print(f"   danger rate among LATE trigger states in base bank: "
              f"{late_trig_danger}/{late_trig} = {late_trig_danger/late_trig:.3f}")
    allt = len(dang_by_ply_frac)
    if allt:
        dr = sum(d for d,_ in dang_by_ply_frac)/allt
        print(f"   danger rate among ALL trigger states: {dr:.3f} (n={allt})")
