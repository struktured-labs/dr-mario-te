#!/usr/bin/env python3
"""Build a copro firmware image to an ARBITRARY output path, with the emitter modules
pinned to THIS worktree.

Two reasons this exists instead of `fpga/copro/dbg_build.py`:

1. dbg_build.py writes fpga/copro/copro_rom.hex IN PLACE -- the file the repo ships.
   Every sweep then needs a save/restore dance, and a crash mid-sweep leaves a debug
   image sitting in the ship slot. build_image() does not write anything; only
   dbg_build's last six lines do, so writing them here removes the hazard entirely.

2. ** `import tuck_v3` inside build_copro_d3.py does NOT resolve to the tree the build
   is running in. ** Measured 2026-08-07: a build launched from dr-mario-cosimfarm-wt
   compiled dr-mario-canonical-wt/fpga/copro/tuck_v3.py. build_copro_d3.py's own
   header documents exactly this trap (a hardcoded sibling-worktree sys.path.insert in
   test_vrdy/test_readiness_ext) and force-registers `test_search_d3` to defeat it --
   but the guard covers that ONE module name, and tuck_v3 is imported later, from the
   already-polluted path. The two copies happened to be byte-identical when this was
   found, so no published result was wrong; had they differed, every theta variant
   would have been built from source nobody was reading. Pin it explicitly and assert.

Usage: build_dbgpub.py <out.hex>   (build knobs come from the environment, as usual)
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))      # worktree root
COPRO = os.path.join(ROOT, "fpga", "copro")


def pin(name, path):
    """Register `name` in sys.modules from `path` before anything else can claim it."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    out = os.path.abspath(sys.argv[1])

    sys.path.insert(0, COPRO)
    D3 = pin("test_search_d3", os.path.join(ROOT, "tests", "test_search_d3.py"))
    TV = pin("tuck_v3", os.path.join(COPRO, "tuck_v3.py"))
    assert hasattr(D3, "USE_DELTA"), f"wrong emitter pinned: {D3.__file__}"

    D3.DEBUG_VAL1 = False                       # matches `dbg_build.py all 0`
    D3.USE_DELTA = True
    D3.DELTA_P0 = D3.DELTA_P2 = D3.DELTA_P3 = None

    import build_copro_d3 as B
    assert B.D3 is D3, f"build_copro_d3 bound a different emitter: {B.D3.__file__}"

    img, clen, slen = B.build_image([0xFF] * 128, 0, 0, 0, 0)
    for i in range(128):
        img[0x0500 + i] = 0xFF
    rom = img[0x8000:0xC000]

    # Re-check AFTER the build: build_copro_d3 imports tuck_v3 lazily, inside the
    # EMIT_* branches, so a mismatch only becomes visible once the branch has run.
    got = sys.modules["tuck_v3"]
    assert got is TV, f"tuck_v3 was rebound mid-build to {got.__file__}"
    assert os.path.samefile(got.__file__, os.path.join(COPRO, "tuck_v3.py")), got.__file__

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write("\n".join("%02x" % x for x in rom) + "\n")
    print(f"wrote {out}  search={clen}B stub={slen}B "
          f"THETA={TV.THETA} DBGPUB={TV.DBGPUB} tuck_v3={got.__file__}")


if __name__ == "__main__":
    main()
