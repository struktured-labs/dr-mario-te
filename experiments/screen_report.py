#!/usr/bin/env python3
"""Rank the sensitivity screen, and say honestly how much of it is multiplicity.

MULTIPLICITY IS THE WHOLE PROBLEM HERE. The screen tests ~30 candidates at a 95% CI, so
under a TRUE NULL you expect ~1.5 of them to look significant by luck alone. That is the
exact shape of this project's two retracted wins. So nothing here is a result -- everything
that clears the bar is a CANDIDATE for stage-2 confirmation on a fresh seed block.

Also checks whether MARGIN agrees with WIN RATE. Margin is the lower-variance signal and it
is tempting to search on it, but substituting a proxy objective is what caused the trouble
in the first place; this measures the agreement instead of assuming it.
"""
from __future__ import annotations
import sys, json, math
import statistics as st


def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def main(path):
    rows = load(path)
    if not rows:
        print("no rows"); return
    n = len(rows)
    print(f"SCREEN REPORT  ({n} candidates, reference = WINNER, seed-paired 95% bootstrap CI)")
    print(f"  expected FALSE positives at 95% under a true null: {0.05*n:.1f}")
    print()

    rows.sort(key=lambda r: -r["winrate"])
    print(f"  {'knob':>8} {'val':>5}  {'winrate':>8}  {'95% CI':>17}  {'margin':>7}  "
          f"{'atk c/r':>10}  verdict")
    for r in rows:
        if r["wr_lo"] > 0.5:
            v = "BETTER (candidate)"
        elif r["wr_hi"] < 0.5:
            v = "worse"
        else:
            v = "-"
        print(f"  {r['knob']:>8} {r['value']:>5}  {r['winrate']:7.1%}  "
              f"[{r['wr_lo']:6.1%},{r['wr_hi']:6.1%}]  {r['margin']:+7.2f}  "
              f"{r['atk_cand']:.2f}/{r['atk_ref']:.2f}  {v}")

    better = [r for r in rows if r["wr_lo"] > 0.5]
    worse = [r for r in rows if r["wr_hi"] < 0.5]
    print()
    print(f"  {len(better)} candidates BETTER, {len(worse)} worse, {n-len(better)-len(worse)} "
          f"not separated")
    if len(better) <= 0.05 * n:
        print(f"  ⚠ {len(better)} 'better' is AT OR BELOW the {0.05*n:.1f} expected by chance "
              f"-- consistent with NO knob helping")

    # margin vs win rate agreement
    wr = [r["winrate"] for r in rows]; mg = [r["margin"] for r in rows]
    if len(rows) > 2 and st.pstdev(wr) > 0 and st.pstdev(mg) > 0:
        mw, mm = st.mean(wr), st.mean(mg)
        cov = sum((a - mw) * (b - mm) for a, b in zip(wr, mg)) / len(wr)
        rho = cov / (st.pstdev(wr) * st.pstdev(mg))
        verdict = ("margin tracks win rate -- usable as a lower-variance search signal"
                   if rho > 0.85 else
                   "margin only loosely tracks win rate -- screen on margin, ACCEPT on win rate"
                   if rho > 0.6 else
                   "MARGIN AND WIN RATE DISAGREE -- do not search on margin")
        print(f"\n  margin vs winrate correlation across candidates: r = {rho:+.3f}\n"
              f"    {verdict}")

    # does attack volume explain winning?
    aw = [r["atk_cand"] - r["atk_ref"] for r in rows]
    if st.pstdev(aw) > 0:
        mw, ma = st.mean(wr), st.mean(aw)
        cov = sum((a - mw) * (b - ma) for a, b in zip(wr, aw)) / len(wr)
        rho2 = cov / (st.pstdev(wr) * st.pstdev(aw))
        print(f"\n  winrate vs (attacks sent - attacks taken): r = {rho2:+.3f}")
        print("    ⚠ CONFOUNDED, do not read as 'attacking causes winning'. A stronger eval"
              " both\n      clears faster AND stumbles into more doubles, so quality drives"
              " both terms.\n      The causal test is the attack-shaping sweep: BUY attacks"
              " directly and see if\n      win rate follows.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         "/home/struktured/projects/dr-mario-qa-wt/tmp/selfplay/screen_real.jsonl")
