#!/usr/bin/env python3
"""Task #47 GARBAGE-PRESSURE rig: ab47.py plus a simulated human opponent's
counter-attack channel.  Identical paired A/B skeleton (base-only decider,
wt/ws knobs, worker processes) but every game takes garbage:

  After every fully-resolved placement once pills_placed >= 25, every 8th
  placement (pills_placed % 8 == 0) injects k=2 garbage halves: 2 DISTINCT
  random columns (rng = random.Random(seed*1000 + pills_placed) for
  reproducibility), each getting ONE unlinked single half of a random color
  (1..3) at the topmost empty cell of that column (skip silently if the
  column's row-0 cell is occupied).  Then board.resolve() so the halves fall
  and accidental matches resolve, then re-check spawn_blocked() -> 'topout'
  (the death mode under measurement) and virus_count()==0 -> 'clear'.

All ab47 metrics kept (funnel_mm, mm_vert, stranded_final, tower_final,
deaths+stalls) plus garbage_injected per game.  Usage:
  pressure_rig.py --seeds 120 --workers 6 --arms 0:20 --out r
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

_C = {}

H0 = 8   # height where the tower tax starts; fixed across arms this pass

GARBAGE_MIN_PILLS = 25   # injections start once pills_placed >= this
GARBAGE_PERIOD = 8       # ... on every placement where pills_placed % this == 0
GARBAGE_K = 2            # halves per injection event


def _init(level, wt, ws):
    import numpy as np
    import fast_rtl_x as FX
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    from terms47 import g_tower, g_stranded
    # jit warmup on a dummy board so play() never pays compile time
    z = np.zeros(128, dtype=np.int8)
    g_tower(z, z, H0)
    g_stranded(z, z)
    _C.update(level=level, wt=wt, ws=ws, w=w, fl=fl)


def _choose_base(col, vir, ca, cb, na, nb, w, fl, wt, ws):
    import numpy as np
    import fast_rtl_x as FX
    import root_search as RS
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_tower, g_stranded

    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_val, best_a, best_c1 = None, None, None
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            if wt:
                val -= wt * g_tower(c1, v1, H0)
            if ws:
                val -= ws * g_stranded(c1, v1)
            if best_val is None or val > best_val:
                best_val, best_a, best_c1 = val, var * 8 + cc, c1.copy()
    return best_a, best_c1


def _inject_garbage(board, seed, pills_placed):
    """Drop GARBAGE_K unlinked single halves into distinct random columns.

    Returns the number of halves actually placed (columns whose row-0 cell is
    occupied are skipped silently)."""
    from drmario.faithful_game import EMPTY, LINK_NONE

    rng = random.Random(seed * 1000 + pills_placed)
    cols = rng.sample(range(board.cols), GARBAGE_K)
    placed = 0
    for c in cols:
        color = rng.randint(1, 3)
        if board.color[0, c] != EMPTY:
            continue   # column full to the top -- skip silently
        r = 0
        while r < board.rows and board.color[r, c] != EMPTY:
            r += 1   # first empty row from the top (r=0 unless overhang)
        board.color[r, c] = color
        board.is_virus[r, c] = False
        board.link[r, c] = LINK_NONE   # plain single half, no partner
        placed += 1
    if placed:
        # resolve() only runs gravity AFTER a clear step, so a half parked at
        # row 0 with no match would float forever (and fake a spawn-block).
        # Drop the halves explicitly first, then resolve accidental matches.
        board._apply_gravity()
        board.resolve()
    return placed


def play(seed):
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS
    from terms47 import g_tower, g_stranded

    level, wt, ws, w, fl = _C["level"], _C["wt"], _C["ws"], _C["w"], _C["fl"]
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    funnel = 0        # all repeated same-column verticals (includes GOOD monocolor stacking)
    funnel_mm = 0     # repeated same-column verticals whose bottom half lands on a
                      # DIFFERENT colour -- the actual disease signature
    mm_vert = 0       # every mismatched-support vertical, streak or not
    garbage_injected = 0
    last_vert_col = -1
    col = vir = None
    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        a, c1b = _choose_base(col, vir, int(env.cur.a), int(env.cur.b),
                              int(env.nxt.a), int(env.nxt.b), w, fl, wt, ws)
        if a is None:
            break
        var, cc = a // 8, a % 8
        vertical = var in (2, 3)   # o4 {0,1}=VERT -> _VAR_OF_O4 maps them to var {2,3}
        mism = False
        if vertical:
            # bottom NEW cell in the placed column vs its support cell's colour
            newr = [r for r in range(16) if c1b[r * 8 + cc] != col[r * 8 + cc]]
            if newr:
                rb = max(newr)
                if rb < 15 and col[(rb + 1) * 8 + cc] != 0:
                    mism = c1b[rb * 8 + cc] != col[(rb + 1) * 8 + cc]
        if mism:
            mm_vert += 1
        if vertical and cc == last_vert_col:
            funnel += 1
            if mism:
                funnel_mm += 1
        last_vert_col = cc if vertical else -1
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break
        # --- GARBAGE PRESSURE: after the placement is fully resolved and the
        # win/topout checks above have passed ---
        if (env.pills_placed >= GARBAGE_MIN_PILLS
                and env.pills_placed % GARBAGE_PERIOD == 0):
            garbage_injected += _inject_garbage(env.board, seed, env.pills_placed)
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"   # the death mode we are measuring
                break

    if col is None:
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
    return {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"),
            "stall": int(res == "stall"), "pills": env.pills_placed,
            "funnel": funnel, "funnel_mm": funnel_mm, "mm_vert": mm_vert,
            "garbage_injected": garbage_injected,
            "stranded_final": int(g_stranded(col, vir)),
            "tower_final": int(g_tower(col, vir, H0))}


def boot_ci(xs, stat=st.mean, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = [stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n)]
    reps.sort()
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def _log_rss(tag):
    import subprocess
    try:
        out = subprocess.run(
            ["bash", "-c", "ps -o rss= -C python 2>/dev/null | awk '{s+=$1} END {print s+0}'"],
            capture_output=True, text=True, timeout=10)
        print(f"  [RSS] {tag}: {int(out.stdout.strip() or 0)/1024:.0f} MB total python",
              flush=True)
    except Exception as e:
        print(f"  [RSS] {tag}: failed ({e})", flush=True)


def run_arm(level, seeds, workers, wt, ws):
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(level, wt, ws)) as ex:
        futs = [ex.submit(play, s) for s in range(seeds)]
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if (i + 1) % max(1, seeds // 5) == 0 or (i + 1) == seeds:
                _log_rss(f"L{level} wt={wt} ws={ws} {i + 1}/{seeds}")
    print(f"  arm wt={wt} ws={ws} done ({len(rows)} games)", flush=True)
    return {r["seed"]: r for r in rows}


def compare(ctrl, arm, tag):
    ss = sorted(set(ctrl) & set(arm))
    both = [s for s in ss if ctrl[s]["won"] and arm[s]["won"]]
    d = [arm[s]["pills"] - ctrl[s]["pills"] for s in both]
    lo, hi = boot_ci(d)
    c0 = sum(ctrl[s]["won"] for s in ss) / len(ss)
    c1 = sum(arm[s]["won"] for s in ss) / len(ss)
    fn0 = st.mean([ctrl[s]["funnel_mm"] for s in ss])
    fn1 = st.mean([arm[s]["funnel_mm"] for s in ss])
    mv0 = st.mean([ctrl[s]["mm_vert"] for s in ss])
    mv1 = st.mean([arm[s]["mm_vert"] for s in ss])
    sd0 = st.mean([ctrl[s]["stranded_final"] for s in ss])
    sd1 = st.mean([arm[s]["stranded_final"] for s in ss])
    gb0 = st.mean([ctrl[s]["garbage_injected"] for s in ss])
    gb1 = st.mean([arm[s]["garbage_injected"] for s in ss])
    tp0 = sum(ctrl[s]["topout"] + ctrl[s]["stall"] for s in ss)
    tp1 = sum(arm[s]["topout"] + arm[s]["stall"] for s in ss)
    verdict = "REAL" if (hi < 0 or lo > 0) else "WASH"
    print(f"{tag}: pills {st.mean(d) if d else float('nan'):+.2f} [{lo:+.2f},{hi:+.2f}] "
          f"{verdict}  clear {c0:.1%}->{c1:.1%}  funnelMM/g {fn0:.2f}->{fn1:.2f}  "
          f"mmvert/g {mv0:.2f}->{mv1:.2f}  stranded {sd0:.2f}->{sd1:.2f}  "
          f"garbage/g {gb0:.2f}->{gb1:.2f}  deaths+stalls {tp0}->{tp1}", flush=True)
    return {"tag": tag, "pills_delta": st.mean(d) if d else None, "ci": [lo, hi],
            "verdict": verdict, "clear0": c0, "clear1": c1, "funnel0": fn0,
            "funnel1": fn1, "mmvert0": mv0, "mmvert1": mv1,
            "stranded0": sd0, "stranded1": sd1,
            "garbage0": gb0, "garbage1": gb1,
            "bad_ends0": tp0, "bad_ends1": tp1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=120)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--arms", type=str, nargs="+", default=["2:0", "6:0", "18:0", "0:50", "6:50"],
                    help="wt:ws dose pairs; control 0:0 always runs first")
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    print(f"=== #47 GARBAGE-PRESSURE A/B, L{a.level}, n={a.seeds}, H0={H0}, "
          f"garbage k={GARBAGE_K}/{GARBAGE_PERIOD} pills from {GARBAGE_MIN_PILLS}, "
          f"arms={a.arms} ===", flush=True)
    ctrl = run_arm(a.level, a.seeds, a.workers, 0, 0)

    results = []
    for arm in a.arms:
        wt, ws = (int(x) for x in arm.split(":"))
        on = run_arm(a.level, a.seeds, a.workers, wt, ws)
        results.append(compare(ctrl, on, f"wt={wt} ws={ws}"))
        if a.out:
            with open(f"{a.out}_wt{wt}_ws{ws}.json", "w") as fh:
                json.dump({"summary": results[-1],
                           "ctrl": [ctrl[s] for s in sorted(ctrl)],
                           "arm": [on[s] for s in sorted(on)]}, fh)

    print("\n=== SUMMARY (control funnel/stranded shown in each row) ===")
    for r in results:
        if r["pills_delta"] is None:
            r = dict(r, pills_delta=float("nan"))
        print(f"  {r['tag']:>14s}  pills {r['pills_delta']:+7.2f} [{r['ci'][0]:+7.2f},{r['ci'][1]:+7.2f}] "
              f"{r['verdict']}  clear {r['clear0']:.1%}->{r['clear1']:.1%}  "
              f"funnel {r['funnel0']:.2f}->{r['funnel1']:.2f}  "
              f"stranded {r['stranded0']:.2f}->{r['stranded1']:.2f}  "
              f"garbage {r['garbage0']:.2f}->{r['garbage1']:.2f}  "
              f"badends {r['bad_ends0']}->{r['bad_ends1']}")
    print("\nDONE")


if __name__ == "__main__":
    main()
