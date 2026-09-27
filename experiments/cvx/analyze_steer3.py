"""STEER3 analysis per PREREG_STEER3.md: tap period P vs DAS, reach root on, couch steering on."""
import sys, os, json, glob, random
CVX = os.path.dirname(os.path.abspath(__file__)); os.chdir(CVX); sys.path.insert(0, CVX)
from vs_race import evaluate


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
def win(r, dl): return int(evaluate(r, 177.0, 0.15, dl)[0] == "win_race")


def paired(A, B, fn):
    s = sorted(set(A) & set(B)); d = [fn(A[x]) - fn(B[x]) for x in s]; lo, hi = boot(d)
    return 100 * sum(d) / len(d), 100 * lo, 100 * hi, len(s)


if __name__ == "__main__":
    base = rows("steer1/remote/reach_*.jsonl", "fw540_steer_reach")
    S = {"DAS (P=inf)": base}
    for P in (2, 3, 4, 5):
        S[f"P={P}"] = rows(f"steer3/surv/tap{P}_*.jsonl", f"fw540_steer_tap{P}_reach")
        if not S[f"P={P}"]:
            S[f"P={P}"] = rows(f"steer3/remote/tap{P}_*.jsonl", f"fw540_steer_tap{P}_reach")
    d2 = paired(S["P=2"], base, early)[0] if S["P=2"] else None
    print("SURVIVAL gate (b), owner model, L11 MED, fw540 + reach root (mask at the same P), steering on")
    print(f"{'P (Hz)':14s} {'n':>4} {'tap<=100':>9} {'d vs DAS [95% CI]':>24} {'tap-out':>8} {'d vs DAS [95% CI]':>24} {'kept':>6}")
    for k, d in S.items():
        if not d: print(f"{k:14s} (pending)"); continue
        s = list(d.values()); n = len(s)
        line = f"{k:14s} {n:4d} {100*sum(early(r) for r in s)/n:8.2f}%"
        if k.startswith("P="):
            e = paired(d, base, early); t = paired(d, base, tap)
            kept = f"{100*e[0]/d2:5.0f}%" if d2 else "-"
            line += f" {e[0]:+6.2f} [{e[1]:+6.2f},{e[2]:+6.2f}] {100*sum(tap(r) for r in s)/n:7.2f}% {t[0]:+6.2f} [{t[1]:+6.2f},{t[2]:+6.2f}] {kept:>6}"
        else:
            line += f" {'(baseline)':>24} {100*sum(tap(r) for r in s)/n:7.2f}%"
        print(line)
    rb = rows("steer2/race/fw540_reach_*.jsonl", "fw540_reach~steer")
    print("\nRACE vs_race lam 6, vs a 177-s human, steering on (reach mask at the same P)")
    print(f"  DAS (P=inf) n={len(rb)} win d2.65 {100*sum(win(r,2.65) for r in rb.values())/len(rb):.1f}%  d2.0 {100*sum(win(r,2.0) for r in rb.values())/len(rb):.1f}%")
    for P in (2, 4):
        d = rows(f"steer3/race/tap{P}_*.jsonl", f"fw540_reach_tap{P}~steer")
        if not d: print(f"  P={P} (pending)"); continue
        s = list(d.values())
        a = paired(d, rb, lambda r: win(r, 2.65)); b = paired(d, rb, lambda r: win(r, 2.0))
        print(f"  P={P} n={len(s)} win d2.65 {100*sum(win(r,2.65) for r in s)/len(s):.1f}% ({a[0]:+.2f} [{a[1]:+.2f},{a[2]:+.2f}])"
              f"  d2.0 {100*sum(win(r,2.0) for r in s)/len(s):.1f}% ({b[0]:+.2f} [{b[1]:+.2f},{b[2]:+.2f}])")
