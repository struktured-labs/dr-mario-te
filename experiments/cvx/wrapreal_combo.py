import sys, numpy as np, importlib
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
sys.path.insert(0,H16); import h16_arm
sys.path.insert(0,CVX)
FX=importlib.import_module("fast_rtl_x"); WP=importlib.import_module("wrapprobe")
# STALE PROBE GUARD: wrapprobe is a COPY of fast_rtl_x with only the int16 wrap removed.
# If fast_rtl_x gains a term and the copy is not regenerated, `raw != got` everywhere and
# the probe reports phantom WRAPS.  Compare the two sources with the wrap line normalised.
_a=open(FX.__file__).read().replace("    s = s & 0xFFFF\n    if s >= 0x8000:\n        s -= 0x10000\n    return s","    return s",1)
_b=open(WP.__file__).read().replace("@njit(cache=False)","@njit(cache=True)")
assert _a==_b, "wrapprobe.py is STALE -- regenerate it from fast_rtl_x.py before trusting any wrap count"
assert FX.NRW==WP.NRW, f"NRW mismatch {FX.NRW} vs {WP.NRW}"
PR=importlib.import_module("pressure_rig_probe")
import fast_sim_x as FS
NCELL=FX.NCELL

NGAMES=int(sys.argv[1]) if len(sys.argv)>1 else 12
POLICY=sys.argv[2] if len(sys.argv)>2 else "winner"
arms=["winner","wincombo"]
PR.MAXPILLS=600; PR._init(20,0,20,model_kind="drip")

# capture REAL boards from REAL play under the CHAMPION's own policy
PR._PROBE=[]
w0,fl0=FX.variant(POLICY); PR._C["w"],PR._C["fl"]=w0,fl0
for i in range(NGAMES): PR.play(63000+i*2)
plies=PR._PROBE
print(f"captured {len(plies)} real root boards over {NGAMES} {POLICY} games (L20 drip, cap 600)"+f"")

ccol=np.empty(NCELL,np.int8); cvir=np.empty(NCELL,np.int8)
gcol=np.empty(NCELL,np.int8); gvir=np.empty(NCELL,np.int8)
print(f"{'arm':8s} {'depth':>6} {'boards':>10} {'min raw':>9} {'max raw':>9} {'wrapped':>8} {'headroom':>9}")
for a in arms:
    w,fl=FX.variant(a); w=np.asarray(w,np.float64); fl=np.asarray(fl,np.int32)
    for depth in (0,1,2):
        lo,hi,nw,n=10**9,-10**9,0,0
        for (col,vir,pa,pb,na,nb) in plies:
            if depth==0:
                cand=[(col,vir)]
            else:
                cand=[]
                for var in range(4):
                    for c in range(8):
                        ok,_,_=FS._expand_core(col,vir,var,c,pa,pb,ccol,cvir)
                        if not ok: continue
                        if depth==1: cand.append((ccol.copy(),cvir.copy()))
                        else:
                            for v2 in range(4):
                                for c2 in range(8):
                                    ok2,_,_=FS._expand_core(ccol,cvir,v2,c2,na,nb,gcol,gvir)
                                    if ok2: cand.append((gcol.copy(),gvir.copy()))
            for (cc,vv) in cand:
                raw=WP._eval_rtl(cc,vv,w,fl); got=FX._eval_rtl(cc,vv,w,fl)
                lo=min(lo,raw); hi=max(hi,raw); n+=1
                if raw!=got: nw+=1
        head=min(32767-hi, lo+32768)
        print(f"{a:8s} {depth:6d} {n:10d} {lo:9d} {hi:9d} {nw:8d} {head:9d}  {'OK' if nw==0 else '*** WRAPS ***'}")
