import sys, numpy as np, importlib
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
sys.path.insert(0,H16); import h16_arm
sys.path.insert(0,CVX); sys.path.insert(0,"/home/struktured/projects/dr-mario-h16-wt/tmp/oldmod")
NEW=importlib.import_module("fast_rtl_x"); OLD=importlib.import_module("fast_rtl_old")
R,C=NEW.ROWS,NEW.COLS; N=R*C
rng=np.random.default_rng(4242)
wn,fn=NEW.variant("winner"); wo,fo=OLD.variant("winner")
wn=np.asarray(wn,np.float64); fn=np.asarray(fn,np.int32)
wo=np.asarray(wo,np.float64); fo=np.asarray(fo,np.int32)
we,fe=NEW.variant("winend4_24"); we=np.asarray(we,np.float64); fe=np.asarray(fe,np.int32)

bad=0; fires_low=0; fires_high=0; n_low=0; n_high=0
for i in range(20000):
    d=rng.uniform(0.05,0.9); occ=rng.random(N)<d
    col=np.where(occ,rng.integers(1,4,N),0).astype(np.int8)
    nv=rng.choice([1,2,3,4,6,12,40])
    vir=np.zeros(N,np.int8)
    idx=np.flatnonzero(occ)
    if len(idx): vir[rng.choice(idx,size=min(nv,len(idx)),replace=False)]=1
    a=NEW._eval_rtl(col,vir,wn,fn); b=OLD._eval_rtl(col,vir,wo,fo)
    if a!=b: bad+=1
    e=NEW._eval_rtl(col,vir,we,fe)
    vc=int(vir.sum())
    if vc<=4: n_low+=1;  fires_low  += (e!=a)
    else:     n_high+=1; fires_high += (e!=a)
print(f"NULL CONTROL   winner NEW vs OLD over 20000 boards: {bad} mismatches  -> {'PASS' if bad==0 else 'FAIL'}")
print(f"POSITIVE CTRL  winend4_24 differs from winner on virus_count<=4 : {fires_low}/{n_low}")
print(f"NEGATIVE CTRL  winend4_24 differs from winner on virus_count >4 : {fires_high}/{n_high}  -> {'PASS' if fires_high==0 else 'FAIL'}")
