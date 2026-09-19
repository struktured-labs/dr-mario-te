import sys, os, json, importlib
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"; E47="/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
sys.path.insert(0,H16); import h16_arm
sys.path.insert(0,CVX); sys.path.insert(1,E47)
for m in ("fast_rtl_x","pressure_rig_time"): sys.modules.pop(m,None)
FX=importlib.import_module("fast_rtl_x"); PR=importlib.import_module("pressure_rig_time")
from nutmeg_model import NutmegModel
tr,v,lo,cnt,step,out=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5]),sys.argv[6]
PR._init(11,0,20,model_kind="bursty",bursty_model_obj=NutmegModel()); PR._C["trate"]=float(tr)
w,fl=FX.variant(v); PR.MAXPILLS=600
with open(out,"w") as fh:
    for i in range(cnt):
        s=lo+i*step; PR._C["w"],PR._C["fl"]=w,fl; r=PR.play(s)
        fh.write(json.dumps({"tr":tr,"seed":s,"clear":int(r["won"]),"topout":int(r["topout"]),"pills":int(r["pills"])})+"\n"); fh.flush()
