#!/usr/bin/env python3
"""Recompute the release-share column from the CORRECT h_min (task #124).

WHY THIS EXISTS. GARBAGE_WINDOW_DESIGN.md's section 1.3 `releases` column, and
every percentage derived from it (the 52.4% gating the recommendation, the 14.4%
at p90, the h>=14 tail), came from the co-sim farm's logged `h_hit` — which
`cosim_farm/game.py:184` defines as the **MAX** settled stack height over
garbage-hit columns. The window formula needs the **MIN**: a tile falls 15 - h,
so the drop animation ends with the tile that falls FURTHEST, i.e. the one in the
SHALLOWEST hit column, giving W = 24 + 16*(15 - h_min) = 264 - 16*h_min.
Measured bias on 446 real boards x 12 volley shapes: the logged variable
overstates h by a median of 7 and understates the window by 112 frames.

THE REPLACEMENT COSTS NOTHING. S0-A's screen already records `h_hit` correctly
at every real post-garbage ply (`screen_gw.py:307`, min over the columns that
actually received garbage, measured on the pre-injection board). So the run that
screens the deepening also supplies ~90x the invalidated denominator on the right
variable, with no extra compute.

    invalidated : prestart pilot lat[4],  n=208,     MAX over hit columns
    replacement : S0-A `prepost` rows,    n~19,000,  MIN over hit columns

⚠ SCOPE, carried forward rather than dropped: this is post-garbage plies under
the bursty dr. lulu injector — the SAME pressure model the pilot used, so the
comparison is like-for-like, but it is still ONE opponent model. Release rate and
its h distribution are properties of the opponent; a weaker opponent produces
fewer releases and a different shape. Do not present this column as universal.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
NTSC = 60.0988
HZ = {"pocket": 54_669_358.36, "mister": 85_909_088.0}
PILOT = "/mnt/data/drmario_cosim/results/prestart_pilot.jsonl"


def champion_cost():
    """C_median and C_p90 in copro cycles — unaffected by the h_hit bug."""
    lat = []
    for line in open(PILOT):
        lat.extend(json.loads(line)["lat"])
    c = sorted(t[0] for t in lat)
    return c[len(c) // 2], c[int(0.9 * len(c))]


def load_releases(path):
    """h_hit over every post-garbage ply, computed correctly by the screen."""
    hs = []
    for line in open(path):
        for r in json.loads(line).get("rows", []):
            if r.get("kind") == "prepost" and r.get("h_hit", -1) >= 0:
                hs.append(int(r["h_hit"]))
    return hs


def old_releases():
    """The INVALIDATED distribution, for the side-by-side."""
    hs = []
    for line in open(PILOT):
        for t in json.loads(line)["lat"]:
            if t[3] == 1 and t[4] >= 0:
                hs.append(int(t[4]))
    return hs


def table(hs, C50, C90, dom="pocket"):
    cpf = HZ[dom] / NTSC
    n = len(hs)
    cnt = Counter(hs)
    print(f"\n## Section 1.3 RECOMPUTED — {dom} tap, n={n} real releases "
          f"(h_min, correct variable)\n")
    print("| h | W (f) | releases | cum. | budget @median | budget @p90 | extra @median |")
    print("|---|---|---|---|---|---|---|")
    cum = 0
    for h in range(0, 17):
        wf = 264 - 16 * h
        share = 100.0 * cnt.get(h, 0) / n if n else 0.0
        cum += share
        n50, n90 = wf * cpf / C50, wf * cpf / C90
        extra = ("**base itself doesn't fit**" if n50 < 1
                 else f"**{n50 - 1:.2f}**")
        print(f"| {h} | {wf} | {share:.1f}% | {cum:.1f}% | {n50:.2f} | {n90:.2f} | {extra} |")
    return cnt, n


def affordability(hs, C50, C90, dom="pocket"):
    cpf = HZ[dom] / NTSC
    n = len(hs)
    cnt = Counter(hs)

    def share(mult, C):
        return 100.0 * sum(k for h, k in cnt.items()
                           if (264 - 16 * h) * cpf >= mult * C) / n
    print(f"\n## Section 1.4 RECOMPUTED — share of releases that can afford it\n")
    print("| computation | @median cost | @p90 cost |")
    print("|---|---|---|")
    for name, mult in (("base re-search only (1x)", 1.0),
                       ("base + 2-candidate deepening (3x)", 3.0),
                       ("...same, truncated at 80% (2.6x)", 2.6),
                       ("base + top-4 deepening (5x)", 5.0)):
        print(f"| {name} | **{share(mult, C50):.1f}%** | {share(mult, C90):.1f}% |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--s0a", default=os.path.join(HERE, "out", "s0a_50100.jsonl"))
    a = ap.parse_args()

    C50, C90 = champion_cost()
    new = load_releases(a.s0a)
    old = old_releases()
    if not new:
        sys.exit("no post-garbage rows found — has S0-A finished?")

    import statistics as st
    print("## The correction, side by side\n")
    print("| distribution | n | median h | median W | share h>=13 |")
    print("|---|---|---|---|---|")
    for name, hs in (("INVALIDATED — farm lat[4], max over hit cols", old),
                     ("REPLACEMENT — S0-A, min over hit cols", new)):
        hi = 100.0 * sum(1 for h in hs if h >= 13) / len(hs)
        m = st.median(hs)
        print(f"| {name} | {len(hs)} | {m:.0f} | {264 - 16*m:.0f} f | {hi:.1f}% |")

    table(new, C50, C90)
    affordability(new, C50, C90)
    print(f"\nC_median = {C50/1e6:.1f} M cycles · C_p90 = {C90/1e6:.1f} M "
          f"(unaffected by the h_hit bug — cost, not distribution)")
    print("⚠ One opponent model (bursty dr. lulu), same as the pilot: like-for-like, "
          "not universal.")


if __name__ == "__main__":
    main()
