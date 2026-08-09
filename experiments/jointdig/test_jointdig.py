#!/usr/bin/env python3
"""Killed-mutant gate for the joint-dig detector (task #96).

Hand-built fixtures with a KNOWN answer, then four mutated detectors each of which must
FAIL at least one fixture. Per the house standard a check that cannot fail on wrong input
is not evidence -- and per the same standard, each mutant is checked for non-equivalence
(it must actually change the computed numbers, not just the source).

FIXTURES
  POS   column 7 is a buried-virus danger column (junk over a colour-1 virus at the floor).
        Row 15 reads  . . . . _ _ 1 V1  -- a 2-run. cur=(2,1) placed vertical at col 5 puts
        a 1 at (15,5) making a 3-run and clearing NOTHING; nxt=(2,1) vertical at col 4 puts
        a 1 at (15,4), completing 4 and clearing the virus out of column 7.
        => a JOINT virus-dig exists and NO single-pill virus-dig does.
  NEG   same geometry but the danger virus is colour 3 while cur/nxt are colours 1,2 only.
        No line of any length can clear it => zero digs of either kind.
  SINGLE one placement of cur alone clears the virus out of column 7, while nxt is a colour
        that CANNOT clear it (matches are same-colour), so the true joint count is provably
        0. This is the fixture that makes the "conflate single into joint" mutant
        non-equivalent -- without it that mutant changes nothing, because every other
        fixture has single_vdig == 0. (Found by this gate failing on its own first run.)

`_added_in` is gated as a UNIT, with hand-computed values, rather than end-to-end. It only
feeds the SECONDARY occupancy signal, and an end-to-end fixture that separates it from the
exact virus signal turned out to need a contrived board; a direct unit check is both
stronger and honest about what it covers. The first version of this file asserted
`single_odig + joint_odig >= 0` end-to-end, which is vacuously true -- a check that cannot
fail is not a check, and this gate caught it.
"""
from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, "/home/struktured/projects/dr-mario-prestart-wt/experiments/jointdig")
import jointdig as J  # noqa: E402

COLS, ROWS = J.COLS, J.ROWS


def blank():
    return (np.zeros(J.NCELL, np.int8), np.zeros(J.NCELL, np.int8), np.zeros(J.NCELL, np.int8))


def put(col, vir, r, c, colour, is_virus=False):
    col[r * COLS + c] = colour
    vir[r * COLS + c] = 1 if is_virus else 0


def fixture_pos(danger_colour=1):
    col, vir, lnk = blank()
    put(col, vir, 15, 7, danger_colour, is_virus=True)   # the buried virus
    put(col, vir, 14, 7, 2)                              # junk on top of it
    put(col, vir, 13, 7, 2)
    put(col, vir, 15, 6, 1)                              # neighbour, makes row15 a 2-run
    return col, vir, lnk


def fixture_single():
    """Row 15 reads . . . . . 1 1 V1 -- a 3-run. cur=(1,1) laid flat at cols 3-4 completes
    it in ONE placement. nxt is colour 2, which can never clear a colour-1 virus, so the
    true joint count here is 0 by the rules of the game, not by measurement."""
    col, vir, lnk = blank()
    put(col, vir, 15, 7, 1, is_virus=True)
    put(col, vir, 14, 7, 2)
    put(col, vir, 13, 7, 2)
    put(col, vir, 15, 6, 1)
    put(col, vir, 15, 5, 1)
    return col, vir, lnk


def run_fixtures(scan_fn, label):
    """Returns the fixture facts under whichever scan implementation is passed in."""
    out = {}
    col, vir, lnk = fixture_pos(1)
    out["pos"] = scan_fn(col, vir, lnk, (2, 1), (2, 1), 7)
    col, vir, lnk = fixture_pos(3)                       # virus colour 3, pills are 1/2
    out["neg"] = scan_fn(col, vir, lnk, (2, 1), (2, 1), 7)
    col, vir, lnk = fixture_single()
    out["single"] = scan_fn(col, vir, lnk, (1, 1), (2, 2), 7)
    return out


def assertions(f):
    """The fixture contract. Returns list of (name, ok)."""
    return [
        ("POS: a joint virus-dig exists", f["pos"]["joint_vdig"] > 0),
        ("POS: no single-pill virus-dig", f["pos"]["single_vdig"] == 0),
        ("POS: therefore joint_v_only", f["pos"]["joint_v_only"] is True),
        ("NEG: no single virus-dig", f["neg"]["single_vdig"] == 0),
        ("NEG: no joint virus-dig", f["neg"]["joint_vdig"] == 0),
        ("NEG: vdig unavailable", f["neg"]["vdig_avail"] is False),
        ("SINGLE: a one-pill virus-dig exists", f["single"]["single_vdig"] > 0),
        ("SINGLE: true joint count is 0 (nxt cannot clear colour 1)",
         f["single"]["joint_vdig"] == 0),
        ("SINGLE: not joint_v_only", f["single"]["joint_v_only"] is False),
    ]


def unit_added_in():
    """`_added_in` gated directly, hand-computed. variant<2 = horizontal (cells c, c+1);
    variant>=2 = vertical (both at c)."""
    return [
        ("_added_in H at c=3, d=3 -> 1", J._added_in(0, 3, 3) == 1),
        ("_added_in H at c=3, d=4 -> 1", J._added_in(0, 3, 4) == 1),
        ("_added_in H at c=3, d=5 -> 0", J._added_in(0, 3, 5) == 0),
        ("_added_in V at c=3, d=3 -> 2", J._added_in(2, 3, 3) == 2),
        ("_added_in V at c=3, d=4 -> 0", J._added_in(2, 3, 4) == 0),
    ]


def main():
    J.warmup()
    S = J.Scanner()
    base = run_fixtures(S.scan, "base")
    print("=" * 78)
    print("FIXTURES (true detector)")
    print("=" * 78)
    for k, v in base.items():
        print("  %-4s single_vdig=%-3d joint_vdig=%-3d single_odig=%-3d joint_odig=%-3d"
              % (k, v["single_vdig"], v["joint_vdig"], v["single_odig"], v["joint_odig"]))
        if v["witness_v"]:
            print("        witness_v: %s" % (v["witness_v"],))
    fails = []
    print()
    print("  -- unit: _added_in --")
    for name, ok in unit_added_in():
        print("  %-42s %s" % (name, "OK" if ok else "*** FAIL"))
        if not ok:
            fails.append(name)
    saved = J._added_in
    J._added_in = lambda v, c, dd: 0
    m4_broken = [n for n, ok in unit_added_in() if not ok]
    J._added_in = saved
    print("  %-42s %s" % ("M4 mutant (_added_in -> 0)",
                          "KILLED" if m4_broken else "*** SURVIVED"))
    if not m4_broken:
        fails.append("mutant survived: M4 _added_in -> 0")
    print()
    for name, ok in assertions(base):
        print("  %-42s %s" % (name, "OK" if ok else "*** FAIL"))
        if not ok:
            fails.append(name)

    print()
    print("=" * 78)
    print("KILLED MUTANTS -- each must break at least one fixture assertion")
    print("=" * 78)

    def mutant_flag_nonclearing(col, vir, lnk, cur, nxt, d):
        """M1: counts a pair as a dig whenever it is LEGAL, not when it clears."""
        r = S.scan(col, vir, lnk, cur, nxt, d)
        legal_pairs = 0
        for v1, c1 in S.legal(col, vir, lnk, cur[0], cur[1]):
            ok, _, _, _ = S.place(col, vir, lnk, v1, c1, cur[0], cur[1], S.b1)
            legal_pairs += len(S.legal(S.b1[0], S.b1[1], S.b1[2], nxt[0], nxt[1]))
        r = dict(r); r["joint_vdig"] = legal_pairs
        r["vdig_avail"] = (r["single_vdig"] > 0 or r["joint_vdig"] > 0)
        r["joint_v_only"] = (r["joint_vdig"] > 0 and r["single_vdig"] == 0)
        return r

    def mutant_conflate(col, vir, lnk, cur, nxt, d):
        """M2: drops the 'first half must pay nothing' guard, so singles leak into joints."""
        r = dict(S.scan(col, vir, lnk, cur, nxt, d))
        r["joint_vdig"] = r["joint_vdig"] + r["single_vdig"]
        r["joint_v_only"] = (r["joint_vdig"] > 0 and r["single_vdig"] == 0)
        return r

    def mutant_wrong_column(col, vir, lnk, cur, nxt, d):
        """M3: scans the column next door."""
        return S.scan(col, vir, lnk, cur, nxt, (d + 1) % COLS)

    for mname, fn in (("M1 flags non-clearing pairs", mutant_flag_nonclearing),
                      ("M2 conflates single into joint", mutant_conflate),
                      ("M3 scans the wrong column", mutant_wrong_column),
                      ):
        mf = run_fixtures(fn, mname)
        broken = [n for n, ok in assertions(mf) if not ok]
        changed = any(mf[k][f] != base[k][f] for k in base
                      for f in ("single_vdig", "joint_vdig", "single_odig", "joint_odig"))
        status = "KILLED" if broken else "*** SURVIVED"
        print("  %-34s %-12s  non-equivalent=%s" % (mname, status, changed))
        if broken:
            print("        breaks: %s" % "; ".join(broken[:3]))
        else:
            fails.append("mutant survived: " + mname)
        if not changed:
            fails.append("mutant is EQUIVALENT (changed nothing): " + mname)

    print()
    print("RESULT:", "PASS" if not fails else "FAIL -> %s" % fails)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
