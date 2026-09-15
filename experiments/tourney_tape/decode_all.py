import sys, glob, json, numpy as np
sys.path.insert(0,"/home/struktured/projects/dr-mario-h16-wt/tmp/tourney")
import huddec
from PIL import Image
L=np.load("digit_templates.npy"); D=np.load("digit_labels.npy")
gp=sorted({json.loads(l)["f"] for f in glob.glob("scan4_*.jsonl") for l in open(f) if '"TL"' in l})
files={int(p[-10:-4]):p for p in glob.glob("hud/*.jpg")}
K=int(sys.argv[1]); N=int(sys.argv[2])
out=open(f"vir_{K}.jsonl","w")
for fr in gp[K::N]:
    if fr not in files: continue
    try:
        imL=np.array(Image.open(files[fr]).convert("L")).astype(float)
        rec={"f":fr}
        for k in huddec.BANDS:
            got=""; dm=0
            for bits in huddec.cells(imL,k):
                dist=np.count_nonzero(L!=bits,axis=(1,2))
                i=int(dist.argmin()); dm=max(dm,int(dist[i]))
                got += str(D[i]) if dist[i]<=45 else "?"
            rec[k]={"s":got,"d":dm}
        out.write(json.dumps(rec)+"\n")
    except Exception as e:
        out.write(json.dumps({"f":fr,"err":str(e)})+"\n")
    out.flush()
