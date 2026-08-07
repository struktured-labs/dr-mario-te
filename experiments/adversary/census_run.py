#!/usr/bin/env python3
"""census_run.py -- Hunt A: SEED CENSUS driver.

Runs the champion decide path (adversary_harness.play_seed, no pressure)
over as much of the SEED_SPACE=65536 as fits a wall-clock time budget,
using a PERSISTENT ProcessPoolExecutor (unlike adversary_harness.run_batch,
which spins up/tears down a pool per call -- fatal for a chunked multi-hour
run since every teardown pays the numba JIT warm cost again per worker).

Seed order: range(65536) shuffled once under a FIXED, logged RNG seed, then
consumed in that order. This makes any prefix of the run (if cut short by
the time budget) a genuine uniform-random sample of the FULL seed space --
not just "the first N seeds" -- while remaining exactly reproducible.

Checkpointing: results are appended to census_results.jsonl one line per
completed game after each wave (so a crash loses at most one wave). Any
TOPOUT/STALL seen is ALSO appended immediately to failures_seen.jsonl (seed
+ result only, cheap) so the tail is never lost even if the main run is
killed before its final summary.

Usage: python census_run.py --budget-seconds 10200 --wave 300 --workers 6
"""
from __future__ import annotations

import sys
import os
import json
import time
import random
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import adversary_harness as AH

OUT_DIR = os.path.join(HERE, "census")
RESULTS_PATH = os.path.join(OUT_DIR, "census_results.jsonl")
FAILURES_PATH = os.path.join(OUT_DIR, "failures_seen.jsonl")
PROGRESS_PATH = os.path.join(OUT_DIR, "census_progress.json")
DONE_PATH = os.path.join(OUT_DIR, "CENSUS_DONE")

SHUFFLE_RNG_SEED = 20260806  # fixed + logged: makes the consumed order reproducible


def build_seed_order():
    seeds = list(range(AH.SEED_SPACE))
    random.Random(SHUFFLE_RNG_SEED).shuffle(seeds)
    return seeds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-seconds", type=float, default=10200.0)  # 2h50m; buffer for post-processing
    ap.add_argument("--wave", type=int, default=300)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--warmup-seeds", type=int, default=12)
    a = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(DONE_PATH):
        os.remove(DONE_PATH)

    seed_order = build_seed_order()
    print(f"[census] seed order built: {len(seed_order)} seeds, shuffle_rng_seed={SHUFFLE_RNG_SEED}", flush=True)

    results_f = open(RESULTS_PATH, "w")
    failures_f = open(FAILURES_PATH, "w")

    counts = {"clear": 0, "topout": 0, "stall": 0}
    n_dies_ahead = 0
    t_start = time.monotonic()

    with ProcessPoolExecutor(max_workers=a.workers, initializer=AH._lazy) as ex:
        # untimed warmup: pays per-process numba JIT + import cost once
        warm = seed_order[:a.warmup_seeds]
        list(ex.map(AH._play_one, [(s, None, 300) for s in warm]))
        print(f"[census] warmup done ({a.warmup_seeds} seeds, untimed)", flush=True)

        idx = a.warmup_seeds
        t_run_start = time.monotonic()
        n_done = 0
        stop = False
        while not stop and idx < len(seed_order):
            wave_seeds = seed_order[idx: idx + a.wave]
            idx += len(wave_seeds)
            futs = [ex.submit(AH._play_one, (s, None, 300)) for s in wave_seeds]
            for f in as_completed(futs):
                r = f.result()
                results_f.write(json.dumps(r) + "\n")
                counts[r["result"]] = counts.get(r["result"], 0) + 1
                if r["result"] in ("topout", "stall"):
                    failures_f.write(json.dumps(r) + "\n")
                    failures_f.flush()
                if r.get("dies_ahead"):
                    n_dies_ahead += 1
                n_done += 1
            results_f.flush()

            elapsed = time.monotonic() - t_run_start
            rate = n_done / elapsed if elapsed > 0 else 0.0
            progress = {
                "n_done": n_done, "elapsed_s": elapsed, "games_per_sec": rate,
                "counts": dict(counts), "n_dies_ahead": n_dies_ahead,
                "seed_order_consumed": idx, "seed_space": len(seed_order),
                "budget_seconds": a.budget_seconds,
            }
            with open(PROGRESS_PATH, "w") as pf:
                json.dump(progress, pf, indent=2)
            print(f"[census] n={n_done} elapsed={elapsed:.0f}s rate={rate:.3f}g/s "
                  f"counts={counts} dies_ahead={n_dies_ahead}", flush=True)

            if elapsed >= a.budget_seconds:
                stop = True

    results_f.close()
    failures_f.close()

    total_elapsed = time.monotonic() - t_start
    summary = {
        "n_done": n_done, "elapsed_s": total_elapsed,
        "warmup_seeds": a.warmup_seeds, "wave": a.wave, "workers": a.workers,
        "counts": dict(counts), "n_dies_ahead": n_dies_ahead,
        "seed_order_consumed": idx, "seed_space": len(seed_order),
        "shuffle_rng_seed": SHUFFLE_RNG_SEED,
        "budget_seconds": a.budget_seconds,
    }
    with open(DONE_PATH, "w") as df:
        json.dump(summary, df, indent=2)
    print("[census] DONE " + json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
