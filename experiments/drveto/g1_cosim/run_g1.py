#!/usr/bin/env python3
"""G1 evaluator: applies the assertion matrix over the four vsim runs.

  fixa_delta  (a2b2e4ac, the ship candidate, USE_DELTA=True)   -- must PASS all
  fixa_base   (b85e8945, USE_DELTA=False)                      -- must PASS all
  m2_delta    (0b2f9998, veto flag at o_cand, USE_DELTA=True)  -- must be KILLED
  veto1       (47edb895, tonight's shipped pre-Fix-A delta)    -- delta-path audit:
              finals/invariants PASS, but the ANYTIME trajectory must show the
              vetoed pub on PC4cap0 (the RTL-level positive control for the hole)

Checks per case (from sim_g1_veto.cpp observations + g1_reference.json):
  A  b4-executes      b4zero > 0 and == py65 reference count (same shortlist)
  B  cmd4-fresh       cmd4viol == 0 (C1: reads sit on the candidate's own CMD-4)
  C  delta==base      fixa_delta final == fixa_base final (the binding equality)
  D  no-vetoed-pub    no search-phase pub with the veto flag set while unvetoed
                      candidates exist (vsim variant of G2/T1)
  E  py65 cross-check final vs the py65 full-stub reference -- REPORTED only
                      (RTL chain leaf may legitimately diverge on dense boards)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF = json.load(open(os.path.join(HERE, "g1_reference.json")))


def parse(run):
    out = {}
    for line in open(os.path.join(HERE, f"run_{run}", "out.txt")):
        m = re.match(r"CASE (\S+) final=(-?\d+),(-?\d+) done=(\d+) b4zero=(\d+) "
                     r"b4one=(\d+) cmd4viol=(\d+) pubs=(\S+) clocks=(\d+) "
                     r"timeout=(\d+)", line)
        if not m:
            continue
        name = m.group(1)
        pubs = []
        if m.group(8) != "-":
            for p in m.group(8).rstrip(";").split(";"):
                c, o, v, ph = p.split(":")
                pubs.append((int(c), int(o), int(v), ph))
        out[name] = {"final": (int(m.group(2)), int(m.group(3))),
                     "done": int(m.group(4)), "b4zero": int(m.group(5)),
                     "b4one": int(m.group(6)), "cmd4viol": int(m.group(7)),
                     "pubs": pubs, "clocks": int(m.group(9)),
                     "timeout": int(m.group(10))}
    return out


def main():
    runs = {r: parse(r) for r in ("fixa_delta", "fixa_base", "m2_delta", "veto1")}
    names = list(REF.keys())
    missing = [(r, n) for r in runs for n in names if n not in runs[r]]
    if missing:
        print(f"INCOMPLETE: {len(missing)} case-results missing: {missing[:6]}")
        return 2

    fails = []
    report = []
    for n in names:
        ref = REF[n]
        fd, fb, m2, v1 = (runs[r][n] for r in
                          ("fixa_delta", "fixa_base", "m2_delta", "veto1"))
        for tag, r in (("fixa_delta", fd), ("fixa_base", fb), ("veto1", v1)):
            if r["timeout"] or not r["done"]:
                fails.append((n, tag, "TIMEOUT/no-DONE"))
            if r["b4zero"] == 0 or r["b4zero"] != ref["b4zero"]:
                fails.append((n, tag, f"A b4zero {r['b4zero']} != ref {ref['b4zero']}"))
            if r["cmd4viol"] != 0:
                fails.append((n, tag, f"B cmd4viol {r['cmd4viol']}"))
        if fd["final"] != fb["final"]:
            fails.append((n, "delta-vs-base", f"C {fd['final']} != {fb['final']}"))
        for tag, r in (("fixa_delta", fd), ("fixa_base", fb)):
            bad = [p for p in r["pubs"]
                   if p[3] == "s" and p[2] == 1 and ref["unvetoed_exists"]]
            if bad:
                fails.append((n, tag, f"D vetoed search-pub {bad}"))
        pyref = tuple(ref["final"])
        note = "" if fd["final"] == pyref else \
            f"  [E py65 divergence: rtl={fd['final']} py65={pyref}]"
        # M2 kill evidence per case
        m2_broke = (m2["cmd4viol"] > 0) or (m2["final"] != fd["final"])
        # veto1 hole evidence
        v1_hole = [p for p in v1["pubs"] if p[3] == "s" and p[2] == 1]
        report.append((n, fd, m2_broke, v1_hole, note))

    m2_killed = any(r[2] for r in report)
    m2_viol_total = sum(runs["m2_delta"][n]["cmd4viol"] for n in names)
    v1_hole_cases = [r[0] for r in report if r[3] and REF[r[0]]["unvetoed_exists"]]

    print("=" * 78)
    print("G1 (minimal) -- delta-path co-sim gate, real RTL (Verilator CoproDrMario)")
    print("=" * 78)
    for (n, fd, m2b, v1h, note) in report:
        print(f"  {n:<18} final={fd['final']} b4zero={fd['b4zero']} "
              f"clocks={fd['clocks']:>10}  m2_broke={'Y' if m2b else 'n'} "
              f"veto1_vetoed_pubs={len(v1h)}{note}")
    print()
    for f in fails:
        print("  FAIL:", f)
    print(f"\n  M2-under-delta: cmd4viol total {m2_viol_total} across "
          f"{sum(1 for n in names if runs['m2_delta'][n]['cmd4viol'])} cases; "
          f"finals diverged on "
          f"{sum(1 for r in report if runs['m2_delta'][r[0]]['final'] != runs['fixa_delta'][r[0]]['final'])} "
          f"-> {'KILLED' if m2_killed else 'SURVIVED'}")
    print(f"  veto1 (pre-Fix-A) anytime hole visible on: {v1_hole_cases} "
          f"({'positive control OK' if v1_hole_cases else 'NOT SEEN -- control failed'})")
    ediv = [r[0] for r in report if r[4]]
    print(f"  py65 cross-check divergences (reported, not gated): {ediv or 'none'}")
    ok = not fails and m2_killed and bool(v1_hole_cases)
    print(f"\nG1 GATE: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
