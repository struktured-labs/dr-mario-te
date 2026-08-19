#!/usr/bin/env python3
"""PREREG_ROTDIR verdict. Reads tmp/rotwedge/rw_<arm>_o<orient>_12000_s<seed>/ and decides
P1/P2/P3 exactly as registered, then applies the mutant table.

Written to be run on the MUTANT arms too: the same predicates that pass on the real fix must
FAIL on each mutant, which is the only thing that shows they discriminate.  A self-test
(--selftest) drives the predicates with synthetic tables straddling every threshold, because
a verdict script that has only ever seen one real table has not been shown to discriminate
either (gate standard, "extend it to the ANALYSIS code").
"""
import csv, os, re, sys, statistics

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
RUNS = os.path.normpath(os.path.join(ROOT, "tmp", "rotwedge"))

# copro orient -> (game orient, CCW presses under the OFF cart, delta under the ON cart)
LADDER = {0: (3, 1, 3), 1: (1, 3, 1), 2: (0, 0, 0), 3: (2, 2, 2)}
WIN_ORIENT = 1            # the only delta-1 cell
TOL = 0.6                 # f/pill, registered
WIN_MIN, WIN_MAX = 78.3, 79.5   # registered 78.9 +- 0.6


def cell(arm, orient, seed, maxf=12000):
    d = os.path.join(RUNS, f"rw_{arm}_o{orient}_{maxf}_s{seed}")
    log = os.path.join(d, "rotwedge.log")
    csvp = os.path.join(d, "frames.csv")
    if not os.path.isfile(log) or not os.path.isfile(csvp):
        return None                       # ABSENCE IS NOT PASS -- caller must count it
    txt = open(log, errors="replace").read()
    m = re.search(r"^SUMMARY .*$", txt, re.M)
    if not m:
        return None
    s = dict(re.findall(r"(\w+)=(-?\d+)", m.group(0)))
    rows = [r for r in csv.DictReader(open(csvp)) if r.get("p2y")]
    pills, prev = 0, None
    for r in rows:
        y = int(r["p2y"])
        if prev is not None and y > prev:
            pills += 1
        prev = y
    return {"pills": pills, "mode4f": len(rows),
            "fpp": len(rows) / pills if pills else float("nan"),
            "wedges": int(s.get("wedges", 0)),
            "pressA": int(s.get("pressA", 0)), "pressB": int(s.get("pressB", 0))}


def collect(arms, seeds, orients):
    tbl, missing = {}, []
    for a in arms:
        for o in orients:
            for sd in seeds:
                c = cell(a, o, sd)
                if c is None:
                    missing.append((a, o, sd))
                else:
                    tbl[(a, o, sd)] = c
    return tbl, missing


def verdict(tbl, seeds, orients, arm_on, label):
    """Apply P1/P2/P3. Returns (ok, lines)."""
    out, ok = [], True
    dropped = []
    for o in orients:
        for sd in seeds:
            off, on = tbl.get(("off", o, sd)), tbl.get((arm_on, o, sd))
            if off and off["wedges"] > 0:
                dropped.append((o, sd, "off wedged"))
            elif on and on["wedges"] > 0:
                dropped.append((o, sd, f"{arm_on} wedged"))
    drop = {(o, sd) for o, sd, _ in dropped}
    for o, sd, why in dropped:
        out.append(f"  DROPPED cell orient={o} seed={sd}: {why} (registered rule)")
    if len(drop) > 2:
        return False, out + [f"  NO-VERDICT: {len(drop)} cells dropped, registered cap is 2"]

    for o in orients:
        offs = [tbl[("off", o, sd)]["fpp"] for sd in seeds if (o, sd) not in drop and ("off", o, sd) in tbl]
        ons = [tbl[(arm_on, o, sd)]["fpp"] for sd in seeds if (o, sd) not in drop and (arm_on, o, sd) in tbl]
        if not offs or not ons:
            out.append(f"  orient {o}: MISSING data -> FAIL (absence is not pass)")
            ok = False
            continue
        mo, mn = statistics.mean(offs), statistics.mean(ons)
        d = mn - mo
        game_o, ccw, delta = LADDER[o]
        tag = "WIN" if o == WIN_ORIENT else "control"
        if o == WIN_ORIENT:
            good = WIN_MIN <= mn <= WIN_MAX
            out.append(f"  P1 orient {o} (game {game_o}, delta {delta}) {tag}: "
                       f"off {mo:.2f} -> on {mn:.2f} (d {d:+.2f})  registered on in "
                       f"[{WIN_MIN},{WIN_MAX}] -> {'PASS' if good else 'FAIL'}")
        else:
            good = abs(d) <= TOL
            out.append(f"  P2 orient {o} (game {game_o}, delta {delta}) {tag}: "
                       f"off {mo:.2f} -> on {mn:.2f} (d {d:+.2f})  |d| <= {TOL} -> "
                       f"{'PASS' if good else 'FAIL'}")
        ok = ok and good

    # P3 not-inert / inert-when-off
    for o in orients:
        for sd in seeds:
            if (o, sd) in drop:
                continue
            off, on = tbl.get(("off", o, sd)), tbl.get((arm_on, o, sd))
            if off and off["pressB"] != 0:
                out.append(f"  P3 FAIL: OFF cart pressed B (orient {o} seed {sd}, n={off['pressB']})")
                ok = False
            if on and o == WIN_ORIENT and on["pressB"] <= 0.5 * on["pills"]:
                out.append(f"  P3 FAIL: {arm_on} orient {o} seed {sd} pressB={on['pressB']} "
                           f"<= 0.5*pills={0.5 * on['pills']:.0f} (branch not exercised)")
                ok = False
            if on and o != WIN_ORIENT and on["pressB"] != 0:
                out.append(f"  P3 FAIL: {arm_on} pressed B on a delta!=1 orient "
                           f"({o}, seed {sd}, n={on['pressB']})")
                ok = False
    out.append(f"  => {label}: {'PASS' if ok else 'FAIL'}")
    return ok, out


def selftest():
    """Drive the predicates with synthetic cells straddling every registered threshold."""
    def mk(fpp, pressB=0, pills=100, wedges=0, pressA=100):
        return {"pills": pills, "mode4f": int(fpp * pills), "fpp": fpp,
                "wedges": wedges, "pressA": pressA, "pressB": pressB}
    seeds, orients = [1], [0, 1, 2, 3]
    base_off = {(("off"), o, 1): mk({0: 78.99, 1: 81.07, 2: 77.79, 3: 80.48}[o]) for o in orients}
    fails = 0

    def run(name, on_cells, expect):
        nonlocal fails
        tbl = dict(base_off)
        tbl.update(on_cells)
        got, _ = verdict(tbl, seeds, orients, "on", name)
        mark = "ok" if got == expect else "SELFTEST FAILURE"
        if got != expect:
            fails += 1
        print(f"  selftest {name:<34} got={got} expect={expect}  {mark}")

    good = {("on", 0, 1): mk(78.99), ("on", 1, 1): mk(78.9, pressB=100, pressA=0),
            ("on", 2, 1): mk(77.79), ("on", 3, 1): mk(80.48)}
    run("the registered PASS shape", good, True)

    bad = dict(good); bad[("on", 1, 1)] = mk(81.07, pressB=100, pressA=0)
    run("win arm did not move -> P1 fail", bad, False)

    bad = dict(good); bad[("on", 0, 1)] = mk(77.0)
    run("a control moved -1.99 -> P2 fail", bad, False)

    bad = dict(good); bad[("on", 0, 1)] = mk(79.5)
    run("a control moved +0.51 (inside tol)", bad, True)

    bad = dict(good); bad[("on", 1, 1)] = mk(78.9, pressB=0, pressA=100)
    run("win arm fast but B never pressed", bad, False)

    bad = dict(good); bad[("on", 3, 1)] = mk(80.48, pressB=40)
    run("B pressed on a delta!=1 orient", bad, False)

    tbl = dict(base_off); tbl.update(good)
    tbl[("off", 1, 1)] = mk(81.07, wedges=1)
    got, lines = verdict(tbl, seeds, orients, "on", "one wedged cell")
    print(f"  selftest {'wedged cell is DROPPED, not scored':<34} got={got} expect=False  "
          f"{'ok' if got is False else 'SELFTEST FAILURE'}")
    if got is not False:
        fails += 1
    print(f"\nselftest: {'ALL PASS' if fails == 0 else f'{fails} FAILURES'}")
    return 0 if fails == 0 else 1


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    seeds = [271, 2001, 3001]
    print("=== PREREG_ROTDIR verdict ===\n")
    tbl, missing = collect(["off", "on"], seeds, [0, 1, 2, 3])
    if missing:
        print("MISSING CELLS (absence is not pass):")
        for m in missing:
            print("   ", m)
        sys.exit(2)
    print("raw f/pill (pills, pressA/pressB, wedges):")
    for o in [2, 0, 3, 1]:
        for a in ["off", "on"]:
            cs = [tbl[(a, o, sd)] for sd in seeds]
            print(f"  o{o} game{LADDER[o][0]} delta{LADDER[o][2]} {a:<3}: " +
                  "  ".join(f"{c['fpp']:6.2f}({c['pills']:3d},{c['pressA']}/{c['pressB']},w{c['wedges']})"
                            for c in cs))
    print()
    ok, lines = verdict(tbl, seeds, [0, 1, 2, 3], "on", "REAL FIX")
    print("\n".join(lines))

    print("\n=== mutant kill sheet (must all FAIL) ===")
    survivors = []
    for m in ["m1", "m2", "m3", "m4"]:
        mt, mm = collect(["off", m], seeds, [0, 1])
        if mm:
            print(f"  {m}: MISSING cells {mm} -> cannot score (counts as SURVIVING)")
            survivors.append(m)
            continue
        mok, mlines = verdict(mt, seeds, [0, 1], m, m)
        print(f"  --- {m}")
        print("\n".join("  " + l for l in mlines))
        if mok:
            survivors.append(m)
    print()
    if survivors:
        print(f"MUTANTS SURVIVED: {survivors} -- the cases are vacuous, do not read the numbers")
    else:
        print("all 4 mutants killed")
    sys.exit(0 if (ok and not survivors) else 1)


if __name__ == "__main__":
    main()
