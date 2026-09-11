import sys, numpy as np, importlib
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
sys.path.insert(0,H16); import h16_arm
sys.path.insert(0,CVX)
FX=importlib.import_module("fast_rtl_x")          # WITH the int16 wrap (production)
WP=importlib.import_module("wrapprobe")
# STALE PROBE GUARD: wrapprobe is a COPY of fast_rtl_x with only the int16 wrap removed.
# If fast_rtl_x gains a term and the copy is not regenerated, `raw != got` everywhere and
# the probe reports phantom WRAPS.  Compare the two sources with the wrap line normalised.
_a=open(FX.__file__).read().replace("    s = s & 0xFFFF\n    if s >= 0x8000:\n        s -= 0x10000\n    return s","    return s",1)
_b=open(WP.__file__).read().replace("@njit(cache=False)","@njit(cache=True)")
assert _a==_b, "wrapprobe.py is STALE -- regenerate it from fast_rtl_x.py before trusting any wrap count"
assert FX.NRW==WP.NRW, f"NRW mismatch {FX.NRW} vs {WP.NRW}"           # identical, wrap removed
R,C=FX.ROWS,FX.COLS
rng=np.random.default_rng(20260910)
arms=["winner","winsc2","winsc5","winsc10","winsc20"]
W={a:FX.variant(a) for a in arms}
stats={a:[10**9,-10**9,0] for a in arms}          # min, max, n_wrapped
N=40000
for i in range(N):
    dens=rng.uniform(0.02,0.98)                   # sweep empty..near-full boards
    occ=rng.random(R*C)<dens
    col=np.where(occ, rng.integers(1,4,R*C), 0).astype(np.int8)
    vir=(occ & (rng.random(R*C)<rng.uniform(0.0,0.6))).astype(np.int8)
    for a in arms:
        w,fl=W[a]
        w=np.asarray(w,dtype=np.float64); fl=np.asarray(fl,dtype=np.int32)
        raw=WP._eval_rtl(col,vir,w,fl)
        got=FX._eval_rtl(col,vir,w,fl)
        st=stats[a]
        st[0]=min(st[0],raw); st[1]=max(st[1],raw)
        if raw!=got: st[2]+=1
print(f"int16-wrap probe: {N} random boards x {len(arms)} arms, densities 0.02-0.98")
print(f"safe signed-int16 range: [-32768, 32767]")
print(f"{'arm':9s} {'min raw':>10} {'max raw':>10} {'wrapped':>9} {'headroom':>10}")
for a in arms:
    lo,hi,nw=stats[a]
    head=min(32767-hi, lo+32768)
    print(f"{a:9s} {lo:10d} {hi:10d} {nw:9d} {head:10d}  {'OK' if nw==0 else '*** WRAPS ***'}")
