#!/usr/bin/env python3
"""Per-DECISION tuck-candidate distribution at a fixed theta (default 150, the phase-2
recommendation). This is the search-COST driver for RTL/6502 sizing: the margin gate
(theta) prunes AFTER scoring, so the enumeration cost the copro pays is the candidate
count per decision, not the post-gate fire count. Logs one record per PILL PLACEMENT
(not per fired tuck) -- every decision where the tuck arm is on gets its candidate count,
virus count, and fill height recorded, via ab_root.play(..., log_decisions=True).

Usage:
  python3 decision_dist.py --level 11 --seeds 120 --theta 150 --workers 16 --out results/decisions_L11.json
  python3 decision_dist.py --level 20 --seeds 240 --theta 150 --workers 16 --out results/decisions_L20.json
"""
from __future__ import annotations

import sys
import os
import json
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import ab_root as AB   # noqa: E402


def pctl(sorted_xs, p):
    if not sorted_xs:
        return float("nan")
    k = min(len(sorted_xs) - 1, int(round(p / 100 * (len(sorted_xs) - 1))))
    return sorted_xs[k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, required=True)
    ap.add_argument("--seeds", type=int, required=True)
    ap.add_argument("--theta", type=float, default=150.0)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--P", type=int, default=12)
    ap.add_argument("--exec-only", type=int, default=1)
    ap.add_argument("--out", type=str, required=True)
    a = ap.parse_args()

    print(f"=== per-decision candidate distribution, L{a.level}, n={a.seeds}, "
          f"theta={a.theta} ===", flush=True)

    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=AB._init,
                             initargs=(a.level, 1, a.P, bool(a.exec_only), a.theta, True)
                             ) as ex:
        done = 0
        for f in as_completed([ex.submit(AB.play, s) for s in range(a.seeds)]):
            rows.append(f.result())
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{a.seeds} games done", flush=True)

    all_decisions = []
    for r in rows:
        for d in r["decisions"]:
            d2 = dict(d)
            d2["seed"] = r["seed"]
            all_decisions.append(d2)

    ns = sorted(d["n"] for d in all_decisions)
    total_decisions = len(ns)
    total_pills = sum(r["pills"] for r in rows)

    p50 = pctl(ns, 50)
    p90 = pctl(ns, 90)
    p99 = pctl(ns, 99)
    mx = ns[-1] if ns else float("nan")

    worst = [d for d in all_decisions if d["n"] == mx] if ns else []

    print(f"\ntotal decisions logged: {total_decisions}  (total pills placed across "
          f"{len(rows)} games: {total_pills})")
    print(f"candidates/decision: p50={p50}  p90={p90}  p99={p99}  max={mx}")
    print(f"mean candidates/decision: {sum(ns)/total_decisions:.3f}" if total_decisions else "")
    print(f"decisions with n==0: {sum(1 for n in ns if n == 0)} "
          f"({100*sum(1 for n in ns if n == 0)/total_decisions:.1f}%)" if total_decisions else "")
    print(f"\nworst decision(s), n={mx}: {len(worst)} instance(s)")
    for w in worst[:10]:
        print(f"  seed={w['seed']}  virus_count={w['vc']}  fill_height={w['fill']}")

    out = {
        "level": a.level, "seeds": a.seeds, "theta": a.theta,
        "total_decisions": total_decisions, "total_pills": total_pills,
        "p50": p50, "p90": p90, "p99": p99, "max": mx,
        "mean": (sum(ns) / total_decisions if total_decisions else float("nan")),
        "frac_zero": (sum(1 for n in ns if n == 0) / total_decisions if total_decisions else float("nan")),
        "worst_instances": worst[:50],
    }
    with open(a.out, "w") as fh:
        json.dump(out, fh)
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
