#!/usr/bin/env python3
"""Re-optimise the eval on the ENDGAME CONVERSION objective, including POLLUTION.

The original coef-opt tuned 5 constants {vrdy, buried, rdy_ext, setup, matched} against
pills-to-clear. Two things are now known to be wrong with that:
  1. POLLUTION was never in the set, and a lone sweep says 6 -> 12 is worth -9.4% endgame
     conversion. It is the only term that models junk BLOCKING a virus's completion line.
  2. Pills-to-clear is dominated by the opening/mid, where the brain is already efficient
     (1.28 / 1.79 p/v) -- it barely sees the endgame (4.49 p/v), which is where the user
     actually observes failure ("cleared the trash but gave back a huge edge").

So: coordinate descent over 6 constants, scored on ENDGAME pills-per-virus with a topout
penalty, tuning seeds only, then a HELD-OUT re-score. This project kills tuned constants on
holdout routinely -- see the NES-pill retune -- so the holdout is the verdict, not the sweep.
"""
import sys, os, json, argparse, statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed
ROOT="/home/struktured/projects/dr_mario_rl"
for p in (ROOT+"/tmp/combo_term", ROOT+"/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path: sys.path.insert(0,p)
# ALL 10 tunable eval terms. The original coef-opt touched 5; the endgame re-tune 6.
# maxh/holes/toprisk/spawn have NEVER been tuned by anything -- they are the shipped
# hand-picked values from the first RTL leaf.
KEYS=("vrdy","buried","rdyext","setup","matched","poll","maxh","holes","toprisk","spawn")
BASE={"vrdy":8,"buried":48,"rdyext":8,"setup":32,"matched":48,"poll":6,
      "maxh":12,"holes":20,"toprisk":90,"spawn":150}
GRID={"vrdy":[4,8,12],"buried":[40,48,56,64],"rdyext":[4,8,12,16],
      "setup":[24,32,40],"matched":[40,48,56],"poll":[6,10,12,16,20],
      "maxh":[8,12,16,20],"holes":[12,20,28,36],
      "toprisk":[60,90,120],"spawn":[100,150,200]}
TOPOUT=40.0
_W={}
def _init(wd,level):
    global _W
    import fast_rtl_x as NEW; NEW.warmup_ship_eh(topk2=8); _W=dict(wd); _W["_lv"]=level
def play(seed):
    import fast_rtl_x as NEW
    from drmario.faithful_env import FaithfulDrMarioEnv
    w,fl=NEW.variant("winner")
    w[NEW.R_VRDY]=_W["vrdy"]; w[NEW.R_BURIED]=_W["buried"]; w[NEW.R_RDYEXT]=_W["rdyext"]
    w[NEW.R_SETUP]=_W["setup"]; w[NEW.R_MATCHED]=_W["matched"]; w[NEW.R_POLL]=_W["poll"]
    w[NEW.R_MAXH]=_W["maxh"]; w[NEW.R_HOLES]=_W["holes"]
    w[NEW.R_TOPRISK]=_W["toprisk"]; w[NEW.R_SPAWN]=_W["spawn"]
    dec=NEW.FastShipD3DeciderEH(w,fl,topk2=8)
    env=FaithfulDrMarioEnv(level=_W["_lv"],seed=seed,max_pills=300); env.reset()
    ep=ev=0; res="stall"
    while True:
        a=dec.choose(env.board,env.cur,env.nxt)
        if a is None: res="topout"; break
        vc=env.board.virus_count()
        _,_,term,trunc,info=env.step(int(a))
        if vc<=8: ep+=1; ev+=vc-env.board.virus_count()
        if term: res="clear" if info["won"] else "topout"; break
        if trunc: break
    return (res,ep,ev)
def score(wd,seeds,workers,level):
    out=[]
    with ProcessPoolExecutor(max_workers=workers,initializer=_init,initargs=(wd,level)) as ex:
        for f in as_completed([ex.submit(play,s) for s in seeds]): out.append(f.result())
    P=sum(o[1] for o in out); V=sum(o[2] for o in out)
    fail=sum(1 for o in out if o[0]!="clear")
    ppv=P/V if V else 99.0
    return {"obj":ppv+TOPOUT*fail/len(out),"ppv":ppv,"clear":1-fail/len(out)}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--seeds",type=int,default=80)
    ap.add_argument("--holdout",type=int,default=120); ap.add_argument("--workers",type=int,default=6)
    ap.add_argument("--level",type=int,default=11); ap.add_argument("--passes",type=int,default=2)
    a=ap.parse_args()
    tune=list(range(2000,2000+a.seeds)); hold=list(range(9000,9000+a.holdout))
    cur=dict(BASE); base=score(cur,tune,a.workers,a.level); best=base["obj"]
    print(f"start {cur}\n  obj={base['obj']:.3f} endgame_ppv={base['ppv']:.3f} clear={base['clear']:.1%}",flush=True)
    for p in range(a.passes):
        print(f"\n--- pass {p+1} ---",flush=True)
        for k in KEYS:
            results=[]
            for v in GRID[k]:
                if v==cur[k]: results.append((v,best)); continue
                c=dict(cur); c[k]=v; s=score(c,tune,a.workers,a.level)
                results.append((v,s["obj"]))
                print(f"  {k:>8}={v:<3} obj={s['obj']:.3f} ppv={s['ppv']:.3f} clear={s['clear']:.1%}",flush=True)
            v,o=min(results,key=lambda t:t[1])
            if o<best-1e-9: print(f"  -> {k}: {cur[k]} -> {v}",flush=True); cur[k]=v; best=o
            else: print(f"  -> {k}: keep {cur[k]}",flush=True)
    print(f"\ntuned {cur} obj={best:.3f}",flush=True)
    print("HELD-OUT (the verdict):",flush=True)
    hb=score(BASE,hold,a.workers,a.level); hc=score(cur,hold,a.workers,a.level)
    print(f"  shipped : obj={hb['obj']:.3f} endgame_ppv={hb['ppv']:.3f} clear={hb['clear']:.1%}")
    print(f"  tuned   : obj={hc['obj']:.3f} endgame_ppv={hc['ppv']:.3f} clear={hc['clear']:.1%}")
    print(f"  => {'TUNED WINS' if hc['obj']<hb['obj'] else 'NO IMPROVEMENT - keep shipped'}")
    json.dump({"tuned":cur,"holdout":{"shipped":hb,"tuned":hc}},
              open(ROOT+"/tmp/champion/coefopt10.json","w"),indent=2)
if __name__=="__main__": main()
