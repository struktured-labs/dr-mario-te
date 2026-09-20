"""VS self-play v2: fictitious play over winner-trunk + interaction knobs.

v1 (k_race, k_tempo only) gen0 crowned k=0. Frozen in cvx/vsloop/.
v2 adds k_atk (send_halves × opp spawn), k_safe (own spawn × ahead),
k_time (short drop × clock urgency).

Objective is match win, not solitaire tap-out. Incumbent is all-k=0 (pure winner).
"""
import sys, json, os, subprocess, itertools, random, collections, hashlib, shlex
sys.path.insert(0, "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx")
import import_pin
import_pin.pin()
from vs_choose import VsPolicy, zeros, KNOBS

CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
OUT = os.environ.get("VSLOOP_OUT", CVX + "/vsloop2")
os.makedirs(OUT, exist_ok=True)
GEN = int(sys.argv[1])
NSEED = int(sys.argv[2])  # seeds per pairing; each seed is 2 seats
KEEP, CHILDREN = 3, 4
SEED0 = int(os.environ.get("VSLOOP_SEED0", "41134"))  # DECLARED REUSE (fresh vs v1 36734)
POOLF = OUT + "/POOL.json"
LEDGER = OUT + "/LEDGER.md"
PY = "/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python"

STEPS = {"k_race": 400.0, "k_tempo": 80.0, "k_atk": 200.0, "k_safe": 200.0, "k_time": 80.0}


def gen0():
    # Sparse: incumbent + one-change of the NEW knobs + one combo.
    # k_race/k_tempo already failed as the gen0 axis (vsloop/ LEDGER).
    members = [zeros()]
    for ka in (200.0, 800.0):
        d = zeros(); d["k_atk"] = ka; members.append(d)
    d = zeros(); d["k_safe"] = 200.0; members.append(d)
    d = zeros(); d["k_time"] = 80.0; members.append(d)
    d = zeros(); d["k_atk"] = 200.0; d["k_safe"] = 200.0; members.append(d)
    return members


def pname(m):
    return VsPolicy(**{k: m.get(k, 0.0) for k in KNOBS}).name()


def pf(a, b):
    return f"{OUT}/g_{hashlib.md5((a+'#'+b).encode()).hexdigest()[:10]}.jsonl"


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
print(f"gen {GEN}: pool {len(pool['members'])}, new pairings {len(jobs)} x {NSEED} seeds x 2 seats",
      flush=True)
J = "/home/struktured/projects/dr-mario-h16-wt/tmp/vsloop2_jobs.txt"
os.makedirs(os.path.dirname(J), exist_ok=True)
with open(J, "w") as fh:
    per = max(1, NSEED // 4)
    for ma, mb, f in jobs:
        for k in range(4):
            fh.write(f"{shlex.quote(ma)} {shlex.quote(mb)} {SEED0+k*per*2} {per} 2 {f}.{k}\n")
json.dump(pool, open(POOLF, "w"))
if jobs:
    env = dict(os.environ,
               NUMBA_CACHE_DIR="/home/struktured/projects/dr-mario-h16-wt/tmp/nbcache_grad2",
               PYTHONUNBUFFERED="1")
    subprocess.run(f"xargs -P 12 -L 1 {PY} -u vs_selfplay_worker.py < {J}",
                   shell=True, env=env, check=False, cwd=CVX)
    for ma, mb, f in jobs:
        with open(f, "w") as out:
            for k in range(4):
                p = f"{f}.{k}"
                if os.path.exists(p):
                    out.write(open(p).read())

W = collections.defaultdict(lambda: [0, 0])
how = collections.Counter()
vs_inc = collections.defaultdict(lambda: [0, 0])
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
        if inc_name in (r["A"], r["B"]):
            other = r["B"] if r["A"] == inc_name else r["A"]
            if wname == inc_name:
                vs_inc[other][1] += 1
            else:
                vs_inc[other][0] += 1
fit = {n: (w / (w + l) if w + l else 0.0, w + l) for n, (w, l) in W.items()}
rank = sorted(fit.items(), key=lambda kv: -kv[1][0])
with open(LEDGER, "a") as L:
    L.write(f"\n## gen {GEN} — pool {len(pool['members'])} (VS win vs ALL others, seat-swapped)\n")
    L.write(f"seeds {SEED0}+ n={NSEED} how={dict(how)}\n")
    for n, (p, k) in rank:
        L.write(f"- {p*100:5.1f}%  (n={k})  gen{pool['gen'].get(n, '?')}  {n}\n")
    L.write(f"\n### vs incumbent {inc_name} (promote bar: >55%)\n")
    for n, (w, l) in sorted(vs_inc.items(), key=lambda kv: -(kv[1][0] / (sum(kv[1]) or 1))):
        ntot = w + l
        L.write(f"- {100*w/ntot:5.1f}%  ({w}/{ntot})  {n}\n")
print("\n".join(f"{p*100:5.1f}% n={k} gen{pool['gen'].get(n, '?')} {n}" for n, (p, k) in rank),
      flush=True)
print("vs incumbent:", flush=True)
for n, (w, l) in sorted(vs_inc.items(), key=lambda kv: -(kv[1][0] / (sum(kv[1]) or 1))):
    ntot = w + l
    print(f"  {100*w/ntot:5.1f}% ({w}/{ntot}) {n}", flush=True)

rng = random.Random(2000 + GEN)
top_names = {n for n, _ in rank[:KEEP]}
top = [m for m in pool["members"] if pname(m) in top_names]
names = {pname(m) for m in pool["members"]}
added, tries = 0, 0
while added < CHILDREN and tries < 200:
    tries += 1
    parent = dict(zeros())
    parent.update(rng.choice(top))
    k = rng.choice(list(STEPS))
    parent[k] = max(0.0, float(parent.get(k, 0.0)) + rng.choice([-2, -1, 1, 2]) * STEPS[k])
    if pname(parent) in names:
        continue
    pool["members"].append(parent)
    pool["gen"][pname(parent)] = GEN + 1
    names.add(pname(parent))
    added += 1
json.dump(pool, open(POOLF, "w"))
print(f"spawned {added} children for gen {GEN+1}", flush=True)
