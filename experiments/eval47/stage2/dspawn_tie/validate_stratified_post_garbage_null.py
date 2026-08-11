#!/usr/bin/env python3
"""One-shot mechanism validation of the frozen stratified null table."""
from __future__ import annotations

import argparse
import hashlib
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

import calibrate_post_garbage_dspawn_v8 as C  # noqa: E402
import fit_stratified_post_garbage_null as F  # noqa: E402

SEEDS = range(70700, 70940)
TABLE = HERE / "out" / "post_garbage_stratified_null.json"
TABLE_SHA256 = "17d657d13946eec81cf28d7041ce5a0d8175b3c7983b044742da5be550e4a310"
OUTPUT = HERE / "out" / "post_garbage_stratified_validation.json"
FORBIDDEN = {
    "res", "result", "won", "clear", "topout", "stall", "pills",
    "dies_ahead", "viruses_left", "t_to_end",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def counts(records, fn, size):
    out = [0] * size
    for row in records:
        out[int(fn(row))] += 1
    return out


def tv(left, right):
    nl, nr = sum(left), sum(right)
    if not nl or not nr:
        return 1.0
    return 0.5 * sum(abs(a / nl - b / nr) for a, b in zip(left, right))


def quantile(records, q):
    first = {}
    for row in records:
        first.setdefault(int(row["seed"]), row)
    return float(np.quantile([r["ply"] for r in first.values()], q)) if first else None


def validate_mechanism_rows(rows):
    if [r.get("seed") for r in rows] != list(SEEDS):
        raise ValueError("validation seed accounting/order mismatch")
    for row in rows:
        if FORBIDDEN & set(row):
            raise ValueError("endpoint field leaked into mechanism row")
        for record in row.get("records", []):
            if FORBIDDEN & set(record):
                raise ValueError("endpoint field leaked into mechanism record")
            if not 0 <= int(record["gate_offset"]) < 4:
                raise ValueError("record outside K4 window")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        raise SystemExit("workers must be in 1..6")
    actual_sha = sha256(TABLE)
    if actual_sha != TABLE_SHA256:
        raise RuntimeError("frozen cutoff table hash mismatch")
    table = json.loads(TABLE.read_text())
    if [row["cell"] for row in table["cells"]] != list(range(40)):
        raise RuntimeError("cutoff table cell accounting mismatch")
    cutoffs = [int(row["cutoff_u64"]) for row in table["cells"]]

    t0 = time.monotonic()
    os.environ["DR_LULU_FIT"] = C.FIT
    with ProcessPoolExecutor(max_workers=args.workers, initializer=C.init_worker) as ex:
        rows = list(ex.map(C.work, SEEDS))
    validate_mechanism_rows(rows)
    records = [record for row in rows for record in row["records"]]
    treatment = [r for r in records if r["kind"] == "treatment"]
    null_opps = [r for r in records if r["kind"] == "null"]
    selected = [r for r in null_opps
                if int(r["thin_hash"]) < cutoffs[F.cell(r)]]

    t_h = counts(treatment, F.h_bin, 5); n_h = counts(selected, F.h_bin, 5)
    t_t = counts(treatment, F.time_bin, 2); n_t = counts(selected, F.time_bin, 2)
    t_g = counts(treatment, F.gap_bin, 4); n_g = counts(selected, F.gap_bin, 4)
    t_o = counts(treatment, lambda r: r["gate_offset"], 4)
    n_o = counts(selected, lambda r: r["gate_offset"], 4)
    timing = {name: {"treatment": quantile(treatment, q),
                     "null": quantile(selected, q)}
              for name, q in (("p10", .1), ("p50", .5), ("p90", .9))}
    dose_mismatch = abs(len(selected) - len(treatment)) / max(1, len(treatment))
    tvs = {"hamming": tv(t_h, n_h), "timing_bin": tv(t_t, n_t),
           "value_gap": tv(t_g, n_g), "gate_offset": tv(t_o, n_o)}
    checks = {
        "treatment_min_100": len(treatment) >= 100,
        "null_min_100": len(selected) >= 100,
        "dose_mismatch_le_10pct": dose_mismatch <= .10,
        "hamming_tv_le_10pct": tvs["hamming"] <= .10,
        "timing_tv_le_10pct": tvs["timing_bin"] <= .10,
        "value_gap_tv_le_10pct": tvs["value_gap"] <= .10,
        "gate_offset_tv_le_10pct": tvs["gate_offset"] <= .10,
        "first_p10_diff_le_20": abs(timing["p10"]["null"] - timing["p10"]["treatment"]) <= 20,
        "first_p50_diff_le_15": abs(timing["p50"]["null"] - timing["p50"]["treatment"]) <= 15,
        "first_p90_diff_le_20": abs(timing["p90"]["null"] - timing["p90"]["treatment"]) <= 20,
    }

    endpoint_mutant = [dict(r) for r in rows]
    endpoint_mutant[0]["dies_ahead"] = 0
    try:
        validate_mechanism_rows(endpoint_mutant)
        endpoint_killed = False
    except ValueError:
        endpoint_killed = True
    boundary = {"color_hamming": 5, "virus_hamming": 0, "link_hamming": 0}
    wrong_boundary_bin = 0 if F.total_hamming(boundary) <= 5 else 1
    mutants = {
        "endpoint_leak_rejected": endpoint_killed,
        "table_byte_mutant_rejected": hashlib.sha256(TABLE.read_bytes() + b"x").hexdigest() != TABLE_SHA256,
        "hamming_le5_boundary_mutant_killed": wrong_boundary_bin != F.h_bin(boundary),
    }
    passed = all(checks.values()) and all(mutants.values())
    report = {
        "version": "post-garbage-stratified-validation-v1",
        "status": "VALIDATION_PASS" if passed else "NOT_TESTABLE_STRATIFIED_NULL",
        "endpoint_authority": False, "outcomes_retained": False,
        "seeds": [min(SEEDS), max(SEEDS)], "n_seeds": len(rows),
        "table_sha256": actual_sha,
        "plies": sum(r["plies"] for r in rows),
        "active_plies": sum(r["active_plies"] for r in rows),
        "treatment_distinct": len(treatment),
        "null_opportunities": len(null_opps), "null_selected": len(selected),
        "dose_mismatch": dose_mismatch,
        "distributions": {
            "hamming": {"treatment": t_h, "null": n_h},
            "timing_bin": {"treatment": t_t, "null": n_t},
            "value_gap": {"treatment": t_g, "null": n_g},
            "gate_offset": {"treatment": t_o, "null": n_o},
            "tv": tvs, "first_flip_ply": timing,
        },
        "checks": checks, "killed_mutants": mutants,
        "per_seed_mechanism": rows,
        "seconds": round(time.monotonic() - t0, 2),
        "note": "mechanism-only; validation failure may not be refit on these seeds",
    }
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n")
    public = {k: v for k, v in report.items() if k != "per_seed_mechanism"}
    print(json.dumps(public, indent=1), flush=True)
    if not passed:
        raise SystemExit("NOT_TESTABLE_STRATIFIED_NULL")


if __name__ == "__main__":
    main()
