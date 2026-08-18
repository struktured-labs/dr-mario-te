#!/usr/bin/env python3
"""The approved reopening attempt: can a LINEAR rule's CONFIDENT picks be good?

The lane closed because the only silicon-feasible shape (a linear score) has
NEGATIVE held-out mean margin at every firing rate — its confident picks are
systematically bad — while the benign GBM tail is both unshippable and ~8x below
the N=9000 detection floor.  Two approved attacks, both on BANKED data, zero new
rollouts:

  (a) ASYMMETRIC / DEPLOYMENT-SHAPED LOSS.  Every model so far was trained on a
      target that is not the deployment objective: the binary gate label, or
      squared error on the signed margin.  Neither penalises the thing that
      actually hurts — firing on a board that is much WORSE.  Four linear
      variants are tried, ending with one that optimises the deployment
      objective directly.

  (b) CLEAN SUBPOPULATION.  Maybe the linear tail is dirty only in aggregate and
      some silicon-checkable stratum is clean.  Searched on TRAIN seeds only,
      then the single selected predicate is scored ONCE on held-out seeds.

SUCCESS BAR, fixed before running (team lead's wording): a LINEAR rule with
POSITIVE held-out mean margin at a firing rate of AT LEAST 2%, reported with the
operating-point table.  AUC is not reported as a headline anywhere in this file —
that rule cost this lane three corrections.

MULTIPLE-COMPARISONS DISCIPLINE for (b): the predicate is chosen on train and
evaluated once on held-out, and the NUMBER of predicates tried is printed next
to the winner so the reader can discount it.  A stratum that only looks clean
because 40 were tried is not a finding.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from analyse_h12_dataset import (load_ties, build_listwise_design, seed_split,
                                 H12_MARGIN_SUM, FEAT_NAMES)
from temporal_accum import CAND_TEMPORAL_NAMES, STATE_TEMPORAL_NAMES

DOSES = (0.005, 0.01, 0.02, 0.05)
BAR_DOSE = 0.02          # the success bar is at >= 2% firing


def op_table(score, marg, doses=DOSES):
    """The only reporting format this lane is allowed to use for a gate."""
    out = {}
    for q in doses:
        k = max(1, int(q * len(score)))
        idx = np.argsort(-score)[:k]
        out[q] = {"n": int(k),
                  "mean_margin": round(float(marg[idx].mean()), 3),
                  "precision_ge3": round(float((marg[idx] >= H12_MARGIN_SUM).mean()), 4),
                  "frac_le_-3": round(float((marg[idx] <= -3).mean()), 4)}
    return out


def show(name, tab, ref):
    cells = " | ".join(
        f"{q*100:g}%: {t['mean_margin']:+.2f} (p{t['precision_ge3']:.2f} "
        f"bad{t['frac_le_-3']:.2f})" for q, t in tab.items())
    bar = tab[BAR_DOSE]["mean_margin"] > 0
    print(f"  {'PASS' if bar else 'fail'}  {name:34s} {cells}")
    return bar


def main():
    rows, _ = load_ties(["out/distill_pilot_v2_60000", "out/distill_ext_62000"])
    L = build_listwise_design(rows)
    X = np.concatenate([L["X_static"], L["ctx_static"],
                        L["X_temporal"], L["ctx_temporal"]], axis=1)
    marg, seeds = L["marg"], L["seeds"]
    tr, te = seed_split(seeds)
    yg = (marg >= H12_MARGIN_SUM).astype(int)
    ref = {"mean_margin": round(float(marg[te].mean()), 3),
           "frac_le_-3": round(float((marg[te] <= -3).mean()), 4)}
    print(f"pooled {len(rows)} events / {len(set(seeds.tolist()))} seeds; "
          f"held-out rows {int(te.sum())}")
    print(f"REFERENCE (random alternative): mean margin {ref['mean_margin']}, "
          f"frac<=-3 {ref['frac_le_-3']}")
    print(f"SUCCESS BAR: positive held-out mean margin at >= {BAR_DOSE*100:g}% "
          f"firing, LINEAR only\n")

    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression, Ridge
    sc = StandardScaler().fit(X[tr])
    Xtr, Xte = sc.transform(X[tr]), sc.transform(X[te])
    mtr, mte = marg[tr], marg[te]
    doc = {"reference": ref, "bar_dose": BAR_DOSE, "results": {}}
    passed = []

    print("(a) LINEAR VARIANTS, deployment-shaped losses")
    # a0 baseline: the gate classifier that failed, for comparison
    m0 = LogisticRegression(max_iter=5000).fit(Xtr, yg[tr])
    t = op_table(m0.decision_function(Xte), mte)
    doc["results"]["a0_gate_logit_baseline"] = {str(k): v for k, v in t.items()}
    passed.append(("a0 gate-logit (baseline)", show("a0 gate-logit (baseline)", t, ref)))

    # a1 plain ridge on SIGNED margin -- low R2, but its TAIL was never measured
    m1 = Ridge(alpha=1.0).fit(Xtr, mtr)
    t = op_table(m1.predict(Xte), mte)
    doc["results"]["a1_ridge_signed_margin"] = {str(k): v for k, v in t.items()}
    passed.append(("a1 ridge on signed margin", show("a1 ridge on signed margin", t, ref)))

    # a2 asymmetric sample weights: rows that would be costly to fire on are
    # upweighted, so the fit pays extra for putting them high
    for lam in (3.0, 10.0):
        w = np.where(mtr <= -3, lam, 1.0)
        m2 = Ridge(alpha=1.0).fit(Xtr, mtr, sample_weight=w)
        t = op_table(m2.predict(Xte), mte)
        doc["results"][f"a2_ridge_asym_lam{lam:g}"] = {str(k): v for k, v in t.items()}
        passed.append((f"a2 ridge asym w={lam:g}",
                       show(f"a2 ridge asym w={lam:g}", t, ref)))

    # a3 DIRECT deployment objective: maximise the SOFT top-q mean margin of a
    # linear score.  softmax(s/T) is a differentiable stand-in for "the rows we
    # would actually fire on", so the optimiser is scored on the same quantity
    # the deployment is scored on, rather than on a proxy label.
    from scipy.optimize import minimize
    for T in (0.5, 1.0):
        def neg_obj(w, T=T):
            s = Xtr @ w
            s = s - s.max()
            e = np.exp(s / T)
            p = e / e.sum()
            return -(p @ mtr) + 1e-3 * (w @ w)
        r = minimize(neg_obj, np.zeros(Xtr.shape[1]), method="L-BFGS-B",
                     options={"maxiter": 500})
        t = op_table(Xte @ r.x, mte)
        doc["results"][f"a3_softtopk_T{T:g}"] = {str(k): v for k, v in t.items()}
        passed.append((f"a3 soft-top-k T={T:g}",
                       show(f"a3 soft-top-k T={T:g}", t, ref)))

    # (b) CLEAN SUBPOPULATION -------------------------------------------------
    print("\n(b) CLEAN-SUBPOPULATION SEARCH (chosen on TRAIN, scored ONCE on held-out)")
    names = ([f"d_{n}" for n in FEAT_NAMES] + ["d_champ_val"]
             + ["ctx_viruses", "ctx_maxh", "ctx_d_spawn_h", "ctx_n_legal",
                "ctx_pills_placed"]
             + [f"d_{n}" for n in CAND_TEMPORAL_NAMES]
             + [f"c_{n}" for n in STATE_TEMPORAL_NAMES])
    ci = {n: i for i, n in enumerate(names)}
    preds = []
    for col, cuts in (("ctx_viruses", (4, 8, 12, 20)),
                      ("ctx_maxh", (8, 10, 12, 14)),
                      ("ctx_d_spawn_h", (6, 9, 12)),
                      ("ctx_n_legal", (24, 30, 36)),
                      ("ctx_pills_placed", (30, 60, 100)),
                      ("c_ts_burial_max", (5, 20, 50)),
                      ("c_ts_pills_since_any_clear", (2, 5, 10))):
        j = ci[col]
        for c in cuts:
            preds.append((f"{col}<={c}", lambda A, j=j, c=c: A[:, j] <= c))
            preds.append((f"{col}>{c}", lambda A, j=j, c=c: A[:, j] > c))
    Xr_tr, Xr_te = X[tr], X[te]
    best = None
    for nm, f in preds:
        mk = f(Xr_tr)
        if mk.sum() < 800:
            continue
        s = StandardScaler().fit(Xr_tr[mk])
        mm = Ridge(alpha=1.0).fit(s.transform(Xr_tr[mk]), mtr[mk])
        tt = op_table(mm.predict(s.transform(Xr_tr[mk])), mtr[mk])
        v = tt[BAR_DOSE]["mean_margin"]
        if best is None or v > best[1]:
            best = (nm, v, f, mk.sum())
    print(f"  tried {len(preds)} predicates; best on TRAIN: {best[0]} "
          f"(train mean margin at {BAR_DOSE*100:g}% = {best[1]:+.2f}, "
          f"n_train={best[3]})")
    mk_tr, mk_te = best[2](Xr_tr), best[2](Xr_te)
    s = StandardScaler().fit(Xr_tr[mk_tr])
    mm = Ridge(alpha=1.0).fit(s.transform(Xr_tr[mk_tr]), mtr[mk_tr])
    t = op_table(mm.predict(s.transform(Xr_te[mk_te])), mte[mk_te])
    doc["results"]["b_best_subpop"] = {"predicate": best[0],
                                       "n_predicates_tried": len(preds),
                                       "n_heldout": int(mk_te.sum()),
                                       "table": {str(k): v for k, v in t.items()}}
    passed.append((f"b subpop {best[0]}",
                   show(f"b subpop {best[0]}", t, ref)))

    any_pass = any(p for _, p in passed)
    doc["verdict"] = "REOPEN_AB" if any_pass else "LANE_CLOSED_THIRD_VERDICT"
    doc["passing"] = [n for n, p in passed if p]
    print(f"\nVERDICT: {doc['verdict']}"
          + (f"  passing: {doc['passing']}" if any_pass else
             "  — no linear rule clears positive mean margin at >=2% dose"))
    json.dump(doc, open("results_distill/asymmetric_fit.json", "w"), indent=1,
              default=float)
    print("wrote results_distill/asymmetric_fit.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
