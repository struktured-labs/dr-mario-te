#!/usr/bin/env python3
"""STAGE 1h -- IS THE HEADROOM REACHABLE BY A NONLINEAR FUNCTION OF THE SAME FEATURES?

THE GAP THIS CLOSES
-------------------
Stage 1b refuted LINEAR-in-existing-features: the best linear refit of the shipped
eval's eleven terms, cross-validated by position and placed back inside the same
depth-3 search, gained -0.57 pills [-2.40,+1.37] against an oracle worth +3.74.
It did NOT test NONLINEAR-in-existing-features, and those are different claims. The
shipped eval is a linear model over hand features; a hidden layer over the SAME
features is a strictly richer class and a far smaller, far more deployable answer
than new sparse board features would be. Worth an hour before committing to Stage 2.

Two outcomes, both useful:
  * a rich function over the 11 terms captures a good share of +3.74  => the
    vocabulary is fine, the FUNCTIONAL FORM was the limit, and the eventual eval is
    small.
  * it captures nothing => two function classes now agree the features themselves
    cannot express the distinction, which is a well-powered argument for Stage 2 as
    written rather than an assumption.

ISOLATING FUNCTION CLASS, AND ONLY FUNCTION CLASS
-------------------------------------------------
Stage 1b scored its linear refit INSIDE the depth-3 search. A neural leaf cannot be
put inside the njit search, so scoring an MLP at depth 1 against that number would
confound function class with depth -- the exact error this program has been careful
to avoid. So EVERY model here, linear included, is scored the same way: as a
DEPTH-1 policy that ranks the position's labelled actions by its own score. The
linear arm is therefore the controlled baseline, and (nonlinear - linear) isolates
the function class with depth, features, labels, fitting protocol and ruler all
held fixed. The champion's real depth-3 choice is carried alongside purely as a
reference point, never as the thing the delta is taken against.

FUNCTION CLASSES (all closed-form ridge -- deterministic, no optimiser to tune or
blame for a negative):
  linear    -- the shipped eval's own class
  quad      -- all squares and pairwise products: every interaction between terms
  rbf       -- random Fourier features, a universal approximator at this size
  mlp       -- a small tanh network, included because "small MLP" is the thing
               people picture; it is NOT the load-bearing arm, the closed-form
               ones are, because a negative from an optimiser invites "you trained
               it wrong" and a negative from a ridge solution does not.

HONEST PROTOCOL
  * cross-validated BY POSITION, never by row (rows of one position share a board,
    a pill and a rollout stream)
  * targets centred WITHIN position -- ranking successors is the job; a model fitted
    on raw values would predict "how many viruses are left" and score well doing
    nothing useful
  * ridge strength chosen by an INNER split over training positions only
  * scored with the same split-sample estimator as every other Stage-1 number
  * a SHUFFLED-TARGET control fits each class on within-position permuted targets;
    it must come out at ~0 or the pipeline is fitting noise and no arm means anything
  * terminal wins are excluded from FITTING (their leaf is a sentinel, not a score)
    but a winning move still scores +inf in the POLICY, exactly as the real search's
    win bonus makes it -- virus_count==0 is observable, so this is not clairvoyance
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


def _v(pills, outcome):
    return [(-float(p) if o == "clear" else -VALUE_CENSOR)
            for p, o in zip(pills, outcome)]


def boot_ci(xs, n=10000, seed=5):
    if len(xs) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(st.mean([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def _spearman(x, y):
    n = len(x)
    if n < 3:
        return float("nan")

    def rank(v):
        o = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[o[j + 1]] == v[o[i]]:
                j += 1
            a = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[o[k]] = a
            i = j + 1
        return r
    rx, ry = rank(x), rank(y)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (dx * dy) if dx > 0 and dy > 0 else float("nan")


def split_regret(vals, acts, a_ref, rng, nsplits, M):
    half = M // 2
    tot = 0.0
    for _ in range(nsplits):
        idx = list(range(M))
        rng.shuffle(idx)
        sel, ev = idx[:half], idx[half:]
        vs = {a: st.mean(vals[a][i] for i in sel) for a in acts}
        ve = {a: st.mean(vals[a][i] for i in ev) for a in acts}
        tot += ve[max(acts, key=lambda a: vs[a])] - ve[a_ref]
    return tot / nsplits


# ----------------------------------------------------------------- featurisers
def f_linear(X):
    return X


def f_quad(X):
    n, d = X.shape
    cols = [X]
    for i in range(d):
        cols.append(X[:, i:i + 1] * X[:, i:])
    return np.hstack(cols)


def make_rbf(d, D=300, gamma=0.5, seed=0):
    rng = np.random.default_rng(seed)
    W = rng.normal(0.0, math.sqrt(2 * gamma), size=(d, D))
    b = rng.uniform(0, 2 * math.pi, size=D)

    def f(X):
        return np.sqrt(2.0 / D) * np.cos(X @ W + b)
    return f


def fit_ridge(Phi, y, lam):
    d = Phi.shape[1]
    A = Phi.T @ Phi + lam * np.eye(d)
    return np.linalg.solve(A, Phi.T @ y)


def fit_mlp(X, y, hidden=32, epochs=400, lr=0.02, lam=1e-3, seed=0):
    """Small tanh MLP, plain numpy + Adam. Deterministic given `seed`."""
    rng = np.random.default_rng(seed)
    d = X.shape[1]
    W1 = rng.normal(0, 1.0 / math.sqrt(d), (d, hidden))
    b1 = np.zeros(hidden)
    W2 = rng.normal(0, 1.0 / math.sqrt(hidden), (hidden, 1))
    b2 = np.zeros(1)
    ps = [W1, b1, W2, b2]
    ms = [np.zeros_like(p) for p in ps]
    vs = [np.zeros_like(p) for p in ps]
    yy = y.reshape(-1, 1)
    n = len(X)
    for t in range(1, epochs + 1):
        H = np.tanh(X @ W1 + b1)
        P = H @ W2 + b2
        E = P - yy
        gW2 = H.T @ E / n + lam * W2
        gb2 = E.mean(axis=0)
        dH = (E @ W2.T) * (1 - H ** 2)
        gW1 = X.T @ dH / n + lam * W1
        gb1 = dH.mean(axis=0)
        for p, g, m, v in zip(ps, [gW1, gb1, gW2, gb2], ms, vs):
            m *= 0.9
            m += 0.1 * g
            v *= 0.999
            v += 0.001 * (g * g)
            p -= lr * (m / (1 - 0.9 ** t)) / (np.sqrt(v / (1 - 0.999 ** t)) + 1e-8)
    return lambda Z: (np.tanh(Z @ W1 + b1) @ W2 + b2).ravel()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="out/labels_main.jsonl")
    ap.add_argument("--feats", default="out/feats.npz")
    ap.add_argument("--depth", default="out/depth.jsonl")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--splits", type=int, default=100)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--drop-nvir", action="store_true",
                    help="use only the 11 terms the shipped eval multiplies")
    args = ap.parse_args()

    f = np.load(args.feats)
    pos, act = f["pos"], f["act"]
    T = f["terms_search"].astype(np.float64)
    WIN = f["win"] if "win" in f else np.zeros(len(pos), dtype=np.int64)
    if args.drop_nvir:
        T = T[:, :11]
    row = {(int(p), int(a)): i for i, (p, a) in enumerate(zip(pos, act))}

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
        blocks.append(dict(pos=i, acts=acts, rows=rows, vals=vals, M=M,
                           hand=L["hand_act"], win=WIN[rows]))
    print(f"positions {len(blocks)}  features {T.shape[1]}"
          f"{' (nvir dropped)' if args.drop_nvir else ''}")

    # standardise globally once; centring is done per position inside the fit
    mu, sd = T.mean(axis=0), T.std(axis=0)
    sd[sd == 0] = 1.0
    Tz = (T - mu) / sd

    rng = random.Random(args.seed)
    order = list(range(len(blocks)))
    rng.shuffle(order)
    folds = [order[i::args.folds] for i in range(args.folds)]

    feats = {
        "linear": f_linear,
        "quad": f_quad,
        "rbf": make_rbf(Tz.shape[1], D=300, gamma=0.5, seed=1),
    }
    lams = [0.1, 1.0, 10.0, 100.0, 1000.0]

    def design(bs, featf):
        X, y = [], []
        for b in bs:
            keep = b["win"] == 0
            if keep.sum() < 3:
                continue
            ft = featf(Tz[b["rows"]][keep])
            tv = np.array([st.mean(b["vals"][a]) for a in b["acts"]])[keep]
            X.append(ft - ft.mean(axis=0))
            y.append(tv - tv.mean())
        return np.vstack(X), np.concatenate(y)

    def score_blocks(bs, predict, split_rng):
        reg, rho = [], []
        for b in bs:
            s = predict(Tz[b["rows"]])
            s = np.where(b["win"] == 1, np.inf, s)   # a winning move IS the best move
            k = int(np.argmax(s))
            a_model = b["acts"][k]
            reg.append(split_regret(b["vals"], b["acts"], a_model,
                                    split_rng, args.splits, b["M"]))
            finite = np.isfinite(s)
            if finite.sum() >= 3:
                rho.append(_spearman(list(s[finite]),
                                     [st.mean(b["vals"][a])
                                      for a, ok in zip(b["acts"], finite) if ok]))
        return reg, rho

    results = {}
    for name, featf in feats.items():
        for shuffled in (False, True):
            reg_all, rho_all = [], []
            srng = random.Random(args.seed + 1)
            for fi in range(args.folds):
                test = set(folds[fi])
                tr = [b for j, b in enumerate(blocks) if j not in test]
                te = [blocks[j] for j in folds[fi]]
                if shuffled:
                    # within-position permutation of the TARGET only
                    pr = random.Random(args.seed + 100 + fi)
                    tr = [dict(b, vals={a: b["vals"][a2] for a, a2 in
                                        zip(b["acts"], pr.sample(b["acts"], len(b["acts"])))})
                          for b in tr]
                X, y = design(tr, featf)
                # inner ridge selection on training positions only
                cut = max(1, int(0.8 * len(tr)))
                Xi, yi = design(tr[:cut], featf)
                Xv, yv = design(tr[cut:] or tr[:1], featf)
                best, bl = None, lams[0]
                for lam in lams:
                    beta = fit_ridge(Xi, yi, lam)
                    err = float(((Xv @ beta - yv) ** 2).mean())
                    if best is None or err < best:
                        best, bl = err, lam
                beta = fit_ridge(X, y, bl)
                mean_ft = featf(Tz).mean(axis=0)
                reg, rho = score_blocks(
                    te, lambda Z, b=beta, ff=featf, mf=mean_ft: (ff(Z) - mf) @ b, srng)
                reg_all += reg
                rho_all += [r for r in rho if r == r]
            results[(name, shuffled)] = (reg_all, rho_all)

    # MLP arm (real fit, not closed form) -- reported but not load-bearing
    reg_all, rho_all = [], []
    srng = random.Random(args.seed + 2)
    for fi in range(args.folds):
        test = set(folds[fi])
        tr = [b for j, b in enumerate(blocks) if j not in test]
        te = [blocks[j] for j in folds[fi]]
        X, y = design(tr, f_linear)
        pred = fit_mlp(X, y, hidden=32, epochs=400, seed=args.seed + fi)
        mf = Tz.mean(axis=0)
        reg, rho = score_blocks(te, lambda Z, p=pred, m=mf: p(Z - m), srng)
        reg_all += reg
        rho_all += [r for r in rho if r == r]
    results[("mlp", False)] = (reg_all, rho_all)

    # reference arms
    srng = random.Random(args.seed + 3)
    champ_reg, d4_reg, handd1_reg = [], [], []
    for b in blocks:
        champ_reg.append(split_regret(b["vals"], b["acts"], b["hand"],
                                      srng, args.splits, b["M"]))
        r = dep.get(b["pos"])
        if r and r["arms"].get("d4", -1) in b["acts"]:
            d4_reg.append(split_regret(b["vals"], b["acts"], r["arms"]["d4"],
                                       srng, args.splits, b["M"]))
        # THE CALIBRATION CONTROL. The shipped eval is itself a LINEAR model over
        # these same features, so a fitted linear must at least approach the hand
        # weights AT THE SAME DEPTH. If it cannot, the fitting procedure -- not the
        # function class and not the feature set -- is the binding constraint, and no
        # negative conclusion about features can be drawn from any arm below.
        if r and r["arms"].get("d1", -1) in b["acts"]:
            handd1_reg.append(split_regret(b["vals"], b["acts"], r["arms"]["d1"],
                                           srng, args.splits, b["M"]))

    def line(tag, xs, unit="pills"):
        if not xs:
            print(f"{tag:44s} (no data)")
            return None
        lo, hi = boot_ci(xs)
        print(f"{tag:44s} {st.mean(xs):+7.3f} [{lo:+.3f},{hi:+.3f}] n={len(xs)} {unit}")
        return st.mean(xs)

    print()
    print("=" * 78)
    print("REGRET vs the split-sample oracle  (lower = better play)")
    print("=" * 78)
    c = line("  champion (real depth-3)", champ_reg)
    if d4_reg:
        line("  depth-4, same hand eval", d4_reg)
    hd1 = line("  HAND eval at depth 1 (calibration ctrl)", handd1_reg)
    print()
    print("  models below are ALL depth-1 over the SAME features, so the only")
    print("  difference between them is FUNCTION CLASS:")
    base = None
    for name in ("linear", "quad", "rbf", "mlp"):
        k = (name, False)
        if k in results:
            m = line(f"    {name}", results[k][0])
            if name == "linear":
                base = m
    print()
    print("  shuffled-target CONTROL (must be ~ the champion's own regret: a model")
    print("  fitted on permuted targets carries no information and should rank no")
    print("  better than an arbitrary pick):")
    for name in ("linear", "quad", "rbf"):
        k = (name, True)
        if k in results:
            line(f"    {name} [shuffled]", results[k][0])

    print()
    print("=" * 78)
    print("WITHIN-POSITION rank correlation with true value")
    print("=" * 78)
    for name in ("linear", "quad", "rbf", "mlp"):
        k = (name, False)
        if k in results and results[k][1]:
            line(f"  {name}", results[k][1], "rho")

    print()
    print("=" * 78)
    print("VERDICT")
    print("=" * 78)
    if base is None or c is None:
        return
    best_nl = min((st.mean(results[(n, False)][0]), n)
                  for n in ("quad", "rbf", "mlp") if (n, False) in results)
    print(f"  champion, real depth-3            {c:+.2f} pills")
    if hd1 is not None:
        print(f"  HAND eval at depth 1              {hd1:+.2f} pills   <- the bar to clear")
    print(f"  best FITTED LINEAR, depth 1       {base:+.2f} pills")
    print(f"  best FITTED NONLINEAR ({best_nl[1]:<6s})    {best_nl[0]:+.2f} pills")
    print(f"  function-class delta (lin - nonlin) {base - best_nl[0]:+.2f} pills")
    print()
    if hd1 is not None and base > hd1 + 0.25:
        print("  *** INCONCLUSIVE -- THE CALIBRATION CONTROL FAILED. ***")
        print()
        print(f"  A fitted LINEAR model over these features scores {base:+.2f}, WORSE than the")
        print(f"  hand-tuned weights over the SAME features at the SAME depth ({hd1:+.2f}).")
        print("  The shipped eval IS a linear model over exactly these terms, so a fit that")
        print("  cannot match it has not exhausted the linear class -- it has run out of")
        print("  data. The binding constraint here is the FITTING (140 positions, ~4.2")
        print("  pills of MC noise per action against a 6.4-pill true spread), not the")
        print("  function class and not the feature set.")
        print()
        print("  Therefore the nonlinear arms CANNOT support 'the vocabulary is the")
        print("  limit'. The function-class delta is measured on a base that is itself")
        print("  below the bar, so it says nothing about what a well-fitted nonlinear")
        print("  model could do. Do NOT read this as a negative for nonlinear evals.")
        print()
        print("  What would make it conclusive: raise the label budget until a fitted")
        print("  linear MATCHES the hand weights at depth 1, then re-run. That is more")
        print("  positions and/or more rollouts per action -- the same cost wall as")
        print("  before (~8 s/rollout), so it is a real spend, not a tweak.")
    elif (base - best_nl[0]) < 0.5:
        print("  READ: with the fitted linear calibrated against the hand weights, a")
        print("  richer function of the SAME features buys essentially nothing. Two")
        print("  function classes agree the vocabulary is the limit -- the well-powered")
        print("  argument for new FEATURES, i.e. Stage 2 as written.")
    else:
        print("  READ: the functional form was a real limit. A small nonlinear eval over")
        print("  the EXISTING features captures a meaningful share of the gap -- a much")
        print("  smaller and more deployable answer than new features.")


if __name__ == "__main__":
    main()
