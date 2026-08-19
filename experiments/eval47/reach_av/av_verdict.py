#!/usr/bin/env python3
"""Evaluate the PRE-REGISTERED kill criterion against the dose-response results.

CRITERION (registered before the run, NOT softened here).  The best A_v dose must
    (a) beat baseline dies-ahead by >= 2.5 percentage points, AND
    (b) beat baseline bad-ends  by >= 3.0 percentage points, AND
    (c) do so with >= 60 discordant pairs, AND
    (d) the scale-matched reach=OFF control must NOT reproduce the gain.
"Best" is chosen on the PRIMARY endpoint (dies-ahead delta).

THE INADMISSIBLE AMENDMENT, NAMED SO IT CANNOT BE MADE QUIETLY.  The mass
decomposition (av_mass_decomp.py) showed A_v's effective lever is 24.9% of
sum(max(hq,vq)), not the 44.9% axis-level figure -- roughly a quarter of what the
task brief assumed.  The tempting move is to scale the bar down in proportion.
That would move the decision after seeing data and is FORBIDDEN.  The thresholds
above stand exactly as written.

THE ADMISSIBLE HANDLING (this routing is itself pre-registered -- committed while
the sweep was on arm 1 of 11, with ZERO arm summaries written and no results JSON
on disk; the commit that introduced this docstring is the timestamp).  A sub-bar
result is never promoted to a pass; it is ROUTED:

  PASS        all of (a)-(d) hold.
  ROUTE_A_H   NOT a pass, but the shape shows an undersized signal:
                (i)   best A_v dies-ahead delta > 0 (directional, primary endpoint)
                (ii)  >= 60 discordant pairs -- the SAME healthiness threshold as
                      (c), deliberately not a looser one
                (iii) best A_v beats its OWN scale-matched control on the primary
                      endpoint (the shape, not the scalar, is carrying it)
              Verdict: "A_v alone insufficient -- proceed to A_v+A_h."  The
              horizontal half is the indicated next step because max(hq,vq)
              currently swallows the correction for 26.3% of the viruses that lose
              vertical credit; unmasking those is what A_h buys.
  REFUTED     anything else.  Report the numbers and stop.

WHY THE CONTROL ROW IS THE WHOLE TEST.  A_v and its scale-matched scalar-only arm
flip nearly identical shares of real decisions at every dose (3.83% vs 3.92% at
w=8; 26.3% vs 26.6% at w=24).  So "A_v beats baseline" proves nothing -- the pure
scalar space is already closed by coefficient optimisation.  Only "A_v beats its
matched control at the same flip rate" credits the SHAPE.  One control per dose
(constant 0.7506 ratio) makes that readable dose-by-dose rather than at a point.

Usage: av_verdict.py results/av_bursty_n300.json
"""
from __future__ import annotations

import json
import sys

DA_MIN_PTS = 2.5
BE_MIN_PTS = 3.0
MIN_DISCORDANT = 60


def main(path):
    with open(path) as fh:
        d = json.load(fh)
    n = d["n"]
    base = d["baseline"]
    arms = d["arms"]
    print(f"kernel_hash={d['kernel_hash']}  n={n}  L{d['level']}  wt={d['wt']} ws={d['ws']}"
          f"  model=bursty-v1.1")
    print(f"BASELINE (champion strand180_20, reach OFF w_rdyext=8): "
          f"dies-ahead {base['dies_ahead']}/{base['n']} = {base['dies_ahead'] / base['n']:.2%}"
          f"   bad-ends {base['bad_ends']}/{base['n']} = {base['bad_ends'] / base['n']:.2%}")
    print()
    hdr = (f"{'arm':>32s} {'DA n':>7s} {'DA rate':>8s} {'DA pts':>7s} {'DA disc':>8s} "
           f"{'DA p':>7s} {'BE n':>6s} {'BE rate':>8s} {'BE pts':>7s} {'BE disc':>8s} "
           f"{'BE p':>7s} {'clear':>7s}")
    print(hdr)
    print("-" * len(hdr))
    for r in arms:
        print(f"{r['tag']:>32s} {r['dies_ahead1']:>7d} {r['dies_ahead_rate1']:>7.2%} "
              f"{r['dies_ahead_delta_pts']:>+7.2f} {r['da_discordant_n']:>8d} "
              f"{r['da_p']:>7.4f} {r['bad_ends1']:>6d} {r['bad_rate1']:>7.2%} "
              f"{r['bad_delta_pts']:>+7.2f} {r['be_discordant_n']:>8d} {r['be_p']:>7.4f} "
              f"{r['clear1']:>7.1%}")

    av = [r for r in arms if r["tag"].startswith("A_v")]
    ctrl = [r for r in arms if r["tag"].startswith("SCALE-CTRL")]
    if not av:
        print("\nno A_v arms in file")
        return 2
    best = max(av, key=lambda r: r["dies_ahead_delta_pts"])
    print(f"\nBEST A_v arm on the primary endpoint: {best['tag']}")
    checks = [
        ("(a) dies-ahead delta >= +2.5 pts",
         best["dies_ahead_delta_pts"] >= DA_MIN_PTS,
         f"{best['dies_ahead_delta_pts']:+.2f} pts"),
        ("(b) bad-ends  delta >= +3.0 pts",
         best["bad_delta_pts"] >= BE_MIN_PTS,
         f"{best['bad_delta_pts']:+.2f} pts"),
        ("(c) >= 60 discordant pairs (primary)",
         best["da_discordant_n"] >= MIN_DISCORDANT,
         f"{best['da_discordant_n']} (b={best['da_discordant_b']}, "
         f"c={best['da_discordant_c']})"),
    ]
    cbest = max(ctrl, key=lambda r: r["dies_ahead_delta_pts"]) if ctrl else None
    if cbest is not None:
        reproduced = cbest["dies_ahead_delta_pts"] >= DA_MIN_PTS
        checks.append(("(d) scale-matched control does NOT reproduce it",
                       not reproduced,
                       f"best control {cbest['tag']} = "
                       f"{cbest['dies_ahead_delta_pts']:+.2f} pts"))
    print()
    for name, ok, detail in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<44s}  {detail}")
    passed = all(ok for _n, ok, _d in checks)

    # ---- the SHAPE test: best A_v vs ITS OWN matched control, dose by dose ----
    own = _matched_control(best, ctrl)
    print("\n  per-dose SHAPE test (A_v vs its OWN scale-matched control, same flip rate):")
    for r in av:
        m = _matched_control(r, ctrl)
        if m is None:
            print(f"    {r['tag']:>28s}: no matched control in file")
            continue
        gap = r["dies_ahead_delta_pts"] - m["dies_ahead_delta_pts"]
        print(f"    {r['tag']:>28s}: A_v {r['dies_ahead_delta_pts']:+6.2f} pts vs "
              f"control({m['tag'].split('w=')[-1]:>7s}) {m['dies_ahead_delta_pts']:+6.2f} pts"
              f"   shape gap {gap:+6.2f} pts")

    if passed:
        verdict = "PASS"
        text = "PASS -- A_v clears the pre-registered bar"
    elif (best["dies_ahead_delta_pts"] > 0
          and best["da_discordant_n"] >= MIN_DISCORDANT
          and own is not None
          and best["dies_ahead_delta_pts"] > own["dies_ahead_delta_pts"]):
        verdict = "ROUTE_A_H"
        text = ("ROUTE -- A_v alone INSUFFICIENT (sub-bar), but directional with "
                "healthy discordant counts and beating its own matched control: "
                "proceed to A_v+A_h. NOT a softened pass.")
    else:
        verdict = "REFUTED"
        text = "REFUTED -- report the numbers and stop."
    print(f"\nPRE-REGISTERED VERDICT: {verdict}\n  {text}")
    return {"PASS": 0, "ROUTE_A_H": 3, "REFUTED": 1}[verdict]


def _matched_control(av_row, ctrl_rows, ratio=0.7506, tol=0.05):
    """The reach=OFF control whose mean term contribution matches this A_v dose."""
    try:
        w = float(av_row["tag"].split("=")[-1])
    except ValueError:
        return None
    want = w * ratio
    for r in ctrl_rows:
        try:
            cw = float(r["tag"].split("=")[-1])
        except ValueError:
            continue
        if abs(cw - want) <= tol:
            return r
    return None


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
