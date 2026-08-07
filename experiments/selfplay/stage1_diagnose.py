#!/usr/bin/env python3
"""STAGE 1e -- WHERE does the eval lose value, and is the loss EXPRESSIBLE?

Stage 1 says how much a perfect leaf is worth. Stage 1b says how much of that a
reweighting of the existing features can recover. This file asks the follow-up that
decides what to actually build: when the oracle disagrees with the champion, WHAT
is different about the move it prefers?

Two readings, and they point at opposite programs:

  * If the oracle's preferred moves differ systematically along the existing terms
    (say, consistently lower `buried` or higher `vrdy`), the eval has the right
    vocabulary and the wrong prices -- a coefficient problem.
  * If the oracle's preference is NOT explained by any combination of the eleven
    terms, then the distinction it is making is one the feature set cannot say out
    loud. That is the case for new features, and it is the interesting one.

METHOD
------
Restrict to CONFIDENT disagreements: positions where the value gap between the
oracle's pick and the champion's exceeds a multiple of that position's own
Monte-Carlo standard error. Ranking on noisy estimates and then describing the
winner would otherwise just describe the noise -- the same winner's-curse trap
Stage 1 controls for, wearing different clothes.

For those positions, compute the term-vector difference (oracle pick minus hand
pick), standardised by each term's within-position spread so terms with different
natural scales are comparable, and bootstrap a CI per term. Then regress the
observed value gap on those term differences: the R^2 is how much of the oracle's
advantage the existing vocabulary can account for AT ALL.

A permutation control repeats the whole thing with the oracle's pick replaced by a
RANDOM non-hand action from the same position. Any term that looks "systematic"
there is an artefact of comparing a chosen move against an unchosen one, not of
comparing a good move against a worse one.
"""
from __future__ import annotations

import os
import sys
import json
import math
import random
import argparse
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np

VALUE_CENSOR = 200.0
TERM_NAMES = ["maxh", "holes", "toprisk", "spawn", "setup", "matched",
              "buried", "rdy", "vrdy", "cross", "poll", "nvir"]


def values(rec, a):
    return [(-float(p) if o == "clear" else -VALUE_CENSOR)
            for p, o in zip(rec["pills"][str(a)], rec["outcome"][str(a)])]


def boot_ci(xs, n=6000, seed=17):
    if len(xs) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(st.mean([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="out/labels_main.jsonl")
    ap.add_argument("--feats", default="out/feats.npz")
    ap.add_argument("--k", type=float, default=1.0,
                    help="value gap must exceed k * the position's own MC se")
    ap.add_argument("--seed", type=int, default=3)
    args = ap.parse_args()

    f = np.load(args.feats)
    T = f["terms_search"].astype(np.float64)
    WIN = f["win"] if "win" in f else np.zeros(len(f["pos"]), dtype=np.int64)
    row = {(int(p), int(a)): i for i, (p, a) in enumerate(zip(f["pos"], f["act"]))}

    recs = []
    for line in open(args.labels):
        line = line.strip()
        if line:
            try:
                recs.append(json.loads(line))
            except Exception:
                pass

    rng = random.Random(args.seed)
    diffs, diffs_ctl, gaps, gapfeat = [], [], [], []
    used = 0
    for r in recs:
        acts = [a for a in r["acts"] if (r["idx"], a) in row]
        ih = r["hand_act"]
        if len(acts) < 3 or ih not in acts:
            continue
        V = {a: values(r, a) for a in acts}
        M = len(V[acts[0]])
        vAll = {a: st.mean(V[a]) for a in acts}
        # position's own MC se, CRN-corrected (centre each stream on its own mean)
        d = {a: [] for a in acts}
        for m in range(M):
            mu = st.mean(V[a][m] for a in acts)
            for a in acts:
                d[a].append(V[a][m] - mu)
        se = math.sqrt(max(1e-9, st.mean(st.variance(d[a]) for a in acts) / M))

        best = max(acts, key=lambda a: vAll[a])
        gap = vAll[best] - vAll[ih]
        if best == ih or gap < args.k * se:
            continue
        # terminal wins are a different kind of move; the eval never scores them
        if WIN[row[(r["idx"], best)]] or WIN[row[(r["idx"], ih)]]:
            continue
        used += 1

        Tp = np.stack([T[row[(r["idx"], a)]] for a in acts])
        sd = Tp.std(axis=0)
        sd[sd == 0] = 1.0
        dv = (T[row[(r["idx"], best)]] - T[row[(r["idx"], ih)]]) / sd
        diffs.append(dv)
        gaps.append(gap)
        gapfeat.append(dv)

        alt = rng.choice([a for a in acts if a != ih])
        diffs_ctl.append((T[row[(r["idx"], alt)]] - T[row[(r["idx"], ih)]]) / sd)

    print(f"positions with a confident oracle disagreement: {used} "
          f"(of {len(recs)}, gap > {args.k} x se)")
    if used < 5:
        print("too few to say anything; rerun with more positions or lower --k")
        return

    D = np.stack(diffs)
    C = np.stack(diffs_ctl)
    print()
    print("=" * 78)
    print("WHAT DISTINGUISHES THE ORACLE'S MOVE FROM THE CHAMPION'S")
    print("=" * 78)
    print(f"{'term':10s} {'oracle-hand':>22s} {'random-hand (control)':>24s}")
    for i, nm in enumerate(TERM_NAMES):
        lo, hi = boot_ci(list(D[:, i]))
        clo, chi = boot_ci(list(C[:, i]))
        flag = "  <-- " if (lo > 0 and clo > 0) or (hi < 0 and chi < 0) else ""
        flag = "" if (lo <= 0 <= hi) else ("  SIGNIFICANT" if (clo <= 0 <= chi) else
                                          "  (also in control)")
        print(f"{nm:10s} {D[:,i].mean():+7.3f} [{lo:+.3f},{hi:+.3f}]"
              f" {C[:,i].mean():+7.3f} [{clo:+.3f},{chi:+.3f}]{flag}")
    print("    ^ standardised by each term's within-position spread. A row is only")
    print("      informative if it is significant for oracle-hand AND not for the")
    print("      random control -- otherwise it just reflects 'chosen vs unchosen'.")

    # how much of the oracle's advantage the existing vocabulary can explain at all
    X = np.stack(gapfeat)
    y = np.array(gaps)
    npar = X.shape[1] + 1
    print()
    print("=" * 78)
    print("IS THE ORACLE'S ADVANTAGE EXPRESSIBLE IN THE EXISTING VOCABULARY?")
    print("=" * 78)
    print(f"  points {len(y)}, free parameters {npar}")
    if len(y) < 3 * npar:
        # With 13 parameters and a handful of points the in-sample R^2 saturates at
        # 1.000 and means nothing. Refusing to print a verdict is the correct
        # behaviour here -- a saturated fit reads as "fully explained" and would
        # argue exactly backwards.
        print("  UNDERDETERMINED: too few confident disagreements to fit 13")
        print("  parameters. No verdict. (An in-sample R^2 here would saturate at")
        print("  1.000 and argue the opposite of the truth.)")
        return
    # cross-validated R^2 -- the only version that can support a claim
    idx = list(range(len(y)))
    random.Random(args.seed).shuffle(idx)
    folds = [idx[i::5] for i in range(5)]
    pred = np.zeros(len(y))
    for k in range(5):
        te = folds[k]
        tr = [i for i in idx if i not in set(te)]
        Xtr = np.hstack([X[tr], np.ones((len(tr), 1))])
        Xte = np.hstack([X[te], np.ones((len(te), 1))])
        beta, *_ = np.linalg.lstsq(Xtr, y[tr], rcond=None)
        pred[te] = Xte @ beta
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    print(f"  CROSS-VALIDATED R^2 of the value gap on term differences : {r2:.3f}")
    if r2 < 0.25:
        print("  READ: the existing features barely account for why the oracle's move")
        print("  is better. The distinction it makes is one this vocabulary cannot")
        print("  state -- which is the case FOR new features, not new coefficients.")
    else:
        print("  READ: a good part of the oracle's advantage IS visible in the")
        print("  existing terms, so reweighting/re-pricing them is the cheaper lever")
        print("  to exhaust before reaching for a learned eval.")


if __name__ == "__main__":
    main()
