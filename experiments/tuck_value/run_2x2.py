#!/usr/bin/env python3
"""THE INDEPENDENT 2x2: firmware vocabulary x cart executor, in the FAST sim.

Mirrors the co-sim farm's RTL 2x2 (experiments/cosim_farm/README.md) by a
different route -- fast numba sim instead of verilated RTL -- so that agreement
between the two is corroboration and disagreement is a finding. This rig can
afford n in the hundreds per arm; the co-sim cannot.

                 drop (today's cart)      tuck (a DRTUCK=1 cart)
    v1  e970e9ab      A  shipped champion      C  executor on, v1 firmware
    t3  5d010f62      B  ship tier-3 today     D  the full program

  D - B   the EXECUTOR'S OWN VALUE, tier-3 firmware held fixed  <-- headline
  C - A   the executor's own value, v1 firmware held fixed
  B - A   value of shipping tier-3 onto today's (executor-less) cart
  D - A   the full program: cart rebuild + tier-3

WHY THE TWO VOCABULARIES NEED DIFFERENT CODE (see exec_model.py's docstring):
v1 runs its enumerator AFTER the search ("call it after the search",
build_copro_d3.py:93) and never writes D_BC/D_BO, so under v1 THE DECISION IS
PURE base32 IN BOTH MODES and only the landing row can differ -- the purest
form of "hold the brain fixed, change the executor". tier-3 scores tuck
candidates inside the search and overwrites D_BC/D_BO when one wins, so its
`drop` arm is steered to the tuck's column and orientation and plain-dropped.

THETA -- a discrepancy this rig found and did not inherit. reach_root.py's
THETA_FULL is 250, commented as "the tuck_v3 ship config's theta". The
firmware disagrees: build_copro_d3.py:101 says "theta=150 gate" and
fpga/copro/tuck_v3.py:79 is `THETA = int(os.environ.get(
"DRCOPRO_TUCKV3_THETA", "150"))`. Every offline tier sweep to date
(run_tier_sweep.py, firmware_tier3_ab.py) used RR's 250 default, a TIGHTER
gate than the silicon's. Default here is 150, the firmware value, and
--theta sweeps it, because tuck_v3.py:70-72 also records that the same
numeric theta is a LOOSER gate in firmware eval units than offline (4.38 vs
2.80 fires/game), so no single number reproduces the firmware exactly and the
honest answer is to show whether the verdict is theta-robust.

SIMULATOR OF RECORD: every number this file produces is a FAST-SIM number.
fast_rtl_x.decide_ship_d3 agrees with the real RTL on 38% of full (col,
orient) base-search moves. That matters far less for an A-vs-B comparison
than for an absolute claim, because both arms run under the same simulator
and shared error cancels -- but it is why the co-sim farm exists and why this
rig's job is corroboration, not adjudication.

Usage:
  run_2x2.py --seeds 400 --workers 6 --pressure bursty --out results/bursty
  run_2x2.py --seeds 400 --workers 6 --pressure clean  --out results/clean
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS = os.path.dirname(HERE)
EVAL47 = os.path.join(EXPERIMENTS, "eval47")
for _p in (HERE, EXPERIMENTS, EVAL47):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import exec_model as EM                     # noqa: E402
import reach_root as RR                     # noqa: E402 -- read-only import
import reach_root_ab as AB                  # noqa: E402 -- compare/mcnemar reused
import firmware_tier3_ab as FT3             # noqa: E402 -- firmware_tier_of reused

ARMS = ("v1_drop", "v1_tuck", "t3_drop", "t3_tuck")
ARM_LABEL = {"v1_drop": "A  v1  x drop (SHIPPED)", "v1_tuck": "C  v1  x tuck",
             "t3_drop": "B  t3  x drop", "t3_tuck": "D  t3  x tuck"}
FIRMWARE_THETA = 150         # fpga/copro/tuck_v3.py:79 -- NOT reach_root's 250

_C = {}


# --------------------------------------------------------------------------
# tier_of, memoised per board
# --------------------------------------------------------------------------
_TIER_CACHE = {"key": None, "ctx": None}


def cached_firmware_tier_of(col, candidate):
    """`firmware_tier3_ab.firmware_tier_of` with the three per-BOARD
    derivations (row_bfs_visited, mono_reach L/R) hoisted out of the
    per-CANDIDATE path. The original recomputes all three for every candidate;
    with 10-40 tuck candidates per decision that is a 10-40x redundant BFS.

    Equivalent by construction -- they are pure functions of the board, and
    `_selftest_cached_tier_matches` checks that claim rather than asserting
    it."""
    target, rest, orient = FT3._unpack(candidate)
    key = bytes(bytearray(int(x) & 0xFF for x in col))
    if _TIER_CACHE["key"] != key:
        board = FT3._to_nes_board(col)
        _TIER_CACHE["key"] = key
        _TIER_CACHE["ctx"] = (board, FT3.TR.row_bfs_visited(board),
                              FT3.T3R.mono_reach(board, "L"),
                              FT3.T3R.mono_reach(board, "R"))
    board, visited, mono_L, mono_R = _TIER_CACHE["ctx"]
    if FT3.TR.derive_verified(board, target, rest, orient, visited) is not None:
        return 1
    if FT3.T3R.derive_tier3_verified(board, target, rest, orient, visited,
                                     mono_L, mono_R) is not None:
        return 1
    return 99


# --------------------------------------------------------------------------
# decision: same call chain reach_root.choose_reach_tier uses, but the base
# pick is kept as well (the `drop` arms need it as a fallback, and
# choose_reach_tier discards it when a tuck wins)
# --------------------------------------------------------------------------
def choose_with_base(fb, col, vir, ca, cb, na, nb, vocab, theta):
    """-> (pick, base_action). `pick` is byte-identical to what
    reach_root.choose_reach_tier / choose_base32 would return -- this calls
    the same functions in the same order with the same arguments rather than
    reimplementing any eval arithmetic. `_selftest_choose_matches_reach_root`
    proves the equality on real boards."""
    if vocab == "v1":
        pick = RR.choose_base32(col, vir, ca, cb, na, nb)
        return pick, pick["action"]

    cands = RR._scored_base_candidates(fb, col, vir, ca, cb, na, nb, RR.WS, RR.TOPK2)
    reach_cands = [c for c in cands if c["reachable"]]
    pool = reach_cands if reach_cands else cands
    best = max(pool, key=lambda c: c["val"])
    base_action = best["action"]
    best_out = {"kind": "base", "action": base_action, "val": best["val"]}
    tier_filter = lambda p: cached_firmware_tier_of(col, p) <= 1   # noqa: E731
    pick = RR._tuck_branch_pick(fb, col, vir, ca, cb, na, nb, RR.WS, theta,
                                RR.TOPK2, best["val"], best_out,
                                extra_filter=tier_filter)
    return pick, base_action


# --------------------------------------------------------------------------
# game loop
# --------------------------------------------------------------------------
def _init(level, arm, pressure, theta, on_blocked, bursty_model_obj=None):
    RR._lazy()
    _C.update(level=level, arm=arm, pressure=pressure, theta=theta,
              on_blocked=on_blocked, bursty_model_obj=bursty_model_obj)


def _place_cells(env, r0, c0, r1, c1, col0, col1):
    """Lock a pill at explicit cells. Same convention as run_tier_sweep.py's
    own tuck execution: cell0 is LEFT (horizontal) or TOP (vertical), matching
    fast_sim_x._resting's return order and _expand_core's colour assignment."""
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    b = env.board
    b.color[r0, c0] = col0
    b.color[r1, c1] = col1
    if r0 == r1:
        b.link[r0, c0] = LINK_RIGHT
        b.link[r1, c1] = LINK_LEFT
    else:
        b.link[r0, c0] = LINK_DOWN
        b.link[r1, c1] = LINK_UP
    b.is_virus[r0, c0] = False
    b.is_virus[r1, c1] = False
    b.resolve()
    env.pills_placed += 1
    env.cur = env.nxt
    env.nxt = env._rand_pill()


def _cells_for(var, cc, rest_row):
    """(r0, c0, r1, c1) for anchor row `rest_row` in column `cc`."""
    if EM.is_horizontal(var):
        return (rest_row, cc, rest_row, cc + 1)
    return (rest_row - 1, cc, rest_row, cc)


def _colors_for(var, ca, cb):
    return (ca, cb) if var in (0, 2) else (cb, ca)


def play(seed):
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    import fast_sim_x as FS

    level, arm, pressure = _C["level"], _C["arm"], _C["pressure"]
    theta, on_blocked = _C["theta"], _C["on_blocked"]
    bursty_model_obj = _C.get("bursty_model_obj")
    if pressure == "bursty":
        from bursty_model import inject_bursty_garbage

    vocab, mode = arm.split("_")
    L = RR._lazy()
    FB, RS = L["FB"], L["RS"]

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    fired_tuck = 0            # executions that actually differed from the drop
    n_published = 0           # decisions where the firmware offered a tuck
    n_coherent = 0            # ... that the executor could perform
    n_deeper = 0              # ... that landed strictly deeper than the drop
    n_degraded = 0            # t3 drop-mode: tuck won, plain-dropped instead
    garbage_injected = 0
    v_at_topout = None

    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        pick, base_action = choose_with_base(fb, col, vir, ca, cb, na, nb,
                                             vocab, theta)

        occ_before = int(np.count_nonzero(env.board.color)) if pressure == "bursty" else 0
        stepped = False

        if vocab == "v1":
            var, cc = base_action // 8, base_action % 8
            approach, trigger = EM.v1_descriptor(col)
            if approach is not None:
                n_published += 1
            if mode == "tuck" and approach is not None:
                rest, landed, status = EM.v1_execute(col, var, cc, approach,
                                                     trigger, on_blocked=on_blocked)
                if status == "coherent":
                    n_coherent += 1
                plain = EM.straight_drop_row(col, cc, EM.is_horizontal(var))
                if rest is not None and (landed != cc or rest != plain):
                    if rest > plain and landed == cc:
                        n_deeper += 1
                    fired_tuck += 1
                    r0, c0, r1, c1 = _cells_for(var, landed, rest)
                    col0, col1 = _colors_for(var, ca, cb)
                    _place_cells(env, r0, c0, r1, c1, col0, col1)
                    stepped = True
            if not stepped:
                action = base_action
        else:
            if pick["kind"] == "tuck":
                n_published += 1
                n_coherent += 1        # tier-3 descriptors are 100% coherent by
                                       # construction (derive_tier3_verified)
                p = pick["placement"]
                if mode == "tuck":
                    r0, c0, r1, c1 = p["cells"]
                    fired_tuck += 1
                    plain = EM.straight_drop_row(col, int(p["col"]),
                                                 EM.is_horizontal(int(p["variant"])))
                    anchor = max(r0, r1) if c0 == c1 else r0
                    if plain is None or anchor > plain:
                        n_deeper += 1
                    _place_cells(env, r0, c0, r1, c1, pick["ca"], pick["cb"])
                    stepped = True
                else:
                    a = EM.tier3_drop_action(p)
                    ok = FS._resting(col, a // 8, a % 8)[0]
                    action = a if ok else base_action
                    n_degraded += 1
            else:
                action = pick["action"]

        if not stepped:
            if action is None:
                break
            _, _, term, trunc, info = env.step(int(action))
            if term:
                res = "clear" if info["won"] else "topout"
                if res == "topout":
                    v_at_topout = env.board.virus_count()
                break
            if trunc:
                break
        else:
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_topout = env.board.virus_count()
                break
            if env.pills_placed >= 300:
                break

        if pressure == "bursty" and env.pills_placed >= AB.GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                garbage_injected += inject_bursty_garbage(
                    env.board, bursty_model_obj, seed, env.pills_placed, clear_size)
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_topout = env.board.virus_count()
                break

    dies_ahead = int(res == "topout" and v_at_topout is not None
                     and v_at_topout <= AB.DIES_AHEAD_VIRUS_THRESHOLD)
    return {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"),
            "stall": int(res == "stall"), "pills": env.pills_placed,
            "fired_tuck": fired_tuck, "n_published": n_published,
            "n_coherent": n_coherent, "n_deeper": n_deeper,
            "n_degraded": n_degraded, "garbage_injected": garbage_injected,
            "viruses_left_at_end": (v_at_topout if v_at_topout is not None
                                    else env.board.virus_count()),
            "dies_ahead": dies_ahead}


def run_arm(level, seeds, workers, arm, pressure, theta, on_blocked,
            bursty_model_obj):
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(level, arm, pressure, theta, on_blocked,
                                       bursty_model_obj)) as ex:
        futs = [ex.submit(play, s) for s in range(seeds)]
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if (i + 1) % max(1, seeds // 4) == 0 or (i + 1) == seeds:
                print(f"  {arm} {pressure} {i + 1}/{seeds}", flush=True)
    return {r["seed"]: r for r in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=400)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--pressure", choices=("clean", "bursty"), default="bursty")
    ap.add_argument("--theta", type=float, default=FIRMWARE_THETA)
    ap.add_argument("--on-blocked", choices=("drop", "approach"), default="drop",
                    help="v1 tuck-mode convention for an unperformable descriptor: "
                         "'drop' = degrade to a plain drop (conservative, matches the "
                         "co-sim farm); 'approach' = the capsule lands in the approach "
                         "column (the hazard the driver source implies)")
    ap.add_argument("--arms", type=str, default=",".join(ARMS))
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    bm = None
    if a.pressure == "bursty":
        import run_bursty_v1_1_validity as V11
        bm = V11.build_v1_1()
        s = bm.fit_summary()
        print(f"=== bursty v1.1 (struktured-only): n_volleys={s['n_volleys']} "
              f"n_clears={s['n_clears']} size={s['volley_size_mean']:.2f} "
              f"gap={s['inter_volley_gap_mean_s']:.1f}s ===", flush=True)
        bm.meta = {k: v for k, v in bm.meta.items() if k != "raw_events"}

    arms = [x for x in a.arms.split(",") if x]
    print(f"=== INDEPENDENT 2x2 (fast sim), L{a.level}, n={a.seeds}, "
          f"pressure={a.pressure}, theta={a.theta:g}, on_blocked={a.on_blocked} ===",
          flush=True)

    rows = {}
    for arm in arms:
        rows[arm] = run_arm(a.level, a.seeds, a.workers, arm, a.pressure,
                            a.theta, a.on_blocked, bm)

    print()
    for arm in arms:
        r = [rows[arm][s] for s in sorted(rows[arm])]
        n = len(r)
        print(f"{ARM_LABEL.get(arm, arm):<26} clear {sum(x['won'] for x in r) / n:6.1%}  "
              f"bad_ends {sum(x['topout'] + x['stall'] for x in r):3d}/{n}  "
              f"dies-ahead {sum(x['dies_ahead'] for x in r):3d}  "
              f"fires/g {sum(x['fired_tuck'] for x in r) / n:5.2f}  "
              f"published/g {sum(x['n_published'] for x in r) / n:5.2f}  "
              f"deeper/g {sum(x['n_deeper'] for x in r) / n:5.2f}", flush=True)

    print()
    pairs = [("t3_tuck", "t3_drop", "D-B  EXECUTOR VALUE, tier-3 firmware"),
             ("v1_tuck", "v1_drop", "C-A  executor value, v1 firmware  "),
             ("t3_drop", "v1_drop", "B-A  tier-3 onto today's cart     "),
             ("t3_tuck", "v1_drop", "D-A  full program                 ")]
    summaries = {}
    for on, ctrl, tag in pairs:
        if on in rows and ctrl in rows:
            summaries[tag.split()[0]] = AB.compare(rows[ctrl], rows[on], tag)

    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(f"{a.out}.json", "w") as fh:
            json.dump({"config": vars(a), "summaries": summaries,
                       "rows": {k: [v[s] for s in sorted(v)] for k, v in rows.items()}},
                      fh)
        print(f"\nwrote {a.out}.json")
    print("DONE")


if __name__ == "__main__":
    main()
