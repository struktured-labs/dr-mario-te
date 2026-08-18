#!/usr/bin/env python3
"""The two "what would change my mind" tests, run on BANKED data only.

Phase 1 closed with PIVOT on this reasoning: the comparator can rank (AUC ~0.65,
clears its null) but cannot price — margin regression R2 ~0.01 and the readout
against H12's own theta gate came back BELOW chance.  Two objections deserve a
measurement rather than an assertion, and both are answerable without a single
new rollout:

  TEST 1  MAGNITUDE, targeted directly.  The earlier regression predicted SIGNED
          margin from SIGNED feature differences.  A linear model cannot express
          "these boards differ a lot, in whichever direction" from signed inputs,
          so the R2~0.01 floor may have been a model-shape artefact rather than
          an information limit.  Tested here: |margin| from ABS differences
          (linear CAN express it), |margin| from signed differences via trees
          (which can represent symmetry), and — the one that actually decides
          deployability — a DIRECT CLASSIFIER for H12's gate, y = margin >= 3.
          That last one was never fitted in phase 1; the 0.32-0.38 figure came
          from thresholding a regression, which is a weaker instrument.

  TEST 2  REGIME.  Refit the three-way decomposition on the h<=12 band where
          DRPRESTART is strongest (89.4% of releases spawn-ready), with h>=13 as
          the contrast arm.  Pooling a regime where the mechanism is weak with
          one where it is strong can hide a real effect in the average.

Same discipline as the sizing run: split BY SEED, permuted-label null band with
N_SHUFFLE draws, and the verdict is "clears the null MAX", not "beats 0.5".

Usage: test_counterfactuals.py --ties DIR [DIR ...] --out report.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from analyse_h12_dataset import (load_ties, build_listwise_design, seed_split,
                                 cluster_boot_auc, N_SHUFFLE, SPLIT_RNG,
                                 H12_MARGIN_SUM, FEAT_NAMES)
from temporal_accum import CAND_TEMPORAL_NAMES, STATE_TEMPORAL_NAMES


def _classes(L):
    """static / temporal / combined blocks, each with its own context."""
    return {
        "static": np.concatenate([L["X_static"], L["ctx_static"]], axis=1),
        "temporal": np.concatenate([L["X_temporal"], L["ctx_temporal"]], axis=1),
        "combined": np.concatenate([L["X_static"], L["ctx_static"],
                                    L["X_temporal"], L["ctx_temporal"]],
                                   axis=1)}


def fit_reg(Xtr, ytr, Xte, yte, kind):
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import HistGradientBoostingRegressor
    if kind == "ridge":
        sc = StandardScaler().fit(Xtr)
        m = Ridge(alpha=1.0).fit(sc.transform(Xtr), ytr)
        return float(m.score(sc.transform(Xte), yte))
    m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06,
                                      max_leaf_nodes=15, random_state=0)
    m.fit(Xtr, ytr)
    return float(m.score(Xte, yte))


def fit_clf(Xtr, ytr, Xte, yte, kind, seeds_te=None):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    if len(np.unique(ytr)) < 2 or len(np.unique(yte)) < 2:
        return None, None
    if kind == "logit":
        sc = StandardScaler().fit(Xtr)
        m = LogisticRegression(max_iter=5000).fit(sc.transform(Xtr), ytr)
        p = m.predict_proba(sc.transform(Xte))[:, 1]
    else:
        m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06,
                                           max_leaf_nodes=15, random_state=0)
        m.fit(Xtr, ytr)
        p = m.predict_proba(Xte)[:, 1]
    return float(roc_auc_score(yte, p)), p


def null_band_reg(Xtr, ytr, Xte, yte, kind):
    out = []
    for i in range(N_SHUFFLE):
        rng = np.random.default_rng(SPLIT_RNG + 500 + i)
        out.append(fit_reg(Xtr, rng.permutation(ytr), Xte, yte, kind))
    return out


def null_band_clf(Xtr, ytr, Xte, yte, kind):
    out = []
    for i in range(N_SHUFFLE):
        rng = np.random.default_rng(SPLIT_RNG + 700 + i)
        a, _ = fit_clf(Xtr, rng.permutation(ytr), Xte, yte, kind)
        if a is not None:
            out.append(a)
    return out


def test1_magnitude(L, doc):
    """Can ANYTHING price the margin, given a model shape that could express it?"""
    C = _classes(L)
    marg, seeds = L["marg"], L["seeds"]
    tr, te = seed_split(seeds)
    absmarg = np.abs(marg)
    res = {}
    print("\n=== TEST 1: MAGNITUDE, targeted directly ===")
    print(f"  |margin| mean {absmarg.mean():.2f}  frac|margin|>=3 "
          f"{(absmarg >= 3).mean():.4f}  frac margin>=3 "
          f"{(marg >= H12_MARGIN_SUM).mean():.4f}")
    for cls, X in C.items():
        Xa = np.abs(X)                       # sign-invariant inputs
        r = {}
        # (a) linear on ABS differences -- the shape phase 1 could not express
        r["ridge_absfeat_R2_absmargin"] = round(
            fit_reg(Xa[tr], absmarg[tr], Xa[te], absmarg[te], "ridge"), 4)
        nb = null_band_reg(Xa[tr], absmarg[tr], Xa[te], absmarg[te], "ridge")
        r["ridge_null_R2_max"] = round(float(np.max(nb)), 4)
        # (b) trees on SIGNED differences -- can represent symmetry
        r["gbm_signed_R2_absmargin"] = round(
            fit_reg(X[tr], absmarg[tr], X[te], absmarg[te], "gbm"), 4)
        # (c) DIRECT CLASSIFIER for H12's OWN GATE.  This is the deployable
        #     target and it was never fitted in phase 1.
        yg = (marg >= H12_MARGIN_SUM).astype(int)
        for k in ("logit", "gbm"):
            a, p = fit_clf(X[tr], yg[tr], X[te], yg[te], k)
            r[f"gate_clf_{k}_auc"] = round(a, 4) if a else None
            if k == "gbm" and a is not None:
                r["gate_clf_gbm_ci95"] = cluster_boot_auc(yg[te], p, seeds[te])
        nbc = null_band_clf(X[tr], yg[tr], X[te], yg[te], "gbm")
        r["gate_clf_null_max"] = round(float(np.max(nbc)), 4) if nbc else None
        r["gate_clf_beats_null"] = bool(
            r["gate_clf_gbm_auc"] and r["gate_clf_null_max"]
            and r["gate_clf_gbm_auc"] > r["gate_clf_null_max"])
        res[cls] = r
        print(f"  {cls:9s} |margin| R2: ridge/abs {r['ridge_absfeat_R2_absmargin']} "
              f"(null max {r['ridge_null_R2_max']})  gbm/signed "
              f"{r['gbm_signed_R2_absmargin']}")
        print(f"            GATE clf AUC logit {r['gate_clf_logit_auc']} "
              f"gbm {r['gate_clf_gbm_auc']} CI {r.get('gate_clf_gbm_ci95')} "
              f"| null max {r['gate_clf_null_max']} | beats_null "
              f"{r['gate_clf_beats_null']}")
    doc["test1_magnitude"] = res
    return res


def test2_regime(rows, doc):
    """Does the h<=12 band, where DRPRESTART is strongest, behave differently?"""
    print("\n=== TEST 2: REGIME RESTRICTION ===")
    res = {}
    bands = {"h_le_12": [r for r in rows if r["d_spawn_h"] <= 12],
             "h_ge_13": [r for r in rows if r["d_spawn_h"] >= 13]}
    for band, sub in bands.items():
        if len(sub) < 500:
            print(f"  {band}: only {len(sub)} events — skipped")
            continue
        L = build_listwise_design(sub)
        C = _classes(L)
        y, seeds, marg = L["y"], L["seeds"], L["marg"]
        tr, te = seed_split(seeds)
        b = {"n_events": len(sub), "n_rows": int(len(y)),
             "prefer_rate": round(float(L["prefer_by_event"].mean()), 4)}
        print(f"  --- {band}: {len(sub)} events, {len(y)} rows, "
              f"prefer {b['prefer_rate']}")
        for cls, X in C.items():
            a, p = fit_clf(X[tr], y[tr], X[te], y[te], "logit")
            nb = null_band_clf(X[tr], y[tr], X[te], y[te], "logit")
            ci = cluster_boot_auc(y[te], p, seeds[te]) if a else None
            beats = bool(a and nb and a > max(nb))
            b[cls] = {"logit_auc": round(a, 4) if a else None,
                      "ci95": ci,
                      "null_max": round(float(np.max(nb)), 4) if nb else None,
                      "beats_null": beats}
            # and the gate readout inside this band
            yg = (marg >= H12_MARGIN_SUM).astype(int)
            ag, _ = fit_clf(X[tr], yg[tr], X[te], yg[te], "gbm")
            b[cls]["gate_clf_gbm_auc"] = round(ag, 4) if ag else None
            print(f"      {cls:9s} prefer AUC {b[cls]['logit_auc']} CI {ci} "
                  f"null_max {b[cls]['null_max']} beats {beats} | "
                  f"gate AUC {b[cls]['gate_clf_gbm_auc']}")
        res[band] = b
    doc["test2_regime"] = res
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ties", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows, paths = load_ties(a.ties)
    seeds = sorted({r["seed"] for r in rows})
    print(f"pooled {len(rows)} tie events from {len(seeds)} seeds "
          f"({len(paths)} files); seed range {seeds[0]}..{seeds[-1]}")
    doc = {"n_tie_events": len(rows), "n_seeds": len(seeds),
           "seed_min": seeds[0], "seed_max": seeds[-1], "sources": a.ties}

    L = build_listwise_design(rows)
    test1_magnitude(L, doc)
    test2_regime(rows, doc)

    # VERDICT, mechanical rather than narrated.
    t1 = doc["test1_magnitude"]
    gate_ok = any(v.get("gate_clf_beats_null") and
                  (v.get("gate_clf_gbm_auc") or 0) >= 0.65 for v in t1.values())
    mag_ok = any(v["ridge_absfeat_R2_absmargin"] > 0.10 or
                 v["gbm_signed_R2_absmargin"] > 0.10 for v in t1.values())
    t2 = doc.get("test2_regime", {})
    band_ok = any(c.get("gate_clf_gbm_auc", 0) and c["gate_clf_gbm_auc"] >= 0.65
                  for b in t2.values() for k, c in b.items()
                  if isinstance(c, dict))
    doc["verdict"] = ("REOPEN" if (gate_ok or mag_ok or band_ok)
                      else "CONFIRM_PIVOT")
    doc["verdict_inputs"] = {"gate_clf_beats_null_and_ge_0.65": gate_ok,
                             "magnitude_R2_gt_0.10": mag_ok,
                             "any_band_gate_auc_ge_0.65": band_ok}
    print(f"\nVERDICT: {doc['verdict']}  {json.dumps(doc['verdict_inputs'])}")
    json.dump(doc, open(a.out, "w"), indent=1, default=float)
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
