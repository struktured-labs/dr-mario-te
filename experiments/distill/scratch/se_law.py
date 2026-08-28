"""Measure how the CLUSTERED SE actually responds to its two axes —
number of GAMES and states PER GAME — instead of assuming 1/sqrt(n_states).
Fit Var = A/n_g + B/(n_g*s) on subsamples of the banked danger states, then
extrapolate to the phase-1 design. R9: measure the instrument before choosing.
"""
import sys, json, os, math, random
import numpy as np
sys.path.insert(0,"/home/struktured/projects/dr-mario-distill-wt/experiments/distill")
import m2_screens as M

rows = M.assemble("L20")
frz = json.load(open(os.path.join(M.HERE,"out","m2_fit_frozen.json")))
mu,sd,wq = np.array(frz["mu"]),np.array(frz["sd"]),np.array(frz["wq"])
def g(X): return ((X-mu)/sd)@wq
tau,m = frz["tau"],frz["m"]

# pool ALL danger states (train+held) for the scaling measurement — the law is
# a property of the estimator, not of the split
by = {}
for r in rows:
    if not r["danger"]: continue
    gain,_ = M._gain(r,g,tau,m); by.setdefault(r["seed"],[]).append(gain)
print(f"pool: {sum(len(v) for v in by.values())} danger states, "
      f"{len(by)} games, states/game mean={np.mean([len(v) for v in by.values()]):.2f}")

def clust_se(d):
    ns = np.array([len(v) for v in d.values()],float)
    gs = np.array([sum(v) for v in d.values()],float)
    if len(ns) < 3 or ns.sum() == 0: return None
    th = gs.sum()/ns.sum(); r = gs - th*ns
    return math.sqrt(len(ns)/(len(ns)-1)*(r**2).sum()/ns.sum()**2)

rng = random.Random(7)
obs = []
keys = list(by)
for ng in (20, 40, 80, 120, len(keys)):
    for frac in (0.34, 0.67, 1.0):
        vals = []
        for _ in range(120):
            ks = rng.sample(keys, min(ng, len(keys)))
            d = {}
            for k in ks:
                v = by[k]
                take = max(1, int(round(len(v)*frac)))
                d[k] = rng.sample(v, take)
            se = clust_se(d)
            if se: vals.append(se)
        if not vals: continue
        s = np.mean([len(v) for v in
                     [by[k][:max(1,int(round(len(by[k])*frac)))] for k in keys]])
        obs.append((min(ng,len(keys)), s, float(np.mean(vals))))
        print(f"  games={min(ng,len(keys)):3d} states/game={s:.2f} "
              f"-> clustered SE={np.mean(vals):.4f}")

# fit Var*n_g = A + B/s
X = np.array([[1.0, 1.0/s] for _,s,_ in obs])
y = np.array([se*se*ng for ng,s,se in obs])
(Ahat,Bhat),*_ = np.linalg.lstsq(X,y,rcond=None)
print(f"\nfit: Var = ({Ahat:.5f} + {Bhat:.5f}/s) / n_games")
print(f"  A (BETWEEN-game, irreducible by un-thinning) = {Ahat:.5f}")
print(f"  B (WITHIN-game sampling noise, removed by un-thinning) = {Bhat:.5f}")
def se_of(ng,s): return math.sqrt(max(Ahat+Bhat/s,1e-12)/ng)
def power(se): 
    z=(0.099-0.0645)/se-1.96; return 0.5*(1+math.erf(z/math.sqrt(2)))
print(f"\ncheck vs the real pre-A5 held-out reading (38 games, 2.45/game): "
      f"predicted SE={se_of(38,2.45):.4f} vs measured 0.0301")
print(f"\n{'design':<44} {'games':>5} {'st/gm':>6} {'SE':>7} {'power':>6}")
for lab,ng,s in (("pre-A5 held-out (measured)",38,2.45),
                 ("A5 approved: W=30 topout-only",58,383/58),
                 ("PHASE 1: un-thin all held-out games",164,785/164),
                 ("PHASE 1 + phase 2 (train too, same held n)",164,785/164)):
    print(f"{lab:<44} {ng:5d} {s:6.2f} {se_of(ng,s):7.4f} {power(se_of(ng,s)):6.0%}")
print("\nwhat WOULD reach 80% power:")
for ng in (164, 250, 400, 600, 900):
    s_needed = None
    for s in np.arange(1,60,0.5):
        if power(se_of(ng,s)) >= 0.80: s_needed = s; break
    print(f"  games={ng:4d} -> needs {'%.1f states/game'%s_needed if s_needed else 'UNREACHABLE at any density'}")
