#!/usr/bin/env python3
"""Mechanism-only calibration for the post-garbage K4/wq60 prototype."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ORACLE = HERE.parent / "oracle"
for path in (str(HERE), str(ORACLE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import post_garbage_dspawn_v8 as P  # noqa: E402
import oracle_arm as O  # noqa: E402

FIT = ("/home/struktured/projects/dr-mario-te/source/experiments/eval47/results/"
       "dr_lulu_20260808_fit.json")
SEEDS = range(70400, 70640)
U64_DEN = 1 << 64
_W = {}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runtime_manifest():
    O.init_rig("exo_lulu")
    names = (
        "post_garbage_dspawn_v8", "dspawn_tie_v8", "firmware_v8_policy",
        "oracle_arm", "pressure_rig", "p0_ab", "bursty_model",
        "exogenous_pressure", "cascade_chain_x", "cascade_link_x",
        "cascade_stranded_x", "fast_rtl_x", "fast_sim_x", "nes_pills",
        "drmario.faithful_env", "drmario.faithful_game",
    )
    files = {
        "runner": str(Path(__file__).resolve()), "fit": FIT,
        "contract": str(HERE / "CALIBRATION_CONTRACT_POST_GARBAGE_V8.md"),
    }
    for name in names:
        files[name] = str(Path(importlib.import_module(name).__file__).resolve())
    docs = {name: {"path": path, "sha256": sha256(path)}
            for name, path in files.items()}
    rolled = hashlib.sha256("".join(
        f"{name}:{doc['sha256']}" for name, doc in sorted(docs.items()))
        .encode()).hexdigest()
    return {"rolled": rolled, "files": docs, "python": sys.version.split()[0]}


def init_worker():
    os.environ["DR_LULU_FIT"] = FIT
    C, model = O.init_rig("exo_lulu")
    _W.update(C=C, model=model)


def work(seed):
    arm = P.PostGarbageArm("calibration")
    row = P.play_one(seed, arm, _W["C"], _W["model"])
    # Intentionally return mechanism only. Endpoint and tempo fields are not
    # available to the parent process and therefore cannot steer this design.
    return {
        "seed": int(seed), "plies": int(row["plies"]),
        "active_plies": int(row["active_plies"]),
        "landed_pulses": int(row["landed_pulses"]),
        "landed_cells": int(row["garbage"]),
        "treatment_distinct_flips": int(row["treatment_distinct_flips"]),
        "null_distinct_opportunities": int(row["null_distinct_opportunities"]),
        "alias_normalizations": int(row["alias_normalizations"]),
        "records": row["calibration_log"],
    }


def quantiles(values):
    if not values:
        return None
    q = np.quantile(np.asarray(values, dtype=float), [0.1, 0.25, 0.5, 0.75, 0.9])
    return {name: float(value) for name, value in
            zip(("p10", "p25", "p50", "p75", "p90"), q)}


def distribution(records):
    first = {}
    for row in records:
        first.setdefault(int(row["seed"]), row)
    hamming = [int(r["color_hamming"]) + int(r["virus_hamming"])
               + int(r["link_hamming"]) for r in records]
    return {
        "n": len(records), "n_games": len(first),
        "first_flip_ply": quantiles([r["ply"] for r in first.values()]),
        "first_flip_gate_offset": quantiles(
            [r["gate_offset"] for r in first.values()]),
        "base_value_gap": quantiles([r["base_value_gap"] for r in records]),
        "successor_total_hamming": quantiles(hamming),
        "metadata_differences": sum(not r["metadata_equal"] for r in records),
    }


def require_gate():
    path = HERE / "out" / "post_garbage_gate.json"
    if not path.exists():
        raise RuntimeError("run gate_post_garbage_dspawn_v8.py first")
    gate = json.loads(path.read_text())
    if not gate.get("pass"):
        raise RuntimeError("engineering gate failed")
    return path, sha256(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        raise SystemExit("workers must be in 1..6")
    os.environ["DR_LULU_FIT"] = FIT
    gate_path, gate_sha = require_gate()
    t0 = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers, initializer=init_worker) as ex:
        rows = list(ex.map(work, SEEDS))
    if [r["seed"] for r in rows] != list(SEEDS):
        raise RuntimeError("ordered calibration seed accounting failed")

    records = [record for row in rows for record in row["records"]]
    treatment = [r for r in records if r["kind"] == "treatment"]
    null_opps = [r for r in records if r["kind"] == "null"]
    null_hashes = [int(r["thin_hash"]) for r in null_opps]
    if len(set(null_hashes)) != len(null_hashes):
        status, cutoff, selected = "FAIL_HASH_COLLISION", 0, []
    elif len(treatment) < 100:
        status, cutoff, selected = "NOT_TESTABLE_LOW_DOSE", 0, []
    elif len(null_opps) < len(treatment):
        status, cutoff, selected = "NOT_TESTABLE_NULL_OPPORTUNITY", 0, []
    else:
        cutoff = (sorted(null_hashes)[len(treatment) - 1] + 1
                  if treatment else 0)
        selected = [r for r in null_opps if int(r["thin_hash"]) < cutoff]
        status = "CALIBRATION_PASS" if len(selected) == len(treatment) else "FAIL_DOSE"

    plies = sum(r["plies"] for r in rows)
    active = sum(r["active_plies"] for r in rows)
    report = {
        "version": "post-garbage-dspawn-v8-calibration-v1",
        "status": status, "endpoint_authority": False,
        "outcomes_retained": False,
        "seeds": [min(SEEDS), max(SEEDS)], "n_seeds": len(rows),
        "policy_semantics": "firmware_v8/p2_surrogate",
        "pressure": "exo_lulu", "k": P.K, "wq": P.WQ,
        "hinge": P.HINGE, "plies": plies, "active_plies": active,
        "active_duty": active / max(1, plies),
        "landed_pulses": sum(r["landed_pulses"] for r in rows),
        "landed_cells": sum(r["landed_cells"] for r in rows),
        "alias_normalizations": sum(r["alias_normalizations"] for r in rows),
        "treatment_distinct_flips": len(treatment),
        "null_distinct_opportunities": len(null_opps),
        "null_selected_distinct_flips": len(selected),
        "null_keep_num": int(cutoff), "null_keep_den": U64_DEN,
        "realized_dose_mismatch": (
            abs(len(selected) - len(treatment)) / max(1, len(treatment))),
        "distributions": {
            "treatment": distribution(treatment),
            "null_selected": distribution(selected),
        },
        "gate": {"path": str(gate_path), "sha256": gate_sha},
        "runtime_manifest": runtime_manifest(),
        "per_seed_mechanism": rows,
        "seconds": round(time.monotonic() - t0, 2),
        "note": "mechanism-only; no result/clear/topout/stall/pills/dies-ahead retained",
    }
    path = HERE / "out" / "post_garbage_calibration.json"
    path.write_text(json.dumps(report, indent=1) + "\n")
    public = {k: v for k, v in report.items()
              if k not in ("per_seed_mechanism", "runtime_manifest")}
    print(json.dumps(public, indent=1), flush=True)
    if status != "CALIBRATION_PASS":
        raise SystemExit(status)


if __name__ == "__main__":
    main()
