#!/usr/bin/env python
"""
depth4-transfer: mine a compact structural signature from d4-vs-d3 disagreements.

Joins the existing depth4/ phase-3 adjudication corpus:
  - experiments/depth4/results/disagree_nes_k3-6_corpus.jsonl  (board state @ disagreement)
  - experiments/depth4/results/adjudicate_rows.jsonl           (outcome of playing a3 vs a4,
    both continued by d3 afterward, on the identical true capsule stream)

on (seed, k), builds hand features from the board state + the disagreement itself, defines a
binary label "was d4's move better than d3's, net of downstream d3 steering", and asks whether
a cheap probe (logistic regression / shallow decision tree) can separate the two classes on
BOARD FEATURES ALONE, using GroupKFold by seed (a game is the unit — matches the clustering
finding already on record in depth4/README.md, avoids leaking one game's positions across the
train/test split).

No new simulation is run. This is a re-analysis of an existing, already-vendored corpus — the
cheapest possible test of the mining hypothesis.
"""
import json
import sys
from collections import defaultdict

import numpy as np

DEPTH4 = "/home/struktured/projects/dr-mario-qa-wt/experiments/depth4"
DISAGREE = f"{DEPTH4}/results/disagree_nes_k3-6_corpus.jsonl"
ADJUDICATE = f"{DEPTH4}/results/adjudicate_rows.jsonl"

NUM_ROWS = 16
NUM_COLS = 8
CENSOR = 300.0   # same convention as depth4/analyze.py: charge non-clears at 300 pills
MARGIN = 8.0     # pill deltas smaller than this are noise-level (search/exec granularity);
                  # rows inside the margin are dropped from the binary label (kept for regression)


def load():
    dis = {}
    for line in open(DISAGREE):
        r = json.loads(line)
        dis[(r["seed"], r["k"])] = r
    adj = [json.loads(line) for line in open(ADJUDICATE)]
    rows = []
    for a in adj:
        key = (a["seed"], a["k"])
        d = dis.get(key)
        if d is None:
            continue
        rows.append((a, d))
    return rows


def col_heights(col):
    """col: 128-len row-major (idx=r*8+c). Returns per-column fill count and topmost filled row."""
    arr = np.array(col, dtype=np.int32).reshape(NUM_ROWS, NUM_COLS)
    fill = (arr != 0)
    counts = fill.sum(axis=0).astype(np.float64)               # cells filled per column
    top = np.where(fill.any(axis=0), fill.argmax(axis=0), NUM_ROWS).astype(np.float64)
    return counts, top


def virus_by_column(vir):
    arr = np.array(vir, dtype=np.int32).reshape(NUM_ROWS, NUM_COLS)
    return arr.sum(axis=0).astype(np.float64)


def color_counts(col, mask_fn):
    arr = np.array(col, dtype=np.int32)
    m = np.array(mask_fn, dtype=bool) if mask_fn is not None else np.ones_like(arr, dtype=bool)
    vals = arr[m]
    return {c: int((vals == c).sum()) for c in (1, 2, 3)}


REGIME_ORD = {"open": 0, "mid": 1, "end": 2}
KINDS = ["col_only", "orient_only", "both"]


def build_row(a, d):
    col = d["col"]
    vir = d["vir"]
    counts, top = col_heights(col)                 # len 8 each
    vbycol = virus_by_column(vir)                   # len 8
    vc_by_color = color_counts(col, vir)             # virus color histogram
    board_fill = float(np.array(col).astype(bool).sum())
    open_cols = int((counts == 0).sum())

    a3, a4 = a["a3"], a["a4"]
    col3, col4 = a3 % NUM_COLS, a4 % NUM_COLS
    var3, var4 = a3 // NUM_COLS, a4 // NUM_COLS
    horiz3, horiz4 = int(var3 >= 2), int(var4 >= 2)

    h3 = counts[col3] if col3 < NUM_COLS else 0.0
    h4 = counts[col4] if col4 < NUM_COLS else 0.0

    cur = d.get("cur", [0, 0])
    nxt = d.get("nxt", [0, 0])

    feat = {
        # global board shape
        "vc": float(d["vc"]),
        "ply": float(d.get("ply", 0)),
        "regime": REGIME_ORD.get(d["regime"], 1),
        "board_fill": board_fill,
        "open_cols": float(open_cols),
        "max_col_h": float(counts.max()),
        "min_col_h": float(counts.min()),
        "std_col_h": float(counts.std()),
        "max_top_row": float(top[top < NUM_ROWS].min()) if (top < NUM_ROWS).any() else float(NUM_ROWS),
        # color balance among remaining viruses
        "v1": float(vc_by_color[1]), "v2": float(vc_by_color[2]), "v3": float(vc_by_color[3]),
        # the disagreement itself, encoded structurally (not as raw column index)
        "kind_col_only": float(a["kind"] == "col_only"),
        "kind_orient_only": float(a["kind"] == "orient_only"),
        "kind_both": float(a["kind"] == "both"),
        "col_dist": float(abs(col3 - col4)),
        "orient_flip": float(horiz3 != horiz4),
        "d4_horiz": float(horiz4),
        "d3_horiz": float(horiz3),
        # THE headline candidate signature: does d4 prefer the shorter (more open) column?
        "d4_targets_shorter_col": float(h4 < h3),
        "d4_targets_taller_col": float(h4 > h3),
        "height_delta_d4_minus_d3": float(h4 - h3),
        "d4_targets_open_col": float(h4 == 0),
        "d3_targets_open_col": float(h3 == 0),
        "virus_under_d4_col": float(vbycol[col4]) if col4 < NUM_COLS else 0.0,
        "virus_under_d3_col": float(vbycol[col3]) if col3 < NUM_COLS else 0.0,
        # pill colors vs board state
        "cur_match": float(cur[0] == cur[1]),
        "nxt_match": float(nxt[0] == nxt[1]),
        "cur0_scarce": float(vc_by_color.get(cur[0], 0) <= 1) if cur[0] in (1, 2, 3) else 0.0,
    }
    return feat


def build_label(a):
    cost3 = a["pills3"] if a["res3"] == "clear" else CENSOR
    cost4 = a["pills4"] if a["res4"] == "clear" else CENSOR
    value = cost3 - cost4     # positive => d4 cheaper => d4 better
    return value


def main():
    rows = load()
    print(f"joined rows: {len(rows)} (disagree corpus x adjudicate rows on seed,k)")

    feats = []
    values = []
    seeds = []
    for a, d in rows:
        feats.append(build_row(a, d))
        values.append(build_label(a))
        seeds.append(a["seed"])
    values = np.array(values)
    seeds = np.array(seeds)

    keys = sorted(feats[0].keys())
    X_all = np.array([[f[k] for k in keys] for f in feats], dtype=np.float64)

    # ---- label: binary, margin-gated (drop noise-level ties) ----
    label = np.where(values > MARGIN, 1, np.where(values < -MARGIN, 0, -1))
    keep = label >= 0
    n_drop = (~keep).sum()
    X = X_all[keep]
    y = label[keep]
    grp = seeds[keep]
    print(f"binary label: {y.sum()} d4-better / {(1 - y).sum()} d3-better "
          f"(dropped {n_drop} within +/-{MARGIN} pill margin as noise)")
    print(f"distinct games (seeds) in labeled set: {len(set(grp))}")

    if len(set(grp)) < 5 or min(np.bincount(y.astype(int))) < 10:
        print("INSUFFICIENT DATA for a held-out probe (games or class count too small).")
        sys.exit(0)

    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler

    n_splits = min(5, len(set(grp)))
    gkf = GroupKFold(n_splits=n_splits)

    results = defaultdict(list)
    fold_n = []
    for tr, te in gkf.split(X, y, groups=grp):
        if len(set(y[tr])) < 2 or len(set(y[te])) < 2:
            continue
        fold_n.append(len(te))
        scaler = StandardScaler().fit(X[tr])
        Xtr, Xte = scaler.transform(X[tr]), scaler.transform(X[te])

        lr = LogisticRegression(max_iter=2000, C=1.0)
        lr.fit(Xtr, y[tr])
        results["logreg"].append(roc_auc_score(y[te], lr.predict_proba(Xte)[:, 1]))

        dt = DecisionTreeClassifier(max_depth=3, min_samples_leaf=20, random_state=0)
        dt.fit(X[tr], y[tr])
        results["tree_d3"].append(roc_auc_score(y[te], dt.predict_proba(X[te])[:, 1]))

        rf = RandomForestClassifier(n_estimators=200, max_depth=4, min_samples_leaf=10,
                                     random_state=0, n_jobs=2)
        rf.fit(X[tr], y[tr])
        results["forest_d4"].append(roc_auc_score(y[te], rf.predict_proba(X[te])[:, 1]))

    print(f"\nGroupKFold by seed, {n_splits} folds, held-out fold sizes: {fold_n}")
    for name, aucs in results.items():
        aucs = np.array(aucs)
        print(f"  {name:12s} AUC per fold: {[round(x,3) for x in aucs]}  "
              f"mean={aucs.mean():.3f}  min={aucs.min():.3f}")

    # single-feature screen: does any ONE feature alone separate the classes?
    print("\nsingle-feature AUC screen (train=test, upper bound / sanity check only):")
    single = []
    for i, k in enumerate(keys):
        try:
            auc = roc_auc_score(y, X[:, i])
            auc = max(auc, 1 - auc)
        except Exception:
            auc = float("nan")
        single.append((auc, k))
    single.sort(reverse=True)
    for auc, k in single[:8]:
        print(f"  {k:28s} {auc:.3f}")

    # a global feature-importance readout from the full-data forest, for reporting only
    rf_full = RandomForestClassifier(n_estimators=300, max_depth=4, min_samples_leaf=10,
                                      random_state=0, n_jobs=2).fit(X, y)
    order = np.argsort(rf_full.feature_importances_)[::-1]
    print("\nfull-data RF feature importances (descriptive; overfit to the whole corpus):")
    for i in order[:8]:
        print(f"  {keys[i]:28s} {rf_full.feature_importances_[i]:.3f}")

    best_mean = max(np.mean(v) for v in results.values())
    verdict = "ALIVE (>=0.60 held-out AUC)" if best_mean >= 0.60 else "DEAD (<0.60 held-out AUC)"
    print(f"\nbest held-out mean AUC = {best_mean:.3f} -> {verdict}")

    out = {
        "n_rows_joined": len(rows),
        "n_labeled": int(keep.sum()),
        "n_dropped_margin": int(n_drop),
        "n_seeds_labeled": len(set(grp)),
        "class_balance": {"d4_better": int(y.sum()), "d3_better": int((1 - y).sum())},
        "held_out_auc": {k: [float(x) for x in v] for k, v in results.items()},
        "held_out_auc_mean": {k: float(np.mean(v)) for k, v in results.items()},
        "single_feature_auc_top8": [(float(a), k) for a, k in single[:8]],
        "best_held_out_mean_auc": float(best_mean),
        "verdict": verdict,
    }
    with open(f"{sys.path[0]}/results_signature.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {sys.path[0]}/results_signature.json")


if __name__ == "__main__":
    main()
