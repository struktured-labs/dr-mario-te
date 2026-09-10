#!/usr/bin/env python3
"""CRN-paired A/B: champion 'winner' vs a nonlinear-eval candidate (faithful sim).
Same seed => same virus layout, pill stream AND garbage => properly paired.

⚠ root_search does `import fast_rtl_x as FX` at MODULE level, so shadowing via
sys.path alone leaves it bound to the ORIGINAL eval (the banked
python-from-import-defeats-monkeypatch trap). We rebind every holder explicitly.

Usage: ab.py <variantA> <variantB> <seed_lo> <n> [level] [out.jsonl]"""
import sys, os, json, importlib
H16 = "/home/struktured/projects/dr-mario-h16-wt/experiments/h16"
CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
sys.path.insert(0, H16)
import h16_arm                                   # wires oracle/labels sys.path
sys.path.insert(0, CVX)
sys.modules.pop("fast_rtl_x", None)
FX = importlib.import_module("fast_rtl_x")       # the PATCHED copy
assert FX.NRW == 18 and FX.__file__.startswith(CVX), f"shadow failed: {FX.__file__}"
_rebound = []
for _n, _m in list(sys.modules.items()):
    if _m is None: continue
    _f = getattr(_m, "FX", None)
    if _f is not None and getattr(_f, "__name__", "") == "fast_rtl_x" and _f is not FX:
        _m.FX = FX; _rebound.append(_n)
print("rebound FX in:", _rebound, file=sys.stderr)
import pressure_rig as PR

vA, vB, lo, n = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
level = int(sys.argv[5]) if len(sys.argv) > 5 else 11
outp  = sys.argv[6] if len(sys.argv) > 6 else None
PR._init(level, 0, 20, model_kind="drip")
rows = []
fh = open(outp, "w") if outp else None
for i in range(n):
    seed = lo + i
    rec = {"seed": seed}
    for tag, vname in (("A", vA), ("B", vB)):
        w, fl = FX.variant(vname)
        PR._C["w"], PR._C["fl"] = w, fl
        r = PR.play(seed)
        rec[tag] = {"clear": int(r["won"]), "topout": int(r["topout"]),
                    "stall": int(r["stall"]), "pills": int(r["pills"]),
                    "vleft": int(r["viruses_left_at_end"])}
    rows.append(rec)
    line = json.dumps(rec)
    if fh: fh.write(line + "\n"); fh.flush()
    else: print(line, flush=True)
if fh: fh.close()
cA = sum(r["A"]["clear"] for r in rows); cB = sum(r["B"]["clear"] for r in rows)
diff = sum(1 for r in rows if r["A"] != r["B"])
print(f"SUMMARY n={len(rows)} {vA}_clear={cA} ({100*cA/len(rows):.1f}%) "
      f"{vB}_clear={cB} ({100*cB/len(rows):.1f}%) divergent_games={diff}")
