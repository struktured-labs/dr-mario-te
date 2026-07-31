#!/usr/bin/env python3
"""Can a CHEAP bounded scan find the tucks that matter, or is the full BFS required?

The executor is built (driver, DRTUCK). The other half is the copro firmware producing
candidates. A full reachability BFS in 6502 is expensive; this tests the cheap alternative
that a bounded scan can find the SAME value.

CHEAP DETECTOR (the candidate firmware design):
  for each EMPTY cell that is COVERED (something above it in its column):
      if putting one of our two capsule colours there completes a >=4 run CONTAINING A VIRUS,
      and the partner half has a legal adjacent cell,
      and some neighbouring column is open all the way down to that row (the approach),
  then emit (approach_col, trigger_row) -- exactly the two bytes the executor consumes.

That is O(128 x small): no queue, no visited set, no path reconstruction. If it retains most
of the full enumerator's measured gain (-7.7% median pills on the real NES stream at L11),
it is the firmware spec. If not, the firmware needs the real BFS and the cost calculus
changes completely.
"""
import sys, argparse, statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed
ROOT="/home/struktured/projects/dr_mario_rl"
for p in (ROOT+"/tmp/tuck", ROOT+"/tmp/endgame", ROOT+"/tmp/combo_term",
          ROOT+"/tmp/pillrng", ROOT+"/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path: sys.path.insert(0,p)
import numpy as np
from fb import FB, COLS
import destroy as D
import tuck_enum as TE
ROWS=16
_C={}
def _init(level,mode,nes): D._init("winner",level,300,4,600,28,8,6); _C.update(level=level,mode=mode,nes=nes)

def completes_virus_run(col, vir, r, c, color):
    """Would colour `color` at (r,c) complete a >=4 run that CONTAINS a virus?"""
    for dr,dc in ((0,1),(1,0)):
        cells=[(r,c)]
        for sgn in (1,-1):
            rr,cc = r+dr*sgn, c+dc*sgn
            while 0<=rr<ROWS and 0<=cc<COLS and col[rr*COLS+cc]==color:
                cells.append((rr,cc)); rr+=dr*sgn; cc+=dc*sgn
        if len(cells)>=4 and any(vir[y*COLS+x] for y,x in cells):
            return True
    return False

def cheap_tucks(fb, pa, pb):
    """Bounded scan -> list of (cells, ca, cb). No BFS."""
    col, vir = fb.col, fb.vir
    out=[]
    for r in range(ROWS):
        for c in range(COLS):
            i=r*COLS+c
            if col[i]!=0: continue
            covered = any(col[rr*COLS+c]!=0 for rr in range(r))
            if not covered: continue                      # a straight drop reaches it
            for ca,cb in ((pa,pb),(pb,pa)):
                if not completes_virus_run(col,vir,r,c,ca): continue
                for dr,dc in ((0,1),(0,-1)):              # partner half, horizontal only
                    r2,c2 = r+dr, c+dc
                    if not (0<=c2<COLS) or col[r2*COLS+c2]!=0: continue
                    # approach column must be open from the top down to this row
                    for ac in (c2, c):
                        if all(col[rr*COLS+ac]==0 for rr in range(0, r+1)):
                            cells=(r,c,r2,c2) if c<c2 else (r2,c2,r,c)
                            cc1,cc2=(ca,cb) if c<c2 else (cb,ca)
                            out.append((cells,cc1,cc2)); break
    return out

def score(fb, cells, ca, cb):
    NEW,w,fl = D._G["NEW"], D._G["w"], D._G["fl"]
    r0,c0,r1,c1=cells
    nb=fb.clone()
    try: nb.place_at(r0,c0,ca,r1,c1,cb)
    except Exception: return None
    n,nv,_=nb.resolve()
    cc=np.frombuffer(bytes(nb.col),dtype=np.uint8).astype(np.int8)
    vv=np.frombuffer(bytes(nb.vir),dtype=np.uint8).astype(np.int8)
    return (w[NEW.R_WVIR]*nv + w[NEW.R_WCELLS]*n + (w[NEW.R_VBONUS] if nv>=2 else 0.0)
            + NEW._leafv_ship(cc,vv,w,fl)), nv

def play(seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT,LINK_RIGHT,LINK_UP,LINK_DOWN
    dec=D._G["dec"]; mode=_C["mode"]
    env=FaithfulDrMarioEnv(level=_C["level"],seed=seed,max_pills=300); env.reset()
    if _C["nes"]:
        from nes_pills import NesPillSource
        NesPillSource(seed=seed).attach(env); env.cur=env._rand_pill(); env.nxt=env._rand_pill()
    fired=0; res="stall"
    while True:
        a=dec.choose(env.board,env.cur,env.nxt)
        if a is None: res="topout"; break
        vc=env.board.virus_count()
        play_tuck=None
        if mode:
            fb=FB.from_board(env.board); pa,pb=env.cur.a,env.cur.b
            base=D.child(fb,int(a)//COLS,int(a)%COLS,pa,pb)
            bv = base[1][1] if base[0] is not None else 0
            best_sd=bv
            for var in range(4):
                for cc in range(COLS):
                    ch=D.child(fb,var,cc,pa,pb)
                    if ch[0] is not None and ch[1][1]>best_sd: best_sd=ch[1][1]
            if mode=="full":
                try: cands=[(p["cells"],*((pa,pb) if not p.get("flip") else (pb,pa)))
                            for p in TE.enumerate(fb,pa,pb,mode="gravity",frames_per_row=12)
                            if p.get("is_tuck")]
                except Exception: cands=[]
            else:
                cands=cheap_tucks(fb,pa,pb)
            best=None
            for cells,ca,cb in cands:
                r=score(fb,cells,ca,cb)
                if r is None: continue
                sc,nv=r
                if nv>best_sd and (best is None or sc>best[0]): best=(sc,cells,ca,cb)
            if best is not None: play_tuck=best
        if play_tuck is not None:
            _,cells,ca,cb=play_tuck; r0,c0,r1,c1=cells; b=env.board
            b.color[r0,c0]=ca; b.color[r1,c1]=cb
            if r0==r1: b.link[r0,c0]=LINK_RIGHT; b.link[r1,c1]=LINK_LEFT
            else:      b.link[r0,c0]=LINK_DOWN;  b.link[r1,c1]=LINK_UP
            b.is_virus[r0,c0]=False; b.is_virus[r1,c1]=False
            b.resolve(); env.pills_placed+=1; env.cur=env.nxt; env.nxt=env._rand_pill(); fired+=1
            if b.virus_count()==0: res="clear"; break
            if b.spawn_blocked(): res="topout"; break
            if env.pills_placed>=300: break
            continue
        _,_,term,trunc,info=env.step(int(a))
        if term: res="clear" if info["won"] else "topout"; break
        if trunc: break
    return {"seed":seed,"won":int(res=="clear"),"pills":env.pills_placed,"fired":fired}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--seeds",type=int,default=150)
    ap.add_argument("--workers",type=int,default=6); ap.add_argument("--level",type=int,default=11)
    a=ap.parse_args()
    print(f"=== CHEAP SCAN vs FULL BFS, REAL NES capsules (L{a.level}, n={a.seeds}) ===")
    print(f"{'arm':>10} {'clear':>8} {'medpills':>9} {'fires/game':>11}")
    for mode,label in ((None,"off"),("cheap","cheap scan"),("full","full BFS")):
        rows=[]
        with ProcessPoolExecutor(max_workers=a.workers,initializer=_init,
                                 initargs=(a.level,mode,1)) as ex:
            for f in as_completed([ex.submit(play,s) for s in range(a.seeds)]): rows.append(f.result())
        print(f"{label:>10} {sum(r['won'] for r in rows)/len(rows):8.1%} "
              f"{st.median([r['pills'] for r in rows]):9.1f} {st.mean([r['fired'] for r in rows]):11.1f}")
if __name__=="__main__": main()
