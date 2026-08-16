#!/usr/bin/env python3
"""Price candidate first placements from a single transcribed board.

Every distinct legal placement of the board's current capsule becomes an ARM.
All arms are rolled forward under the same champion decider over the SAME set of
freshly sampled capsule streams (capsule-refork), so the comparison is paired
per stream and only the first move differs.

The headline is the paired delta of each arm against a nominated REFERENCE arm
(normally the placement actually played), with a bootstrap CI over streams.

PRESSURE. A solo rollout from a mid-game board almost never tops out -- the
champion's clean-board failure rate is under 0.2% (`dr-mario-clean-failure-rate`)
-- so a solo arm mostly measures nothing and returns a confident null. `--drip`
turns on the pressure_rig garbage injector (identical function, identical
per-placement schedule) so the arms are separated under the regime that actually
kills. Run both and report both; they answer different questions.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import forced_board as FBM   # noqa: E402

_W = {}


def _init(wt, ws, level, spec, cur, nxt, horizon, drip_period, drip_k):
    _W["dec"] = FBM.Decider(wt=wt, ws=ws, level=level)
    _W.update(level=level, spec=spec, cur=cur, nxt=nxt, horizon=horizon,
              drip_period=drip_period, drip_k=drip_k)


def _make_hook(stream_seed):
    """Garbage injector, or None. Uses pressure_rig's own `_inject_garbage`, so
    the halves land and settle by exactly the mechanism the A/B rigs use."""
    if not _W["drip_period"]:
        return None
    import pressure_rig as PR

    def hook(env, i):
        if (i + 1) % _W["drip_period"]:
            return None
        PR._inject_garbage(env.board, stream_seed, i + 1, k=_W["drip_k"])
        if env.board.virus_count() == 0:
            return "clear"
        if env.board.spawn_blocked():
            return "topout"
        return None
    return hook


def _one(job):
    action, stream_seed = job
    planes = FBM.planes_from_spec(_W["spec"])
    env, src, meta = FBM.make_env(planes, stream_seed=stream_seed,
                                  cur=_W["cur"], nxt=_W["nxt"], level=_W["level"])
    if meta["settle_moved"]:
        raise FBM.BoardSpecError("board is not settled on import -- refusing to price it")
    r = FBM.rollout(env, _W["dec"], _W["horizon"], forced_action=action,
                    record=False, after_lock=_make_hook(stream_seed))
    r.pop("traj", None)
    r["action"] = action
    r["stream"] = stream_seed
    return r


def boot_ci(xs, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(st.mean([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", required=True, help="JSON with col/vir[/lnk]")
    ap.add_argument("--cur", type=int, nargs=2, required=True, help="current capsule colours a b")
    ap.add_argument("--nxt", type=int, nargs=2, default=None)
    ap.add_argument("--ref", type=int, default=None,
                    help="reference action int (the placement actually played)")
    ap.add_argument("--streams", type=int, default=48)
    ap.add_argument("--stream-base", type=int, default=900000)
    ap.add_argument("--horizon", type=int, default=30)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--wt", type=int, default=0)
    ap.add_argument("--ws", type=int, default=20)
    ap.add_argument("--drip", type=int, default=0, help="garbage every N placements (0=solo)")
    ap.add_argument("--drip-k", type=int, default=2)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    spec = json.load(open(a.board))
    planes = FBM.planes_from_spec(spec)
    env0, _, meta0 = FBM.make_env(planes, stream_seed=1, cur=tuple(a.cur),
                                  nxt=tuple(a.nxt) if a.nxt else None, level=a.level)
    if meta0["settle_moved"]:
        print("REFUSING: the board moved under gravity on import -- the transcription "
              "or its link plane is wrong. Nothing downstream would be about this board.")
        return 2
    print(env0.board.ascii())
    print(f"\nviruses={meta0['viruses']}  cur={meta0['cur']}  nxt={meta0['nxt']}  "
          f"H={a.horizon}  streams={a.streams}  drip={a.drip or 'off'}")

    # distinct arms: with a==b the two horizontal variants place identical cells,
    # as do the two verticals, so dedupe on the CELLS actually occupied.
    seen, arms = set(), []
    for p in FBM.legal_placements(env0):
        key = tuple(sorted(tuple(map(int, c)) for c in p["cells"]))
        if key in seen:
            continue
        seen.add(key)
        arms.append(p)
    print(f"distinct legal placements: {len(arms)}")

    streams = [a.stream_base + i for i in range(a.streams)]
    jobs = [(p["action"], s) for p in arms for s in streams]
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(a.wt, a.ws, a.level, spec, tuple(a.cur),
                                       tuple(a.nxt) if a.nxt else None, a.horizon,
                                       a.drip, a.drip_k)) as ex:
        for r in ex.map(_one, jobs, chunksize=4):
            rows.append(r)

    by = {}
    for r in rows:
        by.setdefault(r["action"], {})[r["stream"]] = r
    ref = a.ref if a.ref is not None else arms[0]["action"]

    def summ(d):
        ss = sorted(d)
        return {"topout_rate": sum(d[s]["topout"] for s in ss) / len(ss),
                "dies_ahead": sum(d[s]["dies_ahead"] for s in ss) / len(ss),
                "pills": st.mean([d[s]["pills"] for s in ss]),
                "cleared": st.mean([d[s]["viruses_cleared"] for s in ss]),
                "spawn_h": st.mean([d[s]["spawn_height"] for s in ss]),
                "max_h": st.mean([d[s]["max_height"] for s in ss])}

    print(f"\n{'arm':>22s} {'topout':>8s} {'diesAhd':>8s} {'pills':>7s} {'vClr':>6s} "
          f"{'spawnH':>7s}  {'d(topout) vs ref [95% CI]':>30s}")
    out = []
    refd = by[ref]
    for p in sorted(arms, key=lambda q: q["action"]):
        d = by[p["action"]]
        s = summ(d)
        common = sorted(set(d) & set(refd))
        diff = [d[k]["topout"] - refd[k]["topout"] for k in common]
        lo, hi = boot_ci(diff)
        tag = f"{p['orient']}@col{p['col']}r{p['top_row']}" + (" *REF" if p["action"] == ref else "")
        print(f"{tag:>22s} {s['topout_rate']:8.1%} {s['dies_ahead']:8.1%} {s['pills']:7.2f} "
              f"{s['cleared']:6.2f} {s['spawn_h']:7.2f}  "
              f"{st.mean(diff):+8.3f} [{lo:+.3f},{hi:+.3f}]"
              f"{'  REAL' if (hi < 0 or lo > 0) else '  wash'}")
        out.append({"action": p["action"], "tag": tag, **s,
                    "d_topout": st.mean(diff), "ci": [lo, hi]})

    if a.out:
        with open(a.out, "w") as fh:
            json.dump({"ref": ref, "arms": out, "rows": rows,
                       "cfg": vars(a)}, fh, indent=1, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
