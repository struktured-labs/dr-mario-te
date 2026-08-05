#!/usr/bin/env python3
"""Analysis for dissect_trajectory.py's JSONL output -- answers the saga plan's
questions in order:

1. MATCH-CLASS RATES along real firmware trajectories (vs the 20-board static
   harvest's 11/20 base agreement + 2/20 flips): how often do the two deciders
   agree per decision, and which disagreement class dominates?
2. REGRET ACCOUNTING under the mirror ruler: total mirror-value the firmware
   bleeds per game, split by match class and by regime -- the class carrying the
   most summed regret NAMES THE FIX (per the plan's step 3).
3. FIRE-QUALITY: for decisions where the firmware fired a tuck, its margin under
   the mirror (mirval_fw - mir_base) vs the mirror's own fires' margins -- are
   firmware fires systematically lower-true-margin?
4. ENUMERATOR MEMBERSHIP: fraction of firmware fires whose (cells,colors) do not
   even exist in the mirror's candidate list (tuck_scan_v3 vs
   RS.tuck_root_candidates set divergence).
5. STRUCTURE: regret correlation with maxh / vc (the plan's step 2 fingerprint
   check on the ~107 residual).

Usage: dissect_analyze.py results/dissect/dissect_L11.jsonl
"""
from __future__ import annotations

import sys
import json
import statistics as st
from collections import defaultdict


def main(fn):
    rows, games = [], []
    with open(fn) as fh:
        for line in fh:
            r = json.loads(line)
            (games if "GAME_END" in r else rows).append(r)

    n = len(rows)
    print(f"=== DISSECTION ANALYSIS: {fn} ===")
    print(f"{len(games)} games ({sum(1 for g in games if g['GAME_END']=='clear')} clears), "
          f"{n} decisions\n")

    # 1. match classes
    by_cls = defaultdict(list)
    for r in rows:
        by_cls[r["cls"]].append(r)
    print("1. MATCH CLASSES (per decision, firmware trajectory)")
    for cls in ("base_same", "base_diff", "tuck_same", "tuck_diff",
                "fw_tuck_mir_base", "fw_base_mir_tuck"):
        k = len(by_cls.get(cls, []))
        if k:
            print(f"   {cls:18s} {k:5d}  ({k/n:6.1%})")
    agree = len(by_cls.get("base_same", [])) + len(by_cls.get("tuck_same", []))
    print(f"   AGREE overall      {agree:5d}  ({agree/n:6.1%})\n")

    # 2. regret accounting
    print("2. REGRET under the mirror ruler (mirror's pick value - firmware's pick value)")
    tot_regret = sum(r["regret"] for r in rows if r["regret"] is not None)
    per_game = tot_regret / max(1, len(games))
    print(f"   total {tot_regret:,.0f} over {len(games)} games = {per_game:,.0f}/game")
    print(f"   {'class':18s} {'n':>5s} {'sum_regret':>12s} {'share':>7s} {'mean':>8s} {'median':>8s}")
    for cls, rs in sorted(by_cls.items(), key=lambda kv: -sum(x["regret"] or 0 for x in kv[1])):
        regs = [x["regret"] for x in rs if x["regret"] is not None]
        if not regs:
            continue
        s = sum(regs)
        print(f"   {cls:18s} {len(regs):5d} {s:12,.0f} {s/max(tot_regret,1e-9):7.1%} "
              f"{st.mean(regs):8.1f} {st.median(regs):8.1f}")
    print()
    print("   by regime:")
    by_reg = defaultdict(list)
    for r in rows:
        if r["regret"] is not None:
            by_reg[r["regime"]].append(r["regret"])
    for reg in ("open", "mid", "end"):
        regs = by_reg.get(reg, [])
        if regs:
            print(f"   {reg:5s} n={len(regs):5d}  sum {sum(regs):12,.0f}  "
                  f"mean {st.mean(regs):8.1f}")
    print()

    # 3. fire quality: firmware fires vs mirror fires, margin under mirror ruler
    print("3. FIRE QUALITY (margin over mirror's best base, mirror ruler)")
    fw_fires = [r for r in rows if r["fw_kind"] == "tuck"
                and r["mirval_fw"] is not None and r["mir_base"] is not None]
    mir_fires = [r for r in rows if r["mir_kind"] == "tuck" and r["mir_base"] is not None]
    if fw_fires:
        m = [r["mirval_fw"] - r["mir_base"] for r in fw_fires]
        neg = sum(1 for x in m if x < 150)
        print(f"   firmware fires n={len(fw_fires)}  mirror-margin mean {st.mean(m):+.1f} "
              f"median {st.median(m):+.1f}  below-theta(150) {neg} ({neg/len(m):.1%})")
    if mir_fires:
        m = [r["mir_val"] - r["mir_base"] for r in mir_fires]
        print(f"   mirror   fires n={len(mir_fires)}  mirror-margin mean {st.mean(m):+.1f} "
              f"median {st.median(m):+.1f}")
    print()

    # 4. enumerator membership
    fwt = [r for r in rows if r["fw_kind"] == "tuck"]
    miss = [r for r in fwt if r["fw_in_mir_cands"] is False]
    print(f"4. ENUMERATOR MEMBERSHIP: {len(fwt)} firmware fires, "
          f"{len(miss)} NOT in mirror candidate list "
          f"({len(miss)/max(1,len(fwt)):.1%})")
    if miss:
        for r in miss[:10]:
            print(f"   seed {r['seed']} pill {r['pill']} vc {r['vc']} cells {r['fw_desc']}")
    print()

    # 5. structure: regret vs height/vc
    print("5. STRUCTURE (mean regret by maxh band / vc band)")
    bands = [(0, 4), (5, 7), (8, 10), (11, 16)]
    for lo, hi in bands:
        regs = [r["regret"] for r in rows
                if r["regret"] is not None and lo <= r["maxh"] <= hi]
        if regs:
            print(f"   maxh {lo:2d}-{hi:2d}: n={len(regs):5d}  mean {st.mean(regs):8.1f}")
    # anomalies
    illegal = [r for r in rows if r["mirval_fw"] is None]
    if illegal:
        print(f"\n!! {len(illegal)} decisions where the firmware pick was ILLEGAL under "
              f"mirror physics (mirval_fw None) -- inspect these first:")
        for r in illegal[:10]:
            print(f"   seed {r['seed']} pill {r['pill']} fw {r['fw_kind']} {r['fw_desc']}")


if __name__ == "__main__":
    main(sys.argv[1])
