#!/usr/bin/env python3
"""Build the G1 hex battery (build_dbgpub pattern: pinned emitter, asserted paths).
  fixa_base.hex   USE_DELTA=False, DRVETO=1, Fix A      (py65-comparable base)
  m2_delta.hex    USE_DELTA=True,  DRVETO=1, _VETO_AT_OCAND=True  (must be KILLED)
fixa_delta (tmp/drveto/veto2_fixa.hex) and veto1 (tmp/drveto/veto1.hex) already exist."""
import hashlib
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
COPRO = os.path.join(ROOT, "fpga", "copro")
RECIPE_ENV = {"DRSTRAND": "20", "DRCHAIN": "180", "DRCOPRO_ARM": "1", "DRFIX": "1",
              "DRCOPRO_TUCKBFS": "1", "DRCOPRO_TUCKBFS_TIER3": "1",
              "DRCOPRO_TUCKV3_THETA": "400", "DRDBLCANON": "1",
              "DRCOPRO_TUCKV3_FIXSLOT": "1", "DRVETO": "1"}
os.environ.update(RECIPE_ENV)


def build(out, use_delta, m2=False):
    for m in ("test_search_d3", "tuck_v3", "build_copro_d3"):
        sys.modules.pop(m, None)
    if COPRO not in sys.path:
        sys.path.insert(0, COPRO)

    def pin(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod

    D3 = pin("test_search_d3", os.path.join(ROOT, "tests", "test_search_d3.py"))
    TV = pin("tuck_v3", os.path.join(COPRO, "tuck_v3.py"))
    D3.DEBUG_VAL1 = False
    D3.USE_DELTA = use_delta
    D3.DELTA_P0 = D3.DELTA_P2 = D3.DELTA_P3 = None
    if m2:
        D3._VETO_AT_OCAND = True
    # PIN the builder by path too: the emitter's own module-level sys.path
    # inserts (dr-mario-mods first) plus test_vrdy's sibling-worktree insert can
    # put ANOTHER tree's build_copro_d3 ahead of ours on re-import -- measured in
    # this very script: the second build silently bound a builder whose
    # build_image lacks the DRVETO/DRDBLCANON lines and emitted the th400
    # baseline (f78f1e93) while claiming to build the M2 mutant.
    B = pin("build_copro_d3", os.path.join(COPRO, "build_copro_d3.py"))
    print(f"   [debug] builder: {B.__file__}")
    assert B.D3 is D3
    img, clen, slen = B.build_image([0xFF] * 128, 0, 0, 0, 0)
    print(f"   [debug] B.D3 is D3: {B.D3 is D3}  D3.DRVETO={D3.DRVETO} "
          f"D3.DBLCANON={D3.DBLCANON} D3.USE_DELTA={D3.USE_DELTA} "
          f"at_ocand={D3._VETO_AT_OCAND} pub_mut={D3._VETO_PUB_MUTANT} clen={clen}")
    assert B.D3 is D3 and D3.DRVETO == 1
    for i in range(128):
        img[0x0500 + i] = 0xFF
    rom = img[0x8000:0xC000]
    txt = "\n".join("%02x" % x for x in rom) + "\n"
    with open(out, "w") as f:
        f.write(txt)
    print(f"{os.path.basename(out)}: md5={hashlib.md5(txt.encode()).hexdigest()} "
          f"search={clen}B delta={use_delta} m2={m2}")


if __name__ == "__main__":
    build(os.path.join(HERE, "fixa_base.hex"), use_delta=False)
    build(os.path.join(HERE, "m2_delta.hex"), use_delta=True, m2=True)
