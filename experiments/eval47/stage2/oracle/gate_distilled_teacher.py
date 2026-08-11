#!/usr/bin/env python3
"""Fail-closed E0 dose gate and exploratory endpoint display."""
from __future__ import annotations

import argparse
import copy
import json
import os

EXPECTED_POLICY_SHA = "9ae58f0d9c0d69dfc3d781fbca16b126bed254517589a7ae8a1d6312b10b9b32"


def load_rows(outdir):
    by_seed = {}
    for fn in sorted(os.listdir(outdir)):
        if not (fn.startswith("seg_") and fn.endswith(".jsonl")):
            continue
        for line in open(os.path.join(outdir, fn)):
            row = json.loads(line)
            seed = int(row["seed"])
            if seed in by_seed:
                raise RuntimeError(f"duplicate seed {seed}")
            by_seed[seed] = row
    return [by_seed[s] for s in sorted(by_seed)]


def metrics(rows):
    n = len(rows)
    out = {"n": n, "arms": {}}
    for arm in ("base", "true", "null"):
        plies = sum(r[arm]["plies_scored"] for r in rows)
        flips = sum(r[arm]["flips"] for r in rows)
        out["arms"][arm] = {
            "plies": plies, "flips": flips,
            "flip_rate": flips / max(1, plies),
            "garbage_per_ply": sum(r[arm]["garbage"] for r in rows)
                               / max(1, plies),
            "forks": sum(r[arm]["forks"] for r in rows),
            "provenance": sum(len(r[arm].get("flip_log", [])) for r in rows),
        }
    return out


def gates(m, policy_sha):
    a = m["arms"]
    tr, nu = a["true"], a["null"]
    dose_count = tr["flips"] / max(1, nu["flips"])
    dose_rate = tr["flip_rate"] / max(1e-12, nu["flip_rate"])
    pressure = tr["garbage_per_ply"] / max(1e-12, nu["garbage_per_ply"])
    checks = {
        "registered_complete_block": m["n"] == 60,
        "policy_hash": policy_sha == EXPECTED_POLICY_SHA,
        "zero_forks": all(a[x]["forks"] == 0 for x in a),
        "activity": tr["flips"] > 0 and nu["flips"] > 0,
        "provenance_complete": (tr["provenance"] == tr["flips"]
                                and nu["provenance"] == nu["flips"]),
        "churn_ceiling": (tr["flip_rate"] <= 0.15
                          and nu["flip_rate"] <= 0.15),
        "dose_count_ratio": 0.80 <= dose_count <= 1.25,
        "dose_rate_ratio": 0.80 <= dose_rate <= 1.25,
        "pressure_sanity": 0.80 <= pressure <= 1.25,
    }
    return checks, {"flip_count_ratio": dose_count,
                    "flip_rate_ratio": dose_rate,
                    "garbage_per_ply_ratio": pressure}


def endpoint(rows):
    n = len(rows)
    keys = ("won", "topout", "stall", "dies_ahead")
    rates = {}
    for arm in ("base", "true", "null"):
        rates[arm] = {k: sum(r[arm][k] for r in rows) / n for k in keys}
        rates[arm]["bad_end"] = sum(
            bool(r[arm]["topout"] or r[arm]["stall"]) for r in rows) / n

    def transitions(left, right, key):
        def value(r, arm):
            if key == "bad_end":
                return int(r[arm]["topout"] or r[arm]["stall"])
            return int(r[arm][key])
        return {
            "0_to_1": sum(value(r, left) == 0 and value(r, right) == 1
                          for r in rows),
            "1_to_0": sum(value(r, left) == 1 and value(r, right) == 0
                          for r in rows),
        }

    trans = {arm: {k: transitions("base", arm, k)
                   for k in ("bad_end", "won", "dies_ahead", "topout", "stall")}
             for arm in ("true", "null")}
    trans["topout_stall"] = {
        arm: {
            "topout_to_stall": sum(r["base"]["topout"] and r[arm]["stall"]
                                   for r in rows),
            "stall_to_topout": sum(r["base"]["stall"] and r[arm]["topout"]
                                   for r in rows),
        } for arm in ("true", "null")}
    did_bad = ((rates["true"]["bad_end"] - rates["base"]["bad_end"])
               - (rates["null"]["bad_end"] - rates["base"]["bad_end"]))
    nomination = {
        "true_bad_end_nonincrease": (rates["true"]["bad_end"]
                                     <= rates["base"]["bad_end"]),
        "true_clear_floor": rates["true"]["won"] >= rates["base"]["won"] - 2/n,
        "bad_end_DiD_at_most_minus_1_over_60": did_bad <= -1/60,
    }
    return {"rates": rates, "paired_transitions": trans,
            "effects": {
                "true_minus_base_bad_end": rates["true"]["bad_end"] - rates["base"]["bad_end"],
                "null_minus_base_bad_end": rates["null"]["bad_end"] - rates["base"]["bad_end"],
                "true_minus_null_bad_end_DiD": did_bad,
                "true_minus_base_clear": rates["true"]["won"] - rates["base"]["won"],
                "null_minus_base_clear": rates["null"]["won"] - rates["base"]["won"],
            },
            "nomination_checks": nomination,
            "nominate_larger_run": all(nomination.values())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    rows = load_rows(a.outdir)
    meta = json.load(open(os.path.join(a.outdir, "META.json")))
    m = metrics(rows)
    checks, ratios = gates(m, meta.get("policy_sha256", ""))

    # Killed mutants: each must turn its named green gate red.
    high = copy.deepcopy(m)
    high["arms"]["true"]["flip_rate"] = 0.150001
    high_checks, _ = gates(high, EXPECTED_POLICY_SHA)
    dose = copy.deepcopy(m)
    dose["arms"]["true"]["flips"] = max(1, int(
        dose["arms"]["null"]["flips"] * 0.50))
    dose["arms"]["true"]["flip_rate"] = (
        dose["arms"]["true"]["flips"] / max(1, dose["arms"]["true"]["plies"]))
    dose_checks, _ = gates(dose, EXPECTED_POLICY_SHA)
    mutants = {
        "high_churn_rejected": not high_checks["churn_ceiling"],
        "low_count_dose_rejected": not dose_checks["dose_count_ratio"],
        "low_rate_dose_rejected": not dose_checks["dose_rate_ratio"],
        "wrong_policy_hash_rejected": not gates(m, "WRONG")[0]["policy_hash"],
    }
    valid = all(checks.values()) and all(mutants.values())
    result = {"authority": "E0_IMPLEMENTATION_AND_DOSE_ONLY",
              "metrics_before_endpoints": m, "ratios": ratios,
              "gates": checks, "killed_mutants": mutants,
              "e0_valid": valid,
              "endpoint": endpoint(rows) if valid else
              "VOID_NOT_DISPLAYED_BECAUSE_E0_GATE_FAILED"}
    print(json.dumps(result, indent=1))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(result, f, indent=1)
    raise SystemExit(0 if valid else 1)


if __name__ == "__main__":
    main()

