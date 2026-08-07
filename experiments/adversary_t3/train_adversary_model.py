#!/usr/bin/env python3
"""Train the off-policy value model: P(champion dies within N pills | features).

MODEL CHOICE, justified once here: sklearn HistGradientBoostingClassifier
(histogram-based gradient-boosted trees, same family as LightGBM/XGBoost) over a
deep net, because (1) the feature space is 15-dimensional, hand-built, tabular --
exactly the regime where tree ensembles are the sample-efficient, well-understood
default, not a deep net; (2) it is directly INSPECTABLE via permutation
importance, and inspectability is not a nice-to-have here -- the deliverable
itself is "what did the adversary learn to exploit"; (3) trains in seconds on
tens of thousands of rows with no architecture search, so iteration is cheap;
(4) handles the severe class imbalance (champion deaths are rare) via explicit
sample weighting, done below rather than assumed.

SPLIT BY SEED, NOT BY ROW. Rows from the same game are highly correlated (same
board trajectory); a row-level train/test split would leak game identity across
the split and overstate held-out performance. The split held here is by SEED --
entire games go to one side or the other -- matching the overfitting-check
discipline used throughout this tier (measure_fourway.py's TRAIN/HELDOUT seeds).
"""
from __future__ import annotations

import os
# Cap BLAS/OpenMP thread pools BEFORE importing numpy/sklearn -- under this
# box's CPU oversubscription (multiple 6-worker jobs from other agents already
# running), sklearn's own internal parallelism (HistGradientBoostingClassifier,
# permutation_importance) was OBSERVED to thrash rather than help: a first
# attempt at n_jobs=2 ran >5 min on a ~35K-row, 15-feature dataset that should
# take seconds, and killing + capping threads was the fix, not more workers.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "2")
import json
import glob
import time
import argparse
import numpy as np

DATA_DIR = "/mnt/data/drmario_adversary_t3/replay_buffer"
CKPT_DIR = "/mnt/data/drmario_adversary_t3/checkpoints"

import sys
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from adversary_features import FEATURE_NAMES


def load_corpus(data_dir=DATA_DIR):
    rows = []
    for path in sorted(glob.glob(os.path.join(data_dir, "*.jsonl"))):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue   # tolerate a truncated last line from a killed worker
    return rows


def seed_split(rows, heldout_frac=0.2, seed=20260806):
    """Split by SEED (whole games), STRATIFIED on whether a seed has ANY positive
    row. Champion deaths are rare enough (observed: 2 of 445 game-seeds in this
    tier's corpus) that a plain random seed split has real odds of putting EVERY
    positive-bearing seed on one side -- happened on the first run here (0
    positives in train, all 32 in held-out, silently degenerate). Positive-
    bearing and negative-only seeds are now split separately at heldout_frac,
    each guaranteed >=1 seed per side once there are >=2 seeds of that kind."""
    rng = np.random.default_rng(seed)
    pos_seeds = sorted({r["seed"] for r in rows if r["label"] == 1})
    all_seeds = {r["seed"] for r in rows}
    neg_seeds = sorted(all_seeds - set(pos_seeds))

    def split_group(group):
        group = list(group)
        rng.shuffle(group)
        n = len(group)
        n_held = max(1, min(n - 1, int(round(n * heldout_frac)))) if n >= 2 else 0
        return set(group[n_held:]), set(group[:n_held])

    train_pos, held_pos = split_group(pos_seeds)
    train_neg, held_neg = split_group(neg_seeds)
    train_seeds = train_pos | train_neg
    held_seeds = held_pos | held_neg
    train = [r for r in rows if r["seed"] in train_seeds]
    held = [r for r in rows if r["seed"] in held_seeds]
    print(f"  seed_split: {len(pos_seeds)} positive-bearing seeds -> "
          f"{len(train_pos)} train / {len(held_pos)} held-out; "
          f"{len(neg_seeds)} negative-only seeds -> "
          f"{len(train_neg)} train / {len(held_neg)} held-out", flush=True)
    return train, held, held_seeds


def to_xy(rows):
    X = np.array([r["features"] for r in rows], dtype=np.float64)
    y = np.array([r["label"] for r in rows], dtype=np.int64)
    return X, y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=DATA_DIR)
    ap.add_argument("--out", default=os.path.join(CKPT_DIR, "adversary_value_model.pkl"))
    ap.add_argument("--heldout-frac", type=float, default=0.2)
    a = ap.parse_args()

    os.makedirs(CKPT_DIR, exist_ok=True)
    t0 = time.time()
    rows = load_corpus(a.data_dir)
    n_total = len(rows)
    n_pos = sum(r["label"] for r in rows)
    n_seeds = len({r["seed"] for r in rows})
    if n_total == 0:
        print("NO DATA -- run gen_rollout_data.py first"); return
    print(f"loaded {n_total} examples from {n_seeds} seeds/games, "
          f"{n_pos} positive ({n_pos/n_total:.2%})", flush=True)

    train_rows, held_rows, held_seeds = seed_split(rows, a.heldout_frac)
    Xtr, ytr = to_xy(train_rows)
    Xho, yho = to_xy(held_rows)
    if len(set(ytr)) < 2:
        print(f"\nTRAIN split has only class {sorted(set(ytr))} present -- "
              f"champion deaths are too rare in this corpus ({n_pos} positive "
              f"rows total) for ANY train/held-out split to guarantee both sides "
              f"see a positive example. This is a genuine data-sparsity finding, "
              f"not a fixable split parameter: report it as such rather than "
              f"training a model that has never seen a positive example.")
        return
    tr_pos_rate = ytr.mean() if len(ytr) else 0.0
    ho_pos_rate = yho.mean() if len(yho) else 0.0
    print(f"train: {len(ytr)} rows ({int(ytr.sum())} pos, {tr_pos_rate:.2%}) / "
          f"held-out: {len(yho)} rows ({int(yho.sum()) if len(yho) else 0} pos, "
          f"{ho_pos_rate:.2%})", flush=True)

    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score, average_precision_score
    from sklearn.inspection import permutation_importance

    pos_rate = ytr.mean() if len(ytr) else 0.5
    pos_rate = max(pos_rate, 1e-6)
    w_pos = 0.5 / pos_rate
    w_neg = 0.5 / (1 - pos_rate)
    sample_weight = np.where(ytr == 1, w_pos, w_neg)

    clf = HistGradientBoostingClassifier(
        max_depth=4, max_iter=80, learning_rate=0.1,
        l2_regularization=1.0, random_state=20260806, early_stopping=True,
        validation_fraction=0.15, n_iter_no_change=10,
    )
    t_fit = time.time()
    clf.fit(Xtr, ytr, sample_weight=sample_weight)
    print(f"  fit done in {time.time()-t_fit:.1f}s", flush=True)

    ptr = clf.predict_proba(Xtr)[:, 1]
    auc_tr = roc_auc_score(ytr, ptr) if len(set(ytr)) > 1 else float("nan")
    ap_tr = average_precision_score(ytr, ptr) if len(set(ytr)) > 1 else float("nan")
    print(f"TRAIN  AUC={auc_tr:.4f}  AP={ap_tr:.4f}", flush=True)

    if len(yho) and len(set(yho)) > 1:
        pho = clf.predict_proba(Xho)[:, 1]
        auc_ho = roc_auc_score(yho, pho)
        ap_ho = average_precision_score(yho, pho)
        print(f"HELDOUT AUC={auc_ho:.4f}  AP={ap_ho:.4f}  "
              f"(n={len(yho)}, {len(held_seeds)} held-out seeds)", flush=True)
    else:
        auc_ho = ap_ho = float("nan")
        print(f"HELDOUT: insufficient positive examples to score "
              f"(n={len(yho)}, pos={int(yho.sum()) if len(yho) else 0})", flush=True)

    # inspectability: permutation importance, SUBSAMPLED and thread-capped.
    # n_jobs=1, n_repeats=2, and a hard cap of 4000 rows -- under this box's CPU
    # oversubscription this step was OBSERVED to run >5 minutes uncapped on a
    # ~35K-row set that should score in seconds; this is an inspectability aid,
    # not the reported metric, so it does not need the full corpus.
    imp_X, imp_y = (Xho, yho) if len(yho) and len(set(yho)) > 1 else (Xtr, ytr)
    if len(imp_y) > 4000:
        rng_sub = np.random.default_rng(0)
        idx = rng_sub.choice(len(imp_y), 4000, replace=False)
        imp_X, imp_y = imp_X[idx], imp_y[idx]
    t_pi = time.time()
    pi = permutation_importance(clf, imp_X, imp_y, n_repeats=2, random_state=0,
                                scoring="average_precision", n_jobs=1)
    print(f"  permutation_importance done in {time.time()-t_pi:.1f}s "
          f"(n={len(imp_y)})", flush=True)
    order = np.argsort(pi.importances_mean)[::-1]
    print("\nfeature importance (permutation, drop in average-precision):")
    for i in order:
        print(f"  {FEATURE_NAMES[i]:<20} {pi.importances_mean[i]:+.4f} "
              f"(+/-{pi.importances_std[i]:.4f})")

    import pickle
    with open(a.out, "wb") as fh:
        pickle.dump({"model": clf, "feature_names": FEATURE_NAMES}, fh)
    meta = {
        "n_total": n_total, "n_pos": n_pos, "n_seeds": n_seeds,
        "n_train": len(ytr), "n_heldout": len(yho), "n_heldout_seeds": len(held_seeds),
        "auc_train": auc_tr, "ap_train": ap_tr, "auc_heldout": auc_ho, "ap_heldout": ap_ho,
        "feature_importance": {FEATURE_NAMES[i]: float(pi.importances_mean[i]) for i in order},
        "trained_at": time.time(), "wall_s": time.time() - t0,
    }
    meta_path = a.out + ".meta.json"
    with open(meta_path, "w") as fh:
        json.dump(meta, fh, indent=2)
    print(f"\nsaved model -> {a.out}\nsaved meta  -> {meta_path}\n({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
