#!/usr/bin/env python3
"""Paired analysis for the d3-vs-d4 re-test.

METRICS, and why each is the form it is:
  * PILLS-TO-CLEAR is only defined on games that cleared, so the honest paired form is
    the difference on seeds where BOTH arms cleared.  Reported with a seed-level
    bootstrap CI on the mean and median -- a bare mean would hide that the per-seed
    spread in this project is +-20 pills at n=10.
  * CLEAR RATE is reported as counts plus the DISCORDANT PAIRS (b = d3 cleared and d4
    did not, c = the reverse).  A paired comparison lives entirely in b and c; McNemar's
    exact binomial is the test.  The two bare percentages are printed for context only.
  * CENSORED PILLS charges every non-clearing game the max-pills budget, which makes a
    single number that cannot be gamed by clearing fewer, easier games faster.  This is
    the modern stand-in for the 07-12 memo's "expected pills incl. topout cost"; that
    memo's own 0.17*400 formula is reproduced too, so the verdicts are comparable.
  * PILLS-PER-VIRUS BY REGIME is computed PER SEED and then paired.  The pooled
    ratio-of-sums is printed separately and labelled, because it silently weights by
    game length.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    rows = defaultdict(dict)
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        rows[(r["stream"], r["depth"])][r["seed"]] = r
    return rows


def boot_ci(vals, stat=np.mean, n=20000, seed=12345, lo=2.5, hi=97.5):
    v = np.asarray(vals, dtype=np.float64)
    if v.size == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, v.size, size=(n, v.size))
    s = stat(v[idx], axis=1)
    return (float(np.percentile(s, lo)), float(np.percentile(s, hi)))


def mcnemar_exact(b, c):
    """Two-sided exact binomial p on the discordant pairs."""
    from math import comb
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2.0 ** n)
    return min(1.0, 2.0 * tail)


def ppv_seed(r, k):
    """Pills-per-virus in one regime for ONE seed, or None if that seed cleared no virus
    in that regime (undefined, not zero)."""
    p, v = r["seg"][k]
    return (p / v) if v else None


def report(A, B, label, nameA="d3", nameB="d4", maxp=300):
    seeds = sorted(set(A) & set(B))
    n = len(seeds)
    a = [A[s] for s in seeds]
    b = [B[s] for s in seeds]
    out = {"label": label, "n": n}
    print(f"\n{'='*78}\n{label}   n={n} paired seeds   ({nameA} vs {nameB})\n{'='*78}")

    # ---- clear rate: counts + discordant pairs -----------------------------------
    wa = sum(x["won"] for x in a)
    wb = sum(x["won"] for x in b)
    only_a = sum(1 for x, y in zip(a, b) if x["won"] and not y["won"])
    only_b = sum(1 for x, y in zip(a, b) if y["won"] and not x["won"])
    both = sum(1 for x, y in zip(a, b) if x["won"] and y["won"])
    p_mc = mcnemar_exact(only_a, only_b)
    print(f"  clear      {nameA} {wa}/{n}   {nameB} {wb}/{n}   (both {both})")
    print(f"  DISCORDANT {nameA}-only {only_a}   {nameB}-only {only_b}   "
          f"McNemar exact p={p_mc:.4f}")
    out.update(clear_a=wa, clear_b=wb, both=both, only_a=only_a, only_b=only_b,
               mcnemar_p=p_mc)

    # ---- outcome mix --------------------------------------------------------------
    for nm, rows in ((nameA, a), (nameB, b)):
        mix = defaultdict(int)
        for x in rows:
            mix[x["result"]] += 1
        print(f"  outcomes {nm:>3}: " + "  ".join(f"{k}={v}" for k, v in sorted(mix.items())))
        out[f"mix_{nm}"] = dict(mix)

    # ---- paired pills on BOTH-CLEARED games ---------------------------------------
    d = [y["pills"] - x["pills"] for x, y in zip(a, b) if x["won"] and y["won"]]
    if d:
        ci_m = boot_ci(d, np.mean)
        ci_med = boot_ci(d, np.median)
        better = sum(1 for v in d if v < 0)
        worse = sum(1 for v in d if v > 0)
        print(f"  PAIRED PILLS (both cleared, n={len(d)}):  "
              f"mean {st.mean(d):+.2f} CI95 [{ci_m[0]:+.2f},{ci_m[1]:+.2f}]   "
              f"median {st.median(d):+.1f} CI95 [{ci_med[0]:+.1f},{ci_med[1]:+.1f}]")
        print(f"      ({nameB} better/worse/tie: {better}/{worse}/{len(d)-better-worse};"
              f"  negative = {nameB} clears in FEWER pills)")
        out.update(paired_n=len(d), paired_mean=st.mean(d), paired_mean_ci=ci_m,
                   paired_median=st.median(d), paired_median_ci=ci_med,
                   better=better, worse=worse)
    else:
        print("  PAIRED PILLS: no seed cleared under both arms")
        out["paired_n"] = 0

    # ---- censored pills (non-clear charged the full budget) ------------------------
    ca = [x["pills"] if x["won"] else maxp for x in a]
    cb = [y["pills"] if y["won"] else maxp for y in b]
    dc = [y - x for x, y in zip(ca, cb)]
    ci_c = boot_ci(dc, np.mean)
    print(f"  CENSORED PILLS (non-clear = {maxp}):  {nameA} {st.mean(ca):.1f}   "
          f"{nameB} {st.mean(cb):.1f}   paired delta {st.mean(dc):+.2f} "
          f"CI95 [{ci_c[0]:+.2f},{ci_c[1]:+.2f}]")
    out.update(cens_a=st.mean(ca), cens_b=st.mean(cb), cens_delta=st.mean(dc),
               cens_ci=ci_c)

    # ---- the 07-12 memo's own summary statistic, for comparability -----------------
    # TWO conventions, because they differ and the difference is not cosmetic.  The memo
    # ran max_pills=400 and its non-clears were TOPOUTS, so `topout-only` is the true
    # like-for-like reconstruction of its number.  `all non-clears` additionally charges
    # STALLS (a game that exhausted the pill budget without ever topping out) -- an
    # outcome this harness distinguishes and the memo's did not.  Printing only one of
    # them would be a quiet apples-to-oranges against the verdict being re-tested.
    def memo_exp(rows, topout_only):
        cl = [x["pills"] for x in rows if x["won"]]
        if topout_only:
            bad = sum(1 for x in rows if x["result"] == "topout") / len(rows)
        else:
            bad = 1.0 - len(cl) / len(rows)
        return (st.mean(cl) if cl else float("nan")) + bad * 400.0
    mca = st.mean([x["pills"] for x in a if x["won"]]) if any(x["won"] for x in a) else float("nan")
    mcb = st.mean([y["pills"] for y in b if y["won"]]) if any(y["won"] for y in b) else float("nan")
    print("  memo-form expected pills (mean-on-clear + rate*400):")
    print(f"      topout-only (the memo's own convention): {nameA} {memo_exp(a,1):.0f}"
          f"   {nameB} {memo_exp(b,1):.0f}     [07-12 verdict was d3=121 vs d4=160]")
    print(f"      all non-clears charged                 : {nameA} {memo_exp(a,0):.0f}"
          f"   {nameB} {memo_exp(b,0):.0f}")
    print(f"      mean pills on clear                    : {nameA} {mca:.1f}"
          f"   {nameB} {mcb:.1f}")
    out.update(memo_a=memo_exp(a, 1), memo_b=memo_exp(b, 1),
               memo_a_all=memo_exp(a, 0), memo_b_all=memo_exp(b, 0),
               mean_on_clear_a=mca, mean_on_clear_b=mcb)

    # ---- pills per virus by regime, PER SEED then paired ---------------------------
    for k in ("open", "mid", "end"):
        pairs = [(ppv_seed(x, k), ppv_seed(y, k)) for x, y in zip(a, b)]
        pairs = [(u, v) for u, v in pairs if u is not None and v is not None]
        if not pairs:
            continue
        dd = [v - u for u, v in pairs]
        ci = boot_ci(dd, np.mean)
        pa = sum(x["seg"][k][0] for x in a); va = sum(x["seg"][k][1] for x in a)
        pb = sum(y["seg"][k][0] for y in b); vb = sum(y["seg"][k][1] for y in b)
        print(f"  ppv[{k:>4}] per-seed paired delta {st.mean(dd):+.3f} "
              f"CI95 [{ci[0]:+.3f},{ci[1]:+.3f}] (n={len(dd)})   "
              f"| pooled ratio-of-sums {pa/va if va else float('nan'):.2f} -> "
              f"{pb/vb if vb else float('nan'):.2f}")
        out[f"ppv_{k}"] = {"delta": st.mean(dd), "ci": ci, "n": len(dd)}

    # ---- latency -------------------------------------------------------------------
    la = [x["cpu_ms_per_dec"] for x in a]
    lb = [y["cpu_ms_per_dec"] for y in b]
    print(f"  LATENCY cpu ms/decision:  {nameA} median {st.median(la):.1f} "
          f"(mean {st.mean(la):.1f})   {nameB} median {st.median(lb):.1f} "
          f"(mean {st.mean(lb):.1f})   ratio {st.median(lb)/st.median(la):.1f}x")
    out.update(lat_a=st.median(la), lat_b=st.median(lb),
               lat_ratio=st.median(lb) / st.median(la))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", nargs="+")
    ap.add_argument("--maxp", type=int, default=300)
    ap.add_argument("--nameB", default="d4")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows = defaultdict(dict)
    for p in a.jsonl:
        for k, v in load(p).items():
            rows[k].update(v)
    streams = sorted({k[0] for k in rows})
    summary = []
    for stream in streams:
        A = rows.get((stream, "d3"))
        B = rows.get((stream, "d4"))
        if not A or not B:
            print(f"[skip {stream}: missing arm]")
            continue
        summary.append(report(A, B, f"STREAM = {stream.upper()}", "d3", a.nameB,
                              maxp=a.maxp))
    if a.out:
        json.dump(summary, open(os.path.join(HERE, a.out), "w"), indent=2, default=float)
        print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
