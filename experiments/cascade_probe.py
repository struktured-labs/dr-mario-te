#!/usr/bin/env python3
"""Does CASCADE-AWARE scoring pick different (better) moves than our cap-1 search?

meatfighter resolves to fixpoint (`while(removeConnections()) dropUnsupported();`) with full
link state. Our shipped search does a targeted CAP-1 resolve -- one round, then stop -- and
the RTL cell encoding (3 bits: vir + color) cannot even represent links, so an orphan fall is
not computable in the leaf.

FB can do both, so we can price the gap offline before anyone touches RTL:
  cap1  = score the child after ONE clear+gravity round
  casc  = score the child after resolving to FIXPOINT (links honoured)
On each real position, take the depth-1 argmax under each scorer and ask how often they
disagree -- and when they do, whether the cascade choice actually clears more.

We closed cascade-resolve as NEGATIVE once, on n=10, which our own sample-size audit flagged
SUSPECT. This is the powered re-open.
"""
import sys, os, argparse, statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed
ROOT="/home/struktured/projects/dr_mario_rl"
for p in (ROOT+"/tmp/endgame", ROOT+"/tmp/combo_term", ROOT+"/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path: sys.path.insert(0,p)
from fb import FB, COLS
import destroy as D

def _init(level): D._init("winner", level, 300, 4, 600, 28, 8, 6)

def score_child(fb, var, c, pa, pb, cascade):
    """Return (score, cells, virus) under cap-1 or full-cascade resolve."""
    import numpy as np
    NEW, w, fl = D._G["NEW"], D._G["w"], D._G["fl"]
    orient = 0 if var < 2 else 1
    pos = fb.resting(orient, c)
    if pos is None: return None
    r0,c0,r1,c1 = pos
    x,y = (pa,pb) if var in (0,2) else (pb,pa)
    nb = fb.clone(); nb.place_at(r0,c0,x,r1,c1,y)
    if cascade:
        cells, nvir, chain = nb.resolve()                 # to FIXPOINT, links honoured
    else:
        mask = nb._find_clears(); cells = sum(mask)
        nvir = nb._apply_clear(mask) if cells else 0
        if cells: nb._apply_gravity()                     # ONE round only = our search
        chain = 1 if cells else 0
    cv = np.frombuffer(bytes(nb.col),dtype=np.uint8).astype(np.int8)
    vv = np.frombuffer(bytes(nb.vir),dtype=np.uint8).astype(np.int8)
    leaf = NEW._leafv_ship(cv, vv, w, fl)
    s = (w[NEW.R_WVIR]*nvir + w[NEW.R_WCELLS]*cells
         + (w[NEW.R_VBONUS] if nvir>=2 else 0.0) + leaf)
    return s, cells, nvir, chain

def argmax(fb, pa, pb, cascade):
    best=None
    for var in range(4):
        for c in range(COLS):
            r = score_child(fb,var,c,pa,pb,cascade)
            if r is None: continue
            if best is None or r[0] > best[0]: best=(r[0],var,c,r[2],r[3])
    return best

def play(seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    dec = D._G["dec"]
    env = FaithfulDrMarioEnv(level=D._G["level"], seed=seed, max_pills=300); env.reset()
    out={"n":0,"dis":0,"casc_more_vir":0,"cap_more_vir":0,"chains":0,
         "n_end":0,"dis_end":0,"casc_more_end":0}
    while True:
        a = dec.choose(env.board, env.cur, env.nxt)
        if a is None: break
        vc = env.board.virus_count()
        fb = FB.from_board(env.board)
        b1 = argmax(fb, env.cur.a, env.cur.b, False)
        b2 = argmax(fb, env.cur.a, env.cur.b, True)
        if b1 and b2:
            out["n"]+=1
            end = vc<=8
            if end: out["n_end"]+=1
            if b2[4] > 1: out["chains"]+=1          # cascade actually chained
            if (b1[1],b1[2]) != (b2[1],b2[2]):
                out["dis"]+=1
                if end: out["dis_end"]+=1
                if b2[3] > b1[3]:
                    out["casc_more_vir"]+=1
                    if end: out["casc_more_end"]+=1
                elif b1[3] > b2[3]: out["cap_more_vir"]+=1
        _,_,term,trunc,_ = env.step(int(a))
        if term or trunc: break
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--seeds",type=int,default=60)
    ap.add_argument("--workers",type=int,default=5); ap.add_argument("--level",type=int,default=11)
    a=ap.parse_args()
    rows=[]
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init, initargs=(a.level,)) as ex:
        for f in as_completed([ex.submit(play,s) for s in range(a.seeds)]): rows.append(f.result())
    T=lambda k: sum(r[k] for r in rows)
    n,ne=T("n"),T("n_end")
    print(f"=== CASCADE vs CAP-1  (L{a.level}, {a.seeds} games, {n} decisions) ===")
    print(f"  positions where a cascade actually CHAINS (>1 round): {T('chains')}/{n} = {T('chains')/n:.1%}")
    print(f"  argmax DISAGREES cap-1 vs cascade                   : {T('dis')}/{n} = {T('dis')/n:.1%}")
    print(f"    ...and cascade choice clears MORE viruses         : {T('casc_more_vir')}")
    print(f"    ...and cap-1   choice clears MORE viruses         : {T('cap_more_vir')}")
    print(f"  ENDGAME (vc<=8): decisions {ne}, disagree {T('dis_end')}"
          f" = {T('dis_end')/ne:.1%}" if ne else "  ENDGAME: none")
    print(f"    ...cascade clears more, endgame only              : {T('casc_more_end')}")
if __name__ == "__main__":
    main()
