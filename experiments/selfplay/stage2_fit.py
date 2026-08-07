#!/usr/bin/env python3
"""STAGE 2 FIT -- learned evaluator vs hand-tuned coefficients, at matched depth.

THE CALIBRATION GATE IS STRUCTURAL, NOT REMEMBERED
--------------------------------------------------
Stage 1 produced a negative I had to retract, because the fitting procedure could
not reproduce a KNOWN-GOOD solution and I drew a conclusion from its failure to find
a better one. The rule that came out of it:

    If your fitting procedure cannot reproduce a known-good solution, you may draw
    no conclusion from its failure to find a better one.

Here that rule is enforced by control flow rather than by discipline. `main()` runs
the gate FIRST and RETURNS on failure, so the model comparisons are not merely
discouraged when the gate fails -- they are never computed and never printed. The
shipped eval is a linear model over eleven of these features, so a fitted linear
model must reach the hand weights at the SAME depth on HELD-OUT positions. Until it
does, nothing downstream is evidence about anything.

WHAT IS COMPARED, and why each arm exists
-----------------------------------------
Everything is a depth-1 ranking over the position's labelled actions, fitted and
scored identically, so the ONLY difference between arms is the hypothesis class:

  terms11   the shipped eval's own vocabulary          -- the calibration reference
  terms12   + virus count                              -- one feature the eval lacks
  handplus  + column heights, holes, colour/virus
            counts, height profile (~40 features)      -- hand features it never had
  board     128 cells x 7 one-hot planes (896 binary)  -- the NNUE-style arm, the
                                                          feature set with no hand
                                                          design in it at all

Classes: ridge (closed form, deterministic -- a negative from it cannot be blamed on
an optimiser) and a small MLP for the arms where nonlinearity is the question.

Deployment is NOT a constraint at this stage: no quantisation, no size limit, no
integer arithmetic. The question is what near-optimal play looks like; making it fit
on silicon is a later, separate problem.

TWO DIRECTIONAL CAVEATS, PRE-REGISTERED BEFORE ANY NUMBER EXISTS
----------------------------------------------------------------
They point OPPOSITE ways, and stating only one would bias the reading:

  1. On the GATE.  The hand weights were tuned for depth-3 play, so at depth 2 they
     are off-design and the calibration bar is LOWER than Stage 1's. Passing it here
     therefore proves less than passing it there would have. (This is why GATE B
     exists: it asks whether the fit has converged, which needs no reference at all.)

  2. On the HEADLINE, and it runs the other way.  At depth 2 there is less search to
     compensate for a bad leaf, so the leaf carries MORE of the decision than it does
     at depth 3. A better leaf should therefore help MORE here. Consequently:

         a POSITIVE result at depth 2 is an UPPER BOUND on the depth-3 benefit,
         not a prediction of it.

     The asymmetry does not weaken a NEGATIVE. If a learned leaf cannot beat hand
     tuning in the regime where the leaf matters MOST, it will not do so where the
     search compensates for it. So: negative here is strong and transfers; positive
     here is an upper bound and must be re-proven at depth 3 before it is claimed.

Every number uses the Stage-1 machinery unchanged: split-sample regret estimator,
cross-validation BY POSITION, within-position centring, permutation/shuffled-target
controls, and terminal wins excluded from fitting but scored +inf in the policy.
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

VALUE_CENSOR = 250.0
GATE_TOL = 0.25          # pills: how close a fitted linear must get to the hand weights


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


def build_features(col, vir):
    """Rich board features. col/vir are int8[128], row-major, row 0 = TOP."""
    c = col.reshape(16, 8)
    v = vir.reshape(16, 8)
    occ = (c != 0)
    heights = np.zeros(8)
    holes = np.zeros(8)
    for j in range(8):
        colj = occ[:, j]
        nz = np.nonzero(colj)[0]
        if len(nz):
            top = nz[0]
            heights[j] = 16 - top
            holes[j] = int((~colj[top:]).sum())
    colour_counts = np.array([(c == k).sum() for k in (1, 2, 3)], dtype=np.float64)
    virus_counts = np.array([((c == k) & (v != 0)).sum() for k in (1, 2, 3)],
                            dtype=np.float64)
    row_occ = occ.sum(axis=1).astype(np.float64)
    extra = np.array([heights.max(), heights.mean(), heights.std(),
                      np.abs(np.diff(heights)).sum(), occ.sum(), (v != 0).sum()])
    return np.concatenate([heights, holes, colour_counts, virus_counts, row_occ, extra])


def build_board_onehot(col, vir):
    """896 binary features: per cell, one-hot over {empty, pill c1..3, virus c1..3}."""
    out = np.zeros((128, 7), dtype=np.float64)
    for i in range(128):
        k = int(col[i])
        if k == 0:
            out[i, 0] = 1.0
        else:
            out[i, (k if vir[i] == 0 else 3 + k)] = 1.0
    return out.reshape(-1)


def fit_ridge(Phi, y, lam):
    A = Phi.T @ Phi + lam * np.eye(Phi.shape[1])
    return np.linalg.solve(A, Phi.T @ y)


def fit_mlp(X, y, hidden=64, epochs=600, lr=0.02, lam=1e-4, seed=0):
    rng = np.random.default_rng(seed)
    d = X.shape[1]
    W1 = rng.normal(0, 1.0 / math.sqrt(d), (d, hidden)); b1 = np.zeros(hidden)
    W2 = rng.normal(0, 1.0 / math.sqrt(hidden), (hidden, 1)); b2 = np.zeros(1)
    ps = [W1, b1, W2, b2]
    ms = [np.zeros_like(p) for p in ps]; vs = [np.zeros_like(p) for p in ps]
    yy = y.reshape(-1, 1); n = len(X)
    for t in range(1, epochs + 1):
        H = np.tanh(X @ W1 + b1); P = H @ W2 + b2; E = P - yy
        gW2 = H.T @ E / n + lam * W2; gb2 = E.mean(axis=0)
        dH = (E @ W2.T) * (1 - H ** 2)
        gW1 = X.T @ dH / n + lam * W1; gb1 = dH.mean(axis=0)
        for p, g, m, v in zip(ps, [gW1, gb1, gW2, gb2], ms, vs):
            m *= 0.9; m += 0.1 * g
            v *= 0.999; v += 0.001 * (g * g)
            p -= lr * (m / (1 - 0.9 ** t)) / (np.sqrt(v / (1 - 0.999 ** t)) + 1e-8)
    return lambda Z: (np.tanh(Z @ W1 + b1) @ W2 + b2).ravel()


def load(args):
    import sp_engine as E
    import fast_rtl_x as FX
    from fast_sim_x import NCELL, _expand_core

    d = np.load(args.corpus)
    C, V, P = d["col"], d["vir"], d["pills"]
    recs = [json.loads(l) for l in open(args.labels) if l.strip()]
    print(f"labelled positions: {len(recs)}")

    c1 = np.empty(NCELL, dtype=np.int8); v1 = np.empty(NCELL, dtype=np.int8)
    blocks = []
    for r in recs:
        i = r["idx"]
        acts = r["acts"]
        if len(acts) < 3 or r["hand_act"] not in acts:
            continue
        vals = {a: _v(r["pills"][str(a)], r["outcome"][str(a)]) for a in acts}
        M = min(len(x) for x in vals.values())
        if M < 4:
            continue
        col = C[i].astype(np.int8); vir = V[i].astype(np.int8)
        ca, cb = int(P[i][0]), int(P[i][1])
        F = {"terms11": [], "terms12": [], "handplus": [], "board": []}
        win = []
        for a in acts:
            var, cc = a // 8, a % 8
            _ok, _nv, _cl = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            t = np.array(r["terms"][str(a)], dtype=np.float64)
            F["terms11"].append(t[:11])
            F["terms12"].append(t)
            F["handplus"].append(np.concatenate([t, build_features(c1, v1)]))
            F["board"].append(build_board_onehot(c1, v1))
            win.append(r["win"][str(a)])
        blocks.append(dict(idx=i, acts=acts, vals=vals, M=M,
                           hand=acts.index(r["hand_act"]),
                           win=np.array(win, dtype=bool),
                           F={k: np.stack(x) for k, x in F.items()}))
    print(f"usable positions: {len(blocks)}")
    return blocks


def prep(blocks, args):
    """Dense padded tensors + shared split-sample partitions (Stage-1 estimator)."""
    rng = np.random.default_rng(args.seed)
    NS = args.nsplits
    P = len(blocks)
    Kmax = max(len(b["acts"]) for b in blocks)
    VE = np.zeros((P, NS, Kmax)); ORC = np.zeros((P, NS))
    valid = np.zeros((P, Kmax), dtype=bool); winm = np.zeros((P, Kmax), dtype=bool)
    hand_i = np.zeros(P, dtype=np.int64)
    for pi, b in enumerate(blocks):
        K, M, half = len(b["acts"]), b["M"], b["M"] // 2
        valid[pi, :K] = True; winm[pi, :K] = b["win"]
        Vm = np.array([b["vals"][a] for a in b["acts"]])
        perm = np.stack([rng.permutation(M) for _ in range(NS)])
        vs = np.stack([Vm[:, perm[s, :half]].mean(axis=1) for s in range(NS)])
        ve = np.stack([Vm[:, perm[s, half:]].mean(axis=1) for s in range(NS)])
        VE[pi, :, :K] = ve
        ORC[pi] = ve[np.arange(NS), np.argmax(vs, axis=1)]
        hand_i[pi] = b["hand"]
    return dict(VE=VE, ORC=ORC, valid=valid, winm=winm, hand=hand_i,
                P=P, Kmax=Kmax, NS=NS)


def regret(T, idx, k):
    ve = T["VE"][idx][np.arange(len(idx))[:, None], np.arange(T["NS"])[None, :],
                      k[:, None]]
    return (T["ORC"][idx] - ve).mean(axis=1)


def score_arm(blocks, T, key, model, folds, fi_test):
    """held-out regret of ranking by `model` on feature set `key`"""
    ks, idxs = [], []
    for j in fi_test:
        b = blocks[j]
        s = model(b["F"][key])
        s = np.where(b["win"], np.inf, s)
        ks.append(int(np.argmax(s)))
        idxs.append(j)
    return list(regret(T, np.array(idxs), np.array(ks)))


def design(blocks, key, js, winfilter=True):
    X, y = [], []
    for j in js:
        b = blocks[j]
        ft = b["F"][key]
        tv = np.array([st.mean(b["vals"][a]) for a in b["acts"]])
        keep = ~b["win"] if winfilter else np.ones(len(tv), bool)
        if keep.sum() < 3:
            continue
        ft = ft[keep]; tv = tv[keep]
        X.append(ft - ft.mean(axis=0))
        y.append(tv - tv.mean())
    return np.vstack(X), np.concatenate(y)


def run_arm(blocks, T, key, folds, kind, args, shuffled=False, frac=1.0):
    out = []
    for fi in range(args.folds):
        te = folds[fi]
        tr = [j for j in range(T["P"]) if j not in set(te)]
        if frac < 1.0:
            # subsample TRAINING positions only; the held-out fold is untouched so
            # every point on the curve is scored on exactly the same positions
            rr = random.Random(args.seed + 4000 + fi)
            tr = sorted(rr.sample(tr, max(10, int(frac * len(tr)))))
        if shuffled:
            pr = random.Random(args.seed + 900 + fi)
            saved = {}
            for j in tr:
                b = blocks[j]
                saved[j] = b["vals"]
                order = pr.sample(b["acts"], len(b["acts"]))
                b["vals"] = {a: saved[j][o] for a, o in zip(b["acts"], order)}
        X, y = design(blocks, key, tr)
        mu, sd = X.mean(axis=0), X.std(axis=0); sd[sd == 0] = 1.0
        Xs = X / sd
        if kind == "ridge":
            best, bl = None, args.lams[0]
            cut = max(1, int(0.8 * len(tr)))
            Xi, yi = design(blocks, key, tr[:cut]); Xv, yv = design(blocks, key, tr[cut:])
            Xi = Xi / sd; Xv = Xv / sd
            for lam in args.lams:
                bta = fit_ridge(Xi, yi, lam)
                e = float(((Xv @ bta - yv) ** 2).mean())
                if best is None or e < best:
                    best, bl = e, lam
            beta = fit_ridge(Xs, y, bl)
            gmean = np.vstack([blocks[j]["F"][key] for j in tr]).mean(axis=0)
            model = (lambda Z, b=beta, s=sd, m=gmean: ((Z - m) / s) @ b)
        else:
            pred = fit_mlp(Xs, y, hidden=args.hidden, epochs=args.epochs,
                           seed=args.seed + fi)
            gmean = np.vstack([blocks[j]["F"][key] for j in tr]).mean(axis=0)
            model = (lambda Z, p=pred, s=sd, m=gmean: p((Z - m) / s))
        out += score_arm(blocks, T, key, model, folds, te)
        if shuffled:
            for j in tr:
                blocks[j]["vals"] = saved[j]
    return out


def line(tag, xs, unit="pills"):
    if not xs:
        print(f"{tag:46s} (no data)")
        return None
    lo, hi = boot_ci(xs)
    print(f"{tag:46s} {st.mean(xs):+7.3f} [{lo:+.3f},{hi:+.3f}] n={len(xs)} {unit}")
    return st.mean(xs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="out/s2_labels.jsonl")
    ap.add_argument("--corpus", default="out/s2_corpus.npz")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--nsplits", type=int, default=40)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--epochs", type=int, default=600)
    ap.add_argument("--plateau-tol", type=float, default=0.15,
                    help="pills: max held-out gain over the last data doubling")
    ap.add_argument("--min-positions", type=int, default=200,
                    help="refuse to run below this; smoke tests only")
    args = ap.parse_args()
    args.lams = [0.1, 1.0, 10.0, 100.0, 1000.0, 1e4]

    blocks = load(args)
    if len(blocks) < args.min_positions:
        print("too few usable positions; aborting")
        return 1
    T = prep(blocks, args)
    order = list(range(T["P"]))
    random.Random(args.seed).shuffle(order)
    folds = [order[i::args.folds] for i in range(args.folds)]
    allidx = np.arange(T["P"])

    hand = list(regret(T, allidx, T["hand"]))

    print()
    print("=" * 78)
    print("CALIBRATION GATE -- runs FIRST, and nothing downstream is computed if it fails")
    print("=" * 78)
    h = line("  HAND weights, depth 2 (the bar)", hand)
    lin11 = run_arm(blocks, T, "terms11", folds, "ridge", args)
    f = line("  fitted LINEAR over the same 11 terms", lin11)
    ctl = run_arm(blocks, T, "terms11", folds, "ridge", args, shuffled=True)
    line("  shuffled-target control", ctl)

    # GATE B -- LABEL SUFFICIENCY, and it does not depend on the hand weights at all.
    # Gate A compares the fit to a known-good reference, but at depth 2 those hand
    # weights are OFF-DESIGN (they were tuned for depth 3), so the bar is lower here
    # than it was in Stage 1 and passing it proves correspondingly less. The
    # reference-free question is whether the fit has stopped improving with data: if
    # held-out regret is still falling at the full training set, the fit is still
    # label-limited and a negative from the richer arms would again be a statement
    # about my label budget rather than about hypothesis classes.
    print()
    print("=" * 78)
    print("GATE B -- has the fit CONVERGED, or is it still label-limited?")
    print("=" * 78)
    curve = []
    for frac in (0.25, 0.5, 0.75, 1.0):
        xs = run_arm(blocks, T, "terms11", folds, "ridge", args, frac=frac)
        m = line(f"  linear/terms11 on {frac:.0%} of training positions", xs)
        curve.append((frac, m))
    tail_gain = curve[-2][1] - curve[-1][1] if len(curve) >= 2 else float("nan")
    print(f"\n  improvement over the last doubling: {tail_gain:+.3f} pills")
    converged = abs(tail_gain) <= args.plateau_tol
    print(f"  {'CONVERGED' if converged else 'STILL LABEL-LIMITED'} "
          f"(plateau tolerance {args.plateau_tol})")

    print()
    if f is None or h is None or f > h + GATE_TOL:
        print("  *** GATE FAILED -- NO CONCLUSIONS DRAWN, NO MODELS SCORED. ***")
        print()
        print(f"  A fitted linear model over the eleven terms scores {f:+.3f} against the")
        print(f"  hand weights' {h:+.3f} at the same depth on held-out positions. The")
        print("  shipped eval IS a linear model over these features, so the fit has not")
        print("  exhausted the class -- it is still label-limited. Per the rule this")
        print("  harness enforces, a procedure that cannot reproduce a known-good")
        print("  solution licenses no conclusion from failing to find a better one.")
        print()
        print("  The richer arms are NOT run. Their numbers would be uninterpretable and")
        print("  reporting them would repeat the Stage-1 error exactly.")
        print(f"  Next lever: more labelled positions (currently {T['P']}).")
        return 2

    if not converged:
        print("  *** GATE B FAILED -- NO CONCLUSIONS DRAWN. ***")
        print()
        print(f"  Held-out regret is still improving by {tail_gain:+.3f} pills over the")
        print("  last doubling of training data, so the fit has NOT converged. A")
        print("  negative from the richer arms would again be a statement about the")
        print("  label budget, which is the Stage-1 error. Richer arms NOT run.")
        print(f"  Next lever: more labelled positions (currently {T['P']}).")
        return 3
    print(f"  GATES PASSED: fitted linear {f:+.3f} vs hand {h:+.3f} "
          f"(within {GATE_TOL}), and converged (last doubling {tail_gain:+.3f}).")
    print("  The fitting procedure can reproduce hand tuning from data alone, so")
    print("  differences between the arms below are attributable to the hypothesis")
    print("  class rather than to the fit running out of signal.")

    print()
    print("=" * 78)
    print("LEARNED EVALUATOR vs HAND WEIGHTS, matched depth (lower regret = better)")
    print("=" * 78)
    line("  HAND weights", hand)
    line("  linear / terms11", lin11)
    results = {"hand": h, "terms11": f}
    arm_spec = {"terms11": ("terms11", "ridge")}
    for key, kind, tag in (("terms12", "ridge", "linear / terms12 (+virus count)"),
                           ("handplus", "ridge", "linear / hand+ (~40 features)"),
                           ("handplus", "mlp", "MLP    / hand+"),
                           ("board", "ridge", "linear / board one-hot (896)"),
                           ("board", "mlp", "MLP    / board one-hot (NNUE-shaped)")):
        xs = run_arm(blocks, T, key, folds, kind, args)
        m = line(f"  {tag}", xs)
        results[f"{kind}:{key}"] = m
        arm_spec[f"{kind}:{key}"] = (key, kind)

    best_v, best_name = min((v, k) for k, v in results.items()
                            if k != "hand" and v is not None)
    best_key, best_kind = arm_spec[best_name]
    nfeat = blocks[0]["F"][best_key].shape[1]
    print()
    print("=" * 78)
    print("VERDICT")
    print("=" * 78)
    print(f"  best learned arm: {best_name} ({nfeat} features) at {best_v:+.3f} "
          f"vs hand {h:+.3f}")
    print(f"  gain over hand-tuned coefficients: {h - best_v:+.3f} pills")
    print()

    if h - best_v > 0.25:
        print("  => supervised learning on rollout labels BEATS hand tuning at matched")
        print("     depth. Stage 3 is licensed, but the SIZE of this gain is an UPPER")
        print("     BOUND on the depth-3 benefit and must NOT be quoted as a prediction")
        print("     of it -- see caveat 2 below. Re-prove at depth 3 before claiming it.")
        print()
        print("  (No convergence gate is applied to a POSITIVE: a fit that beats hand")
        print("   tuning while still label-starved is a STRONGER result, not a weaker")
        print("   one, so the check would only ever argue against its own conclusion.)")
    else:
        # GATE C -- convergence of the arm the VERDICT ACTUALLY RESTS ON.
        # Gate B certified terms11 (11 features, ~273 positions per feature). The
        # winning arm can be board one-hot at 896 features -- roughly 3 positions per
        # feature, 82x thinner. terms11 having plateaued says nothing about whether
        # THAT arm has. Without this, the "negative transfers, do not start Stage 3"
        # branch could fire on a fit that simply ran out of labels, which is the
        # Stage-1 error displaced one arm to the left.
        print("=" * 78)
        print(f"  GATE C -- has the WINNING arm ({best_name}, {nfeat} features)")
        print(f"            converged? Gate B only certified terms11 (11 features).")
        print("=" * 78)
        c2 = []
        for frac in (0.25, 0.5, 0.75, 1.0):
            xs = run_arm(blocks, T, best_key, folds, best_kind, args, frac=frac)
            c2.append(line(f"    {best_name} on {frac:.0%} of training positions", xs))
        tail2 = c2[-2] - c2[-1] if len(c2) >= 2 and None not in c2[-2:] else float("nan")
        print(f"\n    improvement over the last doubling: {tail2:+.3f} pills")
        if not (abs(tail2) <= args.plateau_tol):
            print()
            print("  *** GATE C FAILED -- THE NEGATIVE IS NOT CLAIMED. ***")
            print()
            print(f"  The winning arm is still improving by {tail2:+.3f} pills per data")
            print(f"  doubling at {nfeat} features and {T['P']} positions "
                  f"(~{T['P']/nfeat:.1f} per feature).")
            print("  Its loss to hand tuning is therefore a statement about the LABEL")
            print("  BUDGET, not about hypothesis classes, and it does NOT transfer to")
            print("  depth 3. Stage 3 is neither licensed nor refused on this evidence.")
            print(f"  Next lever: more labelled positions (currently {T['P']}).")
            return 4
        print()
        print(f"  GATE C PASSED (last doubling {tail2:+.3f}).")
        print("  => supervised learning does NOT beat hand tuning at matched depth,")
        print("     with a fitting procedure that passed ALL THREE gates -- including")
        print("     convergence of the winning arm itself. That is a real negative, and")
        print("     by caveat 2 it TRANSFERS: the leaf has more leverage at depth 2 than")
        print("     at depth 3, so failing here implies failing there.")
        print("     Stage 3 should not be started on this.")
    print()
    print("  PRE-REGISTERED SCOPE (written before these numbers existed):")
    print("   1. Hand weights were tuned for depth 3, so they are off-design here and")
    print("      the calibration bar is LOWER than Stage 1's -- passing it proves less.")
    print("   2. At depth 2 there is less search to compensate for a bad leaf, so the")
    print("      leaf carries MORE of the decision. A POSITIVE is therefore an UPPER")
    print("      BOUND on the depth-3 benefit; a NEGATIVE is unaffected and transfers.")
    print("   These point in OPPOSITE directions and both are on the record.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
