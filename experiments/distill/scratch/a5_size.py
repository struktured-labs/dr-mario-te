"""A5 sizing curve: held-out danger yield and cost vs back-fill design.
Rates are measured per plies-to-end bucket on the base bank's own trigger
states, then applied to trace-counted trigger plies. Offline, no compute."""
import glob, gzip, json, os, binascii, math
import numpy as np
OUT = "/home/struktured/projects/dr-mario-distill-wt/experiments/distill/out/labels_m1"
ST = "L20"
def held(s): return binascii.crc32(str(s).encode()) % 4 == 0
def fire(H): return max(H[3], H[4]) >= 13
EDGES = [0,10,20,30,45,60,90,10**9]
def buck(d):
    for i in range(len(EDGES)-1):
        if EDGES[i] <= d < EDGES[i+1]: return i
    raise ValueError(d)

trig = {}          # bucket -> [n, n_degen, n_danger_nondegen]
games = []         # (seed, n_plies, res, [trigger plies-to-end])
S=[];F=[];P=[]
for f in sorted(glob.glob(os.path.join(OUT, ST, "seed_*.json.gz"))):
    r = json.load(gzip.open(f, "rt"))
    if r["smoke"]: continue
    n = r["game"]["n_plies"]; S.append(r["secs"]); P.append(n)
    F.append(r["counters"]["tribunal_forks"])
    for a in r["adjudications"]:
        if "trigger" not in a["classes"]: continue
        b = buck(n - a["ply"]); t = trig.setdefault(b, [0,0,0])
        t[0]+=1; t[1]+=a["degenerate"]
        if not a["degenerate"] and a["champ_s2"]<=3: t[2]+=1
    games.append((r["seed"], n, r["game"]["res"],
                  [n-p for p,H in enumerate(r["heights_trace"]) if fire(H)]))
S,F,P = map(np.array,(S,F,P))
A = np.column_stack([np.ones(len(S)),F,P]); c,*_ = np.linalg.lstsq(A,S,rcond=None)
FPA = 89.8
print("base-bank trigger states by plies-to-end bucket:")
for b in sorted(trig):
    n_,dg,dn = trig[b]
    nd = n_-dg
    print(f"  [{EDGES[b]:>3},{EDGES[b+1] if EDGES[b+1]<10**9 else 'inf':>4}) "
          f"n={n_:5d} degen={dg/max(n_,1):.3f} danger|nondeg={dn/max(nd,1):.3f}")
rate = {b: ((trig[b][0]-trig[b][1])/max(trig[b][0],1),
            trig[b][2]/max(trig[b][0]-trig[b][1],1)) for b in trig}

se0, n0, cap, bar = 0.0302, 93, 0.0645, 0.099
def power(n):
    se = se0*math.sqrt(n0/n); z=(bar-cap)/se-1.96
    return 0.5*(1+math.erf(z/math.sqrt(2)))

print(f"\n{'design':<34} {'games':>6} {'adjs':>7} {'held-dang':>9} "
      f"{'TOTAL':>6} {'core-h':>7} {'KILLpow':>7}")
def price(sel):
    adjs=0; hd=0.0; gh=0; pl=0
    for seed,n,res,tri in sel:
        gh+=1; pl+=n
        for d in tri:
            b=buck(d); adjs+=1
            if held(seed):
                nd,dr = rate.get(b,(0.93,0.16)); hd += nd*dr
    ch = (adjs*FPA*c[1] + gh*c[0] + pl*c[2])/3600
    return gh, adjs, hd, ch
for label, sel in (
    ("W=30  topout only (A5 as sized)", [(s,n,r,[d for d in t if d<30]) for s,n,r,t in games if r=="topout"]),
    ("W=45  topout only", [(s,n,r,[d for d in t if d<45]) for s,n,r,t in games if r=="topout"]),
    ("W=60  topout only", [(s,n,r,[d for d in t if d<60]) for s,n,r,t in games if r=="topout"]),
    ("W=90  topout only", [(s,n,r,[d for d in t if d<90]) for s,n,r,t in games if r=="topout"]),
    ("FULL game, topout only", [(s,n,r,t) for s,n,r,t in games if r=="topout"]),
    ("FULL game, ALL games (un-thin)", games),
):
    gh,adjs,hd,ch = price(sel)
    tot = 93+hd
    print(f"{label:<34} {gh:6d} {adjs:7d} {hd:9.0f} {tot:6.0f} {ch:7.1f} "
          f"{power(tot):7.0%}")
