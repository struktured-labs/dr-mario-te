#!/usr/bin/env python3
"""Run an existing firmware gate script with copro_bootstrap installed FIRST (the #127 rule build_fw.py follows).

On main (d730ed31) experiments/reach/gate_reach_search.py and experiments/dist/gate_dist_golden.py import
test_search_d3 before the bootstrap finder exists: test_search_d3 then binds the dr-mario-mods copy of patch_vs_cpu
(its hardcoded HERE path) and setdefault()s its extra opcodes there, while tuck_v3 -- imported after build_copro_d3
installs the finder -- gets this tree's patch_vs_cpu without them: `KeyError: 'SBC_absX'` at the first image build,
with every flag off (pre-existing, not caused by this branch). Installing the finder before anything is imported makes
every module resolve in this tree, exactly as build_fw.py does when it builds the shipped hex.
Usage: run_bootstrapped.py <gate.py> [gate args...]
"""
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "fpga", "copro"))
import copro_bootstrap  # noqa: E402
copro_bootstrap.install(ROOT)
script = os.path.abspath(sys.argv[1])
sys.argv = [script] + sys.argv[2:]
sys.path.insert(0, os.path.dirname(script))
runpy.run_path(script, run_name="__main__")
