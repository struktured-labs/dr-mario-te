#!/usr/bin/env python3
"""Pre-registered analysis + verdict for task #80.

UNIT OF ANALYSIS = THE SEED, everywhere. The two games of a seed share a capsule
stream and (in the mirror arm) a board pair, so they are not independent; per-game
counting is how a four-seed effect once impersonated p=0.0002 in this project.

WHAT THIS DOES NOT COVER (stated next to the result, per measurement-rules #24):
  * the offline fast sim only. Nothing here is a silicon or RTL claim.
  * level 11, max_pills 300, garbage ON. A side asymmetry that exists only at
    other levels or with the attack channel severed is out of scope.
  * the champion-vs-evolved-adversary and champion-vs-champion pairings only. It
    says nothing about human opponents or the native-d1 stand-in.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
from collections import defaultdict

# ----------------------------------------------------------------- registered rule
CLAIM_DELTA_PP = 5.33      # the effect this re-test was funded to detect (6.00 - 0.67)
CONFIRM_RATIO = 2.0        # a CONFIRM also needs the higher side >= 2x the lower
ALPHA = 0.05
MIRROR_BOUND = 0.05        # an "absent" mirror verdict needs a CI tighter than this


def load(paths):
    rows, meta = [], []
    for p in paths:
        with open(p) as fh:
            for line in fh:
                r = json.loads(line)
                if "_status" in r:
                    meta.append({**r, "_file": p})
                else:
                    rows.append(r)
    return rows, meta


# --------------------------------------------------------------------- statistics
def boot_ci(vals, n=10000, seed=12345, stat=None):
    """Seed-clustered bootstrap: `vals` must already be ONE value per seed."""
    if not vals:
        return (float("nan"), float("nan"))
    stat = stat or (lambda xs: sum(xs) / len(xs))
    rng = random.Random(seed)
    k = len(vals)
    reps = sorted(stat([vals[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def binom_exact_two_sided(b, c):
    """Exact McNemar: P(|X - n/2| >= |b - n/2|) for X ~ Binom(b+c, 0.5).

    Summed in LOG space. The naive `math.comb(n, k) / 2**n` overflows float for
    n above ~1000, and the overflow raises rather than returning a wrong number --
    but only for the large-n tables, which are exactly the ones a gate built on
    small synthetic cases would never reach.
    """
    n = b + c
    if n == 0:
        return float("nan")
    obs = abs(b - n / 2)
    ln2 = math.log(2.0)
    lg = math.lgamma
    tot = 0.0
    for k in range(n + 1):
        if abs(k - n / 2) >= obs - 1e-12:
            tot += math.exp(lg(n + 1) - lg(k + 1) - lg(n - k + 1) - n * ln2)
    return min(1.0, tot)


# -------------------------------------------------------------------- the two arms
def analyse_adv(rows):
    """PRIMARY ENDPOINT. Champion death rate as a function of the champion's SEAT."""
    by_seed = defaultdict(dict)
    for r in rows:
        by_seed[r["seed"]][r["champ_side"]] = r
    paired = {s: d for s, d in by_seed.items() if 0 in d and 1 in d}

    b = c = 0                      # b: died as P1 only, c: died as P2 only
    per_seed_delta = []
    n0 = n1 = 0
    for s, d in sorted(paired.items()):
        d0 = int(d[0]["champ_died"])   # champion seated at side 0
        d1 = int(d[1]["champ_died"])   # champion seated at side 1
        n0 += d0
        n1 += d1
        b += (d0 and not d1)
        c += (d1 and not d0)
        per_seed_delta.append(d0 - d1)

    n = len(paired)
    lo, hi = boot_ci(per_seed_delta)
    return {
        "n_seeds": n, "n_games": 2 * n,
        "deaths_side0": n0, "deaths_side1": n1,
        "rate_side0": n0 / n if n else float("nan"),
        "rate_side1": n1 / n if n else float("nan"),
        "delta_pp": 100 * (n0 - n1) / n if n else float("nan"),
        "delta_ci_pp": [100 * lo, 100 * hi],
        "discordant_b": b, "discordant_c": c,
        "mcnemar_p": binom_exact_two_sided(b, c),
        "total_deaths": n0 + n1,
    }


def analyse_mirror(rows):
    """MECHANISM ARM. Champion vs champion, each seed played in BOTH board
    orientations, so the board draw cancels exactly and any residual seat
    preference is harness/mechanics rather than skill."""
    by_seed = defaultdict(dict)
    for r in rows:
        by_seed[r["seed"]][r["board_orient"]] = r
    paired = {s: d for s, d in by_seed.items() if 0 in d and 1 in d}

    win0_frac, death0_frac = [], []
    seat_det = board_det = 0
    stalls = 0
    d0 = d1 = 0
    for s, d in sorted(paired.items()):
        ws = [d[0]["winner_side"], d[1]["winner_side"]]
        stalls += sum(1 for w in ws if w < 0)
        if all(w >= 0 for w in ws):
            win0_frac.append(sum(1 for w in ws if w == 0) / 2.0)
            # the decomposition: same SEAT wins twice vs same BOARD wins twice
            if ws[0] == ws[1]:
                seat_det += 1
            else:
                board_det += 1
        ds = [d[0]["death_side"], d[1]["death_side"]]
        got = [x for x in ds if x >= 0]
        if got:
            death0_frac.append(sum(1 for x in got if x == 0) / len(got))
            d0 += sum(1 for x in got if x == 0)
            d1 += sum(1 for x in got if x == 1)

    wlo, whi = boot_ci(win0_frac)
    dlo, dhi = boot_ci(death0_frac)
    return {
        "n_seeds": len(paired), "n_games": 2 * len(paired), "stall_games": stalls,
        "win0_rate": sum(win0_frac) / len(win0_frac) if win0_frac else float("nan"),
        "win0_ci": [wlo, whi],
        "seat_determined_seeds": seat_det, "board_determined_seeds": board_det,
        "deaths_side0": d0, "deaths_side1": d1, "total_deaths": d0 + d1,
        "death0_rate": sum(death0_frac) / len(death0_frac) if death0_frac else float("nan"),
        "death0_ci": [dlo, dhi],
        # ⚠ GAME-level, not seed-clustered: anti-conservative, reported for shape only.
        # The mirror verdict rests on win0_ci / death0_ci, which ARE seed-clustered.
        "death_mcnemar_p_GAMELEVEL": binom_exact_two_sided(d0, d1),
        "n_seeds_with_death": len(death0_frac),
    }


# ----------------------------------------------------------------------- verdicts
def verdict_adv(a):
    """Registered bands for the PRIMARY endpoint. Written before any data existed."""
    if a["total_deaths"] == 0:
        return ("UNMEASURABLE",
                "zero champion deaths in either seat: the arm cannot express the "
                "quantity, so this is not evidence of symmetry (rule 24 #2)")
    p = a["mcnemar_p"]
    hi, lo = max(a["rate_side0"], a["rate_side1"]), min(a["rate_side0"], a["rate_side1"])
    ratio = (hi / lo) if lo > 0 else float("inf")
    ci = a["delta_ci_pp"]
    excl = abs(ci[0]) < CLAIM_DELTA_PP and abs(ci[1]) < CLAIM_DELTA_PP
    if p < ALPHA and ratio >= CONFIRM_RATIO:
        return ("CONFIRM", f"McNemar p={p:.4g} < {ALPHA} and ratio {ratio:.2f}x "
                           f">= {CONFIRM_RATIO}x")
    if p >= ALPHA and excl:
        return ("REFUTE", f"McNemar p={p:.4g}; 95% CI on delta {ci[0]:.2f}..{ci[1]:.2f} pp "
                          f"excludes the claimed {CLAIM_DELTA_PP} pp")
    if p < ALPHA:
        return ("INDETERMINATE", f"p={p:.4g} significant but ratio {ratio:.2f}x below "
                                 f"the {CONFIRM_RATIO}x bar -- a real but much smaller effect")
    return ("INDETERMINATE", f"p={p:.4g} and the CI {ci[0]:.2f}..{ci[1]:.2f} pp still "
                             f"contains the claimed {CLAIM_DELTA_PP} pp: underpowered, "
                             f"not negative")


def verdict_mirror(m):
    lo, hi = m["win0_ci"]
    half = (hi - lo) / 2
    if not (lo <= 0.5 <= hi):
        return ("STRUCTURAL_BIAS", f"P(side 0 wins)={m['win0_rate']:.4f} "
                                   f"CI [{lo:.4f},{hi:.4f}] excludes 0.5 in a perfect "
                                   f"board-cancelled mirror")
    if half < MIRROR_BOUND:
        return ("NO_STRUCTURAL_BIAS", f"CI [{lo:.4f},{hi:.4f}] contains 0.5 with "
                                      f"half-width {half:.4f} < {MIRROR_BOUND}")
    return ("INDETERMINATE", f"CI [{lo:.4f},{hi:.4f}] half-width {half:.4f} too wide")


# -------------------------------------------------------------------- mutant gate
def gate_swap_mutant(base_rows, mut_rows):
    """The killed-mutant gate on the SIDE COUNTER: relabelling sides at scoring time
    must exchange every by-side count EXACTLY. A counter that survives this is not
    reading the side at all."""
    def counts(rows):
        arm = rows[0]["arm"]
        if arm == "adv":
            a = analyse_adv(rows)
            return (a["deaths_side0"], a["deaths_side1"],
                    a["discordant_b"], a["discordant_c"])
        m = analyse_mirror(rows)
        return (m["deaths_side0"], m["deaths_side1"],
                m["seat_determined_seeds"], m["board_determined_seeds"])
    base, mut = counts(base_rows), counts(mut_rows)
    ok_deaths = (base[0], base[1]) == (mut[1], mut[0])
    # seat/board determination and discordance are side-symmetric by construction,
    # so they must be INVARIANT, not exchanged -- an equally strong prediction.
    ok_inv = (base[2], base[3]) == (mut[3], mut[2]) or (base[2], base[3]) == (mut[2], mut[3])
    return {"base": base, "mutant": mut, "deaths_exchanged": ok_deaths,
            "pass": bool(ok_deaths and ok_inv)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adv", nargs="*", default=[])
    ap.add_argument("--mirror", nargs="*", default=[])
    ap.add_argument("--adv-mutant", nargs="*", default=[])
    ap.add_argument("--mirror-mutant", nargs="*", default=[])
    ap.add_argument("--same-board", nargs="*", default=[],
                    help="the population mutant: both seats on one virus board")
    ap.add_argument("--json-out", default=None)
    a = ap.parse_args()

    out = {}
    if a.mirror:
        rows, _ = load(a.mirror)
        m = analyse_mirror(rows)
        v, why = verdict_mirror(m)
        m["verdict"], m["verdict_reason"] = v, why
        out["mirror"] = m
    if a.adv:
        rows, _ = load(a.adv)
        d = analyse_adv(rows)
        v, why = verdict_adv(d)
        d["verdict"], d["verdict_reason"] = v, why
        out["adv"] = d
    if a.same_board:
        rows, _ = load(a.same_board)
        out["same_board"] = analyse_mirror(rows)
    for tag, base_p, mut_p in (("adv", a.adv, a.adv_mutant),
                               ("mirror", a.mirror, a.mirror_mutant)):
        if base_p and mut_p:
            br, _ = load(base_p)
            mr, _ = load(mut_p)
            seeds = {r["seed"] for r in mr}
            out[f"mutant_gate_{tag}"] = gate_swap_mutant(
                [r for r in br if r["seed"] in seeds], mr)

    print(json.dumps(out, indent=2, default=str))
    if a.json_out:
        with open(a.json_out, "w") as fh:
            json.dump(out, fh, indent=2, default=str)


if __name__ == "__main__":
    main()
