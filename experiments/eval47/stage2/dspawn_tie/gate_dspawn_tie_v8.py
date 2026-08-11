#!/usr/bin/env python3
"""Prospective two-sided gates for PREREG_DSPAWN_TIE_V8.md."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ORACLE = os.path.dirname(HERE) + "/oracle"
for path in (HERE, ORACLE):
    if path not in sys.path:
        sys.path.insert(0, path)

import dspawn_tie_v8 as D  # noqa: E402
import firmware_v8_policy as V8  # noqa: E402
import oracle_arm as O  # noqa: E402

SMOKE_SEEDS = range(60300, 60304)


def synthetic_gates():
    a0, a1 = int(D.CHAMP_ORDER[0]), int(D.CHAMP_ORDER[1])
    vals = np.full(32, np.nan)
    vals[a0] = vals[a1] = 100
    sensor = np.full(32, -1, dtype=int)
    sensor[a0], sensor[a1] = 12, 10
    got = D.treatment_choice(vals, sensor, a0)
    clipped = sensor.copy()
    clipped[clipped >= 0] = np.minimum(clipped[clipped >= 0], 8)
    clipped_got = D.treatment_choice(vals, clipped, a0)

    strict = vals.copy()
    strict[a1] = 99
    strict_got = D.treatment_choice(strict, sensor, a0)
    gap_mutant = D.treatment_choice(strict, sensor, a0, gap_mutant=True)

    null_before = D.null_choice(vals, a0, 17, 9, 1, 1)
    perm_sensor = sensor[::-1].copy()
    null_after = D.null_choice(vals, a0, 17, 9, 1, 1)
    # Deliberately wrong null reads the sensor, so the sensor permutation kills it.
    wrong_before = int(np.nanargmin(np.where(sensor >= 0, sensor, 999)))
    wrong_after = int(np.nanargmin(np.where(perm_sensor >= 0, perm_sensor, 999)))
    return {
        "equal_value_lower_height": {"pass": got == a1, "got": got, "want": a1},
        "clipped_deadzone_mutant_killed": {
            "pass": clipped_got != a1, "mutant_got": clipped_got},
        "strict_decision_unchanged": {"pass": strict_got == a0, "got": strict_got},
        "gap1_mutant_killed": {"pass": gap_mutant == a1, "mutant_got": gap_mutant},
        "null_sensor_invariant": {
            "pass": null_before == null_after, "before": null_before, "after": null_after},
        "sensor_reading_null_mutant_killed": {
            "pass": wrong_before != wrong_after,
            "before": wrong_before, "after": wrong_after},
    }


def real_gates():
    C, model = O.init_rig("exo_lulu")
    decisions = mismatches = 0
    identity = True
    wrong_tie_diffs = 0
    legal_mask_mutant_rejected = False
    games = []
    for seed in SMOKE_SEEDS:
        base = D.TieArm("base")
        got = D.play_one(seed, base, C, model)
        ref_arm = O.OracleArm(label_mode="const", policy_semantics="firmware_v8",
                              tie_seed_mode="p2_surrogate")
        ref = O.play_one(seed, ref_arm, C, model)
        same = (got["_actions"] == ref["_actions"] and got["res"] == ref["res"]
                and got["pills"] == ref["pills"] and got["garbage"] == ref["garbage"])
        identity &= same

        env = O.make_env(seed, C["level"])
        for ply in range(min(40, len(got["_actions"]))):
            col, vir, lnk = D.board_inputs(env)
            vals = V8.candidate_values(col, vir, lnk, int(env.cur.a), int(env.cur.b),
                                       int(env.nxt.a), int(env.nxt.b), C["w"], C["fl"])
            sensor = D.post_dspawn_linked(col, vir, lnk, int(env.cur.a), int(env.cur.b))
            sensor_legal = sensor >= 0
            value_legal = np.isfinite(vals)
            mismatches += int(not np.array_equal(sensor_legal, value_legal))
            if not legal_mask_mutant_rejected:
                mutant = sensor_legal.copy()
                mutant[int(D.CHAMP_ORDER[0])] = ~mutant[int(D.CHAMP_ORDER[0])]
                legal_mask_mutant_rejected = not np.array_equal(mutant, value_legal)
            decisions += 1
            p2 = V8.choose_seeded(vals, O.policy_tie_seed(seed, "p2_surrogate"))
            seed0 = V8.choose_seeded(vals, 0)
            wrong_tie_diffs += int(p2 != seed0)
            out, _v = O._advance(env, got["_actions"][ply], C, seed, model)
            if out is not None:
                break
        games.append({"seed": seed, "same": same, "res": got["res"],
                      "pills": got["pills"]})
    return {
        "real_legal_masks": {"pass": decisions >= 100 and mismatches == 0,
                             "decisions": decisions, "mismatches": mismatches},
        "legal_mask_mutant_killed": {"pass": legal_mask_mutant_rejected,
                                     "mutation": "invert CHAMP_ORDER[0] legality"},
        "base_action_outcome_identity": {"pass": identity, "games": games},
        "seed0_tie_mutant_killed": {"pass": wrong_tie_diffs > 0,
                                    "action_differences": wrong_tie_diffs},
    }


def main():
    os.environ["DR_LULU_FIT"] = (
        "/home/struktured/projects/dr-mario-te/source/experiments/eval47/results/"
        "dr_lulu_20260808_fit.json")
    checks = {**synthetic_gates(), **real_gates()}
    repo = os.path.abspath(os.path.join(HERE, "../../../.."))
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    report = {"version": "dspawn-tie-v8-gate-v1", "source_commit": source,
              "smoke_seeds": list(SMOKE_SEEDS),
              "checks": checks, "pass": all(row["pass"] for row in checks.values())}
    print(json.dumps(report, indent=1))
    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "gate.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    if not report["pass"]:
        raise SystemExit("GATE FAIL")


if __name__ == "__main__":
    main()
