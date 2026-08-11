#!/usr/bin/env python3
"""Fail-closed analysis and verdict for the sealed post-garbage endpoint."""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

HERE = Path(__file__).resolve().parent
ORACLE = HERE.parent / "oracle"
for path in (str(HERE), str(ORACLE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import fit_stratified_post_garbage_null as F  # noqa: E402
import post_garbage_dspawn_v8 as P  # noqa: E402

N = 9000
B = 5000
RNG = 20260812
START = 80000
FLIP_FIELDS = {
    "seed", "arm", "kind", "ply", "t_to_end", "gate_offset", "viruses",
    "maxh", "d_spawn_h", "base_action", "chosen_action", "base_raw_value",
    "chosen_raw_value", "base_value_gap", "base_sensor", "chosen_sensor",
    "base_post_d_spawn_h", "chosen_post_d_spawn_h", "color_hamming",
    "virus_hamming", "link_hamming", "metadata_equal", "matching_cell",
    "champ_rank_chosen", "thin_hash", "res",
}


def load_rows(root):
    rows, errors = {}, []
    for path in sorted(Path(root).glob("seg_*.jsonl")):
        for lineno, line in enumerate(path.open(), 1):
            try:
                row = json.loads(line)
                seed = int(row["seed"])
            except Exception as exc:
                errors.append(f"{path.name}:{lineno}: {exc}"); continue
            if seed in rows:
                errors.append(f"duplicate seed {seed}")
            else:
                rows[seed] = row
    return [rows[s] for s in sorted(rows)], errors


def binary(left, right, rng):
    left, right = np.asarray(left, np.int8), np.asarray(right, np.int8)
    delta = left.astype(float) - right.astype(float); n = len(delta)
    discordant = int(np.count_nonzero(left != right))
    better = int(np.count_nonzero((left == 0) & (right == 1)))
    worse = int(np.count_nonzero((left == 1) & (right == 0)))
    boot = delta[rng.integers(0, n, size=(B, n), dtype=np.int32)].mean(1)
    se = math.sqrt((discordant / n) / n); half = 1.96 * se
    return {
        "difference": float(delta.mean()),
        "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        "discordant": discordant, "left_better": better, "left_worse": worse,
        "mcnemar_exact_p": float(binomtest(better, discordant, .5).pvalue)
        if discordant else 1.0,
        "analytic_se": se, "analytic_halfwidth": half,
        "one_pp_margin_reachable": half <= .01,
    }


def flip_errors(rows):
    errors = []
    for row in rows:
        seed = int(row["seed"])
        for arm in ("base", "treatment", "null"):
            rec = row.get(arm, {}); logs = rec.get("flip_log")
            if int(rec.get("seed", -1)) != seed:
                errors.append(f"{seed} {arm}: inner seed")
            if not isinstance(logs, list):
                errors.append(f"{seed} {arm}: flip_log type"); continue
            if len(logs) != int(rec.get("raw_action_flips", -1)):
                errors.append(f"{seed} {arm}: flip count")
            if arm == "base" and logs:
                errors.append(f"{seed} base: flip")
            for i, flip in enumerate(logs):
                missing = FLIP_FIELDS - set(flip)
                if missing:
                    errors.append(f"{seed} {arm} {i}: missing {sorted(missing)}"); continue
                if int(flip["seed"]) != seed or flip["arm"] != arm:
                    errors.append(f"{seed} {arm} {i}: identity")
                if int(flip["t_to_end"]) != int(rec["n_plies"]) - 1 - int(flip["ply"]):
                    errors.append(f"{seed} {arm} {i}: t_to_end")
                if flip["res"] != rec["res"] or int(flip["base_action"]) == int(flip["chosen_action"]):
                    errors.append(f"{seed} {arm} {i}: result/action")
                total = sum(int(flip[k]) for k in
                            ("color_hamming", "virus_hamming", "link_hamming"))
                if total == 0 and bool(flip["metadata_equal"]):
                    errors.append(f"{seed} {arm} {i}: semantic alias")
                cell = P.matching_cell_from_metrics(
                    total, flip["ply"], flip["base_value_gap"])
                if cell != int(flip["matching_cell"]):
                    errors.append(f"{seed} {arm} {i}: matching cell")
                if arm == "treatment" and not (
                    int(flip["chosen_sensor"]) < int(flip["base_sensor"])):
                    errors.append(f"{seed} treatment {i}: sensor not lower")
    return errors


def no_flip_errors(rows):
    fields = ("res", "won", "topout", "stall", "pills", "dies_ahead",
              "viruses_left", "n_plies", "garbage")
    errors = []
    for row in rows:
        for arm in ("treatment", "null"):
            if row[arm]["raw_action_flips"]:
                continue
            bad = [key for key in fields if row[arm][key] != row["base"][key]]
            if bad:
                errors.append(f"{row['seed']} {arm}: no-flip mismatch {bad}")
    return errors


def transitions(rows, left, right):
    states = ("clear", "topout", "stall")
    return {f"{a}_to_{b}": sum(r[left]["res"] == a and r[right]["res"] == b
                                for r in rows)
            for a in states for b in states}


def churn(rows, arm):
    return {
        "games_with_flip": sum(bool(r[arm]["raw_action_flips"]) for r in rows),
        "result_changed": sum(r[arm]["res"] != r["base"]["res"] for r in rows),
        "result_or_pills_changed": sum(
            r[arm]["res"] != r["base"]["res"]
            or r[arm]["pills"] != r["base"]["pills"] for r in rows),
        "bad_end_changed": sum(
            bool(r[arm]["topout"] or r[arm]["stall"])
            != bool(r["base"]["topout"] or r["base"]["stall"]) for r in rows),
        "dies_ahead_changed": sum(
            r[arm]["dies_ahead"] != r["base"]["dies_ahead"] for r in rows),
    }


def tv(left, right):
    nl, nr = sum(left), sum(right)
    if not nl or not nr:
        return 1.0
    return .5 * sum(abs(a / nl - b / nr) for a, b in zip(left, right))


def distribution(logs):
    h = [sum(int(r[k]) for k in ("color_hamming", "virus_hamming", "link_hamming"))
         for r in logs]
    hc = [0] * 5; tc = [0] * 2; gc = [0] * 4; oc = [0] * 4
    for row, total in zip(logs, h):
        hc[F.h_bin(row)] += 1; tc[F.time_bin(row)] += 1
        gc[F.gap_bin(row)] += 1; oc[int(row["gate_offset"])] += 1
    first = {}
    for row in logs:
        first.setdefault(int(row["seed"]), row)
    first_ply = ([float(np.quantile([r["ply"] for r in first.values()], q))
                  for q in (.1, .5, .9)] if first else [None] * 3)
    return {"hamming": hc, "timing_bin": tc, "value_gap": gc,
            "gate_offset": oc, "first_flip_ply": first_ply}


def decide(complete, null_valid, adequate, bad_tb, bad_tn, da_tb, da_tn):
    if not complete:
        return "PARTIAL_NO_VERDICT"
    if not null_valid:
        return "NULL_INVALID_NO_GO"
    if not adequate:
        return "NOT_DECIDABLE_BADEND_MARGIN"
    go = (da_tb["ci95"][1] < 0 and da_tn["ci95"][1] < 0
          and bad_tb["ci95"][1] < .01 and bad_tn["ci95"][1] < .01)
    return "GO" if go else "NO_GO"


def diagnostic_mutants():
    good = {"ci95": [-.02, -.01], "one_pp_margin_reachable": True}
    safe = {"ci95": [-.005, .005], "one_pp_margin_reachable": True}
    bad = {"ci95": [-.005, .02], "one_pp_margin_reachable": True}
    base = decide(True, True, True, safe, safe, good, good)
    verdict = {
        "go_fixture": base == "GO",
        "dies_base_harm_rejected": decide(True, True, True, safe, safe, bad, good) != "GO",
        "dies_null_harm_rejected": decide(True, True, True, safe, safe, good, bad) != "GO",
        "bad_base_harm_rejected": decide(True, True, True, bad, safe, good, good) != "GO",
        "bad_null_harm_rejected": decide(True, True, True, safe, bad, good, good) != "GO",
        "null_invalid_rejected": decide(True, False, True, safe, safe, good, good) == "NULL_INVALID_NO_GO",
        "adequacy_rejected": decide(True, True, False, safe, safe, good, good) == "NOT_DECIDABLE_BADEND_MARGIN",
    }
    flip = {
        "seed": 1, "arm": "treatment", "kind": "treatment", "ply": 3,
        "t_to_end": 6, "gate_offset": 1, "viruses": 8, "maxh": 10,
        "d_spawn_h": 8, "base_action": 1, "chosen_action": 2,
        "base_raw_value": 100.0, "chosen_raw_value": 76.0,
        "base_value_gap": 24.0, "base_sensor": 12, "chosen_sensor": 10,
        "base_post_d_spawn_h": 12, "chosen_post_d_spawn_h": 10,
        "color_hamming": 4, "virus_hamming": 0, "link_hamming": 4,
        "metadata_equal": True,
        "matching_cell": P.matching_cell_from_metrics(8, 3, 24),
        "champ_rank_chosen": 2, "thin_hash": 17, "res": "clear",
    }
    arm0 = {"seed": 1, "res": "clear", "n_plies": 10,
            "raw_action_flips": 0, "flip_log": [], "won": 1,
            "topout": 0, "stall": 0, "pills": 10, "dies_ahead": 0,
            "viruses_left": -1, "garbage": 2}
    fixture = {"seed": 1, "base": copy.deepcopy(arm0),
               "null": copy.deepcopy(arm0), "treatment": copy.deepcopy(arm0)}
    fixture["treatment"]["raw_action_flips"] = 1
    fixture["treatment"]["flip_log"] = [flip]
    if flip_errors([fixture]) or no_flip_errors([fixture]):
        raise RuntimeError("valid endpoint diagnostic fixture rejected")
    missing = copy.deepcopy(fixture)
    del missing["treatment"]["flip_log"][0]["matching_cell"]
    alias = copy.deepcopy(fixture)
    for key in ("color_hamming", "virus_hamming", "link_hamming"):
        alias["treatment"]["flip_log"][0][key] = 0
    wrong_cell = copy.deepcopy(fixture)
    wrong_cell["treatment"]["flip_log"][0]["matching_cell"] += 1
    identity = copy.deepcopy(fixture)
    identity["null"]["pills"] += 1
    verdict.update({
        "missing_provenance_rejected": bool(flip_errors([missing])),
        "semantic_alias_rejected": bool(flip_errors([alias])),
        "wrong_matching_cell_rejected": bool(flip_errors([wrong_cell])),
        "no_flip_identity_rejected": bool(no_flip_errors([identity])),
        "zero_flip_distribution_rejected": tv([0, 0], [0, 0]) == 1.0,
    })
    return verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(HERE / "out" / "post_garbage_endpoint" / "evaluation"))
    ap.add_argument("--allow-partial", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    mutants = diagnostic_mutants()
    if not all(mutants.values()):
        raise SystemExit("verdict mutant gate failed")
    if args.selftest:
        print(json.dumps({"pass": True, "killed_mutants": mutants}, indent=1)); return
    rows, errors = load_rows(args.root)
    if len(rows) != N and not args.allow_partial:
        raise SystemExit(f"refusing verdict: have {len(rows)}/{N}")
    if not rows or [r["seed"] for r in rows] != list(range(START, START + len(rows))):
        raise SystemExit("rows are not the registered ascending prefix")
    errors += flip_errors(rows) + no_flip_errors(rows)
    if errors:
        raise SystemExit("integrity gate failed: " + json.dumps(errors[:20]))

    arms = ("base", "treatment", "null")
    bad = {a: [int(r[a]["topout"] or r[a]["stall"]) for r in rows] for a in arms}
    da = {a: [int(r[a]["dies_ahead"]) for r in rows] for a in arms}
    rng = np.random.default_rng(RNG)
    bad_tb = binary(bad["treatment"], bad["base"], rng)
    bad_tn = binary(bad["treatment"], bad["null"], rng)
    da_tb = binary(da["treatment"], da["base"], rng)
    da_tn = binary(da["treatment"], da["null"], rng)
    logs = {a: [f for r in rows for f in r[a]["flip_log"]]
            for a in ("treatment", "null")}
    dist = {a: distribution(logs[a]) for a in logs}
    dose = abs(len(logs["treatment"]) / sum(r["treatment"]["plies"] for r in rows)
               - len(logs["null"]) / sum(r["null"]["plies"] for r in rows))
    dose /= max(len(logs["treatment"]) /
                sum(r["treatment"]["plies"] for r in rows), 1e-15)
    tvs = {key: tv(dist["treatment"][key], dist["null"][key])
           for key in ("hamming", "timing_bin", "value_gap", "gate_offset")}
    timing_diff = [
        abs(a - b) if a is not None and b is not None else float("inf")
        for a, b in zip(dist["treatment"]["first_flip_ply"],
                        dist["null"]["first_flip_ply"])]
    null_valid = (len(logs["treatment"]) >= 100 and len(logs["null"]) >= 100
                  and dose <= .10 and all(value <= .10 for value in tvs.values())
                  and timing_diff[0] <= 20 and timing_diff[1] <= 15
                  and timing_diff[2] <= 20)
    adequate = (bad_tb["one_pp_margin_reachable"]
                and bad_tn["one_pp_margin_reachable"])
    complete = len(rows) == N
    verdict = decide(complete, null_valid, adequate, bad_tb, bad_tn, da_tb, da_tn)
    counts = {a: {key: sum(int(r[a][key]) for r in rows)
                  for key in ("won", "topout", "stall", "dies_ahead")}
              for a in arms}
    common = [r for r in rows if r["base"]["won"] and r["treatment"]["won"]]
    pill_delta = np.asarray(
        [r["treatment"]["pills"] - r["base"]["pills"] for r in common],
        dtype=float)
    if len(pill_delta):
        pill_boot = pill_delta[
            rng.integers(0, len(pill_delta), size=(B, len(pill_delta)),
                         dtype=np.int32)].mean(1)
        pills = {"n_common_clears": len(pill_delta),
                 "mean_treatment_minus_base": float(pill_delta.mean()),
                 "ci95": [float(np.percentile(pill_boot, 2.5)),
                           float(np.percentile(pill_boot, 97.5))]}
    else:
        pills = {"n_common_clears": 0, "mean_treatment_minus_base": None,
                 "ci95": None}
    result = {
        "version": "post-garbage-v8-endpoint-result-v1", "verdict": verdict,
        "n_pairs": len(rows), "complete": complete,
        "seeds": [rows[0]["seed"], rows[-1]["seed"]], "counts": counts,
        "null_validity": {"pass": null_valid, "dose_mismatch": dose,
                          "tv": tvs, "first_flip_ply_difference": timing_diff,
                          "treatment_flips": len(logs["treatment"]),
                          "null_flips": len(logs["null"])},
        "bad_end": {"treatment_minus_base": bad_tb,
                    "treatment_minus_null": bad_tn},
        "dies_ahead": {"treatment_minus_base": da_tb,
                       "treatment_minus_null": da_tn},
        "outcome_transitions": {
            "base_to_treatment": transitions(rows, "base", "treatment"),
            "base_to_null": transitions(rows, "base", "null"),
            "null_to_treatment": transitions(rows, "null", "treatment"),
        },
        "churn_vs_base": {"treatment": churn(rows, "treatment"),
                          "null": churn(rows, "null")},
        "pills": pills,
        "mechanism": {a: {
            "landed_cells": sum(int(r[a]["garbage"]) for r in rows),
            "active_plies": sum(int(r[a]["active_plies"]) for r in rows),
            "plies": sum(int(r[a]["plies"]) for r in rows),
            "active_duty": (sum(int(r[a]["active_plies"]) for r in rows)
                            / max(1, sum(int(r[a]["plies"]) for r in rows))),
        } for a in arms},
        "adequacy": {"pass": adequate},
        "provenance": {"integrity_pass": True, "killed_mutants": mutants},
    }
    path = HERE / "out" / "post_garbage_endpoint"
    path.mkdir(parents=True, exist_ok=True)
    out = path / ("result.json" if complete else "partial_result.json")
    out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
