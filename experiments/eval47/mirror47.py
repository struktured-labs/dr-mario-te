#!/usr/bin/env python3
"""Task #47 MIRROR CONFIRMATION: re-prove the ws=20 stranded-half winner under
the RTL-faithful leaf_r47 mirror (leaf_vrdy12) -- the true silicon ruler.

The tuck-saga lesson (dr-mario-tuck-executor-gap memory) applied BEFORE
building anything: the fast_rtl_x variant("winner") chain the dose sweep ran
on is a documented approximation of the real firmware eval. A REAL result on
the approximation ruler (ws=20: pills -7.90 [-13.98,-1.68], stranded -66%,
deaths 5->1 at n=120) must reproduce under mirrored_leaf's chain, or it does
not ship.

Decider: base-only choose loop, mirrored_leaf.root_value_mirrored per action,
minus ws * g_stranded (terms47) -- the identical term the sweep tested, on the
identical seeds, with only the leaf ruler swapped. Control arm ws=0.

Usage: mirror47.py --seeds 120 --workers 8 --ws 20 --out results/mirror_ws20
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
           QA + "/tuck_v3", QA + "/bitexact_gate"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_C = {}


def _init(level, ws):
    import numpy as np
    import fast_rtl_x as FX
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    from terms47 import g_stranded
    z = np.zeros(128, dtype=np.int8)
    g_stranded(z, z)
    _C.update(level=level, ws=ws, w=w)


def _choose_base_mirror(col, vir, ca, cb, na, nb, w, ws):
    import numpy as np
    import fast_rtl_x as FX
    import mirrored_leaf as ML
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_stranded

    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_val, best_a = None, None
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = ML.root_value_mirrored(c1, v1, nv, cells, na, nb, 8,
                                         FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w)
            if ws:
                val -= ws * g_stranded(c1, v1)
            if best_val is None or val > best_val:
                best_val, best_a = val, var * 8 + cc
    return best_a


def play(seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS
    from terms47 import g_stranded

    level, ws, w = _C["level"], _C["ws"], _C["w"]
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    col = vir = None
    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        a = _choose_base_mirror(col, vir, int(env.cur.a), int(env.cur.b),
                                int(env.nxt.a), int(env.nxt.b), w, ws)
        if a is None:
            break
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break

    if col is None:
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
    return {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"),
            "stall": int(res == "stall"), "pills": env.pills_placed,
            "stranded_final": int(g_stranded(col, vir))}


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


def run_arm(level, seeds, workers, ws):
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(level, ws)) as ex:
        futs = [ex.submit(play, s) for s in range(seeds)]
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if (i + 1) % max(1, seeds // 5) == 0 or (i + 1) == seeds:
                _log_rss(f"MIRROR L{level} ws={ws} {i + 1}/{seeds}")
    print(f"  MIRROR arm ws={ws} done ({len(rows)} games)", flush=True)
    return {r["seed"]: r for r in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=120)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--ws", type=int, default=20)
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    print(f"=== #47 MIRROR CONFIRMATION (leaf_r47.leaf_vrdy12), L{a.level}, "
          f"n={a.seeds}, ws={a.ws} ===", flush=True)
    ctrl = run_arm(a.level, a.seeds, a.workers, 0)
    on = run_arm(a.level, a.seeds, a.workers, a.ws)

    ss = sorted(set(ctrl) & set(on))
    both = [s for s in ss if ctrl[s]["won"] and on[s]["won"]]
    d = [on[s]["pills"] - ctrl[s]["pills"] for s in both]
    lo, hi = boot_ci(d)
    c0 = sum(ctrl[s]["won"] for s in ss) / len(ss)
    c1 = sum(on[s]["won"] for s in ss) / len(ss)
    sd0 = st.mean([ctrl[s]["stranded_final"] for s in ss])
    sd1 = st.mean([on[s]["stranded_final"] for s in ss])
    tp0 = sum(ctrl[s]["topout"] + ctrl[s]["stall"] for s in ss)
    tp1 = sum(on[s]["topout"] + on[s]["stall"] for s in ss)
    verdict = "REAL" if (hi < 0 or lo > 0) else "WASH"
    print(f"\nMIRROR ws={a.ws}: pills {st.mean(d) if d else float('nan'):+.2f} "
          f"[{lo:+.2f},{hi:+.2f}] {verdict}  clear {c0:.1%}->{c1:.1%}  "
          f"stranded {sd0:.2f}->{sd1:.2f}  deaths+stalls {tp0}->{tp1}", flush=True)
    if a.out:
        with open(f"{a.out}.json", "w") as fh:
            json.dump({"ws": a.ws, "verdict": verdict,
                       "pills_delta": st.mean(d) if d else None, "ci": [lo, hi],
                       "clear0": c0, "clear1": c1, "stranded0": sd0, "stranded1": sd1,
                       "bad0": tp0, "bad1": tp1,
                       "ctrl": [ctrl[s] for s in sorted(ctrl)],
                       "on": [on[s] for s in sorted(on)]}, fh)
        print(f"wrote {a.out}.json")
    print("DONE")


if __name__ == "__main__":
    main()
