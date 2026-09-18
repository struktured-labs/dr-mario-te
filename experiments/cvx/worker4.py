import sys, json, importlib
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
E47="/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
sys.path.insert(0,H16); import h16_arm
sys.path.insert(0,CVX); sys.path.insert(1,E47)
for m in ("fast_rtl_x","pressure_rig_time"): sys.modules.pop(m,None)
FX=importlib.import_module("fast_rtl_x"); PR=importlib.import_module("pressure_rig_time")
assert FX.NRW==25 and PR.__file__.startswith(CVX)
import bursty_model as BM
variant,lo,cnt,step,out,level,cap = sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),sys.argv[5],int(sys.argv[6]),int(sys.argv[7])
PR.MAXPILLS=cap
# BURSTY pressure = the owner's own send pattern (film-review fit, 2026-08-04), not the gentle drip.
PR._init(level,0,20,model_kind="bursty",bursty_model_obj=BM.fit_struktured_20260804())
PR._C["trate"]=float(__import__("os").environ.get("TRATE","0"))
import root_search as RS
assert RS.FX is FX
w,fl=FX.variant(variant)
# STALE-JIT GUARD (the run-05 and run-18 hazard): root_search's cached _root_value can silently link
# an OLD _eval_rtl, making every new-variant arm byte-identical to baseline (a clean false null).
# Assert the LEAF ITSELF (same compiled object the search uses) distinguishes this variant from the
# champion-family baseline on a synthetic low-virus board whenever the weights differ at all.
import numpy as _np
_w0,_f0=FX.variant("winholes80")
if list(w)!=list(_w0):
    _rng=_np.random.default_rng(7)
    _diff=False
    for _ in range(600):
        _occ=_rng.random(FX.NCELL)<0.4
        _col=_np.where(_occ,_rng.integers(1,4,FX.NCELL),0).astype(_np.int8)
        _vir=_np.zeros(FX.NCELL,_np.int8)
        _idx=_np.flatnonzero(_occ)
        _nv=5 if _%2==0 else 30   # probe BOTH gate regimes: a >K-gated arm differs only on high-virus boards
        if len(_idx)>=_nv: _vir[_rng.choice(_idx,_nv,replace=False)]=1
        if FX._eval_rtl(_col,_vir,_np.asarray(w,_np.float64),_np.asarray(fl,_np.int32))!=FX._eval_rtl(_col,_vir,_np.asarray(_w0,_np.float64),_np.asarray(_f0,_np.int32)):
            _diff=True; break
    assert _diff, f"variant {variant} is indistinguishable from baseline on 300 probe boards -- stale JIT cache?"
with open(out,"w") as fh:
    for i in range(cnt):
        s=lo+i*step; PR._C["w"],PR._C["fl"]=w,fl; r=PR.play(s)
        fh.write(json.dumps({"v":variant,"seed":s,"cap":cap,"model":"bursty_struktured_20260804","clear":int(r["won"]),"stall":int(r["stall"]),
                             "topout":int(r["topout"]),"pills":int(r["pills"]),"elapsed":r.get("elapsed_s"),"vleft":int(r["viruses_left_at_end"])})+"\n"); fh.flush()
