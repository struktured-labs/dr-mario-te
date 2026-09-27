"""Rebuild the Childproof (veto2fixa) copro firmware with a chosen DRCHAIN, pinned-path pattern from
dr-mario-tempo-wt/experiments/drveto/g1_cosim/build_g1_hexes.py (fixa_delta = USE_DELTA=True)."""
import hashlib, importlib.util, os, sys
ROOT = "/home/struktured/projects/dr-mario-tempo-wt"
COPRO = os.path.join(ROOT, "fpga", "copro")
chain, out = sys.argv[1], sys.argv[2]
os.environ.update({"DRSTRAND": "20", "DRCHAIN": chain, "DRCOPRO_ARM": "1", "DRFIX": "1",
                   "DRCOPRO_TUCKBFS": "1", "DRCOPRO_TUCKBFS_TIER3": "1", "DRCOPRO_TUCKV3_THETA": "400",
                   "DRDBLCANON": "1", "DRCOPRO_TUCKV3_FIXSLOT": "1", "DRVETO": "1"})
for m in ("test_search_d3", "tuck_v3", "build_copro_d3"):
    sys.modules.pop(m, None)
sys.path.insert(0, COPRO)
def pin(name, path):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod; spec.loader.exec_module(mod); return mod
D3 = pin("test_search_d3", os.path.join(ROOT, "tests", "test_search_d3.py"))
TV = pin("tuck_v3", os.path.join(COPRO, "tuck_v3.py"))
D3.DEBUG_VAL1 = False; D3.USE_DELTA = True; D3.DELTA_P0 = D3.DELTA_P2 = D3.DELTA_P3 = None
B = pin("build_copro_d3", os.path.join(COPRO, "build_copro_d3.py"))
img, clen, slen = B.build_image([0xFF] * 128, 0, 0, 0, 0)
assert B.D3 is D3 and D3.DRVETO == 1 and B.__file__.startswith(COPRO), (B.__file__, D3.DRVETO)
for i in range(128): img[0x0500 + i] = 0xFF
txt = "\n".join("%02x" % x for x in img[0x8000:0xC000]) + "\n"
open(out, "w").write(txt)
print(f"DRCHAIN={chain} -> {out} md5={hashlib.md5(txt.encode()).hexdigest()} search={clen}B builder={B.__file__}")
