#!/usr/bin/env python3
"""STAGE 2 corpus description (PREREG_STAGE2.md @ b9725fc).

Structural description ONLY. No model is fitted here and the holdout is not
opened: every label-associated statistic is computed on TRAIN rows.

The one thing this file exists to prove is the fix for recon A's ★★★ COVERAGE
COLLAPSE: stage 1's corpus had ZERO fatal decisions below max_height 13, so a
leaf evaluator fitted on it was extrapolating over ~95% of real play -- exactly
the population where the STRUCTURAL LAW says breakage is decided. The height
histogram below is the receipt.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")

END_KIND = {"clear": 0, "step_clear": 1, "garbage_clear": 2, "step_topout": 3,
            "garbage_topout": 4, "stall": 5, "choose_none": 6}
EK_NAME = {v: k for k, v in END_KIND.items()}
MECH_NAME = {0: "T_GARB", 1: "T_PLACE", 2: "T_TRUNC", 3: "T_NOMOVE", 4: "CLEAR"}
BANDS = [(0, 9), (10, 12), (13, 14), (15, 16)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="local")
    a = ap.parse_args()
    rep = {"tag": a.tag, "prereg": "PREREG_STAGE2.md @ b9725fc"}
    parts = {}
    for part in ("fail", "ctrl", "stall"):
        p = os.path.join(RESULTS, f"s2lulu_{part}_{a.tag}.npz")
        if os.path.exists(p):
            z = np.load(p)
            parts[part] = {k: z[k] for k in z.files}

    tot = 0
    for part, d in parts.items():
        n = d["seed"].shape[0]
        tot += n
        g = np.unique(d["seed"]).shape[0]
        mech = {MECH_NAME[int(k)]: int(v) for k, v in
                zip(*np.unique(d["mechanism"], return_counts=True))}
        ek = {EK_NAME[int(k)]: int(v) for k, v in
              zip(*np.unique(d["end_kind"], return_counts=True))}
        rep[part] = {
            "decisions": n, "games": g, "decisions_per_game": round(n / g, 1),
            "mechanism_decisions": mech, "end_kind_decisions": ek,
            "y1": int((d["y"] == 1).sum()), "y0": int((d["y"] == 0).sum()),
            "y_excluded": int((d["y"] == -1).sum()),
            "holdout_decisions": int(d["hold"].sum()),
        }
    rep["decisions_total"] = tot

    # ---- THE COVERAGE RECEIPT ------------------------------------------------
    cov = {}
    for part, d in parts.items():
        h = d["max_height"].astype(int)
        row = {}
        for lo, hi in BANDS:
            m = (h >= lo) & (h <= hi)
            row[f"h{lo}-{hi}"] = {"n": int(m.sum()),
                                  "pct": round(100 * m.mean(), 2)}
        row["min"], row["max"] = int(h.min()), int(h.max())
        cov[part] = row
    # target class alone (y==1) -- the direct comparison against stage 1's
    # "ZERO fatal decisions below h=13"
    df = parts["fail"]
    hp = df["max_height"][df["y"] == 1].astype(int)
    cov["TARGET_CLASS_y1"] = {
        **{f"h{lo}-{hi}": {"n": int(((hp >= lo) & (hp <= hi)).sum()),
                           "pct": round(100 * ((hp >= lo) & (hp <= hi)).mean(), 2)}
           for lo, hi in BANDS},
        "min": int(hp.min()), "max": int(hp.max()),
        "stage1_comparison": "stage 1 fatal rows: 0 below h=13 (13:38 14:402 "
                             "15:2774 16:5686). Any nonzero count in h0-9 / "
                             "h10-12 here is coverage stage 1 did not have."}
    rep["height_coverage"] = cov

    # ---- t_to_end coverage (attribution looseness is now a SLICE) -----------
    t = df["t_to_end"][df["y"] == 1].astype(int)
    rep["t_to_end_target_class"] = {
        "max": int(t.max()), "median": int(np.median(t)),
        "le2": int((t <= 2).sum()), "le9": int((t <= 9).sum()),
        "gt9": int((t > 9).sum()),
        "note": "stage 1 kept ONLY t_to_end<=9 (K_LAST=10). Rows with t>9 are "
                "decisions stage 1 could not see at all."}

    # ---- split guards -------------------------------------------------------
    allseeds = np.unique(np.concatenate([d["seed"] for d in parts.values()]))
    tr = {int(s) for s in allseeds if s % 10 not in (7, 8, 9)}
    ho = {int(s) for s in allseeds if s % 10 in (7, 8, 9)}
    rep["split"] = {"rule": "hold = seed % 10 in {7,8,9}, BY GAME",
                    "train_games": len(tr), "holdout_games": len(ho),
                    "seed_overlap": len(tr & ho),
                    "holdout_frac_games": round(len(ho) / len(allseeds), 4)}
    assert rep["split"]["seed_overlap"] == 0

    with open(os.path.join(RESULTS, f"s2_corpus_report_{a.tag}.json"), "w") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
