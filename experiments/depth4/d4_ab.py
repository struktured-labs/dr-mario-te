#!/usr/bin/env python3
"""PAIRED depth-3 vs depth-4 A/B at real n -- the re-test of the n=10 NO-GO.

BOTH ARMS RUN THE SAME KERNEL SNAPSHOT AND THE SAME DELTA LEAF.  d3 is
`fast_rtl_x._choose_d3_ship_eh_delta`; d4 is `d4_kernel._choose_d4_ship_eh_delta`,
which is that function with ONE structural change (ply-3 beam + ply-4 subtree) and
which collapses back onto it exactly under `--degenerate` (gate: d4_kernel.validate).
The delta-vs-full substitution is itself gated first (validate_delta_vs_full), so the
only difference between the arms is DEPTH.

PAIRING: a seed fixes the starting board AND the capsule sequence, and the env draws
exactly one capsule per placement, so both arms see the identical capsule prefix.

STREAMS: `uniform` = the sim's iid capsule draw; `nes` = the real ROM LFSR sequence
(`pillrng/nes_pills.NesPillSource`).  The NES number is the one that counts -- uniform
capsules have twice flattered a capsule-dependent strategy into a later retraction.

LATENCY is recorded as CPU time per decision (`time.process_time`), not wall clock:
this box runs an FPGA compile and several other agents, so wall clock would measure
the neighbours.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
# `snap/` and `..` (experiments/, which holds the landed nes_pills.py) come FIRST so a
# git-archive export of this directory runs against the PINNED kernel and the landed
# capsule generator, not against whatever is currently in a gitignored tmp/.  The tmp
# paths remain as fallbacks for the faithful sim, which is not vendored here.
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
    _G.update(
        level=level, maxp=maxp, stream=stream, arm=arm,
        dec={
            "d3": F.FastShipD3DeciderEHDelta(w, fl, topk2=topk2),
            "d4": K.FastShipD4DeciderEHDelta(w, fl, topk2=topk2, topk3=topk3,
                                             pills4=pills4),
            "d4deg": K.FastShipD4DeciderEHDelta(w, fl, topk2=topk2, topk3=0,
                                                pills4=pills4, ply4_mode=0),
        },
    )


def play(args):
    seed, depth = args
    from drmario.faithful_env import FaithfulDrMarioEnv
    dec = _G["dec"][depth]
    env = FaithfulDrMarioEnv(level=_G["level"], seed=seed, max_pills=_G["maxp"])
    env.reset()
    if _G["stream"] == "nes":
        from nes_pills import NesPillSource
        NesPillSource(seed=seed).attach(env)
        env.cur = env._rand_pill()
        env.nxt = env._rand_pill()
    start = env._start_viruses
    seg = {"open": [0, 0], "mid": [0, 0], "end": [0, 0]}
    cpu = 0.0
    wall = 0.0
    ndec = 0
    result = "stall"
    while True:
        t0 = time.process_time()
        w0 = time.perf_counter()
        a = dec.choose(env.board, env.cur, env.nxt)
        cpu += time.process_time() - t0
        wall += time.perf_counter() - w0
        ndec += 1
        if a is None:
            result = "topout"
            break
        vc = env.board.virus_count()
        k = "open" if vc > 32 else ("mid" if vc > 8 else "end")
        _o, _r, term, trunc, info = env.step(int(a))
        seg[k][0] += 1
        seg[k][1] += vc - env.board.virus_count()
        if term:
            result = "clear" if info["won"] else "topout"
            break
        if trunc:
            result = "stall"
            break
    return {"seed": seed, "depth": depth, "stream": _G["stream"], "result": result,
            "won": int(result == "clear"), "pills": env.pills_placed, "start": start,
            "left": env.board.virus_count(), "seg": seg,
            "cpu_ms_per_dec": 1e3 * cpu / max(ndec, 1),
            "wall_ms_per_dec": 1e3 * wall / max(ndec, 1), "ndec": ndec}


def run_arm(depth, seeds, a, stream, out_fh):
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(a.arm, a.level, a.max_pills, a.topk2,
                                       a.topk3, a.pills4, stream)) as ex:
        futs = [ex.submit(play, (s, depth)) for s in seeds]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            rows.append(r)
            out_fh.write(json.dumps(r) + "\n")
            out_fh.flush()
            if i % 10 == 0:
                print(f"    [{stream}/{depth}] {i}/{len(seeds)}  {time.time()-t0:.0f}s",
                      flush=True)
    print(f"  {stream}/{depth}: {len(rows)} games in {time.time()-t0:.0f}s", flush=True)
    return sorted(rows, key=lambda r: r["seed"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="winner")
    ap.add_argument("--seeds", type=int, default=120)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--topk2", type=int, default=8)
    ap.add_argument("--topk3", type=int, default=6)
    ap.add_argument("--pills4", default="4")
    ap.add_argument("--streams", default="nes,uniform")
    ap.add_argument("--depths", default="d3,d4")
    ap.add_argument("--out", default="d4_ab")
    a = ap.parse_args()

    seeds = list(range(a.seed0, a.seed0 + a.seeds))
    depths = a.depths.split(",")
    tag = f"{a.out}_k3-{a.topk3}_p4-{a.pills4}"
    path = os.path.join(HERE, tag + "_perseed.jsonl")
    print(f"=== D3 vs D4  arm={a.arm} L{a.level} n={len(seeds)} topk2={a.topk2} "
          f"topk3={a.topk3} pills4={a.pills4} maxp={a.max_pills} ===", flush=True)
    res = {}
    with open(path, "w") as fh:
        for stream in a.streams.split(","):
            for depth in depths:
                res[(stream, depth)] = run_arm(depth, seeds, a, stream, fh)
    meta = {"args": vars(a), "seeds": seeds}
    json.dump(meta, open(os.path.join(HERE, tag + "_meta.json"), "w"), indent=2)
    print(f"wrote {path}", flush=True)


if __name__ == "__main__":
    main()
