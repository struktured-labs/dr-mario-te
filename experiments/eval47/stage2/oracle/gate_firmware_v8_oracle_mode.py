#!/usr/bin/env python3
"""Infrastructure gates for PREREG_FIRMWARE_V8_ORACLE_MODE.md."""
from __future__ import annotations

import copy
import json
import os
import tempfile

import numpy as np

import oracle_arm as O
import run_oracle as R

SEEDS = range(43000, 43006)
PROV_FIELDS = {"policy_semantics", "tie_seed_mode", "tie_seed", "base_action",
               "trt_action", "cands", "labels", "ply"}


def direct(seed, C, model, semantics, tie_mode):
    from fb import FB
    import root_search as RS
    env = O.make_env(seed, C["level"])
    actions = []
    result = "stall"
    for _ply in range(300):
        if env.board.virus_count() == 0:
            result = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        lnk = (np.ascontiguousarray(env.board.link, dtype=np.int8).reshape(-1)
               if semantics == "firmware_v8" else None)
        vals = O._policy_values(col, vir, lnk, int(env.cur.a), int(env.cur.b),
                                int(env.nxt.a), int(env.nxt.b), C["w"], C["fl"],
                                C["wt"], C["ws"], semantics)
        ranked = O._policy_rank_values(vals, semantics,
                                       O.policy_tie_seed(seed, tie_mode))
        action = O._champ_action(ranked, O.CHAMP_ORDER)
        if action is None:
            break
        actions.append(action)
        r, _v = O._advance(env, action, C, seed, model)
        if r is not None:
            result = r
            break
    return actions, result, env.pills_placed


def find_gated(seed, C, model):
    env = O.make_env(seed, C["level"])
    arm = O.OracleArm(label_mode="const", policy_semantics="firmware_v8",
                      tie_seed_mode="p2_surrogate")
    for ply in range(300):
        fires, _dh, _vr = O.gate_fires(env)
        if fires:
            return env, ply
        action, _ = arm.choose(env, seed, C, model, C["w"], C["fl"],
                               C["wt"], C["ws"], ply)
        if action is None:
            break
        result, _v = O._advance(env, action, C, seed, model)
        if result is not None:
            break
    raise RuntimeError("failed to find a real gated state")


def main():
    C, model = O.init_rig("lulu")
    gates = {}

    # Default must remain the historical arm exactly.
    default_exact = explicit_exact = 0
    actual_exact = historical_mutant_breaks = seed0_mutant_breaks = 0
    for seed in SEEDS:
        rd = O.play_one(seed, O.OracleArm(label_mode="const"), C, model)
        re = O.play_one(seed, O.OracleArm(
            label_mode="const", policy_semantics="historical_compact",
            tie_seed_mode="seed0"), C, model)
        default_exact += int(rd["_actions"] == re["_actions"] and rd["res"] == re["res"])
        hd, hr, hp = direct(seed, C, model, "historical_compact", "seed0")
        explicit_exact += int(re["_actions"] == hd and re["res"] == hr and re["pills"] == hp)

        arm = O.OracleArm(label_mode="const", policy_semantics="firmware_v8",
                          tie_seed_mode="p2_surrogate")
        ra = O.play_one(seed, arm, C, model)
        ad, ar, ap = direct(seed, C, model, "firmware_v8", "p2_surrogate")
        actual_exact += int(ra["_actions"] == ad and ra["res"] == ar and ra["pills"] == ap)
        historical_mutant_breaks += int(ra["_actions"] != hd)
        z, _zr, _zp = direct(seed, C, model, "firmware_v8", "seed0")
        seed0_mutant_breaks += int(ra["_actions"] != z)
    gates["default_equals_explicit_historical"] = f"{default_exact}/{len(SEEDS)}"
    gates["historical_arm_equals_direct"] = f"{explicit_exact}/{len(SEEDS)}"
    gates["firmware_arm_equals_direct"] = f"{actual_exact}/{len(SEEDS)}"
    gates["historical_mutant_breaks_firmware"] = f"{historical_mutant_breaks}/{len(SEEDS)}"
    gates["seed0_mutant_breaks_surrogate"] = f"{seed0_mutant_breaks}/{len(SEEDS)}"

    # Observe the semantics requested at the real root and inside real horizon-2 forks.
    seed = 43100
    env, ply = find_gated(seed, C, model)
    original_values = O._policy_values
    seen = []
    def observed(*args, **kwargs):
        semantics = args[-1] if args else kwargs["semantics"]
        seen.append(semantics)
        return original_values(*args, **kwargs)
    O._policy_values = observed
    try:
        real_arm = O.OracleArm(label_mode="true", horizon=2,
                               policy_semantics="firmware_v8",
                               tie_seed_mode="p2_surrogate")
        real_arm.choose(copy.deepcopy(env), seed, C, model, C["w"], C["fl"],
                        C["wt"], C["ws"], ply)
    finally:
        O._policy_values = original_values
    path_exact = len(seen) > 1 and set(seen) == {"firmware_v8"}
    mutant_seen = ["historical_compact"] * len(seen)
    historical_path_mutant = len(mutant_seen) > 1 and not all(
        semantics == "firmware_v8" for semantics in mutant_seen)
    gates["root_and_forks_request_firmware_v8"] = {"pass": path_exact, "calls": len(seen)}
    gates["historical_path_mutant_fails"] = historical_path_mutant

    # Force a non-base label solely to inspect new provenance schema.
    calls = [0]
    original_fork = O._fork_label
    def forced_fork(*_args, **_kwargs):
        i = calls[0]; calls[0] += 1
        return (1, 1) if i % 4 == 1 else (1, 0)
    O._fork_label = forced_fork
    try:
        pa = O.OracleArm(label_mode="true", horizon=2, provenance=True,
                         policy_semantics="firmware_v8", tie_seed_mode="p2_surrogate")
        pa.choose(copy.deepcopy(env), seed, C, model, C["w"], C["fl"],
                  C["wt"], C["ws"], ply)
    finally:
        O._fork_label = original_fork
    provenance_exact = (len(pa.flip_log) == 1 and PROV_FIELDS <= set(pa.flip_log[0])
                        and pa.flip_log[0]["policy_semantics"] == "firmware_v8"
                        and pa.flip_log[0]["tie_seed_mode"] == "p2_surrogate"
                        and pa.flip_log[0]["tie_seed"] == O.policy_tie_seed(seed, "p2_surrogate"))
    gates["firmware_provenance_fields"] = provenance_exact

    # Resume metadata must reject either changed field.
    with tempfile.TemporaryDirectory(prefix="oracle-mode-") as tmp:
        manifest = {"rolled": "gate", "files": {}, "python": "gate"}
        base = {"policy_semantics": "firmware_v8", "tie_seed_mode": "p2_surrogate"}
        R.freeze_meta(tmp, base, manifest)
        R.freeze_meta(tmp, base, manifest)
        rejected = []
        for key, value in (("policy_semantics", "historical_compact"),
                           ("tie_seed_mode", "seed0")):
            wrong = dict(base); wrong[key] = value
            try:
                R.freeze_meta(tmp, wrong, manifest)
            except RuntimeError:
                rejected.append(key)
        gates["resume_rejects_changed_semantics"] = rejected == ["policy_semantics", "tie_seed_mode"]

    manifest = R.runtime_manifest("lulu", "firmware_v8")
    manifest_names = set(manifest["files"])
    manifest_exact = {"firmware_v8_policy", "cascade_chain_x", "cascade_link_x",
                      "cascade_stranded_x"} <= manifest_names
    gates["firmware_dependencies_in_manifest"] = manifest_exact

    tie = np.full(32, np.nan); tie[O.CHAMP_ORDER[0]] = tie[O.CHAMP_ORDER[1]] = 0
    reverse_killed = O._champ_action(tie, O.CHAMP_ORDER) != O._champ_action(tie, O.CHAMP_ORDER[::-1])
    gates["reverse_tie_order_mutant_killed"] = reverse_killed

    ok = (default_exact == len(SEEDS) and explicit_exact == len(SEEDS)
          and actual_exact == len(SEEDS) and historical_mutant_breaks > 0
          and seed0_mutant_breaks > 0 and path_exact and historical_path_mutant
          and provenance_exact and gates["resume_rejects_changed_semantics"]
          and manifest_exact and reverse_killed)
    result = {"seeds": [min(SEEDS), max(SEEDS)], "gates": gates,
              "ALL_GATES_PASS": bool(ok)}
    print(json.dumps(result, indent=1))
    with open("/tmp/firmware_v8_oracle_mode_gate.json", "w") as out:
        json.dump(result, out, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
