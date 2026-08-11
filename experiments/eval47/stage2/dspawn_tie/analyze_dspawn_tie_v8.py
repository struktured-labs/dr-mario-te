#!/usr/bin/env python3
"""Fail-closed paired analysis for the exact-v8 d_spawn tie arm."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

HERE = Path(__file__).resolve().parent
N_REQUIRED = 9000
B = 5000
RNG = 20260811
FLIP_FIELDS = {
    "seed", "arm", "ply", "t_to_end", "viruses", "maxh", "d_spawn_h",
    "raw_tie_size", "base_action", "treatment_action",
    "base_post_d_spawn_h", "chosen_post_d_spawn_h", "champ_rank_chosen", "res",
}


def load_rows(root):
    by_seed = {}
    errors = []
    for path in sorted(Path(root).glob("seg_*.jsonl")):
        for lineno, line in enumerate(path.open(), 1):
            try:
                row = json.loads(line)
            except Exception as exc:
                errors.append(f"{path.name}:{lineno}: invalid JSON: {exc}")
                continue
            seed = int(row["seed"])
            if seed in by_seed:
                errors.append(f"duplicate seed {seed} at {path.name}:{lineno}")
            else:
                by_seed[seed] = row
    return [by_seed[s] for s in sorted(by_seed)], errors


def binary_contrast(left, right, rng):
    """left-right paired risk difference; negative favors left."""
    left = np.asarray(left, dtype=np.int8)
    right = np.asarray(right, dtype=np.int8)
    d = left.astype(float) - right.astype(float)
    n = len(d)
    discordant = int(np.count_nonzero(left != right))
    l_better = int(np.count_nonzero((left == 0) & (right == 1)))
    l_worse = int(np.count_nonzero((left == 1) & (right == 0)))
    draws = rng.integers(0, n, size=(B, n), dtype=np.int32)
    boot = d[draws].mean(axis=1)
    halfwidth_floor = 1.96 * math.sqrt((discordant / n) / n)
    return {
        "difference": float(d.mean()),
        "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        "discordant": discordant, "left_better": l_better, "left_worse": l_worse,
        "mcnemar_exact_p": float(binomtest(l_better, discordant, 0.5).pvalue)
        if discordant else 1.0,
        "analytic_se": math.sqrt((discordant / n) / n),
        "analytic_halfwidth": halfwidth_floor,
        "one_pp_margin_reachable": bool(halfwidth_floor <= 0.01),
    }


def counts(rows, arm):
    return {name: sum(int(r[arm][key]) for r in rows) for name, key in
            (("clear", "won"), ("topout", "topout"), ("stall", "stall"),
             ("bad_end", "topout"), ("dies_ahead", "dies_ahead"))} | {
        "bad_end": sum(int(r[arm]["topout"] or r[arm]["stall"]) for r in rows)}


def provenance(rows, arm):
    logs = [f for r in rows for f in r[arm].get("flip_log", [])]
    if not logs:
        return {"n": 0}
    t = np.array([f["t_to_end"] for f in logs])
    first = [min((f["ply"] for f in r[arm].get("flip_log", [])), default=None)
             for r in rows]
    first = np.array([x for x in first if x is not None], dtype=int)
    return {
        "n": len(logs), "median_t_to_end": float(np.median(t)),
        "within_last_5": int((t <= 5).sum()), "within_last_15": int((t <= 15).sum()),
        "games_with_flip": int(len(first)),
        "median_first_flip_ply": float(np.median(first)) if len(first) else None,
        "strict_lane_improvements": int(sum(
            f["chosen_post_d_spawn_h"] < f["base_post_d_spawn_h"] for f in logs)),
        "tie_sizes": {str(k): int(sum(f["raw_tie_size"] == k for f in logs))
                      for k in sorted(set(f["raw_tie_size"] for f in logs))},
        "champion_rank_chosen": {
            str(k): int(sum(f["champ_rank_chosen"] == k for f in logs))
            for k in sorted(set(f["champ_rank_chosen"] for f in logs))},
    }


def provenance_errors(rows):
    """Validate the preregistered per-flip contract before any verdict."""
    errors = []
    for row in rows:
        outer_seed = int(row["seed"])
        for arm in ("base", "treatment", "null"):
            rec = row.get(arm, {})
            if int(rec.get("seed", -1)) != outer_seed:
                errors.append(f"seed {outer_seed} {arm}: inner seed mismatch")
            logs = rec.get("flip_log")
            if not isinstance(logs, list):
                errors.append(f"seed {outer_seed} {arm}: flip_log is not a list")
                continue
            if len(logs) != int(rec.get("flips", -1)):
                errors.append(f"seed {outer_seed} {arm}: flips/log length mismatch")
            if arm == "base" and logs:
                errors.append(f"seed {outer_seed} base: unexpected flip provenance")
            for i, flip in enumerate(logs):
                missing = sorted(FLIP_FIELDS - set(flip))
                if missing:
                    errors.append(
                        f"seed {outer_seed} {arm} flip {i}: missing {missing}")
                    continue
                if int(flip["seed"]) != outer_seed or flip["arm"] != arm:
                    errors.append(f"seed {outer_seed} {arm} flip {i}: identity mismatch")
                if int(flip["t_to_end"]) != int(rec["n_plies"]) - 1 - int(flip["ply"]):
                    errors.append(f"seed {outer_seed} {arm} flip {i}: bad t_to_end")
                if flip["res"] != rec["res"]:
                    errors.append(f"seed {outer_seed} {arm} flip {i}: result mismatch")
                if int(flip["raw_tie_size"]) < 2:
                    errors.append(f"seed {outer_seed} {arm} flip {i}: not a raw tie")
                if int(flip["base_action"]) == int(flip["treatment_action"]):
                    errors.append(f"seed {outer_seed} {arm} flip {i}: unchanged action")
                if arm == "treatment" and not (
                    int(flip["chosen_post_d_spawn_h"])
                    < int(flip["base_post_d_spawn_h"])
                ):
                    errors.append(f"seed {outer_seed} treatment flip {i}: sensor not lower")
    return errors


def diagnostic_mutants():
    """Positive controls: each integrity direction rejects a wrong record."""
    import copy
    template = {
        "seed": 1,
        "base": {"seed": 1, "res": "clear", "n_plies": 10,
                 "flips": 0, "flip_log": [], "won": 1, "topout": 0,
                 "stall": 0, "pills": 10, "dies_ahead": 0,
                 "viruses_left": -1, "garbage": 2},
        "null": {"seed": 1, "res": "clear", "n_plies": 10,
                 "flips": 0, "flip_log": [], "won": 1, "topout": 0,
                 "stall": 0, "pills": 10, "dies_ahead": 0,
                 "viruses_left": -1, "garbage": 2},
        "treatment": {"seed": 1, "res": "clear", "n_plies": 10,
                      "flips": 1, "flip_log": [], "won": 1, "topout": 0,
                      "stall": 0, "pills": 10, "dies_ahead": 0,
                      "viruses_left": -1, "garbage": 2},
    }
    template["treatment"]["flip_log"] = [{
                          "seed": 1, "arm": "treatment", "ply": 3,
                          "t_to_end": 6, "viruses": 8, "maxh": 10,
                          "d_spawn_h": 8, "raw_tie_size": 2,
                          "base_action": 1, "treatment_action": 2,
                          "base_post_d_spawn_h": 9,
                          "chosen_post_d_spawn_h": 8,
                          "champ_rank_chosen": 2, "res": "clear",
                      }]
    if provenance_errors([template]):
        raise RuntimeError("valid diagnostic fixture rejected")
    missing = copy.deepcopy(template)
    del missing["treatment"]["flip_log"][0]["t_to_end"]
    inverted = copy.deepcopy(template)
    inverted["treatment"]["flip_log"][0]["chosen_post_d_spawn_h"] = 10
    count = copy.deepcopy(template)
    count["treatment"]["flips"] = 2
    identity = copy.deepcopy(template)
    identity["null"]["pills"] = 11
    return {
        "missing_field_rejected": bool(provenance_errors([missing])),
        "non_improving_treatment_rejected": bool(provenance_errors([inverted])),
        "flip_count_mismatch_rejected": bool(provenance_errors([count])),
        "no_flip_identity_mismatch_rejected": bool(no_flip_identity_errors([identity])),
    }


def no_flip_identity_errors(rows):
    """A deterministic arm that never intervened must equal base exactly."""
    errors = []
    fields = ("res", "won", "topout", "stall", "pills", "dies_ahead",
              "viruses_left", "n_plies", "garbage")
    for row in rows:
        for arm in ("treatment", "null"):
            if int(row[arm]["flips"]) != 0:
                continue
            bad = [key for key in fields if row[arm][key] != row["base"][key]]
            if bad:
                errors.append(f"seed {row['seed']} {arm}: no-flip mismatch {bad}")
    return errors


def first_divergence(rows, arm):
    """Derive the first-divergence marker omitted from the raw v1 schema."""
    first = []
    transitions = {}
    for row in rows:
        logs = row[arm].get("flip_log", [])
        if not logs:
            continue
        f = min(logs, key=lambda x: int(x["ply"]))
        first.append(f)
        key = f"{row['base']['res']}_to_{row[arm]['res']}"
        transitions[key] = transitions.get(key, 0) + 1
    if not first:
        return {"n": 0}
    drop = np.array([int(f["base_post_d_spawn_h"])
                     - int(f["chosen_post_d_spawn_h"]) for f in first])
    return {
        "n": len(first),
        "derived_marker": "minimum logged ply within each arm trajectory",
        "median_ply": float(np.median([f["ply"] for f in first])),
        "median_t_to_end": float(np.median([f["t_to_end"] for f in first])),
        "median_sensor_drop": float(np.median(drop)),
        "sensor_drop": {str(k): int((drop == k).sum()) for k in sorted(set(drop))},
        "champion_rank_chosen": {
            str(k): int(sum(int(f["champ_rank_chosen"]) == k for f in first))
            for k in sorted(set(int(f["champ_rank_chosen"]) for f in first))},
        "base_to_arm_outcomes": transitions,
    }


def outcome_transitions(rows, left, right):
    states = ("clear", "topout", "stall")
    return {
        f"{a}_to_{b}": int(sum(r[left]["res"] == a and r[right]["res"] == b
                               for r in rows))
        for a in states for b in states
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(HERE / "out" / "evaluation"))
    ap.add_argument("--allow-partial", action="store_true")
    args = ap.parse_args()
    rows, load_errors = load_rows(args.root)
    if len(rows) != N_REQUIRED and not args.allow_partial:
        raise SystemExit(f"refusing verdict: have {len(rows)}/{N_REQUIRED} paired seeds")
    if not rows:
        raise SystemExit("no rows")
    expected = list(range(61000, 61000 + len(rows)))
    seeds = [r["seed"] for r in rows]
    prefix_exact = seeds == expected
    if not prefix_exact:
        raise SystemExit("rows are not the registered ascending seed prefix")
    prov_errors = provenance_errors(rows)
    identity_errors = no_flip_identity_errors(rows)
    mutants = diagnostic_mutants()
    if not all(mutants.values()):
        raise SystemExit("diagnostic killed-mutant gate failed")
    if load_errors or prov_errors or identity_errors:
        raise SystemExit("provenance gate failed: " + json.dumps(
            {"load_errors": load_errors[:10], "provenance_errors": prov_errors[:10],
             "no_flip_identity_errors": identity_errors[:10]}))

    arms = ("base", "treatment", "null")
    bad = {a: np.array([int(r[a]["topout"] or r[a]["stall"]) for r in rows])
           for a in arms}
    da = {a: np.array([r[a]["dies_ahead"] for r in rows]) for a in arms}
    rng = np.random.default_rng(RNG)
    bad_tb = binary_contrast(bad["treatment"], bad["base"], rng)
    bad_tn = binary_contrast(bad["treatment"], bad["null"], rng)
    da_tb = binary_contrast(da["treatment"], da["base"], rng)
    da_tn = binary_contrast(da["treatment"], da["null"], rng)

    flips_t = sum(r["treatment"]["flips"] for r in rows)
    flips_n = sum(r["null"]["flips"] for r in rows)
    plies_t = sum(r["treatment"]["plies"] for r in rows)
    plies_n = sum(r["null"]["plies"] for r in rows)
    dose_t, dose_n = flips_t / plies_t, flips_n / plies_n
    dose_rel = abs(dose_t - dose_n) / max(dose_t, 1e-15)
    dose_ok = dose_rel <= 0.10

    common = [r for r in rows if r["base"]["won"] and r["treatment"]["won"]]
    pd = np.array([r["treatment"]["pills"] - r["base"]["pills"]
                   for r in common], dtype=float)
    pboot = []
    if len(pd):
        for _ in range(B):
            pboot.append(pd[rng.integers(0, len(pd), len(pd))].mean())
    pills = {"n_common_clears": len(pd), "mean_treatment_minus_base":
             float(pd.mean()) if len(pd) else None,
             "ci95": [float(np.percentile(pboot, 2.5)),
                       float(np.percentile(pboot, 97.5))] if pboot else None}

    complete = len(rows) == N_REQUIRED
    adequate = bad_tb["one_pp_margin_reachable"]
    go = (complete and dose_ok and adequate and bad_tb["ci95"][1] < 0
          and bad_tn["ci95"][1] < 0)
    if not complete:
        verdict = "PARTIAL_NO_VERDICT"
    elif not dose_ok:
        verdict = "VOID_DOSE_MISMATCH"
    elif not adequate:
        verdict = "NOT_DECIDABLE_BADEND_MARGIN"
    else:
        verdict = "GO" if go else "NO_GO"

    result = {
        "version": "dspawn-tie-v8-result-v1", "verdict": verdict,
        "n_pairs": len(rows), "seed_min": min(seeds), "seed_max": max(seeds),
        "complete": complete, "prefix_exact": prefix_exact,
        "counts": {a: counts(rows, a) for a in arms},
        "outcome_transitions": {
            "base_to_treatment": outcome_transitions(rows, "base", "treatment"),
            "base_to_null": outcome_transitions(rows, "base", "null"),
            "null_to_treatment": outcome_transitions(rows, "null", "treatment"),
        },
        "dose": {"treatment_flips": flips_t, "treatment_plies": plies_t,
                 "treatment_rate": dose_t, "null_flips": flips_n,
                 "null_plies": plies_n, "null_rate": dose_n,
                 "relative_mismatch": dose_rel, "gate_le_10pct": dose_ok},
        "bad_end": {"treatment_minus_base": bad_tb,
                    "treatment_minus_null_DiD": bad_tn},
        "dies_ahead": {"treatment_minus_base": da_tb,
                       "treatment_minus_null_DiD": da_tn},
        "pills": pills,
        "provenance": {"treatment": provenance(rows, "treatment"),
                       "null": provenance(rows, "null"),
                       "first_divergence": {
                           "treatment": first_divergence(rows, "treatment"),
                           "null": first_divergence(rows, "null")},
                       "no_flip_identity_pass": True,
                       "integrity_pass": True,
                       "killed_mutants": mutants},
        "note": ("topout and 300-pill stall both score as bad ends; exogenous Lulu "
                 "offers are policy-independent; p2_surrogate is not a live NAV_T claim"),
    }
    out = HERE / "out" / ("result.json" if complete else "partial_result.json")
    out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
