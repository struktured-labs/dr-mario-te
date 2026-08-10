#!/usr/bin/env python3
"""Secondary read-outs that need no new compute: harness consistency vs the
census, outcome churn, achieved power, and the null-control difference-in-
differences.  No verdict authority - the verdict is in analyse.py.
"""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyse as A  # noqa: E402

CENSUS = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/jointdig/results_hetzner/lulu_census.jsonl"


def census_stats():
    n = c = t = s = da = 0
    seen = set()
    for ln in open(CENSUS):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r["seed"] in seen:
            continue
        seen.add(r["seed"])
        n += 1
        c += int(r["res"] == "clear")
        t += int(r["res"] == "topout")
        s += int(r["res"] == "stall")
        da += int(r.get("dies_ahead", 0))
    return {"n": n, "clear": c / n, "topout": t / n, "stall": s / n,
            "dies_ahead": da / n}


def needed_n(b01, b10, n):
    """N at which |b01-b10| would reach 1.96*sqrt(b01+b10), holding rates."""
    d, m = abs(b01 - b10), b01 + b10
    if d == 0 or m == 0:
        return None
    # d scales with N, sqrt(m) with sqrt(N)  ->  need k such that k*d = 1.96*sqrt(k*m)
    k = (1.96 ** 2) * m / (d ** 2)
    return int(math.ceil(k * n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lulu", required=True)
    ap.add_argument("--ctrl")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = A.load(a.lulu)
    n = len(rows)
    res = {"n_pairs": n}

    # --- harness consistency: the BASE arm vs the 12,000-seed census --------
    cs = census_stats()
    base = {k: float(A.arr(rows, "base", v).mean())
            for k, v in (("clear", "won"), ("topout", "topout"),
                         ("stall", "stall"), ("dies_ahead", "dies_ahead"))}
    cons = {}
    for k in ("clear", "topout", "stall", "dies_ahead"):
        x = A.arr(rows, "base", {"clear": "won"}.get(k, k))
        lo, hi = A.boot_rate(x)
        cons[k] = {"census_2..12001": cs[k], "base_20000..22999": base[k],
                   "base_ci95": [lo, hi],
                   "census_inside_base_ci": bool(lo <= cs[k] <= hi)}
    res["harness_consistency_vs_census"] = cons
    res["census_n"] = cs["n"]

    # --- churn --------------------------------------------------------------
    cb = A.arr(rows, "base", "won").astype(int)
    ct = A.arr(rows, "trt", "won").astype(int)
    db = A.arr(rows, "base", "dies_ahead").astype(int)
    dt = A.arr(rows, "trt", "dies_ahead").astype(int)
    fl = np.array([r["trt"].get("flips", 0) for r in rows])
    pl = np.array([r["trt"].get("plies_scored", 0) for r in rows])
    ident = np.array([r["base"]["res"] == r["trt"]["res"]
                      and r["base"]["pills"] == r["trt"]["pills"] for r in rows])
    res["churn"] = {
        "ply_flip_rate": float(fl.sum() / pl.sum()),
        "games_with_>=1_flip": int((fl > 0).sum()),
        "games_identical_outcome_and_pills": int(ident.sum()),
        "discordant_clear_pairs": int((cb != ct).sum()),
        "discordant_da_pairs": int((db != dt).sum()),
        "clear_outcome_churn_per_ply_flip":
            float((cb != ct).sum() / max(1, fl.sum())),
        "note": ("a 1.8% per-ply flip rate reshuffles ~20% of GAME outcomes; "
                 "the rig is chaotic in the action sequence, so ANY perturbation "
                 "of this size carries this much variance"),
    }

    # --- achieved power ------------------------------------------------------
    b01 = int(((db == 0) & (dt == 1)).sum())
    b10 = int(((db == 1) & (dt == 0)).sum())
    c01 = int(((cb == 0) & (ct == 1)).sum())
    c10 = int(((cb == 1) & (ct == 0)).sum())
    m = A.summarise(rows, "lulu")["metrics"]
    half = (m["clear"]["diff_ci95"][1] - m["clear"]["diff_ci95"][0]) / 2
    res["power"] = {
        "da_discordant": b01 + b10, "da_net": b10 - b01,
        "n_for_da_mcnemar_p05_at_this_effect": needed_n(b01, b10, n),
        "clear_discordant": c01 + c10,
        "clear_ci_halfwidth_pp": half * 100,
        "n_for_clear_noninferiority_at_this_point_estimate":
            (int(math.ceil(n * (half / (0.01 + m["clear"]["diff_trt_minus_base"]))
                           ** 2))
             if (0.01 + m["clear"]["diff_trt_minus_base"]) > 0 else None),
        "note": ("power arithmetic at the OBSERVED point estimates. It says what "
                 "N the pre-registered gates would have needed; it does NOT say "
                 "the effect is real. The verdict is NO_GO and is not re-opened.")}

    # --- dies-ahead among games the term actually touched --------------------
    touched = fl > 0
    res["da_among_touched_games"] = {
        "n": int(touched.sum()),
        "base": float(db[touched].mean()), "trt": float(dt[touched].mean()),
        "diff": float((dt[touched] - db[touched]).mean())}
    res["da_among_untouched_games"] = {
        "n": int((~touched).sum()),
        "base": float(db[~touched].mean()), "trt": float(dt[~touched].mean()),
        "diff": float((dt[~touched] - db[~touched]).mean()),
        "must_be_zero": bool((dt[~touched] == db[~touched]).all())}

    # --- SCALE-MATCHED NULL CONTROL -----------------------------------------
    if a.ctrl and os.path.exists(a.ctrl):
        sh = {}
        vchecks = {"n": 0, "mismatch": 0}
        for ln in open(a.ctrl):
            try:
                r = json.loads(ln)
            except Exception:
                continue
            sh[r["seed"]] = r
            if "base_recheck" in r:
                vchecks["n"] += 1
        by = {r["seed"]: r for r in rows}
        common = sorted(set(sh) & set(by))
        for s in common:
            if "base_recheck" in sh[s]:
                b = by[s]["base"]
                g = sh[s]["base_recheck"]
                if any(b[k] != g[k] for k in ("res", "pills", "garbage",
                                              "dies_ahead")):
                    vchecks["mismatch"] += 1
        db_c = np.array([by[s]["base"]["dies_ahead"] for s in common])
        dt_c = np.array([by[s]["trt"]["dies_ahead"] for s in common])
        ds_c = np.array([sh[s]["shuf"]["dies_ahead"] for s in common])
        cb_c = np.array([by[s]["base"]["won"] for s in common])
        ct_c = np.array([by[s]["trt"]["won"] for s in common])
        cs_c = np.array([sh[s]["shuf"]["won"] for s in common])
        flS = np.array([sh[s]["shuf"]["flips"] for s in common])
        plS = np.array([sh[s]["shuf"]["plies_scored"] for s in common])
        lo_f, hi_f, _, _ = A.boot_paired((dt_c - db_c).astype(float))
        lo_s, hi_s, _, _ = A.boot_paired((ds_c - db_c).astype(float))
        lo_d, hi_d, fneg, _ = A.boot_paired((dt_c - ds_c).astype(float))
        lo_cf, hi_cf, _, _ = A.boot_paired((ct_c - cb_c).astype(float))
        lo_cs, hi_cs, _, _ = A.boot_paired((cs_c - cb_c).astype(float))
        res["null_control"] = {
            "n_common": len(common),
            "base_recheck_n": vchecks["n"],
            "base_recheck_mismatch": vchecks["mismatch"],
            "shuf_ply_flip_rate": float(flS.sum() / plS.sum()),
            "fitted_ply_flip_rate": float(fl.sum() / pl.sum()),
            "da_base": float(db_c.mean()),
            "da_fitted": float(dt_c.mean()), "da_fitted_diff": float((dt_c - db_c).mean()),
            "da_fitted_ci": [lo_f, hi_f],
            "da_shuffled": float(ds_c.mean()),
            "da_shuffled_diff": float((ds_c - db_c).mean()),
            "da_shuffled_ci": [lo_s, hi_s],
            "did_fitted_minus_shuffled": float((dt_c - ds_c).mean()),
            "did_ci95": [lo_d, hi_d],
            "did_frac_boot_neg": fneg,
            "clear_base": float(cb_c.mean()),
            "clear_fitted_diff": float((ct_c - cb_c).mean()),
            "clear_fitted_ci": [lo_cf, hi_cf],
            "clear_shuffled_diff": float((cs_c - cb_c).mean()),
            "clear_shuffled_ci": [lo_cs, hi_cs],
            "clear_discordant_shuffled": int((cb_c != cs_c).sum()),
            "clear_discordant_fitted": int((cb_c != ct_c).sum()),
            "readout": None}
        r = res["null_control"]
        if abs(r["da_shuffled_diff"] - r["da_fitted_diff"]) < 0.01 or hi_d > 0:
            r["readout"] = ("NOT DISTINGUISHABLE: the label-blind shuffled arm "
                            "moves dies-ahead comparably to the fitted arm, so "
                            "the rollout effect is the PERTURBATION, not the "
                            "TERM. The offline AUC edge did not transfer.")
        else:
            r["readout"] = ("DISTINGUISHABLE: the fitted arm beats the "
                            "scale-matched null on dies-ahead. The term carries "
                            "directional signal that N=3,000 could not resolve "
                            "against the champion, but the verdict remains NO_GO.")

    json.dump(res, open(a.out, "w"), indent=1, default=float)
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
