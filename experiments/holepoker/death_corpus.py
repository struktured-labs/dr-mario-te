#!/usr/bin/env python3
"""Generate a corpus of REAL champion deaths (topout / stall) with FULL
trajectories, so the counterfactual analysis can search backward from each one.

Why we generate our own rather than wait on the tier-1 seed census: backward
analysis needs the whole move history and the exact pill stream, not just the
fatal board. We store only (level, seed, result) plus the action list -- the
board at any ply is then replayed deterministically.

Solo topouts are RARE for this champion (dr-mario-stomper-loss-autopsy: 400 VS
losses, ZERO topouts), so we hunt at high levels where the virus load actually
threatens it. Stalls (300-pill cap with viruses left) are recorded too: a stall
is a slower death of the same disease -- the board is junk-locked.

Usage: death_corpus.py --levels 15 17 19 20 --seeds 400 --workers 6 --out results/deaths
"""
from __future__ import annotations
import sys, os, json, argparse, time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _init():
    import champion as CH
    CH.init_champion()


def pill_stream(level, seed, n):
    """The real NES capsule stream for (level, seed), pulled independently of
    the env so we can replay it."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=n + 8)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    return [(int(p.a), int(p.b)) for p in (env._rand_pill() for _ in range(n + 8))]


def play(args):
    import champion as CH
    level, seed, max_pills = args
    stream = pill_stream(level, seed, max_pills)
    b = CH.new_board(level, seed)
    v0 = b.virus_count()
    acts, res = [], "stall"
    heights = []
    for i in range(max_pills):
        if b.virus_count() == 0:
            res = "clear"; break
        col, vir = CH.board_to_flat(b)
        ca, cb = stream[i]
        na, nb = stream[i + 1]
        a = CH.champion_move(col, vir, ca, cb, na, nb)
        if a is None:
            res = "nomove"; break
        acts.append(int(a))
        ok, _c, _vc, _ch = CH.apply_action(b, a, ca, cb)
        if not ok:
            res = "illegal"; break
        heights.append(int(min(b.top_occupied_row(3), b.top_occupied_row(4))))
        if b.virus_count() == 0:
            res = "clear"; break
        if b.spawn_blocked():
            res = "topout"; break
    return {"level": level, "seed": seed, "result": res, "pills": len(acts),
            "v0": v0, "v_left": int(b.virus_count()), "acts": acts,
            "spawn_top_hist": heights}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", type=int, nargs="+", default=[15, 17, 19, 20])
    ap.add_argument("--seeds", type=int, default=400)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--out", type=str, default="results/deaths")
    a = ap.parse_args()

    jobs = [(lv, s, a.max_pills) for lv in a.levels
            for s in range(a.seed0, a.seed0 + a.seeds)]
    print(f"=== DEATH CORPUS: {len(jobs)} games, levels={a.levels}, "
          f"seeds {a.seed0}..{a.seed0 + a.seeds - 1}, workers={a.workers} ===",
          flush=True)
    t0 = time.time()
    rows, done = [], 0
    outp = os.path.join(HERE, a.out)
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init) as ex:
        futs = [ex.submit(play, j) for j in jobs]
        with open(outp + ".jsonl", "w") as fh:
            for f in as_completed(futs):
                r = f.result()
                rows.append({k: r[k] for k in ("level", "seed", "result", "pills",
                                               "v0", "v_left")})
                if r["result"] in ("topout", "stall", "nomove", "illegal"):
                    fh.write(json.dumps(r) + "\n"); fh.flush()
                done += 1
                if done % 50 == 0 or done == len(jobs):
                    bad = sum(1 for x in rows if x["result"] != "clear")
                    el = time.time() - t0
                    print(f"  {done}/{len(jobs)}  bad={bad} ({bad/done:.1%})  "
                          f"{el:.0f}s  eta {el/done*(len(jobs)-done)/60:.1f}min",
                          flush=True)
    from collections import Counter
    by = {}
    for x in rows:
        by.setdefault(x["level"], Counter())[x["result"]] += 1
    print("\n=== RESULT BY LEVEL ===")
    for lv in sorted(by):
        c = by[lv]; n = sum(c.values())
        print(f"  L{lv}: n={n}  clear {c['clear']/n:.1%}  topout {c['topout']} "
              f"stall {c['stall']} nomove {c['nomove']}")
    with open(outp + "_summary.json", "w") as fh:
        json.dump({"rows": rows, "by_level": {str(k): dict(v) for k, v in by.items()}}, fh)
    print(f"\nwrote {outp}.jsonl + {outp}_summary.json")
    print("DONE")


if __name__ == "__main__":
    main()
