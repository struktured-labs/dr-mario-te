#!/usr/bin/env python3
"""PREREG_ROTDIR_V2 verdict: the WIN orient (copro 1) only, 16 seeds, paired.

Separate from verdict_rotdir.py on purpose -- v1's script stays exactly as registered so its
NO-VERDICT is auditable. This one implements v2's rules and nothing else:
  inclusion  both arms wedges == 0
  power      >= 8 of 16 surviving pairs, else NO-VERDICT
  P1         mean(ON - OFF) <= -1.5 f/pill AND the paired 95% t CI upper bound < 0
  P3         OFF pressB == 0 and pressA > 0; ON pressB > 0.5*pills and pressA == 0
Mutant carts are re-scored by the same predicates on the same surviving seeds.

--selftest drives the predicates with synthetic pairs straddling each threshold.
"""
import math, os, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verdict_rotdir import cell                     # same reader, same absence-is-not-pass

SEEDS = [4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008,
         4009, 4010, 4011, 4012, 4013, 4014, 4015, 4016]
ORIENT = 1                # copro 1 = game 1 = delta 1 = the only cell the flag changes
MIN_PAIRS = 8
P1_BAR = -1.5
# t_{0.975, df} for df = 7..15; v2 cannot be scored below df=7 (8 pairs)
TCRIT = {7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
         13: 2.160, 14: 2.145, 15: 2.131}


def paired_ci(diffs):
    n = len(diffs)
    m = statistics.mean(diffs)
    if n < 2:
        return m, float("-inf"), float("inf")
    sd = statistics.stdev(diffs)
    t = TCRIT.get(n - 1, 2.131)
    h = t * sd / math.sqrt(n)
    return m, m - h, m + h


def score(arm, pairs_getter, label):
    """pairs_getter(seed) -> (off_cell, on_cell) or None if a cell is missing."""
    lines, diffs, dropped, missing = [], [], [], []
    p3_fail = []
    for sd in SEEDS:
        got = pairs_getter(sd)
        if got is None:
            missing.append(sd)
            continue
        off, on = got
        if off["wedges"] or on["wedges"]:
            dropped.append((sd, f"off w{off['wedges']} on w{on['wedges']}"))
            continue
        diffs.append(on["fpp"] - off["fpp"])
        if off["pressB"] != 0 or off["pressA"] <= 0:
            p3_fail.append(f"seed {sd} OFF pressA={off['pressA']} pressB={off['pressB']}")
        if on["pressA"] != 0 or on["pressB"] <= 0.5 * on["pills"]:
            p3_fail.append(f"seed {sd} {arm} pressA={on['pressA']} pressB={on['pressB']} "
                           f"pills={on['pills']}")
    if missing:
        lines.append(f"  MISSING cells for seeds {missing} -- absence is not pass")
        return False, lines
    lines.append(f"  dropped {len(dropped)}/{len(SEEDS)} pairs (a wedge in either arm): "
                 + (", ".join(f"{s}({w})" for s, w in dropped) or "none"))
    if len(diffs) < MIN_PAIRS:
        lines.append(f"  NO-VERDICT: {len(diffs)} surviving pairs < registered bar {MIN_PAIRS}")
        return False, lines
    m, lo, hi = paired_ci(diffs)
    p1 = (m <= P1_BAR) and (hi < 0)
    lines.append(f"  n={len(diffs)} pairs   mean(ON-OFF) = {m:+.3f} f/pill   "
                 f"95% CI [{lo:+.3f}, {hi:+.3f}]")
    lines.append(f"  P1 (mean <= {P1_BAR} and CI upper < 0): {'PASS' if p1 else 'FAIL'}")
    if p3_fail:
        for f in p3_fail[:6]:
            lines.append(f"  P3 FAIL: {f}")
    lines.append(f"  P3: {'PASS' if not p3_fail else 'FAIL'}")
    ok = p1 and not p3_fail
    lines.append(f"  => {label}: {'PASS' if ok else 'FAIL'}")
    return ok, lines


def selftest():
    def mk(fpp, pressA, pressB, pills=110, wedges=0):
        return {"pills": pills, "mode4f": int(fpp * pills), "fpp": fpp,
                "wedges": wedges, "pressA": pressA, "pressB": pressB}
    fails = 0

    def run(name, mkpair, expect):
        nonlocal fails
        ok, _ = score("on", mkpair, name)
        mark = "ok" if ok == expect else "SELFTEST FAILURE"
        if ok != expect:
            fails += 1
        print(f"  selftest {name:<40} got={ok} expect={expect}  {mark}")

    run("clean -2.2 win, all 16 pairs",
        lambda s: (mk(81.0, 390, 0), mk(78.8, 0, 110)), True)
    run("win only -1.0 (above the -1.5 bar)",
        lambda s: (mk(81.0, 390, 0), mk(80.0, 0, 110)), False)
    # noisy: alternate +/- so the CI straddles 0 while the mean clears the bar
    run("mean clears bar but CI straddles 0",
        lambda s: (mk(81.0, 390, 0), mk(81.0 - 1.6 + (12.0 if s % 2 else -12.0), 0, 110)), False)
    run("win present but ON never pressed B",
        lambda s: (mk(81.0, 390, 0), mk(78.8, 110, 0)), False)
    run("OFF cart pressed B (flag leaked)",
        lambda s: (mk(81.0, 390, 4), mk(78.8, 0, 110)), False)
    run("9 of 16 pairs survive (above the bar)",
        lambda s: (mk(81.0, 390, 0, wedges=1 if s >= 4010 else 0), mk(78.8, 0, 110)), True)
    run("7 of 16 pairs survive (below the bar)",
        lambda s: (mk(81.0, 390, 0, wedges=1 if s >= 4008 else 0), mk(78.8, 0, 110)), False)
    run("a missing cell is a FAILURE not a skip",
        lambda s: None if s == 4005 else (mk(81.0, 390, 0), mk(78.8, 0, 110)), False)
    print(f"\nselftest: {'ALL PASS' if fails == 0 else f'{fails} FAILURES'}")
    return 0 if fails == 0 else 1


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print("=== PREREG_ROTDIR_V2 verdict (win orient, copro 1) ===\n")

    def getter(arm):
        def g(sd):
            off, on = cell("off", ORIENT, sd), cell(arm, ORIENT, sd)
            return None if (off is None or on is None) else (off, on)
        return g

    print("per-seed (off -> on):")
    for sd in SEEDS:
        off, on = cell("off", ORIENT, sd), cell("on", ORIENT, sd)
        if off is None or on is None:
            print(f"  {sd}: MISSING off={off is not None} on={on is not None}")
            continue
        print(f"  {sd}: {off['fpp']:7.2f}(p{off['pills']:3d} A{off['pressA']:4d}/B{off['pressB']:3d} "
              f"w{off['wedges']})  ->  {on['fpp']:7.2f}(p{on['pills']:3d} A{on['pressA']:4d}/"
              f"B{on['pressB']:3d} w{on['wedges']})   d={on['fpp'] - off['fpp']:+7.2f}")
    print()
    ok, lines = score("on", getter("on"), "REAL FIX")
    print("\n".join(lines))

    # EXPLORATORY, registered as not-claimable
    offw = sum(1 for sd in SEEDS if (c := cell("off", ORIENT, sd)) and c["wedges"])
    onw = sum(1 for sd in SEEDS if (c := cell("on", ORIENT, sd)) and c["wedges"])
    print(f"\n  EXPLORATORY (not a claim, see prereg): #131 wedges  OFF {offw}/16   ON {onw}/16")

    # ---- mutant kill sheet ------------------------------------------------------------
    # A mutant is KILLED if it fails EITHER half. m2b exists specifically because it passes
    # the win half and can only be caught by the control half -- scoring mutants on the win
    # arm alone would let exactly that mutation through.
    MSEEDS = [271, 2001, 3001, 4001, 4002, 4003]      # OFF cells exist for all of these
    CSEEDS = [271, 2001, 3001]                        # OFF orient-0 cells exist for these

    def win_half(arm):
        diffs = []
        for sd in MSEEDS:
            off, on = cell("off", ORIENT, sd), cell(arm, ORIENT, sd)
            if off is None or on is None:
                return None, f"missing win cell seed {sd}"
            if off["wedges"] or on["wedges"]:
                continue
            diffs.append(on["fpp"] - off["fpp"])
        if len(diffs) < 3:
            return None, f"only {len(diffs)} clean win pairs"
        m = statistics.mean(diffs)
        return (m <= P1_BAR), f"win arm mean {m:+.2f} f/pill over {len(diffs)} pairs"

    def control_half(arm):
        diffs = []
        for sd in CSEEDS:
            off, on = cell("off", 0, sd), cell(arm, 0, sd)
            if off is None or on is None:
                return None, f"missing control cell seed {sd}"
            if off["wedges"] or on["wedges"]:
                continue
            diffs.append(on["fpp"] - off["fpp"])
        if not diffs:
            return None, "no clean control pairs"
        m = statistics.mean(diffs)
        return (abs(m) <= 0.6), f"control (delta-3) arm mean {m:+.2f} f/pill over {len(diffs)} pairs"

    print("\n=== mutant kill sheet (each must FAIL at least one half) ===")
    survivors, unscored = [], []
    for m in ["m1", "m2b", "m3b", "m4"]:
        w, wmsg = win_half(m)
        c, cmsg = control_half(m)
        print(f"  --- {m}")
        print(f"      win half     : {wmsg}   -> {'pass' if w else ('FAIL' if w is False else 'UNSCORED')}")
        print(f"      control half : {cmsg}   -> {'pass' if c else ('FAIL' if c is False else 'UNSCORED')}")
        if w is None or c is None:
            unscored.append(m)
            print(f"      => {m}: UNSCORED (counts as SURVIVING -- absence is not a kill)")
            survivors.append(m)
        elif w and c:
            print(f"      => {m}: SURVIVED (indistinguishable from the fix on both halves)")
            survivors.append(m)
        else:
            print(f"      => {m}: KILLED")
    print()
    if survivors:
        print(f"MUTANTS SURVIVED: {survivors}"
              + (f" (unscored: {unscored})" if unscored else ""))
    else:
        print("all 4 mutants killed")
    sys.exit(0 if (ok and not survivors) else 1)


if __name__ == "__main__":
    main()
