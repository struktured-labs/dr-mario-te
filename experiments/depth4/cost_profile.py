#!/usr/bin/env python3
"""COST PROFILE BY VIRUS COUNT — is depth-4 affordable if gated to the endgame?

THE QUESTION.  The headline 22.9x is an ALL-GAME AVERAGE, and a game spends most of its
decisions on open/mid boards.  The d4 rescues were all endgame topouts, and the endgame is
where search is cheapest (sparse board, fewer legal placements, fewer surviving ply-2
nodes).  So: what does d4 cost *in the endgame specifically*?

WHAT TRANSFERS TO THE COPRO, AND WHAT DOES NOT.  The absolute ms here are x86 + numba and
mean nothing on an FPGA.  The **ratio** d4/d3 within a bucket is the quantity that
approximately transfers, because both arms run the same leaf on the same boards and the
per-leaf cost cancels.  It is still only approximate: the copro's cost is dominated by
leaf-evaluation count and memory traffic, and this measurement additionally carries
python-side per-node overhead that the copro does not have.  Treat the ratio as an
ESTIMATE OF THE RIGHT ORDER, not a budget figure, and confirm any near-boundary answer
with a leaf-count model before committing silicon time.

BUCKETS follow the project's standard regime gate: open vc>32, mid 9..32, end vc<=8.
Boards come off REAL d3 trajectories on the REAL NES capsule stream, so each bucket holds
positions the shipped brain actually reaches at that virus count -- not synthetic fills,
which would misstate the branching factor that drives the cost.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys
import time
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
for _p in (HERE, os.path.join(HERE, "snap"), ROOT + "/tmp/pillrng",
           ROOT + "/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fast_rtl_x as F                                            # noqa: E402
import d4_kernel as K                                             # noqa: E402
from fast_sim_x import (board_flat, _resting, _virus_count,       # noqa: E402
                        _expand_core, NCELL)
from fast_rtl_x import _W_EXCAV_SHIP, _W_HANG_SHIP, _VAR_OF_O4    # noqa: E402


def regime(vc):
    return "open" if vc > 32 else ("mid" if vc > 8 else "end")


# ---------------------------------------------------------------- dv_fallback rate
# WHAT THIS IS AND IS NOT.  The delta engine falls back to a full rescan whenever a
# placement CLEARS (gravity can move every column, so the closed form does not hold) --
# `_expand_leaf_delta` raises it exactly when `_any_clear_lines` fires, mirroring
# LeafEval.sv's `dv_fallback`.  A lower fallback rate means the delta pays off more.
#
# I cannot count it inside the search: the kernel is njit AND hash-pinned, and editing
# `snap/` to add a counter would void the provenance the whole experiment rests on.  So
# this MEASURES THE SAME PREDICATE OUTSIDE the search, using the kernel's own
# `_expand_core` (cells > 0 IS the fallback condition) -- no reimplementation of the
# clear test, no divergence risk.
#
# ⚠ It is a SAMPLED estimate at the plies that matter, not the search's true rate.  Most
# of d4's leaves live at ply 4, so measuring the root board would answer the wrong
# question; instead we descend `depth` RANDOM legal placements first and measure there.
# Random descent is not the search's own topk-guided descent, so read this as "the
# fallback rate in the region of the tree d4 spends its time in", accurate to the board
# DEPTH but not to the search's selection bias.
def _descend(col, vir, rng, steps):
    """Apply `steps` random legal placements; return the resulting board or None."""
    c = col.copy(); v = vir.copy()
    oc = np.empty(NCELL, dtype=np.int8); ov = np.empty(NCELL, dtype=np.int8)
    for _ in range(steps):
        legal = [(int(_VAR_OF_O4[o]), cl) for o in range(4) for cl in range(8)
                 if _resting(c, int(_VAR_OF_O4[o]), cl)[0]]
        if not legal:
            return None
        var, cl = legal[int(rng.integers(len(legal)))]
        pa = int(rng.integers(1, 4)); pb = int(rng.integers(1, 4))
        ok, _nv, _cells = _expand_core(c, v, var, cl, pa, pb, oc, ov)
        if not ok:
            return None
        c = oc.copy(); v = ov.copy()
        if _virus_count(v) == 0:
            return None
    return c, v


def fallback_rate(col, vir, rng, depth, reps):
    """Fraction of legal placements that CLEAR (=> dv_fallback), at ply-`depth` boards."""
    oc = np.empty(NCELL, dtype=np.int8); ov = np.empty(NCELL, dtype=np.int8)
    tot = 0; cleared = 0
    for _ in range(reps):
        d = _descend(col, vir, rng, depth)
        if d is None:
            continue
        c, v = d
        pa = int(rng.integers(1, 4)); pb = int(rng.integers(1, 4))
        for o in range(4):
            var = int(_VAR_OF_O4[o])
            for cl in range(8):
                ok, _nv, cells = _expand_core(c, v, var, cl, pa, pb, oc, ov)
                if ok == 0:
                    continue
                tot += 1
                cleared += (cells > 0)
    return (cleared / tot) if tot else float("nan"), tot


def legal_ply1(col):
    """Legal placements at the root (0..32) -- the branching factor that drives cost."""
    n = 0
    for o4 in range(4):
        var = int(_VAR_OF_O4[o4])
        for c in range(8):
            if _resting(col, var, c)[0]:
                n += 1
    return n


def collect(n_per_bucket, level, seed0, arm, stream):
    """Walk real d3 games, keeping boards until every bucket is full."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    w, fl = F.variant(arm)
    dec = F.FastShipD3DeciderEHDelta(w, fl, topk2=8)
    buckets = defaultdict(list)
    s = seed0
    while any(len(buckets[k]) < n_per_bucket for k in ("open", "mid", "end")):
        if s > seed0 + 4000:
            break
        env = FaithfulDrMarioEnv(level=level, seed=s, max_pills=300)
        env.reset()
        if stream == "nes":
            from nes_pills import NesPillSource
            NesPillSource(seed=s).attach(env)
            env.cur = env._rand_pill(); env.nxt = env._rand_pill()
        s += 1
        while True:
            col, vir = board_flat(env.board)
            vc = int(_virus_count(vir))
            k = regime(vc)
            if len(buckets[k]) < n_per_bucket:
                buckets[k].append((col.copy(), vir.copy(), env.cur.a, env.cur.b,
                                   env.nxt.a, env.nxt.b, vc))
            a = dec.choose(env.board, env.cur, env.nxt)
            if a is None:
                break
            _o, _r, term, trunc, _i = env.step(int(a))
            if term or trunc:
                break
    return buckets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-bucket", type=int, default=60)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--seed0", type=int, default=4000)
    ap.add_argument("--arm", default="winner")
    ap.add_argument("--stream", default="nes")
    ap.add_argument("--topk3", type=int, default=6)
    ap.add_argument("--pills4", default="4")
    ap.add_argument("--copro-d3-frames", type=float, default=24.0,
                    help="measured copro d3 DONE median in the endgame (frames)")
    ap.add_argument("--copro-budget-frames", type=float, default=80.0)
    ap.add_argument("--fb-depth", type=int, default=3,
                    help="plies to descend before measuring the dv_fallback rate")
    ap.add_argument("--fb-reps", type=int, default=6)
    ap.add_argument("--out", default="cost_profile.json")
    a = ap.parse_args()

    w, fl = F.variant(a.arm)
    F.warmup_delta(); K.warmup_d4(topk3=a.topk3, pills4=a.pills4)
    p4x, p4y = K._P4[str(a.pills4)]
    print(f"collecting real {a.stream} boards, {a.per_bucket}/bucket ...", flush=True)
    buckets = collect(a.per_bucket, a.level, a.seed0, a.arm, a.stream)

    out = {"args": vars(a), "buckets": {}}
    print(f"\n=== COST BY REGIME  L{a.level} {a.stream} topk3={a.topk3} "
          f"pills4={a.pills4} ===")
    print(f"{'bucket':>6} {'n':>4} {'vc':>7} {'branch':>7} {'d3 ms':>9} {'d4 ms':>9} "
          f"{'ratio':>7} {'dv_fb':>7}")
    rng = np.random.default_rng(31337)
    for k in ("open", "mid", "end"):
        rows = buckets.get(k, [])
        if not rows:
            continue
        br = st.mean([legal_ply1(r[0]) for r in rows])
        vcm = st.mean([r[6] for r in rows])
        fbs = []
        for (col, vir, *_r) in rows:
            fr, n_obs = fallback_rate(col, vir, rng, a.fb_depth, a.fb_reps)
            if n_obs:
                fbs.append(fr)
        fb = st.mean(fbs) if fbs else float("nan")
        t3 = []
        t4 = []
        for (col, vir, ca, cb, na, nb, _vc) in rows:
            t0 = time.process_time()
            F._choose_d3_ship_eh_delta(col, vir, ca, cb, na, nb, 8,
                                       int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
            t3.append((time.process_time() - t0) * 1e3)
            t0 = time.process_time()
            K._choose_d4_ship_eh_delta(col, vir, ca, cb, na, nb, 8, a.topk3, 1, p4x, p4y,
                                       int(_W_EXCAV_SHIP), int(_W_HANG_SHIP), w, fl)
            t4.append((time.process_time() - t0) * 1e3)
        m3, m4 = st.median(t3), st.median(t4)
        print(f"{k:>6} {len(rows):>4} {vcm:>7.1f} {br:>7.1f} {m3:>9.2f} {m4:>9.2f} "
              f"{m4/m3:>6.1f}x {fb:>6.1%}")
        out["buckets"][k] = {"n": len(rows), "mean_vc": vcm, "mean_branch": br,
                             "d3_ms_median": m3, "d4_ms_median": m4, "ratio": m4 / m3,
                             "d3_ms_mean": st.mean(t3), "d4_ms_mean": st.mean(t4),
                             "dv_fallback_rate": fb, "dv_fallback_n_boards": len(fbs)}
    print(f"  dv_fb = fraction of legal placements that CLEAR (=> delta falls back to a "
          f"full rescan),\n        sampled at ply-{a.fb_depth} boards reached by RANDOM "
          f"legal descent, {a.fb_reps} reps/board.\n        Lower = the delta pays off "
          f"more. Measured OUTSIDE the search via the kernel's own _expand_core;\n"
          f"        accurate to board DEPTH, not to the search's topk selection bias.")

    end = out["buckets"].get("end")
    if end:
        est = a.copro_d3_frames * end["ratio"]
        print(f"\n--- COPRO BUDGET ARITHMETIC (endgame gate) ---")
        print(f"  input: copro d3 endgame DONE median = {a.copro_d3_frames:.0f}f, "
              f"budget = {a.copro_budget_frames:.0f}f   [team-lead's figures]")
        print(f"  endgame ratio measured here        = {end['ratio']:.1f}x")
        print(f"  => estimated d4 endgame DONE       = {est:.0f}f   "
              f"{'FITS' if est <= a.copro_budget_frames else 'DOES NOT FIT'} "
              f"({est/a.copro_budget_frames:.2f}x budget)")
        print("  NOTE: ratio is an x86/numba estimate; it carries python per-node overhead")
        print("        the copro lacks, and the copro's cost tracks LEAF COUNT more than")
        print("        wall time. Confirm with a leaf-count model before spending silicon.")
        out["copro_estimate"] = {"d3_frames": a.copro_d3_frames,
                                 "budget_frames": a.copro_budget_frames,
                                 "ratio": end["ratio"], "d4_frames_est": est,
                                 "fits": bool(est <= a.copro_budget_frames)}
    json.dump(out, open(os.path.join(HERE, a.out), "w"), indent=2, default=float)
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
