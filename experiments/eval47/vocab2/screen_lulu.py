#!/usr/bin/env python3
"""Quick screen of the d_spawn_h survival penalty under the LULU (bursty)
pressure fit — pre-registered in PREREG_PHASE2.md LULU ADDENDUM before running.

val -= WQ * max(0, spawn_h_post - 10) added to pressure_rig._choose_base's
value, inside a replica of pressure_rig.play() (bursty path). Gates:
  G-L1 identity: replica with wq=0 must equal pressure_rig.play() on ALL 240
       seeds (res/pills/garbage) — this doubles as the base arm reference.
  G-L2 killed mutant: penalty hand-case on a synthetic board; a rows-only-0-1
       mutant must give a different answer.
  G-L3 liveness: >=1 seed's trace differs between base and each dose.
"""
from __future__ import annotations
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(HERE)
QA = os.path.dirname(EV)
for p in (EV, QA, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402
import pressure_rig as PR  # noqa: E402

LULU_FIT = os.path.join(EV, "results", "dr_lulu_20260808_fit.json")
SCREEN_RNG = 20260813
K_LANE = 10
DOSES = (60, 120)
SEEDS = [s for s in range(2, 242)]  # 240 seeds, seed 1 excluded by construction


def load_lulu():
    from bursty_model import BurstyPressureModel
    j = json.load(open(LULU_FIT))
    return BurstyPressureModel(
        volley_sizes=j["volley_sizes"], gap_samples=j["gap_samples"],
        p_within_k=j["p_within_k"], k_seconds=j["k_seconds"],
        n_volleys=j["n_volleys"], n_clears=j["n_clears"],
        n_matches=j["n_matches"], opponent_of=j["opponent_of"], meta=j["meta"])


def _spawn_h(c1):
    sph = 0
    for c in (3, 4):
        for r in range(16):
            if c1[r * 8 + c] != 0:
                h = 16 - r
                if h > sph:
                    sph = h
                break
    return sph


def _spawn_h_mutant(c1):
    """G-L2 mutant: only scans rows 0-1 (saturating, SPAWN-like)."""
    sph = 0
    for c in (3, 4):
        for r in range(2):
            if c1[r * 8 + c] != 0:
                h = 16 - r
                if h > sph:
                    sph = h
                break
    return sph


def choose_pen(col, vir, ca, cb, na, nb, w, fl, wt, ws, wq):
    """pressure_rig._choose_base + the pre-registered lane penalty."""
    import fast_rtl_x as FX
    import root_search as RS
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_tower, g_stranded
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_val, best_a = None, None
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            if wt:
                val -= wt * g_tower(c1, v1, PR.H0)
            if ws:
                val -= ws * g_stranded(c1, v1)
            if wq:
                sph = _spawn_h(c1)
                if sph > K_LANE:
                    val -= wq * (sph - K_LANE)
            if best_val is None or val > best_val:
                best_val, best_a = val, var * 8 + cc
    return best_a


def play_lulu(seed, wq):
    """pressure_rig.play() replica, bursty path, penalized chooser.
    wq=0 must be trace-identical to PR.play() (gate G-L1)."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS
    from bursty_model import inject_bursty_garbage

    C = PR._C
    level, wt, ws, w, fl = C["level"], C["wt"], C["ws"], C["w"], C["fl"]
    bmodel = C["bursty_model_obj"]
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    res, garbage_injected, v_at_topout = "stall", 0, None
    for _ in range(300):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        a = choose_pen(col, vir, int(env.cur.a), int(env.cur.b),
                       int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws, wq)
        if a is None:
            break
        occ_before = int(np.count_nonzero(env.board.color))
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout":
                v_at_topout = env.board.virus_count()
            break
        if trunc:
            break
        if env.pills_placed >= PR.GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            landed = 0
            if clear_size > 0:
                landed = inject_bursty_garbage(env.board, bmodel, seed,
                                               env.pills_placed, clear_size)
            garbage_injected += landed
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_topout = env.board.virus_count()
                break
    dies_ahead = int(res == "topout" and v_at_topout is not None
                     and v_at_topout <= PR.DIES_AHEAD_VIRUS_THRESHOLD)
    return {"seed": seed, "res": res, "pills": env.pills_placed,
            "garbage": garbage_injected, "dies_ahead": dies_ahead}


def _winit():
    PR._init(11, 0, 20, model_kind="bursty", bursty_model_obj=load_lulu())


def _worker(args):
    seed, wq = args
    if wq == -1:   # reference arm: the REAL pressure_rig.play()
        r = PR.play(seed)
        return -1, {"seed": r["seed"], "res": r["res"], "pills": r["pills"],
                    "garbage": r["garbage"], "dies_ahead": r["dies_ahead"]}
    return wq, play_lulu(seed, wq)


def mutant_gate():
    """G-L2: synthetic board — col 3 filled to height 12 (rows 4..15), col 4
    empty. Hand value: spawn_h = 12, penalty units = 2. The rows-0-1 mutant
    sees height 0 and must DISAGREE."""
    c1 = np.zeros(128, dtype=np.int8)
    for r in range(4, 16):
        c1[r * 8 + 3] = 1
    assert _spawn_h(c1) == 12, _spawn_h(c1)
    assert max(0, _spawn_h(c1) - K_LANE) == 2
    assert _spawn_h_mutant(c1) != _spawn_h(c1), "mutant NOT killed"
    # second case: lane clear below threshold -> penalty 0
    c2 = np.zeros(128, dtype=np.int8)
    for r in range(8, 16):
        c2[r * 8 + 4] = 2
    assert _spawn_h(c2) == 8 and max(0, _spawn_h(c2) - K_LANE) == 0
    print("[gate G-L2] killed-mutant: PASS", flush=True)


def main():
    mutant_gate()
    jobs = [(s, wq) for wq in (-1, 0) + DOSES for s in SEEDS]
    print(f"[lulu-screen] {len(SEEDS)} seeds x 4 arms (ref/base/60/120) = "
          f"{len(jobs)} games", flush=True)
    out = {wq: {} for wq in (-1, 0) + DOSES}
    t0 = time.monotonic()
    done = 0
    with ProcessPoolExecutor(max_workers=8, initializer=_winit) as ex:
        futs = [ex.submit(_worker, j) for j in jobs]
        for fut in as_completed(futs):
            wq, row = fut.result()
            out[wq][row["seed"]] = row
            done += 1
            if done % 96 == 0:
                dt = time.monotonic() - t0
                print(f"[lulu-screen] {done}/{len(jobs)} {dt:.0f}s "
                      f"{done/dt:.2f} g/s", flush=True)

    # G-L1: replica base must equal the real rig on every seed
    bad = [s for s in SEEDS if any(out[0][s][k] != out[-1][s][k]
                                   for k in ("res", "pills", "garbage"))]
    print(f"[gate G-L1] replica-vs-rig mismatches: {len(bad)}", flush=True)
    result = {"rng": SCREEN_RNG, "k_lane": K_LANE, "doses": DOSES,
              "n_seeds": len(SEEDS), "identity_gate_mismatches": bad}
    if bad:
        json.dump(result, open(os.path.join(HERE, "screen_lulu_result.json"),
                               "w"), indent=1)
        sys.exit("[gate G-L1] FAILED — replica does not reproduce the rig")

    def badend(r):
        return r["res"] != "clear"

    boot = np.random.default_rng(SCREEN_RNG)
    for wq in DOSES:
        b01 = [s for s in SEEDS if badend(out[0][s]) and not badend(out[wq][s])]
        b10 = [s for s in SEEDS if not badend(out[0][s]) and badend(out[wq][s])]
        da0 = sum(out[0][s]["dies_ahead"] for s in SEEDS)
        da1 = sum(out[wq][s]["dies_ahead"] for s in SEEDS)
        be0 = sum(badend(out[0][s]) for s in SEEDS)
        be1 = sum(badend(out[wq][s]) for s in SEEDS)
        changed = sum(1 for s in SEEDS
                      if out[wq][s]["res"] != out[0][s]["res"]
                      or out[wq][s]["pills"] != out[0][s]["pills"])
        # G-L3 liveness
        if changed == 0:
            sys.exit(f"[gate G-L3] FAILED — wq={wq} trace-identical to base")
        # McNemar exact two-sided on discordant pairs
        from math import comb
        n_d = len(b01) + len(b10)
        k = min(len(b01), len(b10))
        p = (sum(comb(n_d, i) for i in range(0, k + 1)) * 2 / 2 ** n_d
             if n_d else 1.0)
        p = min(1.0, p)
        # stream-level sensitivity: collapse 2k/2k+1 to one cluster
        streams = sorted({s // 2 for s in SEEDS})
        sb01 = sum(1 for t in streams
                   if any(x in b01 for x in (2 * t, 2 * t + 1)))
        sb10 = sum(1 for t in streams
                   if any(x in b10 for x in (2 * t, 2 * t + 1)))
        # bootstrap CI over seeds for net bad-end change
        d = np.array([int(badend(out[wq][s])) - int(badend(out[0][s]))
                      for s in SEEDS])
        nets = [d[boot.integers(0, len(d), len(d))].mean() * len(d)
                for _ in range(2000)]
        result[f"wq{wq}"] = {
            "badends_base": be0, "badends_trt": be1,
            "fixed_b01": len(b01), "fixed_seeds": b01,
            "broken_b10": len(b10), "broken_seeds": b10,
            "mcnemar_p": p, "dies_ahead_base": da0, "dies_ahead_trt": da1,
            "stream_fixed": sb01, "stream_broken": sb10,
            "n_games_changed_vs_base": changed,
            "net_badend_delta": int(be1 - be0),
            "net_ci95": [float(np.percentile(nets, 2.5)),
                         float(np.percentile(nets, 97.5))]}
        print(f"[lulu-screen] wq={wq}: bad-ends {be0}->{be1} "
              f"(fixed {len(b01)}, broken {len(b10)}, McNemar p={p:.4f}), "
              f"dies-ahead {da0}->{da1}, changed {changed}/240, "
              f"net {be1-be0:+d} CI "
              f"[{result[f'wq{wq}']['net_ci95'][0]:+.1f},"
              f"{result[f'wq{wq}']['net_ci95'][1]:+.1f}]", flush=True)
    json.dump(result, open(os.path.join(HERE, "screen_lulu_result.json"), "w"),
              indent=1)


if __name__ == "__main__":
    main()
