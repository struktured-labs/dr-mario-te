#!/usr/bin/env python3
"""Sample REAL champion mid-game positions, stratified by spawn-column height.

Why stratify. The admissible bound h = ceil((spawn_top-1)/2) both (a) decides
how dangerous a position is and (b) decides what the search costs: if h exceeds
the depth limit, "no kill within K" is proved for free and the position tells us
nothing new. All the information -- and all the cost -- lives in positions where
the stack is already up. So we bin by spawn_top and take a quota from each bin,
rather than sampling uniformly over plies (which would drown the corpus in
early-game boards that are trivially safe).

These are positions the champion ACTUALLY REACHES in its own play, not
synthetic stress boards -- a hole here is a hole on the real distribution.
"""
from __future__ import annotations
import sys, os, json, argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _init():
    import champion as CH
    CH.init_champion()


def walk(spec):
    """Play one game; return every (board, cur) with its spawn_top."""
    import champion as CH
    import poker as PK
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    level, seed, max_pills = spec
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
    env.reset(); NesPillSource(seed=seed).attach(env)
    stream = [(int(p.a), int(p.b)) for p in (env._rand_pill() for _ in range(max_pills + 4))]
    b = CH.new_board(level, seed)
    out = []
    for i in range(max_pills):
        if b.virus_count() == 0 or b.spawn_blocked():
            break
        col, vir = CH.board_to_flat(b)
        ca, cb = stream[i]
        a = CH.champion_move(col, vir, ca, cb, *stream[i + 1])
        if a is None:
            break
        out.append({"level": level, "seed": seed, "ply": i,
                    "spawn_top": PK.spawn_top(b),
                    "viruses": int(b.virus_count()),
                    "col": col.tolist(), "vir": vir.tolist(),
                    "link": b.link.reshape(-1).astype(int).tolist(),
                    "cur": [ca, cb]})
        ok, _c, _v, _ch = CH.apply_action(b, a, ca, cb)
        if not ok:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", type=int, nargs="+", default=[11, 15, 17, 19, 20])
    ap.add_argument("--seeds", type=int, default=25)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--per-bin", type=int, default=14,
                    help="positions to keep per spawn_top value")
    ap.add_argument("--max-spawn-top", type=int, default=12,
                    help="ignore positions with a stack lower than this "
                         "(they are provably safe within our depth limit)")
    ap.add_argument("--out", type=str, default="results/positions.json")
    a = ap.parse_args()

    jobs = [(lv, s, 300) for lv in a.levels for s in range(a.seeds)]
    print(f"=== SAMPLING {len(jobs)} games ===", flush=True)
    bins = defaultdict(list)
    done = 0
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init) as ex:
        futs = [ex.submit(walk, j) for j in jobs]
        for f in as_completed(futs):
            for p in f.result():
                st = p["spawn_top"]
                if st <= a.max_spawn_top and len(bins[st]) < a.per_bin * 4:
                    bins[st].append(p)
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(jobs)} games; bins="
                      f"{ {k: len(v) for k, v in sorted(bins.items())} }", flush=True)

    # take an evenly-spread quota per bin (spread across levels/seeds)
    keep = []
    for st in sorted(bins):
        pool = bins[st]
        step = max(1, len(pool) // a.per_bin)
        keep.extend(pool[::step][:a.per_bin])
    print(f"\n=== KEPT {len(keep)} positions ===")
    hist = defaultdict(int)
    for p in keep:
        hist[p["spawn_top"]] += 1
    for st in sorted(hist):
        print(f"  spawn_top={st:2d}: {hist[st]:3d} positions  (h={0 if st<=1 else (st-1+1)//2})")
    with open(os.path.join(HERE, a.out), "w") as fh:
        json.dump(keep, fh)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
