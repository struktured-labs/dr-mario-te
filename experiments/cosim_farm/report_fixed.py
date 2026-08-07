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
    out["viruses_cleared"] = {"cand": round(vc, 2), "ctrl": round(vk, 2),
                              "paired_delta": round(vc - vk, 2)}

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
            print(f"    viruses cleared  cand {v['cand']}  ctrl {v['ctrl']}  "
                  f"delta {v['paired_delta']:+.2f}")
            print(f"    fire rate  published {f['published_per_placement']}  "
                  f"executed {f['executed_per_placement']}  "
                  f"incoherent {f['n_incoherent']}")
            print(f"    VERDICT: {d['verdict']}")

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
