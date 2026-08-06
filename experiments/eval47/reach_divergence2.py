#!/usr/bin/env python3
"""CLEAN-BOARD gate, ITERATION 2 divergence side-question (task #60,
REACH_ROOT_VERDICT.md ITERATION 2 point 3c): drives each game with reach32t
(the new time-budgeted arm) -- matching reach_root_ab.py's own "on" arm
exactly -- and at every decision additionally computes choose_base32 AND
choose_reach32 on the IDENTICAL (fb, col, vir, ca, cb, na, nb) snapshot
(never used to drive, pure same-state comparison). Reports:
  - reach32t vs base32 divergence, bucketed by board height (acceptance:
    divergence should concentrate on HIGH boards, not bind on clean/low ones)
  - reach32t vs reach32 divergence (does the time-budget filter, under the
    corrected 12/30 DAS constants, ever change the pick reach32 alone would
    have made? The M3 case study found 0/6 -- this checks it at scale)

Same shape as reach_divergence.py (which does the reach32-vs-base32 version);
new file rather than editing that one so the already-published clean-gate
numbers for reach32 stay exactly reproducible.
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
    decisions = []
    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb, na, nb = int(env.cur.a), int(env.cur.b), int(env.nxt.a), int(env.nxt.b)

        timed = RR.choose_reach32t(fb, col, vir, ca, cb, na, nb)
        base = RR.choose_base32(col, vir, ca, cb, na, nb)
        reach = RR.choose_reach32(fb, col, vir, ca, cb, na, nb)

        h = fill_height(fb)
        div_base = int(timed["action"] != base["action"])
        div_reach32 = int(timed["action"] != reach["action"])
        decisions.append({
            "height": h, "divergent_base32": div_base, "divergent_reach32": div_reach32,
            "fallback_time": int(timed.get("fallback_time", False)),
            "fallback_unreachable": int(timed.get("fallback_unreachable", False)),
            "n_reach": timed.get("n_reach"), "n_within_budget": timed.get("n_within_budget"),
        })

        action = timed["action"]           # drive with reach32t -- matches
        if action is None:                 # reach_root_ab.py's "on" arm exactly
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
    ap.add_argument("--seeds", type=int, default=40)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    print(f"=== reach32t vs base32/reach32 same-state divergence, L{a.level}, n={a.seeds} ===",
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

    bucket_total = {f"{lo}-{hi}": 0 for lo, hi in HEIGHT_BUCKETS}
    bucket_div_base = {f"{lo}-{hi}": 0 for lo, hi in HEIGHT_BUCKETS}
    bucket_div_reach32 = {f"{lo}-{hi}": 0 for lo, hi in HEIGHT_BUCKETS}
    bucket_fbtime = {f"{lo}-{hi}": 0 for lo, hi in HEIGHT_BUCKETS}
    total = div_base_total = div_reach32_total = fbtime_total = fbunreach_total = 0
    for r in rows:
        for d in r["decisions"]:
            b = _bucket(d["height"])
            bucket_total[b] = bucket_total.get(b, 0) + 1
            bucket_div_base[b] = bucket_div_base.get(b, 0) + d["divergent_base32"]
            bucket_div_reach32[b] = bucket_div_reach32.get(b, 0) + d["divergent_reach32"]
            bucket_fbtime[b] = bucket_fbtime.get(b, 0) + d["fallback_time"]
            total += 1
            div_base_total += d["divergent_base32"]
            div_reach32_total += d["divergent_reach32"]
            fbtime_total += d["fallback_time"]
            fbunreach_total += d["fallback_unreachable"]

    print(f"\ntotal decisions={total}  "
          f"divergent_vs_base32={div_base_total} ({div_base_total / total:.2%})  "
          f"divergent_vs_reach32={div_reach32_total} ({div_reach32_total / total:.2%})  "
          f"fallback_time(reach-set-nonempty-but-none-in-budget)={fbtime_total} "
          f"({fbtime_total / total:.2%})  "
          f"fallback_unreachable(all-32-unreachable)={fbunreach_total}", flush=True)
    print(f"{'height':>8s} {'n':>8s} {'div_base32':>11s} {'rate':>8s} "
          f"{'div_reach32':>12s} {'rate':>8s} {'fbtime':>7s}", flush=True)
    table = []
    for lo, hi in HEIGHT_BUCKETS:
        k = f"{lo}-{hi}"
        n = bucket_total[k]
        dvb, dvr, fbt = bucket_div_base[k], bucket_div_reach32[k], bucket_fbtime[k]
        rate_b = dvb / n if n else float("nan")
        rate_r = dvr / n if n else float("nan")
        print(f"{k:>8s} {n:>8d} {dvb:>11d} {rate_b:>7.2%} {dvr:>12d} {rate_r:>7.2%} {fbt:>7d}",
              flush=True)
        table.append({"height_bucket": k, "n": n, "divergent_vs_base32": dvb,
                       "rate_vs_base32": rate_b, "divergent_vs_reach32": dvr,
                       "rate_vs_reach32": rate_r, "fallback_time": fbt})

    summary = {"total_decisions": total,
               "divergent_vs_base32_total": div_base_total,
               "divergent_vs_base32_rate": div_base_total / total if total else float("nan"),
               "divergent_vs_reach32_total": div_reach32_total,
               "divergent_vs_reach32_rate": div_reach32_total / total if total else float("nan"),
               "fallback_time_total": fbtime_total,
               "fallback_unreachable_total": fbunreach_total,
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
