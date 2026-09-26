"""STEER5(a): PRE-TREATMENT stratification by the initial count of high spawn-column viruses (hsv9 = cols 3-5,
row < 9, from the reset layout; hsv_census.py). Baseline dose-response + per-arm paired effect within strata.
Usage: python strata_steer5.py [ARM ...]  (default: all STEER5 arms present)"""
import sys, os, json, glob, random
CVX = os.path.dirname(os.path.abspath(__file__)); os.chdir(CVX); sys.path.insert(0, CVX)
from analyze_steer5 import rows, boot, early, tap

STRATA = [("<=4", lambda h: h <= 4), ("5", lambda h: h == 5), ("6", lambda h: h == 6), (">=7", lambda h: h >= 7)]


def paired_in(A, B, seeds, fn):
    d = [fn(A[x]) - fn(B[x]) for x in seeds if x in A and x in B]
    if not d: return None
    lo, hi = boot(d)
    return 100 * sum(d) / len(d), 100 * lo, 100 * hi, len(d)


if __name__ == "__main__":
    H = {int(k): v["hsv9"] for k, v in json.load(open("steer5/hsv_census.json")).items()}
    base = rows("steer4/remote/s4_base_*.jsonl", "fw540_steer_s4_base")
    ctl = rows("steer5/control/ctl_*.jsonl", "fw540_steer_s5_base")
    print("BASELINE dose-response (reused block) and CONTROL (fresh block), by initial hsv9:")
    for nm, D in (("baseline", base), ("control", ctl)):
        for sn, f in STRATA:
            s = [r for sd, r in D.items() if f(H[sd])]
            if not s: continue
            print(f"  {nm:9s} hsv9 {sn:>3}: n={len(s):3d}  tap<=100 {100*sum(early(r) for r in s)/len(s):5.1f}%  "
                  f"tap-out {100*sum(tap(r) for r in s)/len(s):5.1f}%  win {100*sum(r['won'] for r in s)/len(s):5.1f}%")
    arms = sys.argv[1:] or ["s5_bur32", "s5_bur96", "s5_acc60", "s5_acc180", "s5_rb48", "s5_rb144", "s5b_hsv180", "s5b_hsv540"]
    print("\nPer-arm paired effect vs baseline WITHIN stratum (tap<=100 | tap-out):")
    for a in arms:
        d = rows(f"steer5/*/{a}_*.jsonl", "fw540_steer_" + a)
        if len(d) < len(base): continue
        cells = []
        for sn, f in STRATA:
            sd = [x for x in base if f(H[x])]
            e = paired_in(d, base, sd, early); t = paired_in(d, base, sd, tap)
            cells.append(f"{sn}: {e[0]:+5.1f} [{e[1]:+5.1f},{e[2]:+5.1f}] | {t[0]:+5.1f} [{t[1]:+5.1f},{t[2]:+5.1f}]")
        print(f"  {a:11s} " + "   ".join(cells))
