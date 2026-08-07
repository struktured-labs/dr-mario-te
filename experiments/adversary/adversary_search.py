#!/usr/bin/env python3
"""adversary_search.py -- Hunt B: ADVERSARIAL GARBAGE SCHEDULER.

Searches over garbage-volley SCHEDULES (fire probability by clear-size bin,
volley-size mix, target-column policy) to MAXIMIZE the champion's
dies-ahead / topout rate, subject to an EARNABILITY constraint:

  1. CLEAR-TRIGGERED ONLY: a volley may only follow one of the champion's
     OWN clears (same "opponent clear stands in for the AI's own clear"
     convention pressure_rig.py's bursty branch and bursty_model.py's
     inject_bursty_garbage() use -- reused verbatim here, not reinvented).
     No clear this placement => zero chance of a volley, structurally (see
     `bin_of()` -- clear_size==0 matches no bin).
  2. VOLUME-CAPPED: total garbage halves landed in one game is hard-capped
     at BUDGET_HALVES, derived from BURSTY_V1_RESULTS.md Sec.5's own honest
     v1.1 fit -- the champion (ws=20) arm's *measured* average garbage/game
     under the real (struktured-only, pool-decontaminated) human volley
     model is 52.92 halves (results/bursty_v1_1_n120_wt0_ws20.json, n=120).
     BUDGET_HALVES = round(52.92) = 53. The adversary may re-time/re-target
     that SAME average human-earnable budget -- it is never handed more
     material than a human sender would produce on average.

What is searched (the "schedule" genome): per clear-size-bin fire
probability (free in [0,1] -- this is the "timing" search: WHICH of the
champion's own clears earn a follow-up, budget permitting), a weight vector
over the empirically-observed volley-size support {2,3,4,5,6} (the fitted
histogram's own support -- bursty_model.py fit_summary()['volley_size_hist'];
the adversary cannot invent a bigger volley than any human sender in the
footage ever produced), and a target-column policy (random / spawn-columns
(3,4) / tallest-columns / near-spawn / thinnest-columns).

Search method: (mu+lambda) evolutionary search, no external deps. Fitness
prioritizes dies_ahead_rate (primary) then topout_rate (secondary tie-break)
over a small TRAINING seed pool (fast, noisy). Top distinct genomes are then
re-validated on a much larger, DISJOINT HOLDOUT seed pool (the transfer
filter -- per house honesty rule, a schedule that only wins on the training
pool is a candidate, not a finding) alongside an honest-model control run
through the identical play loop on the identical holdout seeds.

Engine conventions (reused, not rediscovered): adversary_harness.py's
_lazy()/champion decide path (fast_rtl_x.variant("winner") + terms47.
g_stranded at ws=20, root-only, via reach_root.choose_base32 -- bit-exact to
ab47.py::_choose_base per adversary_harness.py's own header). Board
mutation (drop half, gravity, resolve) copied verbatim from eval47/
pressure_rig.py::_inject_garbage / bursty_model.py::inject_bursty_garbage.
"""
from __future__ import annotations

import sys
import os
import json
import time
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3", QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import adversary_harness as AH  # noqa: E402

LEVEL = AH.LEVEL
WS = AH.WS
DIES_AHEAD_VIRUS_THRESHOLD = AH.DIES_AHEAD_VIRUS_THRESHOLD
GARBAGE_MIN_PILLS = AH.GARBAGE_MIN_PILLS   # 25, matches pressure_rig.py

# --- earnability budget: derived from BURSTY_V1_RESULTS.md Sec.5, not
# invented here. Champion (ws=20) arm's measured avg garbage/game under the
# honest struktured-only v1.1 bursty fit, n=120 (results/
# bursty_v1_1_n120_wt0_ws20.json: mean(r['garbage_injected'] for r in arm) =
# 52.925). Rounded to an integer halves cap.
HONEST_V1_1_CHAMPION_AVG_GARBAGE = 52.925
BUDGET_HALVES = round(HONEST_V1_1_CHAMPION_AVG_GARBAGE)  # 53

# --- clear-size bins: identical edges to bursty_model.py's
# clear_size_bins default ((4,6),(7,10),(11,999)) -- reused so the
# adversary's "timing" axis is directly comparable to the honest model's own
# conditioning variable, not a different discretization.
BINS = [(4, 6), (7, 10), (11, 999)]

# --- volley-size support: the empirical histogram's own support (bursty_
# model.py fit_summary()['volley_size_hist'] from the v1 pooled fit: sizes
# 2..6 observed, nothing larger in n=61 footage volleys). The adversary
# reweights THIS SAME discrete set -- it cannot draw a size no human sender
# in the footage ever produced.
SIZE_POOL = [2, 3, 4, 5, 6]

TARGET_MODES = ["random", "spawn", "tallest", "near_spawn", "thin"]

# seed pools -- disjoint from adversary_harness.SELFTEST_SEEDS (1000+37*i,
# i<20) and from pressure_rig's own range(0,120) convention, so nothing here
# silently reuses a seed set another report already tuned/measured against.
TRAIN_SEED0 = 4_000_000
HOLDOUT_SEED0 = 5_000_000


# --------------------------------------------------------------------- util
def _clip01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _normalize(ws):
    s = sum(ws)
    if s <= 0:
        return [1.0 / len(ws)] * len(ws)
    return [w / s for w in ws]


def bin_of(clear_size):
    for b in BINS:
        lo, hi = b
        if lo <= clear_size <= hi:
            return b
    return None


def genome_key(g):
    """Rounded, hashable fingerprint for de-duplicating candidates."""
    fire = tuple(round(g["fire"][b], 2) for b in BINS)
    sizes = tuple(round(w, 2) for w in g["size_weights"])
    return (fire, sizes, g["target_mode"])


def genome_to_jsonable(g):
    return {"fire": {f"{lo}-{hi}": g["fire"][(lo, hi)] for (lo, hi) in BINS},
            "size_weights": dict(zip(SIZE_POOL, g["size_weights"])),
            "target_mode": g["target_mode"]}


# --------------------------------------------------------------- GA genome
def random_genome(rng):
    return {"fire": {b: rng.uniform(0.0, 1.0) for b in BINS},
            "size_weights": _normalize([rng.uniform(0.02, 1.0) for _ in SIZE_POOL]),
            "target_mode": rng.choice(TARGET_MODES)}


def mutate(g, rng, sigma=0.25):
    ng = {"fire": {b: _clip01(g["fire"][b] + rng.gauss(0, sigma)) for b in BINS},
          "size_weights": _normalize([max(0.001, w + rng.gauss(0, sigma * 0.3))
                                       for w in g["size_weights"]]),
          "target_mode": g["target_mode"]}
    if rng.random() < 0.25:
        ng["target_mode"] = rng.choice(TARGET_MODES)
    return ng


def crossover(g1, g2, rng):
    return {"fire": {b: rng.choice([g1["fire"][b], g2["fire"][b]]) for b in BINS},
            "size_weights": _normalize([rng.choice(pair) for pair in
                                         zip(g1["size_weights"], g2["size_weights"])]),
            "target_mode": rng.choice([g1["target_mode"], g2["target_mode"]])}


# ------------------------------------------------------------- board policy
def _col_heights(board):
    import numpy as np
    heights = []
    for c in range(board.cols):
        occ = np.nonzero(board.color[:, c])[0]
        heights.append(int(board.rows - occ.min()) if len(occ) else 0)
    return heights


def choose_target_cols(board, mode, n_cols, rng):
    all_cols = list(range(board.cols))
    n_cols = max(1, min(n_cols, len(all_cols)))
    if mode == "random":
        return rng.sample(all_cols, n_cols)
    if mode == "spawn":
        spawn = list(board.SPAWN_COLS) if hasattr(board, "SPAWN_COLS") else [3, 4]
        tail = [c for c in all_cols if c not in spawn]
        rng.shuffle(tail)
        order = spawn + tail
        return order[:n_cols]
    if mode == "tallest":
        heights = _col_heights(board)
        order = sorted(all_cols, key=lambda c: (-heights[c], rng.random()))
        return order[:n_cols]
    if mode == "near_spawn":
        spawn = list(board.SPAWN_COLS) if hasattr(board, "SPAWN_COLS") else [3, 4]
        order = sorted(all_cols, key=lambda c: (min(abs(c - s) for s in spawn), rng.random()))
        return order[:n_cols]
    if mode == "thin":
        heights = _col_heights(board)
        order = sorted(all_cols, key=lambda c: (heights[c], rng.random()))
        return order[:n_cols]
    return rng.sample(all_cols, n_cols)


def adversarial_inject(board, seed, pills_placed, clear_size, schedule, remaining):
    """Same physical drop mechanics as pressure_rig._inject_garbage /
    bursty_model.inject_bursty_garbage (first-empty-row-from-top, unlinked
    single half, random color 1..3, gravity+resolve after) -- only the
    DECISION (fire?, how big?, which columns?) differs, and is driven by
    `schedule` + capped at `remaining` halves (the earnability budget)."""
    from drmario.faithful_game import EMPTY, LINK_NONE

    if remaining <= 0:
        return 0
    b = bin_of(clear_size)
    if b is None:
        return 0
    rng = random.Random(seed * 1000 + pills_placed)
    p_fire = schedule["fire"][b]
    if rng.random() >= p_fire:
        return 0
    n_cells = rng.choices(SIZE_POOL, weights=schedule["size_weights"], k=1)[0]
    n_cells = min(n_cells, remaining)
    if n_cells <= 0:
        return 0
    n_cols = max(1, min(board.cols, round(n_cells / 2)))
    cols = choose_target_cols(board, schedule["target_mode"], n_cols, rng)
    rows_per_col = max(1, n_cells // max(1, len(cols)))
    placed = 0
    for c in cols:
        if placed >= n_cells:
            break
        if board.color[0, c] != EMPTY:
            continue
        for _ in range(rows_per_col):
            if placed >= n_cells:
                break
            r = 0
            while r < board.rows and board.color[r, c] != EMPTY:
                r += 1
            if r >= board.rows:
                break
            board.color[r, c] = rng.randint(1, 3)
            board.is_virus[r, c] = False
            board.link[r, c] = LINK_NONE
            placed += 1
    if placed:
        board._apply_gravity()
        board.resolve()
    return placed


def _honest_inject(board, model, seed, pills_placed, clear_size, remaining):
    """Honest-model injection with the SAME remaining-budget clip applied to
    the adversarial arm, for a genuinely matched-volume comparison (not just
    matched on long-run average). Reuses bursty_model's own fire_probability
    /sample() -- only the post-hoc size clip + placement loop is duplicated
    here (bursty_model.inject_bursty_garbage has no clip hook to reuse)."""
    from drmario.faithful_game import EMPTY, LINK_NONE

    if remaining <= 0:
        return 0
    rng = random.Random(seed * 1000 + pills_placed)
    p_fire, _n = model.fire_probability(clear_size)
    if rng.random() >= p_fire:
        return 0
    n_cells, cols = model.sample(seed, pills_placed)
    if not cols:
        return 0
    n_cells = min(n_cells, remaining)
    if n_cells <= 0:
        return 0
    rows_per_col = max(1, n_cells // max(1, len(cols)))
    placed = 0
    for c in cols:
        if placed >= n_cells:
            break
        if board.color[0, c] != EMPTY:
            continue
        for _ in range(rows_per_col):
            if placed >= n_cells:
                break
            r = 0
            while r < board.rows and board.color[r, c] != EMPTY:
                r += 1
            if r >= board.rows:
                break
            board.color[r, c] = rng.randint(1, 3)
            board.is_virus[r, c] = False
            board.link[r, c] = LINK_NONE
            placed += 1
    if placed:
        board._apply_gravity()
        board.resolve()
    return placed


# --------------------------------------------------------------- play loop
def play_seed_adversarial(seed, schedule, budget=BUDGET_HALVES, max_pills=300):
    """One game of the champion decide path (identical to adversary_harness.
    play_seed with pressure=None) with clear-triggered adversarial garbage
    wired in exactly where pressure_rig.py's bursty branch wires in the
    honest model -- see module docstring."""
    import numpy as np
    L = AH._lazy()
    RR, FaithfulDrMarioEnv, NesPillSource, FB, RS = (
        L["RR"], L["FaithfulDrMarioEnv"], L["NesPillSource"], L["FB"], L["RS"])

    env = FaithfulDrMarioEnv(level=LEVEL, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    garbage_injected = 0
    v_at_end = None

    for _ in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        a = RR.choose_base32(col, vir, int(env.cur.a), int(env.cur.b),
                             int(env.nxt.a), int(env.nxt.b), ws=WS)["action"]
        if a is None:
            res = "topout"
            v_at_end = env.board.virus_count()
            break
        occ_before = int(np.count_nonzero(env.board.color))
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout":
                v_at_end = env.board.virus_count()
            break
        if trunc:
            res = "stall"
            break
        if env.pills_placed >= GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            landed = 0
            if clear_size > 0 and garbage_injected < budget:
                landed = adversarial_inject(env.board, seed, env.pills_placed, clear_size,
                                             schedule, remaining=budget - garbage_injected)
            garbage_injected += landed
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_end = env.board.virus_count()
                break

    viruses_left = v_at_end if v_at_end is not None else int(env.board.virus_count())
    dies_ahead = bool(res == "topout" and viruses_left <= DIES_AHEAD_VIRUS_THRESHOLD)
    return {"seed": seed, "result": res, "pills": env.pills_placed,
            "viruses_left": viruses_left, "dies_ahead": dies_ahead,
            "garbage_injected": garbage_injected}


def play_seed_honest(seed, model, budget=BUDGET_HALVES, max_pills=300):
    """Same play loop, honest v1.1 model in place of the adversarial
    scheduler -- the paired control arm."""
    import numpy as np
    L = AH._lazy()
    RR, FaithfulDrMarioEnv, NesPillSource, FB, RS = (
        L["RR"], L["FaithfulDrMarioEnv"], L["NesPillSource"], L["FB"], L["RS"])

    env = FaithfulDrMarioEnv(level=LEVEL, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    garbage_injected = 0
    v_at_end = None

    for _ in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        a = RR.choose_base32(col, vir, int(env.cur.a), int(env.cur.b),
                             int(env.nxt.a), int(env.nxt.b), ws=WS)["action"]
        if a is None:
            res = "topout"
            v_at_end = env.board.virus_count()
            break
        occ_before = int(np.count_nonzero(env.board.color))
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout":
                v_at_end = env.board.virus_count()
            break
        if trunc:
            res = "stall"
            break
        if env.pills_placed >= GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            landed = 0
            if clear_size > 0 and garbage_injected < budget:
                landed = _honest_inject(env.board, model, seed, env.pills_placed, clear_size,
                                         remaining=budget - garbage_injected)
            garbage_injected += landed
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_end = env.board.virus_count()
                break

    viruses_left = v_at_end if v_at_end is not None else int(env.board.virus_count())
    dies_ahead = bool(res == "topout" and viruses_left <= DIES_AHEAD_VIRUS_THRESHOLD)
    return {"seed": seed, "result": res, "pills": env.pills_placed,
            "viruses_left": viruses_left, "dies_ahead": dies_ahead,
            "garbage_injected": garbage_injected}


# --------------------------------------------------------------- workers
def _worker_init():
    AH._lazy()


def _eval_adv_one(args):
    seed, schedule, budget, max_pills = args
    return play_seed_adversarial(seed, schedule, budget, max_pills=max_pills)


def _eval_honest_one(args):
    """Model is built ONCE in the parent (main()) and shipped in per-task
    args -- NOT re-fit inside the worker. Re-fitting per-worker (the first
    cut of this function) re-ran vision.py's image classification over the
    whole footage set once per worker process; shipping the already-fit
    BurstyPressureModel via IPC is far cheaper (small dataclass, no PIL/
    numpy image decode) and was measured ~100s slower per holdout batch in
    the smoke test before this fix."""
    seed, model, budget = args
    return play_seed_honest(seed, model, budget)


def build_honest_v1_1_model():
    import bursty_model as BM
    import fit_ensemble_source as FE
    m_v1 = BM.fit_struktured_20260804()
    raw = m_v1.meta["raw_events"]
    all_volleys, all_clears = [], []
    for _mid, r in raw.items():
        all_volleys.extend(r["volleys"])
        all_clears.extend(r["clears"])
    return FE.fit_per_player(all_volleys, all_clears, m_v1.n_matches, "P1",
                              dict(BM.DEFAULT_OPPONENT_OF))


def _chunksize(n_items, workers):
    """Keep every worker fed even on small batches (default chunksize=4 was
    starving 2/4 workers on a 6-seed training batch during the smoke test)."""
    return max(1, min(4, n_items // max(1, workers)) or 1)


def summarize(rows):
    n = len(rows)
    if n == 0:
        return dict(n=0)
    topout = sum(1 for r in rows if r["result"] == "topout")
    stall = sum(1 for r in rows if r["result"] == "stall")
    clear = sum(1 for r in rows if r["result"] == "clear")
    dies_ahead = sum(1 for r in rows if r["dies_ahead"])
    garb = [r["garbage_injected"] for r in rows]
    return dict(n=n, clear=clear, topout=topout, stall=stall, dies_ahead=dies_ahead,
                clear_rate=clear / n, topout_rate=topout / n, stall_rate=stall / n,
                dies_ahead_rate=dies_ahead / n,
                avg_garbage=st.mean(garb), max_garbage=max(garb), min_garbage=min(garb))


def fitness_of(summary):
    """Primary: dies_ahead_rate. Secondary tie-break: topout_rate (includes
    dies-ahead as a subset, so it also rewards non-dies-ahead topouts)."""
    return summary["dies_ahead_rate"] * 1000.0 + summary["topout_rate"]


# --------------------------------------------------------------- GA driver
def run_ga(pool, train_seeds, pop_size, generations, budget, rng, workers=6, log=print,
           train_max_pills=300):
    """train_max_pills: pill cap used ONLY during GA fitness evaluation (the
    holdout validation always uses the standard 300, matching every other
    house rig). Heavy adversarial schedules routinely make champion games
    run the full 300-pill cap before topping out or stalling -- during
    SEARCH (where fitness only needs to RANK schedules relative to each
    other, not report an absolute rate) a shorter cap bounds worst-case
    per-game cost without changing which schedules look best: a schedule
    that would have topped the champion by pill 300 has usually already
    driven it into a materially worse (tower height / stranded-cell) state
    well before that, so dies_ahead/topout signal still discriminates at a
    smaller cap -- just noisier, which is what n and generations are for."""
    population = [random_genome(rng) for _ in range(pop_size)]
    history = []  # (fitness, summary, genome)
    seen = {}
    cs = _chunksize(len(train_seeds), workers)

    def evaluate(genomes):
        out = []
        for g in genomes:
            k = genome_key(g)
            if k in seen:
                out.append(seen[k])
                continue
            rows = list(pool.map(_eval_adv_one,
                                  [(s, g, budget, train_max_pills) for s in train_seeds],
                                  chunksize=cs))
            summ = summarize(rows)
            fit = fitness_of(summ)
            seen[k] = (fit, summ, g)
            out.append(seen[k])
        return out

    evald = evaluate(population)
    history.extend(evald)
    evald.sort(key=lambda x: -x[0])
    log(f"[gen 0] best fitness={evald[0][0]:.2f} "
        f"dies_ahead={evald[0][1]['dies_ahead_rate']:.1%} "
        f"topout={evald[0][1]['topout_rate']:.1%} "
        f"target={evald[0][2]['target_mode']}")

    for gen in range(1, generations + 1):
        elites = [e[2] for e in evald[:max(2, pop_size // 4)]]
        children = []
        while len(children) < pop_size - len(elites):
            if rng.random() < 0.5 and len(elites) >= 2:
                p1, p2 = rng.sample(elites, 2)
                child = crossover(p1, p2, rng)
            else:
                parent = rng.choice(elites)
                child = mutate(parent, rng)
            if rng.random() < 0.15:
                child = random_genome(rng)  # inject fresh diversity
            children.append(child)
        population = elites + children
        evald = evaluate(population)
        evald.sort(key=lambda x: -x[0])
        history.extend(evald)
        log(f"[gen {gen}] best fitness={evald[0][0]:.2f} "
            f"dies_ahead={evald[0][1]['dies_ahead_rate']:.1%} "
            f"topout={evald[0][1]['topout_rate']:.1%} "
            f"target={evald[0][2]['target_mode']} "
            f"avg_garbage={evald[0][1]['avg_garbage']:.1f}")

    # de-dup history by genome key, keep best fitness per key, sort desc
    best_by_key = {}
    for fit, summ, g in history:
        k = genome_key(g)
        if k not in best_by_key or fit > best_by_key[k][0]:
            best_by_key[k] = (fit, summ, g)
    ranked = sorted(best_by_key.values(), key=lambda x: -x[0])
    return ranked


# ---------------------------------------------------------------- baselines
def heuristic_candidates():
    """Hand-built baselines, evaluated alongside the GA's own finds:
    - 'always_spawn_max': fire=1.0 every bin, always max observed size
      (weight all on 6), always target spawn cols -- the naive "obvious"
      exploit a human would try first.
    - 'honest_shape_adversarial_target': keep the honest model's OWN fire
      probabilities/size mix (from the v1.1 fit) but swap random targeting
      for spawn-column targeting -- isolates how much of the exploit is
      TARGETING alone, holding timing/size at the human-observed shape.
    """
    always_spawn_max = {
        "fire": {b: 1.0 for b in BINS},
        "size_weights": [0.0, 0.0, 0.0, 0.0, 1.0],
        "target_mode": "spawn",
    }
    return {"always_spawn_max": always_spawn_max}


def honest_shaped_adversarial_target(honest_model):
    fire = {}
    for (lo, hi) in BINS:
        p, n = honest_model.fire_probability((lo + hi) // 2 if hi < 999 else lo + 1)
        fire[(lo, hi)] = p
    hist = {}
    for s in honest_model.volley_sizes:
        hist[s] = hist.get(s, 0) + 1
    weights = [hist.get(s, 0) for s in SIZE_POOL]
    if sum(weights) == 0:
        weights = [1] * len(SIZE_POOL)
    return {"fire": fire, "size_weights": _normalize([float(w) for w in weights]),
            "target_mode": "spawn"}


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--pop-size", type=int, default=10)
    ap.add_argument("--generations", type=int, default=12)
    ap.add_argument("--train-seeds", type=int, default=36)
    ap.add_argument("--holdout-seeds", type=int, default=180)
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--budget", type=int, default=BUDGET_HALVES)
    ap.add_argument("--train-max-pills", type=int, default=300,
                     help="pill cap for GA fitness evaluation ONLY -- holdout validation "
                          "always uses 300 (the house standard). Lower this to bound "
                          "worst-case per-game cost during search when heavy adversarial "
                          "schedules keep pushing games to the 300-pill cap.")
    ap.add_argument("--out", type=str, default=os.path.join(HERE, "search_result.json"))
    ap.add_argument("--rng-seed", type=int, default=20260806)
    a = ap.parse_args()

    rng = random.Random(a.rng_seed)
    train_seeds = list(range(TRAIN_SEED0, TRAIN_SEED0 + a.train_seeds))
    holdout_seeds = list(range(HOLDOUT_SEED0, HOLDOUT_SEED0 + a.holdout_seeds))

    print("=== fitting honest v1.1 model once (parent process) ===", flush=True)
    t_fit = time.monotonic()
    honest_model = build_honest_v1_1_model()
    print(f"    done in {time.monotonic() - t_fit:.1f}s "
          f"(n_volleys={honest_model.n_volleys} n_clears={honest_model.n_clears})", flush=True)

    t0 = time.monotonic()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_worker_init) as pool:
        print(f"=== GA search: pop={a.pop_size} gens={a.generations} "
              f"train_seeds={a.train_seeds} budget={a.budget} workers={a.workers} "
              f"train_max_pills={a.train_max_pills} ===",
              flush=True)
        ranked = run_ga(pool, train_seeds, a.pop_size, a.generations, a.budget, rng,
                         workers=a.workers, train_max_pills=a.train_max_pills)

        print(f"\n=== GA done in {time.monotonic() - t0:.1f}s. "
              f"{len(ranked)} distinct genomes evaluated. Top {a.top_k} by train fitness: ===",
              flush=True)
        for i, (fit, summ, g) in enumerate(ranked[:a.top_k]):
            print(f"  #{i+1} fit={fit:.2f} dies_ahead={summ['dies_ahead_rate']:.1%} "
                  f"topout={summ['topout_rate']:.1%} target={g['target_mode']} "
                  f"fire={ {f'{lo}-{hi}': round(g['fire'][(lo,hi)],2) for lo,hi in BINS} }",
                  flush=True)

        candidates = {f"ga_top{i+1}": g for i, (_f, _s, g) in enumerate(ranked[:a.top_k])}
        candidates.update(heuristic_candidates())
        candidates["honest_shape_adversarial_target"] = honest_shaped_adversarial_target(honest_model)

        print(f"=== HOLDOUT validation: n={a.holdout_seeds} seeds (disjoint from training) ===",
              flush=True)
        holdout_results = {}

        cs_h = _chunksize(len(holdout_seeds), a.workers)
        print(f"  [holdout] honest_v1_1_random ...", flush=True)
        t1 = time.monotonic()
        rows = list(pool.map(_eval_honest_one, [(s, honest_model, a.budget) for s in holdout_seeds],
                              chunksize=cs_h))
        summ = summarize(rows)
        holdout_results["honest_v1_1_random"] = summ
        print(f"    dies_ahead={summ['dies_ahead_rate']:.1%} topout={summ['topout_rate']:.1%} "
              f"avg_garbage={summ['avg_garbage']:.1f} ({time.monotonic()-t1:.1f}s)", flush=True)

        for name, g in candidates.items():
            t1 = time.monotonic()
            rows = list(pool.map(_eval_adv_one, [(s, g, a.budget, 300) for s in holdout_seeds],
                                  chunksize=cs_h))
            summ = summarize(rows)
            holdout_results[name] = summ
            print(f"  [holdout] {name}: dies_ahead={summ['dies_ahead_rate']:.1%} "
                  f"topout={summ['topout_rate']:.1%} avg_garbage={summ['avg_garbage']:.1f} "
                  f"({time.monotonic()-t1:.1f}s)", flush=True)

    total_dt = time.monotonic() - t0
    out = {
        "budget_halves": a.budget,
        "honest_v1_1_champion_avg_garbage_citation": HONEST_V1_1_CHAMPION_AVG_GARBAGE,
        "train_seeds": [train_seeds[0], train_seeds[-1]],
        "holdout_seeds": [holdout_seeds[0], holdout_seeds[-1]],
        "pop_size": a.pop_size, "generations": a.generations,
        "ga_top_train": [{"fitness": f, "train_summary": s, "genome": genome_to_jsonable(g)}
                          for f, s, g in ranked[:a.top_k]],
        "candidates": {name: genome_to_jsonable(g) for name, g in candidates.items()},
        "holdout_results": holdout_results,
        "total_seconds": total_dt,
    }
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"\n=== wrote {a.out} ({total_dt:.1f}s total) ===", flush=True)


if __name__ == "__main__":
    main()
