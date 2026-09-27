#!/usr/bin/env python3
"""KILLED-MUTANT TEST FOR THE VERDICT FUNCTION ITSELF.

A verdict rule that can only ever emit NO_GO is not a rule.  This builds
synthetic paired rollouts with a KNOWN answer and asserts `analyse.verdict`
returns it.  It also checks the two statistics the rule leans on (McNemar exact
and the seed-clustered paired bootstrap) against hand-computable cases.
"""
import json
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyse as A  # noqa: E402


def synth(n, da_b, da_t, clr_b, clr_t, rng, corr=0.85):
    """Paired rollout with per-seed correlation, so the CIs are realistic."""
    rows = []
    for i in range(n):
        u = rng.random()
        base = {"res": "", "won": 0, "topout": 0, "stall": 0, "pills": 150.0,
                "dies_ahead": 0}
        trt = dict(base)
        # correlated draws
        z = rng.random()
        zb = z if rng.random() < corr else rng.random()
        base["dies_ahead"] = int(z < da_b)
        trt["dies_ahead"] = int(zb < da_t)
        y = rng.random()
        yb = y if rng.random() < corr else rng.random()
        base["won"] = int(y < clr_b)
        trt["won"] = int(yb < clr_t)
        for d in (base, trt):
            d["topout"] = int(d["dies_ahead"] or (not d["won"] and u < 0.4))
            d["stall"] = int(not d["won"] and not d["topout"])
            d["res"] = "clear" if d["won"] else ("topout" if d["topout"] else "stall")
            d["flips"], d["plies_scored"] = 5, 200
        rows.append({"seed": 20000 + i, "base": base, "trt": trt})
    return rows


def run(tag, rows, expect):
    s = A.summarise(rows, tag)
    v = A.verdict(s, primary=True)
    got = v["verdict"]
    ok = got == expect
    print(f"  {tag:34s} expect {expect:12s} got {got:12s} "
          f"{'OK' if ok else '*** MISMATCH ***'}  "
          f"DA {s['metrics']['dies_ahead']['diff_trt_minus_base']*100:+.2f}pp "
          f"clr {s['metrics']['clear']['diff_trt_minus_base']*100:+.2f}pp")
    if not ok:
        print("     reasons:", v["reasons"])
    return ok


def main():
    rng = np.random.default_rng(4242)
    ok = True
    print("verdict-function killed-mutant tests")
    # 1. Large true DA win, clear rate UP -> must be GO
    ok &= run("big DA win, clear up", synth(3000, .12, .06, .80, .83, rng), "GO")
    # 2. Big DA win but clear rate collapses 4pp -> N1 must veto (NO_GO)
    ok &= run("big DA win, clear -4pp", synth(3000, .12, .06, .84, .80, rng), "NO_GO")
    # 3. No effect at all -> N2 (NO_GO)
    ok &= run("null effect", synth(3000, .12, .12, .80, .80, rng), "NO_GO")
    # 4. DA gets WORSE -> NO_GO
    ok &= run("DA worse", synth(3000, .10, .16, .80, .80, rng), "NO_GO")
    # 5. underpowered N -> INCONCLUSIVE
    ok &= run("N=800 underpowered", synth(800, .12, .06, .80, .83, rng),
              "INCONCLUSIVE")
    # 6. exact McNemar hand-checks
    assert abs(A.mcnemar_exact(0, 0) - 1.0) < 1e-12
    assert abs(A.mcnemar_exact(10, 0) - 2 * 0.5 ** 10) < 1e-12
    assert abs(A.mcnemar_exact(5, 5) - 1.0) < 1e-12
    p = A.mcnemar_exact(238, 214)
    assert 0.25 < p < 0.31, p
    print(f"  mcnemar_exact hand-checks OK (238/214 -> p={p:.4f})")
    # 7. bootstrap sanity: a constant -1pp difference must have a CI excluding 0
    d = np.full(3000, -0.01)
    lo, hi, fn, fp = A.boot_paired(d)
    assert hi < 0 and fn == 1.0, (lo, hi, fn)
    d0 = np.zeros(3000)
    lo0, hi0, _, _ = A.boot_paired(d0)
    assert lo0 == 0.0 and hi0 == 0.0
    print("  boot_paired sanity OK")
    print("VERDICT-FUNCTION TESTS:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
