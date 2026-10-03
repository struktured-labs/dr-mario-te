"""STEER8b AMENDED analysis (PREREG_STEER8b.md amendment): block 3 fair settle with the driver's real PROPH window and
ledge fixes A/B/C; block 4 eh on the true b1. All faithful DIST60, corrected 2026-10 fits, 600 paired per cell.

  python analyze_steer8b2.py
"""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_steer8a import cells, diff
from analyze_steer6r import fmt, RC_SEEDS

BONF = (100 * 0.05 / 7 / 2, 100 - 100 * 0.05 / 7 / 2)        # 7 gb10 tap-out comparisons -> 99.29%


def show(name, X, Y, rule=None):
    tt, tr, tl, ns, txt = diff(X, Y)
    b = diff(X, Y, *BONF)
    print(f"\n{name}\n{txt}\n  Bonferroni 99.29%: tap-out {fmt(b[0])}  race {fmt(b[1])}  lulu {fmt(b[2])}")
    if rule:
        print("  -> " + rule(tt, tr))


def discord(X, Y, label):
    """a2 vs 8a fD: rows that differ on ANY banked key except arm/rig, and on the outcome."""
    for cell, Dx, Dy, outc in (("gb10", X[0], Y[0], "topout"), ("rc10", X[1], Y[1], "how"), ("lulu10", X[2], Y[2], "how")):
        S = [s for s in RC_SEEDS if s in Dx and s in Dy]
        anyk = sum(1 for s in S if any(Dx[s].get(k) != v for k, v in Dy[s].items() if k not in ("arm", "rig")))
        outd = sum(1 for s in S if Dx[s][outc] != Dy[s][outc])
        print(f"  {label} {cell}: n={len(S)}  rows differing on any key {anyk}  outcome ({outc}) differs {outd}")


def main():
    A = cells("steer8/{c}_fD_a2_*.jsonl", "fD_a2")
    names = ("fD_bdep2", "fD_bref2", "fD_c2", "fD_brefA", "fD_brefAB", "fD_brefABC", "fD_ehb0")
    X = {k: cells(f"steer8/{{c}}_{k}_*.jsonl", k) for k in names}
    F = cells("steer8/{c}_fD_*.jsonl", "fD")                              # 8a's faithful DIST60 (pre-amendment model)
    print(f"rows fD_a2: gb10 {len(A[0])} rc10 {len(A[1])} lulu10 {len(A[2])};  8a fD: gb10 {len(F[0])} rc10 {len(F[1])} lulu10 {len(F[2])}")
    for k in names:
        print(f"rows {k}: gb10 {len(X[k][0])} rc10 {len(X[k][1])} lulu10 {len(X[k][2])}")
    print("\n=== a2 (today, PROPH to the first publication) vs 8a fD (today, PROPH to the commit) ===")
    discord(A, F, "a2 vs fD")
    show("a2 - fD (paired)", A, F)
    print("\n=== BLOCK 3 (descriptive): every arm vs (a2) today ===")
    for k, lab in (("fD_bdep2", "(b) fair DRSETTLE + DEPLOYED mask"), ("fD_bref2", "(b) fair DRSETTLE + REFIT mask"),
                   ("fD_c2", "(c) fair, no settle cut  [= minus the pin's worth]"), ("fD_brefA", "(b-ref) + fix A"),
                   ("fD_brefAB", "(b-ref) + fixes A+B"), ("fD_brefABC", "(b-ref) + fixes A+B+C")):
        show(f"{lab}  vs  (a2) today", X[k], A)
    print("\n=== BLOCK 3 decomposition (descriptive) ===")
    show("settle cut under fair gravity: bref2 - c2", X["fD_bref2"], X["fD_c2"])
    show("MASK DECISION: bref2 - bdep2", X["fD_bref2"], X["fD_bdep2"],
         lambda t, r: ("REFIT mask better -> recommend T13/G0 3/PROPH end 4" if t[2] < 0 else
                       "DEPLOYED mask better -> keep fw constants" if t[1] > 0 else
                       "no detectable difference -> keep the deployed fw constants (status quo)"))
    show("fix A: brefA - bref2", X["fD_brefA"], X["fD_bref2"])
    show("fix B: brefAB - brefA", X["fD_brefAB"], X["fD_brefA"])
    show("fix C: brefABC - brefAB", X["fD_brefABC"], X["fD_brefAB"])
    print("\n=== BLOCK 4: eh on the TRUE b1 (vs 8a fD, unchanged) ===")
    show("fD_ehb0 (true b1) vs fD (soft b1, today's fw)", X["fD_ehb0"], F,
         lambda t, r: ("RECOMMEND the fw fix" if (t[2] < 0 and r[2] >= 0) else
                       "HARMFUL" if t[1] > 0 else "no detectable difference -> no fw change needed"))


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
