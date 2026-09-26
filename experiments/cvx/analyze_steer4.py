"""STEER4 analysis per PREREG_STEER4.md: shape levers vs the shipping REACH+TAP baseline (gate b, owner, L11)."""
import sys, os, json, glob, random
CVX = os.path.dirname(os.path.abspath(__file__)); os.chdir(CVX); sys.path.insert(0, CVX)

ARMS = ["s4_base", "s4_sv180", "s4_sv540", "s4_sp100", "s4_sp300", "s4_rot2", "s4_combo"]


def rows(arm):
    d = {}
    for f in glob.glob(f"steer4/*/{arm}_*.jsonl"):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == "fw540_steer_" + arm and r.get("level", 11) == 11:
                d[r["seed"]] = r
    return d


def boot(xs, n=4000, seed=1):
    rng = random.Random(seed); k = len(xs)
    o = sorted(sum(xs[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return o[int(.025 * n)], o[int(.975 * n)]


def early(r): return int(r["topout"] and r["pills"] <= 100)
def tap(r): return int(r["topout"])


def paired(A, B, fn):
    s = sorted(set(A) & set(B)); d = [fn(A[x]) - fn(B[x]) for x in s]; lo, hi = boot(d)
    return 100 * sum(d) / len(d), 100 * lo, 100 * hi, len(s)


if __name__ == "__main__":
    D = {a: rows(a) for a in ARMS}
    base = D["s4_base"]
    print(f"{'arm':10s} {'n':>4} {'tap<=100':>9} {'d [95% CI]':>24} {'tap-out':>8} {'d [95% CI]':>24} {'win':>6}  verdict")
    best = None
    for a in ARMS:
        d = D[a]
        if not d: print(f"{a:10s} (pending)"); continue
        s = list(d.values()); n = len(s)
        line = f"{a:10s} {n:4d} {100*sum(early(r) for r in s)/n:8.2f}%"
        if a == "s4_base":
            line += f" {'(baseline)':>24} {100*sum(tap(r) for r in s)/n:7.2f}% {'':>24} {100*sum(r['won'] for r in s)/n:5.1f}%"
        else:
            e = paired(d, base, early); t = paired(d, base, tap)
            ok = (e[2] < 0 and t[2] <= 1.0) or (t[2] < 0 and e[2] <= 1.0)
            line += (f" {e[0]:+6.2f} [{e[1]:+6.2f},{e[2]:+6.2f}] {100*sum(tap(r) for r in s)/n:7.2f}%"
                     f" {t[0]:+6.2f} [{t[1]:+6.2f},{t[2]:+6.2f}] {100*sum(r['won'] for r in s)/n:5.1f}%  {'PASS' if ok else 'fail'}")
            if a in ("s4_sv180", "s4_sv540", "s4_sp100", "s4_sp300") and len(d) == len(base):
                key = (e[0], t[0])
                if best is None or key < best[0]:
                    best = (key, a)
        print(line)
    cands = ("s4_sv180", "s4_sv540", "s4_sp100", "s4_sp300")
    if best and all(len(D[c]) == len(base) for c in cands):
        print(f"\narm (4) selection rule -> best of (1)/(2) by tap<=100 (tie: tap-out): {best[1]} (+ rot2)")
    else:
        print("\narm (4) selection: waiting for all four (1)/(2) arms")
