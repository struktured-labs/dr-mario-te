#!/usr/bin/env python3
"""⚠⚠ DEPRECATED 2026-08-01 — SUPERSEDED BY `vs_harness` (tmp/vs_aware/vs_harness.py).
DO NOT USE FOR NEW WORK. Kept for provenance, not for running.

WHY, so nobody greps for "a VS harness" in six months and picks this one:

  * WRONG ATTACK RULE. Its match loop comes from `vs_env.py`, whose trigger
    counts only lines cleared in the SAME step. The ROM's comboCounter SUMS
    ACROSS CASCADE STEPS and is never reset inside a cascade, so a cascade of
    two single lines DOES attack -- ~85% of all real attacks. Mesen-confirmed.
    This rig fires ~6.7x too rarely. See memory `dr-mario-rom-attack-rule`.
  * ITS GARBAGE FLOATED UNTIL 2026-08-06. `vs_env._drop_garbage` wrote tiles
    into row 0 and called `resolve()` to settle them, but `resolve()` runs
    gravity ONLY after a clear. Tiles hung at row 0, and since `spawn_blocked()`
    tests row 0 of columns 3/4, one third of deliveries topped the receiver out
    instantly -- measured 19/60 on healthy boards. FIXED NOW (an
    `_apply_gravity()` call), so this file is no longer a live hazard, but any
    result produced through it BEFORE that date is contaminated.
  * `h2h_vs.py:11` already calls this "the old selfplay.py", and
    `PORTFOLIO_VERDICT.md:186` records that the surviving
    `dr-mario-selfplay-vs-negative` corpus (40 candidates, zero wins) rests
    entirely on `vs_harness.play_match` -- that negative went through the CLEAN
    path and still stands.

REPLACEMENT: `vs_harness.play_match` (ROM-true attack rule; gravity-correct
`drop_garbage` with `while board._apply_gravity(): pass`, stamped in
REQUIRED_MECHANICS). For eval-constant head-to-head use `h2h_vs.py`, which
defaults to `--rule rom`.

Before trusting ANY VS delivery path, run
`holepoker/gravity_gate.py::assert_delivery_settles` against YOUR OWN function
rather than against a module name -- the same defect existed in three modules
under two names, and one lane's fix never reached the others.

--- original docstring follows ---

Self-play tuning of the eval constants against WIN RATE UNDER GARBAGE.

WHY: every optimisation this project has run scored SOLO pills-to-clear. The user's loss
photo shows the AI topping out while AHEAD on viruses (24 vs 32) -- it won the metric it was
tuned for and lost the game. With vs_env.py we can finally score the objective that matters.

WHAT THIS IS NOT: it is not CFR and not "converging to optimal". The capsule sequence is
deterministic from the seed and shared by both players, so VS Dr. Mario is a PERFECT-
INFORMATION zero-sum game -- there are no information sets for regret matching to average
over. This is plain parameter search against a better objective.

DISCIPLINE (earned the hard way today -- two tuned results were retracted):
  * candidates are scored on PAIRED seeds against a FIXED reference (the shipped brain), so
    differences are not seed luck;
  * win/loss is BINARY and therefore high-variance -- a candidate needs many matches before
    a few points of win-rate means anything. n is sized accordingly and stated;
  * the winner is re-scored on a HELD-OUT seed block before anything is believed;
  * constants must stay on the RTL-friendly grid -- an eval we cannot burn is useless.
"""
import sys, os, json, argparse, random, statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed
ROOT="/home/struktured/projects/dr_mario_rl"
for p in (ROOT+"/tmp/champion", ROOT+"/tmp/combo_term", ROOT+"/tmp/pillrng",
          ROOT+"/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path: sys.path.insert(0,p)
from vs_env import play_match

BASE={"vrdy":8,"buried":48,"rdyext":8,"setup":32,"matched":48,"poll":6,
      "maxh":12,"holes":20,"toprisk":90,"spawn":150}
GRID={"vrdy":[4,8,12],"buried":[40,48,56],"rdyext":[4,8,12],"setup":[24,32,40],
      "matched":[40,48,56],"poll":[6,10,16],"maxh":[8,12,16],"holes":[12,20,28],
      "toprisk":[60,90,120],"spawn":[100,150,200]}
_W={}
def _init(cand):
    global _W
    import fast_rtl_x as NEW; NEW.warmup_ship_eh(topk2=8); _W=dict(cand)
def _mk(cand):
    import fast_rtl_x as NEW
    w,fl=NEW.variant("winner")
    for k,r in (("vrdy",NEW.R_VRDY),("buried",NEW.R_BURIED),("rdyext",NEW.R_RDYEXT),
                ("setup",NEW.R_SETUP),("matched",NEW.R_MATCHED),("poll",NEW.R_POLL),
                ("maxh",NEW.R_MAXH),("holes",NEW.R_HOLES),("toprisk",NEW.R_TOPRISK),
                ("spawn",NEW.R_SPAWN)):
        w[r]=float(cand[k])
    return NEW.FastShipD3DeciderEH(w,fl,topk2=8)
def match(args):
    seed,swap=args
    import fast_rtl_x as NEW
    cand=_mk(_W); ship=_mk(BASE)
    f=lambda d: (lambda b,c,n: d.choose(b,c,n))
    a,b=(cand,ship) if not swap else (ship,cand)
    r=play_match(seed, f(a), f(b))
    cand_side = 0 if not swap else 1
    win = 1.0 if r["winner"]==cand_side else (0.0 if r["winner"]>=0 else 0.5)
    # margin is (opponent viruses - player0 viruses); flip when the candidate is player 1
    marg = r["margin"] if cand_side==0 else -r["margin"]
    return win, marg
def winrate(cand,seeds,workers):
    jobs=[(s,sw) for s in seeds for sw in (0,1)]     # both sides, controls P1/P2 asymmetry
    wins=[]; margins=[]
    with ProcessPoolExecutor(max_workers=workers,initializer=_init,initargs=(cand,)) as ex:
        for f in as_completed([ex.submit(match,j) for j in jobs]):
            w,mg = f.result(); wins.append(w); margins.append(mg)
    return sum(wins)/len(wins), st.mean(margins), len(wins)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--seeds",type=int,default=40)
    ap.add_argument("--hold",type=int,default=80); ap.add_argument("--workers",type=int,default=6)
    ap.add_argument("--passes",type=int,default=1)
    a=ap.parse_args()
    tune=list(range(400,400+a.seeds)); hold=list(range(8000,8000+a.hold))
    cur=dict(BASE)
    wr,mg,n=winrate(cur,tune,a.workers)
    print(f"reference (shipped vs itself) = {wr:.1%} winrate, margin {mg:+.2f} over {n} matches"
          f"  [sanity: both ~0]",flush=True)
    best=mg          # OPTIMISE THE MARGIN, not the binary win rate
    for p in range(a.passes):
        for k in GRID:
            for v in GRID[k]:
                if v==cur[k]: continue
                c=dict(cur); c[k]=v
                w2,m2,_=winrate(c,tune,a.workers)
                mark = "  <- better" if m2>best else ""
                print(f"  {k:>8}={v:<4} winrate {w2:.1%}  margin {m2:+.2f}{mark}",flush=True)
                if m2>best: best, cur = m2, c
    print(f"\ntuned {cur}  tuning margin {best:+.2f}",flush=True)
    hw,hm,hn=winrate(cur,hold,a.workers)
    print(f"HELD-OUT ({hn} matches): winrate {hw:.1%}  margin {hm:+.2f}")
    print(f"  => {'REAL' if hm>0.5 and hw>0.53 else 'NOT SEPARATED FROM NOISE'}")
    json.dump({"tuned":cur,"tune_wr":best,"hold_wr":hw},
              open(ROOT+"/tmp/champion/selfplay.json","w"),indent=2)
if __name__=="__main__": main()
