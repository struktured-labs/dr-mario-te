#!/usr/bin/env python3
"""Secondary endpoints for a price_board run, from its saved rows.

price_board's headline is the topout delta. In a SOLO regime that endpoint is
identically zero for every arm -- the champion essentially does not top out on a
clean board (`dr-mario-clean-failure-rate`) -- and a table of `+0.000 wash` says
nothing about the placements. This adds the paired deltas that still carry
signal there: viruses cleared over the horizon, and the height left in the spawn
columns, both with bootstrap CIs over the shared streams.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics as st


def boot_ci(xs, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(st.mean([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    for f in a.files:
        d = json.load(open(f))
        ref = d["ref"]
        tag = {x.get("arm", x.get("action")): x["tag"] for x in d["arms"]}
        by = {}
        for r in d["rows"]:
            by.setdefault(r.get("arm", r.get("action")), {})[r["stream"]] = r
        refd = by[ref]
        print(f"\n=== {f}  (ref = {tag[ref]}, n={len(refd)} streams) ===")
        print(f"{'arm':>22s} {'vClr':>6s} {'d vs ref [95% CI]':>26s}   "
              f"{'spawnH':>7s} {'d spawnH [95% CI]':>26s}")
        for act in sorted(by):
            d1 = by[act]
            ks = sorted(set(d1) & set(refd))
            dv = [d1[k]["viruses_cleared"] - refd[k]["viruses_cleared"] for k in ks]
            dh = [d1[k]["spawn_height"] - refd[k]["spawn_height"] for k in ks]
            lo, hi = boot_ci(dv)
            lo2, hi2 = boot_ci(dh)
            v = st.mean([d1[k]["viruses_cleared"] for k in ks])
            h = st.mean([d1[k]["spawn_height"] for k in ks])
            mark = "  REAL" if (hi < 0 or lo > 0) else "  wash"
            print(f"{tag[act]:>22s} {v:6.2f} {st.mean(dv):+8.2f} [{lo:+.2f},{hi:+.2f}]{mark}   "
                  f"{h:7.2f} {st.mean(dh):+8.2f} [{lo2:+.2f},{hi2:+.2f}]"
                  f"{'  REAL' if (hi2 < 0 or lo2 > 0) else '  wash'}")


if __name__ == "__main__":
    raise SystemExit(main())
