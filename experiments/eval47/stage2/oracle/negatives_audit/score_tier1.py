#!/usr/bin/env python3
"""TIER 1 SCORER — PREREG_DSH_CONFIRMATORY Amendment 1.

Primary statistic: cap(DSH) - cap(CHAMP), seed-clustered bootstrap, two-sided.
Full control panel FIRST; if any construction control lands off, the treatment number is VOID.

d_spawn_h = max(H[3], H[4]) of the POST-placement board (oracle_arm.py:156). Lower is better,
so the decider rule is argmin. Picks are compared by the PROGRESS LABEL THEY LAND, never by slot
index: 88.7% of tie sets are ~2 distinct boards spread over 4 slots.
"""
import argparse, base64, glob, gzip, json, sys
import numpy as np

def dsh_of(plane_b64):
    a = np.frombuffer(base64.b64decode(plane_b64), dtype=np.uint8).reshape(2, 16, 8)
    occ = a[0] != 0                       # plane 0 = colour/occupancy
    top = np.where(occ, np.arange(16)[:, None], 16).min(0)   # topmost occupied row per col
    H = 16 - top                                             # 0 when column empty
    return int(max(H[3], H[4]))

def load(d):
    rows = []
    for p in sorted(glob.glob(d + "/*.jsonl.gz")):
        for ln in gzip.open(p, "rt"):
            r = json.loads(ln)
            if "labels" not in r:                 # per-game summary row
                continue
            prog = [l[1] for l in r["labels"]]
            if max(prog) == min(prog):            # degenerate: excluded (Amendment 5)
                continue
            cands = [str(c) for c in r["cands"]]
            assert all(c in r["planes"] for c in cands), f"SCHEMA: missing planes, seed {r['seed']}"
            rows.append(dict(seed=r["seed"], prog=np.array(prog, float),
                             champ=r["cands"].index(r["base_action"]),
                             h12=r["cands"].index(r["trt_action"]),
                             dsh=int(np.argmin([dsh_of(r["planes"][c]) for c in cands]))))
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--boot", type=int, default=4000)
    ap.add_argument("--expect-dsh", default=None, help="npy of banked dsh picks: VALIDATION mode")
    a = ap.parse_args()
    R = load(a.dir)
    print(f"discriminating ties {len(R)} over {len({r['seed'] for r in R})} seeds")
    if a.expect_dsh:
        exp = np.load(a.expect_dsh, allow_pickle=True)
        got = np.array([r["dsh"] for r in R]); ref = np.array([e["dsh"] for e in exp])
        assert len(got) == len(ref), f"row count {len(got)} vs banked {len(ref)}"
        m = (got == ref).mean()
        print(f"VALIDATION vs banked picks: {(got==ref).sum()}/{len(ref)} = {100*m:.2f}%")
        print("SCORER VALIDATED" if m == 1.0 else "*** SCORER DOES NOT REPRODUCE THE BANKED PICKS ***")
        return 0 if m == 1.0 else 1
    P = np.array([r["prog"] for r in R]); seed = np.array([r["seed"] for r in R])
    pk = lambda f: P[np.arange(len(P)), np.array([r[f] for r in R])]
    vh, vc, vd = pk("h12"), pk("champ"), pk("dsh")
    vr, vo, vw = P.mean(1), P.max(1), P.min(1)
    den = (vh - vr).sum()
    cap = lambda v: (v - vr).sum() / den
    print("\n## 1. CONTROL PANEL FIRST\n")
    print("| picker | transfer | construction demands |")
    print("|---|---|---|")
    for nm, v, req in (("H12's own pick", vh, "+100.0% exactly"), ("ORACLE (max progress)", vo, ">100%"),
                       ("CHAMPION's pick", vc, "the BASELINE"), ("random tie-break", vr, "~0"),
                       ("WORST candidate", vw, "<0")):
        print(f"| {nm} | {100*cap(v):.1f}% | {req} |")
    ok = abs(cap(vh) - 1) < 1e-9 and cap(vo) > 1 and abs(cap(vr)) < 0.03 and cap(vw) < 0
    print(f"\n**construction controls: {'ALL LAND' if ok else '*** OFF CONSTRUCTION -> TREATMENT NUMBER IS VOID ***'}**")
    us = np.unique(seed); by = {s: np.where(seed == s)[0] for s in us}
    rng = np.random.default_rng(20260826)
    nd, nc = vd - vr, vc - vr
    bs = np.empty(a.boot)
    for b in range(a.boot):
        ii = np.concatenate([by[s] for s in rng.choice(us, len(us), True)])
        bs[b] = (nd[ii].sum() - nc[ii].sum()) / (vh[ii] - vr[ii]).sum()
    lo, hi = np.percentile(bs, [2.5, 97.5])
    pt = cap(vd) - cap(vc)
    print(f"\n## 2. PRIMARY (Amendment 1)\n\n> **cap(DSH) - cap(CHAMP) = {100*pt:+.1f} pts · 95% CI [{100*lo:+.1f}, {100*hi:+.1f}]**")
    print(f">\n> cap(DSH) = {100*cap(vd):.1f}%  ·  cap(CHAMP) = {100*cap(vc):.1f}%")
    v = "T1-a KILL REPLICATES" if hi < 0 else ("T1-c BLOCKS DISAGREE - diagnose, promote nothing" if lo > 0 else "T1-b NOT RESOLVED AT THIS n")
    print(f"\n**VERDICT: {v}**")
    span = 1.0 - cap(vc)
    print(f"\nprojected dies-ahead delta = {-(pt/span)*4.78:+.2f} pp "
          f"[{-(hi/span)*4.78:+.2f}, {-(lo/span)*4.78:+.2f}]  (POSITIVE = worse than champion)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
