"""TEST-ONLY: build_fw.py with one DRDANGER emitter mutant (env DRDANGER_MUT) -- for the co-sim mutant kills.
Same argv as build_fw.py; never used for a ship build."""
import os, sys
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reach", "build_fw.py")).read()
anchor = 'TV = pin("tuck_v3"'
assert src.count(anchor) == 1
src = src.replace(anchor, 'D3._DANGER_MUT = os.environ.get("DRDANGER_MUT") or None\n' + anchor)
__file__ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reach", "build_fw.py")
exec(compile(src, __file__ + "+mut", "exec"))
print("MUT", D3._DANGER_MUT)
