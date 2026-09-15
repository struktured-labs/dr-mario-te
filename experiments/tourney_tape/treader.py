# Tourney-stream board reader: hue-based (the DrMC stream's palette is far duller than our
# capture chain, so read_bottle's RGB-distance PAL misses ~half the cells).
import numpy as np
ROWS,COLS=16,8
def classes(im):
    r,g,b=im[...,0],im[...,1],im[...,2]
    mx=im.max(2); mn=im.min(2)
    v=mx; s=np.where(mx>0,(mx-mn)/np.maximum(mx,1),0)
    h=np.zeros_like(mx)
    m=(mx==r); h[m]=(60*((g-b)/np.maximum(mx-mn,1))%360)[m]
    m=(mx==g); h[m]=(60*((b-r)/np.maximum(mx-mn,1))+120)[m]
    m=(mx==b); h[m]=(60*((r-g)/np.maximum(mx-mn,1))+240)[m]
    k=np.zeros(mx.shape,np.uint8)
    col=(v>70)&(s>=0.25)
    k[col&((h<22)|(h>325))]=1          # red
    k[col&(h>=28)&(h<80)]=2           # yellow
    k[col&(h>=180)&(h<252)]=3         # blue
    return k
def read_grid(km,grid,occ_frac=0.18,frac=0.32):
    x0,y0,cw,ch=grid
    g=np.zeros((ROWS,COLS),int)
    for r in range(ROWS):
        for c in range(COLS):
            cx,cy=x0+(c+0.5)*cw, y0+(r+0.5)*ch
            hw,hh=cw*frac,ch*frac
            p=km[int(cy-hh):int(cy+hh),int(cx-hw):int(cx+hw)].ravel()
            if p.size==0: continue
            cnt=np.bincount(p,minlength=4)[1:]
            g[r,c]=0 if cnt.max()<occ_frac*p.size else int(cnt.argmax()+1)
    return g
