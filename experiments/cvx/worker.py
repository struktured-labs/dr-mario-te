#!/usr/bin/env python3
"""Play one variant over a seed shard; append JSONL. argv: variant lo count step out level"""
import sys, os, json, importlib
H16="/home/struktured/projects/dr-mario-h16-wt/experiments/h16"; CVX="/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
sys.path.insert(0,H16); import h16_arm
sys.path.insert(0,CVX); sys.modules.pop("fast_rtl_x",None)
FX=importlib.import_module("fast_rtl_x")
assert FX.NRW==18 and FX.__file__.startswith(CVX)
import pressure_rig as PR
variant, lo, cnt, step, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
level = int(sys.argv[6]) if len(sys.argv)>6 else 11
PR._init(level,0,20,model_kind="drip")
import root_search as RS
assert RS.FX is FX, "root_search bound to the wrong eval"
w,fl=FX.variant(variant)
with open(out,"w") as fh:
    for i in range(cnt):
        s = lo + i*step
        PR._C["w"], PR._C["fl"] = w, fl
        r = PR.play(s)
        fh.write(json.dumps({"v":variant,"seed":s,"clear":int(r["won"]),
                             "topout":int(r["topout"]),"stall":int(r["stall"]),
                             "pills":int(r["pills"]),"vleft":int(r["viruses_left_at_end"])})+"\n")
        fh.flush()
