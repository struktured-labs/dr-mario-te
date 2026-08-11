#!/usr/bin/env python3
"""Prospective complete-decision gate for firmware_v8_policy."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import random
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
for path in reversed((HERE, os.path.join(REPO, "experiments", "eval47"),
                      os.path.join(REPO, "experiments", "tuck_v3"))):
    if path not in sys.path:
        sys.path.insert(0, path)

import firmware_r4_policy as CAP1  # noqa: E402
import firmware_v8_policy as V8  # noqa: E402
import hang_r4_fidelity as HA  # noqa: E402
import oracle_arm as O  # noqa: E402

N_PER_KIND = 3
MAX_SEED = 30063
DEFAULT_FIT = ("/home/struktured/projects/dr-mario-te/source/experiments/eval47/"
               "results/dr_lulu_20260808_fit.json")
CANON = "/home/struktured/projects/dr-mario-canonical-wt"


def action(vals, order=V8.CHAMP_ORDER):
    return V8.choose_from_values(vals, order)


def lockstep_gate(w, fl, n=200):
    """Candidate-valued flat mode must preserve the existing full-mechanics action."""
    rng = random.Random(20260811)
    mismatches = []
    for case in range(n):
        col = np.zeros(128, dtype=np.int8)
        vir = np.zeros(128, dtype=np.int8)
        lnk = np.zeros(128, dtype=np.int8)
        for c in range(8):
            height = rng.randrange(2, 10)
            for r in range(16 - height, 16):
                i = r * 8 + c
                col[i] = rng.randrange(1, 4)
                vir[i] = int(rng.random() < 0.22)
        ca, cb, na, nb = [rng.randrange(1, 4) for _ in range(4)]
        vals = V8.candidate_values(col, vir, lnk, ca, cb, na, nb, w, fl, r4=False)
        got = action(vals)
        expected = int(V8.CS._choose_d3_chain_s(
            col, vir, lnk, ca, cb, na, nb, V8.TOPK2, V8.W_EXCAV, V8.W_HANG,
            w, fl, 0, V8.W_CHAIN, V8.WS))
        if got != expected:
            mismatches.append({"case": case, "expected": expected, "observed": got})
    empty = np.zeros(128, dtype=np.int8)
    tie_vals = V8.candidate_values(empty, empty, empty, 1, 1, 1, 1, w, fl, r4=True)
    forward = action(tie_vals)
    reverse = action(tie_vals, V8.CHAMP_ORDER[::-1])
    return {"cases": n, "mismatches": mismatches,
            "reverse_tie_order_rejected": forward != reverse,
            "tie_actions": {"forward": forward, "reverse": reverse},
            "pass": not mismatches and forward != reverse}


def snapshot(kind, seed, ply, env, col, vir, lnk, args,
             full, full_flat, cap1):
    return {
        "kind": kind, "seed": int(seed), "ply": int(ply),
        "col": [int(x) for x in col], "vir": [int(x) for x in vir],
        "lnk": [int(x) for x in lnk],
        "ca": int(args[3]), "cb": int(args[4]), "na": int(args[5]), "nb": int(args[6]),
        "viruses": int(env.board.virus_count()),
        "v8_action": action(full), "v8_value": int(round(float(np.nanmax(full)))),
        "full_flat_action": action(full_flat), "cap1_r4_action": action(cap1),
    }


def select_cases(fit):
    os.environ["DR_LULU_FIT"] = fit
    C, model = O.init_rig("lulu")
    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    assert (wt, ws) == (0, 20), (wt, ws)
    cases = {"mechanics_sensitive": [], "hang_sensitive": [], "control": []}
    from fb import FB
    import root_search as RS
    for seed in range(30001, MAX_SEED + 1):
        env = O.make_env(seed, C["level"])
        for ply in range(300):
            if env.board.virus_count() == 0:
                break
            fb = FB.from_board(env.board)
            col, vir = RS.board_flat_from_fb(fb)
            lnk = np.ascontiguousarray(env.board.link, dtype=np.int8).reshape(-1)
            args = (col, vir, lnk, int(env.cur.a), int(env.cur.b),
                    int(env.nxt.a), int(env.nxt.b))
            full = V8.candidate_values(*args, w, fl, r4=True)
            full_flat = V8.candidate_values(*args, w, fl, r4=False)
            cap1 = CAP1.candidate_values(col, vir, *args[3:], w, fl, wt=wt, ws=ws)
            old = O._champ_values(col, vir, *args[3:], w, fl, wt, ws)
            full_a, flat_a, cap1_a = action(full), action(full_flat), action(cap1)
            kind = None
            if full_a != cap1_a and len(cases["mechanics_sensitive"]) < N_PER_KIND:
                kind = "mechanics_sensitive"
            elif full_a != flat_a and len(cases["hang_sensitive"]) < N_PER_KIND:
                kind = "hang_sensitive"
            elif (full_a == flat_a == cap1_a and len(cases["control"]) < N_PER_KIND):
                kind = "control"
            if kind:
                cases[kind].append(snapshot(kind, seed, ply, env, col, vir, lnk,
                                            args, full, full_flat, cap1))
            if all(len(v) == N_PER_KIND for v in cases.values()):
                return C, cases
            old_a = action(old)
            if old_a is None:
                break
            result, _ = O._advance(env, old_a, C, seed, model)
            if result is not None:
                break
    raise AssertionError("case selection failed: " + repr({k: len(v) for k, v in cases.items()}))


def local_firmware_decider():
    path = os.path.join(REPO, "experiments", "tuck_v3", "firmware_decider.py")
    spec = importlib.util.spec_from_file_location("firmware_decider_v8_gate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FirmwareDecider


def git_head(path):
    return subprocess.check_output(["git", "-C", path, "rev-parse", "HEAD"], text=True).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit", default=os.environ.get("DR_LULU_FIT", DEFAULT_FIT))
    ap.add_argument("--out", default=os.path.join(HERE, "out", "firmware_v8_policy.json"))
    a = ap.parse_args()
    os.environ["DR_LULU_FIT"] = a.fit
    C, _ = O.init_rig("lulu")
    w, fl = C["w"], C["fl"]

    mirror = HA.mirror_gate()
    lockstep = lockstep_gate(w, fl)
    if not mirror["pass"] or not lockstep["pass"]:
        raise SystemExit("IMPLEMENTATION GATE FAILED: " + json.dumps(
            {"term": mirror, "lockstep": lockstep}))
    _, strata = select_cases(a.fit)
    selected = [case for kind in ("mechanics_sensitive", "hang_sensitive", "control")
                for case in strata[kind]]

    FirmwareDecider = local_firmware_decider()
    fd = FirmwareDecider(tuck=0, drfix=1, drchain=180, strand=20)
    image, _, _ = fd.B.build_image(bytes([0xFF] * 128), 0, 1, 1, 0)
    rows = []
    for case in selected:
        col = np.asarray(case["col"], dtype=np.int8)
        vir = np.asarray(case["vir"], dtype=np.int8)
        lnk = np.asarray(case["lnk"], dtype=np.int8)
        pick = fd.decide(col, vir, case["ca"], case["cb"], case["na"], case["nb"],
                         lnk=lnk)
        observed_action = None if pick is None else int(pick["action"])
        observed_value = None if pick is None else int(pick["value"])
        row = dict(case)
        row.update(firmware_action=observed_action, firmware_value=observed_value,
                   action_exact=observed_action == case["v8_action"],
                   value_exact=observed_value == case["v8_value"],
                   steps=None if pick is None else int(pick["steps"]))
        rows.append(row)
        print(f"{case['kind']} seed={case['seed']} ply={case['ply']}: "
              f"v8={case['v8_action']}/{case['v8_value']} "
              f"fw={observed_action}/{observed_value}", flush=True)

    exact_action = all(r["action_exact"] for r in rows)
    exact_value = all(r["value_exact"] for r in rows)
    mechanics = [r for r in rows if r["kind"] == "mechanics_sensitive"]
    hang = [r for r in rows if r["kind"] == "hang_sensitive"]
    mutants = {
        "cap1_r4_rejected": all(r["firmware_action"] != r["cap1_r4_action"]
                                for r in mechanics),
        "full_flat_hang_rejected": all(r["firmware_action"] != r["full_flat_action"]
                                       for r in hang),
        "value_plus_one_rejected": all(r["firmware_value"] != r["v8_value"] + 1
                                       for r in rows),
        "reverse_tie_order_rejected": lockstep["reverse_tie_order_rejected"],
    }
    passed = exact_action and exact_value and all(mutants.values())
    result = {
        "authority": "OBSERVATION_INSTRUMENT",
        "semantics": V8.SEMANTICS,
        "prereg": "PREREG_FIRMWARE_V8_POLICY.md",
        "canonical_git": git_head(CANON),
        "firmware_image_sha256": hashlib.sha256(bytes(image)).hexdigest(),
        "fit": os.path.realpath(a.fit),
        "strata": {k: len(v) for k, v in strata.items()},
        "term_gate": mirror, "flat_lockstep": lockstep,
        "complete_decision": {"actions_exact": exact_action, "values_exact": exact_value},
        "killed_mutants": mutants, "rows": rows, "pass": passed,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps({k: result[k] for k in ("semantics", "strata", "complete_decision",
                                             "killed_mutants", "pass")}, indent=1))
    if not passed:
        raise SystemExit("FIRMWARE V8 POLICY GATE FAILED")


if __name__ == "__main__":
    main()

