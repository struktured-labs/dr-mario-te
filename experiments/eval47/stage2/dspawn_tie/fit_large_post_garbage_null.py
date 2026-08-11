#!/usr/bin/env python3
"""Fit population-rate cutoffs from the frozen 1,200-seed mechanism block."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import __version__ as scipy_version
from scipy.optimize import Bounds, LinearConstraint, milp

import fit_stratified_post_garbage_null as F

HERE = Path(__file__).resolve().parent
INPUT = HERE / "out" / "post_garbage_large_null_training.json"
OUTPUT = HERE / "out" / "post_garbage_large_stratified_null.json"
U64 = 1 << 64


def main():
    doc = json.loads(INPUT.read_text())
    rows = doc["per_seed_mechanism"]
    if [r["seed"] for r in rows] != list(range(71000, 72200)):
        raise RuntimeError("large training seed accounting mismatch")
    records = [z for row in rows for z in row["records"]]
    treatment = [r for r in records if r["kind"] == "treatment"]
    null = [r for r in records if r["kind"] == "null"]
    target = np.bincount([F.cell(r) for r in treatment], minlength=F.NCELL)
    capacity = np.bincount([F.cell(r) for r in null], minlength=F.NCELL)
    target_margins = F.margins(target)

    constraints, lower, upper = [], [], []
    for size, extract, wanted in (
        (5, lambda i: i // 8, target_margins["hamming"]),
        (2, lambda i: (i // 4) % 2, target_margins["timing"]),
        (4, lambda i: i % 4, target_margins["value_gap"]),
    ):
        for group in range(size):
            row = np.zeros(2 * F.NCELL)
            row[:F.NCELL] = [int(extract(i) == group) for i in range(F.NCELL)]
            constraints.append(row); lower.append(wanted[group]); upper.append(wanted[group])
    for i in range(F.NCELL):
        row = np.zeros(2 * F.NCELL); row[i] = 1; row[F.NCELL + i] = -1
        constraints.append(row); lower.append(-np.inf); upper.append(target[i])
        row = np.zeros(2 * F.NCELL); row[i] = -1; row[F.NCELL + i] = -1
        constraints.append(row); lower.append(-np.inf); upper.append(-target[i])
    result = milp(
        np.r_[np.zeros(F.NCELL), np.ones(F.NCELL)],
        integrality=np.r_[np.ones(F.NCELL), np.zeros(F.NCELL)],
        bounds=Bounds(np.zeros(2 * F.NCELL),
                      np.r_[capacity, np.full(F.NCELL, np.inf)]),
        constraints=LinearConstraint(np.asarray(constraints), lower, upper),
    )
    if not result.success:
        raise RuntimeError("large stratified table infeasible: " + result.message)
    selected = np.rint(result.x[:F.NCELL]).astype(int)
    if np.any(selected < 0) or np.any(selected > capacity):
        raise RuntimeError("invalid fitted capacities")
    if F.margins(selected) != target_margins:
        raise RuntimeError("fitted margins differ from treatment")

    cells = []
    for index in range(F.NCELL):
        cap, count = int(capacity[index]), int(selected[index])
        cutoff = round(U64 * count / cap) if cap else 0
        if not 0 <= cutoff <= U64:
            raise RuntimeError("invalid population-rate cutoff")
        cells.append({
            "cell": index, "hamming_bin": index // 8,
            "timing_bin": (index // 4) % 2, "value_gap_bin": index % 4,
            "target_joint": int(target[index]), "capacity": cap,
            "selected": count, "cutoff_u64": int(cutoff),
            "acceptance_rate": count / cap if cap else 0.0,
        })
    report = {
        "version": "post-garbage-large-stratified-null-v2",
        "authority": "FROZEN_BEFORE_SEEDS_72200_72799",
        "cutoff_estimator": "round(2^64 * selected_count / null_capacity)",
        "training_n": len(rows), "treatment_distinct": len(treatment),
        "null_opportunities": len(null), "expected_null_selected": int(sum(selected)),
        "objective_l1": float(result.fun),
        "margins": {"treatment": target_margins,
                    "expected_null": F.margins(selected)},
        "cells": cells, "scipy": scipy_version, "outcome_fields_read": False,
    }
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "cells"}, indent=1))


if __name__ == "__main__":
    main()
