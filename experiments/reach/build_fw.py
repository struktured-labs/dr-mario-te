"""Reach-root build (DRREACH arg 3, default 0). Rebuild the Childproof (veto2fixa) copro firmware with a chosen DRCHAIN, pinned-path pattern from
dr-mario-tempo-wt/experiments/drveto/g1_cosim/build_g1_hexes.py (fixa_delta = USE_DELTA=True)."""
import hashlib, importlib.util, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COPRO = os.path.join(ROOT, "fpga", "copro")
chain, out = sys.argv[1], sys.argv[2]
reach = sys.argv[3] if len(sys.argv) > 3 else "0"
reachtap = sys.argv[4] if len(sys.argv) > 4 else "0"
dist = sys.argv[5] if len(sys.argv) > 5 else "0"            # DRDIST (STEER6b dist_target60), default 0 = identical
tuckreach = sys.argv[6] if len(sys.argv) > 6 else "0"       # DRTUCKREACH (tuck extension honours the reach mask, DONE-only publish)
rootord = sys.argv[7] if len(sys.argv) > 7 else "0"         # DRROOTORD (two-pass depth-2 root ordering, same final answer)
tucklive = sys.argv[8] if len(sys.argv) > 8 else "0"        # DRTUCKLIVE (tuck enumerator reads the LIVE board, not stale CUR)
tlat = sys.argv[9] if len(sys.argv) > 9 else "19"           # DRREACH_TLAT: reach-mask answer latency (19 pinned cart, 13 fair)
g0 = sys.argv[10] if len(sys.argv) > 10 else "8"             # DRREACH_G0: reach-mask first gravity frame (8 pinned cart, 3 fair)
os.environ.update({"DRSTRAND": "20", "DRCHAIN": chain, "DRCOPRO_ARM": "1", "DRFIX": "1",
                   "DRCOPRO_TUCKBFS": "1", "DRCOPRO_TUCKBFS_TIER3": "1", "DRCOPRO_TUCKV3_THETA": "400",
                   "DRDBLCANON": "1", "DRCOPRO_TUCKV3_FIXSLOT": "1", "DRVETO": "1", "DRREACH": reach, "DRREACHTAP": reachtap,
                   "DRDIST": dist, "DRTUCKREACH": tuckreach, "DRROOTORD": rootord, "DRTUCKLIVE": tucklive,
                   "DRREACH_TLAT": tlat, "DRREACH_G0": g0})
for m in ("test_search_d3", "tuck_v3", "build_copro_d3"):
    sys.modules.pop(m, None)
sys.path.insert(0, COPRO)
# Make this tree authoritative BEFORE anything is imported (#127). Installing it later (inside
# build_copro_d3) re-imports helpers that test_search_d3 already bound, splitting module state and
# changing the emitted firmware (d7d8293a instead of the shipped 77ec742c). Installed first, the
# build is self-contained and reproduces 77ec742c with zero modules from outside the tree.
import copro_bootstrap
copro_bootstrap.install(ROOT)
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
