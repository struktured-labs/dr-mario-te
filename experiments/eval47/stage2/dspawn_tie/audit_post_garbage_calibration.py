#!/usr/bin/env python3
"""Fail-closed integrity audit for mechanism-only post-garbage calibration."""
from __future__ import annotations

import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE / "out" / "post_garbage_calibration.json"
OUTPUT = HERE / "out" / "post_garbage_calibration_audit.json"

ROW_FIELDS = {
    "seed", "plies", "active_plies", "landed_pulses", "landed_cells",
    "treatment_distinct_flips", "null_distinct_opportunities",
    "alias_normalizations", "records",
}
RECORD_FIELDS = {
    "seed", "ply", "gate_offset", "kind", "base_action", "chosen_action",
    "base_raw_value", "chosen_raw_value", "base_value_gap", "base_sensor",
    "chosen_sensor", "color_hamming", "virus_hamming", "link_hamming",
    "metadata_equal", "thin_hash",
}
FORBIDDEN = {
    "res", "result", "won", "clear", "topout", "stall", "pills",
    "dies_ahead", "viruses_left", "t_to_end",
}


def validate(doc):
    if doc.get("endpoint_authority") is not False:
        raise ValueError("endpoint authority must be false")
    if doc.get("outcomes_retained") is not False:
        raise ValueError("outcomes_retained must be false")
    rows = doc.get("per_seed_mechanism")
    if not isinstance(rows, list) or len(rows) != 240:
        raise ValueError("expected exactly 240 mechanism rows")
    if [r.get("seed") for r in rows] != list(range(70400, 70640)):
        raise ValueError("seed accounting/order mismatch")
    records = []
    for row in rows:
        if set(row) != ROW_FIELDS or FORBIDDEN & set(row):
            raise ValueError("mechanism row schema mismatch or endpoint leak")
        if not 0 <= int(row["active_plies"]) <= int(row["plies"]):
            raise ValueError("invalid active duty")
        for record in row["records"]:
            if set(record) != RECORD_FIELDS or FORBIDDEN & set(record):
                raise ValueError("record schema mismatch or endpoint leak")
            if int(record["seed"]) != int(row["seed"]):
                raise ValueError("record seed mismatch")
            if record["kind"] not in ("treatment", "null"):
                raise ValueError("invalid record kind")
            if not 0 <= int(record["gate_offset"]) < 4:
                raise ValueError("record outside K4 window")
            if int(record["base_action"]) == int(record["chosen_action"]):
                raise ValueError("non-flip recorded as distinct")
            records.append(record)
    treatment = [r for r in records if r["kind"] == "treatment"]
    null = [r for r in records if r["kind"] == "null"]
    hashes = [int(r["thin_hash"]) for r in null]
    if len(hashes) != len(set(hashes)):
        raise ValueError("null hash collision")
    cutoff = int(doc["null_keep_num"])
    selected = [r for r in null if int(r["thin_hash"]) < cutoff]
    expected = (len(treatment), len(null), len(selected))
    claimed = (int(doc["treatment_distinct_flips"]),
               int(doc["null_distinct_opportunities"]),
               int(doc["null_selected_distinct_flips"]))
    if expected != claimed or len(selected) != len(treatment):
        raise ValueError("distinct-state dose/cutoff accounting mismatch")
    return {"treatment": len(treatment), "null_opportunities": len(null),
            "null_selected": len(selected)}


def rejected(doc):
    try:
        validate(doc)
    except (KeyError, TypeError, ValueError):
        return True
    return False


def main():
    doc = json.loads(INPUT.read_text())
    counts = validate(doc)
    endpoint_mutant = copy.deepcopy(doc)
    endpoint_mutant["per_seed_mechanism"][0]["dies_ahead"] = 0
    duplicate_mutant = copy.deepcopy(doc)
    duplicate_mutant["per_seed_mechanism"][1]["seed"] = 70400
    cutoff_mutant = copy.deepcopy(doc)
    cutoff_mutant["null_keep_num"] -= 1
    killed = {
        "endpoint_leak_rejected": rejected(endpoint_mutant),
        "duplicate_seed_rejected": rejected(duplicate_mutant),
        "wrong_cutoff_rejected": rejected(cutoff_mutant),
    }
    report = {
        "version": "post-garbage-calibration-audit-v1",
        "pass": all(killed.values()), "counts": counts,
        "killed_mutants": killed,
    }
    OUTPUT.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
    if not report["pass"]:
        raise SystemExit("AUDIT FAIL")


if __name__ == "__main__":
    main()
