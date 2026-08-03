#!/usr/bin/env python3
"""Aggregate pinned gate for tuck v3, stage 2 -- the single command to answer "is stage 2
still green" (the same role `experiments/tuck_regression.py` plays for v1's three
historical defects, kept SEPARATE from that file rather than merged into it: v1's file is
a pinned regression case for three SPECIFIC historical defects in v1's own enumerator
[ref_tuck_scan], calibrated against v1's data structures; folding v3's entirely different
CANDLIST/theta-gate/publish-contract tests into it would dilute its focused purpose and
risk perturbing its own pinned invariants).

Runs every stage-2 module as a subprocess (bare, no pipes, explicit exit codes -- house
rule), in dependency order (cheapest/most-foundational first, so a break surfaces at the
narrowest possible layer rather than only in the full end-to-end integration test),
reports a PASS/FAIL summary line per module, and exits nonzero if any failed.
"""
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

# dependency order: enumerator -> cell-prep/land-place -> orient map -> imm1/value-
# equivalence gates -> full ply-2 duplicate -> full end-to-end integration -> slot
# isolation (runs the integration build again, so last).
MODULES = [
    "test_tuck_scan_v3.py",
    "test_land_place_at.py",
    "test_tuck_cell_prep.py",
    "tuck_orient_map.py",
    "test_tuck_score.py",
    "test_tuck_ply2_score.py",
    "test_tuck_root_extension.py",
    "test_tuck_slot_isolation.py",
]


def main():
    results = []
    for mod in MODULES:
        path = os.path.join(HERE, mod)
        print(f"=== {mod} ===", flush=True)
        proc = subprocess.run([PY, path], cwd=HERE)
        ok = proc.returncode == 0
        results.append((mod, ok, proc.returncode))
        print(flush=True)

    print("=" * 60)
    for mod, ok, code in results:
        print(f"  {'PASS' if ok else f'FAIL(exit={code})'}  {mod}")
    fails = [m for m, ok, _ in results if not ok]
    print("=" * 60)
    if fails:
        print(f"{len(fails)}/{len(results)} FAILED: {', '.join(fails)}")
        return False
    print(f"ALL {len(results)} GREEN")
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
