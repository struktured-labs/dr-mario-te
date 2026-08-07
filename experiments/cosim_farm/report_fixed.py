#!/usr/bin/env python3
"""The deliverable for the fixed tier-3 firmware: D_fixed - A and B_fixed - A.

WHY ONLY AGAINST A. Arm A (`s20b_drop`, v1 emitter) is the ONLY clean baseline. Arms B
and D both ran the tier-3 firmware, whose `tre_commit` writes TP_TARGET -> D_BC and the
orientation -> D_BO. Drop mode ignores the DESCRIPTOR, not the PLACEMENT, so a spurious
win moved arm B's published column too: measured 0/58 clear for B against 51/53 for A.
Any comparison with old B or old D as the control is void.

  D_fixed - A   does a correctly-scored tuck arm beat the clean base?   <- the question
  B_fixed - A   does the fixed firmware, NOT tucking, match the base?   <- falsifier for
                                                                          the fix itself

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

PREDICTION = {
    "source": "fast-sim lane, registered before the fixed-firmware re-run existed",
    "clear_rate_gain_points": 5.0,
    "fire_rate_range": [0.05, 0.15],
}


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
    return by


def compare(by, cand, ctrl):
    seeds = sorted(set(by.get(cand, {})) & set(by.get(ctrl, {})))
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
    res = {"prediction": PREDICTION,
           "D_fixed_vs_A": compare(by, FIXED_TUCK, BASE),
           "B_fixed_vs_A": compare(by, FIXED_DROP, BASE)}
    for k in ("D_fixed_vs_A", "B_fixed_vs_A"):
        res[k]["verdict"] = verdict(res[k])

    print("arm row counts: " + "  ".join(f"{k}={len(v)}" for k, v in sorted(by.items())))
    for k in ("D_fixed_vs_A", "B_fixed_vs_A"):
        d = res[k]
        print(f"\n=== {k}  ({d['candidate']} vs {d['control']}) ===")
        if d.get("n_paired", 0) == 0:
            print("  no paired seeds yet")
            continue
        print(f"  n paired {d['n_paired']}  (cand-only {d['cand_only']}, "
              f"ctrl-only {d['ctrl_only']})   fw {d['fw']}")
        cl = d["clear"]
        print(f"  clear   cand {cl['cand']} CI[{cl['cand_ci'][0]:.1%},{cl['cand_ci'][1]:.1%}]"
              f"   ctrl {cl['ctrl']} CI[{cl['ctrl_ci'][0]:.1%},{cl['ctrl_ci'][1]:.1%}]")
        print(f"          delta {cl['delta_points']:+.1f} pts   discordant "
              f"{cl['discordant_cand_only']}/{cl['discordant_ctrl_only']}   "
              f"McNemar p={cl['mcnemar_p']}")
        v = d["viruses_cleared"]
        print(f"  viruses cleared  cand {v['cand']}  ctrl {v['ctrl']}  "
              f"delta {v['paired_delta']:+.2f}")
        f = d["fire_rate"]
        print(f"  fire rate  published {f['published_per_placement']}  "
              f"executed {f['executed_per_placement']}  incoherent {f['n_incoherent']}")
        print(f"  VERDICT: {d['verdict']}")

    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
        print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
