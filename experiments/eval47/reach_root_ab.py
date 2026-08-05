#!/usr/bin/env python3
"""reach_root.py's three enumeration modes (base32 / reach32 / reachfull),
paired A/B, base32 always the control -- union_mirror.py's process-pool +
paired-seed + compare() skeleton, adapted to reach_root.choose(mode, ...)
instead of the RS/TE union arms union_mirror.py studies.

base32 reproduces the shipped strand20 decider bit-for-bit (see reach_root.py
selftest). reach32 is a pure LEGALITY subtraction from base32 (never adds a
candidate) -- any measured delta here is entirely "the shipped search stopped
proposing placements no pill can reach", never a new capability. reachfull
ADDS the BFS's full reachable set (straight + tuck-class, theta=250-gated) --
its delta mixes the same legality fix with genuine new tuck reach, so read
reach32 first to isolate the fix, reachfull second to price the ceiling.

--pressure bursty replicates eval47/pressure_rig.py's own bursty-garbage
convention (READ-ONLY import of bursty_model.py; pressure_rig.py itself is
another agent's file and is neither imported nor modified here): rng seeded
from (seed, pills_placed), clear-size computed from the AI's OWN clear this
placement (a solo rig has no second board to watch), board._apply_gravity()
run before resolve() after injecting so a parked half never fakes a topout.

Usage:
  reach_root_ab.py --seeds 120 --workers 6 --arms reach32 reachfull \\
      --pressure bursty --out results/reach_root
"""
from __future__ import annotations

import sys
import os
import json
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import reach_root as RR

_C = {}

GARBAGE_MIN_PILLS = 25   # matches pressure_rig.py's own convention exactly


def _init(level, mode, pressure, bursty_model_obj=None):
    RR._lazy()   # numba warmup once per worker, not once per game
    _C.update(level=level, mode=mode, pressure=pressure, bursty_model_obj=bursty_model_obj)


def play(seed):
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    from nes_pills import NesPillSource

    level, mode, pressure = _C["level"], _C["mode"], _C["pressure"]
    bursty_model_obj = _C.get("bursty_model_obj")
    if pressure == "bursty":
        from bursty_model import inject_bursty_garbage

    L = RR._lazy()
    FB, RS = L["FB"], L["RS"]

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    fired_tuck = 0
    garbage_injected = 0
    n_reach_sum = n_base_sum = n_reach_calls = 0   # reach32 diagnostics
    n_tuck_legal_sum = n_tuck_calls = 0            # reachfull diagnostics

    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb, na, nb = int(env.cur.a), int(env.cur.b), int(env.nxt.a), int(env.nxt.b)
        best = RR.choose(mode, fb, col, vir, ca, cb, na, nb)

        if mode == "reach32" and "n_base_legal" in best:
            n_base_sum += best["n_base_legal"]
            n_reach_sum += best.get("n_reach", 0)
            n_reach_calls += 1
        if mode == "reachfull" and "n_tuck_legal" in best:
            n_tuck_legal_sum += best["n_tuck_legal"]
            n_tuck_calls += 1

        occ_before = int(np.count_nonzero(env.board.color)) if pressure == "bursty" else 0

        if best["kind"] == "tuck":
            p = best["placement"]
            r0, c0, r1, c1 = p["cells"]
            col0, col1 = best["ca"], best["cb"]
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
            fired_tuck += 1
            if b.virus_count() == 0:
                res = "clear"
                break
            if b.spawn_blocked():
                res = "topout"
                break
            if env.pills_placed >= 300:
                break
        else:
            action = best["action"]
            if action is None:
                break   # no legal root candidate at all -- topped out board
            _, _, term, trunc, info = env.step(int(action))
            if term:
                res = "clear" if info["won"] else "topout"
                break
            if trunc:
                break

        if pressure == "bursty" and env.pills_placed >= GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                landed = inject_bursty_garbage(
                    env.board, bursty_model_obj, seed, env.pills_placed, clear_size)
                garbage_injected += landed
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                break

    row = {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"),
           "stall": int(res == "stall"), "pills": env.pills_placed,
           "fired_tuck": fired_tuck, "garbage_injected": garbage_injected}
    if n_reach_calls:
        row["reach_frac"] = n_reach_sum / n_base_sum if n_base_sum else float("nan")
    if n_tuck_calls:
        row["tuck_legal_per_decision"] = n_tuck_legal_sum / n_tuck_calls
    return row


def boot_ci(xs, stat=st.mean, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = [stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n)]
    reps.sort()
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def run_arm(level, seeds, workers, mode, pressure, bursty_model_obj):
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(level, mode, pressure, bursty_model_obj)) as ex:
        futs = [ex.submit(play, s) for s in range(seeds)]
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if (i + 1) % max(1, seeds // 5) == 0 or (i + 1) == seeds:
                print(f"  mode={mode} pressure={pressure} {i + 1}/{seeds}", flush=True)
    return {r["seed"]: r for r in rows}


def compare(ctrl, on, tag):
    ss = sorted(set(ctrl) & set(on))
    both = [s for s in ss if ctrl[s]["won"] and on[s]["won"]]
    d = [on[s]["pills"] - ctrl[s]["pills"] for s in both]
    lo, hi = boot_ci(d)
    c0 = sum(ctrl[s]["won"] for s in ss) / len(ss)
    c1 = sum(on[s]["won"] for s in ss) / len(ss)
    tp0 = sum(ctrl[s]["topout"] + ctrl[s]["stall"] for s in ss)
    tp1 = sum(on[s]["topout"] + on[s]["stall"] for s in ss)
    fired = st.mean([on[s]["fired_tuck"] for s in ss])
    gb0 = st.mean([ctrl[s]["garbage_injected"] for s in ss])
    gb1 = st.mean([on[s]["garbage_injected"] for s in ss])
    verdict = "REAL" if (hi < 0 or lo > 0) else "WASH"
    print(f"{tag}: pills {st.mean(d) if d else float('nan'):+.2f} [{lo:+.2f},{hi:+.2f}] "
          f"{verdict}  clear {c0:.1%}->{c1:.1%}  bad_ends {tp0}->{tp1}  "
          f"tuck_fires/g {fired:.2f}  garbage/g {gb0:.2f}->{gb1:.2f}  "
          f"moved={len(ss)}/{max(len(ctrl), len(on))}", flush=True)
    return {"tag": tag, "delta": st.mean(d) if d else None, "ci": [lo, hi],
            "verdict": verdict, "clear0": c0, "clear1": c1,
            "bad_ends0": tp0, "bad_ends1": tp1, "fired_tuck": fired,
            "garbage0": gb0, "garbage1": gb1, "moved_seeds": len(ss)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=120)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--arms", type=str, nargs="+", default=["reach32", "reachfull"],
                    choices=list(RR.MODES),
                    help="modes to compare against base32 (the control -- always run, "
                         "even if omitted from --arms)")
    ap.add_argument("--pressure", type=str, choices=["none", "bursty"], default="none")
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    bursty_model_obj = None
    if a.pressure == "bursty":
        import bursty_model
        bursty_model_obj = bursty_model.fit_struktured_20260804()
        bursty_model_obj.meta = {k: v for k, v in bursty_model_obj.meta.items()
                                  if k != "raw_events"}
        print(f"=== bursty-v1 fit: n_matches={bursty_model_obj.n_matches} "
              f"n_volleys={bursty_model_obj.n_volleys} n_clears={bursty_model_obj.n_clears} "
              f"p_within_k={bursty_model_obj.p_within_k} ===", flush=True)

    arms = [m for m in a.arms if m != "base32"]
    print(f"=== reach_root A/B, L{a.level}, n={a.seeds}, pressure={a.pressure}, "
          f"arms={arms} (control=base32) ===", flush=True)
    ctrl = run_arm(a.level, a.seeds, a.workers, "base32", a.pressure, bursty_model_obj)

    results = {}
    for mode in arms:
        on = run_arm(a.level, a.seeds, a.workers, mode, a.pressure, bursty_model_obj)
        results[mode] = compare(ctrl, on, f"{mode:>9s} vs base32")
        if a.out:
            with open(f"{a.out}_{mode}.json", "w") as fh:
                json.dump({"summary": results[mode],
                           "ctrl": [ctrl[s] for s in sorted(ctrl)],
                           "arm": [on[s] for s in sorted(on)]}, fh)
            print(f"wrote {a.out}_{mode}.json", flush=True)

    print("\nDONE")


if __name__ == "__main__":
    main()
