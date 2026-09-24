"""Analyze vs_race runs: win rate vs a modelled human, outcome decomposition, break-even pace.

Usage: python analyze_vsrace.py [DIR] [--m 177] [--lam 3.3] [--delta 2.0] [--sigma 0.15] [--base holes80]
"""
import sys, json, glob, random, collections, argparse
sys.path.insert(0, "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx")
from vs_race import evaluate

ap = argparse.ArgumentParser()
ap.add_argument("dir", nargs="?", default="vsrace1")
ap.add_argument("--m", type=float, default=177.0)
ap.add_argument("--lam", type=float, default=3.3)
ap.add_argument("--delta", type=float, default=2.0)
ap.add_argument("--sigma", type=float, default=0.15)
ap.add_argument("--base", default="holes80")
a = ap.parse_args()

rows = [json.loads(l) for f in glob.glob(f"{a.dir}/*.jsonl") for l in open(f) if l.strip()]
by = collections.defaultdict(dict)
for r in rows:
    by[(r["arm"], float(r["lam"]))][r["seed"]] = r
arms = sorted({k[0] for k in by})
lams = sorted({k[1] for k in by})


def wins(d, seeds, m, sigma, delta):
    return {s: evaluate(d[s], m, sigma, delta)[0] == "win_race" for s in seeds}


def boot(xs, n=2000, seed=1):
    rng = random.Random(seed); k = len(xs); out = []
    for _ in range(n):
        out.append(sum(xs[rng.randrange(k)] for _ in range(k)) / k)
    out.sort(); return out[int(0.025 * n)], out[int(0.975 * n)]


def breakeven(d, seeds, sigma, delta):
    lo, hi = 60.0, 900.0                       # smallest human median pace we beat >=50% of the time
    for _ in range(40):
        mid = (lo + hi) / 2
        w = sum(wins(d, seeds, mid, sigma, delta).values()) / len(seeds)
        if w >= 0.5: hi = mid
        else: lo = mid
    return (lo + hi) / 2


print(f"VS-RACE — bot vs modelled human. rev {rows[0]['rev'][:60] if rows else '?'}")
print(f"primary cell: human median {a.m:.0f}s (sigma {a.sigma}), lam {a.lam}/min, delta {a.delta}s/tile\n")
for lam in lams:
    print(f"=== volley rate {lam}/min ===")
    print(f"{'arm':12s} {'n':>4} {'WIN%':>6} {'95% CI':>13} | {'win':>4} {'l_race':>6} {'l_kill':>6} {'l_cap':>5} | {'clear%':>6} {'med t_end':>9} {'sent':>5} {'recv':>5} | {'break-even pace':>15}")
    for arm in arms:
        d = by.get((arm, lam))
        if not d: continue
        seeds = sorted(d)
        oc = collections.Counter(evaluate(d[s], a.m, a.sigma, a.delta)[0] for s in seeds)
        w = [1.0 if evaluate(d[s], a.m, a.sigma, a.delta)[0] == "win_race" else 0.0 for s in seeds]
        lo, hi = boot(w)
        clr = sum(d[s]["how"] == "clear" for s in seeds) / len(seeds)
        te = sorted(d[s]["t_end"] for s in seeds)[len(seeds) // 2]
        sent = sum(d[s]["tiles_sent"] for s in seeds) / len(seeds)
        recv = sum(d[s]["tiles_recv"] for s in seeds) / len(seeds)
        be = breakeven(d, seeds, a.sigma, a.delta)
        print(f"{arm:12s} {len(seeds):4d} {100*sum(w)/len(w):5.1f}% [{100*lo:4.1f},{100*hi:4.1f}] | "
              f"{oc['win_race']:4d} {oc['loss_race']:6d} {oc['loss_kill']:6d} {oc['loss_cap']:5d} | "
              f"{100*clr:5.1f}% {te:8.0f}s {sent:5.1f} {recv:5.1f} | beats humans slower than {be:5.0f}s")
    base = by.get((a.base, lam))
    if base:
        print(f"  paired vs {a.base} (win-rate difference, seed bootstrap):")
        for arm in arms:
            d = by.get((arm, lam))
            if not d or arm == a.base: continue
            seeds = sorted(set(d) & set(base))
            wa = wins(d, seeds, a.m, a.sigma, a.delta); wb = wins(base, seeds, a.m, a.sigma, a.delta)
            diff = [float(wa[s]) - float(wb[s]) for s in seeds]
            lo, hi = boot(diff)
            print(f"    {arm:12s} {100*sum(diff)/len(diff):+5.1f}pp [{100*lo:+5.1f},{100*hi:+5.1f}]  (n={len(seeds)})")
    print()

print(f"=== sensitivity at lam {a.lam}, human {a.m:.0f}s: win% by damage-per-tile delta (ASSUMED param) ===")
print(f"{'arm':12s} " + " ".join(f"{'d=' + str(dl):>7}" for dl in (0.0, 1.0, 2.0, 3.0)) + "   | sigma 0.10 / 0.25 (d=2)")
for arm in arms:
    d = by.get((arm, a.lam))
    if not d: continue
    seeds = sorted(d)
    cells = [100 * sum(wins(d, seeds, a.m, a.sigma, dl).values()) / len(seeds) for dl in (0.0, 1.0, 2.0, 3.0)]
    sg = [100 * sum(wins(d, seeds, a.m, sg, 2.0).values()) / len(seeds) for sg in (0.10, 0.25)]
    print(f"{arm:12s} " + " ".join(f"{c:6.1f}%" for c in cells) + f"   | {sg[0]:5.1f}% / {sg[1]:5.1f}%")
