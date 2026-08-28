"""Does the clustered SE actually fall as states/game grows?
Decompose the pre-A5 held-out danger set: how many GAMES contribute, and how
much of the variance is BETWEEN games (a floor un-thinning cannot remove)
vs WITHIN games (sampling noise un-thinning does remove)."""
import sys, json, os, math, random
import numpy as np
sys.path.insert(0, "/home/struktured/projects/dr-mario-distill-wt/experiments/distill")
import m2_screens as M

rows = M.assemble("L20")
ho_d = [r for r in rows if M.held(r["seed"]) and r["danger"]]
frz = json.load(open(os.path.join(M.HERE, "out", "m2_fit_frozen.json")))
mu, sd, wq = np.array(frz["mu"]), np.array(frz["sd"]), np.array(frz["wq"])
def g(X): return ((X - mu) / sd) @ wq
tau, m = frz["tau"], frz["m"]

per = {}
for r in ho_d:
    gain, _ = M._gain(r, g, tau, m)
    a, n = per.get(r["seed"], (0.0, 0)); per[r["seed"]] = (a + gain, n + 1)
ns = np.array([n for _, n in per.values()]); gs = np.array([a for a, _ in per.values()])
theta = gs.sum() / ns.sum()
print(f"held-out danger states n={len(ho_d)} across {len(per)} GAMES "
      f"(states/game mean={ns.mean():.2f} max={ns.max()})")
# ratio-estimator clustered variance
resid = gs - theta * ns
var = (len(per) / (len(per) - 1)) * (resid**2).sum() / (ns.sum()**2)
se_clust = math.sqrt(var)
print(f"clustered SE (analytic ratio estimator) = {se_clust:.4f}")
lo, hi = M.boot_ci(ho_d, lambda rr: M.plain(rr, g, tau, m)[0])
print(f"bootstrap CI [{lo:.4f},{hi:.4f}] -> SE={(hi-lo)/2/1.96:.4f} "
      f"(agrees with the 0.0302 on record)")
# variance decomposition: between-game vs within-game
pergain = {}
for r in ho_d:
    gain, _ = M._gain(r, g, tau, m); pergain.setdefault(r["seed"], []).append(gain)
allg = np.array([x for v in pergain.values() for x in v])
within = np.mean([np.var(v, ddof=1) for v in pergain.values() if len(v) > 1]) \
    if any(len(v) > 1 for v in pergain.values()) else 0.0
means = np.array([np.mean(v) for v in pergain.values()])
print(f"total per-state var={allg.var(ddof=1):.4f}  "
      f"mean WITHIN-game var={within:.4f}  var of game MEANS={means.var(ddof=1):.4f}")
# projected SE if states/game rises 8.4x with the SAME 173 games available
print("\nprojection — un-thinning adds states to EXISTING games and makes "
      "silent games contribute:")
n_held_games = len({r['seed'] for r in rows if M.held(r['seed'])})
print(f"  held-out games in the bank: {n_held_games}; "
      f"currently contributing danger: {len(per)}")
for mult, label in ((8.4, "phase 1 (n 93->785)"),):
    # optimistic: pure 1/sqrt(n_states);  realistic: clusters grow too
    se_naive = se_clust / math.sqrt(mult)
    # cluster-limited floor: within-game noise -> 0, only between-game left
    ng_new = n_held_games
    se_floor = math.sqrt(means.var(ddof=1) / ng_new)
    print(f"  {label}: naive 1/sqrt(n) SE={se_naive:.4f} | "
          f"cluster floor (within->0, {ng_new} games) SE={se_floor:.4f}")
    for nm, se in (("naive", se_naive), ("floor", se_floor)):
        z = (0.099 - 0.0645) / se - 1.96
        print(f"     {nm:6s} SE={se:.4f} -> KILL power "
              f"{0.5*(1+math.erf(z/math.sqrt(2))):.0%}")
