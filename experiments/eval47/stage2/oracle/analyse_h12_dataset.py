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
* SHUFFLE NULL BAND: the same fit on permuted training labels, repeated
  N_SHUFFLE times.  The real AUC must clear the MAXIMUM of that band.  One
  shuffle draw is NOT a control — a logistic fit on permuted labels is a random
  direction in 31-dim space, and a single draw measured 0.63 against a planted
  signal.  The null is the distribution, not a point.
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
N_SHUFFLE = 12          # draws in the permuted-label null band
N_BOOT = 300            # cluster (by seed) bootstrap draws for the AUC CI


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


def build_listwise_design(rows):
    """One row per DISTINCT ALTERNATIVE board, which keeps every tie event.

    The 2-board design above drops the ~20% of events that resolve to 3 or 4
    distinct boards.  Dropping a fifth of the population and then reporting an
    AUC on the remainder would be sizing a problem nobody has.  Here each
    distinct board d != A contributes a row x = feat(d) - feat(A) labelled "is d
    the rollout's argmax", and the deployed decision is argmax over an event's
    rows against a threshold — the same linear comparator, evaluated the way it
    would actually be used.
    """
    X, y, ev, seeds, marg, ctx = [], [], [], [], [], []
    prefer_by_event, seed_by_event = [], []
    for e, r in enumerate(rows):
        h = r["post_hash"]
        A = h[0]
        best = h[r["rollout_rank1"]]
        fa = np.asarray(r["feats"][0], dtype=np.float64)
        pa = r["labels"][0][1]
        seen = {A}
        n_alt = 0
        for i in range(len(h)):
            if h[i] in seen:
                continue
            seen.add(h[i])
            X.append(np.asarray(r["feats"][i], dtype=np.float64) - fa)
            y.append(int(h[i] == best))
            ev.append(e)
            seeds.append(r["seed"])
            marg.append(int(r["labels"][i][1] - pa))
            ctx.append([r["viruses"], r["maxh"], r["d_spawn_h"],
                        r["n_legal_pre"], r["pills_placed"]])
            n_alt += 1
        prefer_by_event.append(int(best != A))
        seed_by_event.append(r["seed"])
    return (np.asarray(X), np.asarray(y), np.asarray(ev), np.asarray(seeds),
            np.asarray(marg), np.asarray(ctx, dtype=np.float64),
            np.asarray(prefer_by_event), np.asarray(seed_by_event))


def event_decision_accuracy(score, y, ev, prefer_by_event, tau):
    """Fraction of EVENTS where the comparator picks the rollout's board.

    An event is correct when either (a) no alternative clears tau and the
    rollout also kept the champion's board, or (b) the argmax alternative
    clears tau and IS the rollout's board.  This is the number that matters:
    row AUC can look fine while the per-decision behaviour does not match.
    """
    n_ev = int(ev.max()) + 1 if len(ev) else 0
    correct = 0
    fired = 0
    fired_correct = 0
    for e in range(n_ev):
        m = ev == e
        if not m.any():
            correct += int(prefer_by_event[e] == 0)
            continue
        s = score[m]
        j = int(np.argmax(s))
        if s[j] <= tau:
            correct += int(prefer_by_event[e] == 0)
        else:
            fired += 1
            hit = bool(y[m][j] == 1)
            correct += int(hit)
            fired_correct += int(hit)
    return {"event_accuracy": round(correct / max(1, n_ev), 4),
            "n_events": n_ev, "n_fired": fired,
            "precision_when_fired": (round(fired_correct / fired, 4)
                                     if fired else None),
            "base_rate_keep_champion": round(
                float((prefer_by_event == 0).mean()), 4)}


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


def cluster_boot_auc(y, p, seeds):
    """AUC CI resampling WHOLE SEEDS, not rows.

    Tie plies inside one game are not independent — they sit on one board
    trajectory — so a row bootstrap would report a CI several times too narrow
    and turn a coin-flip into a verdict.
    """
    from sklearn.metrics import roc_auc_score
    uniq = np.unique(seeds)
    rng = np.random.default_rng(SPLIT_RNG + 999)
    out = []
    for _ in range(N_BOOT):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([np.flatnonzero(seeds == s) for s in pick])
        if len(np.unique(y[idx])) < 2:
            continue
        out.append(roc_auc_score(y[idx], p[idx]))
    if not out:
        return None
    return [round(float(np.quantile(out, 0.025)), 4),
            round(float(np.quantile(out, 0.975)), 4)]


def run_target(name, X, y, seeds, tr, te, feat_names):
    res = {}
    for kind in ("logit", "gbm"):
        r = fit_eval(X[tr], y[tr], X[te], y[te], kind)
        if isinstance(r, dict):
            res[kind] = r
            continue
        stats, p, coef = r
        stats["auc_ci95_seed_boot"] = cluster_boot_auc(y[te], p, seeds[te])
        res[kind] = stats
        if coef is not None:
            top = sorted(zip(feat_names, coef), key=lambda kv: -abs(kv[1]))[:8]
            res[kind]["top_coefs"] = [[k, round(float(v), 5)] for k, v in top]
            res["_logit_pred"] = p
        else:
            res["_gbm_pred"] = p
    # SHUFFLE CONTROL, REPEATED.  A SINGLE shuffle draw is not a control: a
    # logistic fit on permuted labels yields an essentially RANDOM direction in
    # 31-dim feature space, and the test AUC of a random direction against a
    # label that depends strongly on a few of those features is centred on 0.5
    # but with a wide spread — one draw measured 0.63 on planted-signal smoke
    # data and would have read as a leak.  The null is the DISTRIBUTION.
    nulls = []
    for i in range(N_SHUFFLE):
        rng = np.random.default_rng(SPLIT_RNG + 1 + i)
        ysh = y.copy()
        ysh[tr] = rng.permutation(ysh[tr])
        r = fit_eval(X[tr], ysh[tr], X[te], y[te], "logit")
        if not isinstance(r, dict):
            nulls.append(r[0]["auc"])
    if nulls:
        res["shuffle_null"] = {
            "n_draws": len(nulls),
            "mean": round(float(np.mean(nulls)), 4),
            "max": round(float(np.max(nulls)), 4),
            "q95": round(float(np.quantile(nulls, 0.95)), 4),
            "draws": [round(float(v), 4) for v in nulls]}
        real = res.get("logit", {}).get("auc")
        if real is not None:
            res["beats_null_band"] = bool(real > np.max(nulls))
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
                      if k in ("logit", "gbm", "shuffle_null",
                               "beats_null_band")}, indent=1))

    # ---- LISTWISE: every tie event, including the 3- and 4-board ones ----
    LX, Ly, Lev, Lseed, Lmarg, Lctx, pref_ev, seed_ev = \
        build_listwise_design(rows)
    LXf = np.concatenate([LX, Lctx], axis=1)
    ltr, lte = seed_split(Lseed)
    doc["listwise_design"] = {
        "n_alternative_rows": int(len(LX)),
        "n_events": int(len(pref_ev)),
        "event_prefer_rate": round(float(pref_ev.mean()), 4),
        "row_positive_rate": round(float(Ly.mean()), 4)}
    print("\nlistwise design:", json.dumps(doc["listwise_design"]))
    rl = run_target("T1_listwise", LXf, Ly, Lseed, ltr, lte, names_f)
    lp = rl.pop("_logit_pred", None)
    rl.pop("_gbm_pred", None)
    doc["T1_listwise"] = rl
    print("\nT1 LISTWISE (rank the rollout's board above the other "
          "alternatives), all tie events:")
    print(json.dumps(rl, indent=1))

    if lp is not None:
        # Re-index the test rows to a contiguous event numbering, then sweep the
        # firing threshold.  tau is the silicon knob: it sets how often the
        # distilled term is allowed to overrule the champion.
        ev_te = Lev[lte]
        remap = {e: i for i, e in enumerate(sorted(set(ev_te.tolist())))}
        ev_c = np.array([remap[e] for e in ev_te])
        pref_te = np.array([pref_ev[e] for e in sorted(set(ev_te.tolist()))])
        sweep = []
        for tau in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
            d = event_decision_accuracy(lp, Ly[lte], ev_c, pref_te, tau)
            d["tau"] = tau
            sweep.append(d)
        doc["event_decision_sweep"] = sweep
        print("\nEVENT-LEVEL DECISION MATCH (does the comparator pick the "
              "rollout's board?):")
        for d in sweep:
            print(f"  tau={d['tau']}: acc={d['event_accuracy']} "
                  f"fired={d['n_fired']}/{d['n_events']} "
                  f"prec_when_fired={d['precision_when_fired']} "
                  f"(keep-champion base rate {d['base_rate_keep_champion']})")
        doc["calibration_T1_listwise"] = calibration(lp, Lmarg[lte])
        print("\ncalibration (listwise score vs realized rollout margin):")
        print(json.dumps(doc["calibration_T1_listwise"], indent=1))

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
