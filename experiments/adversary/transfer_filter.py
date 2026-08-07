#!/usr/bin/env python3
"""transfer_filter.py -- TRANSFER FILTER for Hunt A/B candidate exploits.

Separates STRUCTURAL failures (survive perturbation) from FLUKES (don't),
per task instructions:
  Seeds:     (a) neighbouring seeds (fresh, disjoint from the n=120 holdout
                 the candidate was found/validated on)
             (b) the SAME seed with the fatal board's pill history shifted
                 by one pill -- implemented via nes_pills.NesPillSource's
                 own `skip` parameter (skip=2 instead of the default skip=1
                 "the ROM burns one before play") -- same 16-bit seed state,
                 every subsequent pill draw shifted one slot in the same
                 128-length sequence. Applied only to seeds that were
                 actually fatal (dies_ahead or topout) for that candidate.
  Schedules: (c) timing jitter -- the fire/size/column RNG draw for each
                 volley event is anchored at `pills_placed + j` instead of
                 `pills_placed`, j in {-1,+1} drawn per-event from an
                 independent small RNG seeded off (seed, pills_placed) --
                 simulates the adversary's decision clock being off by one
                 pill.
             (d) column jitter -- each chosen target column shifted by
                 j in {-1,+1} (clipped to the board), j drawn per-event from
                 the schedule's own event RNG (extra draw, appended after
                 the unperturbed draws so it never changes what the
                 unperturbed run would have drawn).
             (e) volley-size jitter -- n_cells shifted by j in {-1,+1}
                 (floor 1, still capped at remaining budget), same per-event
                 draw convention as (d).

A candidate is STRUCTURAL if it survives a MAJORITY (>=3/5) of these five
perturbation categories; FLUKE otherwise. "Survives" a category = the
candidate's primary metric (dies_ahead_rate for the three dies-ahead
exploits; topout_rate for always_spawn_max, which the source report itself
frames as the topout lever, not a dies-ahead one) remains far above the
LOCAL honest-baseline rate measured on the SAME seed set for that category
-- specifically: the perturbed rate's 95% CI lower bound still clears the
honest baseline's 95% CI upper bound measured on a matched seed pool. Ties
(overlapping CIs) count as NOT surviving that category (conservative).

Also runs the PREDECESSOR decide path (ws=0 -- winner weights WITHOUT the
ws=20 g_stranded root-only term, i.e. reach_root.choose_base32(..., ws=0),
the pre-#47 shipped config) against every candidate found STRUCTURAL, on a
fresh seed pool, honest-baseline-paired the same way, to tell a long-standing
weakness (kills both configs) from a strand20-introduced regression (kills
only ws=20).

All numbers here are genuinely re-run, not estimated -- see RESULTS_JSON.
"""
from __future__ import annotations

import sys
import os
import json
import time
import random
import argparse
import math
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
import adversary_search as AS   # noqa: E402

LEVEL = AH.LEVEL
WS_CHAMPION = AH.WS               # 20 -- strand20 champion
WS_PREDECESSOR = 0                # pre-#47 shipped config: wt=0, ws=0
DIES_AHEAD_VIRUS_THRESHOLD = AH.DIES_AHEAD_VIRUS_THRESHOLD
GARBAGE_MIN_PILLS = AH.GARBAGE_MIN_PILLS
BUDGET_HALVES = AS.BUDGET_HALVES

# --- candidate genomes, verbatim from validate_only.py / best_schedules.json
GA_NEAR_SPAWN_A = {
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
    "fire": {b: 1.0 for b in AS.BINS},
    "size_weights": [0.0, 0.0, 0.0, 0.0, 1.0],
    "target_mode": "spawn",
}
HONEST_SHAPE_SPAWN = {
    "fire": {(4, 6): 0.28169014084507044, (7, 10): 0.625, (11, 999): 0.5},
    "size_weights": [0.6428571428571429, 0.14285714285714285, 0.14285714285714285,
                      0.03571428571428571, 0.03571428571428571],
    "target_mode": "spawn",
}

CANDIDATES = {
    "ga_near_spawn_a": (GA_NEAR_SPAWN_A, "dies_ahead"),
    "ga_near_spawn_b": (GA_NEAR_SPAWN_B, "dies_ahead"),
    "honest_shape_spawn_target": (HONEST_SHAPE_SPAWN, "dies_ahead"),
    "always_spawn_max": (ALWAYS_SPAWN_MAX, "topout"),
}

# seed pools -- disjoint from GA training (4,000,000+) and from the original
# n=120 holdout (5,000,000-5,000,119) used to find/validate these candidates.
ORIG_HOLDOUT0 = AS.HOLDOUT_SEED0          # 5_000_000
NEIGHBOR_SEED0 = 5_000_200                # fresh, disjoint, immediately adjacent block
PREDECESSOR_SEED0 = 5_000_400             # fresh block for the predecessor A/B

N_BASELINE_CAPTURE = 40   # first N of the original holdout, re-run w/ per-seed capture
N_NEIGHBOR = 40
N_JITTER = 40
N_PREDECESSOR = 60
MAX_HISTORY_SHIFT_SEEDS = 15


# ------------------------------------------------------------ perturbed inject
def adversarial_inject_perturbed(board, seed, pills_placed, clear_size, schedule, remaining,
                                  col_jitter=False, size_jitter=False, timing_jitter=False):
    from drmario.faithful_game import EMPTY, LINK_NONE

    if remaining <= 0:
        return 0
    b = AS.bin_of(clear_size)
    if b is None:
        return 0

    t_off = 0
    if timing_jitter:
        pre_rng = random.Random((seed * 7919 + pills_placed * 131) & 0xFFFFFFFF)
        t_off = pre_rng.choice([-1, 1])

    rng = random.Random(seed * 1000 + pills_placed + t_off)
    p_fire = schedule["fire"][b]
    if rng.random() >= p_fire:
        return 0
    n_cells = rng.choices(AS.SIZE_POOL, weights=schedule["size_weights"], k=1)[0]

    if size_jitter:
        j = rng.choice([-1, 1])
        n_cells = max(1, n_cells + j)

    n_cells = min(n_cells, remaining)
    if n_cells <= 0:
        return 0
    n_cols = max(1, min(board.cols, round(n_cells / 2)))
    cols = AS.choose_target_cols(board, schedule["target_mode"], n_cols, rng)

    if col_jitter:
        j = rng.choice([-1, 1])
        cols = [max(0, min(board.cols - 1, c + j)) for c in cols]

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


def play_seed_adversarial_perturbed(seed, schedule, budget=BUDGET_HALVES, max_pills=300,
                                     ws=WS_CHAMPION, pill_skip=1,
                                     col_jitter=False, size_jitter=False, timing_jitter=False):
    import numpy as np
    L = AH._lazy()
    RR, FaithfulDrMarioEnv, NesPillSource, FB, RS = (
        L["RR"], L["FaithfulDrMarioEnv"], L["NesPillSource"], L["FB"], L["RS"])

    env = FaithfulDrMarioEnv(level=LEVEL, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed, skip=pill_skip).attach(env)
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
                             int(env.nxt.a), int(env.nxt.b), ws=ws)["action"]
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
                landed = adversarial_inject_perturbed(
                    env.board, seed, env.pills_placed, clear_size, schedule,
                    remaining=budget - garbage_injected,
                    col_jitter=col_jitter, size_jitter=size_jitter, timing_jitter=timing_jitter)
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


def play_seed_honest_perturbed(seed, model, budget=BUDGET_HALVES, max_pills=300,
                                ws=WS_CHAMPION, pill_skip=1):
    """Honest-model control, parameterized on ws + pill_skip only (no
    schedule jitter -- honest baseline is the reference line, not a
    candidate under test)."""
    import numpy as np
    L = AH._lazy()
    RR, FaithfulDrMarioEnv, NesPillSource, FB, RS = (
        L["RR"], L["FaithfulDrMarioEnv"], L["NesPillSource"], L["FB"], L["RS"])

    env = FaithfulDrMarioEnv(level=LEVEL, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed, skip=pill_skip).attach(env)
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
                             int(env.nxt.a), int(env.nxt.b), ws=ws)["action"]
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
                landed = AS._honest_inject(env.board, model, seed, env.pills_placed, clear_size,
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


# --------------------------------------------------------------------- stats
def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def rate_and_ci(rows, metric):
    n = len(rows)
    k = sum(1 for r in rows if r[metric]) if metric != "topout" else \
        sum(1 for r in rows if r["result"] == "topout")
    lo, hi = wilson_ci(k, n)
    return {"n": n, "k": k, "rate": k / n if n else 0.0, "ci95": [lo, hi]}


def metric_key(rows, metric):
    if metric == "dies_ahead":
        return sum(1 for r in rows if r["dies_ahead"])
    return sum(1 for r in rows if r["result"] == "topout")


def survives(cand_stat, honest_stat):
    """CI-separation rule: candidate's CI lower bound clears honest's CI
    upper bound. Ties (overlap) do NOT survive -- conservative by design."""
    return cand_stat["ci95"][0] > honest_stat["ci95"][1]


# --------------------------------------------------------------------- workers
def _worker_init():
    AH._lazy()


def _job(args):
    kind = args[0]
    if kind == "adv":
        _, seed, schedule, budget, max_pills, ws, pill_skip, cj, sj, tj = args
        return play_seed_adversarial_perturbed(seed, schedule, budget, max_pills,
                                                ws=ws, pill_skip=pill_skip,
                                                col_jitter=cj, size_jitter=sj, timing_jitter=tj)
    else:  # honest
        _, seed, model, budget, max_pills, ws, pill_skip = args
        return play_seed_honest_perturbed(seed, model, budget, max_pills, ws=ws, pill_skip=pill_skip)


def run_batch(pool, jobs):
    cs = AS._chunksize(len(jobs), 6)
    return list(pool.map(_job, jobs, chunksize=cs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=str, default=os.path.join(HERE, "transfer_filter_result.json"))
    a = ap.parse_args()

    t_start = time.monotonic()
    print("=== fitting honest v1.1 model once (parent process) ===", flush=True)
    honest_model = AS.build_honest_v1_1_model()
    print(f"    done (n_volleys={honest_model.n_volleys} n_clears={honest_model.n_clears})",
          flush=True)

    out = {"candidates": {}, "meta": {
        "n_baseline_capture": N_BASELINE_CAPTURE, "n_neighbor": N_NEIGHBOR,
        "n_jitter": N_JITTER, "n_predecessor": N_PREDECESSOR,
        "max_history_shift_seeds": MAX_HISTORY_SHIFT_SEEDS,
        "orig_holdout0": ORIG_HOLDOUT0, "neighbor_seed0": NEIGHBOR_SEED0,
        "predecessor_seed0": PREDECESSOR_SEED0,
    }}

    with ProcessPoolExecutor(max_workers=a.workers, initializer=_worker_init) as pool:

        # ---- shared honest-baseline reference pools (ws=champion) --------
        base_seeds = list(range(ORIG_HOLDOUT0, ORIG_HOLDOUT0 + N_BASELINE_CAPTURE))
        neigh_seeds = list(range(NEIGHBOR_SEED0, NEIGHBOR_SEED0 + N_NEIGHBOR))
        jitter_seeds = base_seeds  # reuse baseline-capture seeds for apples-to-apples jitter compare

        print("=== honest baseline: base_seeds (n=%d) ===" % len(base_seeds), flush=True)
        honest_base_rows = run_batch(pool, [("hon", s, honest_model, BUDGET_HALVES, 300,
                                              WS_CHAMPION, 1) for s in base_seeds])
        print("=== honest baseline: neighbor_seeds (n=%d) ===" % len(neigh_seeds), flush=True)
        honest_neigh_rows = run_batch(pool, [("hon", s, honest_model, BUDGET_HALVES, 300,
                                               WS_CHAMPION, 1) for s in neigh_seeds])

        out["honest_baseline"] = {
            "base_seeds": {"dies_ahead": rate_and_ci(honest_base_rows, "dies_ahead"),
                            "topout": rate_and_ci(honest_base_rows, "topout")},
            "neighbor_seeds": {"dies_ahead": rate_and_ci(honest_neigh_rows, "dies_ahead"),
                                "topout": rate_and_ci(honest_neigh_rows, "topout")},
        }

        for name, (schedule, metric) in CANDIDATES.items():
            print(f"\n########## candidate: {name} (primary metric={metric}) ##########",
                  flush=True)
            cand_out = {"metric": metric, "perturbations": {}}

            # (0) baseline capture -- unperturbed, on base_seeds, to identify fatal seeds
            print("  [0] baseline capture (unperturbed, base_seeds)", flush=True)
            rows0 = run_batch(pool, [("adv", s, schedule, BUDGET_HALVES, 300, WS_CHAMPION, 1,
                                       False, False, False) for s in base_seeds])
            stat0 = rate_and_ci(rows0, metric)
            honest0 = out["honest_baseline"]["base_seeds"][metric]
            cand_out["baseline_capture"] = {"stat": stat0, "honest": honest0,
                                             "survives": survives(stat0, honest0)}
            fatal_seeds = [r["seed"] for r in rows0
                           if (r["dies_ahead"] if metric == "dies_ahead" else r["result"] == "topout")]
            print(f"      rate={stat0['rate']:.1%} ci={stat0['ci95']} "
                  f"honest={honest0['rate']:.1%} fatal_seeds_found={len(fatal_seeds)}", flush=True)

            # (a) neighbouring seeds
            print("  [a] neighbouring seeds", flush=True)
            rows_a = run_batch(pool, [("adv", s, schedule, BUDGET_HALVES, 300, WS_CHAMPION, 1,
                                        False, False, False) for s in neigh_seeds])
            stat_a = rate_and_ci(rows_a, metric)
            honest_a = out["honest_baseline"]["neighbor_seeds"][metric]
            surv_a = survives(stat_a, honest_a)
            cand_out["perturbations"]["neighbor_seeds"] = {
                "stat": stat_a, "honest": honest_a, "survives": surv_a}
            print(f"      rate={stat_a['rate']:.1%} ci={stat_a['ci95']} "
                  f"honest={honest_a['rate']:.1%} survives={surv_a}", flush=True)

            # (b) history-shift on fatal seeds only
            hs_seeds = fatal_seeds[:MAX_HISTORY_SHIFT_SEEDS]
            if hs_seeds:
                print(f"  [b] history-shift (skip=2) on {len(hs_seeds)} fatal seeds", flush=True)
                rows_b = run_batch(pool, [("adv", s, schedule, BUDGET_HALVES, 300, WS_CHAMPION, 2,
                                            False, False, False) for s in hs_seeds])
                stat_b = rate_and_ci(rows_b, metric)
                # honest reference for history-shift: same fatal-seed set, honest schedule, skip=2
                rows_b_hon = run_batch(pool, [("hon", s, honest_model, BUDGET_HALVES, 300,
                                                WS_CHAMPION, 2) for s in hs_seeds])
                honest_b = rate_and_ci(rows_b_hon, metric)
                surv_b = survives(stat_b, honest_b)
            else:
                stat_b = {"n": 0, "k": 0, "rate": None, "ci95": None}
                honest_b = {"n": 0, "k": 0, "rate": None, "ci95": None}
                surv_b = False
                print("  [b] history-shift SKIPPED -- zero fatal seeds in baseline capture", flush=True)
            cand_out["perturbations"]["history_shift"] = {
                "stat": stat_b, "honest": honest_b, "survives": surv_b,
                "n_fatal_seeds_available": len(fatal_seeds)}
            if hs_seeds:
                print(f"      rate={stat_b['rate']:.1%} ci={stat_b['ci95']} "
                      f"honest={honest_b['rate']:.1%} survives={surv_b}", flush=True)

            # (c)(d)(e) schedule jitters -- on jitter_seeds (== base_seeds)
            for label, kw in (("timing_jitter", dict(timing_jitter=True)),
                               ("column_jitter", dict(col_jitter=True)),
                               ("size_jitter", dict(size_jitter=True))):
                print(f"  [{label}]", flush=True)
                rows_j = run_batch(pool, [("adv", s, schedule, BUDGET_HALVES, 300, WS_CHAMPION, 1,
                                            kw.get("col_jitter", False), kw.get("size_jitter", False),
                                            kw.get("timing_jitter", False)) for s in jitter_seeds])
                stat_j = rate_and_ci(rows_j, metric)
                honest_j = out["honest_baseline"]["base_seeds"][metric]
                surv_j = survives(stat_j, honest_j)
                cand_out["perturbations"][label] = {
                    "stat": stat_j, "honest": honest_j, "survives": surv_j}
                print(f"      rate={stat_j['rate']:.1%} ci={stat_j['ci95']} "
                      f"honest={honest_j['rate']:.1%} survives={surv_j}", flush=True)

            n_surv = sum(1 for k in ("neighbor_seeds", "history_shift", "timing_jitter",
                                      "column_jitter", "size_jitter")
                         if cand_out["perturbations"][k]["survives"])
            cand_out["n_perturbations_survived"] = n_surv
            cand_out["n_perturbations_total"] = 5
            cand_out["verdict"] = "STRUCTURAL" if n_surv >= 3 else "FLUKE"
            print(f"  ==> {name}: {n_surv}/5 survived -> {cand_out['verdict']}", flush=True)

            out["candidates"][name] = cand_out

        # ---------------------------------------------------- predecessor A/B
        structural = [n for n, c in out["candidates"].items() if c["verdict"] == "STRUCTURAL"]
        print(f"\n########## predecessor (ws=0) A/B on STRUCTURAL candidates: {structural} ##########",
              flush=True)
        pred_seeds = list(range(PREDECESSOR_SEED0, PREDECESSOR_SEED0 + N_PREDECESSOR))
        out["predecessor_ab"] = {"seeds0": PREDECESSOR_SEED0, "n": N_PREDECESSOR, "arms": {}}

        if structural:
            print("  honest baseline @ ws=0", flush=True)
            hon_pred_rows = run_batch(pool, [("hon", s, honest_model, BUDGET_HALVES, 300,
                                               WS_PREDECESSOR, 1) for s in pred_seeds])
            out["predecessor_ab"]["honest_ws0"] = {
                "dies_ahead": rate_and_ci(hon_pred_rows, "dies_ahead"),
                "topout": rate_and_ci(hon_pred_rows, "topout")}

            print("  honest baseline @ ws=20 (same pred_seeds, for a same-seed champion/predecessor pair)",
                  flush=True)
            hon_champ_rows = run_batch(pool, [("hon", s, honest_model, BUDGET_HALVES, 300,
                                                WS_CHAMPION, 1) for s in pred_seeds])
            out["predecessor_ab"]["honest_ws20"] = {
                "dies_ahead": rate_and_ci(hon_champ_rows, "dies_ahead"),
                "topout": rate_and_ci(hon_champ_rows, "topout")}

            for name in structural:
                schedule, metric = CANDIDATES[name]
                print(f"  {name} @ ws=0 (predecessor)", flush=True)
                rows_pred = run_batch(pool, [("adv", s, schedule, BUDGET_HALVES, 300,
                                               WS_PREDECESSOR, 1, False, False, False)
                                              for s in pred_seeds])
                print(f"  {name} @ ws=20 (champion, same pred_seeds, for a clean same-seed pair)",
                      flush=True)
                rows_champ = run_batch(pool, [("adv", s, schedule, BUDGET_HALVES, 300,
                                                WS_CHAMPION, 1, False, False, False)
                                               for s in pred_seeds])
                out["predecessor_ab"]["arms"][name] = {
                    "predecessor_ws0": {"dies_ahead": rate_and_ci(rows_pred, "dies_ahead"),
                                         "topout": rate_and_ci(rows_pred, "topout")},
                    "champion_ws20": {"dies_ahead": rate_and_ci(rows_champ, "dies_ahead"),
                                       "topout": rate_and_ci(rows_champ, "topout")},
                }
                pred_stat = out["predecessor_ab"]["arms"][name]["predecessor_ws0"][metric]
                champ_stat = out["predecessor_ab"]["arms"][name]["champion_ws20"][metric]
                print(f"      predecessor {metric}: {pred_stat['rate']:.1%} {pred_stat['ci95']} | "
                      f"champion(same seeds) {metric}: {champ_stat['rate']:.1%} {champ_stat['ci95']}",
                      flush=True)
        else:
            print("  no STRUCTURAL candidates -- predecessor A/B skipped", flush=True)

    out["total_seconds"] = time.monotonic() - t_start
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"\n=== wrote {a.out} ({out['total_seconds']:.1f}s total) ===", flush=True)


if __name__ == "__main__":
    main()
