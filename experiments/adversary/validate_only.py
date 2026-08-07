#!/usr/bin/env python3
"""validate_only.py -- SKIP the GA search (already run 3x at small n in this
session -- see ADVERSARIAL_PRESSURE.md's "search phase" section; consistently
finds near_spawn/spawn targeting as the dominant lever) and go straight to
the n=120 HOLDOUT comparison the honesty rules require before calling
anything a finding. Reuses adversary_search.py's play_seed_adversarial /
play_seed_honest / build_honest_v1_1_model verbatim -- no new game logic.

Candidates validated here are the FIXED genomes already discovered by the
in-session GA runs (smoke_result3.json's candidates, representative of what
every independent GA run converged to), not re-searched.
"""
from __future__ import annotations

import sys
import os
import json
import time
import argparse
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import adversary_search as AS  # noqa: E402

BINS = AS.BINS

# Genomes taken verbatim from smoke_result3.json's "candidates" (GA-found,
# n=6 train seeds, 3 independent GA runs this session converged on the same
# near_spawn/spawn shape -- see report). Kept as plain dicts with tuple keys
# for AS's internal convention.
GA_NEAR_SPAWN = {
    "fire": {(4, 6): 0.36536897181816486, (7, 10): 0.4156494986616913, (11, 999): 0.025055204344575976},
    "size_weights": [0.18410152926912224, 0.23279968847815752, 0.19903870175332875,
                      0.15207118141147202, 0.2319888990879195],
    "target_mode": "near_spawn",
}
GA_NEAR_SPAWN_B = {
    "fire": {(4, 6): 0.5132947857140642, (7, 10): 0.45501320210952045, (11, 999): 0.0},
    "size_weights": [0.2578867864545552, 0.228994252624265, 0.15891397910757388,
                      0.19001973263515182, 0.1641852491784541],
    "target_mode": "near_spawn",
}
ALWAYS_SPAWN_MAX = {
    "fire": {b: 1.0 for b in BINS},
    "size_weights": [0.0, 0.0, 0.0, 0.0, 1.0],
    "target_mode": "spawn",
}


def honest_shaped_spawn(honest_model):
    return AS.honest_shaped_adversarial_target(honest_model)


def _worker_init():
    AS._worker_init()


def _eval_adv(args):
    seed, schedule, budget, max_pills = args
    return AS.play_seed_adversarial(seed, schedule, budget, max_pills=max_pills)


def _eval_honest(args):
    seed, model, budget = args
    return AS.play_seed_honest(seed, model, budget)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--holdout-seeds", type=int, default=120)
    ap.add_argument("--budget", type=int, default=AS.BUDGET_HALVES)
    ap.add_argument("--out", type=str, default=os.path.join(HERE, "validate_result.json"))
    a = ap.parse_args()

    holdout_seeds = list(range(AS.HOLDOUT_SEED0, AS.HOLDOUT_SEED0 + a.holdout_seeds))

    print("=== fitting honest v1.1 model once (parent process) ===", flush=True)
    t_fit = time.monotonic()
    honest_model = AS.build_honest_v1_1_model()
    print(f"    done in {time.monotonic()-t_fit:.1f}s "
          f"(n_volleys={honest_model.n_volleys} n_clears={honest_model.n_clears})", flush=True)

    candidates = {
        "ga_near_spawn_a": GA_NEAR_SPAWN,
        "ga_near_spawn_b": GA_NEAR_SPAWN_B,
        "always_spawn_max": ALWAYS_SPAWN_MAX,
        "honest_shape_spawn_target": honest_shaped_spawn(honest_model),
    }

    t0 = time.monotonic()
    results = {}
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_worker_init) as pool:
        cs = AS._chunksize(len(holdout_seeds), a.workers)

        print(f"=== HOLDOUT n={a.holdout_seeds} budget={a.budget} workers={a.workers} ===",
              flush=True)

        t1 = time.monotonic()
        rows = list(pool.map(_eval_honest, [(s, honest_model, a.budget) for s in holdout_seeds],
                              chunksize=cs))
        summ = AS.summarize(rows)
        results["honest_v1_1_random"] = summ
        print(f"  honest_v1_1_random: dies_ahead={summ['dies_ahead_rate']:.1%} "
              f"topout={summ['topout_rate']:.1%} clear={summ['clear_rate']:.1%} "
              f"avg_garbage={summ['avg_garbage']:.1f} ({time.monotonic()-t1:.1f}s)", flush=True)

        for name, g in candidates.items():
            t1 = time.monotonic()
            rows = list(pool.map(_eval_adv, [(s, g, a.budget, 300) for s in holdout_seeds],
                                  chunksize=cs))
            summ = AS.summarize(rows)
            results[name] = summ
            print(f"  {name}: dies_ahead={summ['dies_ahead_rate']:.1%} "
                  f"topout={summ['topout_rate']:.1%} clear={summ['clear_rate']:.1%} "
                  f"avg_garbage={summ['avg_garbage']:.1f} ({time.monotonic()-t1:.1f}s)", flush=True)

    total_dt = time.monotonic() - t0
    out = {
        "budget_halves": a.budget,
        "holdout_seeds": [holdout_seeds[0], holdout_seeds[-1]],
        "n": a.holdout_seeds,
        "candidates": {name: AS.genome_to_jsonable(g) if name != "honest_v1_1_random" else None
                        for name, g in candidates.items()},
        "results": results,
        "total_seconds": total_dt,
    }
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"\n=== wrote {a.out} ({total_dt:.1f}s total) ===", flush=True)


if __name__ == "__main__":
    main()
