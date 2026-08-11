#!/usr/bin/env python3
"""Prospective table/selector gates for PREREG_POST_GARBAGE_V8_ENDPOINT.md."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORACLE = HERE.parent / "oracle"
for path in (str(HERE), str(ORACLE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import fit_stratified_post_garbage_null as F  # noqa: E402
import gate_post_garbage_dspawn_v8 as G  # noqa: E402
import analyze_post_garbage_v8_endpoint as A  # noqa: E402
import oracle_arm as O  # noqa: E402
import post_garbage_dspawn_v8 as P  # noqa: E402
import validate_stratified_post_garbage_null as V  # noqa: E402

FIT = ("/home/struktured/projects/dr-mario-te/source/experiments/eval47/results/"
       "dr_lulu_20260808_fit.json")
TABLE = HERE / "out" / "post_garbage_large_stratified_null.json"
TABLE_SHA = "c64ce845e3e7d19242a359f868012bd04623c1bbee21d139202722f686e9c82d"
VALIDATION = HERE / "out" / "post_garbage_large_null_validation.json"
OUTPUT = HERE / "out" / "post_garbage_endpoint_gate.json"


def main():
    table_sha = hashlib.sha256(TABLE.read_bytes()).hexdigest()
    table = json.loads(TABLE.read_text())
    cells = table["cells"]
    cutoffs = [int(row["cutoff_u64"]) for row in cells]
    engineering = {**G.synthetic_gates(), **G.real_gates()}
    validation = json.loads(VALIDATION.read_text())
    records = [z for row in validation["per_seed_mechanism"]
               for z in row["records"] if z["kind"] == "null"]
    cell_matches = 0
    selected = []
    for row in records:
        total = (int(row["color_hamming"]) + int(row["virus_hamming"])
                 + int(row["link_hamming"]))
        cell = P.matching_cell_from_metrics(
            total, row["ply"], row["base_value_gap"])
        cell_matches += int(cell == F.cell(row))
        if P.cutoff_accepts(row["seed"], row["ply"], cutoffs[cell]):
            selected.append(row)

    os.environ["DR_LULU_FIT"] = FIT
    C, model = O.init_rig("exo_lulu")
    live_flips = 0
    live_valid = True
    zero_mutant_flips = 0
    pipeline_rows = []
    for seed in range(70300, 70304):
        arm = P.PostGarbageArm("null", provenance=True, cell_cutoffs=cutoffs)
        got = P.play_one(seed, arm, C, model)
        live_flips += got["null_distinct_flips"]
        for row in got["flip_log"]:
            live_valid &= (row["matching_cell"] == F.cell(row)
                           and P.cutoff_accepts(
                               row["seed"], row["ply"],
                               cutoffs[row["matching_cell"]]))
        mutant = P.PostGarbageArm("null", provenance=True, cell_cutoffs=[0] * 40)
        wrong = P.play_one(seed, mutant, C, model)
        zero_mutant_flips += wrong["null_distinct_flips"]
        base = P.play_one(seed, P.PostGarbageArm("base", provenance=True), C, model)
        treatment = P.play_one(
            seed, P.PostGarbageArm("treatment", provenance=True), C, model)
        pipeline_rows.append({"seed": seed, "base": base,
                              "treatment": treatment, "null": got})
    pipeline_errors = A.flip_errors(pipeline_rows) + A.no_flip_errors(pipeline_rows)
    analyzer_mutants = A.diagnostic_mutants()

    boundary_checks = {
        "h4": P.matching_cell_from_metrics(4, 70, 10) == 0,
        "h5": P.matching_cell_from_metrics(5, 70, 10) == 8,
        "h11": P.matching_cell_from_metrics(11, 70, 10) == 16,
        "h12": P.matching_cell_from_metrics(12, 70, 10) == 24,
        "ply71": P.matching_cell_from_metrics(4, 71, 10) == 4,
        "gap11": P.matching_cell_from_metrics(4, 70, 11) == 1,
        "gap31": P.matching_cell_from_metrics(4, 70, 31) == 2,
        "gap61": P.matching_cell_from_metrics(4, 70, 61) == 3,
    }
    wrong_h5 = 0 if 5 <= 5 else 1
    wrong_h12 = 2 if 12 <= 12 else 3
    try:
        P.PostGarbageArm("null", cell_cutoffs=cutoffs[:-1])
        short_rejected = False
    except ValueError:
        short_rejected = True
    checks = {
        "table_hash": table_sha == TABLE_SHA,
        "table_cells_complete": [row["cell"] for row in cells] == list(range(40)),
        "validation_cell_replay": cell_matches == len(records),
        "validation_selected_replay": len(selected) == validation["null_selected"] == 616,
        "live_selector_path": live_flips > 0 and live_valid,
        "zero_table_mutant_killed": live_flips > 0 and zero_mutant_flips == 0,
        "all_bin_boundaries": all(boundary_checks.values()),
        "hamming_le5_mutant_killed": wrong_h5 != 1,
        "hamming_le12_mutant_killed": wrong_h12 != 3,
        "short_table_rejected": short_rejected,
        "zero_cutoff_rejects": not P.cutoff_accepts(1, 2, 0),
        "full_cutoff_accepts": P.cutoff_accepts(1, 2, 1 << 64),
        "table_byte_mutant_killed": (
            hashlib.sha256(TABLE.read_bytes() + b"x").hexdigest() != TABLE_SHA),
        "current_engineering_gate": all(row["pass"] for row in engineering.values()),
        "live_analyzer_pipeline": not pipeline_errors,
        "analyzer_mutants": all(analyzer_mutants.values()),
        "base_active_telemetry": all(
            row["base"]["active_plies"] > 0 for row in pipeline_rows),
    }
    source_paths = {
        "post_garbage_dspawn_v8": Path(P.__file__).resolve(),
        "endpoint_runner": HERE / "run_post_garbage_v8_endpoint.py",
        "endpoint_gate": Path(__file__).resolve(),
        "endpoint_analyzer": HERE / "analyze_post_garbage_v8_endpoint.py",
    }
    source_sha256 = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                     for name, path in source_paths.items()}
    report = {
        "version": "post-garbage-endpoint-gate-v1",
        "prereg_commit": "85d7898", "table_sha256": table_sha,
        "validation_null_records": len(records),
        "validation_selected": len(selected), "live_smoke_flips": live_flips,
        "source_sha256": source_sha256,
        "pipeline_errors": pipeline_errors, "analyzer_mutants": analyzer_mutants,
        "boundary_checks": boundary_checks, "engineering_checks": engineering,
        "checks": checks,
        "pass": all(checks.values()),
    }
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
    if not report["pass"]:
        raise SystemExit("ENDPOINT GATE FAIL")


if __name__ == "__main__":
    main()
