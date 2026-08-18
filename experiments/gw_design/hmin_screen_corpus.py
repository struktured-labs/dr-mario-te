#!/usr/bin/env python3
"""h_min over the h13-gate flip-screen corpus — MID-GAME arm of the cross-check.

WHY. Every "% of releases" figure in GARBAGE_WINDOW_DESIGN.md inherits an
`h_hit` distribution of n=208 from 10 games of ONE arm at ONE level, with 4-8
observations in the decisive cells — the weakest input in the budget table, and
the 52.4% that gates the recommendation rests on it. The h13-gate screen banks
both board planes per flip over a MID-GAME population (median 15 viruses), so a
second, independent `h_min` distribution is recoverable with no re-run.

METHOD PARITY IS THE POINT. The column rule and the h_min definition are taken
from `garbwin/hmin_neardeath.py`, the same rig that produced the near-death
numbers, so the two distributions are comparable by construction rather than by
assertion. h13-gate deliberately shipped a decoder that computes NO h_min for
exactly this reason.

⚠ h_min IS NOT min(H). It is the minimum over GARBAGE-HIT columns. These plies
are not necessarily post-volley, so the honest computation is COUNTERFACTUAL
over volley phase — size 2 -> {c, c+4}, size 3 -> {c, c+2, c+4}, size 4 ->
{c, c+2, c+4, c+6}, c = frameCounter & 3 (or &1 for size 4) — reported across
phases, which is how the near-death "adversarial worst phase" row is produced.

⚠⚠ PRE-COMMITTED READING (registered in the design doc's risk register BEFORE
any of this data was seen, and repeated here at the point of use):
  * mid-game h_min RESEMBLES near-death (median ~4)  => ample windows are
    REGIME-GENERAL; the section 1.5 retraction generalises beyond death boards.
  * mid-game h_min DIFFERS materially                => window length is
    REGIME-DEPENDENT, and every release-share percentage in sections 1.3-1.4 is
    under-powered and must be re-derived per regime before being quoted.
Neither outcome is the one this lane needs. The second costs the document more,
and the h13-gate lane weighted it as the more likely of the two.

`--check-only` runs the full pipeline and asserts well-formedness WITHOUT
printing any distribution, so the instrument can be verified on a partial file
without spending a look at the answer.
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys

H13 = ("/home/struktured/projects/dr-mario-te/h13-gate/"
       "experiments/eval47/stage2/oracle")
CF = "/home/struktured/projects/dr_mario_rl/tmp/vs_aware"   # vs_harness.garbage_columns
CORPUS = os.path.join(H13, "out", "screen_90000.jsonl")

for p in (H13, CF):
    if p not in sys.path:
        sys.path.insert(0, p)

ROWS = 16


def _rules():
    """The ROM's own garbage column rule, from the shared VS harness."""
    from vs_harness import garbage_columns
    return garbage_columns


def hmin_over_phases(heights, garbage_columns, cols=8):
    """Every (size, phase) volley shape -> h_min. Returns a list."""
    out = []
    for size in (2, 3, 4):
        for phase in range(4):
            hit = [c for c in garbage_columns(size, phase) if 0 <= c < cols]
            if hit:
                out.append(min(int(heights[c]) for c in hit))
    return out


def collect(path):
    import decode_screen_boards as D
    gc = _rules()
    rows = []
    for ev in D.iter_events(path):
        plane = D.decode_plane(ev["pre_col"])   # colour plane; occupancy is != 0
        H = D.column_heights(plane)
        rows.append({"heights": [int(x) for x in H],
                     "hmins": hmin_over_phases(H, gc),
                     "maxh": int(max(H))})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=CORPUS)
    ap.add_argument("--check-only", action="store_true",
                    help="verify the pipeline WITHOUT revealing the distribution")
    a = ap.parse_args()

    rows = collect(a.corpus)

    # --- structural assertions, safe to run on a partial file
    assert rows, "no events decoded — corpus empty or schema changed"
    for r in rows:
        assert len(r["heights"]) == 8, "expected 8 columns"
        assert all(0 <= h <= ROWS for h in r["heights"]), "height out of range"
        assert r["hmins"], "no volley phase produced a hit column"
        assert all(0 <= h <= ROWS for h in r["hmins"]), "h_min out of range"

    if a.check_only:
        print(f"PIPELINE OK — {len(rows)} events decoded, "
              f"{sum(len(r['hmins']) for r in rows)} (event, volley-phase) pairs, "
              f"all heights and h_min in [0, {ROWS}]")
        print("distribution deliberately NOT printed (see the pre-commitment "
              "in this file's docstring)")
        return 0

    typical = [statistics.median(r["hmins"]) for r in rows]
    worst = [max(r["hmins"]) for r in rows]          # adversarial phase
    maxh = [r["maxh"] for r in rows]
    print(f"MID-GAME h_min over the flip-screen corpus  (n={len(rows)} flips)")
    print(f"  tallest column        : median {statistics.median(maxh):.0f}")
    print(f"  h_min, median phase   : median {statistics.median(typical):.1f}"
          f"   -> W = {264 - 16*statistics.median(typical):.0f} f")
    print(f"  h_min, worst phase    : median {statistics.median(worst):.1f}"
          f"   -> W = {264 - 16*statistics.median(worst):.0f} f")
    short = sum(1 for t in typical if 264 - 16 * t <= 56)
    print(f"  boards at W <= 56 f   : {short}/{len(rows)} = "
          f"{100.0*short/len(rows):.1f}%")
    print("\nNEAR-DEATH reference (garbwin/hmin_neardeath.py, 125 kill boards):")
    print("  tallest column median 15 · h_min median 4 · W median 200 f · "
          "W<=56 f on 3.2%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
