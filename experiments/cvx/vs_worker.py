import sys, json, importlib
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
E47="/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
sys.path.insert(0,H16); import h16_arm
sys.path.insert(0,CVX); sys.path.insert(1,E47)
import fast_rtl_x as FX, pressure_rig as PR, vs_sim
PR._init(11,0,20)
va,vb,lo,cnt,step,out=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5]),sys.argv[6]
wA,fA=FX.variant(va); wB,fB=FX.variant(vb)
with open(out,"w") as fh:
    for i in range(cnt):
        s=lo+i*step
        r=vs_sim.play_vs(s,11,wA,fA,wB,fB)
        r.update({"seed":s,"A":va,"B":vb})
        fh.write(json.dumps(r)+"\n"); fh.flush()
