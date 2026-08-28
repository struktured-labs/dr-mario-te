"""Phase design: un-thin ALL trigger plies (no window, no outcome selection).
Held-out games alone drive the held-danger n; train games drive the fit."""
import glob, gzip, json, os, binascii, math
import numpy as np
OUT="/home/struktured/projects/dr-mario-distill-wt/experiments/distill/out/labels_m1"
def held(s): return binascii.crc32(str(s).encode()) % 4 == 0
def fire(H): return max(H[3],H[4]) >= 13
EDGES=[0,10,20,30,45,60,90,10**9]
def buck(d):
    for i in range(len(EDGES)-1):
        if EDGES[i]<=d<EDGES[i+1]: return i
trig={}; games=[]; S=[];F=[];P=[]
for f in sorted(glob.glob(os.path.join(OUT,"L20","seed_*.json.gz"))):
    r=json.load(gzip.open(f,"rt"))
    if r["smoke"]: continue
    n=r["game"]["n_plies"]; S.append(r["secs"]); P.append(n); F.append(r["counters"]["tribunal_forks"])
    for a in r["adjudications"]:
        if "trigger" not in a["classes"]: continue
        b=buck(n-a["ply"]); t=trig.setdefault(b,[0,0,0]); t[0]+=1; t[1]+=a["degenerate"]
        if not a["degenerate"] and a["champ_s2"]<=3: t[2]+=1
    games.append((r["seed"],n,r["game"]["res"],
                  [n-p for p,H in enumerate(r["heights_trace"]) if fire(H)]))
S,F,P=map(np.array,(S,F,P)); A=np.column_stack([np.ones(len(S)),F,P])
c,*_=np.linalg.lstsq(A,S,rcond=None); FPA=89.8
rate={b:((trig[b][0]-trig[b][1])/trig[b][0], trig[b][2]/max(trig[b][0]-trig[b][1],1)) for b in trig}
se0,n0,cap,bar=0.0302,93,0.0645,0.099
def power(n):
    se=se0*math.sqrt(n0/n); return 0.5*(1+math.erf(((bar-cap)/se-1.96)/math.sqrt(2)))
def price(sel):
    adjs=sum(len(t) for _,_,_,t in sel); gh=len(sel); pl=sum(n for _,n,_,_ in sel)
    dang=sum(rate[buck(d)][0]*rate[buck(d)][1] for _,_,_,t in sel for d in t)
    return gh,adjs,dang,(adjs*FPA*c[1]+gh*c[0]+pl*c[2])/3600
H=[g for g in games if held(g[0])]; T=[g for g in games if not held(g[0])]
gh,adjs,hd,ch = price(H)
print(f"PHASE 1  un-thin ALL trigger plies in HELD-OUT games only")
print(f"  games={gh} ({gh/len(games):.1%})  adjudications={adjs}  "
      f"new held-danger={hd:.0f}  TOTAL held-danger={93+hd:.0f}")
print(f"  cost={ch:.0f} core-h   KILL power={power(93+hd):.0%}")
print(f"  train UNCHANGED (danger 260) => arm F == arm P, no training confound")
gh2,adjs2,td,ch2 = price(T)
print(f"PHASE 2  un-thin ALL trigger plies in TRAIN games")
print(f"  games={gh2}  adjudications={adjs2}  new train-danger={td:.0f} "
      f"(260 -> {260+td:.0f}, {(260+td)/260:.1f}x)")
print(f"  cost={ch2:.0f} core-h")
print(f"BOTH = {ch+ch2:.0f} core-h;  wall @14w = {(ch+ch2)/14:.0f}h "
      f"(phase 1 alone {ch/14:.1f}h)")
print(f"\nCOMPARISON at matched cost:")
for lab,g_,a_,d_,c_ in (("A5 approved (W=30, topout-only)",254,4579,290,119.9),
                        ("PHASE 1 (un-thin, held-out games)",gh,adjs,hd,ch)):
    print(f"  {lab:36s} {c_:6.1f} core-h  held-danger {93+d_:5.0f}  "
          f"power {power(93+d_):4.0%}")
