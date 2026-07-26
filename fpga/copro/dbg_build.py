#!/usr/bin/env python3
"""Reproducible delta-firmware builder for the co-sim debug loop.
Force-loads the LOCAL (incr-delta) tests/test_search_d3.py (the delta emitter) over the
hardcoded-HERE main-repo shadow, sets the delta/debug flags, then drives build_copro_d3's
build_image to write copro_rom.hex (EMPTY board; the co-sim host streams the real board).

Usage: dbg_build.py <mode>
  mode in {baseline, p0, p2, p3, all}
"""
import sys, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # incr-delta worktree root

# Pre-load the local delta emitter into sys.modules so build_copro_d3's
# `import test_search_d3` reuses it instead of the main-repo copy.
_spec = importlib.util.spec_from_file_location(
    "test_search_d3", os.path.join(ROOT, "tests", "test_search_d3.py"))
D3 = importlib.util.module_from_spec(_spec)
sys.modules["test_search_d3"] = D3
_spec.loader.exec_module(D3)
assert hasattr(D3, "USE_DELTA"), "loaded wrong test_search_d3 (no USE_DELTA)"
assert D3.__file__.startswith(ROOT), f"wrong emitter: {D3.__file__}"

mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
debug = (sys.argv[2] != "0") if len(sys.argv) > 2 else True

D3.DEBUG_VAL1 = debug
D3.USE_DELTA = False
D3.DELTA_P0 = D3.DELTA_P2 = D3.DELTA_P3 = None
if mode == "baseline":
    pass
elif mode == "p0":
    D3.DELTA_P0, D3.DELTA_P2, D3.DELTA_P3 = True, False, False
elif mode == "p2":
    D3.DELTA_P0, D3.DELTA_P2, D3.DELTA_P3 = False, True, False
elif mode == "p3":
    D3.DELTA_P0, D3.DELTA_P2, D3.DELTA_P3 = False, False, True
elif mode == "all":
    D3.USE_DELTA = True
else:
    raise SystemExit(f"unknown mode {mode}")

import build_copro_d3 as B
assert B.D3 is D3, "build_copro_d3 imported a different test_search_d3"

img, clen, slen = B.build_image([0xFF] * 128, 0, 0, 0, 0)
for i in range(128):
    img[0x0500 + i] = 0xFF
rom = img[0x8000:0xC000]
with open(os.path.join(HERE, "copro_rom.hex"), "w") as f:
    f.write("\n".join("%02x" % x for x in rom) + "\n")
print(f"built mode={mode} debug={debug} search={clen}B stub={slen}B "
      f"USE_DELTA={D3.USE_DELTA} P0={D3.DELTA_P0} P2={D3.DELTA_P2} P3={D3.DELTA_P3} "
      f"DEBUG_VAL1={D3.DEBUG_VAL1} emitter={os.path.relpath(D3.__file__, ROOT)}")
