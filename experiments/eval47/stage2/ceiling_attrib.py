#!/usr/bin/env python3
"""STAGE 2 CEILING, part 4: FEATURE ATTRIBUTION under the swept (best) config.

  (a) holdout permutation importance, 5 repeats, all 26 features;
  (b) GREEDY FORWARD SELECTION starting from the 11 champion terms, adding one
      candidate at a time by INNER-fold AUC (holdout untouched during selection),
      5 rounds -- this answers "which features carry the gain" as a PATH, not a
      correlational ranking, and shows how few features reach the ceiling;
  (c) each step's holdout AUC + paired seed-clustered CI vs CHAMP_EVAL, scored once.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "6")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from ceiling_fit import auc_fast, boot_paired, load, NAMES11, SEED, INNER_MOD, OUT  # noqa

CAND15 = ["a_topout_dist", "a_d_maxh", "b_spawn_prox", "b_spawn_prox_strict",
          "c_das_reach", "c_d_das_reach", "c_nlegal_probe", "c_d_nlegal",
          "d_gvuln_mass", "d_crit_cols", "d_spawn_h", "e_escape_routes",
          "e_escape_reach", "x_hvar", "x_jagged"]
OFF_BUDGET = {"c_das_reach", "c_d_das_reach", "e_escape_reach"}


def main():
    t0 = time.time()
    d = load()
    names = d["names"]
    IDX = {n: i for i, n in enumerate(names)}
    X, y, seeds, hold = d["X"], d["y"].astype(int), d["seed"], d["hold"]
    tr, ho = ~hold, hold
    Xtr, ytr = X[tr], y[tr]
    inner = np.isin(seeds[tr] % 10, INNER_MOD)
    with open(os.path.join(OUT, "ceiling_best.pkl"), "rb") as f:
        pk = pickle.load(f)
    cfg, sgn = pk["cfg"], pk["sgn"]
    kw = {k: v for k, v in cfg["cfg"].items() if k != "kind"}
    NIT = cfg["n_iter"]
    champ_ho = sgn * d["champ"][ho]
    yh, sdh = y[ho], seeds[ho]
    a_champ = auc_fast(yh, champ_ho)
    out = {"best_cfg": cfg, "auc_champ": a_champ}

    def fit(cols, Xa=None, ya=None):
        m = HistGradientBoostingClassifier(max_iter=NIT, max_bins=255,
                                           early_stopping=False, random_state=SEED, **kw)
        m.fit((Xtr if Xa is None else Xa)[:, cols], ytr if ya is None else ya)
        return m

    # (a) permutation importance under the best model
    m26 = fit(list(range(26)))
    base = auc_fast(yh, m26.decision_function(X[ho]))
    out["auc_all26"] = base
    rng = np.random.default_rng(SEED + 7)
    Xho = X[ho].copy()
    imp = {}
    for j, nm in enumerate(names):
        col = Xho[:, j].copy()
        drops = []
        for _ in range(5):
            Xho[:, j] = col[rng.permutation(len(col))]
            drops.append(base - auc_fast(yh, m26.decision_function(Xho)))
        Xho[:, j] = col
        imp[nm] = dict(mean_auc_drop=float(np.mean(drops)), sd=float(np.std(drops)),
                       silicon=("OFF_BUDGET" if nm in OFF_BUDGET else "in-class"))
    out["perm_importance"] = dict(sorted(imp.items(),
                                         key=lambda kv: -kv[1]["mean_auc_drop"]))
    print("PERM IMP:", flush=True)
    for k, v in out["perm_importance"].items():
        print(f"   {k:22s} {v['mean_auc_drop']:+.4f}  {v['silicon']}", flush=True)

    # (b) greedy forward selection from the 11 champion terms
    cur = [IDX[n] for n in NAMES11]
    remaining = [n for n in CAND15]
    path = []
    m0 = fit(cur)
    a0 = auc_fast(yh, m0.decision_function(X[ho][:, cur]))
    b0 = boot_paired(yh, sdh, m0.decision_function(X[ho][:, cur]), champ_ho, B=200,
                     seed=SEED + 41)
    path.append(dict(step=0, added=None, n_feat=len(cur), holdout_auc=a0,
                     vs_champ=[b0[0], b0[1], b0[2]]))
    print(f"step0 BASE11 hold={a0:.4f}", flush=True)
    for step in range(1, 6):
        best_n, best_a = None, -1.0
        for nm in remaining:
            cols = cur + [IDX[nm]]
            mm = HistGradientBoostingClassifier(max_iter=NIT, max_bins=255,
                                                early_stopping=False,
                                                random_state=SEED, **kw)
            mm.fit(Xtr[~inner][:, cols], ytr[~inner])
            a = auc_fast(ytr[inner], mm.decision_function(Xtr[inner][:, cols]))
            if a > best_a:
                best_a, best_n = a, nm
        cur = cur + [IDX[best_n]]
        remaining.remove(best_n)
        mm = fit(cur)
        s = mm.decision_function(X[ho][:, cur])
        a = auc_fast(yh, s)
        bb = boot_paired(yh, sdh, s, champ_ho, B=200, seed=SEED + 41)
        path.append(dict(step=step, added=best_n, n_feat=len(cur),
                         inner_auc=best_a, holdout_auc=a,
                         vs_champ=[bb[0], bb[1], bb[2]],
                         frac_of_ceiling_gain=((a - a_champ) / (base - a_champ))))
        print(f"step{step} +{best_n:22s} inner={best_a:.4f} hold={a:.4f} "
              f"frac_of_ceiling={(a-a_champ)/(base-a_champ):.3f}", flush=True)
    out["forward_selection"] = path

    # (c) explicit d_spawn_h-forced comparison: BASE11 + d_spawn_h only
    cols = [IDX[n] for n in NAMES11] + [IDX["d_spawn_h"]]
    mm = fit(cols)
    s = mm.decision_function(X[ho][:, cols])
    a = auc_fast(yh, s)
    bb = boot_paired(yh, sdh, s, champ_ho, B=200, seed=SEED + 41)
    out["base11_plus_dsh"] = dict(holdout_auc=a, vs_champ=[bb[0], bb[1], bb[2]],
                                  frac_of_ceiling_gain=(a - a_champ) / (base - a_champ))
    print("BASE11+d_spawn_h", out["base11_plus_dsh"], flush=True)

    with open(os.path.join(OUT, "ceiling_attrib.json"), "w") as f:
        json.dump(out, f, indent=1, default=float)
    print("wrote", time.time() - t0, flush=True)


if __name__ == "__main__":
    main()
