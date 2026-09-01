"""The OTHER direction of the confusion matrix: video-says-champion-death where the poll
said NOT. Sampled from rounds the poll called AMBIGUOUS or TOPOUT_P1 -- without this the
matrix is one-sided by construction, since video was only ever run on poll-flagged deaths."""
import csv, glob, os, random, re
import adjudicate as A, rounds, reloads

rows=[]
for i,f in enumerate(("ab_samples_L20_seg1_TRUNC.csv","ab_samples_L20_TRUNC.csv")):
    if os.path.exists(f):
        for r in csv.DictReader(open(f)):
            r["block"]="s%d_%s"%(i,r["block"]); rows.append(r)
blocks={}
for r in rows:
    blocks.setdefault((r["arm"],r["block"]),[]).append(
        (float(r["t_epoch"]),
         int(r["p1"]) if r["p1"] not in ("","None") else None,
         int(r["p2"]) if r["p2"] not in ("","None") else None,
         float(r["fill_p1"]),float(r["fill_p2"]),
         int(r["throat_p1"]),int(r["throat_p2"]),
         int(r["topcells_p1"]),int(r["topcells_p2"])))
pool=[(a,rec) for (a,b),ser in sorted(blocks.items()) for rec in rounds.transitions(ser)
      if rec["outcome"]!="TOPOUT_P2"]
random.seed(11)
by={}
for a,rec in pool: by.setdefault(a,[]).append(rec)
SAMPLE=15   # per arm
sel=[(a,rec) for a in sorted(by) for rec in random.sample(by[a],min(SAMPLE,len(by[a])))]
print("sampling %d NON-flagged rounds (%d per arm) for the reverse cell\n"%(len(sel),SAMPLE))
res={}
for i,(a,rec) in enumerate(sel):
    d=A.find_death(rec["end"], tag="C%02d"%i)
    v=d.get("verdict","?")
    res.setdefault((a,rec["outcome"]),{}).setdefault(v,0)
    res[(a,rec["outcome"])][v]=res[(a,rec["outcome"])].get(v,0)+1
    print("  C%02d arm=%-8s poll=%-12s -> video=%s"%(i,a,rec["outcome"],v),flush=True)
print("\n== REVERSE CELL: video says TOPOUT_P2 where the poll did NOT ==")
for a in sorted(by):
    miss=sum(c.get("TOPOUT_P2",0) for (arm,o),c in res.items() if arm==a)
    tot=sum(sum(c.values()) for (arm,o),c in res.items() if arm==a)
    print("   %-9s %d of %d sampled non-flagged rounds were actually champion deaths (%.0f%%)"
          %(a,miss,tot,100*miss/tot if tot else 0))
