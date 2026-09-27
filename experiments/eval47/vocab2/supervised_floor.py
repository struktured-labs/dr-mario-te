#!/usr/bin/env python3
"""#84 supervised floor: does LEARNING add anything beyond un-clipping the spawn sensor?

Endpoints, split, arms and controls are pre-registered in PREREG_SUPERVISED_FLOOR.md,
committed before this ran. This file executes that plan.

Reuses feature_battery.py's own make_contrast / stratified_auc_machinery / boot_weights
UNCHANGED, so the floor is measured on the instrument that produced 0.9002 / 0.9290.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import feature_battery as FB   # noqa: E402
from sklearn.linear_model import LogisticRegression        # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.preprocessing import StandardScaler            # noqa: E402
from sklearn.pipeline import make_pipeline                  # noqa: E402

RNG = 20260809
B_BOOT = 200
HOLDOUT_MOD = (7, 8, 9)     # seed % 10 in here -> holdout


def auc_on(strata, isf, score):
    return FB.stratified_auc_machinery(strata, score, isf)(np.ones(len(isf)))[0]


def paired_boot_diff(strata, isf, seeds, s_a, s_b, rng, B=B_BOOT):
    """Bootstrap the AUC difference (a - b) resampling SEEDS, so correlated decisions from
    one game move together -- the same reason the split is by game."""
    ma = FB.stratified_auc_machinery(strata, s_a, isf)
    mb = FB.stratified_auc_machinery(strata, s_b, isf)
    d = []
    for _ in range(B):
        w = FB.boot_weights(seeds, isf, rng)
        a, _ = ma(w)
        b, _ = mb(w)
        if np.isfinite(a) and np.isfinite(b):
            d.append(a - b)
    d = np.array(d)
    return float(np.mean(d)), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def rank_metrics(isf, score):
    """Rank agreement with the outcome, not just AUC.

    Top-DECILE lift is useless here: the contrast is 41% positive, so any arm that gets its
    top 10% right saturates at 1/0.41 = 2.42 and every arm ties. Reported instead: Spearman,
    top-1% lift (headroom left), and partial AUC restricted to FPR <= 0.10 -- the region that
    decides whether an evaluator orders the EXTREMES correctly, which is what matters near an
    absorbing state."""
    from scipy.stats import spearmanr
    rho = float(spearmanr(score, isf.astype(float)).statistic)
    k = max(1, int(0.01 * len(score)))
    top = np.argsort(-score)[:k]
    lift1 = float(isf[top].mean() / isf.mean())
    o = np.argsort(-score)
    y = isf[o].astype(float)
    npos, nneg = y.sum(), (1 - y).sum()
    tpr = np.cumsum(y) / npos
    fpr = np.cumsum(1 - y) / nneg
    m = fpr <= 0.10
    pauc = float(np.trapezoid(tpr[m], fpr[m]) / 0.10) if m.sum() > 1 else float("nan")
    return rho, lift1, pauc


def main():
    fat, ctl, featF, featC = FB.load_all_features()
    names11 = list(FB.NAMES11)
    cands = list(FB.CAND_NAMES)
    # ★ THE CHAMPION'S ACTUAL EVALUATOR, not a proxy. `cand_vals[i, action[i]]` is the
    # hand-tuned eval's own value for the placement it chose. The battery's baseline was
    # SPAWN alone -- correct for ITS question (best single EXISTING feature vs a new
    # candidate) but WRONG for this one: the task asks whether a learned evaluator beats the
    # HAND-TUNED EVALUATOR, and that evaluator is a weighted combination, not one term.
    # Comparing a fitted combination against a single term would flatter the learned model.
    fm = fat["outcome"] == 1
    featF = dict(featF); featC = dict(featC)
    featF["CHAMP_EVAL"] = fat["cand_vals"][np.arange(len(fat["action"])), fat["action"]]
    featC["CHAMP_EVAL"] = ctl["cand_vals"][np.arange(len(ctl["action"])), ctl["action"]]
    con = FB.make_contrast(fat, ctl, featF, featC, fm)
    strata, isf, seeds = con["strata"], con["isf"], con["seeds"]
    X = con["X"]
    allnames = names11 + cands + ["CHAMP_EVAL"]
    M = np.column_stack([X[n] for n in allnames])
    print("contrast: %d fatal / %d control decisions, %d features"
          % (con["n_fatal"], con["n_ctrl"], M.shape[1]), flush=True)

    hold = np.isin(seeds % 10, HOLDOUT_MOD)
    tr = ~hold
    assert not (set(np.unique(seeds[tr])) & set(np.unique(seeds[hold]))), "SEED LEAK"
    print("split by GAME: %d train decisions (%d seeds) / %d holdout (%d seeds); disjoint OK"
          % (tr.sum(), len(np.unique(seeds[tr])), hold.sum(), len(np.unique(seeds[hold]))),
          flush=True)

    # SIGN ORIENTATION, fit on TRAIN only. PREF_SIGN covers the 11 hand features but NOT the
    # candidate features, so a .get(default) silently inverted d_spawn_h on the first run
    # (AUC 0.0993 = 1 - 0.9007). Orientation is one bit; fit it on TRAIN like any other
    # parameter and apply it unchanged to the holdout. Never orient on the holdout.
    def single(name):
        v = X[name].astype(np.float64)
        a_tr = auc_on(strata[tr], isf[tr], v[tr])
        sgn = 1.0 if a_tr >= 0.5 else -1.0
        return sgn * v

    def fit(cols, kind):
        idx = [allnames.index(c) for c in cols]
        Xtr, Xho = M[tr][:, idx], M[hold][:, idx]
        y = isf[tr].astype(int)
        if kind == "lin":
            mdl = make_pipeline(StandardScaler(),
                                LogisticRegression(max_iter=2000, C=1.0))
        else:
            mdl = HistGradientBoostingClassifier(max_iter=300, random_state=RNG)
        mdl.fit(Xtr, y)
        return mdl.predict_proba(Xho)[:, 1]

    sh, ih, sd = strata[hold], isf[hold], seeds[hold]
    arms = {}
    arms["CHAMPION EVAL (actual, hand-tuned)"] = single("CHAMP_EVAL")[hold]
    arms["SPAWN alone (best single term)"] = single("SPAWN")[hold]
    arms["d_spawn_h alone (unclipped)"] = single("d_spawn_h")[hold]
    arms["linear, 11 hand features"] = fit(names11, "lin")
    arms["linear, 11 + d_spawn_h"] = fit(names11 + ["d_spawn_h"], "lin")
    feat_only = names11 + cands          # learned arms never see CHAMP_EVAL: it is the
    arms["linear, ALL features"] = fit(feat_only, "lin")   # comparator, not an input
    arms["GBM, ALL features (ceiling)"] = fit(feat_only, "gbm")

    rng = np.random.default_rng(RNG)
    print("\n%-32s %8s %9s %8s %9s"
          % ("arm", "AUC", "spearman", "top1%lift", "pAUC@.10"), flush=True)
    res = {}
    for k, s in arms.items():
        a = auc_on(sh, ih, s)
        rho, lift1, pauc = rank_metrics(ih, s)
        res[k] = dict(auc=a, spearman=rho, lift_top1pct=lift1, pauc_fpr10=pauc)
        print("%-32s %8.4f %9.3f %8.2f %9.4f" % (k, a, rho, lift1, pauc), flush=True)

    # ---- PRIMARY: best learned model minus d_spawn_h ALONE
    base = arms["d_spawn_h alone (unclipped)"]
    learned = {k: v for k, v in arms.items() if k.startswith(("linear", "GBM"))}
    best = max(learned, key=lambda k: res[k]["auc"])
    m, lo, hi = paired_boot_diff(sh, ih, sd, arms[best], base, rng)
    print("\nPRIMARY  best learned = %s" % best, flush=True)
    print("  AUC(best learned) - AUC(d_spawn_h alone) = %+.4f  95%% CI [%+.4f, %+.4f]"
          % (m, lo, hi), flush=True)
    verdict = "JUSTIFIES stage 2" if lo > 0 else "does NOT justify stage 2"
    print("  -> %s" % verdict, flush=True)

    # context: what un-clipping alone buys over the champion's own term
    m2, lo2, hi2 = paired_boot_diff(sh, ih, sd, base, arms["SPAWN alone (best single term)"], rng)
    print("  (context) d_spawn_h - SPAWN       = %+.4f [%+.4f, %+.4f]" % (m2, lo2, hi2), flush=True)
    m3, lo3, hi3 = paired_boot_diff(sh, ih, sd, arms[best],
                                    arms["CHAMPION EVAL (actual, hand-tuned)"], rng)
    print("  ★ best learned - CHAMPION EVAL   = %+.4f [%+.4f, %+.4f]" % (m3, lo3, hi3), flush=True)
    m4, lo4, hi4 = paired_boot_diff(sh, ih, sd, arms["linear, 11 + d_spawn_h"],
                                    arms["CHAMPION EVAL (actual, hand-tuned)"], rng)
    print("    linear(11+dsh) - CHAMPION EVAL = %+.4f [%+.4f, %+.4f]" % (m4, lo4, hi4), flush=True)

    # ---- KILLED MUTANT: shuffled labels within stratum, refit end to end
    yp = FB.perm_labels_within_stratum(strata, isf, np.random.default_rng(RNG + 1))
    idx = [allnames.index(c) for c in feat_only]
    mdl = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    mdl.fit(M[tr][:, idx], yp[tr].astype(int))
    sp = mdl.predict_proba(M[hold][:, idx])[:, 1]
    a_null = auc_on(sh, yp[hold], sp)
    ok = 0.45 <= a_null <= 0.55
    print("\nSHUFFLED-LABEL CONTROL (refit end to end): AUC %.4f  -> %s"
          % (a_null, "OK" if ok else "*** LEAK -- no arm may be read"), flush=True)

    json.dump(dict(prereg="PREREG_SUPERVISED_FLOOR.md", n_fatal=con["n_fatal"],
                   n_ctrl=con["n_ctrl"], n_train=int(tr.sum()), n_hold=int(hold.sum()),
                   arms=res, primary=dict(best=best, diff=m, lo=lo, hi=hi, verdict=verdict),
                   context_dspawnh_minus_spawn=dict(diff=m2, lo=lo2, hi=hi2),
                   vs_champion_eval=dict(best=dict(diff=m3, lo=lo3, hi=hi3),
                                         linear11_dsh=dict(diff=m4, lo=lo4, hi=hi4)),
                   shuffled_control_auc=a_null, shuffled_control_pass=bool(ok)),
              open(os.path.join(HERE, "supervised_floor_result.json"), "w"), indent=2)
    print("\nwrote supervised_floor_result.json", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
