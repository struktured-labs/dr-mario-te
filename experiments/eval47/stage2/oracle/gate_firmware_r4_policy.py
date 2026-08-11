#!/usr/bin/env python3
"""Prospective complete-decision gate for firmware_r4_policy.py."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
for path in (HERE, os.path.join(REPO, "experiments", "eval47"),
             os.path.join(REPO, "experiments", "tuck_v3")):
    if path not in sys.path:
        sys.path.insert(0, path)

import firmware_r4_policy as R4  # noqa: E402
import hang_r4_fidelity as HA  # noqa: E402
import oracle_arm as O  # noqa: E402

ORDER = O.CHAMP_ORDER
N_PER_KIND = 4
MAX_SEED = 30031
DEFAULT_FIT = ("/home/struktured/projects/dr-mario-te/source/experiments/eval47/"
               "results/dr_lulu_20260808_fit.json")
CANON = "/home/struktured/projects/dr-mario-canonical-wt"


def action(vals):
    return R4.choose_from_values(vals, ORDER)


def legacy_values(args, w, fl, wt, ws):
    return O._champ_values(*args, w, fl, wt, ws)


def snapshot(kind, seed, ply, env, col, vir, args, legacy, r4, r4_ws0):
    return {
        "kind": kind, "seed": int(seed), "ply": int(ply),
        "col": [int(x) for x in col], "vir": [int(x) for x in vir],
        "ca": int(args[2]), "cb": int(args[3]), "na": int(args[4]), "nb": int(args[5]),
        "viruses": int(env.board.virus_count()),
        "legacy_action": action(legacy), "r4_action": action(r4),
        "r4_ws0_action": action(r4_ws0),
        "r4_value": int(round(float(np.nanmax(r4)))),
    }


def select_cases(fit):
    os.environ["DR_LULU_FIT"] = fit
    C, model = O.init_rig("lulu")
    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    assert (wt, ws) == (0, 20), (wt, ws)
    cases = {"flat_sensitive": [], "strand_sensitive": [], "control": []}
    used = set()
    from fb import FB
    import root_search as RS
    for seed in range(30000, MAX_SEED + 1):
        env = O.make_env(seed, C["level"])
        for ply in range(300):
            if env.board.virus_count() == 0:
                break
            fb = FB.from_board(env.board)
            col, vir = RS.board_flat_from_fb(fb)
            args = (col, vir, int(env.cur.a), int(env.cur.b),
                    int(env.nxt.a), int(env.nxt.b))
            old = legacy_values(args, w, fl, wt, ws)
            r4 = R4.candidate_values(*args, w, fl, wt=wt, ws=ws)
            r4_ws0 = R4.candidate_values(*args, w, fl, wt=wt, ws=0)
            old_a, r4_a, ws0_a = action(old), action(r4), action(r4_ws0)
            key = (seed, ply)
            kind = None
            if old_a != r4_a and len(cases["flat_sensitive"]) < N_PER_KIND:
                kind = "flat_sensitive"
            elif ws0_a != r4_a and len(cases["strand_sensitive"]) < N_PER_KIND:
                kind = "strand_sensitive"
            elif (old_a == r4_a == ws0_a and len(cases["control"]) < N_PER_KIND):
                kind = "control"
            if kind and key not in used:
                cases[kind].append(snapshot(kind, seed, ply, env, col, vir,
                                            args, old, r4, r4_ws0))
                used.add(key)
            if all(len(v) == N_PER_KIND for v in cases.values()):
                return C, cases
            if old_a is None:
                break
            result, _ = O._advance(env, old_a, C, seed, model)
            if result is not None:
                break
    raise AssertionError("case selection failed: " + repr({k: len(v) for k, v in cases.items()}))


def git_head(path):
    return subprocess.check_output(["git", "-C", path, "rev-parse", "HEAD"], text=True).strip()


def local_firmware_decider():
    """Load this worktree's decider by path; oracle imports reorder sys.path."""
    path = os.path.join(REPO, "experiments", "tuck_v3", "firmware_decider.py")
    spec = importlib.util.spec_from_file_location("firmware_decider_r4_gate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FirmwareDecider


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit", default=os.environ.get("DR_LULU_FIT", DEFAULT_FIT))
    ap.add_argument("--out", default=os.path.join(HERE, "out", "firmware_r4_policy.json"))
    a = ap.parse_args()

    mirror = HA.mirror_gate()
    if not mirror["pass"]:
        raise SystemExit("R4 TERM GATE FAILED: " + json.dumps(mirror))
    C, strata = select_cases(a.fit)
    selected = [case for kind in ("flat_sensitive", "strand_sensitive", "control")
                for case in strata[kind]]

    FirmwareDecider = local_firmware_decider()
    fd = FirmwareDecider(tuck=0, strand=20)
    probe = bytes([0xFF] * 128)
    image, _, _ = fd.B.build_image(probe, 0, 1, 1, 0)
    image_hash = hashlib.sha256(bytes(image)).hexdigest()

    rows = []
    for case in selected:
        col = np.asarray(case["col"], dtype=np.int8)
        vir = np.asarray(case["vir"], dtype=np.int8)
        pick = fd.decide(col, vir, case["ca"], case["cb"], case["na"], case["nb"])
        observed_action = None if pick is None else int(pick["action"])
        observed_value = None if pick is None else int(pick["value"])
        row = dict(case)
        row.update(firmware_action=observed_action, firmware_value=observed_value,
                   action_exact=observed_action == case["r4_action"],
                   value_exact=observed_value == case["r4_value"],
                   steps=None if pick is None else int(pick["steps"]))
        rows.append(row)
        print(f"{case['kind']} seed={case['seed']} ply={case['ply']}: "
              f"r4={case['r4_action']}/{case['r4_value']} "
              f"fw={observed_action}/{observed_value}", flush=True)

    exact_action = all(r["action_exact"] for r in rows)
    exact_value = all(r["value_exact"] for r in rows)
    flat_rows = [r for r in rows if r["kind"] == "flat_sensitive"]
    strand_rows = [r for r in rows if r["kind"] == "strand_sensitive"]
    mutants = {
        "legacy_flat_rejected": all(r["firmware_action"] != r["legacy_action"]
                                    for r in flat_rows),
        "strand0_rejected": all(r["firmware_action"] != r["r4_ws0_action"]
                                for r in strand_rows),
        "value_plus_one_rejected": all(r["firmware_value"] != r["r4_value"] + 1
                                       for r in rows),
    }
    passed = exact_action and exact_value and all(mutants.values()) and mirror["pass"]
    result = {
        "authority": "OBSERVATION_INSTRUMENT",
        "semantics": R4.SEMANTICS,
        "prereg": "PREREG_FIRMWARE_R4_POLICY.md",
        "canonical_git": git_head(CANON),
        "firmware_image_sha256": image_hash,
        "fit": os.path.realpath(a.fit),
        "strata": {k: len(v) for k, v in strata.items()},
        "term_gate": mirror,
        "complete_decision": {"actions_exact": exact_action, "values_exact": exact_value},
        "killed_mutants": mutants,
        "rows": rows,
        "pass": passed,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps({k: result[k] for k in ("semantics", "strata", "complete_decision",
                                             "killed_mutants", "pass")}, indent=1))
    if not passed:
        raise SystemExit("FIRMWARE R4 POLICY GATE FAILED")


if __name__ == "__main__":
    main()
