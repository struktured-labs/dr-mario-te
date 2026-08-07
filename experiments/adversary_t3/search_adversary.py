#!/usr/bin/env python3
"""Evolutionary search over the 5-int adversary vector (w_chain, ws, w_press, w_hold,
w_bigsq -- see adversary_search.py) to MAXIMISE the champion's death rate.

NOT full CMA-ES: a (1+lambda) evolution strategy with a single self-adapting global
step size (classic Rechenberg 1/5 rule), scaled by a fixed per-parameter unit vector.
Chosen over covariance-matrix adaptation because the search space is only 5-D, each
knob has a distinct interpretable mechanism (roughly axis-aligned), and the paired-seed
fitness is already the expensive part (each candidate costs n_seeds*2 full VS matches);
a simpler, cheaper-to-implement-correctly search was judged the better trade here. If
this proves too weak (stuck / noisy), the fallback is bumping n_seeds per candidate,
not switching algorithms.

PAIRED SEEDS: every candidate in a generation, and the parent it is compared against,
is evaluated on the EXACT SAME seed set (TRAIN_SEEDS) -- the project has been burned
repeatedly by unpaired comparisons (memory dr-mario-selfplay-vs-negative,
dr-mario-vs-harness-defects). No candidate ever gets an easier seed set than its rivals.

ANYTIME: best-so-far vector + fitness is written to checkpoint.json after every
generation, so the search can be killed at any point and still report a usable result.
"""
from __future__ import annotations

import sys
import os
import json
import random
import time

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from batch_run import evaluate, fitness_scalar, OPP_ADV, get_pool, shutdown_pool

# search space bounds: (lo, hi) per parameter
BOUNDS = [(0, 500),      # w_chain
          (0, 80),       # ws
          (-100, 150),   # w_press
          (-200, 400),   # w_hold
          (0, 50)]       # w_bigsq
SCALE0 = [40.0, 8.0, 15.0, 40.0, 6.0]   # per-parameter mutation unit (at sigma=1.0)
NAMES = ["w_chain", "ws", "w_press", "w_hold", "w_bigsq"]

TRAIN_SEEDS = list(range(5000, 5020))     # n=20, per task spec's "start with 20-30"
CKPT = os.path.join(HERE, "search_checkpoint.json")
LOG = os.path.join(HERE, "search_log.jsonl")


def clamp(vec):
    return tuple(max(lo, min(hi, int(round(x)))) for (lo, hi), x in zip(BOUNDS, vec))


def mutate(vec, sigma, rng):
    child = [v + rng.gauss(0, 1) * s * sigma for v, s in zip(vec, SCALE0)]
    return clamp(child)


def random_init(rng):
    return clamp([rng.uniform(lo, hi) for lo, hi in BOUNDS])


def log_line(obj):
    with open(LOG, "a") as fh:
        fh.write(json.dumps(obj) + "\n")


def checkpoint(gen, best_vec, best_fit, best_res, sigma, t0):
    with open(CKPT, "w") as fh:
        json.dump({
            "generation": gen, "best_vec": list(best_vec),
            "best_vec_named": dict(zip(NAMES, best_vec)),
            "best_fitness": best_fit,
            "best_death_rate": best_res["champ_death_rate"],
            "best_death_ci": best_res["death_ci"],
            "best_dies_ahead_rate": best_res["dies_ahead_rate"],
            "best_pills_to_clear": best_res["champ_pills_to_clear"],
            "sigma": sigma, "elapsed_s": time.time() - t0,
            "train_seeds": [TRAIN_SEEDS[0], TRAIN_SEEDS[-1], len(TRAIN_SEEDS)],
        }, fh, indent=2)


def run(generations=18, lam=6, workers=6, seed=20260806, init_vec=None):
    rng = random.Random(seed)
    t0 = time.time()
    get_pool(workers=workers)

    parent = clamp(init_vec) if init_vec else random_init(rng)
    parent_res = evaluate(TRAIN_SEEDS, OPP_ADV, vec=parent, workers=workers)
    parent_fit = fitness_scalar(parent_res)
    print(f"[gen 0] init {dict(zip(NAMES, parent))} death={parent_res['champ_death_rate']:.3f} "
          f"fit={parent_fit:.2f}", flush=True)
    log_line({"gen": 0, "vec": list(parent), "fitness": parent_fit,
              "death_rate": parent_res["champ_death_rate"],
              "dies_ahead_rate": parent_res["dies_ahead_rate"]})
    checkpoint(0, parent, parent_fit, parent_res, sigma=1.0, t0=t0)

    sigma = 1.0
    for g in range(1, generations + 1):
        children = [mutate(parent, sigma, rng) for _ in range(lam)]
        # also inject one fully-random child each generation to escape local optima
        children.append(random_init(rng))
        results = [evaluate(TRAIN_SEEDS, OPP_ADV, vec=c, workers=workers) for c in children]
        fits = [fitness_scalar(r) for r in results]
        best_i = max(range(len(children)), key=lambda i: fits[i])
        success = fits[best_i] > parent_fit
        if success:
            parent, parent_fit, parent_res = children[best_i], fits[best_i], results[best_i]
            sigma = min(sigma * 1.5, 4.0)     # 1/5 rule: improved -> widen step
        else:
            sigma = max(sigma * 0.85, 0.15)   # no improvement -> narrow step

        print(f"[gen {g}] best-child death={results[best_i]['champ_death_rate']:.3f} "
              f"fit={fits[best_i]:.2f} {'(ACCEPTED)' if success else '(rejected, kept parent)'} "
              f"sigma={sigma:.2f}  parent={dict(zip(NAMES, parent))}", flush=True)
        log_line({"gen": g, "children": [list(c) for c in children],
                  "fitness": fits, "accepted": success,
                  "parent_vec": list(parent), "parent_fitness": parent_fit,
                  "parent_death_rate": parent_res["champ_death_rate"],
                  "sigma": sigma, "elapsed_s": time.time() - t0})
        checkpoint(g, parent, parent_fit, parent_res, sigma, t0)

    shutdown_pool()
    print(f"DONE in {time.time()-t0:.0f}s. Best: {dict(zip(NAMES, parent))} "
          f"death_rate={parent_res['champ_death_rate']:.3f} "
          f"CI={parent_res['death_ci']}", flush=True)
    return parent, parent_res


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=18)
    ap.add_argument("--lam", type=int, default=6)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=20260806)
    a = ap.parse_args()
    if os.path.exists(LOG):
        os.remove(LOG)
    run(generations=a.generations, lam=a.lam, workers=a.workers, seed=a.seed)
