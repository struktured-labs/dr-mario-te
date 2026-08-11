#!/usr/bin/env python3
"""Exploratory distillation of the historical ORACLE-CLAIR pilot.

This is mechanism mining, not a verdict.  It reconstructs the treatment
trajectory from the pilot's `(seed, ply, trt_action)` flip log without rerunning
any forks, verifies the endpoint and every logged top-4 set, then asks whether
cheap existing post-move features predict the teacher's action at *all* gated
plies.  A label-blind null preserves the exact flip/no-flip dose but permutes
which non-champion alternative is called correct on flip plies.

Why this is different from stage 2: the labels are per-decision counterfactual
oracle choices, not one terminal game label broadcast onto every decision.
The pilot is already disclosed and self-coupled to the legacy Lulu proxy, so
all results are exploratory and must be re-earned under exogenous pressure.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE2 = os.path.dirname(HERE)
EV = os.path.dirname(STAGE2)
QA = os.path.dirname(EV)
for p in (HERE, STAGE2, EV, QA):
    if p not in sys.path:
        sys.path.insert(0, p)

import oracle_arm as O  # noqa: E402
import s2_features as S2F  # noqa: E402
import feature_battery as FBAT  # noqa: E402

DEFAULT_PILOT = ("/home/struktured/projects/dr-mario-oracle-wt/experiments/"
                 "eval47/stage2/oracle/out/pilot_true/seg_030000.jsonl")
_W = {}


def _sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _init_replay(fit):
    os.environ["DR_LULU_FIT"] = fit
    C, model = O.init_rig("lulu")
    _W.update(C=C, model=model)


def _replay(row):
    """Reconstruct one teacher trajectory and return every gated decision."""
    from fb import FB
    import root_search as RS

    seed = int(row["seed"])
    C, model = _W["C"], _W["model"]
    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    logs = {int(f["ply"]): f for f in row["trt"].get("flip_log", [])}
    consumed = set()
    errors = []
    records = []
    env = O.make_env(seed, C["level"])
    res, v_at_topout = "stall", None
    actions = []

    for ply in range(300):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        vals = O._champ_values(col, vir, int(env.cur.a), int(env.cur.b),
                               int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)
        base = O._champ_action(vals, O.CHAMP_ORDER)
        if base is None:
            break
        fires, d_spawn_h, viruses = O.gate_fires(env)
        legal = [int(a) for a in O.CHAMP_ORDER if np.isfinite(vals[int(a)])]
        ranked_i = sorted(range(len(legal)),
                          key=lambda i: (-vals[legal[i]], i))[:O.TOPK]
        cands = [legal[i] for i in ranked_i]

        f = logs.get(ply)
        teacher = int(f["trt_action"]) if f is not None else int(base)
        if f is not None:
            consumed.add(ply)
            if not fires:
                errors.append(f"ply {ply}: logged flip outside gate")
            if int(f["base_action"]) != int(base):
                errors.append(f"ply {ply}: base {base} != log {f['base_action']}")
            if [int(x) for x in f["cands"]] != cands:
                errors.append(f"ply {ply}: top4 {cands} != log {f['cands']}")
            if teacher not in cands:
                errors.append(f"ply {ply}: teacher {teacher} outside top4")

        if fires:
            try:
                teacher_rank = cands.index(teacher)
            except ValueError:
                errors.append(f"ply {ply}: teacher {teacher} outside gated top4")
                teacher_rank = 0
            H = O.heights(env.board.color)
            progress_delta = None
            survival_delta = None
            if f is not None:
                labels = [tuple(int(v) for v in x) for x in f["labels"]]
                progress_delta = labels[teacher_rank][1] - labels[0][1]
                survival_delta = labels[teacher_rank][0] - labels[0][0]
            records.append({
                "seed": seed, "ply": ply,
                "col": np.asarray(col, dtype=np.int8).copy(),
                "vir": np.asarray(vir, dtype=np.int8).copy(),
                "cur": (int(env.cur.a), int(env.cur.b)),
                "nxt": (int(env.nxt.a), int(env.nxt.b)),
                "cands": np.asarray(cands, dtype=np.int8),
                "cand_vals": np.asarray([vals[a] for a in cands], dtype=np.float64),
                "teacher_rank": teacher_rank,
                "was_flip": int(f is not None),
                "viruses_pre": int(viruses), "maxh_pre": int(H.max()),
                "d_spawn_h_pre": int(d_spawn_h), "n_legal": len(legal),
                "progress_delta": progress_delta,
                "survival_delta": survival_delta,
            })

        actions.append(teacher)
        r, v = O._advance(env, teacher, C, seed, model)
        if r is not None:
            res, v_at_topout = r, v
            break

    expected = row["trt"]
    if res != expected["res"] or len(actions) != int(expected["n_plies"]):
        errors.append(f"endpoint {res}/{len(actions)} != "
                      f"{expected['res']}/{expected['n_plies']}")
    missing = sorted(set(logs) - consumed)
    if missing:
        errors.append(f"unconsumed flip plies {missing}")
    return {"seed": seed, "records": records, "errors": errors,
            "endpoint": f"{res}/{len(actions)}", "n_flips": len(logs)}


def reconstruct(rows, fit, workers):
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_replay,
                             initargs=(fit,)) as ex:
        games = list(ex.map(_replay, rows, chunksize=1))
    errors = [{"seed": g["seed"], "errors": g["errors"]}
              for g in games if g["errors"]]
    recs = [r for g in games for r in g["records"]]
    return games, recs, errors


def feature_matrix(recs):
    """Expand top-4 actions through the existing stage-2 feature instrument."""
    ndec = len(recs)
    n = ndec * O.TOPK
    cols = np.repeat(np.stack([r["col"] for r in recs]), O.TOPK, axis=0)
    virs = np.repeat(np.stack([r["vir"] for r in recs]), O.TOPK, axis=0)
    cura = np.repeat(np.array([r["cur"][0] for r in recs], dtype=np.int8), O.TOPK)
    curb = np.repeat(np.array([r["cur"][1] for r in recs], dtype=np.int8), O.TOPK)
    actions = np.concatenate([r["cands"] for r in recs]).astype(np.int64)

    f11 = np.zeros((n, 11), dtype=np.int64)
    nvir_post = np.zeros(n, dtype=np.int64)
    posts = np.zeros((n, 128), dtype=np.int8)
    ok = np.zeros(n, dtype=np.int8)
    pre11 = np.zeros((n, 11), dtype=np.int64)
    prenvir = np.zeros(n, dtype=np.int64)
    expand, _all32, fl = S2F.build_expander()
    expand(cols, virs, cura, curb, actions, fl, f11, nvir_post, posts,
           ok, pre11, prenvir)
    if not np.all(ok == 1):
        raise RuntimeError(f"teacher corpus contains {(ok == 0).sum()} illegal actions")

    Hpost = FBAT.heights_from_boards(posts)
    Hpre = FBAT.heights_from_boards(cols)
    nlegal = np.repeat(np.array([r["n_legal"] for r in recs], dtype=np.int32),
                       O.TOPK)
    cand = FBAT.candidate_features(posts, Hpost, Hpre, nlegal)
    post26 = np.concatenate(
        [f11.astype(np.float64)]
        + [np.asarray(cand[k], dtype=np.float64)[:, None]
           for k in S2F.CAND_NAMES], axis=1)

    occ_pre = np.count_nonzero(cols, axis=1)
    occ_post = np.count_nonzero(posts, axis=1)
    vals = np.concatenate([r["cand_vals"] for r in recs])
    best = np.repeat(np.array([r["cand_vals"][0] for r in recs]), O.TOPK)
    gap = np.maximum(0.0, best - vals)
    rank = np.tile(np.arange(O.TOPK), ndec)
    act_var, act_col = actions // 8, actions % 8
    state = np.column_stack([
        np.repeat([r["viruses_pre"] for r in recs], O.TOPK),
        np.repeat([r["maxh_pre"] for r in recs], O.TOPK),
        np.repeat([r["d_spawn_h_pre"] for r in recs], O.TOPK),
    ]).astype(np.float64)
    extra = np.column_stack([
        f11 - pre11,
        prenvir - nvir_post,
        occ_pre + 2 - occ_post,
        np.log1p(gap), rank, act_var, act_col, state,
    ]).astype(np.float64)
    extra_names = (["delta_" + x for x in S2F.NAMES11]
                   + ["virus_progress_now", "cells_cleared_now",
                      "log1p_champ_gap", "champ_rank", "action_var",
                      "action_col", "viruses_pre", "maxh_pre",
                      "d_spawn_h_pre"])
    X = np.concatenate([post26, extra], axis=1)
    names = list(S2F.FEAT_NAMES) + extra_names

    teacher_rank = np.array([r["teacher_rank"] for r in recs], dtype=np.int8)
    y = (rank == np.repeat(teacher_rank, O.TOPK)).astype(np.int8)
    did = np.repeat(np.arange(ndec), O.TOPK)
    groups = np.repeat(np.array([r["seed"] for r in recs]), O.TOPK)
    flip = np.array([r["was_flip"] for r in recs], dtype=bool)
    return X, names, y, did, groups, teacher_rank, flip


def null_ranks(recs):
    """Dose-matched label-blind null: preserve flip mask, random alternative."""
    out = []
    for r in recs:
        if not r["was_flip"]:
            out.append(0)
            continue
        rng = random.Random((int(r["seed"]) << 16) ^ int(r["ply"])
                            ^ 0xD15A11)
        out.append(rng.choice((1, 2, 3)))
    return np.asarray(out, dtype=np.int8)


def _metrics(scores, did, teacher_rank, flip):
    chosen = []
    for d in np.unique(did):
        ix = np.flatnonzero(did == d)
        chosen.append(int(np.argmax(scores[ix])))
    chosen = np.asarray(chosen, dtype=np.int8)
    return {
        "action_accuracy": float(np.mean(chosen == teacher_rank)),
        "flip_recall": float(np.mean(chosen[flip] == teacher_rank[flip])),
        "noflip_retention": float(np.mean(chosen[~flip] == 0)),
        "perturb_rate": float(np.mean(chosen != 0)),
    }


def crossval(X, y, did, groups, teacher_rank, flip, kind):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    scores = np.zeros(y.shape[0], dtype=np.float64)
    cv = GroupKFold(n_splits=5)
    for tr, te in cv.split(X, y, groups):
        if kind == "linear":
            model = make_pipeline(
                StandardScaler(),
                LogisticRegression(C=0.2, max_iter=1000, class_weight="balanced"))
        else:
            depth = int(kind.removeprefix("hgb"))
            model = HistGradientBoostingClassifier(
                max_depth=depth, max_iter=140, learning_rate=0.07,
                min_samples_leaf=30, l2_regularization=2.0,
                class_weight="balanced", random_state=20260811)
        model.fit(X[tr], y[tr])
        scores[te] = model.predict_proba(X[te])[:, 1]
    return _metrics(scores, did, teacher_rank, flip)


def decision_matrix(X, names):
    """One row/decision: base candidate plus each alternative-minus-base."""
    ndec = X.shape[0] // O.TOPK
    z = X.reshape(ndec, O.TOPK, X.shape[1])
    blocks = [z[:, 0]] + [z[:, r] - z[:, 0] for r in range(1, O.TOPK)]
    out_names = (["base_" + n for n in names]
                 + [f"rank{r+1}_minus_base_{n}" for r in range(1, O.TOPK)
                    for n in names])
    return np.concatenate(blocks, axis=1), out_names


def shuffled_teacher(recs):
    """Exact-dose null: permute flip locations, randomise non-base choices."""
    n = len(recs)
    nflip = sum(r["was_flip"] for r in recs)
    order = list(range(n))
    random.Random(20260811).shuffle(order)
    flip = np.zeros(n, dtype=bool)
    flip[order[:nflip]] = True
    rank = np.zeros(n, dtype=np.int8)
    for d in np.flatnonzero(flip):
        r = recs[int(d)]
        rank[d] = random.Random((int(r["seed"]) << 16) ^ int(r["ply"])
                                ^ 0x51A7E).choice((1, 2, 3))
    return flip, rank


def structured_crossval(Xd, Xcand, groups_dec, flip, teacher_rank, kind):
    """Predict flip location, then the winning non-base rank."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, roc_auc_score
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    def model():
        if kind == "linear":
            return make_pipeline(
                StandardScaler(),
                LogisticRegression(C=0.1, max_iter=1500,
                                   class_weight="balanced"))
        depth = int(kind.removeprefix("hgb"))
        return HistGradientBoostingClassifier(
            max_depth=depth, max_iter=180, learning_rate=0.06,
            min_samples_leaf=25, l2_regularization=3.0,
            class_weight="balanced", random_state=20260811)

    ndec = Xd.shape[0]
    fp = np.zeros(ndec, dtype=np.float64)
    flip_pred = np.zeros(ndec, dtype=bool)
    alt_pred = np.zeros(ndec, dtype=np.int8)
    cv = GroupKFold(n_splits=5)
    for tr, te in cv.split(Xd, flip.astype(np.int8), groups_dec):
        fm = model()
        fm.fit(Xd[tr], flip[tr].astype(np.int8))
        fp[te] = fm.predict_proba(Xd[te])[:, 1]
        # Calibrate dose using only TRAIN prevalence; select that many highest
        # scores in the held-out fold.  No test labels choose the threshold.
        take = int(round(float(flip[tr].mean()) * len(te)))
        if take:
            pick = te[np.argsort(fp[te], kind="mergesort")[-take:]]
            flip_pred[pick] = True

        train_flip = tr[flip[tr]]
        rows = np.concatenate(
            [np.arange(d * O.TOPK + 1, d * O.TOPK + O.TOPK)
             for d in train_flip])
        ay = np.concatenate(
            [np.arange(1, O.TOPK) == teacher_rank[d] for d in train_flip]
        ).astype(np.int8)
        am = model()
        am.fit(Xcand[rows], ay)
        for d in te:
            ix = np.arange(d * O.TOPK + 1, d * O.TOPK + O.TOPK)
            alt_pred[d] = 1 + int(np.argmax(am.predict_proba(Xcand[ix])[:, 1]))

    policy = np.where(flip_pred, alt_pred, 0).astype(np.int8)
    tp = int(np.sum(flip_pred & flip))
    pp = int(flip_pred.sum())
    return {
        "flip_roc_auc": float(roc_auc_score(flip, fp)),
        "flip_average_precision": float(average_precision_score(flip, fp)),
        "flip_prevalence": float(flip.mean()),
        "perturb_rate": float(flip_pred.mean()),
        "flip_recall": tp / max(1, int(flip.sum())),
        "flip_precision": tp / max(1, pp),
        "alternative_accuracy_on_true_flips": float(
            np.mean(alt_pred[flip] == teacher_rank[flip])),
        "combined_action_accuracy": float(np.mean(policy == teacher_rank)),
        "noflip_retention": float(np.mean(policy[~flip] == 0)),
    }


def univariate(recs, X, names):
    """At flip plies only, which single feature points toward the teacher?"""
    flip_ids = [i for i, r in enumerate(recs) if r["was_flip"]]
    rows = []
    for j, nm in enumerate(names):
        delta = np.array([X[d * O.TOPK + recs[d]["teacher_rank"], j]
                          - X[d * O.TOPK, j] for d in flip_ids])
        pos = int((delta > 0).sum())
        neg = int((delta < 0).sum())
        tie = int((delta == 0).sum())
        agree = max(pos, neg) / max(1, len(delta))
        rows.append({"feature": nm,
                     "direction": "+" if pos >= neg else "-",
                     "agreement": agree, "positive": pos,
                     "negative": neg, "ties": tie,
                     "median_delta": float(np.median(delta))})
    return sorted(rows, key=lambda r: (-r["agreement"], r["feature"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", default=DEFAULT_PILOT)
    ap.add_argument("--fit", default=os.environ.get("DR_LULU_FIT"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0,
                    help="implementation smoke: first N pilot rows; 0 = all")
    ap.add_argument("--out", default=os.path.join(HERE, "out",
                                                   "oracle_teacher_distill.json"))
    a = ap.parse_args()
    if not a.fit:
        raise SystemExit("--fit or DR_LULU_FIT is required")
    a.pilot, a.fit = os.path.abspath(a.pilot), os.path.abspath(a.fit)
    rows = [json.loads(x) for x in open(a.pilot) if x.strip()]
    if a.limit:
        rows = rows[:a.limit]

    t0 = time.monotonic()
    games, recs, errors = reconstruct(rows, a.fit, a.workers)
    if errors:
        raise SystemExit("REPLAY GATE FAILED: " + json.dumps(errors[:3]))
    X, names, y, did, groups, trank, flip = feature_matrix(recs)
    Xd, decision_names = decision_matrix(X, names)
    groups_dec = np.array([r["seed"] for r in recs])
    baseline = {"action_accuracy": float(np.mean(trank == 0)),
                "flip_recall": 0.0, "noflip_retention": 1.0,
                "perturb_rate": 0.0}

    models = {k: crossval(X, y, did, groups, trank, flip, k)
              for k in ("linear", "hgb2", "hgb3", "hgb4")}
    nrank = null_ranks(recs)
    yn = (np.tile(np.arange(O.TOPK), len(recs))
          == np.repeat(nrank, O.TOPK)).astype(np.int8)
    null_models = {k: crossval(X, yn, did, groups, nrank, flip, k)
                   for k in ("linear", "hgb2", "hgb3", "hgb4")}
    structured = {k: structured_crossval(Xd, X, groups_dec, flip, trank, k)
                  for k in ("linear", "hgb2", "hgb3", "hgb4")}
    null_flip, null_rank = shuffled_teacher(recs)
    structured_null = {
        k: structured_crossval(Xd, X, groups_dec, null_flip, null_rank, k)
        for k in ("linear", "hgb2", "hgb3", "hgb4")}

    # Full-fit random forest only for a readable feature-importance hypothesis;
    # cross-validated metrics above own every predictive number.
    from sklearn.ensemble import RandomForestClassifier
    rf = RandomForestClassifier(n_estimators=300, max_depth=8,
                                min_samples_leaf=20, class_weight="balanced_subsample",
                                random_state=20260811, n_jobs=a.workers)
    rf.fit(X, y)
    importance = sorted(
        ({"feature": nm, "importance": float(v)}
         for nm, v in zip(names, rf.feature_importances_)),
        key=lambda r: -r["importance"])
    rf_flip = RandomForestClassifier(
        n_estimators=300, max_depth=8, min_samples_leaf=20,
        class_weight="balanced_subsample", random_state=20260811,
        n_jobs=a.workers)
    rf_flip.fit(Xd, flip.astype(np.int8))
    flip_importance = sorted(
        ({"feature": nm, "importance": float(v)}
         for nm, v in zip(decision_names, rf_flip.feature_importances_)),
        key=lambda r: -r["importance"])

    progress = collections.Counter(
        int(r["progress_delta"]) for r in recs if r["was_flip"])
    survival = collections.Counter(
        int(r["survival_delta"]) for r in recs if r["was_flip"])
    result = {
        "authority": "EXPLORATORY_ONLY_seen_historical_self_coupled_pilot",
        "code": {"path": os.path.abspath(__file__),
                 "sha256": _sha256(os.path.abspath(__file__))},
        "pilot": {"path": a.pilot, "sha256": _sha256(a.pilot),
                  "n_games": len(rows)},
        "fit": {"path": a.fit, "sha256": _sha256(a.fit)},
        "replay_gate": {"games_exact": len(games), "errors": errors,
                        "logged_flips": sum(g["n_flips"] for g in games)},
        "corpus": {"gated_decisions": len(recs),
                   "candidate_rows": int(X.shape[0]),
                   "flips": int(flip.sum()),
                   "flip_rate_gated": float(flip.mean()),
                   "progress_delta": dict(sorted(progress.items())),
                   "survival_delta": dict(sorted(survival.items()))},
        "champion_baseline": baseline,
        "crossval_true_teacher": models,
        "crossval_dose_matched_label_blind_null": null_models,
        "structured_crossval_true_teacher": structured,
        "structured_crossval_exact_dose_shuffled_teacher": structured_null,
        "top_univariate_flip_directions": univariate(recs, X, names)[:20],
        "full_fit_rf_importance_hypothesis_only": importance[:25],
        "full_fit_flip_rf_importance_hypothesis_only": flip_importance[:25],
        "seconds": round(time.monotonic() - t0, 1),
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps({"replay_gate": result["replay_gate"],
                      "corpus": result["corpus"],
                      "champion": baseline, "true": models,
                      "null": null_models,
                      "structured_true": structured,
                      "structured_null": structured_null,
                      "top_features": importance[:10],
                      "top_flip_features": flip_importance[:10],
                      "seconds": result["seconds"]}, indent=1))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
