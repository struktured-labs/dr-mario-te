#!/usr/bin/env python3
"""DISAGREEMENT RATE + the oracle mining corpus.

The A/B plays each arm its own game, so after the first divergence the two arms are
looking at different boards and "how often do they disagree" is not defined on it.
This probe fixes the board distribution: it replays the D3 arm's own trajectory --
the boards the SHIPPED brain actually reaches -- and at every one of them asks BOTH
deciders for a placement.

Two numbers come out:
  * DISAGREEMENT RATE: the fraction of real decisions where one more ply changes the
    answer.  This bounds the oracle idea before anyone invests in it -- at 2% even a
    real quality edge is a thin signal to mine; at 15% there is material.
  * THE CORPUS: every disagreeing position is written out whole (board, capsules,
    both actions, virus count, regime), so a later pass can roll each one forward and
    ask which choice was actually better.  That downstream adjudication is NOT done
    here; this produces the positions, not the verdict.

Conditioning on the d3 trajectory is deliberate: the question is what the shipped
brain gets wrong on boards the shipped brain reaches.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
# See the note in d4_ab.py: pinned kernel and landed nes_pills.py first, tmp/ as fallback.
for _p in (HERE, os.path.join(HERE, "snap"), os.path.join(HERE, ".."),
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_G = {}


def _init(arm, level, maxp, topk2, topk3, pills4, stream):
    import fast_rtl_x as F
    import d4_kernel as K
    w, fl = F.variant(arm)
    F.warmup_delta(topk2=topk2)
    K.warmup_d4(topk2=topk2, topk3=topk3, pills4=pills4)
    _G.update(level=level, maxp=maxp, stream=stream,
              d3=F.FastShipD3DeciderEHDelta(w, fl, topk2=topk2),
              d4=K.FastShipD4DeciderEHDelta(w, fl, topk2=topk2, topk3=topk3,
                                            pills4=pills4))


def walk(seed):
    """Play the seed with d3; at every board also ask d4.  d3's answer is the one
    executed, so the trajectory is exactly the shipped brain's.

    Each corpus row carries `seed` + `k` (0-based placement index) + `src_i` (the live
    NesPillSource cursor).  Those make phase-3 adjudication DETERMINISTIC: the capsule
    buffer is generated up front from the seed, so from any recorded position the true
    future is known exactly and both candidate actions can be played forward on the SAME
    true stream with zero rollout variance -- no Monte Carlo needed.  `src_i` follows
    openbook's cursor convention (`bookab.play` reads the clairvoyant k+2 capsule as
    `ids[src.i % 128]`), so an adjudicator can reuse that plumbing instead of growing a
    second copy of the same off-by-one risk."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from fast_sim_x import board_flat
    d3, d4 = _G["d3"], _G["d4"]
    env = FaithfulDrMarioEnv(level=_G["level"], seed=seed, max_pills=_G["maxp"])
    env.reset()
    src = None
    if _G["stream"] == "nes":
        from nes_pills import NesPillSource
        src = NesPillSource(seed=seed)
        src.attach(env)
        env.cur = env._rand_pill()
        env.nxt = env._rand_pill()
    rows = []
    n = 0
    ndis = 0
    misalign = 0
    by_regime = defaultdict(lambda: [0, 0])          # regime -> [decisions, disagreements]
    kind = defaultdict(int)                          # col-only / orient-only / both
    while True:
        a3 = d3.choose(env.board, env.cur, env.nxt)
        if a3 is None:
            break
        # ALIGNMENT ASSERT (openbook's): a clairvoyant read of the stream at (k, k+1)
        # must equal the capsules actually served as cur/next.  COUNTED, not raised -- a
        # worker crash would silently shrink the sample instead of reporting the bug.
        src_i = -1
        if src is not None:
            from nes_pills import PILL_COLORS
            src_i = src.i
            want_cur = PILL_COLORS[src.ids[(src.i - 2) % 128]]
            want_nxt = PILL_COLORS[src.ids[(src.i - 1) % 128]]
            if want_cur != (env.cur.a, env.cur.b) or want_nxt != (env.nxt.a, env.nxt.b):
                misalign += 1
        a4 = d4.choose(env.board, env.cur, env.nxt)
        vc = env.board.virus_count()
        reg = "open" if vc > 32 else ("mid" if vc > 8 else "end")
        n += 1
        by_regime[reg][0] += 1
        if a4 is not None and a4 != a3:
            ndis += 1
            by_regime[reg][1] += 1
            same_col = (a3 % 8) == (a4 % 8)
            same_var = (a3 // 8) == (a4 // 8)
            kind["orient_only" if same_col else ("col_only" if same_var else "both")] += 1
            col, vir = board_flat(env.board)
            rows.append({"seed": seed, "k": int(env.pills_placed), "src_i": int(src_i),
                         "stream": _G["stream"], "level": _G["level"],
                         "ply": n, "vc": int(vc), "regime": reg,
                         "a3": int(a3), "a4": int(a4),
                         "cur": [env.cur.a, env.cur.b], "nxt": [env.nxt.a, env.nxt.b],
                         "col": col.tolist(), "vir": vir.tolist()})
        _o, _r, term, trunc, _i = env.step(int(a3))
        if term or trunc:
            break
    return {"seed": seed, "n": n, "ndis": ndis, "rows": rows, "misalign": misalign,
            "by_regime": {k: v for k, v in by_regime.items()}, "kind": dict(kind)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="winner")
    ap.add_argument("--seeds", type=int, default=60)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--topk2", type=int, default=8)
    ap.add_argument("--topk3", type=int, default=6)
    ap.add_argument("--pills4", default="4")
    ap.add_argument("--stream", default="nes")
    ap.add_argument("--out", default="disagree")
    a = ap.parse_args()

    seeds = list(range(a.seed0, a.seed0 + a.seeds))
    tag = f"{a.out}_{a.stream}_k3-{a.topk3}"
    corpus = open(os.path.join(HERE, tag + "_corpus.jsonl"), "w")
    tot_n = tot_d = tot_mis = 0
    per_seed = []
    reg = defaultdict(lambda: [0, 0])
    kind = defaultdict(int)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(a.arm, a.level, a.max_pills, a.topk2,
                                       a.topk3, a.pills4, a.stream)) as ex:
        futs = [ex.submit(walk, s) for s in seeds]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            tot_n += r["n"]
            tot_d += r["ndis"]
            tot_mis += r["misalign"]
            per_seed.append({"seed": r["seed"], "n": r["n"], "ndis": r["ndis"]})
            for k, v in r["by_regime"].items():
                reg[k][0] += v[0]
                reg[k][1] += v[1]
            for k, v in r["kind"].items():
                kind[k] += v
            for row in r["rows"]:
                corpus.write(json.dumps(row) + "\n")
            corpus.flush()
            if i % 10 == 0:
                print(f"  {i}/{len(seeds)}  {time.time()-t0:.0f}s", flush=True)
    corpus.close()

    # per-seed rate, then a seed-level bootstrap -- decisions inside one game are
    # correlated, so the pooled decision count would understate the interval.
    import numpy as np
    rates = np.array([s["ndis"] / s["n"] for s in per_seed if s["n"]], dtype=np.float64)
    rng = np.random.default_rng(7)
    bs = rng.integers(0, rates.size, size=(20000, rates.size))
    m = rates[bs].mean(axis=1)
    print(f"\n=== DISAGREEMENT  stream={a.stream} k3={a.topk3} p4={a.pills4} "
          f"n={len(seeds)} seeds ===")
    print(f"  decisions {tot_n}   disagreements {tot_d}   pooled {tot_d/tot_n:.1%}")
    print(f"  stream alignment (clairvoyant k,k+1 == served cur,next): "
          f"{'OK' if tot_mis == 0 else f'*** {tot_mis} MISALIGNED ***'}")
    print(f"  per-seed mean rate {rates.mean():.1%}  CI95 "
          f"[{np.percentile(m,2.5):.1%},{np.percentile(m,97.5):.1%}]")
    for k in ("open", "mid", "end"):
        if k in reg and reg[k][0]:
            print(f"  {k:>5}: {reg[k][1]}/{reg[k][0]} = {reg[k][1]/reg[k][0]:.1%}")
    tk = sum(kind.values()) or 1
    print("  kind: " + "  ".join(f"{k}={v} ({v/tk:.0%})" for k, v in sorted(kind.items())))
    json.dump({"pooled": tot_d / tot_n if tot_n else 0.0,
               "per_seed_mean": float(rates.mean()),
               "ci95": [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))],
               "decisions": tot_n, "disagreements": tot_d, "misaligned": tot_mis,
               "by_regime": {k: v for k, v in reg.items()}, "kind": dict(kind),
               "per_seed": per_seed, "args": vars(a)},
              open(os.path.join(HERE, tag + "_summary.json"), "w"), indent=2)
    print(f"wrote {tag}_summary.json and {tag}_corpus.jsonl")


if __name__ == "__main__":
    main()
