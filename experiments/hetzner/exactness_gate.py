#!/usr/bin/env python3
"""exactness_gate.py -- prove a compute node reproduces the champion decide
path BIT-IDENTICALLY before we trust a single number it produces.

The project has been burned by silent divergence (a node that computes
*slightly* different answers is worse than no node: its output pollutes the
census with failures that aren't real and hides ones that are). So the gate
hashes the FULL per-seed record -- result, pills, viruses_left, the entire
move trace, and the fatal board when there is one -- not just the summary
line. Two nodes agree only if every action of every game matches.

Usage:
    exactness_gate.py --out /path/node.json [--seeds 20] [--seed-list ...]

Then diff the two JSONs: the `digest` field is a single hash over all seeds,
so agreement is one string comparison; per-seed hashes localise a mismatch.
"""
from __future__ import annotations

import sys
import os
import json
import hashlib
import argparse
import platform

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
sys.path.insert(0, QA + "/adversary")

import adversary_harness as AH  # noqa: E402


# The gate deliberately spans BOTH halves of the seed space: the local agent
# owns 0..32767 and this node owns 32768..65535, and a divergence that only
# appears in one half (e.g. a wider board reached by a longer game) would slip
# past a gate that sampled only one.
def default_seeds(n):
    lo = [1000 + 37 * i for i in range(n // 2)]           # AH.SELFTEST_SEEDS
    hi = [32768 + 1009 * i for i in range(n - n // 2)]    # this node's half
    return lo + hi


# The source files that actually decide a game. A remote node runs a SNAPSHOT
# of an actively-developed tree, so it drifts the moment someone edits the
# original -- and the drift is invisible in aggregate stats. This is not
# hypothetical: `adversary_harness.py` gained stall-board capture 12 minutes
# after the tree was synced, and the two nodes then produced different records
# for the same seed while every printed field (result, pills, viruses_left,
# n_moves) still matched. Hash the code, compare it alongside the results.
_SRC_ROOT = "/home/struktured/projects"
CODE_FILES = [
    f"{_SRC_ROOT}/dr-mario-qa-wt/experiments/adversary/adversary_harness.py",
    f"{_SRC_ROOT}/dr-mario-qa-wt/experiments/eval47/reach_root.py",
    f"{_SRC_ROOT}/dr-mario-qa-wt/experiments/eval47/terms47.py",
    f"{_SRC_ROOT}/dr-mario-qa-wt/experiments/tuck_v3/root_search.py",
    f"{_SRC_ROOT}/dr_mario_rl/tmp/combo_term/fast_rtl_x.py",
    f"{_SRC_ROOT}/dr_mario_rl/tmp/combo_term/fast_sim_x.py",
    f"{_SRC_ROOT}/dr_mario_rl/tmp/endgame/fb.py",
    f"{_SRC_ROOT}/dr-mario-qa-wt/experiments/nes_pills.py",
    f"{_SRC_ROOT}/dr_mario_rl/.claude/worktrees/faithful-sim/src/drmario/faithful_env.py",
    f"{_SRC_ROOT}/dr_mario_rl/.claude/worktrees/faithful-sim/src/drmario/faithful_game.py",
]


def code_manifest():
    """sha256 per decide-path source file, plus one rolled-up hash."""
    per = {}
    for p in CODE_FILES:
        try:
            with open(p, "rb") as f:
                per[os.path.basename(p)] = hashlib.sha256(f.read()).hexdigest()[:16]
        except OSError:
            per[os.path.basename(p)] = "MISSING"
    rolled = hashlib.sha256(
        "".join(f"{k}:{v}" for k, v in sorted(per.items())).encode()).hexdigest()
    return {"files": per, "rolled": rolled}


def record_hash(r):
    """Canonical hash of one game. Sorted keys + separators so formatting can
    never change the digest; the trace is included in full."""
    payload = {
        "seed": r["seed"],
        "result": r["result"],
        "pills": r["pills"],
        "viruses_left": r["viruses_left"],
        "dies_ahead": r["dies_ahead"],
        "garbage_injected": r["garbage_injected"],
        "trace": [[int(i), int(a)] for i, a in r["trace"]],
        "board": r["first_topout_board"],
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--seed-list", type=int, nargs="*", default=None)
    a = ap.parse_args()

    seeds = a.seed_list if a.seed_list else default_seeds(a.seeds)

    per = []
    for s in seeds:
        r = AH.play_seed(s)
        per.append({"seed": s, "result": r["result"], "pills": r["pills"],
                    "viruses_left": r["viruses_left"], "n_moves": len(r["trace"]),
                    "hash": record_hash(r)})
        print(f"  seed {s:6d}  {r['result']:6s}  pills={r['pills']:3d}  "
              f"vl={r['viruses_left']:2d}  {per[-1]['hash'][:16]}", flush=True)

    digest = hashlib.sha256(
        "".join(p["hash"] for p in per).encode()).hexdigest()

    import numpy, numba, llvmlite
    env = {"node": platform.node(),
           "machine": platform.machine(),
           "python": platform.python_version(),
           "numpy": numpy.__version__,
           "numba": numba.__version__,
           "llvmlite": llvmlite.__version__,
           "cpu": _cpu_model()}

    code = code_manifest()
    out = {"digest": digest, "n_seeds": len(seeds), "seeds": seeds,
           "per_seed": per, "env": env, "code": code}
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nDIGEST {digest}")
    print(f"CODE   {code['rolled']}")
    print(f"ENV    {env}")
    print(f"wrote  {a.out}")


def _cpu_model():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "?"


if __name__ == "__main__":
    main()
