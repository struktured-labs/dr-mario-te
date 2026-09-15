import sys, os, glob, json, hashlib, numpy as np
sys.path.insert(0,"/home/struktured/projects/dr-mario-h16-wt/tmp/tourney")
import treader as T, l2dec
from PIL import Image
D="/home/struktured/projects/dr-mario-h16-wt/tmp/tourney"
G={k:[v/2 for v in g] for k,g in json.load(open(f"{D}/grids_L2.json")).items()}
L=np.load(f"{D}/l2_templates.npy"); DIG=np.load(f"{D}/l2_labels.npy")
K=int(sys.argv[1]); N=int(sys.argv[2])
frames=sorted(int(p[-10:-4]) for p in glob.glob(f"{D}/l2hud/*.jpg"))
out=open(f"{D}/l2scan_{K}.jsonl","w")
os.makedirs(f"{D}/nameglyphs",exist_ok=True)
for fr in frames[K::N]:
    try:
        rec={"f":fr}
        p1=f"{D}/f1/{fr:06d}.jpg"
        if os.path.exists(p1):
            im=np.array(Image.open(p1).convert("RGB")).astype(float)
            km=T.classes(im)
            for tag,g in G.items():
                grid=T.read_grid(km,g); occ=grid>0
                h=[int(16-np.argmax(occ[:,c])) if occ[:,c].any() else 0 for c in range(8)]
                rec[tag]={"occ":int(occ.sum()),"h":h,"top3":int(occ[:3].sum())}
        imL=np.array(Image.open(f"{D}/l2hud/{fr:06d}.jpg").convert("L")).astype(float)
        for k in ("Lv","Ls","Rv","Rs"):
            got=""
            for b in l2dec.cells(imL,k):
                d=np.count_nonzero(L!=b,axis=(1,2))
                got+=str(DIG[d.argmin()]) if d.min()<=50 else "?"
            rec[k]=got
        # name plates: downsample halves to a stable hash
        imn=np.array(Image.open(f"{D}/l2name/{fr:06d}.jpg").convert("L"))
        for side,(a,b) in (("nL",(90,600)),("nR",(940,1440))):
            strip=(imn[10:50,a:b]>150).astype(np.uint8)
            sm=np.array(Image.fromarray(strip*255).resize((64,8),Image.NEAREST))>127
            hsh=hashlib.md5(sm.tobytes()).hexdigest()[:10]
            fn=f"{D}/nameglyphs/{hsh}.npy"
            if not os.path.exists(fn): np.save(fn,sm)
            rec[side]=hsh
        out.write(json.dumps(rec)+"\n"); out.flush()
    except Exception as e:
        out.write(json.dumps({"f":fr,"err":str(e)})+"\n"); out.flush()
