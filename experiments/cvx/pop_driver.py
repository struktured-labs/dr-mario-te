"""Generation driver: builds the job list for all UNPLAYED pairings in the pool, runs them via xargs,
scores the pool (fictitious-play mean win rate), writes POOL.json + LEDGER.md, spawns the next gen."""
import sys, json, os, subprocess, itertools, random, collections, glob, hashlib, shlex
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"; E47="/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
sys.path.insert(0,H16); import h16_arm  # noqa  (provides fast_sim_x et al.)
sys.path.insert(0,CVX); sys.path.insert(1,E47)
os.chdir(CVX)
GEN=int(sys.argv[1]); N=int(sys.argv[2]); KEEP=3; CHILDREN=5
import fast_rtl_x  # noqa
assert fast_rtl_x.__file__.startswith(CVX)
import population as POP
POOL="pop/POOL.json"; os.makedirs("pop",exist_ok=True)
pool=json.load(open(POOL)) if os.path.exists(POOL) else {"members":[], "gen":{}}
if GEN==0 and not pool["members"]:
    for m in POP.gen0(): pool["members"].append(m); pool["gen"][POP.name(m)]=0
def pf(a,b): return f"pop/g_{hashlib.md5((a+'#'+b).encode()).hexdigest()[:10]}.jsonl"
jobs=[]
for ma,mb in itertools.combinations(pool["members"],2):
    a,b=POP.name(ma),POP.name(mb); f=pf(a,b)
    if os.path.exists(f) and sum(1 for _ in open(f))>=N: continue
    jobs.append((json.dumps(ma),json.dumps(mb),f))
print(f"gen {GEN}: pool {len(pool['members'])}, new pairings {len(jobs)} x {N} games")
J="/home/struktured/projects/dr-mario-h16-wt/tmp/pop_jobs.txt"
with open(J,"w") as fh:
    for ma,mb,f in jobs:
        # split each pairing into 4 shards for parallelism
        per=N//4
        for k in range(4):
            fh.write(f"{shlex.quote(ma)} {shlex.quote(mb)} {36734+k*per*2} {per} 2 {f}.{k}\n")
json.dump(pool,open(POOL,"w"))
if jobs:
    env=dict(os.environ,NUMBA_CACHE_DIR="/home/struktured/projects/dr-mario-h16-wt/tmp/nbcache_grad2")
    subprocess.run(f"xargs -P 12 -L 1 /home/struktured/projects/dr_mario_rl/tmp/venv/bin/python pop_worker.py < {J}",shell=True,env=env,check=False)
    for ma,mb,f in jobs:
        with open(f,"w") as out:
            for k in range(4):
                if os.path.exists(f"{f}.{k}"): out.write(open(f"{f}.{k}").read())
# score
W=collections.defaultdict(lambda:[0,0])
for ma,mb in itertools.combinations(pool["members"],2):
    a,b=POP.name(ma),POP.name(mb); f=pf(a,b)
    if not os.path.exists(f): continue
    for l in open(f):
        r=json.loads(l)
        if r["winner"]==0: W[a][0]+=1; W[b][1]+=1
        elif r["winner"]==1: W[b][0]+=1; W[a][1]+=1
fit={n:(w/(w+l) if w+l else 0.0, w+l) for n,(w,l) in W.items()}
rank=sorted(fit.items(),key=lambda kv:-kv[1][0])
with open("pop/LEDGER.md","a") as L:
    L.write(f"\n## gen {GEN} — pool {len(pool['members'])} (fictitious-play win rate vs ALL others)\n")
    for n,(p,k) in rank: L.write(f"- {p*100:5.1f}%  (n={k})  gen{pool['gen'][n]}  {n}\n")
print("\n".join(f"{p*100:5.1f}% n={k} gen{pool['gen'][n]} {n}" for n,(p,k) in rank))
# next generation
rng=random.Random(1000+GEN)
top=[m for m in pool["members"] if POP.name(m) in {n for n,_ in rank[:KEEP]}]
names={POP.name(m) for m in pool["members"]}
added=0; tries=0
while added<CHILDREN and tries<200:
    tries+=1; c=POP.mutate(rng.choice(top),rng)
    if POP.name(c) in names: continue
    pool["members"].append(c); pool["gen"][POP.name(c)]=GEN+1; names.add(POP.name(c)); added+=1
json.dump(pool,open(POOL,"w"))
print(f"spawned {added} children for gen {GEN+1}")
