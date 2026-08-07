#!/usr/bin/env python3
"""analyze_ws.py -- read the paired ws sweep and report it honestly.

PAIRED analysis. Every dose played the same seeds, so the comparison against
the shipped dose (ws=20) is within-seed: McNemar on discordant pairs, not two
independent rates. At a ~20% base failure rate the unpaired comparison would
need several times the sample for the same power, and the project's own
history (matched-index control reversing a tight-CI result) says pairing is
the difference between a real effect and an artefact.

Reports, per dose:
  fail%        raw failure rate over seeds BOTH arms completed
  rescued      seeds the shipped dose FAILED and this dose CLEARED
  broken       seeds the shipped dose CLEARED and this dose FAILED
  net          rescued - broken (the only number that matters)
  McNemar p    exact binomial on the discordant pairs, two-sided
  pills        median pills-to-clear on seeds BOTH arms cleared -- a dose that
               cuts failures while slowing every clear is not obviously a win
"""
from __future__ import annotations

import sys
import json
import argparse
import statistics as st
from collections import defaultdict
from math import comb

CONTROL = 20


def mcnemar_exact(b, c):
    """Two-sided exact binomial on discordant pairs (b vs c)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(0, k + 1)) * (0.5 ** n)
    return min(1.0, 2 * tail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    a = ap.parse_args()

    by_dose = defaultdict(dict)      # ws -> seed -> row
    for line in open(a.path):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        by_dose[r["ws"]][r["seed"]] = r

    if CONTROL not in by_dose:
        sys.exit(f"no control arm ws={CONTROL} in {a.path}")

    ctrl = by_dose[CONTROL]
    doses = sorted(by_dose)
    print(f"{'ws':>4} {'n':>5} {'fail%':>7} {'resc':>5} {'brok':>5} {'net':>5} "
          f"{'McNemar p':>10} {'med pills':>10}")
    print("-" * 62)

    for ws in doses:
        arm = by_dose[ws]
        common = sorted(set(arm) & set(ctrl))
        if not common:
            continue
        fails = sum(1 for s in common if arm[s]["result"] != "clear")
        rescued = sum(1 for s in common
                      if ctrl[s]["result"] != "clear" and arm[s]["result"] == "clear")
        broken = sum(1 for s in common
                     if ctrl[s]["result"] == "clear" and arm[s]["result"] != "clear")
        both_clear = [s for s in common
                      if ctrl[s]["result"] == "clear" and arm[s]["result"] == "clear"]
        med = st.median(arm[s]["pills"] for s in both_clear) if both_clear else float("nan")
        p = mcnemar_exact(rescued, broken) if ws != CONTROL else float("nan")
        tag = "  <-- SHIPPED" if ws == CONTROL else ""
        print(f"{ws:>4} {len(common):>5} {100 * fails / len(common):>6.1f}% "
              f"{rescued:>5} {broken:>5} {rescued - broken:>5} "
              f"{p:>10.4f} {med:>10.1f}{tag}")

    print(f"\ncontrol = ws={CONTROL} (shipped strand20). 'rescued'/'broken' are "
          f"vs that arm on identical seeds.")
    print("net > 0 with small p = the dose genuinely helps; net ~ 0 with a big "
          "rescued count means it is TRADING failures, not removing them.")


if __name__ == "__main__":
    main()
