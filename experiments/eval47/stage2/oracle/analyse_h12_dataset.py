#!/usr/bin/env python3
"""analyse_h12_dataset.py — PHASE 1 SIZING of the H12 distillation problem.

THE QUESTION
------------
H12 wins by consulting a 15-pill x 5-sample rollout at gated exact-tie plies.
That rollout cannot run on silicon.  Can a one-ply, silicon-feasible function of
the candidate boards REPRODUCE THE ROLLOUT'S VERDICT?

This is deliberately NOT the question that hit the vocabulary wall.  That one
asked a one-ply feature to DETECT A GAP FROM SCRATCH (proto_cvd flipped 1 of 7
certified fixtures).  This one asks it to imitate a specific, already-certified
decision rule on the exact sub-population where that rule fires.  If the answer
is still "near chance", that is a much stronger negative than the wall was, and
it retires the whole distillation lane in favour of garbage-window compute.

TARGETS, DECLARED BEFORE FITTING
--------------------------------
T1  PREFER  — does the rollout's argmax land on a board OTHER than the
    champion's rank-0 board?  This is the rollout's raw verdict, margin gate
    excluded.  It is the thing a distilled comparator would have to reproduce.
T2  FLIP    — does H12 actually change the action (rollout prefers the other
    board AND the theta-margin dose gate passes)?  This is the deployed
    behaviour, and it is what a silicon term must match to preserve the
    certified endpoint.

MODEL SHAPE, DECLARED BEFORE FITTING
------------------------------------
The silicon precedent is stage 2's shippable 64-level LUT: no multiplies, 0.34
M10K, 18 of 250 cycles.  So the PRIMARY model is the cheapest thing that could
ship: a LINEAR comparator on the FEATURE DIFFERENCE between the two candidate
boards, score = w . (x_B - x_A), decide B iff score > threshold.  A gradient-
boosted model on the same inputs is fitted ONLY as a capacity ceiling — it says
how much signal exists, not what ships.

CONTROLS (a check that cannot fail is not a check)
--------------------------------------------------
* SHUFFLE: the same fit on permuted labels must land at AUC ~0.5.  If it does
  not, the split leaks and every number below is void.
* GROUPED SPLIT: train/test split is BY SEED.  Plies within a game share a
  board trajectory; a random row split would inflate AUC by memorising games.
* PRIOR: the majority-class rate is printed next to every accuracy, because an
  86%-confirm prior makes raw accuracy meaningless on its own.

Usage:
  analyse_h12_dataset.py --ties <dir-or-glob> [--out report.json]
  analyse_h12_dataset.py --ties <dir> --gate-features   # cross-impl feature gate
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from h12_arm_dataset import (FEAT_NAMES, BASE_NAMES, CAND_NAMES,  # noqa: E402
                             FREE_IN_COLWALK, OFF_BUDGET)

SPLIT_RNG = 20260817
TEST_FRAC = 0.30


# ------------------------------------------------------------------- loading
def load_ties(spec):
    paths = []
    for s in spec:
        if os.path.isdir(s):
            paths += sorted(glob.glob(os.path.join(s, "ties_*.jsonl")))
        else:
            paths += sorted(glob.glob(s))
    rows = []
    for p in paths:
        with open(p) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows, paths


# ------------------------------------------------------------------ census
def census(rows):
    """Structure of the tie population.  Reported BEFORE any model is fitted,
    because the structure decides what the model is even allowed to be."""
    n = len(rows)
    seeds = sorted({r["seed"] for r in rows})
    ndist = np.array([len(set(r["post_hash"])) for r in rows])
    dup01 = np.array([r["post_hash"][0] == r["post_hash"][1] for r in rows])
    rank1 = np.array([r["rollout_rank1"] for r in rows])
    flipped = np.array([r["flipped"] for r in rows])
    # did the rollout prefer a DIFFERENT BOARD than the champion's?
    prefer = np.array([r["post_hash"][r["rollout_rank1"]] != r["post_hash"][0]
                       for r in rows])
    margin = np.array([r["margin_sum"] for r in rows])
    return {
        "n_tie_events": n,
        "n_seeds": len(seeds),
        "ties_per_seed": round(n / max(1, len(seeds)), 2),
        "distinct_boards_hist": {int(k): int(v) for k, v in
                                 zip(*np.unique(ndist, return_counts=True))},
        "frac_top2_same_board": round(float(dup01.mean()), 4),
        "rollout_rank1_hist": {int(k): int(v) for k, v in
                               zip(*np.unique(rank1, return_counts=True))},
        "n_prefer_other_board": int(prefer.sum()),
        "frac_prefer_other_board": round(float(prefer.mean()), 4),
        "n_flipped": int(flipped.sum()),
        "frac_flipped": round(float(flipped.mean()), 4),
        "n_margin_rejected": int((prefer & ~flipped.astype(bool)).sum()),
        "margin_sum_quantiles": [int(np.quantile(margin, q))
                                 for q in (0, .25, .5, .75, .9, 1.0)],
        "viruses_median": float(np.median([r["viruses"] for r in rows])),
        "d_spawn_h_median": float(np.median([r["d_spawn_h"] for r in rows])),
    }


# ------------------------------------------------- design matrix (2-board)
def build_pair_design(rows):
    """One row per tie event that resolves to EXACTLY TWO distinct boards.

    A = the champion's rank-0 board.  B = the first candidate whose board
    differs from A.  x = features(B) - features(A), the difference a linear
    comparator would see.  Events with 3+ distinct boards are excluded here and
    counted, because a 2-way comparator is the shape being sized.
    """
    X, yP, yF, seeds, marg, ctx = [], [], [], [], [], []
    n_multi = 0
    for r in rows:
        h = r["post_hash"]
        distinct = list(dict.fromkeys(h))
        if len(distinct) != 2:
            n_multi += 1
            continue
        iA = 0
        iB = next(i for i in range(len(h)) if h[i] != h[0])
        fa = np.asarray(r["feats"][iA], dtype=np.float64)
        fb = np.asarray(r["feats"][iB], dtype=np.float64)
        X.append(fb - fa)
        prefer = h[r["rollout_rank1"]] != h[0]
        yP.append(int(prefer))
        yF.append(int(r["flipped"]))
        seeds.append(r["seed"])
        # realized rollout margin in the arm's own units: progress-sum of B
        # minus progress-sum of A.  This is the quantity the theta gate reads.
        marg.append(int(r["labels"][iB][1] - r["labels"][iA][1]))
        ctx.append([r["viruses"], r["maxh"], r["d_spawn_h"],
                    r["n_legal_pre"], r["pills_placed"]])
    return (np.asarray(X), np.asarray(yP), np.asarray(yF),
            np.asarray(seeds), np.asarray(marg), np.asarray(ctx,
                                                            dtype=np.float64),
            n_multi)


def seed_split(seeds):
    uniq = np.unique(seeds)
    rng = np.random.default_rng(SPLIT_RNG)
    perm = rng.permutation(uniq)
    n_test = max(1, int(round(TEST_FRAC * len(uniq))))
    test_seeds = set(perm[:n_test].tolist())
    te = np.array([s in test_seeds for s in seeds])
    return ~te, te


# ------------------------------------------------------------------- models
def fit_eval(Xtr, ytr, Xte, yte, kind, seed=0):
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score, accuracy_score
    from sklearn.preprocessing import StandardScaler

    if len(np.unique(ytr)) < 2 or len(np.unique(yte)) < 2:
        return {"auc": None, "note": "degenerate class in a split"}
    if kind == "logit":
        sc = StandardScaler().fit(Xtr)
        m = LogisticRegression(max_iter=5000, C=1.0)
        m.fit(sc.transform(Xtr), ytr)
        p = m.predict_proba(sc.transform(Xte))[:, 1]
        coef = m.coef_[0] / np.maximum(sc.scale_, 1e-12)
    else:
        m = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.06, max_leaf_nodes=15,
            l2_regularization=1.0, random_state=seed)
        m.fit(Xtr, ytr)
        p = m.predict_proba(Xte)[:, 1]
        coef = None
    prior = max(yte.mean(), 1 - yte.mean())
    out = {"auc": round(float(roc_auc_score(yte, p)), 4),
           "acc": round(float(accuracy_score(yte, p > 0.5)), 4),
           "majority_prior": round(float(prior), 4),
           "n_train": int(len(ytr)), "n_test": int(len(yte)),
           "pos_rate_train": round(float(ytr.mean()), 4),
           "pos_rate_test": round(float(yte.mean()), 4)}
    return out, p, coef


def run_target(name, X, y, seeds, tr, te, feat_names):
    res = {}
    for kind in ("logit", "gbm"):
        r = fit_eval(X[tr], y[tr], X[te], y[te], kind)
        if isinstance(r, dict):
            res[kind] = r
            continue
        stats, p, coef = r
        res[kind] = stats
        if coef is not None:
            top = sorted(zip(feat_names, coef), key=lambda kv: -abs(kv[1]))[:8]
            res[kind]["top_coefs"] = [[k, round(float(v), 5)] for k, v in top]
            res["_logit_pred"] = p
        else:
            res["_gbm_pred"] = p
    # SHUFFLE CONTROL: permute labels within the training set only.
    rng = np.random.default_rng(SPLIT_RNG + 1)
    ysh = y.copy()
    ysh[tr] = rng.permutation(ysh[tr])
    r = fit_eval(X[tr], ysh[tr], X[te], y[te], "logit")
    res["shuffle_control"] = r if isinstance(r, dict) else r[0]
    return res


def calibration(score, realized_margin, nbins=8):
    """Does a higher predicted preference mean a bigger REAL rollout margin?

    A distilled term that ranks correctly but cannot tell a 1-virus edge from a
    10-virus edge cannot reproduce the theta-margin dose gate, and the dose gate
    is what made H12 work (undosed, the median fair gain at the raw tie is 0.00).
    """
    from scipy.stats import spearmanr
    order = np.argsort(score)
    bins = np.array_split(order, nbins)
    rows = []
    for b in bins:
        rows.append({"n": int(len(b)),
                     "score_mean": round(float(score[b].mean()), 4),
                     "realized_margin_mean": round(float(
                         realized_margin[b].mean()), 3),
                     "frac_margin_ge3": round(float(
                         (realized_margin[b] >= 3).mean()), 4)})
    rho, p = spearmanr(score, realized_margin)
    return {"spearman_rho": round(float(rho), 4), "spearman_p": float(p),
            "bins": rows}


# ------------------------------------------------------------ feature gate
def gate_features(rows, n=400):
    """Cross-implementation check: the 26 logged features must be reproducible
    from the STORED BOARDS by an independent code path.

    The 15 candidate features are re-derived by `vocab2/feature_battery.py`
    itself (the module the arm deliberately does NOT import at runtime, because
    it rewrites sys.path); the 11 base terms are re-derived by a fresh
    `_base_scan` on the stored post board.  Two implementations agreeing is the
    check.  A mutant that corrupts one stored board must FAIL it.
    """
    import feature_battery as FBAT       # pollutes sys.path; harmless offline
    import fast_rtl_x as FX
    import reach_root as RR
    fl = RR._lazy()["fl"]

    sel = rows[:n]
    bad = []
    posts, hpres, nlegs, logged = [], [], [], []
    for r in sel:
        pre = np.frombuffer(bytes.fromhex(r["pre_col"]), dtype=np.uint8)
        Hpre = FBAT.heights_from_boards(pre.reshape(1, -1).astype(np.int8))
        for i in range(len(r["post_col"])):
            posts.append(np.frombuffer(bytes.fromhex(r["post_col"][i]),
                                       dtype=np.uint8))
            hpres.append(Hpre[0])
            nlegs.append(r["n_legal_pre"])
            logged.append(r["feats"][i])
    posts = np.stack(posts).astype(np.int8)
    Hpre = np.stack(hpres)
    Hpost = FBAT.heights_from_boards(posts)
    logged = np.asarray(logged, dtype=np.float64)

    # feature_battery computes c_d_nlegal against a scalar n_legal_pre per row
    cf = FBAT.candidate_features(posts, Hpost, Hpre, np.asarray(nlegs))
    for j, nm in enumerate(CAND_NAMES):
        ref = np.asarray(cf[nm], dtype=np.float64)
        got = logged[:, 11 + j]
        d = np.abs(ref - got).max()
        if d > 1e-6:
            bad.append([nm, float(d)])

    # 11 base terms, recomputed from the stored post board
    base = np.empty(FX.NBASE, dtype=np.int64)
    v_zero = np.zeros(128, dtype=np.int8)
    n_base_checked = 0
    base_bad = 0
    for k, r in enumerate(sel):
        for i in range(len(r["post_col"])):
            idx = sum(len(x["post_col"]) for x in sel[:k]) + i
            # the virus plane is not stored; terms that need it are skipped, so
            # only the colour-plane-only terms are cross-checked here
            FX._base_scan(posts[idx], v_zero, fl, base)
            got = logged[idx, :4]                 # MAXH HOLES TOPRISK SPAWN
            ref = np.array([float(base[t]) for t in range(4)])
            n_base_checked += 1
            if np.abs(ref - got).max() > 1e-6:
                base_bad += 1

    # MUTANT: corrupt one stored board; the check must notice.
    mut = posts.copy()
    mut[0, 0] = 3 if mut[0, 0] != 3 else 1
    Hmut = FBAT.heights_from_boards(mut)
    cfm = FBAT.candidate_features(mut, Hmut, Hpre, np.asarray(nlegs))
    mutant_detected = bool(
        max(np.abs(np.asarray(cfm[nm], dtype=np.float64)
                   - logged[:, 11 + j]).max()
            for j, nm in enumerate(CAND_NAMES)) > 1e-6)

    ok = (not bad) and base_bad == 0 and mutant_detected
    return {"pass": bool(ok), "rows_checked": len(sel),
            "cand_mismatches": bad,
            "base_rows_checked": n_base_checked,
            "base_mismatches": base_bad,
            "mutant_detected": mutant_detected}


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ties", nargs="+", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "out",
                                                  "h12_distill_sizing.json"))
    ap.add_argument("--gate-features", action="store_true")
    a = ap.parse_args()

    rows, paths = load_ties(a.ties)
    print(f"loaded {len(rows)} tie records from {len(paths)} files")
    if not rows:
        print("NO DATA")
        return 1

    if a.gate_features:
        g = gate_features(rows)
        print("FEATURE GATE " + ("PASS" if g["pass"] else "FAIL"))
        print(json.dumps(g, indent=1))
        return 0 if g["pass"] else 1

    doc = {"n_files": len(paths), "census": census(rows)}
    print(json.dumps(doc["census"], indent=1))

    X, yP, yF, seeds, marg, ctx, n_multi = build_pair_design(rows)
    doc["pair_design"] = {"n_rows": int(len(X)),
                          "n_excluded_multiboard": int(n_multi),
                          "prefer_rate": round(float(yP.mean()), 4),
                          "flip_rate": round(float(yF.mean()), 4)}
    print("\npair design:", json.dumps(doc["pair_design"]))
    if len(X) < 200:
        doc["verdict"] = "INSUFFICIENT DATA"
        json.dump(doc, open(a.out, "w"), indent=1)
        print("too few 2-board tie events to size the problem")
        return 1

    tr, te = seed_split(seeds)
    Xf = np.concatenate([X, ctx], axis=1)
    names_f = [f"d_{n}" for n in FEAT_NAMES] + [
        "ctx_viruses", "ctx_maxh", "ctx_d_spawn_h", "ctx_n_legal",
        "ctx_pills_placed"]

    doc["T1_prefer"] = {}
    r1 = run_target("T1", Xf, yP, seeds, tr, te, names_f)
    logit_p = r1.pop("_logit_pred", None)
    r1.pop("_gbm_pred", None)
    doc["T1_prefer"] = r1
    print("\nT1 PREFER (rollout picks the non-champion board):")
    print(json.dumps(r1, indent=1))

    r2 = run_target("T2", Xf, yF, seeds, tr, te, names_f)
    r2.pop("_logit_pred", None)
    r2.pop("_gbm_pred", None)
    doc["T2_flip"] = r2
    print("\nT2 FLIP (H12 actually changes the action):")
    print(json.dumps(r2, indent=1))

    # feature-budget ablation: drop the 3 off-budget reach features
    keep = [i for i, n in enumerate(FEAT_NAMES) if n not in OFF_BUDGET]
    Xb = np.concatenate([X[:, keep], ctx], axis=1)
    rb = run_target("T1_budget", Xb, yP, seeds, tr, te,
                    [f"d_{FEAT_NAMES[i]}" for i in keep] + names_f[-5:])
    rb.pop("_logit_pred", None)
    rb.pop("_gbm_pred", None)
    doc["T1_free_budget_only"] = rb
    print("\nT1 restricted to FREE_IN_COLWALK features:")
    print(json.dumps({k: v for k, v in rb.items()
                      if k in ("logit", "gbm", "shuffle_control")}, indent=1))

    if logit_p is not None:
        doc["calibration_T1_logit"] = calibration(logit_p, marg[te])
        print("\ncalibration (predicted preference vs realized rollout "
              "margin, TEST split):")
        print(json.dumps(doc["calibration_T1_logit"], indent=1))

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(doc, open(a.out, "w"), indent=1, default=float)
    print("\nwrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
