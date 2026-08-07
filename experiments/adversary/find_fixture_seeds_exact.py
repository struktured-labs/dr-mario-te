#!/usr/bin/env python3
"""find_fixture_seeds_exact.py -- reusable fixture-seed generator for
fixtures/fx_hb_*.json.

Pulls Hunt B candidate genomes at FULL float precision straight from
validate_result.json's own "candidates" dict -- best_schedules.json's
"genome" field is rounded to 3dp for readability, and a spot check found
that rounding flips the outcome for 1/120 holdout seeds (78 vs. 79 topouts
under `ga_near_spawn_a` on an otherwise-identical 120-seed scan). This
script exists so any fixture built from its output bit-exactly reproduces
what ADVERSARIAL_PRESSURE.md / validate_result.json actually measured,
not a rounded approximation of it.

Scans only the first N holdout seeds (default 20, cheap) to find concrete
per-seed fatal outcomes for the fixture library -- NOT a full holdout
re-run (that's validate_only.py's job, already done, n=120, see
validate_result.json).

Usage: python find_fixture_seeds_exact.py [n_scan=20]
Writes: fixture_seed_scan_exact.json (per-candidate genome + dies_ahead/
topout seed lists + full per-seed rows, in this directory)
"""
from __future__ import annotations

import sys
import os
import json
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import adversary_search as ASX  # noqa: E402

with open(os.path.join(HERE, "validate_result.json")) as f:
    VR = json.load(f)


def genome_from_validate(name):
    g = VR["candidates"][name]
    fire = {(4, 6): g["fire"]["4-6"], (7, 10): g["fire"]["7-10"], (11, 999): g["fire"]["11-999"]}
    size_weights = [g["size_weights"][str(s)] for s in ASX.SIZE_POOL]
    return {"fire": fire, "size_weights": size_weights, "target_mode": g["target_mode"]}


def _genome_jsonable(g):
    """(lo,hi)-tuple keys aren't JSON-serializable -- round-trip through the
    same string-keyed shape adversary_search.genome_to_jsonable /
    fixtures/runner.py's _schedule_from_fixture already use."""
    lo_hi = [(4, 6), (7, 10), (11, 999)]
    return {"fire": {f"{lo}-{hi}": g["fire"][(lo, hi)] for lo, hi in lo_hi},
            "size_weights": dict(zip((str(s) for s in ASX.SIZE_POOL), g["size_weights"])),
            "target_mode": g["target_mode"]}


def _run_one(args):
    seed, g, budget = args
    return ASX.play_seed_adversarial(seed, g, budget, max_pills=300)


def main():
    n_scan = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    holdout = list(range(5_000_000, 5_000_000 + n_scan))
    budget = VR["budget_halves"]
    out = {}
    with ProcessPoolExecutor(max_workers=4, initializer=ASX._worker_init) as ex:
        for name in ("ga_near_spawn_a", "ga_near_spawn_b",
                      "honest_shape_spawn_target", "always_spawn_max"):
            g = genome_from_validate(name)
            rows = list(ex.map(_run_one, [(s, g, budget) for s in holdout], chunksize=2))
            dies_ahead = sorted(r["seed"] for r in rows if r["dies_ahead"])
            topout = sorted(r["seed"] for r in rows if r["result"] == "topout")
            out[name] = {"genome": _genome_jsonable(g), "dies_ahead_seeds": dies_ahead,
                         "topout_seeds": topout, "rows": rows}
            print(name, "dies_ahead:", dies_ahead, "topout:", topout, flush=True)
    with open(os.path.join(HERE, "fixture_seed_scan_exact.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote fixture_seed_scan_exact.json", flush=True)


if __name__ == "__main__":
    main()
