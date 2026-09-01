import csv, glob, os
import numpy as np
from PIL import Image
import adjudicate as A, eligibility as E, rounds, vid_ocr as V
rows=list(csv.DictReader(open("ab_samples_L20.csv")))
blocks={}
for r in rows:
    blocks.setdefault((r["arm"],r["block"]),[]).append(
        (float(r["t_epoch"]),
         int(r["p1"]) if r["p1"] not in ("","None") else None,
         int(r["p2"]) if r["p2"] not in ("","None") else None,
         float(r["fill_p1"]),float(r["fill_p2"]),
         int(r["throat_p1"]),int(r["throat_p2"]),
         int(r["topcells_p1"]),int(r["topcells_p2"])))
deaths=[(a,rec["end"]) for (a,b),ser in sorted(blocks.items(),key=lambda kv:kv[0][1])
        for rec in rounds.transitions(ser) if rec["outcome"]=="TOPOUT_P2"]
print("checking parent frames for %d poll-indexed champion deaths"%len(deaths),flush=True)
bad=0; n=0
for i,(arm,ep) in enumerate(deaths):
    tag="OC%02d"%i
    d=A.find_death(ep, tag=tag)
    if d.get("verdict")!="TOPOUT_P2": continue
    frames=sorted(glob.glob(os.path.join(os.path.dirname(d["frame"]),tag+"_*.png")))
    hold=frames.index(d["frame"])
    pi,grid,pspan=E.parent_board(frames,hold)
    if grid is None: continue
    ref=max(0,pi-5)
    g0=V.cell_grid(np.array(Image.open(frames[ref]).convert("RGB")).astype(int),"p2",16)
    lost=sum(1 for r in range(16) for c in range(8) if g0[r][c]>0.25 and grid[r][c]<=0.25)
    n+=1; bad += 1 if lost>=10 else 0
    print("  %s parent=idx%-3d (hold-%d)  cells lost vs 0.5s earlier: %-3d%s"%(
        tag,pi,hold-pi,lost,"  <-- INSIDE ANIMATION" if lost>=10 else ""),flush=True)
print("checked %d; parent frames inside the death animation: %d"%(n,bad),flush=True)
