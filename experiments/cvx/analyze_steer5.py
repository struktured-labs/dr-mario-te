"""STEER5 analysis per PREREG_STEER5.md: leaf terms vs the shipping REACH+TAP baseline; fresh-block control."""
import sys, os, json, glob, random
CVX = os.path.dirname(os.path.abspath(__file__)); os.chdir(CVX); sys.path.insert(0, CVX)

ARMS = ["s5_bur32", "s5_bur96", "s5_acc60", "s5_acc180", "s5_rb48", "s5_rb144"]


def rows(pattern, label):
    d = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == label and r.get("level", 11) == 11:
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


def unpaired(A, B, fn, n=4000, seed=2):
    a = [fn(r) for r in A.values()]; b = [fn(r) for r in B.values()]
    rng = random.Random(seed); out = []
    for _ in range(n):
        ma = sum(a[rng.randrange(len(a))] for _ in a) / len(a)
        mb = sum(b[rng.randrange(len(b))] for _ in b) / len(b)
        out.append(ma - mb)
    out.sort()
    return 100 * (sum(a) / len(a) - sum(b) / len(b)), 100 * out[int(.025 * n)], 100 * out[int(.975 * n)]


if __name__ == "__main__":
    base = rows("steer4/remote/s4_base_*.jsonl", "fw540_steer_s4_base")
    print(f"{'arm':10s} {'n':>4} {'tap<=100':>9} {'d [95% CI]':>24} {'tap-out':>8} {'d [95% CI]':>24} {'win':>6}  verdict")
    s = list(base.values()); n = len(s)
    print(f"{'base':10s} {n:4d} {100*sum(early(r) for r in s)/n:8.2f}% {'(baseline)':>24} {100*sum(tap(r) for r in s)/n:7.2f}% {'':>24} {100*sum(r['won'] for r in s)/n:5.1f}%")
    for a in ARMS:
        d = rows(f"steer5/*/{a}_*.jsonl", "fw540_steer_" + a)
        if len(d) < len(base): print(f"{a:10s} (pending: {len(d)})"); continue
        s = list(d.values()); n = len(s)
        e = paired(d, base, early); t = paired(d, base, tap)
        ok = (e[2] < 0 and t[2] <= 1.0) or (t[2] < 0 and e[2] <= 1.0)
        print(f"{a:10s} {n:4d} {100*sum(early(r) for r in s)/n:8.2f}% {e[0]:+6.2f} [{e[1]:+6.2f},{e[2]:+6.2f}] "
              f"{100*sum(tap(r) for r in s)/n:7.2f}% {t[0]:+6.2f} [{t[1]:+6.2f},{t[2]:+6.2f}] {100*sum(r['won'] for r in s)/n:5.1f}%  {'PASS' if ok else 'fail'}")
    ctl = rows("steer5/control/ctl_*.jsonl", "fw540_steer_s5_base")
    if ctl:
        s = list(ctl.values()); n = len(s)
        e = unpaired(ctl, base, early); t = unpaired(ctl, base, tap)
        print(f"\nCONTROL (baseline on {n} FRESH streams) tap<=100 {100*sum(early(r) for r in s)/n:.2f}% "
              f"(fresh - reused {e[0]:+.2f} [{e[1]:+.2f},{e[2]:+.2f}])  tap-out {100*sum(tap(r) for r in s)/n:.2f}% "
              f"(fresh - reused {t[0]:+.2f} [{t[1]:+.2f},{t[2]:+.2f}])  win {100*sum(r['won'] for r in s)/n:.1f}%")
