"""Beat kc40 on blackmage: finer k_clock + flatten-penalty (k_hold).

Bar: VS vs k=0 ≥60% AND Hartford tap-out ≤42.8% (kc40 n=400). Screen n=80.
Seeds 47134+ DECLARED REUSE. -P 10 so Quartus keeps cores.
"""
import sys, json, os, subprocess, hashlib, shlex, collections
sys.path.insert(0, "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx")
import import_pin
import_pin.pin()
from vs_choose import VsPolicy, zeros, KNOBS

CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
OUT = os.environ.get("CLOCK_BEAT_OUT", CVX + "/clockbeat")
os.makedirs(OUT, exist_ok=True)
NSEED = int(sys.argv[1]) if len(sys.argv) > 1 else 80
SEED0 = int(os.environ.get("CLOCK_BEAT_SEED0", "47134"))
PY = "/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python"
P = int(os.environ.get("CLOCK_BEAT_P", "10"))
LEDGER = OUT + "/LEDGER.md"
ENV = dict(os.environ,
           NUMBA_CACHE_DIR="/home/struktured/projects/dr-mario-h16-wt/tmp/nbcache_grad2",
           PYTHONUNBUFFERED="1")
JOBS = "/home/struktured/projects/dr-mario-h16-wt/tmp/clockbeat_jobs.txt"
HJOBS = "/home/struktured/projects/dr-mario-h16-wt/tmp/clockbeat_hjobs.txt"


def mem(**kw):
    d = zeros()
    d.update(kw)
    return d


def pname(m):
    return VsPolicy(**{k: m.get(k, 0.0) for k in KNOBS}).name()


# Override with CLOCK_BEAT_MEMBERS=kc34 for confirm.
_raw = os.environ.get("CLOCK_BEAT_MEMBERS", "")
if _raw == "kc34":
    MEMBERS = [mem(), mem(k_clock=34.0)]
else:
    MEMBERS = [
        mem(),  # k=0 bar
        mem(k_clock=26.0),
        mem(k_clock=30.0),
        mem(k_clock=34.0),
        mem(k_clock=38.0),
        mem(k_hold=40.0),
        mem(k_hold=80.0),
        mem(k_clock=30.0, k_hold=40.0),
    ]
inc = mem()
inc_name = pname(inc)


def pf(a, b):
    return f"{OUT}/g_{hashlib.md5((a+'#'+b).encode()).hexdigest()[:10]}.jsonl"


def hf(n):
    return f"{OUT}/h_{hashlib.md5(n.encode()).hexdigest()[:10]}.jsonl"


cands = [m for m in MEMBERS if pname(m) != inc_name]
print(f"beat n={NSEED} seeds {SEED0}+ vs {inc_name}; {len(cands)} cands P={P}", flush=True)

jobs = []
for m in cands:
    f = pf(inc_name, pname(m))
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
for m in MEMBERS:
    n = pname(m)
    f = hf(n)
    if os.path.exists(f) and sum(1 for _ in open(f)) >= NSEED:
        continue
    hjobs.append((json.dumps(m), f))
print(f"hartford {len(hjobs)} x {NSEED}", flush=True)
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
for m in MEMBERS:
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

BAR_VS, BAR_H = 0.60, 0.428
with open(LEDGER, "a") as L:
    L.write(f"\n## beat n={NSEED} seeds {SEED0}+  bar VS≥{BAR_VS:.0%} H_topout≤{BAR_H:.1%}\n")
    L.write("### VS vs k=0\n")
    for n, (w, l) in sorted(vs_inc.items(), key=lambda kv: -(kv[1][0] / (sum(kv[1]) or 1))):
        ntot = w + l
        rate = w / ntot if ntot else 0
        flag = " BEAT" if rate >= BAR_VS else ""
        L.write(f"- {100*rate:5.1f}%  ({w}/{ntot}){flag}  {n}\n")
        print(f"VS {100*rate:5.1f}% ({w}/{ntot}){flag} {n}", flush=True)
    L.write("### Hartford\n")
    for n, h in sorted(H.items(), key=lambda kv: kv[1]["topout"] / (kv[1]["n"] or 1)):
        nn = h["n"] or 1
        ht = h["topout"] / nn
        flag = " BEAT" if n != inc_name and ht <= BAR_H else ""
        L.write(f"- topout {100*ht:5.1f}%  da {100*h['dies_ahead']/nn:4.1f}%  "
                f"t={h['elapsed']:.0f}s  n={h['n']}{flag}  {n}\n")
        print(f"H topout {100*ht:5.1f}% da {100*h['dies_ahead']/nn:4.1f}%{flag} {n}",
              flush=True)
print("BEAT_DONE", flush=True)
