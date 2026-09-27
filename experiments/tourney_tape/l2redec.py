import sys, glob, json, numpy as np
sys.path.insert(0,"/home/struktured/projects/dr-mario-h16-wt/tmp/tourney")
import l2dec
from PIL import Image
L=np.load("l2_templates.npy"); D=np.load("l2_labels.npy")
def header_ok(imL):
    lab=imL[30:74,6:58]; box=imL[20:80,6:230]
    return (lab<110).mean()>0.06 and box.mean()>120
K=int(sys.argv[1]); N=int(sys.argv[2])
out=open(f"l2v_{K}.jsonl","w")
for p in sorted(glob.glob("l2hud/*.jpg"))[K::N]:
    fr=int(p[-10:-4])
    imL=np.array(Image.open(p).convert("L")).astype(float)
    if not header_ok(imL):
        out.write(json.dumps({"f":fr,"hdr":0})+"\n"); continue
    rec={"f":fr,"hdr":1}
    for k in ("Lv","Ls","Rv","Rs"):
        got=""
        for b in l2dec.cells(imL,k):
            d=np.count_nonzero(L!=b,axis=(1,2))
            got+=str(D[d.argmin()]) if d.min()<=42 else "?"
        rec[k]=got
    out.write(json.dumps(rec)+"\n")
