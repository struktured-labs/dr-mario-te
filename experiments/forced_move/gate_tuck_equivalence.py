#!/usr/bin/env python3
"""GATE: step_cells must equal env.step wherever both can express the placement.

WHY THIS GATE DECIDES WHETHER TUCK ARMS MEAN ANYTHING. A tuck cannot be named by
an action int, so tuck arms go through `step_cells` while every non-tuck arm goes
through `env.step`. If those two paths differ AT ALL -- link bytes, resolve order,
the order of the win/topout/truncate checks, when cur/nxt advances -- then the
tuck-vs-non-tuck comparison measures the difference between two code paths and
not the difference between two moves. That is the failure this file exists to
prevent, and it would not show up as an error: both paths produce plausible
boards.

METHOD. On real mid-game positions, for EVERY straight-drop-reachable placement
(the set both paths can express), run the same position twice from an identical
snapshot -- once via env.step(action), once via step_cells(cells, colors) -- and
require the resulting board to be identical cell-for-cell INCLUDING LINKS, plus
identical (terminated, truncated, won, pills_placed, cur, nxt).

CONTROL. The same comparison with the two colours SWAPPED must FAIL on the
placements where the halves differ in colour. Without it, a `step_cells` that
ignored `colors` entirely would pass the main arm on every monochrome capsule.

TUCK COVERAGE. Separately reports how many placements tuck_enum finds beyond the
straight drops, in both 'free' and 'gravity' mode -- if that count is zero on
every board, a tuck arm is untestable here and the sheet says so rather than
reporting a silent null.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import forced_board as FBM   # noqa: E402


def _snapshot(env, src):
    return (env.board.color.copy(), env.board.is_virus.copy(), env.board.link.copy(),
            (int(env.cur.a), int(env.cur.b)), (int(env.nxt.a), int(env.nxt.b)),
            int(env.pills_placed), int(src.i))


def _restore(env, src, s):
    from drmario.faithful_env import Pill
    env.board.color[:] = s[0]
    env.board.is_virus[:] = s[1]
    env.board.link[:] = s[2]
    env.cur = Pill(*s[3])
    env.nxt = Pill(*s[4])
    env.pills_placed = s[5]
    src.i = s[6]


def _state(env):
    return (FBM.board_key(env.board), int(env.pills_placed),
            (int(env.cur.a), int(env.cur.b)), (int(env.nxt.a), int(env.nxt.b)))


def run(seeds, plies, level=11, wt=0, ws=20, verbose=True):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource

    dec = FBM.Decider(wt=wt, ws=ws, level=level)
    n_cmp = n_ok = 0
    n_ctrl = n_ctrl_killed = 0
    tuck_free = tuck_grav = 0
    boards = 0

    for seed in seeds:
        env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
        env.reset()
        src = NesPillSource(seed=seed)
        src.attach(env)
        env.cur = env._rand_pill()
        env.nxt = env._rand_pill()
        want = set(plies)

        for ply in range(max(plies) + 1):
            if env.board.virus_count() == 0:
                break
            if ply in want:
                boards += 1
                snap = _snapshot(env, src)
                straight = {tuple(sorted((cc[0], cc[1]) for cc in p["cells"]))
                            for p in FBM.legal_placements(env)}
                for p in FBM.legal_placements(env):
                    # env.step path
                    _restore(env, src, snap)
                    env.step(int(p["action"]))
                    ref = _state(env)
                    # step_cells path, same placement expressed as cells
                    (r0, c0, k0), (r1, c1, k1) = p["cells"]
                    _restore(env, src, snap)
                    FBM.step_cells(env, ((r0, c0), (r1, c1)), (k0, k1))
                    got = _state(env)
                    n_cmp += 1
                    n_ok += int(got == ref)
                    # CONTROL: swapped colours must DIFFER when the halves differ
                    if k0 != k1:
                        _restore(env, src, snap)
                        FBM.step_cells(env, ((r0, c0), (r1, c1)), (k1, k0))
                        n_ctrl += 1
                        n_ctrl_killed += int(_state(env) != ref)
                _restore(env, src, snap)
                for mode in ("free", "gravity"):
                    try:
                        ps = FBM.tuck_placements(env, mode=mode)
                    except Exception as e:                     # noqa: BLE001
                        print(f"  tuck_enum {mode} failed: {e}")
                        continue
                    extra = {tuple(sorted(((c[0], c[1]), (c[2], c[3]))))
                             for c in (p["cells"] for p in ps if p.get("reachable", True))}
                    extra = {e for e in extra if e not in straight}
                    if mode == "free":
                        tuck_free += len(extra)
                    else:
                        tuck_grav += len(extra)
                _restore(env, src, snap)
            a = dec(env)
            if a is None:
                break
            _, _, term, trunc, _ = env.step(int(a))
            if term or trunc:
                break

    ok = (n_cmp and n_ok == n_cmp and n_ctrl and n_ctrl_killed == n_ctrl)
    if verbose:
        print(f"  boards                     : {boards}")
        print(f"  step_cells == env.step     : {n_ok}/{n_cmp}")
        print(f"  colour-swap control killed : {n_ctrl_killed}/{n_ctrl}")
        print(f"  tuck-only cells, free mode : {tuck_free} (over {boards} boards)")
        print(f"  tuck-only cells, gravity   : {tuck_grav}")
        if not tuck_free:
            print("  ⚠ no tuck-only placements found: a tuck arm is untestable on "
                  "these boards, so any tuck null here would be vacuous")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[2, 3, 4, 5, 6])
    ap.add_argument("--plies", type=int, nargs="+", default=[20, 35, 50])
    a = ap.parse_args()
    print(f"=== step_cells / env.step EQUIVALENCE GATE  seeds={a.seeds} "
          f"plies={a.plies} ===")
    ok = run(a.seeds, a.plies)
    print(f"\nGATE {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
