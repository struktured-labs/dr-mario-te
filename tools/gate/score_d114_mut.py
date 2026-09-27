#!/usr/bin/env python3
"""score_d114_mut.py -- the #114 mutant kill sheet, per PREREG_ROTDIR_V2 + v3 addendum G.

A mutant is KILLED if it FAILS at least one registered predicate on the cells it was scored
on. It SURVIVES if it passes them all -- and per v2 a surviving mutant VOIDS the verdict.
UNSCORED counts as SURVIVING: absence is not a kill. That rule is why v2 returned NO-VERDICT,
so it is enforced here rather than left to prose.

The two halves, and why the control half exists (v2's own words): m2b is chosen precisely to
"sail through a win-only gate" -- it presses B unconditionally, which wins the delta-1 case and
must break the delta-3 control, where the correct behaviour is 3 presses and it emits 1. A gate
that only ran the win half would hand m2b a pass.

  win half     (orient 1, delta 1): P3 shape -- ON-like carts must press B, not A
  control half (orient 0, delta 3): the mutant must NOT reproduce the OFF arm's f/pill

Predicates applied per mutant cell:
  K1  validity: leaked==0 and blocked>=1, else the cell is INVALID (v3-B) and cannot kill
  K2  wedges==0, else the cell is dropped (v2 inclusion) and cannot kill
  K3  P3 press signature for the arm's intent
  K4  f/pill vs the same-seed OFF baseline from the main sheet

Exit 0 = every mutant killed. Exit 1 = at least one survivor or unscored (verdict VOID).
"""
from __future__ import annotations

import os
import re
import sys

D = "/home/struktured/projects/dr-mario-hygiene-wt/tmp/d114"
MUTANTS = ["m1", "m2b", "m3b", "m4"]
MAXF = 12000


def cell(arm, orient, seed):
    d = os.path.join(D, f"d114_{arm}_o{orient}_{MAXF}_s{seed}")
    log, cen = os.path.join(d, "rotwedge.log"), os.path.join(d, "d135_census.txt")
    if not os.path.exists(log):
        return None
    txt = open(log, "rb").read().decode("utf-8", "replace")
    m = [l for l in txt.splitlines() if l.startswith("SUMMARY")]
    if not m:
        return None
    s = m[-1]

    def g(k, dflt=None):
        mm = re.search(rf"\b{k}=(-?\d+)", s)
        return int(mm.group(1)) if mm else dflt

    r = {"pills": g("pills"), "wedges": g("wedges"), "pressA": g("pressA"),
         "pressB": g("pressB"), "frames": g("frames", MAXF)}
    r["fpp"] = (r["frames"] / r["pills"]) if r["pills"] else None
    r["blocked"] = r["leaked"] = None
    if os.path.exists(cen):
        c = open(cen).read()
        b, l = re.search(r"blocked=(\d+)", c), re.search(r"leaked=(\d+)", c)
        r["blocked"] = int(b.group(1)) if b else None
        r["leaked"] = int(l.group(1)) if l else None
    return r


def surviving_seeds():
    out = []
    for s in range(4001, 4017):
        ok = True
        for arm in ("off", "on"):
            r = cell(arm, 1, s)
            if (r is None or r["wedges"] != 0 or r["leaked"] != 0
                    or (r["blocked"] or 0) < 1):
                ok = False
                break
        if ok:
            out.append(s)
    return out


def main():
    seeds = surviving_seeds()[:3]     # addendum G, registered
    print(f"mutant seed set (first 3 surviving, ascending): {seeds}")
    if not seeds:
        print("no surviving seeds -- mutants UNSCORED => all SURVIVING => VERDICT VOID")
        return 1

    rc = 0
    for m in MUTANTS:
        print(f"\n--- {m}")
        reasons, scored = [], 0
        for orient, half in ((1, "win"), (0, "control")):
            for s in seeds:
                r = cell(m, orient, s)
                base = cell("off", orient, s) if orient == 1 else None
                if r is None:
                    print(f"    {half:>7} s{s}: MISSING -- cannot kill")
                    continue
                if r["leaked"] != 0 or (r["blocked"] or 0) < 1:
                    print(f"    {half:>7} s{s}: INVALID (leaked={r['leaked']} "
                          f"blocked={r['blocked']}) -- cannot kill")
                    continue
                if r["wedges"] != 0:
                    print(f"    {half:>7} s{s}: wedged ({r['wedges']}) -- dropped, cannot kill")
                    continue
                scored += 1
                bits = []
                # K3: press signature. A working DRROTDIR-on cart presses B, never A.
                if r["pressA"] > 0 and r["pressB"] == 0:
                    bits.append("P3 fail: presses A not B")
                if r["pills"] and r["pressB"] <= 0.5 * r["pills"] and r["pressB"] > 0:
                    bits.append(f"P3 fail: pressB {r['pressB']} <= 0.5*pills")
                if r["pressB"] == 0 and r["pressA"] == 0:
                    bits.append("P3 fail: no rotation presses at all")
                # K4: tempo vs the matched OFF baseline (win half only, where a baseline exists)
                if base and base["fpp"] and r["fpp"]:
                    d = r["fpp"] - base["fpp"]
                    if d > -1.5:
                        bits.append(f"P1 fail: delta {d:+.2f} f/pill vs OFF (needs <= -1.5)")
                print(f"    {half:>7} s{s}: pills={r['pills']} A/B={r['pressA']}/{r['pressB']} "
                      f"f/pill={r['fpp']:.2f}" + ("  => " + "; ".join(bits) if bits else "  (passes)"))
                reasons += bits
        if scored == 0:
            print(f"  => {m}: UNSCORED -- counts as SURVIVING (absence is not a kill). VOID.")
            rc = 1
        elif reasons:
            print(f"  => {m}: KILLED ({len(reasons)} failing predicate(s) over {scored} cells)")
        else:
            print(f"  => {m}: SURVIVED all {scored} scored cells -- VERDICT VOID (v2). "
                  f"Registered response: widen to the full surviving set, do NOT call it killed.")
            rc = 1

    print("\nall mutants killed" if rc == 0 else "\nMUTANT SHEET NOT CLEAN -- verdict is VOID")
    return rc


if __name__ == "__main__":
    sys.exit(main())
