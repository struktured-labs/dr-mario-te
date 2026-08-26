#!/usr/bin/env python
"""
B1 FLOOR, MEASURED AS A NULL BAND instead of trusting one permutation draw.

WHY: the corpus's single pre-registered `y_shuf` draw is a +2.5 sd unlucky one --
game-level concordance with `y` is 0.4957 / 0.4433 where a null permutation gives
0.4679 / 0.4679.  PREREG_STAGE2's own section-10 A3 amendment already made exactly this
move for the A3 floor after measuring 400 permutations ("every AUC this lane reports is
read against the MEASURED null band ... and not against the single pre-registered
y_shuf draw").  B1 is the same statistic on a refit model, so it gets the same
treatment.  The single-draw number is reported too, never replaced.

The check CAN fail: if the shippable shapes could learn the true label from a permuted
one, the null band would sit near the real AUC and B1 would be genuinely refuted.
A POSITIVE CONTROL is included -- a 20% game-level label leak, the leak size
PREREG_STAGE2 measured as this floor's detection limit -- and it must land ABOVE the
null band.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s2_shippable import (OUT, auc, cols, load, FEAT_SCALE, _fit_additive,  # noqa
                          hinge_compress)
import models as M
from sklearn.ensemble import HistGradientBoostingClassifier

B = 20
SEL = json.load(open(os.path.join(OUT, "selected.json")))["selected"]


def game_permute(seed_arr, y, rng):
    """Permute the label over GAMES -- the same operation build_s2_corpus does, but
    with a fresh rng each time."""
    g, inv = np.unique(seed_arr, return_inverse=True)
    gy = np.array([y[inv == i][0] for i in range(len(g))])
    return gy[rng.permutation(len(g))][inv]


def leak_labels(seed_arr, y, frac, rng):
    """POSITIVE CONTROL: a game-level label leak of size `frac`."""
    g, inv = np.unique(seed_arr, return_inverse=True)
    gy = np.array([y[inv == i][0] for i in range(len(g))])
    perm = gy[rng.permutation(len(g))]
    keep = rng.random(len(g)) < frac
    return np.where(keep, gy, perm)[inv]


def fit_score(shape, Xtr, ytr, Xho, sizes):
    if shape == "S3":
        m = HistGradientBoostingClassifier(max_iter=32, max_depth=4, max_leaf_nodes=16,
                                           learning_rate=0.2, early_stopping=False,
                                           random_state=0, max_bins=255).fit(Xtr, ytr)
        return m.decision_function(Xho)
    if shape == "S2":
        m = HistGradientBoostingClassifier(max_iter=256, max_depth=1, max_leaf_nodes=2,
                                           learning_rate=0.15, early_stopping=False,
                                           random_state=0, max_bins=255).fit(Xtr, ytr)
        return m.decision_function(Xho)
    if shape in ("S1b", "S1"):
        luts, _ = _fit_additive(Xtr.astype(np.uint8), ytr, SEL, sizes, 800)
        mm = M.AdditiveLUT(SEL, sizes, luts)
        return mm.raw(Xho.astype(np.uint8))
    if shape == "S0":
        j = SEL.index("d_spawn_h")
        luts, _ = _fit_additive(Xtr[:, [j]].astype(np.uint8), ytr, ["d_spawn_h"],
                                [sizes[j]], 400)
        mm = M.AdditiveLUT(["d_spawn_h"], [sizes[j]], luts)
        return mm.raw(Xho[:, [j]].astype(np.uint8))
    raise KeyError(shape)


def main():
    d = load(with_holdout=True)
    tr, ho = d.hold == 0, d.hold == 1
    sizes = [{"MAXH": 16, "HOLES": 40, "SPAWN": 8, "d_spawn_h": 16,
              "d_gvuln_mass": 40, "x_jagged": 73, "x_hvar": 52,
              "e_escape_routes": 8}[f] + 1 for f in SEL]
    Xq, _ = M.quantise_features(cols(d, SEL), [FEAT_SCALE[f] for f in SEL])
    Xtr, Xho = Xq[tr].astype(np.float64), Xq[ho].astype(np.float64)
    ytr, yho = d.y[tr].astype(int), d.y[ho].astype(int)
    str_ = d.seed[tr]
    out = {"B": B, "shapes": {}}

    for shape in ["S0", "S1", "S1b", "S2", "S3"]:
        nulls = []
        for b in range(B):
            rng = np.random.default_rng(90000 + b)
            yp = game_permute(str_, ytr, rng)
            nulls.append(auc(fit_score(shape, Xtr, yp, Xho, sizes), yho))
        rng = np.random.default_rng(777)
        leak = auc(fit_score(shape, Xtr, leak_labels(str_, ytr, 0.20, rng), Xho, sizes),
                   yho)
        real = auc(fit_score(shape, Xtr, ytr, Xho, sizes), yho)
        n = np.array(nulls)
        out["shapes"][shape] = {
            "real_auc": real, "null_mean": float(n.mean()),
            "null_p95": float(np.percentile(n, 95)), "null_max": float(n.max()),
            "null_min": float(n.min()), "nulls": [float(v) for v in n],
            "leak20pct_positive_control": leak,
            "B1_margin_vs_null_mean": real - float(n.mean()),
            "B1_margin_vs_null_p95": real - float(np.percentile(n, 95)),
            "positive_control_fires": bool(leak > np.percentile(n, 95))}
        print(f"[b1null] {shape:4s} real {real:.4f} null mean {n.mean():.4f} "
              f"p95 {np.percentile(n,95):.4f} max {n.max():.4f} | leak20% {leak:.4f} "
              f"fires={leak > np.percentile(n,95)} | B1 margin "
              f"{real - n.mean():+.4f}", flush=True)

    with open(os.path.join(OUT, "b1_null.json"), "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
