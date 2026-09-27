"""STEER2 analysis per PREREG_STEER2.md (all cells steering ON unless marked 'perfect')."""
import sys, os, json, glob, random
CVX = os.path.dirname(os.path.abspath(__file__)); os.chdir(CVX); sys.path.insert(0, CVX)
from vs_race import evaluate


def rows(pattern, label=None, level=None):
    d = {}
    for f in glob.glob(pattern):
        for l in open(f):
            r = json.loads(l)
            if label is not None and r.get("arm") != label: continue
            if level is not None and r.get("level", 11) != level: continue
            d[r["seed"]] = r
    return d


def boot(xs, n=4000, seed=1):
    rng = random.Random(seed); k = len(xs)
    o = sorted(sum(xs[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return o[int(.025 * n)], o[int(.975 * n)]


def early(r): return int(r["topout"] and r["pills"] <= 100)


def win(r, delta, m=177.0): return int(evaluate(r, m, 0.15, delta)[0] == "win_race")


def breakeven(d, delta):
    lo, hi = 60.0, 900.0; s = list(d.values())
    for _ in range(40):
        mid = (lo + hi) / 2
        if sum(win(r, delta, mid) for r in s) / len(s) >= 0.5: hi = mid
        else: lo = mid
    return (lo + hi) / 2


def paired(A, B, fn):
    s = sorted(set(A) & set(B)); d = [fn(A[x]) - fn(B[x]) for x in s]; lo, hi = boot(d)
    return 100 * sum(d) / len(d), 100 * lo, 100 * hi, len(s)


if __name__ == "__main__":
    extra = "--extra" in sys.argv
    S = {"fw540": rows("steer1/main/couch_*.jsonl", "fw540_steer_couch"),
         "fw540+reach": rows("steer1/remote/reach_*.jsonl", "fw540_steer_reach"),
         "fw180": rows("steer2/surv/w180_*.jsonl", "fw540_steer_w180"),
         "fw180+reach": rows("steer2/remote/w180_reach_*.jsonl", "fw540_steer_w180_reach")}
    if extra:
        S["fw540+reachFW"] = rows("steer2/fw/surv_*.jsonl", "fw540_steer_reachfw")
    print("A. SURVIVAL (gate b, owner model, L11 MED, steering on)")
    print(f"  {'cell':14s} {'n':>4} {'tap<=100':>9} {'tap-out':>8} {'win':>6}")
    for k, d in S.items():
        s = list(d.values()); n = len(s)
        print(f"  {k:14s} {n:4d} {100*sum(early(r) for r in s)/n:8.2f}% {100*sum(r['topout'] for r in s)/n:7.2f}% {100*sum(r['won'] for r in s)/n:5.1f}%")
    pairs = [("fw540+reach", "fw540"), ("fw180+reach", "fw180"), ("fw540", "fw180"), ("fw540+reach", "fw180+reach")]
    if extra: pairs += [("fw540+reachFW", "fw540"), ("fw540+reachFW", "fw540+reach")]
    for a, b in pairs:
        for m, fn in (("tap<=100", early), ("tap-out", lambda r: r["topout"])):
            print(f"    {a:13s} - {b:12s} {m:8s} %+6.2fpp [%+6.2f,%+6.2f] n=%d" % paired(S[a], S[b], fn))
    R = {"fw540": rows("steer2/race/fw540_*.jsonl", "fw540~steer"),
         "fw540+reach": rows("steer2/race/fw540_reach_*.jsonl", "fw540_reach~steer"),
         "fw180": rows("steer2/race/fw_winner_*.jsonl", "fw_winner~steer"),
         "fw180+reach": rows("steer2/race/fw_winner_reach_*.jsonl", "fw_winner_reach~steer"),
         "fw540 (perfect)": rows("vsrace2/fw540_l6.0_*.jsonl", "fw540"),
         "fw180 (perfect)": rows("vsrace2/fw_winner_l6.0_*.jsonl", "fw_winner")}
    if extra:
        R["fw540+reachFW"] = rows("steer2/fw/race_*.jsonl", "fw540_reachfw~steer")
    print("\nB. RACE (vs_race lam 6, vs a 177-s human sigma 0.15)")
    print(f"  {'cell':16s} {'n':>4} {'WIN d2.65':>9} {'WIN d2.0':>9} {'clear%':>7} {'med t_end':>9} {'sent':>5} {'b-even d2.65':>12} {'b-even d2.0':>11}")
    for k, d in R.items():
        s = list(d.values()); n = len(s)
        if not n: continue
        te = sorted(r["t_end"] for r in s)[n // 2]
        print(f"  {k:16s} {n:4d} {100*sum(win(r,2.65) for r in s)/n:8.1f}% {100*sum(win(r,2.0) for r in s)/n:8.1f}% "
              f"{100*sum(r['how']=='clear' for r in s)/n:6.1f}% {te:8.0f}s {sum(r['tiles_sent'] for r in s)/n:5.1f} "
              f"{breakeven(d,2.65):10.0f}s {breakeven(d,2.0):10.0f}s")
    rp = [("fw540+reach", "fw540"), ("fw180+reach", "fw180"), ("fw540", "fw180"), ("fw540+reach", "fw180+reach"),
          ("fw540", "fw540 (perfect)"), ("fw180", "fw180 (perfect)")]
    if extra: rp += [("fw540+reachFW", "fw540"), ("fw540+reachFW", "fw540+reach")]
    for a, b in rp:
        for dl in (2.65, 2.0):
            print(f"    {a:15s} - {b:16s} win d{dl}: %+6.2fpp [%+6.2f,%+6.2f] n=%d" % paired(R[a], R[b], lambda r, dl=dl: win(r, dl)))
    L = {"fw540": rows("steer2/l15/couch_L15_*.jsonl", "fw540_steer_couch", 15),
         "fw540+reach": rows("steer2/l15/reach_L15_*.jsonl", "fw540_steer_reach", 15)}
    print("\nC. L15 (gate b, steering on)")
    for k, d in L.items():
        s = list(d.values()); n = len(s)
        print(f"  {k:14s} {n:4d} tap<=100 {100*sum(early(r) for r in s)/n:6.2f}%  tap-out {100*sum(r['topout'] for r in s)/n:6.2f}%  win {100*sum(r['won'] for r in s)/n:5.1f}%")
    for m, fn in (("tap<=100", early), ("tap-out", lambda r: r["topout"])):
        print(f"    fw540+reach - fw540 {m:8s} %+6.2fpp [%+6.2f,%+6.2f] n=%d" % paired(L["fw540+reach"], L["fw540"], fn))
