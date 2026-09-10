import sys, json, importlib
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
sys.path.insert(0,H16); import h16_arm
sys.path.insert(0,CVX)
for m in ("fast_rtl_x","pressure_rig"): sys.modules.pop(m,None)
FX=importlib.import_module("fast_rtl_x"); PR=importlib.import_module("pressure_rig")
assert PR.__file__.startswith(CVX)
cap=int(sys.argv[1]); lo=int(sys.argv[2]); cnt=int(sys.argv[3]); out=sys.argv[4]
PR.MAXPILLS=cap
PR._init(20,0,20,model_kind="drip")
w,fl=FX.variant("winner"); PR._C["w"],PR._C["fl"]=w,fl
with open(out,"w") as fh:
    for i in range(cnt):
        s=lo+i*2; r=PR.play(s)
        fh.write(json.dumps({"seed":s,"cap":cap,"clear":int(r["won"]),"stall":int(r["stall"]),
                             "topout":int(r["topout"]),"pills":int(r["pills"]),"vleft":int(r["viruses_left_at_end"])})+"\n"); fh.flush()
