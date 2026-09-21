"""n=400 confirm: each nonzero clockloop member vs k_clock=0, both seats,
plus Hartford n=400 for every member including k=0.

Seeds 43134+ DECLARED REUSE. Does not overwrite gen0 files.
"""
import sys, json, os, subprocess, hashlib, shlex, collections
sys.path.insert(0, "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx")
import import_pin
import_pin.pin()
from vs_choose import VsPolicy, zeros, KNOBS

CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
OUT = CVX + "/clockloop"
NSEED = int(sys.argv[1]) if len(sys.argv) > 1 else 400
SEED0 = int(os.environ.get("CLOCK_CONFIRM_SEED0", "43134"))
PY = "/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python"
JOBS = "/home/struktured/projects/dr-mario-h16-wt/tmp/clock_confirm_jobs.txt"
HJOBS = "/home/struktured/projects/dr-mario-h16-wt/tmp/clock_confirm_hjobs.txt"
LEDGER = OUT + "/LEDGER.md"
ENV = dict(os.environ,
           NUMBA_CACHE_DIR="/home/struktured/projects/dr-mario-h16-wt/tmp/nbcache_grad2",
           PYTHONUNBUFFERED="1")
P = 16


def pname(m):
    return VsPolicy(**{k: m.get(k, 0.0) for k in KNOBS}).name()


def pf(a, b):
    return f"{OUT}/c_{hashlib.md5((a+'#'+b).encode()).hexdigest()[:10]}.jsonl"


def hf(n):
    return f"{OUT}/ch_{hashlib.md5(n.encode()).hexdigest()[:10]}.jsonl"


pool = json.load(open(OUT + "/POOL.json"))
inc = zeros()
inc_name = pname(inc)
# gen0 members only — spawned gen1 children are unscreened (do not confirm them).
cands = [m for m in pool["members"] if pname(m) != inc_name
         and pool.get("gen", {}).get(pname(m), 0) == 0]
print(f"confirm n={NSEED} seeds {SEED0}+ vs {inc_name}; {len(cands)} candidates", flush=True)

jobs = []
for m in cands:
    a, b = inc_name, pname(m)
    f = pf(a, b)
    if os.path.exists(f) and sum(1 for _ in open(f)) >= NSEED * 2:
        continue
    jobs.append((json.dumps(inc), json.dumps(m), f))
if jobs:
    with open(JOBS, "w") as fh:
        per = max(1, NSEED // 4)
        for ma, mb, f in jobs:
            for k in range(4):
                fh.write(f"{shlex.quote(ma)} {shlex.quote(mb)} {SEED0+k*per*2} {per} 2 {f}.{k}\n")
    subprocess.run(f"xargs -P {P} -L 1 {PY} -u vs_selfplay_worker.py < {JOBS}",
                   shell=True, env=ENV, check=False, cwd=CVX)
    for ma, mb, f in jobs:
        with open(f, "w") as out:
            for k in range(4):
                p = f"{f}.{k}"
                if os.path.exists(p):
                    out.write(open(p).read())

hjobs = []
for m in pool["members"]:
    n = pname(m)
    f = hf(n)
    if os.path.exists(f) and sum(1 for _ in open(f)) >= NSEED:
        continue
    hjobs.append((json.dumps(m), f))
print(f"hartford confirm jobs {len(hjobs)} x {NSEED}", flush=True)
if hjobs:
    with open(HJOBS, "w") as fh:
        per = max(1, NSEED // 4)
        for md, f in hjobs:
            for k in range(4):
                fh.write(f"{shlex.quote(md)} {SEED0+k*per*2} {per} 2 {f}.{k}\n")
    subprocess.run(f"xargs -P {P} -L 1 {PY} -u clock_hartford_worker.py < {HJOBS}",
                   shell=True, env=ENV, check=False, cwd=CVX)
    for md, f in hjobs:
        with open(f, "w") as out:
            for k in range(4):
                p = f"{f}.{k}"
                if os.path.exists(p):
                    out.write(open(p).read())

vs_inc = collections.defaultdict(lambda: [0, 0])
for m in cands:
    f = pf(inc_name, pname(m))
    if not os.path.exists(f):
        continue
    for l in open(f):
        r = json.loads(l)
        if r["winner"] not in (0, 1):
            continue
        wname = r["A"] if r["winner"] == 0 else r["B"]
        other = r["B"] if r["A"] == inc_name else r["A"]
        if wname == inc_name:
            vs_inc[other][1] += 1
        else:
            vs_inc[other][0] += 1

H = {}
for m in pool["members"]:
    n = pname(m)
    f = hf(n)
    if not os.path.exists(f):
        continue
    top = da = cl = rows = el = 0
    for l in open(f):
        r = json.loads(l)
        rows += 1
        top += r["topout"]
        da += r["dies_ahead"]
        cl += r["won"]
        el += r.get("elapsed_s") or 0
    H[n] = {"n": rows, "topout": top, "dies_ahead": da, "clear": cl,
            "elapsed": (el / rows if rows else 0)}

with open(LEDGER, "a") as L:
    L.write(f"\n## CONFIRM n={NSEED} seeds {SEED0}+ vs {inc_name}\n")
    L.write("### VS vs incumbent\n")
    for n, (w, l) in sorted(vs_inc.items(), key=lambda kv: -(kv[1][0] / (sum(kv[1]) or 1))):
        ntot = w + l
        L.write(f"- {100*w/ntot:5.1f}%  ({w}/{ntot})  {n}\n")
        print(f"VS {100*w/ntot:5.1f}% ({w}/{ntot}) {n}", flush=True)
    L.write("### Hartford TRATE=0.025\n")
    for n, h in sorted(H.items(), key=lambda kv: kv[1]["topout"] / (kv[1]["n"] or 1)):
        nn = h["n"] or 1
        L.write(f"- topout {100*h['topout']/nn:5.1f}%  dies-ahead {100*h['dies_ahead']/nn:4.1f}%  "
                f"clear {100*h['clear']/nn:5.1f}%  t={h['elapsed']:.0f}s  n={h['n']}  {n}\n")
        print(f"H topout {100*h['topout']/nn:5.1f}% da {100*h['dies_ahead']/nn:4.1f}% {n}",
              flush=True)
print("CONFIRM_DONE", flush=True)
