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


def null_readout(rows, path, fl, pl):
    """Paired read-out of a label-blind null arm against the SAME base rows."""
    sh, nver, nmis = {}, 0, 0
    for ln in open(path):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        sh[r["seed"]] = r
    by = {r["seed"]: r for r in rows}
    common = sorted(set(sh) & set(by))
    for s in common:
        if "base_recheck" in sh[s]:
            nver += 1
            b, g = by[s]["base"], sh[s]["base_recheck"]
            if any(b[k] != g[k] for k in ("res", "pills", "garbage", "dies_ahead")):
                nmis += 1
    g = lambda k, w: np.array([(by[s][w][k] if w != "shuf" else sh[s]["shuf"][k])
                               for s in common], dtype=float)
    db, dt, ds = g("dies_ahead", "base"), g("dies_ahead", "trt"), g("dies_ahead", "shuf")
    cb, ct, cs = g("won", "base"), g("won", "trt"), g("won", "shuf")
    flS = np.array([sh[s]["shuf"]["flips"] for s in common], dtype=float)
    plS = np.array([sh[s]["shuf"]["plies_scored"] for s in common], dtype=float)
    lo_f, hi_f, _, _ = A.boot_paired(dt - db)
    lo_s, hi_s, _, _ = A.boot_paired(ds - db)
    lo_d, hi_d, fneg, _ = A.boot_paired(dt - ds)
    lo_cf, hi_cf, _, _ = A.boot_paired(ct - cb)
    lo_cs, hi_cs, _, _ = A.boot_paired(cs - cb)
    fit_flip = float(fl.sum() / pl.sum())
    null_flip = float(flS.sum() / plS.sum())
    r = {"n_common": len(common), "base_recheck_n": nver,
         "base_recheck_mismatch": nmis,
         "null_ply_flip_rate": null_flip, "fitted_ply_flip_rate": fit_flip,
         "flip_ratio_null_over_fitted": null_flip / max(1e-9, fit_flip),
         "da_base": float(db.mean()),
         "da_fitted": float(dt.mean()), "da_fitted_diff": float((dt - db).mean()),
         "da_fitted_ci": [lo_f, hi_f],
         "da_null": float(ds.mean()), "da_null_diff": float((ds - db).mean()),
         "da_null_ci": [lo_s, hi_s],
         "did_fitted_minus_null": float((dt - ds).mean()), "did_ci95": [lo_d, hi_d],
         "did_frac_boot_neg": fneg,
         "clear_base": float(cb.mean()),
         "clear_fitted_diff": float((ct - cb).mean()), "clear_fitted_ci": [lo_cf, hi_cf],
         "clear_null_diff": float((cs - cb).mean()), "clear_null_ci": [lo_cs, hi_cs],
         "clear_discordant_null": int((cb != cs).sum()),
         "clear_discordant_fitted": int((cb != ct).sum())}
    matched = 0.75 <= r["flip_ratio_null_over_fitted"] <= 1.33
    r["dose_matched"] = bool(matched)
    if not matched:
        r["bias_note"] = (
            f"NOT DOSE-MATCHED: the null flips {null_flip*100:.2f}% of plies vs "
            f"the fitted arm's {fit_flip*100:.2f}% "
            f"({r['flip_ratio_null_over_fitted']:.1f}x). A more aggressive "
            f"perturbation does more damage, so the difference-in-differences is "
            f"BIASED IN FAVOUR OF THE FITTED ARM and is an UPPER bound on its "
            f"advantage over a null.")
    else:
        r["bias_note"] = (
            f"DOSE-MATCHED: null flips {null_flip*100:.2f}% vs fitted "
            f"{fit_flip*100:.2f}% of plies. The DiD is a fair comparison.")
    if hi_d >= 0:
        r["readout"] = ("NOT SEPARATED: the difference-in-differences CI includes "
                        "0 - the fitted term's rollout dies-ahead movement is not "
                        "distinguishable from a label-blind perturbation of the "
                        "same size.")
    else:
        r["readout"] = ("SEPARATED: the fitted arm's dies-ahead movement is better "
                        "than the label-blind null's by "
                        f"{-r['did_fitted_minus_null']*100:.2f}pp "
                        f"[{-hi_d*100:.2f},{-lo_d*100:.2f}] - the term carries "
                        "directional signal in rollout, though NOT enough to clear "
                        "the pre-registered gates against the champion. The verdict "
                        "remains NO_GO.")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lulu", required=True)
    ap.add_argument("--ctrl")
    ap.add_argument("--ctrl-matched", dest="ctrl_matched")
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
    res["null_controls"] = {}
    for label, path in (("value_matched_k1", a.ctrl),
                        ("dose_matched_k0.2", a.ctrl_matched)):
        if not path or not os.path.exists(path):
            continue
        res["null_controls"][label] = null_readout(rows, path, fl, pl)
    json.dump(res, open(a.out, "w"), indent=1, default=float)
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
