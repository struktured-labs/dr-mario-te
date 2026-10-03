"""STEER8a analysis (PREREG_STEER8a.md): the SILICON-FAITHFUL brain under the corrected 2026-10 send fits.
  block 1  faithful ANTIBODY (fA) vs python ANTIBODY (STEER6r's s5b_hsv512 rows): how far the brain gap moved levels
  block 2  faithful DIST60 (fD) vs faithful ANTIBODY (fA): the candidate check (STEER6r's rule, analyze_steer6r.verdict)

  python analyze_steer8a.py              # needs steer8/ and steer6r/ rows
  python analyze_steer8a.py --selftest   # the block-2 rule is analyze_steer6r.verdict: re-run its killed-mutant test
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_steer6r as R6
from analyze_steer6r import GB_SEEDS, RC_SEEDS, boot, fmt, load, win, churn


def cells(prefix, label):
    return (load(f"{prefix.format(c='gb10')}", f"{label}@owner202610", GB_SEEDS),
            load(f"{prefix.format(c='rc10')}", f"{label}~steer", RC_SEEDS),
            load(f"{prefix.format(c='lulu10')}", f"{label}~steer", RC_SEEDS))


def diff(X, Y, lo=2.5, hi=97.5):
    """X - Y per cell (paired). Returns (tap, race, lulu) CIs, ns, text."""
    (Gx, Rx, Lx), (Gy, Ry, Ly) = X, Y
    Sg = [s for s in GB_SEEDS if s in Gx and s in Gy]; Sr = [s for s in RC_SEEDS if s in Rx and s in Ry]
    Sl = [s for s in RC_SEEDS if s in Lx and s in Ly]
    nan = (np.nan,) * 3
    tt = boot([Gx[s]["topout"] - Gy[s]["topout"] for s in Sg], lo, hi) if Sg else nan
    t1 = boot([int(Gx[s]["topout"] and Gx[s]["pills"] <= 100) - int(Gy[s]["topout"] and Gy[s]["pills"] <= 100) for s in Sg], lo, hi) if Sg else nan
    tr = boot([win(Rx[s], 177.) - win(Ry[s], 177.) for s in Sr], lo, hi) if Sr else nan
    tl = boot([win(Lx[s], 140.) - win(Ly[s], 140.) for s in Sl], lo, hi) if Sl else nan
    rt = boot([(Rx[s]["how"] == "topout") - (Ry[s]["how"] == "topout") for s in Sr], lo, hi) if Sr else nan
    lt = boot([(Lx[s]["how"] == "topout") - (Ly[s]["how"] == "topout") for s in Sl], lo, hi) if Sl else nan
    cg = churn([Gy[s] for s in Sg], [Gx[s] for s in Sg], lambda r: r["topout"])
    cr = churn([Ry[s] for s in Sr], [Rx[s] for s in Sr], lambda r: not win(r, 177.))
    cl = churn([Ly[s] for s in Sl], [Lx[s] for s in Sl], lambda r: not win(r, 140.))
    m = lambda D, S, f: 100 * np.mean([f(D[s]) for s in S]) if S else np.nan
    txt = (f"  gb10 tap-out (n={len(Sg)}) {m(Gy, Sg, lambda r: r['topout']):.2f}% -> {m(Gx, Sg, lambda r: r['topout']):.2f}%  d {fmt(tt)}  "
           f"churn fixed {cg[0]} / new {cg[1]}   tap<=100 d {fmt(t1)}\n"
           f"  rc10 race win M177 (n={len(Sr)}) {m(Ry, Sr, lambda r: win(r, 177.)):.2f}% -> {m(Rx, Sr, lambda r: win(r, 177.)):.2f}%  d {fmt(tr)}  "
           f"churn fixed {cr[0]} / new {cr[1]}   race-row tap-out d {fmt(rt)}\n"
           f"  lulu10 race win M140 (n={len(Sl)}) {m(Ly, Sl, lambda r: win(r, 140.)):.2f}% -> {m(Lx, Sl, lambda r: win(r, 140.)):.2f}%  d {fmt(tl)}  "
           f"churn fixed {cl[0]} / new {cl[1]}   LULU-row tap-out d {fmt(lt)}")
    return tt, tr, tl, (len(Sg), len(Sr), len(Sl)), txt


def main():
    pA = cells("steer6r/{c}_anti_*.jsonl", "s5b_hsv512"); pD = cells("steer6r/{c}_dist_*.jsonl", "s6_dist_target60")
    fA = cells("steer8/{c}_fA_*.jsonl", "fA"); fD = cells("steer8/{c}_fD_*.jsonl", "fD")
    for name, X in (("python ANTIBODY (STEER6r)", pA), ("python DIST60 (STEER6r)", pD), ("faithful ANTIBODY", fA), ("faithful DIST60", fD)):
        print(f"rows {name}: gb10 {len(X[0])} rc10 {len(X[1])} lulu10 {len(X[2])}")
    print("\nBLOCK 1 (descriptive): faithful ANTIBODY - python ANTIBODY (how far the brain gap moved the levels)")
    print(diff(fA, pA)[4])
    print("\nBLOCK 2 (PRIMARY, STEER6r rule): faithful DIST60 vs faithful ANTIBODY")
    tt, tr, tl, ns, txt = diff(fD, fA)
    print(txt)
    print(f"  -> {R6.verdict(tt, tr, tl, ns, (1500, 600, 600))}")
    print(f"     race gain survives (lower CI > 0): rc10 {'yes' if tr[1] > 0 else 'no'}, lulu10 {'yes' if tl[1] > 0 else 'no'}")
    # the python verdict on the same seeds, and the difference-in-differences (faithful gain - python gain)
    (GfD, RfD, LfD), (GfA, RfA, LfA), (GpD, RpD, LpD), (GpA, RpA, LpA) = fD, fA, pD, pA
    S = [s for s in GB_SEEDS if all(s in X for X in (GfD, GfA, GpD, GpA))]
    if S:
        print(f"\n  DiD tap-out (faithful gain - python gain, n={len(S)}): python d {fmt(boot([GpD[s]['topout'] - GpA[s]['topout'] for s in S]))}  "
              f"faithful d {fmt(boot([GfD[s]['topout'] - GfA[s]['topout'] for s in S]))}  DiD "
              f"{fmt(boot([(GfD[s]['topout'] - GfA[s]['topout']) - (GpD[s]['topout'] - GpA[s]['topout']) for s in S]))}")
    Sr = [s for s in RC_SEEDS if all(s in X for X in (RfD, RfA, RpD, RpA))]
    if Sr:
        print(f"  DiD race M177 (n={len(Sr)}): python d {fmt(boot([win(RpD[s], 177.) - win(RpA[s], 177.) for s in Sr]))}  faithful d "
              f"{fmt(boot([win(RfD[s], 177.) - win(RfA[s], 177.) for s in Sr]))}")
    Sl = [s for s in RC_SEEDS if all(s in X for X in (LfD, LfA, LpD, LpA))]
    if Sl:
        print(f"  DiD LULU M140 (n={len(Sl)}): python d {fmt(boot([win(LpD[s], 140.) - win(LpA[s], 140.) for s in Sl]))}  faithful d "
              f"{fmt(boot([win(LfD[s], 140.) - win(LfA[s], 140.) for s in Sl]))}")
    print("\n  faithful DIST60 - python DIST60 (block-1 analogue for the candidate)")
    print(diff(fD, pD)[4])


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--selftest" in sys.argv:
        sys.exit(0 if R6.selftest() else 1)
    main()
