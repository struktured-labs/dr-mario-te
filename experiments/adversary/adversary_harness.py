#!/usr/bin/env python3
"""adversary_harness.py -- shared substrate for the adversary-search program.

TARGET (the "champion"): the shipped strand20 decide path -- fast_rtl_x.
variant("winner") leaf + eval47/terms47.g_stranded applied ROOT-ONLY at
ws=20, exactly as eval47/ab47.py::_choose_base(wt=0, ws=20) does it. We do
NOT re-implement that arithmetic here -- eval47/reach_root.py::choose_base32
already reproduces it bit-for-bit (see reach_root.py's own
_selftest_base32_matches_shipped), so this harness imports and calls it.

PILL STREAM: the real NES stream (NesPillSource), not uniform random. The
cart's RNG seed is 16-bit, so the reachable stream space is SEED_SPACE=65536
games (dr-mario-seed-is-deterministic-on-cart: only entropy is frames-held-at
level-select; a fixed `seed` int here reproduces one specific stream exactly).

FAILURE TAXONOMY (house definitions -- do not invent new ones):
  TOPOUT     -- spawn blocked (both spawn cells, cols 3-4, occupied when a new
                pill would spawn). Detected here because choose_base32 finds
                NO legal (variant, col) drop -- identical condition.
  DIES_AHEAD -- TOPOUT while holding <= DIES_AHEAD_VIRUS_THRESHOLD (12)
                viruses -- pressure_rig.py's own constant, reused verbatim.
  STALL      -- 300 pills without a full clear (env truncates at max_pills
                without terminating -- virus_count() still > 0).
  SLOW       -- cleared, but pills-to-clear sits in the worst decile for its
                seed class. This is a POPULATION statistic: play_seed() runs
                ONE game and cannot know its own decile, so SLOW is computed
                post-hoc by classify_slow() over a batch of play_seed()
                results the caller has already decided belong to one class
                (e.g. don't pool clean games with drip-pressure games).

Engine/board conventions (house rules, not rediscovered here): sys.path
header + import order per tuck_v3/union_mirror.py; boards are 128-byte
row-major idx=r*8+c with 1-based colors; o4 {0,1}=VERT {2,3}=HORIZ,
variant = o4 XOR 2 (fast_rtl_x._VAR_OF_O4); action ints returned by
choose_base32 (var*8+cc) plug directly into FaithfulDrMarioEnv.step() --
confirmed by reach_root.py's own selftest driving real trajectories with
them.
"""
from __future__ import annotations

import sys
import os
import random
import time
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3", QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

LEVEL = 11                          # standing L11 target class
WS = 20                             # shipped strand20 dose (reach_root.WS)
DIES_AHEAD_VIRUS_THRESHOLD = 12     # pressure_rig.py's own constant, reused
SEED_SPACE = 65536                  # cart RNG is 16-bit

# drip-pressure defaults, reused verbatim from eval47/pressure_rig.py (not
# reinvented) -- only active when play_seed(..., pressure="drip") is passed.
GARBAGE_MIN_PILLS = 25
GARBAGE_PERIOD = 8
GARBAGE_K = 2

_L = {}


def _lazy():
    """Import + numba-warm the champion decide path exactly once per process.
    Idempotent -- safe as a bare call inside play_seed() or as a
    ProcessPoolExecutor initializer (initializer=_lazy, no args)."""
    if _L:
        return _L
    import reach_root as RR
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS

    RR._lazy()   # warms fast_rtl_x.variant("winner") + jits g_stranded/eh terms
    _L.update(RR=RR, FaithfulDrMarioEnv=FaithfulDrMarioEnv,
              NesPillSource=NesPillSource, FB=FB, RS=RS)
    return _L


def _inject_drip(board, seed, pills_placed, k=GARBAGE_K):
    """pressure_rig.py's drip model, reused verbatim: k unlinked single
    halves dropped into k distinct random columns (columns full to row 0
    skipped silently), then settled. ⚠ board._apply_gravity() BEFORE
    resolve() after injection -- a half parked at row 0 with no match would
    float forever and fake a spawn-block otherwise (pressure_rig.py's own
    warning, reproduced here)."""
    from drmario.faithful_game import EMPTY, LINK_NONE
    rng = random.Random(seed * 1000 + pills_placed)
    cols = rng.sample(range(board.cols), min(k, board.cols))
    placed = 0
    for c in cols:
        color = rng.randint(1, 3)
        if board.color[0, c] != EMPTY:
            continue
        r = 0
        while r < board.rows and board.color[r, c] != EMPTY:
            r += 1
        board.color[r, c] = color
        board.is_virus[r, c] = False
        board.link[r, c] = LINK_NONE
        placed += 1
    if placed:
        board._apply_gravity()
        board.resolve()
    return placed


_PRESSURE_MODELS = {"drip": _inject_drip}


def _snapshot(board):
    """Plain-dict board snapshot (col/vir/lnk, 128-cell row-major) -- fixture
    material, independent of numpy/FaithfulBoard so it round-trips through
    JSON."""
    return {"col": board.color.reshape(-1).astype(int).tolist(),
            "vir": board.is_virus.reshape(-1).astype(int).tolist(),
            "lnk": board.link.reshape(-1).astype(int).tolist()}


def play_seed(seed, pressure=None, max_pills=300):
    """Run ONE game of the champion decide path on the real NES stream for
    `seed`.

    pressure: None (clean, default) | "drip" (eval47/pressure_rig.py's drip
    model, reused verbatim) | a callable(board, seed, pills_placed) ->
    int(halves_placed) for a custom model.

    Returns dict(seed, result, pills, viruses_left, dies_ahead,
    garbage_injected, first_topout_board, trace).
      result            "clear" | "topout" | "stall"
      pills             env.pills_placed at the end
      viruses_left      board.virus_count() at the end
      dies_ahead        result=="topout" and viruses_left<=12
      first_topout_board  board snapshot AT THE FATAL MOMENT (only set for
                        result=="topout"; None otherwise) -- fixture material
      trace             [(pill_index, action_int), ...] for exact replay
    """
    L = _lazy()
    RR, FaithfulDrMarioEnv, NesPillSource, FB, RS = (
        L["RR"], L["FaithfulDrMarioEnv"], L["NesPillSource"], L["FB"], L["RS"])

    pressure_fn = None
    if pressure is not None:
        pressure_fn = _PRESSURE_MODELS[pressure] if isinstance(pressure, str) else pressure

    env = FaithfulDrMarioEnv(level=LEVEL, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    trace = []
    first_topout_board = None
    garbage_injected = 0

    for i in range(max_pills):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        a = RR.choose_base32(col, vir, int(env.cur.a), int(env.cur.b),
                             int(env.nxt.a), int(env.nxt.b), ws=WS)["action"]
        if a is None:
            # every one of the 32 straight drops is illegal -- both spawn
            # cells (cols 3-4) are occupied -- i.e. spawn_blocked().
            res = "topout"
            first_topout_board = _snapshot(env.board)
            break
        trace.append((i, int(a)))
        _, _, term, trunc, info = env.step(int(a))

        if pressure_fn is not None and not term and env.pills_placed >= GARBAGE_MIN_PILLS \
                and env.pills_placed % GARBAGE_PERIOD == 0:
            garbage_injected += pressure_fn(env.board, seed, env.pills_placed)
            if env.board.virus_count() == 0:
                term, info = True, {"won": True}
            elif env.board.spawn_blocked():
                term, info = True, {"won": False}

        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout":
                first_topout_board = _snapshot(env.board)
            break
        if trunc:
            res = "stall"
            break

    viruses_left = int(env.board.virus_count())
    return {"seed": seed, "result": res, "pills": env.pills_placed,
            "viruses_left": viruses_left,
            "dies_ahead": bool(res == "topout" and viruses_left <= DIES_AHEAD_VIRUS_THRESHOLD),
            "garbage_injected": garbage_injected,
            "first_topout_board": first_topout_board, "trace": trace}


def classify_slow(games, decile=0.9):
    """POPULATION classification over a batch the caller has already decided
    is one seed class (e.g. all clean, or all one pressure model -- don't
    pool). Returns the set of seeds whose result=="clear" AND whose `pills`
    is >= the `decile` quantile of pills-to-clear within this batch (default:
    worst 10%). Read-only; does not mutate `games`."""
    clears = sorted(g["pills"] for g in games if g["result"] == "clear")
    if not clears:
        return set()
    idx = min(len(clears) - 1, int(decile * len(clears)))
    threshold = clears[idx]
    return {g["seed"] for g in games if g["result"] == "clear" and g["pills"] >= threshold}


# --------------------------------------------------------------------- batch
def _play_one(args):
    seed, pressure, max_pills = args
    r = play_seed(seed, pressure=pressure, max_pills=max_pills)
    r.pop("trace", None)
    r.pop("first_topout_board", None)
    return r


def run_batch(seeds, workers=6, pressure=None, max_pills=300, keep_fixtures=False):
    """Parallel play_seed over `seeds` (an iterable of ints). Drops trace/
    first_topout_board per-row by default (keep_fixtures=True to retain --
    costly at census scale) to keep pool IPC light. Returns list of dicts in
    completion order (NOT seed order)."""
    rows = []
    fn = play_seed if keep_fixtures else _play_one
    if keep_fixtures:
        with ProcessPoolExecutor(max_workers=workers, initializer=_lazy) as ex:
            futs = {ex.submit(play_seed, s, pressure, max_pills): s for s in seeds}
            for f in as_completed(futs):
                rows.append(f.result())
    else:
        with ProcessPoolExecutor(max_workers=workers, initializer=_lazy) as ex:
            futs = [ex.submit(_play_one, (s, pressure, max_pills)) for s in seeds]
            for f in as_completed(futs):
                rows.append(f.result())
    return rows


# ------------------------------------------------------------------ selftest
# 20 fixed seeds -- arbitrary but FIXED so the determinism + clear-rate checks
# are themselves reproducible run-to-run.
SELFTEST_SEEDS = [1000 + 37 * i for i in range(20)]


def selftest(seeds=None, expect_clear_lo=0.85, expect_clear_hi=1.0, verbose=True):
    """(a) determinism: same seed run twice -> bit-identical (result, pills,
    viruses_left, trace) -- the whole census method depends on this.
    (b) champion clear rate over `seeds` lands in [expect_clear_lo,
    expect_clear_hi].

    ⚠ CALIBRATION NOTE (found while building this harness, not assumed): the
    task brief's ballpark of "~70-85%" traces to memory dr-mario-l11-target-
    truth.md (38 days stale at write time) which measured an OLDER, WEAKER
    eval ("greedy2", pre-eval47, no g_stranded, no winner-leaf RTL chain).
    The actual established number for THIS EXACT champion (base32 root
    search, ws=20 g_stranded, winner leaf -- ab47.py::_choose_base(wt=0,
    ws=20) bit-exact) is **99.2% clear, 1/120 bad-ends (topout+stall)** at
    n=120, no pressure, measured by the project's own
    eval47/REACH_ROOT_CLEAN.md (`reach_root_ab.py`'s base32 control arm,
    the same decide path this harness calls). The default band here
    ([0.85,1.0]) is centered on THAT sourced number, not the stale brief
    figure -- a harness bug (wrong action space, wrong pill stream, wrong
    eval dose) would still fail loud against it, but a correct harness
    reproducing the champion's actual near-ceiling clear rate will PASS
    here where it would spuriously FAIL against the brief's 70-85% band.
    Returns dict(determinism_ok, n_determinism_checked, clear_rate, n_clear,
    n, pass_, detail)."""
    seeds = list(SELFTEST_SEEDS if seeds is None else seeds)
    det_mismatches = []
    results = []
    for s in seeds:
        r1 = play_seed(s)
        r2 = play_seed(s)
        same = (r1["result"] == r2["result"] and r1["pills"] == r2["pills"]
                and r1["viruses_left"] == r2["viruses_left"]
                and r1["trace"] == r2["trace"])
        if not same:
            det_mismatches.append(s)
        results.append(r1)

    n = len(results)
    n_clear = sum(1 for r in results if r["result"] == "clear")
    clear_rate = n_clear / n if n else float("nan")
    det_ok = len(det_mismatches) == 0
    rate_ok = expect_clear_lo <= clear_rate <= expect_clear_hi
    ok = det_ok and rate_ok

    if verbose:
        print(f"[selftest] determinism: {n - len(det_mismatches)}/{n} seeds bit-identical "
              f"across 2 runs" + (f" (MISMATCHES: {det_mismatches})" if det_mismatches else ""))
        print(f"[selftest] clear rate: {n_clear}/{n} = {clear_rate:.1%} "
              f"(expect [{expect_clear_lo:.0%},{expect_clear_hi:.0%}]) "
              f"{'OK' if rate_ok else 'OUT OF BAND'}")
        by_result = {}
        for r in results:
            by_result[r["result"]] = by_result.get(r["result"], 0) + 1
        print(f"[selftest] outcome breakdown: {by_result}")
        print(f"[selftest] {'PASS' if ok else 'FAIL'}")
    return {"determinism_ok": det_ok, "n_determinism_checked": n,
            "det_mismatches": det_mismatches, "clear_rate": clear_rate,
            "n_clear": n_clear, "n": n, "pass": ok,
            "detail": [{"seed": r["seed"], "result": r["result"], "pills": r["pills"],
                        "viruses_left": r["viruses_left"]} for r in results]}


# --------------------------------------------------------------- throughput
def measure_throughput(n_seeds=60, workers=6, warmup_seeds=6, seed0=500000):
    """Measure steady-state games/sec with `workers` processes. A `warmup_
    seeds`-seed untimed pass absorbs numba JIT compile + pool spin-up (the
    real cost is per-PROCESS, not per-game, so this must happen before the
    clock starts or every rate measurement is dominated by compile time).
    seed0 is offset well clear of SELFTEST_SEEDS / any small census range so
    a later small-n run never silently reuses these seeds' cached .pyc /
    disk-jit state in a way that hides a determinism bug."""
    warm_seeds = list(range(seed0, seed0 + warmup_seeds))
    run_batch(warm_seeds, workers=workers)  # untimed: pays JIT + pool spin-up

    seeds = list(range(seed0 + warmup_seeds, seed0 + warmup_seeds + n_seeds))
    t0 = time.monotonic()
    rows = run_batch(seeds, workers=workers)
    dt = time.monotonic() - t0
    gps = len(rows) / dt if dt > 0 else float("nan")
    return {"n_seeds": len(rows), "workers": workers, "seconds": dt,
            "games_per_sec": gps, "rows": rows}


def census_plan(games_per_sec, seed_space=SEED_SPACE):
    """Honest census sizing at the measured rate: how many seeds fit a 3h and
    a 12h budget, and whether the full seed_space is feasible within a
    reasonable single run."""
    def reachable(budget_hours):
        return int(games_per_sec * budget_hours * 3600)

    n_3h = reachable(3)
    n_12h = reachable(12)
    full_hours = seed_space / games_per_sec / 3600 if games_per_sec > 0 else float("inf")
    return {"games_per_sec": games_per_sec, "seed_space": seed_space,
            "reachable_3h": n_3h, "reachable_12h": n_12h,
            "full_census_hours": full_hours,
            "full_census_feasible_in_12h": full_hours <= 12,
            "pct_3h": n_3h / seed_space, "pct_12h": n_12h / seed_space}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--throughput", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--n-seeds", type=int, default=60)
    a = ap.parse_args()

    if a.selftest or not (a.selftest or a.throughput):
        st_res = selftest()
    if a.throughput or not (a.selftest or a.throughput):
        tp = measure_throughput(n_seeds=a.n_seeds, workers=a.workers)
        print(f"[throughput] {tp['n_seeds']} seeds / {tp['seconds']:.1f}s = "
              f"{tp['games_per_sec']:.3f} games/sec ({a.workers} workers)")
        cp = census_plan(tp["games_per_sec"])
        print(f"[census] reachable in 3h: {cp['reachable_3h']} seeds "
              f"({cp['pct_3h']:.2%} of {SEED_SPACE})")
        print(f"[census] reachable in 12h: {cp['reachable_12h']} seeds "
              f"({cp['pct_12h']:.2%} of {SEED_SPACE})")
        print(f"[census] full census ({SEED_SPACE} seeds): {cp['full_census_hours']:.1f}h "
              f"({'FEASIBLE' if cp['full_census_feasible_in_12h'] else 'NOT feasible'} in 12h)")


if __name__ == "__main__":
    main()
