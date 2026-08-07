#!/usr/bin/env python3
"""search_adversary.py + explicit exploration pressure, per team-lead's
correction: "add explicit exploration pressure (novelty/entropy bonus,
restarts)". A SEPARATE FILE, not an edit to search_adversary.py, because that
script is a LIVE background job while this was written (memory
live-script-edit-mv: never edit a script a live job runs -- bash reads
incrementally and a live process reading a half-edited file is exactly the
failure this avoids).

TWO explicit exploration mechanisms added on top of the run-1 design (single
random injection/generation, self-adapting step size):

  RESTARTS -- every RESTART_EVERY generations, the LOCAL parent is thrown away
  and reseeded from a fresh random vector. The GLOBAL best-ever (across all
  restarts) is tracked separately and is what gets checkpointed/returned --
  restarting never loses the best candidate found, it only stops the local
  search from being stuck exploiting one basin for the rest of the budget.

  NOVELTY BONUS -- among a generation's children, fitness ties (or near-ties)
  are broken in favour of the child FARTHER (L2, in the bounds-normalised
  parameter space) from every vector already accepted as a parent this run.
  Implemented as an additive bonus scaled by NOVELTY_WEIGHT, not a hard
  override -- a much worse but novel candidate still loses to a much better
  unoriginal one; it only tips close calls.
"""
from __future__ import annotations

import sys
import os
import json
import random
import time
import math

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from batch_run import evaluate, fitness_scalar, OPP_ADV, get_pool, shutdown_pool
from search_adversary import BOUNDS, SCALE0, NAMES, TRAIN_SEEDS, clamp, mutate, random_init

RESTART_EVERY = 6
NOVELTY_WEIGHT = 8.0     # small relative to fitness_scalar's death_rate*1000 dominance

CKPT = os.path.join(HERE, "search_v2_checkpoint.json")
LOG = os.path.join(HERE, "search_v2_log.jsonl")

_RANGE = [hi - lo for lo, hi in BOUNDS]


def norm_dist(a, b):
    return math.sqrt(sum(((x - y) / r) ** 2 for x, y, r in zip(a, b, _RANGE)))


def novelty(vec, history):
    if not history:
        return 0.0
    return min(norm_dist(vec, h) for h in history)


def log_line(obj):
    with open(LOG, "a") as fh:
        fh.write(json.dumps(obj) + "\n")


def checkpoint(gen, global_best_vec, global_best_fit, global_best_res, sigma, t0,
               n_restarts):
    with open(CKPT, "w") as fh:
        json.dump({
            "generation": gen, "best_vec": list(global_best_vec),
            "best_vec_named": dict(zip(NAMES, global_best_vec)),
            "best_fitness": global_best_fit,
            "best_death_rate": global_best_res["champ_death_rate"],
            "best_death_ci": global_best_res["death_ci"],
            "best_dies_ahead_rate": global_best_res["dies_ahead_rate"],
            "best_pills_to_clear": global_best_res["champ_pills_to_clear"],
            "sigma": sigma, "elapsed_s": time.time() - t0, "n_restarts": n_restarts,
            "train_seeds": [TRAIN_SEEDS[0], TRAIN_SEEDS[-1], len(TRAIN_SEEDS)],
        }, fh, indent=2)


def run(generations=18, lam=6, workers=6, seed=20260806, init_vec=None,
        restart_every=RESTART_EVERY):
    rng = random.Random(seed)
    t0 = time.time()
    get_pool(workers=workers)

    history = []   # every vector ever ACCEPTED as a parent, for novelty
    parent = clamp(init_vec) if init_vec else random_init(rng)
    parent_res = evaluate(TRAIN_SEEDS, OPP_ADV, vec=parent, workers=workers)
    parent_fit = fitness_scalar(parent_res)
    history.append(parent)

    global_best_vec, global_best_fit, global_best_res = parent, parent_fit, parent_res
    n_restarts = 0

    print(f"[gen 0] init {dict(zip(NAMES, parent))} death={parent_res['champ_death_rate']:.3f} "
          f"fit={parent_fit:.2f}", flush=True)
    checkpoint(0, global_best_vec, global_best_fit, global_best_res, 1.0, t0, n_restarts)

    sigma = 1.0
    for g in range(1, generations + 1):
        if g % restart_every == 0:
            parent = random_init(rng)
            parent_res = evaluate(TRAIN_SEEDS, OPP_ADV, vec=parent, workers=workers)
            parent_fit = fitness_scalar(parent_res)
            sigma = 1.0
            n_restarts += 1
            history.append(parent)
            print(f"[gen {g}] RESTART -> {dict(zip(NAMES, parent))} "
                  f"death={parent_res['champ_death_rate']:.3f}", flush=True)

        children = [mutate(parent, sigma, rng) for _ in range(lam)]
        children.append(random_init(rng))
        results = [evaluate(TRAIN_SEEDS, OPP_ADV, vec=c, workers=workers) for c in children]
        fits = [fitness_scalar(r) for r in results]
        scored = [f + NOVELTY_WEIGHT * novelty(c, history) for f, c in zip(fits, children)]
        best_i = max(range(len(children)), key=lambda i: scored[i])
        success = fits[best_i] > parent_fit    # acceptance is on RAW fitness, novelty only orders ties
        if success:
            parent, parent_fit, parent_res = children[best_i], fits[best_i], results[best_i]
            history.append(parent)
            sigma = min(sigma * 1.5, 4.0)
        else:
            sigma = max(sigma * 0.85, 0.15)

        if parent_fit > global_best_fit:
            global_best_vec, global_best_fit, global_best_res = parent, parent_fit, parent_res

        print(f"[gen {g}] best-child death={results[best_i]['champ_death_rate']:.3f} "
              f"fit={fits[best_i]:.2f} novelty_bonus={scored[best_i]-fits[best_i]:.2f} "
              f"{'(ACCEPTED)' if success else '(rejected)'} sigma={sigma:.2f} "
              f"global_best_death={global_best_res['champ_death_rate']:.3f}", flush=True)
        log_line({"gen": g, "children": [list(c) for c in children], "fitness": fits,
                  "accepted": success, "parent_vec": list(parent),
                  "global_best_vec": list(global_best_vec),
                  "global_best_fitness": global_best_fit, "sigma": sigma,
                  "n_restarts": n_restarts, "elapsed_s": time.time() - t0})
        checkpoint(g, global_best_vec, global_best_fit, global_best_res, sigma, t0, n_restarts)

    shutdown_pool()
    print(f"DONE in {time.time()-t0:.0f}s, {n_restarts} restarts. Global best: "
          f"{dict(zip(NAMES, global_best_vec))} death_rate="
          f"{global_best_res['champ_death_rate']:.3f} CI={global_best_res['death_ci']}",
          flush=True)
    return global_best_vec, global_best_res


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=18)
    ap.add_argument("--lam", type=int, default=6)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20260807)
    ap.add_argument("--restart-every", type=int, default=RESTART_EVERY)
    a = ap.parse_args()
    if os.path.exists(LOG):
        os.remove(LOG)
    run(generations=a.generations, lam=a.lam, workers=a.workers, seed=a.seed,
        restart_every=a.restart_every)
