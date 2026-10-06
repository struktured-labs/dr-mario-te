"""silfid: build fw = 1488e158 recipe (build_fw.py 540 OUT 1 1 1) with ONE change, behind argv[2]:
  'mask' -> tuck_cell_prep masks the capsule colours to the low nibble (AND #$0F), so the tie-break SEED nibbles that
            ride S_CA/S_CB's high nibbles can no longer leak into the tuck extension's placed cells.
  'none' -> unchanged (negative control: must reproduce 1488e158)."""
import hashlib, importlib.util, os, sys
ROOT = "/home/struktured/projects/dr-mario-execfid-wt"
COPRO = os.path.join(ROOT, "fpga", "copro")
out, mode = os.path.abspath(sys.argv[1]), sys.argv[2]
os.environ.update({"DRSTRAND": "20", "DRCHAIN": "540", "DRCOPRO_ARM": "1", "DRFIX": "1",
                   "DRCOPRO_TUCKBFS": "1", "DRCOPRO_TUCKBFS_TIER3": "1", "DRCOPRO_TUCKV3_THETA": "400",
                   "DRDBLCANON": "1", "DRCOPRO_TUCKV3_FIXSLOT": "1", "DRVETO": "1", "DRREACH": "1", "DRREACHTAP": "1",
                   "DRDIST": "1"})
for m in ("test_search_d3", "tuck_v3", "build_copro_d3"):
    sys.modules.pop(m, None)
sys.path.insert(0, COPRO)
os.chdir(ROOT)
import copro_bootstrap
copro_bootstrap.install(ROOT)
def pin(name, path):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod; spec.loader.exec_module(mod); return mod
D3 = pin("test_search_d3", os.path.join(ROOT, "tests", "test_search_d3.py"))
TV = pin("tuck_v3", os.path.join(COPRO, "tuck_v3.py"))
if mode == "mask":
    orig = TV.emit_tuck_cell_prep
    def emit_tuck_cell_prep(a, s_ca, s_cb):
        # identical to tuck_v3.emit_tuck_cell_prep except the two colour loads are masked to the low nibble
        class Wrap:
            def __init__(s, a): s.a = a
            def __getattr__(s, k): return getattr(s.a, k)
            def ins16(s, op, arg):
                s.a.ins16(op, arg)
                if op == "LDA_abs" and arg in (s_ca, s_cb):
                    s.a.ins("AND_imm", 0x0F)
        orig(Wrap(a), s_ca, s_cb)
    TV.emit_tuck_cell_prep = emit_tuck_cell_prep
D3.DEBUG_VAL1 = False; D3.USE_DELTA = True; D3.DELTA_P0 = D3.DELTA_P2 = D3.DELTA_P3 = None
B = pin("build_copro_d3", os.path.join(COPRO, "build_copro_d3.py"))
img, clen, slen = B.build_image([0xFF] * 128, 0, 0, 0, 0)
for i in range(128): img[0x0500 + i] = 0xFF
txt = "\n".join("%02x" % x for x in img[0x8000:0xC000]) + "\n"
open(out, "w").write(txt)
print(f"mode={mode} -> {out} md5={hashlib.md5(txt.encode()).hexdigest()}")
