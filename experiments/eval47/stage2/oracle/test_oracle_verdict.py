#!/usr/bin/env python3
"""Killed-mutant tests for the oracle-only verdict and null gates."""
from __future__ import annotations

import sys

import analyse_oracle as A


def summary(*, n=9000, da_diff=-0.03, da_ci=(-0.04, -0.02),
            clear_ci=(0.00, 0.02), bad_ci=(-0.04, -0.01), p=0.001,
            decidable=True, flip_rate=0.034):
    return {
        "n_pairs": n,
        "metrics": {
            "dies_ahead": {"diff_trt_minus_base": da_diff,
                           "diff_ci95": list(da_ci)},
            "clear": {"diff_ci95": list(clear_ci)},
            "bad_ends": {"diff_trt_minus_base": sum(bad_ci) / 2,
                         "diff_ci95": list(bad_ci)},
        },
        "discordance": {"dies_ahead": {"mcnemar_exact_p": p}},
        "power_adequacy": {"decidable": decidable},
        "realised_flip_rate": flip_rate,
    }


def expect(tag, got, wanted):
    ok = got == wanted
    print(f"  {tag:42s} expected={wanted:15s} got={got:15s} "
          f"{'OK' if ok else 'FAIL'}")
    return ok


def main():
    ok = True
    go = A.oracle_verdict(summary())
    ok &= expect("positive direction can pass", go["verdict"], "GO")
    ok &= expect("N1 clear loss veto",
                 A.oracle_verdict(summary(clear_ci=(-0.02, 0.00)))["verdict"],
                 "NO_GO")
    ok &= expect("N2 dies-ahead CI crosses zero",
                 A.oracle_verdict(summary(da_ci=(-0.02, 0.01)))["verdict"],
                 "NO_GO")
    ok &= expect("N2 McNemar p veto",
                 A.oracle_verdict(summary(p=0.2))["verdict"], "NO_GO")
    ok &= expect("N3 bad-end CI crossing zero veto",
                 A.oracle_verdict(summary(bad_ci=(-0.02, 0.01)))["verdict"],
                 "NO_GO")
    ok &= expect("undecidable co-primary cannot pass",
                 A.oracle_verdict(summary(decidable=False))["verdict"],
                 "NOT_DECIDABLE")
    ok &= expect("small N cannot pass",
                 A.oracle_verdict(summary(n=1499))["verdict"],
                 "INCONCLUSIVE")

    null_no = A.oracle_verdict(summary(da_diff=0.0, da_ci=(-0.01, 0.01),
                                       p=1.0, bad_ci=(-0.01, 0.01)))
    matched = A.dose_match(summary(flip_rate=.034), summary(flip_rate=.035))
    ok &= expect("true GO + matched null failure",
                 A.combined_verdict(go, null_no, matched)["verdict"], "GO")
    ok &= expect("a GO null voids self-confirming arm",
                 A.combined_verdict(go, go, matched)["verdict"], "VOID")
    mismatched = A.dose_match(summary(flip_rate=.034),
                              summary(flip_rate=.050))
    ok &= expect("over-dosed null voids comparison",
                 A.combined_verdict(go, null_no, mismatched)["verdict"],
                 "VOID")
    inconclusive = {"verdict": "INCONCLUSIVE", "reasons": ["synthetic"]}
    ok &= expect("unfinished null cannot validate GO",
                 A.combined_verdict(go, inconclusive, matched)["verdict"],
                 "INCONCLUSIVE")

    # Named paired transition count: two base topouts are avoided, one becomes
    # a stall.  A sign-only aggregate implementation cannot recover 1/2.
    rows = [
        {"base": {"topout": 1}, "trt": {"topout": 0, "stall": 1}},
        {"base": {"topout": 1}, "trt": {"topout": 0, "stall": 0}},
        {"base": {"topout": 0}, "trt": {"topout": 0, "stall": 1}},
    ]
    s = {"metrics": {
        "topout": {"diff_trt_minus_base": -2 / 3},
        "stall": {"diff_trt_minus_base": 2 / 3},
        "bad_ends": {"diff_trt_minus_base": 0.0,
                     "diff_ci95": [-0.2, 0.2]},
    }}
    sp = A.stall_parity(s, rows)
    sp_ok = (sp["topouts_avoided"] == 2
             and sp["topouts_converted_to_stalls"] == 1
             and sp["conversion_frac_of_avoided"] == 0.5)
    ok &= sp_ok
    print("  paired topout->stall count                 "
          f"expected=1/2 got={sp['topouts_converted_to_stalls']}/"
          f"{sp['topouts_avoided']} {'OK' if sp_ok else 'FAIL'}")

    print("ORACLE VERDICT MUTATION GATE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
