import sys, json, importlib
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
E47="/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
sys.path.insert(0,H16); import h16_arm
sys.path.insert(0,CVX); sys.path.insert(1,E47)
for m in ("fast_rtl_x","pressure_rig"): sys.modules.pop(m,None)
FX=importlib.import_module("fast_rtl_x"); PR=importlib.import_module("pressure_rig")
assert FX.__file__.startswith(CVX)
import vs_sim, policies
PR._init(11,0,20)
pa,vb,lo,cnt,step,out=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5]),sys.argv[6]
def mk(name):
    if name=="racer": return (policies.racer(),None)
    if name=="closer": return (policies.closer(),None)
    w,fl=FX.variant(name); return (w,fl)
wB,fB=mk(vb)
with open(out,"w") as fh:
    for i in range(cnt):
        s=lo+i*step
        wA,fA=mk(pa)   # fresh policy per game (internal state)
        r=vs_sim.play_vs(s,11,wA,fA,wB,fB)
        r.update({"seed":s,"A":pa,"B":vb})
        fh.write(json.dumps(r)+"\n"); fh.flush()
