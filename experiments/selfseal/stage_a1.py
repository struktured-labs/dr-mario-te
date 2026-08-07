#!/usr/bin/env python3
"""STAGE A1 -- free re-mining of the endgame-policy seal corpus.

Answers, with NO new simulation, from portfolio/endgame-policy/seal_probe_n200.json:
  * WHEN do seals happen (viruses-remaining, row, column, pills-to-end)?
  * Do they self-correct (reopen lag distribution), and how many survive to the end?
  * Are seal-games longer than seal-free games (naive, CONFOUNDED -- flagged as such)?

Board convention per eval47/ab47.py: flat 128-cell row-major idx = r*8 + c,
row 0 = TOP, 16 rows x 8 cols. Event tuples are
  seal   = (pill_idx, vc_after, virus_idx, cover_idx)
  reopen = (pill_idx, vc_after, virus_idx)
"""
from __future__ import annotations

import json
import statistics as st
from collections import Counter

SRC = ("/home/struktured/projects/dr-mario-qa-wt/experiments/portfolio/"
       "endgame-policy/seal_probe_n200.json")


def main():
    d = json.load(open(SRC))
    rows = [r for r in d["rows"] if "error" not in r]
    print(f"=== STAGE A1: re-mine of {len(rows)} champion games (L11, ws=20, clean stream) ===\n")

    seal_rows = [r for r in rows if r["n_seal_events"] > 0]
    free_rows = [r for r in rows if r["n_seal_events"] == 0]

    # ---- WHEN: viruses remaining / row / column / pills-to-end -------------
    vc_at_seal, row_at_seal, col_at_seal, pills_to_end = [], [], [], []
    cover_dr = Counter()
    for r in rows:
        for (pill, vc, vi, cj) in r["seal_events"]:
            vc_at_seal.append(vc)
            row_at_seal.append(vi // 8)
            col_at_seal.append(vi % 8)
            pills_to_end.append(r["pills"] - pill)
            cover_dr[(vi - cj) // 8] += 1

    print("-- WHEN (n=%d seal events) --" % len(vc_at_seal))
    print("  viruses remaining at seal :", dict(sorted(Counter(vc_at_seal).items())))
    print("     median %d, mean %.2f" % (st.median(vc_at_seal), st.mean(vc_at_seal)))
    print("  virus ROW (0=top)         :", dict(sorted(Counter(row_at_seal).items())))
    print("  virus COL                 :", dict(sorted(Counter(col_at_seal).items())))
    print("  cover offset (rows above) :", dict(cover_dr))
    print("  pills from seal to game end: median %.0f  mean %.1f  p10 %.0f  p90 %.0f" % (
        st.median(pills_to_end), st.mean(pills_to_end),
        sorted(pills_to_end)[len(pills_to_end) // 10],
        sorted(pills_to_end)[9 * len(pills_to_end) // 10]))

    # ---- SELF-CORRECTION: reopen lag --------------------------------------
    lags, never = [], 0
    for r in rows:
        # match each seal to the next reopen of the SAME virus after it
        reopens = sorted(r["reopen_events"], key=lambda e: e[0])
        used = set()
        for (pill, vc, vi, cj) in sorted(r["seal_events"], key=lambda e: e[0]):
            hit = None
            for k, (rp, rvc, rvi) in enumerate(reopens):
                if k in used or rvi != vi or rp < pill:
                    continue
                hit = (k, rp)
                break
            if hit is None:
                never += 1
            else:
                used.add(hit[0])
                lags.append(hit[1] - pill)

    print("\n-- SELF-CORRECTION --")
    print(f"  seals that later re-open : {len(lags)}/{len(vc_at_seal)} "
          f"({len(lags)/len(vc_at_seal):.1%})")
    print(f"  seals never re-opened    : {never}")
    if lags:
        print("  reopen lag (pills)       : median %.0f  mean %.1f  p90 %.0f  max %d" % (
            st.median(lags), st.mean(lags), sorted(lags)[9 * len(lags) // 10], max(lags)))
        print("  lag distribution         :", dict(sorted(Counter(lags).items())[:12]))
    print(f"  viruses still sealed at game end (all games): "
          f"{sum(r['still_sealed_at_end'] for r in rows)}")
    print(f"  games ending with a sealed virus: "
          f"{sum(1 for r in rows if r['still_sealed_at_end'] > 0)}/{len(rows)}")

    # ---- OUTCOME: does sealing cost anything, naively? ---------------------
    print("\n-- NAIVE COST (CONFOUNDED: longer games have more chances to seal) --")
    for name, g in (("seal games", seal_rows), ("seal-free games", free_rows)):
        pills = [r["pills"] for r in g]
        print(f"  {name:16s} n={len(g):3d}  pills mean {st.mean(pills):6.1f}  "
              f"median {st.median(pills):5.0f}  won {sum(r['won'] for r in g)}/{len(g)}")
    print("  ^ this comparison CANNOT establish causation; see stage_a2 counterfactual.")

    # outcome of the games whose seal never reopened
    stuck = [r for r in rows if r["still_sealed_at_end"] > 0]
    print(f"\n  games with a virus sealed AT THE END: {len(stuck)} -> "
          f"won {sum(r['won'] for r in stuck)}, topout {sum(r['topout'] for r in stuck)}, "
          f"stall {sum(r['stall'] for r in stuck)}")
    print(f"  (whole corpus: won {sum(r['won'] for r in rows)}, "
          f"topout {sum(r['topout'] for r in rows)}, stall {sum(r['stall'] for r in rows)})")


if __name__ == "__main__":
    main()
