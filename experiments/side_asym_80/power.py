#!/usr/bin/env python3
"""Sizing arithmetic for task #80. Kept as CODE, not prose, because a number that is
only ever printed is never checked (measurement-rules #25) -- the prereg cites this
module's OUTPUT, so the N in the prereg and the N the runner uses come from one place.

The claim under test: champion death rate 6.0% on one side vs 0.67% on the other.
"""
from __future__ import annotations

import math

CLAIM_HI = 0.060      # reported death rate, the "bad" side
CLAIM_LO = 0.0067     # reported death rate, the other side
CLAIM_DELTA = CLAIM_HI - CLAIM_LO

# Base death rate the null is centred on, taken from the ONLY prior measurement of
# this arm (adversary_t3 fourway: 5 champion deaths / 160 games). Used to size the
# discordant-pair yield, NOT as a threshold -- an instrument's calibration is not
# part of the instrument, so nothing downstream imports this value as a bar.
BASE_DEATH = 5.0 / 160.0


def discordant_rate(p0, p1):
    """Per-SEED probability that the champion dies on exactly one of its two seats."""
    return p0 * (1 - p1) + p1 * (1 - p0)


def mcnemar_power_table(ns=(80, 150, 500, 1000, 1500, 2000)):
    rows = []
    d_claim = discordant_rate(CLAIM_HI, CLAIM_LO)
    d_null = discordant_rate(BASE_DEATH, BASE_DEATH)
    for n in ns:
        # SE of Delta = (b - c)/N under the null split, b + c ~ Binom(N, d_null)
        se_null = math.sqrt(d_null / n)
        rows.append({
            "n_seeds": n,
            "exp_discordant_if_claim": round(n * d_claim, 1),
            "exp_discordant_if_null": round(n * d_null, 1),
            "se_delta_pp": round(100 * se_null, 3),
            # two-sided alpha=.05, 80% power
            "mde_delta_pp": round(100 * 2.80 * se_null, 3),
            "ci95_halfwidth_pp": round(100 * 1.96 * se_null, 3),
            # can a null result at this n EXCLUDE the claimed effect?
            "excludes_claim": (100 * 1.96 * se_null) < (100 * CLAIM_DELTA),
        })
    return rows


def mirror_power(n_seeds, half_target=0.05):
    """Mirror arm: pooled P(side 0 wins) over both board orientations.

    Worst-case variance is the PURE-SEAT world (every seed contributes 0 or 1), which
    is also the world we are trying to detect, so sizing on it is conservative. In the
    pure-BOARD world every seed contributes exactly 0.5 and the variance is zero.
    """
    se_worst = 0.5 / math.sqrt(n_seeds)
    return {"n_seeds": n_seeds,
            "ci95_halfwidth_worstcase": round(1.96 * se_worst, 4),
            "meets_bound": (1.96 * se_worst) < half_target}


if __name__ == "__main__":
    print(f"claim: {CLAIM_HI:.4%} vs {CLAIM_LO:.4%}  ->  Delta = {100*CLAIM_DELTA:.2f} pp")
    print(f"null base death rate used for sizing: {BASE_DEATH:.4%}\n")
    print(f"{'N seeds':>8} {'disc|claim':>11} {'disc|null':>10} {'SE(pp)':>8} "
          f"{'MDE(pp)':>8} {'CI95+-(pp)':>11} {'excl claim':>11}")
    for r in mcnemar_power_table():
        print(f"{r['n_seeds']:>8} {r['exp_discordant_if_claim']:>11} "
              f"{r['exp_discordant_if_null']:>10} {r['se_delta_pp']:>8} "
              f"{r['mde_delta_pp']:>8} {r['ci95_halfwidth_pp']:>11} "
              f"{str(r['excludes_claim']):>11}")
    print()
    for n in (500, 1000, 1500):
        print("mirror:", mirror_power(n))
