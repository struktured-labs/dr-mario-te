# Per-frame scan of the DrMC 4-bottle layout (960x540 frames): gameplay flag, 4x occupancy grids,
# 8 VIR digit glyphs + 8 SPD digit glyphs (normalized bitmaps, hashed; labeled later via contact sheet).
import sys, os, glob, json, hashlib, numpy as np
sys.path.insert(0,"/home/struktured/projects/dr-mario-h16-wt/tmp/tourney")
import treader as T
from PIL import Image
D="/home/struktured/projects/dr-mario-h16-wt/tmp/tourney"
G={k:[v/2 for v in g] for k,g in json.load(open(f"{D}/grids4.json")).items()}   # 960-scale
# digit windows at 960 scale (full-res /2): [x0,x1] per box column, y bands for VIR and SPD digits
HUD={"TL":(348,378),"TR":(588,619),"BL":(348,378),"BR":(588,619)}
YB={"TL":(44,62),"TR":(44,62),"BL":(314,332),"BR":(314,332)}      # VIR digit band
YS={"TL":(68,86),"TR":(68,86),"BL":(338,356),"BR":(338,356)}      # SPD digit band
def glyphs(imL, xr, yr):
    W=imL[yr[0]:yr[1], xr[0]:xr[1]]
    ink=W<110
    if ink.sum()<6: return []
    cols=ink.any(0); xs=np.where(cols)[0]
    # split into digit runs by gaps
    runs=[]; s=xs[0]; p=xs[0]
    for x in xs[1:]:
        if x-p<=1: p=x
        else: runs.append((s,p)); s=p=x
    runs.append((s,p))
    out=[]
    for a,b in runs:
        if b-a<2: continue
        g=ink[:,a:b+1]; ys=np.where(g.any(1))[0]
        if len(ys)<5: continue
        g=g[ys[0]:ys[-1]+1]
        im=Image.fromarray((g*255).astype(np.uint8)).resize((10,14),Image.NEAREST)
        bits=(np.array(im)>127)
        out.append((hashlib.md5(bits.tobytes()).hexdigest()[:10], bits))
    return out[:2]
K=int(sys.argv[1]); N=int(sys.argv[2]); out=open(f"{D}/scan4_{K}.jsonl","a")
gl_dir=f"{D}/glyphs"; os.makedirs(gl_dir,exist_ok=True)
done=set()
for l in open(f"{D}/scan4_{K}.jsonl"): done.add(json.loads(l)["f"])
for p in sorted(glob.glob(f"{D}/f1/*.jpg"))[K::N]:
    f=int(os.path.basename(p)[:6])
    if f in done: continue
    try:
        im=np.array(Image.open(p).convert("RGB")).astype(float)
        imL=im.mean(2)
        rec={"f":f,"lum":round(float(imL[20:265,380:580].mean()),1)}
        if rec["lum"]<60:
            km=T.classes(im)
            for tag,g in G.items():
                grid=T.read_grid(km,g)
                occ=grid>0
                h=[int(16-np.argmax(occ[:,c])) if occ[:,c].any() else 0 for c in range(8)]
                vg=glyphs(imL,HUD[tag],YB[tag]); sg=glyphs(imL,HUD[tag],YS[tag])
                for hsh,bits in vg+sg:
                    fn=f"{gl_dir}/{hsh}.npy"
                    if not os.path.exists(fn): np.save(fn,bits)
                rec[tag]={"occ":int(occ.sum()),"h":h,"top3":int(occ[:3].sum()),
                          "vir":[h_[0] for h_ in vg],"spd":[h_[0] for h_ in sg]}
        out.write(json.dumps(rec)+"\n"); out.flush()
    except Exception as e:
        out.write(json.dumps({"f":f,"err":str(e)})+"\n"); out.flush()
