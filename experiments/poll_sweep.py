#!/usr/bin/env python3
"""USER INSIGHT (2026-07-28): "you kind of need to clear the junk ADJACENT to the virus
first, not directly on top."

The RTL already has that term -- `pollution` = differently-coloured NON-virus cells in the
virus's row and column (LeafEval.sv:491) -- but it is weighted -6 against `buried` at -48,
and it was NEVER tuned (coef-opt only moved vrdy/buried/rdy_ext/setup/matched).

Scored on the metric that actually matches the complaint: pills spent per virus cleared in
the ENDGAME (vc<=8), where clean play already costs 4.49 vs 1.28 in the opening.
"""
import sys, os, argparse, statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed
ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (ROOT+"/tmp/combo_term", ROOT+"/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path: sys.path.insert(0, p)
_W = {}
def _init(pw, level):
    global _W
    import fast_rtl_x as NEW
    NEW.warmup_ship_eh(topk2=8); _W = {"pw": pw, "level": level}
def play(seed):
    import fast_rtl_x as NEW
    from drmario.faithful_env import FaithfulDrMarioEnv
    w, fl = NEW.variant("winner")
    w[NEW.R_POLL] = float(_W["pw"])
    dec = NEW.FastShipD3DeciderEH(w, fl, topk2=8)
    env = FaithfulDrMarioEnv(level=_W["level"], seed=seed, max_pills=300); env.reset()
    seg = {"open":[0,0], "mid":[0,0], "end":[0,0]}
    res = "stall"
    while True:
        a = dec.choose(env.board, env.cur, env.nxt)
        if a is None: res="topout"; break
        vc = env.board.virus_count()
        k = "open" if vc>32 else ("mid" if vc>8 else "end")
        _,_,term,trunc,info = env.step(int(a))
        seg[k][0]+=1; seg[k][1]+= vc-env.board.virus_count()
        if term: res = "clear" if info["won"] else "topout"; break
        if trunc: break
    return {"won":int(res=="clear"), "pills":env.pills_placed, "seg":seg}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--seeds",type=int,default=80)
    ap.add_argument("--workers",type=int,default=8); ap.add_argument("--level",type=int,default=11)
    ap.add_argument("--weights",default="6,12,24,36,48")
    ap.add_argument("--seed0",type=int,default=0); a=ap.parse_args()
    seeds=list(range(a.seed0, a.seed0+a.seeds))
    print(f"{'W_POLL':>7} {'clear':>7} {'medpills':>9} {'open p/v':>9} {'mid p/v':>8} {'END p/v':>8}")
    for pw in [int(x) for x in a.weights.split(",")]:
        rows=[]
        with ProcessPoolExecutor(max_workers=a.workers, initializer=_init, initargs=(pw,a.level)) as ex:
            for f in as_completed([ex.submit(play,s) for s in seeds]): rows.append(f.result())
        def ppv(k):
            pil=sum(r["seg"][k][0] for r in rows); vir=sum(r["seg"][k][1] for r in rows)
            return pil/vir if vir else float("nan")
        print(f"{pw:>7} {sum(r['won'] for r in rows)/len(rows):7.1%} "
              f"{st.median([r['pills'] for r in rows]):9.1f} {ppv('open'):9.2f} {ppv('mid'):8.2f} {ppv('end'):8.2f}"
              + ("   <- SHIPPED" if pw==6 else ""))
main()
