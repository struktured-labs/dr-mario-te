#!/usr/bin/env python3
"""One-shot N=600 validation of the frozen large-fit population-rate null."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORACLE = HERE.parent / "oracle"
for path in (str(HERE), str(ORACLE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import calibrate_post_garbage_dspawn_v8 as C  # noqa: E402
import fit_stratified_post_garbage_null as F  # noqa: E402
import validate_stratified_post_garbage_null as V  # noqa: E402

SEEDS = range(72200, 72800)
TABLE = HERE / "out" / "post_garbage_large_stratified_null.json"
TABLE_SHA256 = "c64ce845e3e7d19242a359f868012bd04623c1bbee21d139202722f686e9c82d"
OUTPUT = HERE / "out" / "post_garbage_large_null_validation.json"


def validate_rows(rows):
    if [row.get("seed") for row in rows] != list(SEEDS):
        raise ValueError("large validation seed accounting mismatch")
    for row in rows:
        if V.FORBIDDEN & set(row):
            raise ValueError("endpoint field leaked into large validation")
        if any(V.FORBIDDEN & set(record) for record in row.get("records", [])):
            raise ValueError("endpoint field leaked into validation record")


def first_quantile(records, q):
    first = {}
    for row in records:
        first.setdefault(int(row["seed"]), row)
    if not first:
        return None
    import numpy as np
    return float(np.quantile([row["ply"] for row in first.values()], q))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        raise SystemExit("workers must be in 1..6")
    actual_sha = hashlib.sha256(TABLE.read_bytes()).hexdigest()
    if actual_sha != TABLE_SHA256:
        raise RuntimeError("large frozen cutoff table hash mismatch")
    table = json.loads(TABLE.read_text())
    if [row["cell"] for row in table["cells"]] != list(range(40)):
        raise RuntimeError("large cutoff table cell accounting mismatch")
    cutoffs = [int(row["cutoff_u64"]) for row in table["cells"]]

    os.environ["DR_LULU_FIT"] = C.FIT
    t0 = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers, initializer=C.init_worker) as ex:
        rows = list(ex.map(C.work, SEEDS))
    validate_rows(rows)
    records = [z for row in rows for z in row["records"]]
    treatment = [r for r in records if r["kind"] == "treatment"]
    null_opps = [r for r in records if r["kind"] == "null"]
    selected = [r for r in null_opps
                if int(r["thin_hash"]) < cutoffs[F.cell(r)]]

    t_h = V.counts(treatment, F.h_bin, 5); n_h = V.counts(selected, F.h_bin, 5)
    t_t = V.counts(treatment, F.time_bin, 2); n_t = V.counts(selected, F.time_bin, 2)
    t_g = V.counts(treatment, F.gap_bin, 4); n_g = V.counts(selected, F.gap_bin, 4)
    t_o = V.counts(treatment, lambda r: r["gate_offset"], 4)
    n_o = V.counts(selected, lambda r: r["gate_offset"], 4)
    tvs = {"hamming": V.tv(t_h, n_h), "timing_bin": V.tv(t_t, n_t),
           "value_gap": V.tv(t_g, n_g), "gate_offset": V.tv(t_o, n_o)}
    timing = {name: {"treatment": first_quantile(treatment, q),
                     "null": first_quantile(selected, q)}
              for name, q in (("p10", .1), ("p50", .5), ("p90", .9))}
    dose_mismatch = abs(len(selected) - len(treatment)) / max(1, len(treatment))
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
    mutant_hash = hashlib.sha256(TABLE.read_bytes() + b"x").hexdigest()
    boundary = {"color_hamming": 5, "virus_hamming": 0, "link_hamming": 0}
    endpoint_mutant = [dict(row) for row in rows]
    endpoint_mutant[0]["dies_ahead"] = 0
    try:
        validate_rows(endpoint_mutant)
        endpoint_killed = False
    except ValueError:
        endpoint_killed = True
    mutants = {
        "table_byte_mutant_rejected": mutant_hash != TABLE_SHA256,
        "hamming_le5_boundary_mutant_killed": F.h_bin(boundary) == 1,
        "endpoint_field_mutant_rejected": endpoint_killed,
    }
    passed = all(checks.values()) and all(mutants.values())
    report = {
        "version": "post-garbage-large-null-validation-v1",
        "status": "VALIDATION_PASS" if passed else "NOT_TESTABLE_LARGE_NULL",
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
        "note": "mechanism-only; no refit permitted on seeds 72200..72799",
    }
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k != "per_seed_mechanism"}, indent=1), flush=True)
    if not passed:
        raise SystemExit("NOT_TESTABLE_LARGE_NULL")


if __name__ == "__main__":
    main()
