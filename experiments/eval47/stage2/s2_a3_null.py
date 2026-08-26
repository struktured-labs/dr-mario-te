#!/usr/bin/env python3
"""GATE A3 FAILED AS PRE-REGISTERED. This measures the null instead of retuning
the threshold.

WHAT FAILED (s2feat_gates_local.json):
  f_leak vs y        = 1.0000   PASS (>0.95)
  max |AUC-0.5| over the 26 real features vs y_shuf = 0.0119  PASS (<0.05)
  f_leak vs y_shuf   = 0.5291   FAIL -- outside the pre-registered [0.48, 0.52]
  leaky-shuffle mutant max|dev| = 0.0456, did not clear the 0.05 trip point

Both failing numbers are properties of a threshold I guessed, not of the corpus:
the [0.48, 0.52] band and the 0.05 trip point were written for DECISION-level
independence, but this corpus's shuffle is GAME-level over ~1,600 clusters, so
one draw has far more spread than that band allows. Retuning the band after
seeing the result is precisely the post-hoc move the pre-registration exists to
prevent. So instead this script MEASURES the null over B independent game-level
permutations and asks two questions that have answers:

  Q1 IS THE PERMUTATION UNBIASED?  null mean of |AUC-0.5| centred on 0.5 to
     within 0.01 per probed statistic. A biased permutation would mean the
     shuffle is broken and the corpus must be discarded.
  Q2 WHERE DOES THE OBSERVED DRAW SIT?  the observed 0.5291 either falls inside
     the measured null (=> the BAND was wrong) or outside it (=> the CORPUS is
     wrong). Only one of those is a corpus defect.

  Q3 SENSITIVITY: at what leak fraction does the floor detectably move above the
     null p95? That is the gate's real detection limit, and it is a more useful
     number than a pass/fail against a guessed constant.

This is the same amendment stage 1 made to its own G2 (PREREG_PHASE2.md: "the
original G2 wording fixed a 0.03 max threshold ... G2 is amended to test BIAS").
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(HERE)
for _p in (EV, os.path.dirname(EV), os.path.join(EV, "vocab2")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import feature_battery as FBAT  # noqa: E402

RESULTS = os.path.join(HERE, "results")
FEAT_NAMES = FBAT.NAMES11 + FBAT.CAND_NAMES
B = 400
RNG = 20260810


def ranks_of(x):
    """Mid-ranks (ties averaged), so AUC = rank-sum identity is exact."""
    order = np.argsort(x, kind="mergesort")
    xs = x[order]
    r = np.empty(x.shape[0], dtype=np.float64)
    i = 0
    n = xs.shape[0]
    while i < n:
        j = i
        while j + 1 < n and xs[j + 1] == xs[i]:
            j += 1
        r[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return r


def auc_from_ranks(r, ypos, n1, n0):
    return (r[ypos].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "local"
    zf = np.load(os.path.join(RESULTS, f"s2lulu_fail_{tag}.npz"))
    zc = np.load(os.path.join(RESULTS, f"s2lulu_ctrl_{tag}.npz"))
    zx = np.load(os.path.join(RESULTS, f"s2feat_{tag}.npz"))

    y = np.concatenate([zf["y"], zc["y"]])
    seed = np.concatenate([zf["seed"], zc["seed"]])
    hold = np.concatenate([zf["hold"], zc["hold"]])
    leak = np.concatenate([zf["f_leak"], zc["f_leak"]])
    F = np.concatenate([zx["fail_feat"], zx["ctrl_feat"]], axis=0)

    # TRAIN ONLY -- the holdout stays sealed (prereg deviation log entry 1).
    m = (hold == 0) & (y >= 0)
    y, seed, leak, F = y[m], seed[m], leak[m], F[m]
    games, inv = np.unique(seed, return_inverse=True)

    # game-level label without a python loop over rows
    first = np.zeros(games.shape[0], dtype=np.int64)
    first[inv[::-1]] = np.arange(inv.shape[0])[::-1]
    gy = y[first]
    n_g = games.shape[0]
    print(f"[null] train rows {y.shape[0]}  games {n_g} "
          f"({int((gy == 1).sum())}+ / {int((gy == 0).sum())}-)", flush=True)

    # precompute mid-ranks ONCE per statistic (labels change, values do not)
    stats = {"f_leak": ranks_of(leak.astype(np.float64))}
    for k, nm in enumerate(FEAT_NAMES):
        stats[nm] = ranks_of(F[:, k].astype(np.float64))

    rng = np.random.default_rng(RNG)
    null = {k: [] for k in stats}
    nullmax = []
    for b in range(B):
        gp = gy[rng.permutation(n_g)]
        yb = gp[inv]
        pos = yb == 1
        n1 = int(pos.sum())
        n0 = int((yb == 0).sum())
        devs = []
        for nm, r in stats.items():
            a = auc_from_ranks(r, pos, n1, n0)
            null[nm].append(a)
            if nm != "f_leak":
                devs.append(abs(a - 0.5))
        nullmax.append(max(devs))
        if (b + 1) % 100 == 0:
            print(f"[null] {b+1}/{B}", flush=True)

    out = {"B": B, "rng": RNG, "scope": "TRAIN ONLY (holdout sealed)",
           "n_games": int(n_g), "n_rows": int(y.shape[0])}
    # Q1 bias
    bias = {nm: {"null_mean": float(np.mean(v)),
                 "null_sd": float(np.std(v)),
                 "null_p2.5": float(np.percentile(v, 2.5)),
                 "null_p97.5": float(np.percentile(v, 97.5))}
            for nm, v in null.items()}
    out["null_per_statistic"] = bias
    out["Q1_unbiased"] = bool(all(abs(b["null_mean"] - 0.5) < 0.01
                                  for b in bias.values()))
    out["Q1_max_abs_bias"] = float(max(abs(b["null_mean"] - 0.5)
                                       for b in bias.values()))
    # Q2 where the observed draw sits
    obs_leak = 0.5291
    lv = np.array(null["f_leak"])
    out["Q2_observed_leak_vs_yshuf"] = obs_leak
    out["Q2_null_band_leak"] = [bias["f_leak"]["null_p2.5"],
                                bias["f_leak"]["null_p97.5"]]
    out["Q2_inside_null"] = bool(bias["f_leak"]["null_p2.5"] <= obs_leak
                                 <= bias["f_leak"]["null_p97.5"])
    out["Q2_two_sided_p"] = float(np.mean(np.abs(lv - 0.5)
                                          >= abs(obs_leak - 0.5)))
    # family-wise band for the real features (what the gate should test)
    out["family_max_dev_null_p95"] = float(np.percentile(nullmax, 95))
    out["family_max_dev_null_mean"] = float(np.mean(nullmax))
    out["observed_family_max_dev"] = 0.0119
    out["observed_inside_family_null"] = bool(
        0.0119 <= np.percentile(nullmax, 95))

    # Q3 sensitivity: leak fraction needed to clear the family null p95
    p95 = np.percentile(nullmax, 95)
    sens = {}
    for frac in (0.05, 0.10, 0.20, 0.35, 0.50, 0.75):
        r2 = np.random.default_rng(RNG + 7)
        keep = r2.random(n_g) < frac
        gp = gy[r2.permutation(n_g)].copy()
        gp[keep] = gy[keep]
        yb = gp[inv]
        pos = yb == 1
        n1, n0 = int(pos.sum()), int((yb == 0).sum())
        d = max(abs(auc_from_ranks(stats[nm], pos, n1, n0) - 0.5)
                for nm in FEAT_NAMES)
        sens[f"leak_{int(frac*100)}pct"] = {"family_max_dev": float(d),
                                            "clears_null_p95": bool(d > p95)}
    out["Q3_sensitivity"] = sens
    out["Q3_detection_limit"] = next(
        (k for k, v in sens.items() if v["clears_null_p95"]), None)

    with open(os.path.join(RESULTS, f"s2_a3_null_{tag}.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: v for k, v in out.items()
                      if k != "null_per_statistic"}, indent=1))


if __name__ == "__main__":
    main()
