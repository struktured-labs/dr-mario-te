import sys, json, importlib, numpy as np
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"; E47="/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
sys.path.insert(0,H16); import h16_arm
sys.path.insert(0,CVX); sys.path.insert(1,E47)
FX=importlib.import_module("fast_rtl_x"); PR=importlib.import_module("pressure_rig_probe")
import bursty_model as BM
variant,lo,cnt,out=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4]
PR.MAXPILLS=600; PR._init(11,0,20,model_kind="bursty",bursty_model_obj=BM.fit_struktured_20260804())
w,fl=FX.variant(variant); R,C=FX.ROWS,FX.COLS
with open(out,"w") as fh:
    for i in range(cnt):
        s=lo+i*2; PR._PROBE=[]; PR._C["w"],PR._C["fl"]=w,fl; r=PR.play(s)
        rec=[]
        for col,vir,*_ in PR._PROBE:
            occ=(np.asarray(col).reshape(R,C)!=0)
            h=[int(16-np.argmax(occ[:,c])) if occ[:,c].any() else 0 for c in range(C)]
            v=np.asarray(vir).reshape(R,C).astype(bool)
            rec.append({"h":h,"occ":int(occ.sum()),"vir":int(v.sum())})
        fh.write(json.dumps({"seed":s,"res":"clear" if r["won"] else ("topout" if r["topout"] else "stall"),"plies":rec})+"\n"); fh.flush()
