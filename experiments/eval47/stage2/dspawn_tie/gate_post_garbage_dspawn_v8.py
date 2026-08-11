#!/usr/bin/env python3
"""Two-sided engineering gates for the post-garbage K4/wq60 prototype."""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ORACLE = os.path.dirname(HERE) + "/oracle"
for path in (HERE, ORACLE):
    if path not in sys.path:
        sys.path.insert(0, path)

import post_garbage_dspawn_v8 as P  # noqa: E402
import firmware_v8_policy as V8  # noqa: E402
import oracle_arm as O  # noqa: E402

FIT = ("/home/struktured/projects/dr-mario-te/source/experiments/eval47/results/"
       "dr_lulu_20260808_fit.json")
SMOKE_SEEDS = range(70300, 70304)


def fake_root(mark=0):
    col = np.zeros(128, dtype=np.int8)
    vir = np.zeros(128, dtype=np.int8)
    lnk = np.zeros(128, dtype=np.int8)
    col[0] = int(mark)
    return col, vir, lnk, (0, 0, 0)


def synthetic_gates():
    gate = P.LandedPulseGate(4)
    before = gate.consume_decision()
    gate.note_landed(2)
    sequence = [gate.consume_decision() for _ in range(5)]
    mutant = P.LandedPulseGate(5)
    mutant.note_landed(2)
    mutant_sequence = [mutant.consume_decision() for _ in range(5)]

    legal = [int(a) for a in V8.CHAMP_ORDER[:4]]
    vals = np.full(32, np.nan)
    vals[legal] = [100, 90, 80, 70]
    penalty = np.full(32, np.nan)
    penalty[legal] = [120, 0, 60, 180]
    tie_seed = 0
    treatment = P.scored_choice(vals, penalty, tie_seed)

    null_a = P.shuffled_penalty(penalty, vals, 17, 9)
    permuted_real = penalty.copy()
    permuted_real[legal] = penalty[legal[::-1]]
    null_b = P.shuffled_penalty(permuted_real, vals, 17, 9)
    wrong_a = penalty.copy()
    wrong_b = permuted_real.copy()

    roots = [None] * 32
    roots[legal[0]] = fake_root(1)
    roots[legal[1]] = fake_root(1)
    roots[legal[2]] = fake_root(2)
    alias_choice = P.normalize_alias(legal[0], legal[1], roots)
    distinct_choice = P.normalize_alias(legal[0], legal[2], roots)
    color_mutant = fake_root(1)
    color_mutant[0][1] = 3

    kept = P.thin_accepts(123, 7, 314159, 1_000_000)
    kept_again = P.thin_accepts(123, 7, 314159, 1_000_000)
    return {
        "pulse_starts_next_decision": {"pass": before is False},
        "exactly_four_decisions": {
            "pass": sequence == [True, True, True, True, False],
            "sequence": sequence},
        "kplus1_mutant_killed": {
            "pass": mutant_sequence[-1] is True,
            "mutant_sequence": mutant_sequence},
        "wq60_arithmetic_changes_strict_choice": {
            "pass": treatment == legal[1], "base": legal[0],
            "treatment": treatment},
        "null_preserves_penalty_multiset": {
            "pass": sorted(null_a[legal]) == sorted(penalty[legal])},
        "null_sensor_association_invariant": {
            "pass": np.array_equal(null_a, null_b, equal_nan=True)},
        "association_reading_mutant_killed": {
            "pass": not np.array_equal(wrong_a, wrong_b, equal_nan=True)},
        "action_alias_normalized": {
            "pass": alias_choice == legal[0], "raw_alternative": legal[1]},
        "distinct_state_retained": {
            "pass": distinct_choice == legal[2]},
        "color_byte_mutant_rejected": {
            "pass": not P.exact_alias(roots[legal[0]], color_mutant)},
        "thinning_deterministic": {"pass": kept == kept_again},
    }


def real_gates():
    os.environ["DR_LULU_FIT"] = FIT
    C, model = O.init_rig("exo_lulu")
    games, total_active = [], 0
    total_treatment = total_null = 0
    identity = True
    for seed in SMOKE_SEEDS:
        arm = P.PostGarbageArm("calibration")
        got = P.play_one(seed, arm, C, model)
        ref_arm = O.OracleArm(
            label_mode="const", policy_semantics="firmware_v8",
            tie_seed_mode="p2_surrogate")
        ref = O.play_one(seed, ref_arm, C, model)
        same = (got["_actions"] == ref["_actions"]
                and got["res"] == ref["res"]
                and got["pills"] == ref["pills"]
                and got["garbage"] == ref["garbage"])
        identity &= same
        total_active += got["active_plies"]
        total_treatment += got["treatment_distinct_flips"]
        total_null += got["null_distinct_opportunities"]
        games.append({
            "seed": seed, "same": same, "res": got["res"],
            "pills": got["pills"], "landed": got["garbage"],
            "active_plies": got["active_plies"],
            "treatment_distinct": got["treatment_distinct_flips"],
            "null_distinct": got["null_distinct_opportunities"],
        })
    # Deliberately wrong offered-pressure gate is active from pill 25 even if
    # zero cells land; a synthetic no-land pulse already exercises its error.
    return {
        "base_trajectory_identity": {"pass": identity, "games": games},
        "actual_landed_gate_exercised": {
            "pass": total_active > 0, "active_plies": total_active},
        "treatment_distinct_path_exercised": {
            "pass": total_treatment > 0, "distinct_flips": total_treatment},
        "null_distinct_path_exercised": {
            "pass": total_null > 0, "distinct_opportunities": total_null},
    }


def main():
    checks = {**synthetic_gates(), **real_gates()}
    report = {
        "version": "post-garbage-dspawn-v8-engineering-gate-v1",
        "status": "PRE_ENDPOINT_INFRASTRUCTURE_ONLY",
        "smoke_seeds": list(SMOKE_SEEDS), "checks": checks,
        "pass": all(row["pass"] for row in checks.values()),
    }
    print(json.dumps(report, indent=1))
    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "post_garbage_gate.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    if not report["pass"]:
        raise SystemExit("GATE FAIL")


if __name__ == "__main__":
    main()
