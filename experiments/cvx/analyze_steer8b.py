"""STEER8b analysis (PREREG_STEER8b.md): fair settle (block 3), eh on the true b1 (block 4), R4 vs flat hang (block 5),
all on the faithful DIST60 brain under the corrected 2026-10 fits. Block-3 base (a) = STEER8a's fD rows.

  python analyze_steer8b.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_steer8a import cells, diff
from analyze_steer6r import fmt

BONF = (100 * 0.05 / 6 / 2, 100 - 100 * 0.05 / 6 / 2)        # 6 gb10 tap-out comparisons -> 99.17%


def show(name, X, Y, rule=None):
    tt, tr, tl, ns, txt = diff(X, Y)
    b = diff(X, Y, *BONF)
    print(f"\n{name}\n{txt}\n  Bonferroni 99.17%: tap-out {fmt(b[0])}  race {fmt(b[1])}  lulu {fmt(b[2])}")
    if rule:
        print("  -> " + rule(tt, tr))
    return tt, tr


def main():
    A = cells("steer8/{c}_fD_*.jsonl", "fD")
    arms = {k: cells(f"steer8/{{c}}_{k}_*.jsonl", k) for k in ("fD_sB_dep", "fD_sB_ref", "fD_sC", "fD_ehb0", "fD_hang0")}
    print(f"rows (a) fD: gb10 {len(A[0])} rc10 {len(A[1])} lulu10 {len(A[2])}")
    for k, X in arms.items():
        print(f"rows {k}: gb10 {len(X[0])} rc10 {len(X[1])} lulu10 {len(X[2])}")
    print("\n=== BLOCK 3: fair settle (descriptive) ===")
    show("(b-dep) fair DRSETTLE + DEPLOYED mask  vs  (a) today", arms["fD_sB_dep"], A)
    show("(b-ref) fair DRSETTLE + REFIT mask (T13/G0 3)  vs  (a) today", arms["fD_sB_ref"], A)
    show("(c) fair, no settle cut  vs  (a) today   [= minus what the pin was worth]", arms["fD_sC"], A)
    show("(b-ref) vs (c)   [the settle cut under fair gravity]", arms["fD_sB_ref"], arms["fD_sC"])
    show("MASK DECISION: (b-ref) vs (b-dep)", arms["fD_sB_ref"], arms["fD_sB_dep"],
         lambda t, r: ("REFIT mask better -> recommend T13/G0 3" if t[2] < 0 else
                       "DEPLOYED mask better -> keep fw constants" if t[1] > 0 else
                       "no detectable difference -> keep the deployed fw constants (status quo)"))
    print("\n=== BLOCK 4: eh on the TRUE b1 (fw-fix candidate) ===")
    show("fD_ehb0 (true b1) vs fD (soft b1, today's fw)", arms["fD_ehb0"], A,
         lambda t, r: ("RECOMMEND the fw fix" if (t[2] < 0 and r[2] >= 0) else
                       "HARMFUL" if t[1] > 0 else "no detectable difference -> no fw change needed"))
    print("\n=== BLOCK 5: flat hang vs R4 ===")
    show("fD_hang0 (flat 40) vs fD (R4, today's fw)", arms["fD_hang0"], A,
         lambda t, r: ("DROP R4 (flat better)" if (t[2] < 0 and r[2] >= 0) else
                       "R4 earns its keep" if t[1] > 0 else "no detectable difference"))


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
