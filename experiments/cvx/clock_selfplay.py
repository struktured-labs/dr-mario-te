"""Clock-in-search loop: winner trunk + k_clock * dt at the root.

VS fictitious-play (both seats) AND Hartford TRATE=0.025 solo tap-out.
k_clock=0 is pure winner. Do not Quartus. Do not run vsloop2 gen1.
"""
import sys, json, os, subprocess, itertools, random, collections, hashlib, shlex
sys.path.insert(0, "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx")
import import_pin
import_pin.pin()
from vs_choose import VsPolicy, zeros, KNOBS

CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
OUT = os.environ.get("CLOCKLOOP_OUT", CVX + "/clockloop")
os.makedirs(OUT, exist_ok=True)
GEN = int(sys.argv[1])
NSEED = int(sys.argv[2])
KEEP, CHILDREN = 3, 4
SEED0 = int(os.environ.get("CLOCKLOOP_SEED0", "42134"))  # DECLARED REUSE
POOLF = OUT + "/POOL.json"
LEDGER = OUT + "/LEDGER.md"
PY = "/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python"
JOBS = "/home/struktured/projects/dr-mario-h16-wt/tmp/clockloop_jobs.txt"
HJOBS = "/home/struktured/projects/dr-mario-h16-wt/tmp/clockloop_hjobs.txt"
ENV = dict(os.environ,
           NUMBA_CACHE_DIR="/home/struktured/projects/dr-mario-h16-wt/tmp/nbcache_grad2",
           PYTHONUNBUFFERED="1")


def gen0():
    members = []
    # kc80/160 moved 36%/55% in scale — ki80-class, barred from gen0.
    for kc in (0.0, 10.0, 20.0, 40.0):
        d = zeros()
        d["k_clock"] = kc
        members.append(d)
    return members


def pname(m):
    return VsPolicy(**{k: m.get(k, 0.0) for k in KNOBS}).name()


def pf(a, b):
    return f"{OUT}/g_{hashlib.md5((a+'#'+b).encode()).hexdigest()[:10]}.jsonl"


def hf(n):
    return f"{OUT}/h_{hashlib.md5(n.encode()).hexdigest()[:10]}.jsonl"


def _xargs(jobfile, worker):
    os.makedirs(os.path.dirname(jobfile), exist_ok=True)
    subprocess.run(f"xargs -P 12 -L 1 {PY} -u {worker} < {jobfile}",
                   shell=True, env=ENV, check=False, cwd=CVX)


pool = json.load(open(POOLF)) if os.path.exists(POOLF) else {"members": [], "gen": {}}
if GEN == 0 and not pool["members"]:
    for m in gen0():
        pool["members"].append(m)
        pool["gen"][pname(m)] = 0

jobs = []
for ma, mb in itertools.combinations(pool["members"], 2):
    a, b = pname(ma), pname(mb)
    f = pf(a, b)
    if os.path.exists(f) and sum(1 for _ in open(f)) >= NSEED * 2:
        continue
    jobs.append((json.dumps(ma), json.dumps(mb), f))
print(f"gen {GEN}: pool {len(pool['members'])}, VS pairings {len(jobs)} x {NSEED} x 2",
      flush=True)
json.dump(pool, open(POOLF, "w"))
if jobs:
    with open(JOBS, "w") as fh:
        per = max(1, NSEED // 4)
        for ma, mb, f in jobs:
            for k in range(4):
                fh.write(f"{shlex.quote(ma)} {shlex.quote(mb)} {SEED0+k*per*2} {per} 2 {f}.{k}\n")
    _xargs(JOBS, "vs_selfplay_worker.py")
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
    hjobs.append((json.dumps(m), f, n))
print(f"hartford jobs {len(hjobs)} x {NSEED}", flush=True)
if hjobs:
    with open(HJOBS, "w") as fh:
        per = max(1, NSEED // 4)
        for md, f, _n in hjobs:
            for k in range(4):
                fh.write(f"{shlex.quote(md)} {SEED0+k*per*2} {per} 2 {f}.{k}\n")
    _xargs(HJOBS, "clock_hartford_worker.py")
    for md, f, _n in hjobs:
        with open(f, "w") as out:
            for k in range(4):
                p = f"{f}.{k}"
                if os.path.exists(p):
                    out.write(open(p).read())

W = collections.defaultdict(lambda: [0, 0])
how = collections.Counter()
vs_inc = collections.defaultdict(lambda: [0, 0])
dies_vs = collections.defaultdict(int)
inc_name = pname(zeros())
for ma, mb in itertools.combinations(pool["members"], 2):
    a, b = pname(ma), pname(mb)
    f = pf(a, b)
    if not os.path.exists(f):
        continue
    for l in open(f):
        r = json.loads(l)
        how[r.get("how", "?")] += 1
        if r["winner"] not in (0, 1):
            continue
        if r["winner"] == 0:
            W[r["A"]][0] += 1
            W[r["B"]][1] += 1
            wname, lname = r["A"], r["B"]
        else:
            W[r["B"]][0] += 1
            W[r["A"]][1] += 1
            wname, lname = r["B"], r["A"]
        if r.get("how") == "opp_topout":
            dies_vs[lname] += 1
        if inc_name in (r["A"], r["B"]):
            other = r["B"] if r["A"] == inc_name else r["A"]
            if wname == inc_name:
                vs_inc[other][1] += 1
            else:
                vs_inc[other][0] += 1
fit = {n: (w / (w + l) if w + l else 0.0, w + l) for n, (w, l) in W.items()}
rank = sorted(fit.items(), key=lambda kv: -kv[1][0])

H = {}
for m in pool["members"]:
    name = pname(m)
    f = hf(name)
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
    H[name] = {"n": rows, "topout": top, "dies_ahead": da, "clear": cl,
               "elapsed": (el / rows if rows else 0)}

with open(LEDGER, "a") as L:
    L.write(f"\n## gen {GEN} — pool {len(pool['members'])} clock-in-search\n")
    L.write(f"seeds {SEED0}+ n={NSEED} VS how={dict(how)}\n")
    L.write("### VS vs pool\n")
    for n, (p, k) in rank:
        L.write(f"- {p*100:5.1f}%  (n={k})  gen{pool['gen'].get(n, '?')}  {n}\n")
    L.write(f"### VS vs incumbent {inc_name} (promote >55%)\n")
    for n, (w, l) in sorted(vs_inc.items(), key=lambda kv: -(kv[1][0] / (sum(kv[1]) or 1))):
        ntot = w + l
        L.write(f"- {100*w/ntot:5.1f}%  ({w}/{ntot})  {n}\n")
    L.write("### Hartford TRATE=0.025 solo (tap-out / dies-ahead / elapsed)\n")
    for n, h in sorted(H.items(), key=lambda kv: kv[1]["topout"] / (kv[1]["n"] or 1)):
        nn = h["n"] or 1
        L.write(f"- topout {100*h['topout']/nn:5.1f}%  dies-ahead {100*h['dies_ahead']/nn:4.1f}%  "
                f"clear {100*h['clear']/nn:5.1f}%  t={h['elapsed']:.0f}s  n={h['n']}  {n}\n")
print("VS pool:", flush=True)
print("\n".join(f"{p*100:5.1f}% n={k} {n}" for n, (p, k) in rank), flush=True)
print("VS vs incumbent:", flush=True)
for n, (w, l) in sorted(vs_inc.items(), key=lambda kv: -(kv[1][0] / (sum(kv[1]) or 1))):
    ntot = w + l
    print(f"  {100*w/ntot:5.1f}% ({w}/{ntot}) {n}", flush=True)
print("Hartford:", flush=True)
for n, h in sorted(H.items(), key=lambda kv: kv[1]["topout"] / (kv[1]["n"] or 1)):
    nn = h["n"] or 1
    print(f"  topout {100*h['topout']/nn:5.1f}% da {100*h['dies_ahead']/nn:4.1f}% "
          f"t={h['elapsed']:.0f}s n={h['n']} {n}", flush=True)

rng = random.Random(3000 + GEN)
top_names = {n for n, _ in rank[:KEEP]}
top = [m for m in pool["members"] if pname(m) in top_names]
names = {pname(m) for m in pool["members"]}
added, tries = 0, 0
while added < CHILDREN and tries < 200:
    tries += 1
    parent = dict(zeros())
    parent.update(rng.choice(top) if top else zeros())
    parent["k_clock"] = max(0.0, float(parent.get("k_clock", 0.0))
                            + rng.choice([-2, -1, 1, 2]) * 20.0)
    if pname(parent) in names:
        continue
    pool["members"].append(parent)
    pool["gen"][pname(parent)] = GEN + 1
    names.add(pname(parent))
    added += 1
json.dump(pool, open(POOLF, "w"))
print(f"spawned {added} children for gen {GEN+1}", flush=True)
