#!/usr/bin/env python3
"""Fit the frozen 40-cell, label-blind null cutoff table."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import __version__ as scipy_version
from scipy.optimize import Bounds, LinearConstraint, milp

import audit_post_garbage_calibration as A

HERE = Path(__file__).resolve().parent
INPUT = HERE / "out" / "post_garbage_calibration.json"
OUTPUT = HERE / "out" / "post_garbage_stratified_null.json"
NCELL = 40


def total_hamming(row):
    return (int(row["color_hamming"]) + int(row["virus_hamming"])
            + int(row["link_hamming"]))


def h_bin(row):
    value = total_hamming(row)
    return 0 if value <= 4 else 1 if value <= 7 else 2 if value <= 11 else 3 if value <= 19 else 4


def time_bin(row):
    return int(int(row["ply"]) > 70)


def gap_bin(row):
    value = float(row["base_value_gap"])
    return 0 if value <= 10 else 1 if value <= 30 else 2 if value <= 60 else 3


def cell(row):
    return (h_bin(row) * 2 + time_bin(row)) * 4 + gap_bin(row)


def margins(counts):
    return {
        "hamming": [int(sum(counts[(h * 2) * 4:(h * 2 + 2) * 4])) for h in range(5)],
        "timing": [int(sum(counts[i] for i in range(NCELL)
                           if (i // 4) % 2 == t)) for t in range(2)],
        "value_gap": [int(sum(counts[i] for i in range(g, NCELL, 4)))
                      for g in range(4)],
    }


def main():
    doc = json.loads(INPUT.read_text())
    A.validate(doc)
    records = [z for row in doc["per_seed_mechanism"] for z in row["records"]]
    treatment = [r for r in records if r["kind"] == "treatment"]
    null = [r for r in records if r["kind"] == "null"]
    target = np.bincount([cell(r) for r in treatment], minlength=NCELL)
    capacity = np.bincount([cell(r) for r in null], minlength=NCELL)

    # Variables are 40 integer selections followed by 40 continuous absolute
    # deviations from the treatment joint table.
    rows, lower, upper = [], [], []
    for size, extract, target_values in (
        (5, lambda i: i // 8, margins(target)["hamming"]),
        (2, lambda i: (i // 4) % 2, margins(target)["timing"]),
        (4, lambda i: i % 4, margins(target)["value_gap"]),
    ):
        for group in range(size):
            row = np.zeros(2 * NCELL)
            row[:NCELL] = [int(extract(i) == group) for i in range(NCELL)]
            rows.append(row); lower.append(target_values[group]); upper.append(target_values[group])
    for i in range(NCELL):
        row = np.zeros(2 * NCELL); row[i] = 1; row[NCELL + i] = -1
        rows.append(row); lower.append(-np.inf); upper.append(target[i])
        row = np.zeros(2 * NCELL); row[i] = -1; row[NCELL + i] = -1
        rows.append(row); lower.append(-np.inf); upper.append(-target[i])
    result = milp(
        np.r_[np.zeros(NCELL), np.ones(NCELL)],
        integrality=np.r_[np.ones(NCELL), np.zeros(NCELL)],
        bounds=Bounds(np.zeros(2 * NCELL),
                      np.r_[capacity, np.full(NCELL, np.inf)]),
        constraints=LinearConstraint(np.asarray(rows), lower, upper),
    )
    if not result.success:
        raise RuntimeError("stratified null capacity is infeasible: " + result.message)
    selected_counts = np.rint(result.x[:NCELL]).astype(int)
    if np.any(selected_counts < 0) or np.any(selected_counts > capacity):
        raise RuntimeError("solver returned invalid cell capacity")
    if margins(selected_counts) != margins(target):
        raise RuntimeError("fitted marginal counts do not match treatment")

    cells, selected = [], []
    for index in range(NCELL):
        pool = [r for r in null if cell(r) == index]
        hashes = sorted(int(r["thin_hash"]) for r in pool)
        count = int(selected_counts[index])
        cutoff = hashes[count - 1] + 1 if count else 0
        chosen = [r for r in pool if int(r["thin_hash"]) < cutoff]
        if len(chosen) != count:
            raise RuntimeError("cell cutoff did not reproduce fitted count")
        selected.extend(chosen)
        cells.append({
            "cell": index, "hamming_bin": index // 8,
            "timing_bin": (index // 4) % 2, "value_gap_bin": index % 4,
            "target_joint": int(target[index]), "capacity": int(capacity[index]),
            "selected": count, "cutoff_u64": int(cutoff),
        })
    selected_vector = np.bincount([cell(r) for r in selected], minlength=NCELL)
    report = {
        "version": "post-garbage-stratified-null-v1",
        "authority": "FROZEN_BEFORE_SEEDS_70700_70939",
        "training_input": str(INPUT), "training_n": len(doc["per_seed_mechanism"]),
        "treatment_distinct": len(treatment), "null_opportunities": len(null),
        "null_selected": len(selected), "objective_l1": float(result.fun),
        "margins": {"treatment": margins(target),
                    "selected_null": margins(selected_vector)},
        "cells": cells, "scipy": scipy_version,
        "outcome_fields_read": False,
    }
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "cells"}, indent=1))


if __name__ == "__main__":
    main()
