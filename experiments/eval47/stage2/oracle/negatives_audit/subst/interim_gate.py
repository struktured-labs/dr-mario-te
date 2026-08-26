#!/usr/bin/env python3
"""REAL interim gate — emits evidence and CAN STOP THE UNIT. Prereg §9 Amendment 4(c).

The first version of this check existed only in the prereg, not in the code: the runner printed
throughput and nothing else. A check that emits no artifact is indistinguishable from one that
never ran — which is exactly what happened. This one:
  * computes the seed-clustered SE on the CORRECTED tie-group population,
  * prints a greppable `INTERIM SE=<pp> implied_N=<n> verdict=<...>` line,
  * writes interim.json,
  * and calls `systemctl stop` on the unit if implied_N exceeds the registered N.

⚠ VARIANCE ONLY. It never prints or returns the effect estimate — re-sizing on a peeked effect
inflates the false-positive rate; re-sizing on variance alone does not.
"""
import argparse, glob, gzip, json, os, subprocess, sys
import numpy as np

_RNG = np.random.default_rng(20260826)

Z_A, Z_B = 1.959964, 1.2816          # two-sided 95%, 90% power
TRUE_T, BOUND = 0.30, 0.20


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="/root/drm/subst/out_flips")
    ap.add_argument("--min-seeds", type=int, default=200)
    ap.add_argument("--registered-n", type=int, default=1666)
    ap.add_argument("--unit", default="drm-subst")
    ap.add_argument("--stop-on-fail", action="store_true")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.dir, "*.jsonl.gz")))
    if len(files) < a.min_seeds:
        print(f"INTERIM not_ready seeds={len(files)} need={a.min_seeds}")
        return 0
    # per-seed spread of the NORMALISED tie-group statistic. Variance only.
    # ALSO: flips/seed against the 5.05 anchor from the old capture (team-lead condition 2).
    # A rework that silently drops records shows up here first, and if flips are materially
    # low the KEEPS are suspect too — so this stops the run, it does not merely warn.
    per = {}
    flips = {}
    n_tie = n_degen = 0
    for p in files:
        for l in gzip.open(p, "rt"):
            r = json.loads(l)
            if "game" in r:
                continue
            flips[r["seed"]] = flips.get(r["seed"], 0) + int(r.get("is_flip", 0))
            n_tie += 1
            prog = np.array([lab[1] for lab in r["labels"]], dtype=float)
            if prog.max() <= prog.mean():
                # DEGENERATE TIE: every candidate carries an identical label, so this ply
                # cannot discriminate ANY ranker — LUT, champion, H12, random and worst all
                # score identically. Including it would DILUTE the effect toward zero
                # (~0.64x at the measured 36% degenerate rate), which could push a true 30%
                # transfer below the pre-registered 27% floor and report NOT RESOLVED for a
                # substitution that actually worked. EXCLUDED, and counted separately.
                n_degen += 1
                continue
            # ⚠⚠ THE PREVIOUS STATISTIC HERE WAS DEGENERATE AND PRODUCED implied_N=1.
            # It was (median-mean)/(max-mean). For a tie of shape [a,a,b,b] — which is
            # 5,274 of 5,689 discriminating ties, because the top board usually occupies two
            # slots — the median EQUALS the mean, so it is EXACTLY ZERO. Measured: zero on
            # 89.8% of ties, per-seed sd 0.031, SE 0.19pp. Near-constant, so its variance was
            # tiny and had nothing to do with the transfer estimator's variance.
            #
            # CORRECT PROXY: the transfer statistic itself under a BLIND RANDOM pick. Same
            # normalisation and denominator as the primary, so it has the right variance
            # structure, and it uses no ranker — the LUT is never scored here, so the interim
            # stays blind to the effect. Measured: per-seed sd 0.294, SE 1.83pp (plain) /
            # 1.86pp (bootstrap) — two independent estimators agreeing.
            per.setdefault(r["seed"], []).append(
                float((prog[_RNG.integers(len(prog))] - prog.mean())
                      / (prog.max() - prog.mean())))
    seeds = sorted(per)
    for s_ in seeds:
        flips.setdefault(s_, 0)
    v = np.array([np.mean(per[s]) for s in seeds])
    fv = np.array([flips[s] for s in seeds], dtype=float)
    f_mean = float(fv.mean()); f_se = float(fv.std(ddof=1) / np.sqrt(len(fv)))
    ANCHOR = 5.05
    flips_ok = (f_mean + 1.96 * f_se) >= ANCHOR      # not SIGNIFICANTLY below the anchor
    rng = np.random.default_rng(11)
    bs = np.array([rng.choice(v, len(v), replace=True).mean() for _ in range(4000)])
    se = float(bs.std())
    se66 = se * np.sqrt(len(seeds) / 66.0)
    need = (TRUE_T - BOUND) / (Z_A + Z_B)
    implied = 66.0 * (se66 / need) ** 2
    # ⚠ TWO-SIDED. The first version stopped only when implied_N was too LARGE, so it was
    # structurally blind to an impossibly SMALL one — which is exactly the failure that
    # produced implied_N=1. An implied N below MIN_PLAUSIBLE means the variance is degenerate,
    # not that one game suffices.
    MIN_PLAUSIBLE = 20
    implausible = implied < MIN_PLAUSIBLE
    ok = (implied <= a.registered_n) and flips_ok and not implausible
    why = ("" if implied <= a.registered_n else " reason=implied_N_exceeds_registered") + \
          ("" if flips_ok else " reason=flips_below_anchor_RECORDS_MAY_BE_DROPPING") + \
          ("" if not implausible else
           f" reason=implied_N_below_{MIN_PLAUSIBLE}_VARIANCE_LOOKS_DEGENERATE")
    verdict = "CONTINUE" if ok else "STOP_AND_REPORT"
    print(f"INTERIM SE={se*100:.2f}pp seeds={len(seeds)} se66={se66*100:.2f}pp "
          f"ties={n_tie} discriminating={n_tie-n_degen} degenerate={n_degen} "
          f"({n_degen/max(n_tie,1)*100:.1f}%) "
          f"implied_N={implied:.0f} registered_N={a.registered_n} "
          f"flips_per_seed={f_mean:.2f}+-{f_se:.2f} anchor={ANCHOR} "
          f"flips_ok={flips_ok} verdict={verdict}{why}")
    json.dump(dict(seeds=len(seeds), se_pp=se * 100, se66_pp=se66 * 100,
                   implied_N=implied, registered_N=a.registered_n,
                   flips_per_seed=f_mean, flips_se=f_se, anchor=ANCHOR, flips_ok=bool(flips_ok),
                   ties=n_tie, discriminating=n_tie - n_degen, degenerate=n_degen,
                   verdict=verdict),
              open(os.path.join(a.dir, "..", "interim.json"), "w"), indent=1)
    if not ok and a.stop_on_fail:
        print(f"INTERIM stopping unit {a.unit} — implied_N exceeds registered_N", flush=True)
        subprocess.run(["systemctl", "stop", a.unit], check=False)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
