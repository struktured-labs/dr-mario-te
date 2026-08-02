#!/usr/bin/env python3
"""Does the delta-backed decider agree with the canonical one AT THE WEIGHTS I SWEEP?

The delta lane proved `FastShipD3DeciderEHDelta == FastShipD3DeciderEH` by fuzz and by
byte-identical full-game action sequences -- at the SHIPPED weights. This screen varies
constants well off that point (toprisk 45..180, spawn 100..300), and an incremental
evaluator is exactly the kind of code whose equivalence can be weight-dependent: the delta
path recomputes only what a placement touches, so a term that is inert at one weight and
dominant at another can expose a stale-base bug that the shipped-weight fuzz never reaches.

If they diverge anywhere in the grid, every win rate I measure is of a different function
than the one that ships. So: for EVERY candidate in the sweep grid, play whole L11 games on
real NES capsules with both deciders and require byte-identical action sequences.
"""
from __future__ import annotations
import sys, os, argparse
from concurrent.futures import ProcessPoolExecutor

ROOT = "/home/struktured/projects/dr_mario_rl"
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

from h2h_vs import WINNER
from sweep_knobs import GRID


def _mk(cls_name, cand, topk2=8):
    import fast_rtl_x as F
    w, fl = F.variant("winner")
    for k, idx in (("vrdy", F.R_VRDY), ("buried", F.R_BURIED), ("rdyext", F.R_RDYEXT),
                   ("setup", F.R_SETUP), ("matched", F.R_MATCHED), ("poll", F.R_POLL),
                   ("maxh", F.R_MAXH), ("holes", F.R_HOLES), ("toprisk", F.R_TOPRISK),
                   ("spawn", F.R_SPAWN)):
        w[idx] = float(cand[k])
    return getattr(F, cls_name)(w, fl, topk2=topk2)


def _play(dec, seed, level, max_pills):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill(); env.nxt = env._rand_pill()
    acts = []
    while True:
        a = dec.choose(env.board, env.cur, env.nxt)
        if a is None:
            break
        acts.append(int(a))
        _, _, term, trunc, _ = env.step(int(a))
        if term or trunc:
            break
    return acts


def _job(args):
    label, cand, seeds, level, max_pills = args
    import fast_rtl_x as F
    F.warmup_ship_eh(topk2=8); F.warmup_delta(topk2=8)
    ref = _mk("FastShipD3DeciderEH", cand)
    dlt = _mk("FastShipD3DeciderEHDelta", cand)
    bad = []
    for s in seeds:
        a = _play(ref, s, level, max_pills)
        b = _play(dlt, s, level, max_pills)
        if a != b:
            i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
            bad.append((s, i, len(a), len(b)))
    return label, len(seeds), bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    a = ap.parse_args()

    seeds = list(range(400, 400 + a.seeds))
    jobs = [("winner(base)", dict(WINNER), seeds, a.level, a.max_pills)]
    for knob, vals in GRID.items():
        for v in vals:
            if v == WINNER[knob]:
                continue
            c = dict(WINNER); c[knob] = v
            jobs.append((f"{knob}={v}", c, seeds, a.level, a.max_pills))

    print(f"DELTA EQUIVALENCE ACROSS THE SWEEP GRID  ({len(jobs)} weight sets x {a.seeds} "
          f"full L11 games, real NES capsules)", flush=True)
    fails = 0
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for label, n, bad in ex.map(_job, jobs):
            if bad:
                fails += 1
                print(f"  FAIL {label:<16} {len(bad)}/{n} games diverged: {bad[:3]}", flush=True)
            else:
                print(f"  ok   {label:<16} {n}/{n} games byte-identical", flush=True)
    print(f"\n{'ALL WEIGHT SETS AGREE' if not fails else str(fails)+' WEIGHT SETS DIVERGED'}"
          f"  ({len(jobs)} sets)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
