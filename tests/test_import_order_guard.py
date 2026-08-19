#!/usr/bin/env python3
"""Regression test for the import-order guard in fpga/copro/build_copro_d3.py
(task #17, 2026-08-05).

BUG (found while validating the tuck-bfs-6502 DRCOPRO_TUCKBFS wiring, but pre-existing
and unrelated to it -- reproduced on the git-stashed ORIGINAL build_copro_d3.py before
any of that work): `test_vrdy.py`/`test_readiness_ext.py` each unconditionally
`sys.path.insert(0, ...)` a hardcoded sibling worktree ("dr-mario-mods"), not gated on
"already present". If anything imports them before `import test_search_d3`, that
worktree's copy -- which can be on a different branch and is genuinely stale here (it
is missing the "eh_terms_scan" label test_search_d3.build() emits on THIS tree) --
silently wins Python's module-name resolution instead of this tree's own tests/
test_search_d3.py. No error at the import site; the failure surfaces later, confusingly,
as `KeyError: 'eh_terms_scan'` deep inside build_copro_d3.build_image().

FIX (in build_copro_d3.py, right after its own sys.path setup, before anything else is
imported): force-register the correct test_search_d3 into sys.modules if the slot is
either empty or already holds specifically the known-stale sibling-worktree copy --
the same force-preload dbg_build.py already used for its own (deliberate) override,
moved into the library so every entry point inherits the protection. Verified this does
not change build_copro_d3's OWN output: a git-stash before/after comparison of the
knob-off image hash, and a before/after comparison of dbg_build.py's own "all 0" mode
hash (computed in memory, never writing copro_rom.hex), were both byte-identical.

This test reproduces the ORIGINAL bug's import order in a FRESH subprocess (subprocess
isolation matters: sys.modules state from THIS test process must not leak in) and
asserts build_image() now succeeds and produces the KNOWN-GOOD knob-off hash, not just
"didn't crash". A second scenario covers the broader case (some OTHER code, not
build_copro_d3.py itself, having already imported test_vrdy/test_readiness_ext before
build_copro_d3 is ever imported) that the guard also closes.
"""
import subprocess
import sys

PYTHON = "/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python"
COPRO_DIR = "/home/struktured/projects/dr-mario-canonical-wt/fpga/copro"
KNOWN_GOOD_HASH = "753bfb2397d10b5de078a1c9068433d2"   # knob-off (no DR* flags) baseline

_SCENARIO_1 = """
# Scenario 1: build_copro_d3.py's OWN internal import order (test_vrdy/test_readiness_ext
# before test_search_d3) -- the literal reported bug, entirely inside its own module body.
# build_image() itself calls D3.build() with USE_ENGINE/EH_PLY1 set True -- if the wrong
# (stale) test_search_d3 had loaded, this raises KeyError('eh_terms_scan') exactly as the
# original bug report did; success here IS the proof the right module loaded.
import build_copro_d3 as B
assert "dr-mario-mods/" not in B.D3.__file__, B.D3.__file__
img, clen, slen = B.build_image([0xFF] * 128, 0, 1, 2, 0)
import hashlib
h = hashlib.md5(bytes(img)).hexdigest()
print("HASH:" + h)
print("OK")
"""

_SCENARIO_2 = """
# Scenario 2: some OTHER code imports test_vrdy/test_readiness_ext BEFORE build_copro_d3
# is ever imported (the broader case -- build_copro_d3 didn't cause the pollution itself,
# but must still recover from it).
import sys, os
HERE = "{copro_dir}"
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
ROOT = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests")); sys.path.insert(0, ROOT)
import patch_vs_cpu
patch_vs_cpu.OPS.setdefault("SEI", 0x78)
patch_vs_cpu.OPS.setdefault("TXS", 0x9A)
import test_vrdy, test_readiness_ext
assert "test_search_d3" not in sys.modules, "pollution alone must not register the name"
import build_copro_d3 as B
assert "dr-mario-mods/" not in B.D3.__file__, B.D3.__file__
img, clen, slen = B.build_image([0xFF] * 128, 0, 1, 2, 0)
import hashlib
h = hashlib.md5(bytes(img)).hexdigest()
print("HASH:" + h)
print("OK")
""".format(copro_dir=COPRO_DIR)


def _run(script):
    return subprocess.run([PYTHON, "-c", script], cwd=COPRO_DIR,
                          capture_output=True, text=True, timeout=120)


def test_scenario(name, script):
    r = _run(script)
    ok = r.returncode == 0 and "OK" in r.stdout and f"HASH:{KNOWN_GOOD_HASH}" in r.stdout
    print(f"[{name}] returncode={r.returncode} ok={ok}")
    if not ok:
        print("  stdout:", r.stdout.strip().replace("\n", "\n  "))
        print("  stderr:", r.stderr.strip().replace("\n", "\n  "))
    return ok


def main():
    ok = True
    ok &= test_scenario("scenario1_internal_bad_order", _SCENARIO_1)
    ok &= test_scenario("scenario2_external_pollution_before_import", _SCENARIO_2)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
