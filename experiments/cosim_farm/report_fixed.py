#!/usr/bin/env python3
"""The deliverable for the fixed tier-3 firmware: D_fixed - A and B_fixed - A.

WHY ONLY AGAINST A. Arm A (`s20b_drop`, v1 emitter) is the ONLY clean baseline. Arms B
and D both ran the tier-3 firmware, whose `tre_commit` writes TP_TARGET -> D_BC and the
orientation -> D_BO. Drop mode ignores the DESCRIPTOR, not the PLACEMENT, so a spurious
win moved arm B's published column too: measured 0/58 clear for B against 51/53 for A.
Any comparison with old B or old D as the control is void.

  D_fixed - A   does a correctly-scored tuck arm beat the clean base?   <- THE question

  B_fixed - A   ⚠ NOT a falsifier for the fix, despite how it was framed. Drop mode does
                not mean "the firmware declines to tuck" -- tre_commit still overwrites
                D_BC/D_BO with the tuck's TARGET column, and the driver then DROPS there
                without performing the maneuver. The pill comes to rest at the column's
                drop height instead of sliding under the overhang the tuck was aimed at,
                so the placement is incoherent BY CONSTRUCTION, exactly as v1's was and
                exactly why the "fail-safe" firmware variant was refused. A correct fix
                does NOT predict B_fixed ~ A; it predicts B_fixed stays bad.
                What B_fixed - A actually measures is worth having anyway: the cost of
                publishing a tuck placement that never gets executed -- which is the
                SHIPPED CART's situation, since the cart has no tuck executor at all.
                Read it as "what tier-3 would do on today's silicon", not as a check of
                the fix.

PRE-REGISTERED, written before any fixed-arm row existed (see PREDICTION below): the
fast-sim lane registered ~5-point clear-rate GAIN at a 5-15% fire rate. Recording it
here so the check is fixed in advance rather than chosen after seeing the numbers.

Usage: report_fixed.py [results.jsonl] [--out x.json]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
from collections import defaultdict

JSONL = "/mnt/data/drmario_cosim/results/tuck2x2_bursty.jsonl"
BASE = "s20b_drop"                       # the only clean baseline
FIXED_TUCK, FIXED_DROP = "s20t3fix_tuck", "s20t3fix_drop"

# Stratification boundary. Specified by this lane BEFORE the fast-sim lane looked at it,
# which is the only reason their split test carries any weight -- and the same reason it
# must be honoured here rather than re-chosen to taste.
BLOCK_BOUNDARY = 120
WAVE2_START = 135          # first seed of wave 2
WAVE3_START = 400          # outside the fast-sim lane's entire studied range (0-399)

PREDICTION = {
    "source": "fast-sim lane, registered before the fixed-firmware re-run existed",
    "clear_rate_gain_points": 5.0,
    "fire_rate_range": [0.05, 0.15],
    # Their SECOND prediction, put on the record before this wave ran, on whether their
    # own seed-block split is real: "if my split is real, your D_fixed - A should be
    # closer to null on 0-119 and favourable on 135-234; if my split was the coin flip,
    # both blocks look alike." They asked to be falsifiable, so it is adjudicated here
    # rather than left to prose.
    "block_split_is_real_iff": "delta(135-234) meaningfully better than delta(0-119)",
}


# ================= PRE-REGISTERED DECISION RULE (team lead, before n=55 existed) =======
# Three endpoints disagree, so choosing among them after seeing the data would be
# indistinguishable from rationalisation. The rule is therefore applied by CODE, not by
# whoever writes the summary. Do not edit these thresholds to fit a result.
#
#   PRIMARY ENDPOINT IS SURVIVAL (paired clear-rate discordance). NOT pills.
#
#   1. survival cost REPLICATES (p<0.05, one-directional toward the champion)
#        -> NET HARMFUL. Do not build the executor -- EVEN IF conditional pills stays
#           strongly negative. Speed does not buy back an absorbing state, and four
#           independent lanes agree the champion's problem is risk-neutrality near one.
#           A -40-pill headline beside a significant survival cost is a WORSE result
#           than a null, not a better one.
#   2. survival balanced AND conditional pills CI excludes 0 AND the failure-ranked
#      combined test ALSO excludes 0
#        -> GENUINE WIN. Executor becomes a hardware priority, re-proven on the
#           near-death control first.
#   3. survival balanced, combined still spans 0
#        -> WASH at n=55. PARK IT. Still a real deliverable: it retires a question this
#           project has spent weeks on, on validated firmware with a validated control.
#   4. t3_noscan diverges on the NEAR-DEATH corpus
#        -> ATTRIBUTION VOID. Checked FIRST, because it invalidates 1-3.
#
# BINDINGS:
#   * conditional pills is NEVER promoted to primary on its own -- conditioning on
#     mutually-cleared seeds drops exactly the games the candidate lost.
#   * discordance under MIN_DISCORDANT either way -> "not testable at n=55", no direction.
#     Rule 19 applies hardest when the direction agrees with what someone expected.
MIN_DISCORDANT = 5
NEARDEATH_CONTROL = "/mnt/data/drmario_cosim/results/control_noscan_death125.json"


def preregistered_verdict(d):
    """Apply the decision rule mechanically. Returns (outcome, text)."""
    # --- outcome 4 first: it invalidates everything else ---
    try:
        with open(NEARDEATH_CONTROL) as fh:
            ctl = json.load(fh)
        diffs = None
        for k, v in (ctl.get("comparisons") or {}).items():
            diffs = v.get("n_placement_differs")
        if diffs is not None and diffs > 0:
            return (4, f"OUTCOME 4 -- ATTRIBUTION VOID: t3_noscan diverges from base on "
                       f"{diffs} near-death boards, so both the pills delta and the "
                       f"survival discordance are partly attributable to an unidentified "
                       f"image difference.")
    except FileNotFoundError:
        pass                       # near-death control not run yet; note it below

    if d.get("n_paired", 0) == 0:
        return (None, "no data")
    cl = d["clear"]
    b, c = cl["discordant_cand_only"], cl["discordant_ctrl_only"]
    tot = b + c
    if tot < MIN_DISCORDANT:
        return (0, f"NOT TESTABLE at this n: only {tot} discordant pair(s) "
                   f"({b} cand-only / {c} ctrl-only). Report the count and the n, and "
                   f"state NO direction -- rules 13 and 19.")

    survival_bad = cl["mcnemar_p"] < 0.05 and c > b
    if survival_bad:
        return (1, f"OUTCOME 1 -- NET HARMFUL, DO NOT BUILD THE EXECUTOR. Survival cost "
                   f"replicates: {c} champion-only vs {b} candidate-only, McNemar "
                   f"p={cl['mcnemar_p']}. This verdict stands EVEN IF conditional pills "
                   f"is strongly negative -- speed does not buy back an absorbing state.")

    pb = d.get("pills_if_both_cleared") or {}
    pills_excl0 = bool(pb) and not (pb["ci95"][0] <= 0 <= pb["ci95"][1])
    cf = d.get("combined_failure_ranked") or {}
    combined_excl0 = bool(cf) and all(not r["spans_zero"] for r in cf.values())

    if pills_excl0 and combined_excl0:
        return (2, f"OUTCOME 2 -- GENUINE WIN. Survival not significant ({b} vs {c}), "
                   f"conditional pills {pb['mean_delta']:+.1f} CI excludes 0, AND the "
                   f"failure-ranked combined test excludes 0 at every penalty. Executor "
                   f"becomes a hardware priority -- re-prove on the near-death control "
                   f"first.")
    pills_txt = "" if not pb else f", conditional pills {pb['mean_delta']:+.1f}"

    # --- 3b: consistently ONE-DIRECTIONAL but underpowered. Added by the team lead after
    # seeing interim numbers, which normally disqualifies an amendment. Admissible here on
    # a test worth keeping for any mid-flight rule change: DOES IT ALTER WHAT WE DO, OR
    # ONLY WHAT WE SAY? 3 and 3b take the SAME action (do not build), so it changes only
    # the characterisation -- and it makes the report more conservative in BOTH directions
    # at once, refusing "tuck is harmful" as firmly as "tuck has no survival cost".
    # Had it moved the decision, the flawed wording would have had to stand.
    if c != b:
        toward = "the CHAMPION" if c > b else "the CANDIDATE"
        return (3.5, f"OUTCOME 3b -- DO NOT BUILD, AND DO NOT CLAIM HARM. Survival "
                     f"discordance is NOT SIGNIFICANT but {max(b, c)}-to-{min(b, c)} "
                     f"one-directional toward {toward} (p={cl['mcnemar_p']}). The "
                     f"survival question is OPEN, NOT ANSWERED, and settling it needs n "
                     f"well past this{pills_txt}. Same action as outcome 3; only the "
                     f"characterisation differs.")

    return (3, f"OUTCOME 3 -- WASH at this n. PARK IT. Survival discordance is EVEN "
               f"({b} vs {c}); the failure-ranked combined test still spans "
               f"zero{pills_txt}. NOT a wasted night -- it retires a question this "
               f"project has spent weeks on, on validated firmware with a validated "
               f"control.")


def block_verdict(d_null, d_oos):
    """Adjudicate the fast-sim lane's own split, out of sample."""
    if d_null.get("n_paired", 0) == 0 or d_oos.get("n_paired", 0) == 0:
        return "not yet testable -- need paired seeds in BOTH 0-119 and 135-234"
    a = d_null["clear"]["delta_points"]
    b = d_oos["clear"]["delta_points"]
    gap = b - a
    mde = max(x for x in (d_null["power"]["min_detectable_delta_points_approx"],
                          d_oos["power"]["min_detectable_delta_points_approx"], 0)
              if x is not None)
    if gap > mde:
        return (f"SUPPORTS their split: out-of-sample block is {gap:+.1f} points better "
                f"than the null block ({b:+.1f} vs {a:+.1f}), exceeding the ~{mde:.1f} "
                f"points this design can resolve")
    return (f"does NOT support their split: blocks look alike ({b:+.1f} vs {a:+.1f}, "
            f"gap {gap:+.1f}) against ~{mde:.1f} points of resolution -- consistent with "
            f"their p=0.023 being the one test in twenty, which they said they would own")


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar_exact(b, c):
    """Two-sided exact binomial on the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


# Seed 1 is an UNWINNABLE game, not a hard one. Its LFSR state (s0,s1)=(0,1) steps
# straight into (0,0), an absorbing state, so all 128 buffer entries are capsule id 0 =
# colour (1,1): every pill is the same colour and no colour-2 or colour-3 virus can ever
# be cleared. Exactly one such seed exists in the whole 65,536 space, and it is in this
# lane's list. CONFIRMED INDEPENDENTLY from this rig's own rows, not taken on report:
# arm A -- the clean champion that clears 95% elsewhere -- cleared 0 of 48 viruses on
# seed 1 across 153 pills. It ties in every arm so McNemar is unaffected, but it dilutes
# every clear RATE, so it is excluded from the denominators and reported separately.
# (Seed 0 is fine: NesPillSource remaps (0,0) to the ROM warm-boot seed.)
DEGENERATE_SEEDS = {1}


def load(path, drop_degenerate=True):
    by = defaultdict(dict)
    dropped = defaultdict(int)
    for line in open(path):
        r = json.loads(line)
        if r.get("result") == "ERROR":
            continue
        if drop_degenerate and r["seed"] in DEGENERATE_SEEDS:
            dropped[r["arm"]] += 1
            continue
        by[r["arm"]][r["seed"]] = r
    if dropped:
        print("excluded degenerate seed(s) "
              + ",".join(map(str, sorted(DEGENERATE_SEEDS))) + ": "
              + "  ".join(f"{k}={v}" for k, v in sorted(dropped.items())))
    return by


def compare(by, cand, ctrl, seed_filter=None):
    seeds = sorted(set(by.get(cand, {})) & set(by.get(ctrl, {})))
    if seed_filter is not None:
        seeds = [s for s in seeds if seed_filter(s)]
    n = len(seeds)
    out = {"candidate": cand, "control": ctrl, "n_paired": n,
           "cand_only": len(set(by.get(cand, {})) - set(by.get(ctrl, {}))),
           "ctrl_only": len(set(by.get(ctrl, {})) - set(by.get(cand, {})))}
    if n == 0:
        out["note"] = "no paired seeds yet"
        return out

    C = [by[cand][s] for s in seeds]
    K = [by[ctrl][s] for s in seeds]
    out["fw"] = {cand: sorted({r["fw_md5"][:8] for r in C}),
                 ctrl: sorted({r["fw_md5"][:8] for r in K})}

    kc = sum(r["result"] == "clear" for r in C)
    kk = sum(r["result"] == "clear" for r in K)
    b = sum(1 for x, y in zip(C, K) if x["result"] == "clear" and y["result"] != "clear")
    c = sum(1 for x, y in zip(C, K) if x["result"] != "clear" and y["result"] == "clear")
    out["clear"] = {
        "cand": f"{kc}/{n} = {kc/n:.1%}", "ctrl": f"{kk}/{n} = {kk/n:.1%}",
        "cand_ci": [round(v, 4) for v in wilson(kc, n)],
        "ctrl_ci": [round(v, 4) for v in wilson(kk, n)],
        "delta_points": round(100 * (kc - kk) / n, 1),
        "discordant_cand_only": b, "discordant_ctrl_only": c,
        "mcnemar_p": round(mcnemar_exact(b, c), 5),
    }

    vc = sum(r["viruses_cleared"] for r in C) / n
    vk = sum(r["viruses_cleared"] for r in K) / n
    # Paired bootstrap over WITHIN-SEED differences. Pairing is the whole point of this
    # design, so the CI must resample seeds, not arms. Fixed RNG so it cannot drift
    # between runs of the same data.
    diffs = [c["viruses_cleared"] - k["viruses_cleared"] for c, k in zip(C, K)]
    rng = random.Random(12345)
    boots = sorted(sum(rng.choice(diffs) for _ in range(n)) / n for _ in range(10000))
    out["viruses_cleared"] = {
        "cand": round(vc, 2), "ctrl": round(vk, 2),
        "paired_delta": round(vc - vk, 2),
        "paired_delta_ci95": [round(boots[249], 2), round(boots[9749], 2)],
        "n_seeds_moved": sum(1 for d in diffs if d != 0),
        "WARNING": ("CEILING-CENSORED. viruses_cleared pins at 48 whenever BOTH arms "
                    "clear, and the champion clears ~96% of clean L11, so this metric "
                    "has almost no dynamic range here. d=0 means 'both finished the "
                    "job', NOT 'same game' -- measured, the arms differ in PILLS on "
                    "15/15 mutually-cleared seeds, median 43 pills apart. Do not read "
                    "'seeds moved' off this endpoint; use pills_if_both_cleared."),
    }

    # ---- ENDPOINT 2: pills, CONDITIONAL on both arms clearing. Uncensored, but BIASED
    # by construction: conditioning on mutual success drops exactly the seeds where the
    # candidate failed. Never report it without endpoint 1 and 3 beside it.
    both = [(c, k) for c, k in zip(C, K)
            if c["result"] == "clear" and k["result"] == "clear"]
    if both:
        pd_ = [c["pills"] - k["pills"] for c, k in both]
        rng2 = random.Random(999)
        bb = sorted(sum(rng2.choice(pd_) for _ in range(len(pd_))) / len(pd_)
                    for _ in range(10000))
        faster = sum(1 for d in pd_ if d < 0)
        slower = sum(1 for d in pd_ if d > 0)
        out["pills_if_both_cleared"] = {
            "n": len(both), "mean_delta": round(sum(pd_) / len(pd_), 1),
            "ci95": [round(bb[249], 1), round(bb[9749], 1)],
            "faster": faster, "slower": slower, "ties": len(pd_) - faster - slower,
            "sign_test_p": round(mcnemar_exact(faster, slower), 4),
        }

    # ---- ENDPOINT 3: combined. Rank a FAILURE as worse than any success by charging it
    # a penalty pill count, then re-run over ALL paired seeds. Swept across penalties
    # because the answer must not depend on how harshly a loss is priced -- if the sign
    # flips with the penalty, that itself is the finding.
    out["combined_failure_ranked"] = {}
    for pen in (250, 500, 750, 1000):
        def _p(r):
            return r["pills"] if r["result"] == "clear" else pen
        dd = [_p(c) - _p(k) for c, k in zip(C, K)]
        rng3 = random.Random(4242)
        bb3 = sorted(sum(rng3.choice(dd) for _ in range(n)) / n for _ in range(10000))
        f = sum(1 for d in dd if d < 0)
        sl = sum(1 for d in dd if d > 0)
        out["combined_failure_ranked"][f"penalty_{pen}"] = {
            "mean_delta": round(sum(dd) / n, 1),
            "ci95": [round(bb3[249], 1), round(bb3[9749], 1)],
            "spans_zero": bb3[249] <= 0 <= bb3[9749],
            "sign_test_p": round(mcnemar_exact(f, sl), 4),
        }

    # Tucks per game split by OUTCOME. A flat average hides "neutral overall but
    # CONCENTRATED IN THE LOSSES", which would be a different and more interesting
    # finding than a null. Broken out rather than left to be asked for.
    won = [r for r in C if r["result"] == "clear"]
    lost = [r for r in C if r["result"] != "clear"]

    def _per_game(rows, key):
        return None if not rows else round(sum(r[key] for r in rows) / len(rows), 2)

    def _per_placement(rows):
        # ⚠ PER-GAME COUNTS CONFOUND WITH GAME LENGTH. A failed game tops out early and
        # therefore places far fewer pills, so it MECHANICALLY shows fewer tucks per game
        # whatever the policy does. Normalising by placements is the only way to read
        # "does it tuck MORE when losing" -- the same paired-denominator rule the
        # virus-tempo principle already forced on this project once.
        pl = sum(r["pills"] for r in rows)
        return None if not pl else round(sum(r["n_tuck"] for r in rows) / pl, 4)

    out["tucks_by_outcome"] = {
        "cleared": {"n": len(won), "executed_per_game": _per_game(won, "n_tuck"),
                    "pills_per_game": _per_game(won, "pills"),
                    "executed_per_placement": _per_placement(won)},
        "failed": {"n": len(lost), "executed_per_game": _per_game(lost, "n_tuck"),
                   "pills_per_game": _per_game(lost, "pills"),
                   "executed_per_placement": _per_placement(lost)},
    }

    pills = sum(r["pills"] for r in C)
    pub = sum(r["n_tuck_published"] for r in C)
    ex = sum(r["n_tuck"] for r in C)
    out["fire_rate"] = {
        "published_per_placement": round(pub / pills, 4) if pills else None,
        "executed_per_placement": round(ex / pills, 4) if pills else None,
        "n_incoherent": sum(r["n_incoherent"] for r in C),
    }

    # What this n can and cannot exclude, at the observed control rate.
    p0 = kk / n
    mde = 1.96 * math.sqrt(2 * p0 * (1 - p0) / n) if 0 < p0 < 1 else None
    out["power"] = {
        "control_rate": round(p0, 4),
        "min_detectable_delta_points_approx": (None if mde is None
                                               else round(100 * mde, 1)),
    }
    return out


def verdict(d):
    if d.get("n_paired", 0) == 0:
        return "no data yet"
    cl = d["clear"]
    got = cl["delta_points"]
    p = cl["mcnemar_p"]
    mde = d["power"]["min_detectable_delta_points_approx"]
    pred = PREDICTION["clear_rate_gain_points"]
    lo, hi = PREDICTION["fire_rate_range"]
    fr = d["fire_rate"]["published_per_placement"]
    bits = [f"observed clear-rate delta {got:+.1f} points, McNemar p={p}"]
    if p < 0.05:
        bits.append("SIGNIFICANT")
    elif mde is not None and abs(got) < mde:
        bits.append(f"NOT resolved at this n -- the design can only detect ~{mde:.1f} "
                    f"points, so anything smaller is UNRESOLVED, not absent")
    else:
        bits.append("not significant")
    if fr is not None:
        inside = lo <= fr <= hi
        bits.append(f"fire rate {fr:.1%} "
                    f"({'inside' if inside else 'OUTSIDE'} the pre-registered {lo:.0%}-{hi:.0%})")
        if not inside:
            bits.append("=> the pre-registered prediction was conditioned on a fire rate "
                        "this arm does not have; it is not a fair test of it")
        else:
            bits.append(f"=> prediction was {pred:+.0f} points; observed {got:+.1f}")
    return "; ".join(bits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", nargs="?", default=JSONL)
    ap.add_argument("--out")
    a = ap.parse_args()

    by = load(a.jsonl)

    # ⚠ THE SEED-120 SPLIT IS RETRACTED BY THE LANE THAT FOUND IT. Their own five-way
    # check killed it: the wobble WITHIN the "effect" block (thirds at -0.172, -0.075,
    # -0.022, spread 0.151) is ~3x the gap that defined the block (0.055), so it is a
    # gradient, not a cliff -- and a scan finds bigger splits elsewhere 39% of the time
    # under the null. Their p=0.023 was honest for a boundary specified in advance and
    # STILL pointed at nothing: a low p on a pre-specified boundary cannot tell you the
    # structure is AT that boundary.
    #
    # The strata stay anyway, for two reasons that survive the retraction: that lane
    # asked for 135-234 separately as reporting discipline ("a pooled number can't be
    # un-pooled later"), and 40-of-55 seeds in one narrow range is thin coverage on its
    # own merits. What changes is the EXPECTATION -- blocks looking alike is now the
    # predicted result and a second confirmation of the fluke, not a null.
    #
    # ⚠⚠ THE s0 STORY WAS ALSO WRONG, and that lane caught its own error. I had queued a
    # wave to cross seed 256 believing s0=(seed>>8)&0xFF made it a regime boundary. It
    # does not: the pill_switch_rate anomaly lives INSIDE s0=0 --
    #     0-119 (s0=0, lo s1) 0.8326  vs 120-255 (s0=0, hi s1) 0.8690   p=0.0000
    #     120-255 (s0=0)      0.8690  vs 256-399 (s0=1)        0.8648   p=0.44
    # so it is a LOW-SEED property, not an LFSR-high-byte one, and seed 256 is inert on
    # the input side (p=0.44) and their outcome side (p=0.92).
    #
    # ⇒ THE EXISTING WAVES ALREADY STRADDLE THE REAL ANOMALY, for free: wave 1 (0-134)
    # sits largely inside the low-seed region, wave 2 (135-234) sits outside it, and they
    # are already reported separately. That contrast IS the external-validity check.
    # Wave 3 was repointed to seeds 400-459, outside that lane's whole studied range,
    # which is the coverage gap that genuinely remains.
    # HEADLINE IS POOLED (team lead's call, once the split was retracted): fewer numbers,
    # more power, and less chance of someone reading a sub-block wobble as a finding. The
    # blocks are still COMPUTED and kept, for two reasons that are not in tension with
    # that: the fast-sim lane asked that 135-234 stay visible ("a pooled number can't be
    # un-pooled later"), and the split adjudicator below NEEDS 0-119 vs 135-234 to exist.
    # So: pooled first and prominent, blocks as a compact secondary table, everything in
    # the JSON.
    strata = [
        ("block 0-119    (wave 1)", lambda s: s < BLOCK_BOUNDARY),
        ("block 120-134  (wave 1 tail)",
         lambda s: BLOCK_BOUNDARY <= s < WAVE2_START),
        ("block 135-234  (wave 2, out-of-sample for the retracted split)",
         lambda s: WAVE2_START <= s < WAVE3_START),
        ("block 120+     (union, sub-256)",
         lambda s: BLOCK_BOUNDARY <= s < WAVE3_START),
        ("seeds 400+     (wave 3, outside BOTH studied ranges)",
         lambda s: s >= WAVE3_START),
    ]
    POOLED = ("POOLED  <- the headline", None)

    res = {"prediction": PREDICTION, "block_boundary": BLOCK_BOUNDARY,
           "degenerate_seeds_excluded": sorted(DEGENERATE_SEEDS), "comparisons": {}}

    print("arm row counts: " + "  ".join(f"{k}={len(v)}" for k, v in sorted(by.items())))
    for label, cand, ctrl in (("D_fixed_vs_A", FIXED_TUCK, BASE),
                              ("B_fixed_vs_A", FIXED_DROP, BASE)):
        res["comparisons"][label] = {}
        print(f"\n################ {label}  ({cand} vs {ctrl}) ################")

        # --- headline: pooled ---
        d = compare(by, cand, ctrl, POOLED[1])
        d["verdict"] = verdict(d)
        res["comparisons"][label][POOLED[0].split()[0]] = d
        if d.get("n_paired", 0) == 0:
            print("  no paired seeds yet")
        else:
            cl, v, f = d["clear"], d["viruses_cleared"], d["fire_rate"]
            print(f"  {POOLED[0]}   n paired {d['n_paired']}   fw {d['fw']}")
            print(f"    clear   cand {cl['cand']} "
                  f"CI[{cl['cand_ci'][0]:.1%},{cl['cand_ci'][1]:.1%}]"
                  f"   ctrl {cl['ctrl']} CI[{cl['ctrl_ci'][0]:.1%},{cl['ctrl_ci'][1]:.1%}]")
            print(f"            delta {cl['delta_points']:+.1f} pts   discordant "
                  f"{cl['discordant_cand_only']}/{cl['discordant_ctrl_only']}   "
                  f"McNemar p={cl['mcnemar_p']}")
            print(f"    [1] SURVIVAL (PRIMARY)  discordant "
                  f"{cl['discordant_cand_only']} cand-only vs "
                  f"{cl['discordant_ctrl_only']} champion-only   <- the interpretable "
                  f"quantity; p is downstream of it")
            print(f"        clear {cl['cand']} vs {cl['ctrl']}   McNemar p={cl['mcnemar_p']}")
            pb = d.get("pills_if_both_cleared")
            if pb:
                print(f"    [2] SPEED | both cleared  n={pb['n']}  "
                      f"delta {pb['mean_delta']:+.1f} pills "
                      f"CI[{pb['ci95'][0]:+.1f},{pb['ci95'][1]:+.1f}]  "
                      f"{pb['faster']} faster / {pb['slower']} slower  "
                      f"sign p={pb['sign_test_p']}")
                print(f"        ^ BIASED: conditioning on mutual success drops exactly "
                      f"the seeds where the candidate FAILED. Never quote alone.")
            cf = d.get("combined_failure_ranked") or {}
            if cf:
                bits = []
                for k2, r2 in cf.items():
                    bits.append(f"{k2.split('_')[1]}:{r2['mean_delta']:+.0f}"
                                f"{'~0' if r2['spans_zero'] else '!'}"
                                f"(p={r2['sign_test_p']})")
                print(f"    [3] COMBINED (failure ranked worst, penalty swept)  "
                      + "  ".join(bits))
                print(f"        ^ '~0' = CI spans zero. If the sign moves with the "
                      f"penalty, that IS the finding.")
            print(f"    (viruses cleared {v['cand']} vs {v['ctrl']}, delta "
                  f"{v['paired_delta']:+.2f} -- CEILING-CENSORED, see WARNING in JSON)")
            t = d["tucks_by_outcome"]
            for _o in ("cleared", "failed"):
                _t = t[_o]
                print(f"    tucks | {_o:7s} n={_t['n']:3d}  "
                      f"{_t['executed_per_game']}/game over {_t['pills_per_game']} pills"
                      f"  => {_t['executed_per_placement']}/placement")
            print(f"    fire rate  published {f['published_per_placement']}  "
                  f"executed {f['executed_per_placement']}  "
                  f"incoherent {f['n_incoherent']}")
            if cand == FIXED_TUCK:
                oc, txt = preregistered_verdict(d)
                print(f"    >>> PRE-REGISTERED VERDICT: {txt}")
                res["comparisons"][label]["preregistered_outcome"] = oc
                res["comparisons"][label]["preregistered_text"] = txt
            print(f"    (fire-rate note: {d['verdict']})")

        # --- secondary: blocks kept visible, one line each ---
        print(f"    by block (kept visible on request; the split itself is RETRACTED "
              f"-- blocks are expected to look alike):")
        for sname, sfilt in strata:
            b = compare(by, cand, ctrl, sfilt)
            res["comparisons"][label][sname.strip()] = b
            if b.get("n_paired", 0) == 0:
                print(f"      {sname:62s} n=0")
                continue
            print(f"      {sname:62s} n={b['n_paired']:3d}  "
                  f"cand {b['clear']['cand']:15s} ctrl {b['clear']['ctrl']:15s} "
                  f"delta {b['clear']['delta_points']:+6.1f}  p={b['clear']['mcnemar_p']}")

    # Out-of-sample adjudication of the fast-sim lane's own seed-block split.
    cmp_d = res["comparisons"]["D_fixed_vs_A"]
    bv = block_verdict(cmp_d.get("block 0-119   (wave 1, their null block)", {}),
                       cmp_d.get("block 135-234 (wave 2, OUT-OF-SAMPLE)", {}))
    res["block_split_adjudication"] = bv
    print(f"\n################ fast-sim lane's seed-block split, OUT OF SAMPLE ###########")
    print(f"  {bv}")

    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
        print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
