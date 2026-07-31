#!/usr/bin/env python3
"""Do TUCKS pay -- and do they survive the REAL NES capsule stream?

Availability was measured (778 real L11 positions): 18.1% of positions hold a tuck that
kills a virus NO straight drop can reach, 88.4% of those viruses are geometrically
tuck-only, and the shipped eval prefers the tuck in 80.9% of them. Gravity costs ZERO
placements at real L11 speeds. But availability is not win-rate, and nothing has ever
PLAYED a tuck.

Arm B keeps the shipped depth-3 brain and adds a TUCK OVERRIDE: enumerate the gravity-legal
tuck placements, and if one strictly beats the search's choice on the shipped eval AND
clears at least as many viruses, play it. Same shape as the cascade override, so the same
fire-rate discipline applies.

★ Run on BOTH capsule streams. Uniform draws have now flattered two strategies into
retraction (the eval re-tune, the endgame planner). Tucks are capsule-dependent -- a tuck
exists only if the capsule in hand fits the pocket -- so this is exactly the class of idea
the uniform stream inflates. The NES arm is the one that counts.
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
_C={}
def _init(level,tuck,nes,P):
    import os as _o
    D._init("winner",level,300,4,600,28,8,6)
    # DRTUCK_GATE = minimum virus_count for the override to fire (0 = never gated, the
    # default, byte-identical to every run before this flag existed). Set 8 to suppress
    # tucks in the ENDGAME: paired NES runs show tucks help open+mid at BOTH L11 and L20,
    # but the endgame contribution FLIPS sign with level (L11 38.0->34.7 pills, L20
    # 39.9->43.3). Virus counts per regime are identical in both, so that is a real
    # endgame regression, not a composition shift.
    # DRTUCK_EXEC=1 restricts candidates to tucks the SHIPPED EXECUTOR can actually
    # perform (fall in an approach column, ONE horizontal switch at a trigger row, then
    # fall). The headline -8.51 pills was measured over the FULL gravity-legal tuck space;
    # measured coverage of that space by the executor is 78.4% of boards but only 16.7% of
    # tuck cells (tmp/tuck/exec_reachable.py). Publishing a tuck the executor cannot
    # perform is WORSE than publishing none -- the capsule would steer to the approach
    # column and then fail to reach the target, landing somewhere the search never scored.
    _C.update(level=level,tuck=tuck,nes=nes,P=P,gate=int(_o.environ.get("DRTUCK_GATE","0")),
              execonly=_o.environ.get("DRTUCK_EXEC","0")=="1")

def _exec_reach_cells(fb):
    """Rest cells reachable under the executor's one-switch model (see DRTUCK_EXEC)."""
    from fb import ROWS as _R, COLS as _C2, EMPTY as _E
    occ = lambda r,c: fb.col[r*_C2+c] != _E
    def rest(c, r):
        while r+1 < _R and not occ(r+1, c): r += 1
        return r
    def topdrop(c):
        return None if occ(0,c) else rest(c,0)
    out=set()
    for c in range(_C2):
        sd = topdrop(c); sdd = -1 if sd is None else sd
        for a in (c-1, c+1):
            if not (0 <= a < _C2): continue
            ra = topdrop(a)
            if ra is None or occ(ra, c): continue
            rf = rest(c, ra)
            if rf > sdd: out.add((rf, c))
    return out


def score_placement(fb, cells, ca, cb):
    """Apply a placement (cells in place_at order, colours ca/cb), resolve, score."""
    NEW,w,fl = D._G["NEW"], D._G["w"], D._G["fl"]
    r0,c0,r1,c1 = cells
    nb = fb.clone()
    try: nb.place_at(r0,c0,ca,r1,c1,cb)
    except Exception: return None
    cellsn, nvir, _ = nb.resolve()
    c = np.frombuffer(bytes(nb.col),dtype=np.uint8).astype(np.int8)
    v = np.frombuffer(bytes(nb.vir),dtype=np.uint8).astype(np.int8)
    leaf = NEW._leafv_ship(c,v,w,fl)
    return (w[NEW.R_WVIR]*nvir + w[NEW.R_WCELLS]*cellsn
            + (w[NEW.R_VBONUS] if nvir>=2 else 0.0) + leaf), nvir

def play(seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    dec=D._G["dec"]
    env=FaithfulDrMarioEnv(level=_C["level"],seed=seed,max_pills=300); env.reset()
    if _C["nes"]:
        from nes_pills import NesPillSource
        NesPillSource(seed=seed).attach(env); env.cur=env._rand_pill(); env.nxt=env._rand_pill()
    seg={"open":[0,0],"mid":[0,0],"end":[0,0]}; fired=0; res="stall"
    while True:
        a=dec.choose(env.board,env.cur,env.nxt)
        if a is None: res="topout"; break
        vc=env.board.virus_count()
        tuck_play=None
        if _C["tuck"] and vc > _C.get("gate", 0):
            fb=FB.from_board(env.board); pa,pb=env.cur.a,env.cur.b
            base=D.child(fb,int(a)//COLS,int(a)%COLS,pa,pb)
            if base[0] is not None:
                bs = D.proxy_score(base[0],base[1]); bv = base[1][1]
                try:
                    cands = TE.enumerate(fb, pa, pb, mode="gravity", frames_per_row=_C["P"])
                except Exception:
                    cands = []
                # STRICT criterion. The loose version (any tuck out-scoring the search's
                # move at depth-1) fired ~30x/game and was badly negative -- unsurprising,
                # since it pits a DEPTH-1 tuck score against a DEPTH-3 choice. That tested
                # the override, not tucks.
                # Fire ONLY where the availability study located the value: a tuck that
                # kills MORE viruses than ANY straight drop can on this board (~18% of
                # positions). Expected fire rate ~1-2/game, in the range that has worked.
                best_sd_vir = bv
                for var in range(4):
                    for cc in range(COLS):
                        ch = D.child(fb, var, cc, pa, pb)
                        if ch[0] is not None and ch[1][1] > best_sd_vir:
                            best_sd_vir = ch[1][1]
                best=None
                reach = _exec_reach_cells(fb) if _C.get("execonly") else None
                for p in cands:
                    if not p.get("is_tuck"): continue
                    if reach is not None:
                        # APPROXIMATION, stated plainly: require the placement's DEEPEST
                        # cell (the one that makes it a tuck) to be executor-reachable.
                        # Exact two-cell reachability would also constrain the shallower
                        # cell; this is the permissive direction, so it OVER-states the
                        # executor's reach rather than under-stating it.
                        r0,c0,r1,c1 = p["cells"]
                        deep = (r0,c0) if r0 >= r1 else (r1,c1)
                        if deep not in reach: continue
                    ca,cb = (pa,pb) if not p.get("flip") else (pb,pa)
                    r = score_placement(fb, p["cells"], ca, cb)
                    if r is None: continue
                    sc,nv = r
                    if nv > best_sd_vir and (best is None or sc > best[0]):
                        best=(sc,p,ca,cb)
                if best is not None:
                    tuck_play = best
        k="open" if vc>32 else ("mid" if vc>8 else "end")
        if _C["tuck"] and tuck_play is not None:
            # EXECUTE THE TUCK: env.step() can only express straight drops (orient,col), so
            # write the two cells directly, mirroring FaithfulBoard.place_pill's link/virus
            # bookkeeping, then advance the pill queue exactly as step() would.
            from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
            _,pp,ca,cb = tuck_play
            r0,c0,r1,c1 = pp["cells"]
            b=env.board
            b.color[r0,c0]=ca; b.color[r1,c1]=cb
            if r0==r1: b.link[r0,c0]=LINK_RIGHT; b.link[r1,c1]=LINK_LEFT
            else:      b.link[r0,c0]=LINK_DOWN;  b.link[r1,c1]=LINK_UP
            b.is_virus[r0,c0]=False; b.is_virus[r1,c1]=False
            b.resolve()
            env.pills_placed += 1
            env.cur = env.nxt; env.nxt = env._rand_pill()
            fired += 1
            seg[k][0]+=1; seg[k][1]+= vc-b.virus_count()
            if b.virus_count()==0: res="clear"; break
            if b.spawn_blocked(): res="topout"; break
            if env.pills_placed >= 300: break
            continue
        _,_,term,trunc,info=env.step(int(a))
        seg[k][0]+=1; seg[k][1]+=vc-env.board.virus_count()
        if term: res="clear" if info["won"] else "topout"; break
        if trunc: break
    return {"seed":seed,"won":int(res=="clear"),"pills":env.pills_placed,"fired":fired,"seg":seg}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--seeds",type=int,default=120)
    ap.add_argument("--workers",type=int,default=6); ap.add_argument("--level",type=int,default=11)
    ap.add_argument("--P",type=int,default=12)
    a=ap.parse_args(); R={}
    for nes in (0,1):
        for tuck in (0,1):
            rows=[]
            with ProcessPoolExecutor(max_workers=a.workers,initializer=_init,
                                     initargs=(a.level,tuck,nes,a.P)) as ex:
                for f in as_completed([ex.submit(play,s) for s in range(a.seeds)]): rows.append(f.result())
            R[(nes,tuck)]=sorted(rows,key=lambda r:r["seed"])
    def ppv(rows,k="end"):
        p=sum(r["seg"][k][0] for r in rows); v=sum(r["seg"][k][1] for r in rows)
        return p/v if v else float("nan")
    print(f"=== TUCK OVERRIDE, uniform vs REAL NES capsules (L{a.level}, n={a.seeds}) ===")
    print(f"{'stream':>8} {'tuck':>5} {'clear':>7} {'medpills':>9} {'END p/v':>8} {'fires/game':>11}")
    for (nes,tuck),rows in R.items():
        print(f"{'NES' if nes else 'uniform':>8} {'ON' if tuck else 'off':>5} "
              f"{sum(r['won'] for r in rows)/len(rows):7.1%} "
              f"{st.median([r['pills'] for r in rows]):9.1f} {ppv(rows):8.2f} "
              f"{st.mean([r['fired'] for r in rows]):11.1f}")
    e=lambda n,t: ppv(R[(n,t)])
    print(f"\n  tuck gain, uniform : {e(0,0)-e(0,1):+.2f} p/v")
    print(f"  tuck gain, REAL NES: {e(1,0)-e(1,1):+.2f} p/v")
if __name__=="__main__": main()
