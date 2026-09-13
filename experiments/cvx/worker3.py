import sys, json, importlib
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
E47="/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
sys.path.insert(0,H16); import h16_arm
sys.path.insert(0,CVX); sys.path.insert(1,E47)
for m in ("fast_rtl_x","pressure_rig"): sys.modules.pop(m,None)
FX=importlib.import_module("fast_rtl_x"); PR=importlib.import_module("pressure_rig")
assert FX.NRW==21 and PR.__file__.startswith(CVX)
import bursty_model as BM
variant,lo,cnt,step,out,level,cap = sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),sys.argv[5],int(sys.argv[6]),int(sys.argv[7])
PR.MAXPILLS=cap
# BURSTY pressure = the owner's own send pattern (film-review fit, 2026-08-04), not the gentle drip.
PR._init(level,0,20,model_kind="bursty",bursty_model_obj=BM.fit_struktured_20260804())
import root_search as RS
assert RS.FX is FX
w,fl=FX.variant(variant)
with open(out,"w") as fh:
    for i in range(cnt):
        s=lo+i*step; PR._C["w"],PR._C["fl"]=w,fl; r=PR.play(s)
        fh.write(json.dumps({"v":variant,"seed":s,"cap":cap,"model":"bursty_struktured_20260804","clear":int(r["won"]),"stall":int(r["stall"]),
                             "topout":int(r["topout"]),"pills":int(r["pills"]),"vleft":int(r["viruses_left_at_end"])})+"\n"); fh.flush()
