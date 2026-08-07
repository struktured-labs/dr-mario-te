#!/usr/bin/env python3
"""bench_workers.py -- how many worker processes this box actually wants.

The Hetzner CCX23 reports 4 vCPU but lscpu shows 2 cores x 2 threads, so
"4 workers" may be buying hyperthread contention rather than throughput. This
measures it instead of assuming, because every downstream estimate (census
ETA, and the keep-or-cancel verdict) is denominated in games/sec.
"""
import sys
import argparse

sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/experiments/adversary")
import adversary_harness as AH  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4])
ap.add_argument("--n-seeds", type=int, default=48)
a = ap.parse_args()

for w in a.workers:
    tp = AH.measure_throughput(n_seeds=a.n_seeds, workers=w, warmup_seeds=8)
    print(f"workers={w:2d}  {tp['n_seeds']:3d} seeds / {tp['seconds']:6.1f}s "
          f"= {tp['games_per_sec']:.3f} games/sec", flush=True)
