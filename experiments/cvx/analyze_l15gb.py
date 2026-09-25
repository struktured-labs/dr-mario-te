"""L15 gate (b) tap-out (RESULT_DOSE2 pending item): fw_winner / fw540 / fw720, owner burst model,
paired seeds 40134.. step 2, rows from Hetzner /root/drm/l15gb (unit drm-l15gb).
Usage: python analyze_l15gb.py [DIR=gateb_l15]"""
import json, glob, random, sys
import os
D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "gateb_l15")
def load(a):
    d = {}
    for f in glob.glob(f"{D}/{a}_L15_*.jsonl"):
        for l in open(f):
            r = json.loads(l)
            if r.get("arm") == a and r.get("level") == 15: d[r["seed"]] = r
    return d
def boot(xs, n=4000, seed=1):
    rng = random.Random(seed); k = len(xs); o = sorted(sum(xs[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return o[int(.025 * n)], o[int(.975 * n)]
A = {a: load(a) for a in ("fw_winner", "fw540", "fw720")}
for a, d in A.items():
    s = sorted(d); n = len(s)
    if not n: continue
    print(f"{a:10s} n={n:4d} win {100*sum(d[x]['won'] for x in s)/n:5.1f}%  tap-out {100*sum(d[x]['topout'] for x in s)/n:5.2f}%  "
          f"stall(cap) {100*sum(d[x]['stall'] for x in s)/n:5.2f}%  med pills {sorted(d[x]['pills'] for x in s)[n//2]}")
b = A["fw540"]
for a in ("fw_winner", "fw720"):
    s = sorted(set(A[a]) & set(b))
    if not s: continue
    for k in ("topout", "stall", "won"):
        df = [A[a][x][k] - b[x][k] for x in s]; lo, hi = boot(df)
        print(f"  {a} - fw540 {k:6s} {100*sum(df)/len(s):+5.2f}pp [{100*lo:+5.2f},{100*hi:+5.2f}] n={len(s)}")
