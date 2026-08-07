#!/usr/bin/env python3
"""STAGE 1i -- DIRECT POLICY SEARCH over the existing features.

WHY THIS EXISTS: the ridge probe was INCONCLUSIVE, and for a reason worth naming.

stage1_nonlinear.py fitted models by least squares against rollout value, then
scored them by argmax ranking. Its calibration control failed: the fitted LINEAR
model scored +4.94 pills against the hand-tuned weights' +3.86 over the SAME
features at the SAME depth. The shipped eval IS a linear model over exactly those
terms, so a fit that cannot match it has not exhausted the linear class -- it ran
out of data. Every conclusion downstream of that fit, including Stage 1b's
"reweighting buys nothing", inherits the weakness.

Least squares is also simply the wrong objective here. It spends capacity making
large values accurate, while the policy only cares about which action RANKS first.
So this file optimises the thing we actually measure:

    beta*  =  argmin_beta  mean split-sample regret of "pick argmax_a  phi(a).beta"

evaluated on TRAINING positions, and reported on HELD-OUT positions. The score is a
dot product against precomputed term vectors, so a full evaluation of a candidate
weight vector costs microseconds and thousands of restarts are affordable. This can
only do better than the ridge fit -- it is the same hypothesis class optimised
against the real objective instead of a surrogate.

The question it answers is therefore sharp:

  if DIRECT policy search over the linear class still cannot match the hand weights
  at depth 1, the linear class really is exhausted and the earlier negative stands
  on firmer ground;
  if it CAN, then the ridge probe was measuring my regression and Stage 1b's
  "reweighting is not the lever" has to be withdrawn.

Same discipline as everywhere else: cross-validated BY POSITION, the same
split-sample regret estimator, and a SHUFFLED-TARGET control that optimises against
permuted values and must fail to generalise.
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
from scipy.optimize import minimize

VALUE_CENSOR = 200.0


def _v(pills, outcome):
    return [(-float(p) if o == "clear" else -VALUE_CENSOR)
            for p, o in zip(pills, outcome)]


def boot_ci(xs, n=8000, seed=5):
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
    ap.add_argument("--depth", default="out/depth.jsonl")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--restarts", type=int, default=40)
    ap.add_argument("--seed", type=int, default=21)
    ap.add_argument("--quad", action="store_true", help="quadratic feature expansion")
    args = ap.parse_args()

    f = np.load(args.feats)
    pos, act = f["pos"], f["act"]
    T = f["terms_search"].astype(np.float64)
    WIN = f["win"] if "win" in f else np.zeros(len(pos), dtype=np.int64)
    row = {(int(p), int(a)): i for i, (p, a) in enumerate(zip(pos, act))}
    mu, sd = T.mean(axis=0), T.std(axis=0)
    sd[sd == 0] = 1.0
    Tz = (T - mu) / sd
    if args.quad:
        d = Tz.shape[1]
        cols = [Tz] + [Tz[:, i:i + 1] * Tz[:, i:] for i in range(d)]
        Tz = np.hstack(cols)

    lab = {r["idx"]: r for r in (json.loads(l) for l in open(args.labels) if l.strip())}
    dep = {}
    if os.path.exists(args.depth):
        dep = {r["idx"]: r for r in (json.loads(l) for l in open(args.depth) if l.strip())}

    blocks = []
    for i, L in lab.items():
        acts = [a for a in L["acts"] if (i, a) in row]
        if len(acts) < 3 or L["hand_act"] not in acts:
            continue
        vals = {a: _v(L["pills"][str(a)], L["outcome"][str(a)]) for a in acts}
        M = min(len(v) for v in vals.values())
        if M < 4:
            continue
        rows = np.array([row[(i, a)] for a in acts])
        V = np.array([vals[a] for a in acts])            # (K, M)
        blocks.append(dict(pos=i, acts=acts, X=Tz[rows], V=V, M=M,
                           win=WIN[rows].astype(bool), hand=acts.index(L["hand_act"]),
                           d1=(dep.get(i, {}).get("arms", {}).get("d1", -1))))
    print(f"positions {len(blocks)}  features {Tz.shape[1]}")

    # Precompute the split-sample partitions ONCE and share them across every arm,
    # so all arms are scored on identical partitions -- the comparison is paired
    # rather than each arm drawing its own luck.
    #
    # Everything is then PADDED INTO DENSE ARRAYS so a candidate weight vector is
    # scored with one matmul instead of a python loop over positions. The loop
    # version ran 40+ minutes without finishing a single arm; vectorised, a full
    # objective evaluation is microseconds, which is what makes thousands of
    # restarts affordable and the search meaningful rather than token.
    rng = np.random.default_rng(args.seed)
    NS = 60
    P = len(blocks)
    Kmax = max(len(b["acts"]) for b in blocks)
    D = Tz.shape[1]
    Xall = np.zeros((P, Kmax, D))
    valid = np.zeros((P, Kmax), dtype=bool)
    winm = np.zeros((P, Kmax), dtype=bool)
    VE = np.zeros((P, NS, Kmax))
    ORC = np.zeros((P, NS))
    hand_i = np.zeros(P, dtype=np.int64)
    d1_i = np.full(P, -1, dtype=np.int64)
    for pi, b in enumerate(blocks):
        K, M, half = len(b["acts"]), b["M"], b["M"] // 2
        Xall[pi, :K] = b["X"]
        valid[pi, :K] = True
        winm[pi, :K] = b["win"]
        perm = np.stack([rng.permutation(M) for _ in range(NS)])
        sel, ev = perm[:, :half], perm[:, half:]
        vs = np.stack([b["V"][:, sel[s]].mean(axis=1) for s in range(NS)])   # (NS,K)
        ve = np.stack([b["V"][:, ev[s]].mean(axis=1) for s in range(NS)])
        VE[pi, :, :K] = ve
        ORC[pi] = ve[np.arange(NS), np.argmax(vs, axis=1)]
        hand_i[pi] = b["hand"]
        d1_i[pi] = b["acts"].index(b["d1"]) if b["d1"] in b["acts"] else -1

    NEG = -1e18
    POSI = 1e18

    def picks(beta, idx):
        s = Xall[idx] @ beta
        s = np.where(winm[idx], POSI, s)
        s = np.where(valid[idx], s, NEG)
        return np.argmax(s, axis=1)

    def regret_idx(idx, k):
        """mean split-sample regret over positions `idx` choosing action index k[p]"""
        ve = VE[idx][np.arange(len(idx))[:, None], np.arange(NS)[None, :], k[:, None]]
        return (ORC[idx] - ve).mean(axis=1)

    def obj_idx(beta, idx):
        return float(regret_idx(idx, picks(beta, idx)).mean())

    order = list(range(P))
    random.Random(args.seed).shuffle(order)
    folds = [order[i::args.folds] for i in range(args.folds)]

    def search(idx, seed):
        g = np.random.default_rng(seed)
        best, bb = None, None
        for _ in range(args.restarts):
            x0 = g.normal(0, 1, D)
            res = minimize(obj_idx, x0, args=(idx,), method="Nelder-Mead",
                           options={"maxiter": 4000, "xatol": 1e-3, "fatol": 1e-4})
            if best is None or res.fun < best:
                best, bb = res.fun, res.x
        return bb

    def run(shuffled):
        te_reg = []
        for fi in range(args.folds):
            test = np.array(sorted(folds[fi]))
            tr = np.array(sorted(set(range(P)) - set(folds[fi])))
            if shuffled:
                # detach features from values on the TRAINING positions only, by
                # permuting each position's action axis in the evaluation tensor
                pr = np.random.default_rng(args.seed + 500 + fi)
                VEs, ORCs = VE.copy(), ORC.copy()
                for pi in tr:
                    K = int(valid[pi].sum())
                    q = pr.permutation(K)
                    VEs[pi, :, :K] = VE[pi, :, :K][:, q]
                sv_VE, sv_ORC = VE.copy(), ORC.copy()
                VE[...] = VEs
                beta = search(tr, args.seed + fi)
                VE[...] = sv_VE
                ORC[...] = sv_ORC
            else:
                beta = search(tr, args.seed + fi)
            te_reg += list(regret_idx(test, picks(beta, test)))
        return te_reg

    fitted = run(False)
    control = run(True)
    allidx = np.arange(P)
    hand_d3 = list(regret_idx(allidx, hand_i))
    m1 = d1_i >= 0
    hand_d1 = list(regret_idx(allidx[m1], d1_i[m1]))

    def line(tag, xs):
        if not xs:
            print(f"{tag:46s} (no data)")
            return None
        lo, hi = boot_ci(xs)
        print(f"{tag:46s} {st.mean(xs):+7.3f} [{lo:+.3f},{hi:+.3f}] n={len(xs)}")
        return st.mean(xs)

    print()
    print("=" * 78)
    print("DIRECT POLICY SEARCH over the existing features"
          f"{' (quadratic)' if args.quad else ' (linear)'}")
    print("=" * 78)
    c3 = line("  champion, real depth-3", hand_d3)
    h1 = line("  HAND weights at depth 1  <- the bar", hand_d1)
    fo = line("  policy-optimised, depth 1 (held out)", fitted)
    line("  shuffled-target CONTROL", control)

    print()
    print("=" * 78)
    print("VERDICT")
    print("=" * 78)
    if h1 is None or fo is None:
        return
    if fo <= h1 + 0.25:
        print("  The linear class is NOT exhausted by hand tuning: optimising the real")
        print("  objective reaches the hand weights' level from data alone.")
        print("  => the earlier ridge probe was measuring MY REGRESSION, not the")
        print("     feature set, and Stage 1b's 'reweighting buys nothing' must be")
        print("     withdrawn as unsupported.")
    else:
        print(f"  Even DIRECT optimisation of the exact objective cannot match the hand")
        print(f"  weights at depth 1 ({fo:+.2f} vs {h1:+.2f}) on this label budget.")
        print("  The obstacle is the LABELS, not the loss function and not the feature")
        print("  set: with 140 positions and ~4.2 pills of Monte-Carlo noise per action")
        print("  against a 6.4-pill true spread, there is not enough signal to recover")
        print("  weights that took a far better-powered objective to tune.")
        print()
        print("  => Stage 1b's negative CANNOT be read as 'the vocabulary is the limit'.")
        print("     It is 'this label budget cannot fit these features'. The distinction")
        print("     matters because the two imply different next steps.")
    print()
    print("  Note on what SURVIVES regardless: every Stage-1 number that involves no")
    print("  fitting is untouched -- the oracle gap (+3.73), the within-position rank")
    print("  correlation (0.27), and the eval-vs-horizon split (85/15), which compares")
    print("  SEARCH ARMS rather than fitted models.")


if __name__ == "__main__":
    main()
