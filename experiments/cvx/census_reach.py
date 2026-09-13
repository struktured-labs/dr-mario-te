# Reachability census: at endgame positions (<=8 viruses left), is each remaining virus DROP-REACHABLE or OVERHUNG?
import sys, json, importlib, numpy as np
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"; E47="/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
sys.path.insert(0,H16); import h16_arm
sys.path.insert(0,CVX); sys.path.insert(1,E47)
FX=importlib.import_module("fast_rtl_x"); PR=importlib.import_module("pressure_rig_probe")
import bursty_model as BM
variant,lo,cnt,step,out,level=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),sys.argv[5],int(sys.argv[6])
PR.MAXPILLS=600; PR._init(level,0,20,model_kind="bursty",bursty_model_obj=BM.fit_struktured_20260804())
w,fl=FX.variant(variant); R,C=FX.ROWS,FX.COLS
def classify(col,vir):
    occ=(np.asarray(col).reshape(R,C)!=0); v=np.asarray(vir).reshape(R,C).astype(bool)
    out=[]
    for r in range(R):
        for c in range(C):
            if not v[r,c]: continue
            # a cell is "open" if empty and nothing occupied above it in its column (a straight drop can land there)
            def open_(rr,cc): return 0<=cc<C and 0<=rr<R and not occ[rr,cc] and not occ[:rr,cc].any()
            reach = open_(r-1,c) or open_(r,c-1) or open_(r,c+1)     # match from above, or from the side via a clean drop
            out.append(reach)
    return out
with open(out,"w") as fh:
    for i in range(cnt):
        s=lo+i*step; PR._PROBE=[]; PR._C["w"],PR._C["fl"]=w,fl; r=PR.play(s)
        plies=PR._PROBE; n=len(plies); eg=[]
        for k,(col,vir,*_) in enumerate(plies):
            vc=int(sum(vir))
            if 0<vc<=8: eg.append((k,vc,classify(col,vir)))
        if not eg: fh.write(json.dumps({"v":variant,"seed":s,"res":"clear" if r["won"] else ("topout" if r["topout"] else "stall"),"endgame_plies":0})+"\n"); continue
        overh_plies=sum(1 for k,vc,cl in eg if not any(cl))           # plies where EVERY remaining virus is overhung
        anyover=sum(1 for k,vc,cl in eg if not all(cl))
        last=eg[-1]
        fh.write(json.dumps({"v":variant,"seed":s,"res":"clear" if r["won"] else ("topout" if r["topout"] else "stall"),
            "endgame_plies":len(eg),"plies_all_overhung":overh_plies,"plies_any_overhung":anyover,
            "final_vleft":last[1],"final_reachable":int(sum(last[2])),"final_overhung":int(len(last[2])-sum(last[2])),
            "pills_total":int(r["pills"])})+"\n"); fh.flush()
