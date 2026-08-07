#!/usr/bin/env python3
"""STAGE 1d -- DE-NOISE THE ORACLE GAIN.

THE PROBLEM THIS SOLVES
-----------------------
Stage 1 brackets the oracle's advantage between two estimators:

  split-sample  -- unbiased for a NOISY oracle, so it UNDERSTATES a perfect one
  same-sample   -- winner's-curse inflated, so it OVERSTATES it

At M=8 rollouts the bracket came out roughly [+1.3, +5.9] pills, which is too wide
to decide anything. The reason is measurable: the Monte-Carlo standard error per
action (~4.4 pills) is nearly as large as the spread of value ACROSS actions (~6.6
pills). Selecting on M/2 = 4 rollouts is then barely better than picking at random,
so the "lower bound" is not really a bound on the oracle -- it is a statement about
how bad a 4-rollout oracle is. Reporting that as the headroom would understate the
program's case just as badly as reporting the winner's-curse number would overstate it.

TWO FIXES, NEITHER OF WHICH ASSUMES THE ANSWER
----------------------------------------------
1. VARIANCE DECOMPOSITION, correctly accounting for common random numbers.
   Rollout m uses the same pill stream for every action, so the per-action errors
   are CORRELATED and the naive standard error overstates the noise that actually
   matters for RANKING. Centring each rollout on its own stream's mean removes the
   shared component:

       d(a,m) = v(a,m) - mean_a' v(a',m)

   Then tau^2 = var_a( mean_m d(a,m) ) - mean_a( var_m d(a,m) ) / M is an estimate
   of the TRUE between-action value spread, and lambda = tau^2/(tau^2 + noise) is
   the reliability of a single position's estimates. tau is the quantity that says
   how much is actually at stake between the moves available at a position.

2. SELECTION-BUDGET EXTRAPOLATION. Split-sample regret is unbiased for an oracle
   that selects on m rollouts, for ANY m. Computing it at several m and
   extrapolating to 1/m -> 0 estimates the regret of an oracle with unlimited
   rollouts -- the perfect leaf -- without ever evaluating a selection on the data
   that chose it. Selection uses a random size-m subset, evaluation the disjoint
   remainder, averaged over many random splits. This is the honest way to reach the
   number the split-sample estimator is converging to, instead of quoting its M=8
   value as if that were the ceiling.

The extrapolation is a fit, not a measurement, and is labelled as such wherever it
is printed. It is reported next to the raw points it was fitted to so the shape can
be judged rather than trusted.
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

VALUE_CENSOR = 200.0


def values(rec, a):
    return [(-float(p) if o == "clear" else -VALUE_CENSOR)
            for p, o in zip(rec["pills"][str(a)], rec["outcome"][str(a)])]


def boot_ci(xs, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(st.mean([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="out/labels_main.jsonl")
    ap.add_argument("--splits", type=int, default=60,
                    help="random selection/evaluation splits per position per budget")
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    recs = []
    for line in open(args.labels):
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except Exception:
            pass
    print(f"positions: {len(recs)}")

    rng = random.Random(args.seed)
    taus, noises, lams, spreads = [], [], [], []
    budgets = [1, 2, 3, 4, 5, 6]
    reg = {m: [] for m in budgets}

    for r in recs:
        acts = r["acts"]
        if len(acts) < 3 or r["hand_act"] not in acts:
            continue
        V = {a: values(r, a) for a in acts}
        M = len(V[acts[0]])
        if M < 4:
            continue

        # ---- 1. CRN-aware variance decomposition ----------------------------
        # centre every rollout on its OWN stream's across-action mean, which
        # removes the component common random numbers already cancel
        d = {a: [] for a in acts}
        for m in range(M):
            mu = st.mean(V[a][m] for a in acts)
            for a in acts:
                d[a].append(V[a][m] - mu)
        dbar = {a: st.mean(d[a]) for a in acts}
        between = st.pvariance(list(dbar.values()))
        within = st.mean(st.variance(d[a]) for a in acts) if M > 1 else 0.0
        noise = within / M
        tau2 = max(0.0, between - noise)
        taus.append(math.sqrt(tau2))
        noises.append(math.sqrt(noise))
        lams.append(tau2 / (tau2 + noise) if (tau2 + noise) > 0 else 0.0)
        spreads.append(math.sqrt(between))

        # ---- 2. selection-budget curve --------------------------------------
        ih = r["hand_act"]
        for m in budgets:
            if m >= M:
                continue
            acc = []
            for _ in range(args.splits):
                idx = list(range(M))
                rng.shuffle(idx)
                sel, ev = idx[:m], idx[m:]
                vs = {a: st.mean(V[a][i] for i in sel) for a in acts}
                ve = {a: st.mean(V[a][i] for i in ev) for a in acts}
                astar = max(acts, key=lambda a: vs[a])
                acc.append(ve[astar] - ve[ih])
            reg[m].append(st.mean(acc))

    def line(tag, xs, unit="pills"):
        if not xs:
            print(f"{tag:38s} (no data)")
            return None
        lo, hi = boot_ci(xs)
        print(f"{tag:38s} {st.mean(xs):+8.3f}  [{lo:+.3f},{hi:+.3f}]  n={len(xs)} {unit}")
        return st.mean(xs)

    print()
    print("=" * 78)
    print("1. WHAT IS ACTUALLY AT STAKE BETWEEN THE MOVES AT A POSITION")
    print("=" * 78)
    line("  observed sd of V across actions", spreads)
    line("  MC noise sd (CRN-corrected)", noises)
    t = line("  TRUE action-value sd (tau)", taus)
    l = line("  reliability lambda of V-hat", lams, "")
    print("    ^ tau is the real spread once rollout noise is removed. lambda near 0")
    print("      means a single position's estimates are mostly noise, which is why")
    print("      the split-sample bound understates the oracle at M=8.")

    print()
    print("=" * 78)
    print("2. ORACLE GAIN vs SELECTION BUDGET (each point unbiased on its own)")
    print("=" * 78)
    pts = []
    for m in budgets:
        if reg[m]:
            v = line(f"  select on m={m} rollouts", reg[m])
            pts.append((m, v))
    out = {"tau": st.mean(taus) if taus else None,
           "noise": st.mean(noises) if noises else None,
           "lambda": st.mean(lams) if lams else None,
           "curve": {m: v for m, v in pts}}

    if len(pts) >= 3:
        # least squares of regret ~ R_inf - c*(1/m); the intercept at 1/m -> 0 is
        # the unlimited-rollout oracle
        xs = [1.0 / m for m, _ in pts]
        ys = [v for _, v in pts]
        mx, my = st.mean(xs), st.mean(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        slope = sxy / sxx if sxx else 0.0
        inter = my - slope * mx
        print()
        print(f"  EXTRAPOLATED to unlimited rollouts : {inter:+.3f} pills")
        print("    ^ a FIT to the points above (regret ~ R_inf - c/m), not a")
        print("      measurement. Judge it against the shape of the curve.")
        out["extrapolated"] = inter

    print()
    print("=" * 78)
    print("3. READING")
    print("=" * 78)
    if t is not None and out.get("extrapolated") is not None:
        print(f"  A perfect leaf is worth about {out['extrapolated']:+.1f} pills at a")
        print(f"  typical decision, against a true across-action spread of {t:.1f} pills")
        print(f"  and ~52 pills of game remaining from a sampled position.")
    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(out, fh, indent=2)
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
