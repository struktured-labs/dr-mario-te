"""STEER1 analysis per PREREG_STEER1.md. Arms keyed by each row's own `arm` label.
Usage: python analyze_steer1.py [DIR ...]   (default: steer1/main steer1/remote; arm 0 = banked gateb/fw540)
"""
import sys, os, json, glob, random
CVX = os.path.dirname(os.path.abspath(__file__))
os.chdir(CVX)
ORDER = ["off", "couch", "brainproph", "prehold", "pulse", "reach", "couch_byrot", "prehold_byrot", "prehold_plan", "prehold_plan_byrot"]


def load(dirs):
    A = {a: {} for a in ORDER}
    for f in glob.glob("gateb/fw540_*.jsonl"):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == "fw540" and r.get("model") == "owner" and r.get("level", 11) == 11:
                A["off"][r["seed"]] = r
    for d in dirs:
        for f in glob.glob(os.path.join(d, "*.jsonl")):
            for l in open(f):
                r = json.loads(l)
                arm = r.get("arm", "").replace("fw540_steer_", "")
                if arm in A:
                    A[arm][r["seed"]] = r
    return A


def boot(xs, n=4000, seed=1):
    rng = random.Random(seed); k = len(xs)
    o = sorted(sum(xs[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return o[int(.025 * n)], o[int(.975 * n)]


def early(r, n=100):
    return int(r["topout"] and r["pills"] <= n)


if __name__ == "__main__":
    dirs = sys.argv[1:] or ["steer1/main", "steer1/remote", "steer1/sens", "steer1/plan"]
    A = load(dirs)
    print(f"{'arm':11s} {'n':>4} {'tap-out':>8} {'tap<=100':>9} {'win':>6} {'cap':>5} {'hazard/pill':>11} | {'off-tgt':>7} {'PROPH':>6} {'clamp':>6}")
    for a in ORDER:
        d = A[a]
        if not d: print(f"{a:11s} (no rows)"); continue
        s = list(d.values()); n = len(s); P = sum(r["pills"] for r in s)
        st = [r["steer"] for r in s if "steer" in r]; SP = sum(x["pills"] for x in st) or 1
        rate = lambda k: 100 * sum(x[k] for x in st) / SP if st else float("nan")
        print(f"{a:11s} {n:4d} {100*sum(r['topout'] for r in s)/n:7.2f}% {100*sum(early(r) for r in s)/n:8.2f}% "
              f"{100*sum(r['won'] for r in s)/n:5.1f}% {100*sum(r['stall'] for r in s)/n:4.1f}% {100*sum(r['topout'] for r in s)/P:10.3f}% | "
              f"{rate('moved_off_target'):6.2f}% {rate('proph_fired'):5.2f}% {rate('clamp_short'):5.2f}%")
    print("\npaired (seed bootstrap 95% CI):")
    pairs = [("couch", "off")] + [(x, "couch") for x in ORDER[2:6]] + \
            [("couch_byrot", "off"), ("prehold_byrot", "couch_byrot"),
             ("prehold_plan", "couch"), ("prehold_plan_byrot", "couch_byrot")]
    for a, b in pairs:
        s = sorted(set(A[a]) & set(A[b]))
        if not s: continue
        for m, fn in (("tap-out", lambda r: r["topout"]), ("tap<=100", early), ("win", lambda r: r["won"])):
            d = [fn(A[a][x]) - fn(A[b][x]) for x in s]; lo, hi = boot(d)
            print(f"  {a:10s} - {b:6s} {m:8s} {100*sum(d)/len(d):+6.2f}pp [{100*lo:+6.2f},{100*hi:+6.2f}] n={len(s)}")
