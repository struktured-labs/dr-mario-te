import numpy as np
from PIL import Image
BANDS={"Lv":(58,120,30,74),"Ls":(250,315,30,74),"Rv":(370,432,30,74),"Rs":(572,636,30,74)}  # l2hud crop coords
def cells(imL,key,thr=110):
    x0,x1,y0,y1=BANDS[key]
    W=imL[y0:y1,x0:x1]; ink=W<thr
    tot=ink.sum()
    if tot<25 or tot>0.7*ink.size: return []
    colink=ink.sum(0); segs=[]; s=None
    for i,v in enumerate(colink):
        if v>0 and s is None: s=i
        elif v==0 and s is not None: segs.append((s,i)); s=None
    if s is not None: segs.append((s,len(colink)))
    out=[]
    for a,b in segs:
        w=b-a
        if w<7: continue
        sub=[(a,b)] if w<=30 else [(a,(a+b)//2),((a+b)//2,b)]
        for aa,bb in sub:
            g=ink[:,aa:bb]; ys=np.where(g.any(1))[0]
            if len(ys)<14: continue
            g=g[ys[0]:ys[-1]+1]
            bits=np.array(Image.fromarray((g*255).astype(np.uint8)).resize((12,16),Image.NEAREST))>127
            out.append(bits)
    return out[:2]
