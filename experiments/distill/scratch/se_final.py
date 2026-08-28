"""Final A5 sizing: contributing GAMES under each design, counted from the
traces, with the SE law calibrated to the observed held-out reading.
Only the RATIO from the law is used — it overpredicts absolute SE at the
reference point, so an absolute reading would be a plausible wrong answer."""
import sys, glob, gzip, json, os, math, random, binascii
import numpy as np
sys.path.insert(0,"/home/struktured/projects/dr-mario-distill-wt/experiments/distill")
OUT="/home/struktured/projects/dr-mario-distill-wt/experiments/distill/out/labels_m1"
def held(s): return binascii.crc32(str(s).encode())%4==0
def fire(H): return max(H[3],H[4])>=13
EDGES=[0,10,20,30,45,60,90,10**9]
def buck(d):
    for i in range(len(EDGES)-1):
        if EDGES[i]<=d<EDGES[i+1]: return i
trig={}; games=[]
for f in sorted(glob.glob(os.path.join(OUT,"L20","seed_*.json.gz"))):
    r=json.load(gzip.open(f,"rt"))
    if r["smoke"]: continue
    n=r["game"]["n_plies"]
    for a in r["adjudications"]:
        if "trigger" not in a["classes"]: continue
        b=buck(n-a["ply"]); t=trig.setdefault(b,[0,0,0]); t[0]+=1; t[1]+=a["degenerate"]
        if not a["degenerate"] and a["champ_s2"]<=3: t[2]+=1
    games.append((r["seed"],n,r["game"]["res"],
                  [n-p for p,H in enumerate(r["heights_trace"]) if fire(H)]))
rate={b:((trig[b][0]-trig[b][1])/trig[b][0], trig[b][2]/max(trig[b][0]-trig[b][1],1)) for b in trig}
A,B = 0.05245, 0.07124                      # measured law
SE_OBS, NG_OBS, S_OBS = 0.0301, 38, 2.45    # the real pre-A5 held-out reading
def se_model(ng,s): return math.sqrt((A+B/s)/ng)
CAL = SE_OBS/se_model(NG_OBS,S_OBS)         # ratio calibration (R62-style)
def se(ng,s): return CAL*se_model(ng,s)
def power(x):
    z=(0.099-0.0645)/x-1.96; return 0.5*(1+math.erf(z/math.sqrt(2)))
print(f"law Var=(A+B/s)/n_g with A={A} B={B}; model overpredicts the "
      f"reference SE by {1/CAL:.2f}x -> using the RATIO only (cal={CAL:.3f})\n")
def design(sel_games, window):
    ng=0; tot=0.0
    for seed,n,res,tri in sel_games:
        if not held(seed): continue
        d=[x for x in tri if window is None or x<window]
        e=sum(rate[buck(x)][0]*rate[buck(x)][1] for x in d)
        if e>0: ng+= 1-math.exp(-e)     # expected P(game contributes >=1)
        tot+=e
    return ng, tot
print(f"{'design':<40} {'held-games':>10} {'held-dang':>9} {'st/gm':>6} "
      f"{'SE':>7} {'power':>6}")
rows=[("pre-A5 (measured, no design)",None,None,38,93)]
for lab,sel,win in (("A5 approved W=30 topout-only",[g for g in games if g[2]=="topout"],30),
                    ("A5 W=30 all games",games,30),
                    ("PHASE 1 un-thin ALL held-out games",games,None)):
    ng,tot=design(sel,win); rows.append((lab,sel,win,ng,93+tot))
for lab,_,_,ng,tot in rows:
    s=tot/max(ng,1); x=se(ng,s)
    print(f"{lab:<40} {ng:10.0f} {tot:9.0f} {s:6.2f} {x:7.4f} {power(x):6.0%}")
print("\nthe two axes, at the measured law (calibrated):")
for ng in (38,58,100,164):
    print("  games=%3d : " % ng + "  ".join(
        f"s={s:<4.1f} SE={se(ng,s):.4f} pw={power(se(ng,s)):3.0%}"
        for s in (2.5,5,10,1e6)))
