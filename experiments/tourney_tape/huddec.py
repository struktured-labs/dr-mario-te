import numpy as np
from PIL import Image
BANDS={"TLv":(14,52,88,118),"TLs":(14,52,140,168),"TRv":(96,134,88,118),"TRs":(96,134,140,168),
       "BLv":(14,52,628,658),"BLs":(14,52,680,708),"BRv":(96,134,628,658),"BRs":(96,134,680,708)}
def cells(imL, key):
    x0,x1,y0,y1=BANDS[key]
    W=imL[y0:y1,x0:x1]; ink=W<110
    tot=ink.sum()
    if tot<15 or tot>0.75*ink.size: return []          # empty or blackout band
    colink=ink.sum(0)
    segs=[]; s=None
    for i,v in enumerate(colink):
        if v>0 and s is None: s=i
        elif v==0 and s is not None:
            segs.append((s,i)); s=None
    if s is not None: segs.append((s,len(colink)))
    segs=[(a,b) for a,b in segs if b-a>=5]
    out2=[]
    for a,b in segs:
        if b-a<=20: out2.append((a,b))
        elif b-a<=34: m=(a+b)//2; out2.extend([(a,m),(m,b)])
    segs=out2
    out=[]
    for a,b in segs[:2]:
        g=ink[:,a:b]; ys=np.where(g.any(1))[0]
        if len(ys)<10: continue
        g=g[ys[0]:ys[-1]+1]
        if g.shape[0]<12: continue
        bits=np.array(Image.fromarray((g*255).astype(np.uint8)).resize((12,16),Image.NEAREST))>127
        out.append(bits)
    return out
