#!/usr/bin/env python3
"""Snapshot REAL in-play decision states from champion games (clean and under
bursty-v1.1 pressure) for the A_v gate and the term-mass audit.

Why real boards and not only the static bitexact_gate corpus: A_v bites on HOLED
columns, and hole density is a property of how the champion actually plays under
garbage.  A gate run only on synthetic boards would be measuring the wrong
distribution.  Both corpora are used -- static for breadth, real for relevance.

Every snapshot is the exact tuple the decider sees: (col, vir, cur.a, cur.b,
nxt.a, nxt.b), captured BEFORE the placement, driven by the champion itself
(wt=0, ws=20, reach off) so the corpus is on the champion's own state
distribution.

Usage: gen_boards.py --games 40 --mode clean|bursty --out boards_clean.npz
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np

import reach_leaf as RL          # noqa: E402  (sets up sys.path)
import fast_rtl_x as FX          # noqa: E402
import root_search as RS         # noqa: E402
import pressure_rig as PR        # noqa: E402


def snapshot_game(seed, level, mode, bursty_model_obj, ws=20, wt=0, stride=1):
    """Play one champion game; yield (col, vir, ca, cb, na, nb) at every stride-th
    decision.  Mirrors pressure_rig.play()'s loop and garbage convention exactly."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    if mode == "bursty":
        from bursty_model import inject_bursty_garbage

    w, fl = FX.variant("winner")
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    out = []
    k = 0
    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        if k % stride == 0:
            out.append((col.copy(), vir.copy(), ca, cb, na, nb))
        k += 1
        a, _c1b = PR._choose_base(col, vir, ca, cb, na, nb, w, fl, wt, ws)
        if a is None:
            break
        occ_before = int(np.count_nonzero(env.board.color)) if mode == "bursty" else 0
        _, _, term, trunc, _info = env.step(int(a))
        if term or trunc:
            break
        if mode == "bursty" and env.pills_placed >= PR.GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                inject_bursty_garbage(env.board, bursty_model_obj, seed,
                                      env.pills_placed, clear_size)
            if env.board.virus_count() == 0 or env.board.spawn_blocked():
                break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--mode", choices=["clean", "bursty"], default="clean")
    ap.add_argument("--seed0", type=int, default=100000)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--out", type=str, required=True)
    a = ap.parse_args()

    RL.warmup()
    bm = None
    if a.mode == "bursty":
        import run_bursty_v1_1_validity as V11
        bm = V11.build_v1_1()
        s = bm.fit_summary()
        print(f"bursty v1.1: n_volleys={s['n_volleys']} n_clears={s['n_clears']}", flush=True)
        assert s["n_volleys"] == 28 and s["n_clears"] == 89, \
            f"NOT the honest v1.1 pool: {s['n_volleys']}/{s['n_clears']} (want 28/89)"
        bm.meta = {k: v for k, v in bm.meta.items() if k != "raw_events"}

    cols, virs, pills = [], [], []
    for g in range(a.games):
        rows = snapshot_game(a.seed0 + g, a.level, a.mode, bm, stride=a.stride)
        for c, v, ca, cb, na, nb in rows:
            cols.append(c); virs.append(v); pills.append((ca, cb, na, nb))
        print(f"  game {g + 1}/{a.games} seed={a.seed0 + g}: {len(rows)} snapshots "
              f"(total {len(cols)})", flush=True)
    np.savez_compressed(a.out, col=np.array(cols, dtype=np.int8),
                        vir=np.array(virs, dtype=np.int8),
                        pills=np.array(pills, dtype=np.int64),
                        kernel_hash=RL.kernel_hash(), mode=a.mode)
    print(f"wrote {a.out}: {len(cols)} boards, kernel_hash={RL.kernel_hash()}")


if __name__ == "__main__":
    main()
