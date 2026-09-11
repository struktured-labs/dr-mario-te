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
R,C=FX.ROWS,FX.COLS; N=R*C
rng=np.random.default_rng(777)
arms=["winner","winsc2","winsc20"]
W={a:(np.asarray(FX.variant(a)[0],np.float64), np.asarray(FX.variant(a)[1],np.int32)) for a in arms}

def climb(w,fl,sign,restarts=120,steps=900):
    best=-10**12
    for _ in range(restarts):
        d=rng.uniform(0.05,0.95)
        occ=rng.random(N)<d
        col=np.where(occ,rng.integers(1,4,N),0).astype(np.int8)
        vir=(occ&(rng.random(N)<rng.uniform(0,0.6))).astype(np.int8)
        cur=sign*WP._eval_rtl(col,vir,w,fl)
        for _ in range(steps):
            i=rng.integers(0,N); oc,ov=col[i],vir[i]
            col[i]=rng.integers(0,4); vir[i]=0 if col[i]==0 else rng.integers(0,2)
            v=sign*WP._eval_rtl(col,vir,w,fl)
            if v>=cur: cur=v
            else: col[i],vir[i]=oc,ov
        best=max(best,cur)
    return sign*best

print("ADVERSARIAL int16-wrap bound: hill-climb on the board, 120 restarts x 900 flips per direction")
print(f"safe signed-int16 range: [-32768, 32767]")
print(f"{'arm':9s} {'adv min':>10} {'adv max':>10} {'headroom':>10}")
for a in arms:
    w,fl=W[a]
    lo=climb(w,fl,-1); hi=climb(w,fl,+1)
    head=min(32767-hi, lo+32768)
    print(f"{a:9s} {lo:10d} {hi:10d} {head:10d}  {'OK' if head>0 else '*** WRAPS ***'}")
