#!/usr/bin/env python3
"""score_d114.py -- score the #114 re-run against PREREG_ROTDIR_V3, and NOTHING else.

Every threshold here is inherited verbatim from PREREG_ROTDIR_V2 (scope, seeds, inclusion,
power bar, P1, P3, verdict routing); v3 added only the harness-validity census, the no-pooling
rule, and the rule-12 mechanism constraint. This script implements those and refuses to
improvise: if a cell is missing it is reported MISSING, never dropped quietly, because v2's
whole NO-VERDICT turned on a missing cell being visible.

Reading order is fixed by the prereg and enforced by the code path:
  1. VALIDITY   leaked==0 and blocked>=1 per arm, else the cell is INVALID (v3-B)
  2. INCLUSION  both arms wedges==0, else the PAIR is dropped (v2)
  3. POWER      >= 8 of 16 surviving pairs, else NO-VERDICT (v2)
  4. P3         press census -- the MECHANISM (v2)
  5. RULE 12    P1 is only read as a flag effect if P3 held on the same pairs (v3-C)
  6. P1         mean delta <= -1.5 f/pill AND paired 95% CI upper bound < 0 (v2)

Exit 0 = a verdict was produced (GO or a registered non-GO). Exit 1 = NO-VERDICT / blocked.
"""
from __future__ import annotations

import os
import re
import statistics
import sys

D = "/home/struktured/projects/dr-mario-hygiene-wt/tmp/d114"
SEEDS = [4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008, 4009,
         4010, 4011, 4012, 4013, 4014, 4015, 4016]
MAXF = 12000
ORIENT = 1

# two-sided 95% t critical values by df -- embedded so the gate has no numeric dependency
# whose version could silently change a published interval.
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
       9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
       16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 21: 2.080, 22: 2.074,
       23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045,
       30: 2.042}


def cell(arm, seed):
    """Parse one cell. Returns dict or None if the run is MISSING."""
    d = os.path.join(D, f"d114_{arm}_o{ORIENT}_{MAXF}_s{seed}")
    log, cen = os.path.join(d, "rotwedge.log"), os.path.join(d, "d135_census.txt")
    if not os.path.exists(log):
        return None
    txt = open(log, "rb").read().decode("utf-8", "replace")
    m = [l for l in txt.splitlines() if l.startswith("SUMMARY")]
    if not m:
        return None
    s = m[-1]

    def g(k, default=None):
        mm = re.search(rf"\b{k}=(-?\d+)", s)
        return int(mm.group(1)) if mm else default

    r = {"pills": g("pills"), "goes": g("goes"), "wedges": g("wedges"),
         "pressA": g("pressA"), "pressB": g("pressB"), "frames": g("frames", MAXF)}
    r["fpp"] = (r["frames"] / r["pills"]) if r["pills"] else None
    r["blocked"] = r["leaked"] = None
    if os.path.exists(cen):
        c = open(cen).read()
        b, l = re.search(r"blocked=(\d+)", c), re.search(r"leaked=(\d+)", c)
        r["blocked"] = int(b.group(1)) if b else None
        r["leaked"] = int(l.group(1)) if l else None
    return r


def main():
    rows, missing, invalid, wedged, pairs = [], [], [], [], []
    for s in SEEDS:
        off, on = cell("off", s), cell("on", s)
        if off is None or on is None:
            missing.append((s, off is None, on is None)); continue
        # 1. VALIDITY (v3-B) -- reported separately from wedge drops on purpose
        bad = [a for a, r in (("off", off), ("on", on))
               if r["leaked"] != 0 or (r["blocked"] or 0) < 1]
        if bad:
            invalid.append((s, bad)); continue
        # 2. INCLUSION (v2)
        if off["wedges"] != 0 or on["wedges"] != 0:
            wedged.append((s, off["wedges"], on["wedges"])); continue
        pairs.append((s, off, on))
        rows.append((s, off, on))

    print(f"PREREG_ROTDIR_V3 -- win orient {ORIENT}, {MAXF} frames, patched harness")
    print(f"{'seed':>6} {'OFF f/pill':>11} {'ON f/pill':>10} {'delta':>8} "
          f"{'OFF A/B':>10} {'ON A/B':>10} {'blk o/n':>9}")
    for s, off, on in rows:
        print(f"{s:>6} {off['fpp']:>11.2f} {on['fpp']:>10.2f} {on['fpp']-off['fpp']:>8.2f} "
              f"{str(off['pressA'])+'/'+str(off['pressB']):>10} "
              f"{str(on['pressA'])+'/'+str(on['pressB']):>10} "
              f"{str(off['blocked'])+'/'+str(on['blocked']):>9}")

    print()
    for s, o, n in missing:
        print(f"  MISSING seed {s}  (off_missing={o} on_missing={n})  -- absence is not a pass")
    for s, b in invalid:
        print(f"  INVALID seed {s}  arms={b}  -- guard unexercised or leaked; NOT a wedge drop")
    for s, wo, wn in wedged:
        print(f"  WEDGE-DROP seed {s}  off_wedges={wo} on_wedges={wn}")

    n = len(pairs)
    print(f"\nsurviving pairs: {n}/16   (missing {len(missing)}, invalid {len(invalid)}, "
          f"wedge-dropped {len(wedged)})")

    # 3. POWER BAR
    if n < 8:
        print("\nVERDICT: NO-VERDICT -- fewer than 8 surviving pairs (v2 power bar).")
        return 1

    # 4. P3 -- the mechanism
    p3 = []
    for s, off, on in pairs:
        ok = (off["pressB"] == 0 and off["pressA"] > 0
              and on["pressA"] == 0 and on["pressB"] > 0.5 * on["pills"])
        p3.append((s, ok))
    p3_all = all(ok for _, ok in p3)
    print(f"P3 (press census): {'PASS' if p3_all else 'FAIL'} "
          f"({sum(ok for _, ok in p3)}/{n} pairs)")
    for s, ok in p3:
        if not ok:
            print(f"    P3 fail on seed {s}")

    # 6. P1
    deltas = [on["fpp"] - off["fpp"] for _, off, on in pairs]
    mean = statistics.mean(deltas)
    sd = statistics.stdev(deltas) if n > 1 else 0.0
    se = sd / (n ** 0.5) if n > 1 else 0.0
    t = T95.get(n - 1, 1.96)
    lo, hi = mean - t * se, mean + t * se
    print(f"P1: mean delta {mean:+.3f} f/pill   sd {sd:.3f}   "
          f"paired 95% CI [{lo:+.3f}, {hi:+.3f}]  (t={t}, df={n-1})")
    p1_mag = mean <= -1.5
    p1_ci = hi < 0
    print(f"    <= -1.5 f/pill: {'PASS' if p1_mag else 'FAIL'}    "
          f"CI upper < 0: {'PASS' if p1_ci else 'FAIL'}")

    # 5. RULE 12 -- registered interpretation constraint, applied BEFORE calling P1 a flag effect
    print("\nrule-12 mechanism check (v3-C): DRROTDIR is a tempo-shifting flag, so an f/pill "
          "delta\n  is only read as a FLAG effect if the press signature holds on the same pairs.")
    if not p3_all:
        print("  => P3 did not hold on every pair: any P1 result is reported as a TEMPO/PHASE "
              "observation,\n     NOT as DRROTDIR working.")
    else:
        print("  => P3 holds on all surviving pairs: the effect arrives with its mechanism.")

    # verdict routing (v2, unchanged)
    print("\n--- VERDICT ROUTING (PREREG_ROTDIR_V2, inherited) ---")
    if not p3_all:
        print("VERDICT: NO-GO -- P3 failed; the flag is not doing what it claims.")
        return 0
    if not p1_ci:
        print("VERDICT: NULL/UNDER-POWERED -- P1's CI includes 0. Report the interval, do not "
              "ship.")
        return 0
    if not p1_mag:
        print("VERDICT: CI excludes 0 but the point estimate misses the registered -1.5 f/pill "
              "bar.\n         Reported as a measured effect BELOW the registered threshold; "
              "not a GO.")
        return 0
    print("VERDICT: P1 and P3 PASS with >=8 pairs. GO *conditional on the mutant sheet* -- "
          "unscored\n         mutants count as SURVIVING and void the verdict (v2). Mutants are "
          "scored separately.")
    print("\n⚠ OVERLAP LABEL (v3-E): this f/pill figure is measured on a DRDBLCANON core and is "
          "NOT\n  additive with #123's 0.96 s/game.")
    print("⚠ v3-F: this is a MEASUREMENT, not an un-park. #114's park bar is the owner's call.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
