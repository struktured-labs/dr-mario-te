#!/usr/bin/env python3
"""CLEAN-BOARD gate, divergence side-question: how often does reach32 pick a
DIFFERENT root action than base32 would have on the identical board state,
and at what board height?

Drives each game with reach32 (matching the actual "on" arm reach_root_ab.py
plays), and at every decision additionally computes choose_base32 on the same
(fb, col, vir, ca, cb, na, nb) snapshot -- never used to drive, purely a
same-state comparison. Height bucketed via root_search.fill_height(fb) (max
column occupied height, ROWS=16 - top_occ, same definition destroy.py uses).

L11, no pressure, n=120 seeds -- paired with reach_root_ab.py's own arms by
construction (same seed range, same env/pill-source setup).
"""
from __future__ import annotations

import sys
import os
import json
import argparse
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

HEIGHT_BUCKETS = [(0, 3), (4, 6), (7, 9), (10, 12), (13, 16)]


def _bucket(h):
    for lo, hi in HEIGHT_BUCKETS:
        if lo <= h <= hi:
            return f"{lo}-{hi}"
    return "16+"


def _init(level):
    RR._lazy()
    _C.update(level=level)


def play(seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from root_search import fill_height

    level = _C["level"]
    L = RR._lazy()
    FB, RS = L["FB"], L["RS"]

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    decisions = []   # (height, divergent, fallback_unreachable, n_base_legal, n_reach)
    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb, na, nb = int(env.cur.a), int(env.cur.b), int(env.nxt.a), int(env.nxt.b)

        reach = RR.choose_reach32(fb, col, vir, ca, cb, na, nb)
        base = RR.choose_base32(col, vir, ca, cb, na, nb)

        h = fill_height(fb)
        divergent = int(reach["action"] != base["action"])
        decisions.append({
            "height": h, "divergent": divergent,
            "fallback_unreachable": int(reach.get("fallback_unreachable", False)),
            "n_base_legal": reach.get("n_base_legal"), "n_reach": reach.get("n_reach"),
        })

        # drive with reach32 -- matches reach_root_ab.py's "on" arm exactly
        action = reach["action"]
        if action is None:
            break
        _, _, term, trunc, info = env.step(int(action))
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break

    return {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"),
            "stall": int(res == "stall"), "pills": env.pills_placed,
            "decisions": decisions}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=120)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    print(f"=== reach32 vs base32 same-state divergence, L{a.level}, n={a.seeds} ===",
          flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(a.level,)) as ex:
        futs = [ex.submit(play, s) for s in range(a.seeds)]
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if (i + 1) % max(1, a.seeds // 5) == 0 or (i + 1) == a.seeds:
                print(f"  {i + 1}/{a.seeds}", flush=True)
    rows.sort(key=lambda r: r["seed"])

    # aggregate by height bucket
    bucket_total = {f"{lo}-{hi}": 0 for lo, hi in HEIGHT_BUCKETS}
    bucket_div = {f"{lo}-{hi}": 0 for lo, hi in HEIGHT_BUCKETS}
    bucket_fallback = {f"{lo}-{hi}": 0 for lo, hi in HEIGHT_BUCKETS}
    total = div_total = fallback_total = 0
    for r in rows:
        for d in r["decisions"]:
            b = _bucket(d["height"])
            bucket_total[b] = bucket_total.get(b, 0) + 1
            bucket_div[b] = bucket_div.get(b, 0) + d["divergent"]
            bucket_fallback[b] = bucket_fallback.get(b, 0) + d["fallback_unreachable"]
            total += 1
            div_total += d["divergent"]
            fallback_total += d["fallback_unreachable"]

    print(f"\ntotal decisions={total}  divergent={div_total} "
          f"({div_total / total:.2%})  fallback(all-32-unreachable)={fallback_total} "
          f"({fallback_total / total:.2%})", flush=True)
    print(f"{'height':>8s} {'n':>8s} {'divergent':>10s} {'rate':>8s} {'fallback':>9s}",
          flush=True)
    table = []
    for lo, hi in HEIGHT_BUCKETS:
        k = f"{lo}-{hi}"
        n = bucket_total[k]
        dv = bucket_div[k]
        fb_ = bucket_fallback[k]
        rate = dv / n if n else float("nan")
        print(f"{k:>8s} {n:>8d} {dv:>10d} {rate:>7.2%} {fb_:>9d}", flush=True)
        table.append({"height_bucket": k, "n": n, "divergent": dv, "rate": rate,
                       "fallback": fb_})

    summary = {"total_decisions": total, "divergent_total": div_total,
               "divergent_rate": div_total / total if total else float("nan"),
               "fallback_total": fallback_total,
               "fallback_rate": fallback_total / total if total else float("nan"),
               "height_table": table}

    if a.out:
        with open(a.out, "w") as fh:
            json.dump({"summary": summary,
                       "games": [{"seed": r["seed"], "won": r["won"],
                                  "topout": r["topout"], "stall": r["stall"],
                                  "pills": r["pills"]} for r in rows]}, fh)
        print(f"wrote {a.out}", flush=True)

    print("\nDONE")


if __name__ == "__main__":
    main()
