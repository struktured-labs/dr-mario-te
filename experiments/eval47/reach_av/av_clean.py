#!/usr/bin/env python3
"""CLEAN-SOLO SAFETY CHECK for an A_v arm.

The champion's clean (no-pressure) failure rate is 0.0809% (53 / 65,536, full-space
census).  A pressure-regime win is not worth a clean-regime regression, so the
pre-registered auto-kill is: clean failure rate > 0.25% on the best arm.

Failure = the game does not end in a full clear (topout or 300-pill stall), the
census's own taxonomy.

Seeds: canonical even seeds (the LFSR discards the low bit -- 2k and 2k+1 are the
same game), drawn in a fixed shuffled order so any prefix is a uniform sample.
Both arms run the SAME seeds -> paired.

`--selfcheck` proves this file's clean loop at reach=0/w=8 reproduces the
adversary census harness (adversary_harness.play_seed) result-for-result.

Usage:
  av_clean.py --selfcheck --seeds 60 --workers 6
  av_clean.py --seeds 2000 --workers 6 --arm-reach 1 --arm-w 24 --out results/av_clean
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import reach_leaf as RL

LEVEL = 11
WS = 20
WT = 0
MAX_PILLS = 300
SHUFFLE_RNG_SEED = 20260808

_C = {}


def canonical_seeds(n, rng_seed=SHUFFLE_RNG_SEED):
    """n distinct canonical seeds (even), skipping the k=0 degenerate region."""
    ks = list(range(1, 32768))
    random.Random(rng_seed).shuffle(ks)
    return [2 * k for k in ks[:n]]


def _init(reach, w_rdyext):
    RL.warmup()
    w, fl = RL.weights_for(w_rdyext)
    _C.update(reach=int(reach), w=w, fl=fl)


def play_clean(seed):
    """One clean L11 solo game.  Loop mirrors adversary_harness.play_seed()'s
    conventions (same env, same pill source, same 300-pill cap, same taxonomy)."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS

    reach, w, fl = _C["reach"], _C["w"], _C["fl"]
    env = FaithfulDrMarioEnv(level=LEVEL, seed=seed, max_pills=MAX_PILLS)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    for _ in range(MAX_PILLS):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        fb = FB.from_board(env.board)
        col, vir = RS.board_flat_from_fb(fb)
        a, _c1 = RL.choose_base_rx(col, vir, int(env.cur.a), int(env.cur.b),
                                   int(env.nxt.a), int(env.nxt.b), w, fl, WT, WS, reach)
        if a is None:
            res = "topout"
            break
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            res = "stall"
            break
    return {"seed": seed, "result": res, "pills": env.pills_placed,
            "viruses_left": env.board.virus_count(),
            "fail": int(res != "clear")}


def run_arm(seeds, workers, reach, w_rdyext, label):
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(reach, w_rdyext)) as ex:
        futs = [ex.submit(play_clean, s) for s in seeds]
        done = 0
        for f in as_completed(futs):
            rows.append(f.result())
            done += 1
            if done % max(1, len(seeds) // 10) == 0:
                nf = sum(r["fail"] for r in rows)
                print(f"    {label}: {done}/{len(seeds)}  failures so far {nf}",
                      flush=True)
    d = {r["seed"]: r for r in rows}
    nf = sum(r["fail"] for r in rows)
    print(f"  {label}: {nf}/{len(rows)} failures = {nf / len(rows):.4%}", flush=True)
    return d


def selfcheck(n, workers):
    """reach=0/w=8 through this file must reproduce the census harness exactly."""
    sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/experiments/adversary")
    import adversary_harness as AH
    seeds = canonical_seeds(n)
    mine = run_arm(seeds, workers, 0, 8.0, "this-file reach=0 w=8")
    bad = []
    for s in seeds:
        ref = AH.play_seed(s)
        if ref["result"] != mine[s]["result"] or ref["pills"] != mine[s]["pills"]:
            bad.append(f"seed {s}: census {ref['result']}/{ref['pills']} != "
                       f"mine {mine[s]['result']}/{mine[s]['pills']}")
    if bad:
        print(f"SELFCHECK FAILED -- {len(bad)}/{n}:")
        for x in bad[:15]:
            print("   ", x)
        return False
    print(f"SELFCHECK PASSED: {n} seeds, result+pills identical to "
          f"adversary_harness.play_seed", flush=True)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=2000)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--arm-reach", type=int, default=1)
    ap.add_argument("--arm-w", type=float, default=24.0)
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--baseline", action="store_true", default=True,
                    help="also run the champion on the same seeds (paired)")
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    RL.warmup()
    print(f"=== CLEAN-SOLO SAFETY  kernel_hash={RL.kernel_hash()} ===", flush=True)
    if a.selfcheck:
        return 0 if selfcheck(a.seeds, a.workers) else 1

    seeds = canonical_seeds(a.seeds)
    print(f"n={len(seeds)} canonical seeds, L{LEVEL}, no pressure, "
          f"arm = reach{a.arm_reach} w_rdyext={a.arm_w:g}", flush=True)
    arm = run_arm(seeds, a.workers, a.arm_reach, a.arm_w,
                  f"A_v reach={a.arm_reach} w={a.arm_w:g}")
    base = run_arm(seeds, a.workers, 0, 8.0, "champion reach=0 w=8") if a.baseline else None

    nf = sum(arm[s]["fail"] for s in seeds)
    rate = nf / len(seeds)
    out = {"kernel_hash": RL.kernel_hash(), "n": len(seeds),
           "arm": RL.arm_stamp(a.arm_reach, a.arm_w, WT, WS),
           "arm_failures": nf, "arm_rate": rate,
           "arm_failed_seeds": [s for s in seeds if arm[s]["fail"]],
           "auto_kill_threshold": 0.0025,
           "verdict": "KILL" if rate > 0.0025 else "pass"}
    print(f"\n  ARM      : {nf}/{len(seeds)} = {rate:.4%}   "
          f"(auto-kill if > 0.2500%)  -> {out['verdict'].upper()}")
    if base is not None:
        nb = sum(base[s]["fail"] for s in seeds)
        out.update(base_failures=nb, base_rate=nb / len(seeds),
                   base_failed_seeds=[s for s in seeds if base[s]["fail"]])
        print(f"  CHAMPION : {nb}/{len(seeds)} = {nb / len(seeds):.4%}  "
              f"(full-space census reference: 0.0809%)")
        b = sum(1 for s in seeds if base[s]["fail"] and not arm[s]["fail"])
        c = sum(1 for s in seeds if not base[s]["fail"] and arm[s]["fail"])
        out.update(discordant_b=b, discordant_c=c)
        print(f"  paired   : discordant b={b} (champ fails, arm clears) "
              f"c={c} (champ clears, arm fails)")
    if a.out:
        with open(f"{a.out}.json", "w") as fh:
            json.dump(out, fh, indent=1)
        print(f"wrote {a.out}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
