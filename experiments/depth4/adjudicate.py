#!/usr/bin/env python3
"""PHASE 3 — DETERMINISTIC ADJUDICATION of the d3/d4 disagreement corpus.

THE QUESTION.  `disagree.py` established that d4 picks a different placement than d3 on
13.3% of real decisions.  A rate is not a value: opening-book measured 18.4% different
moves carrying ZERO value.  This asks, for every one of those disagreements, whether d4's
choice was actually BETTER.

METHOD — exact, not sampled.  The NES capsule buffer is generated up front from the seed
and loops at 128, so from any position the true future is KNOWN.  From each disagreement
we play BOTH actions forward on the IDENTICAL true stream and compare.  No Monte Carlo, no
rollout variance: the only difference between the two branches is the one move.

★ THE ROLL-FORWARD PLAYER IS d3, DELIBERATELY (team-lead's call, stated so nobody reads it
as an oversight).  The oracle exists to mine leaf terms for the SHIPPED brain, so "was d4's
move better FOR A D3 PLAYER" is the actionable question.  A d4-consistent roll-forward
answers a question we cannot act on -- d4 is unshippable at 22.9x -- and costs 20x more.
CONSEQUENCE TO REMEMBER WHEN READING THE NUMBERS: this measures the value of ONE d4 move
followed by d3 play, so it should come out SMALLER than d4's whole-arm advantage, where d4
keeps steering. It is a lower bound on d4's edge, not an estimate of it.

★ POSITIONS ARE REBUILT BY REPLAY, NOT RESTORED FROM THE CORPUS.  The corpus stores color
and is_virus but NOT `link` (the search reads only the first two -- `board_flat` -- so the
probe never needed it).  Gravity DOES read link: a linked half falls with its partner until
the partner clears.  Restoring a board without link would silently produce a position whose
FUTURE differs from the real one, which is precisely what a roll-forward measures.  So each
seed is replayed from move 0 with the same deterministic d3, reproducing the exact state
including link, and the corpus fields become VERIFICATION GATES rather than the source of
truth -- four independent checks per row (board colors, virus mask, served capsules, stream
cursor, and d3's own action). Replaying once per seed and forking at each of its
disagreements amortises the cost.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
for _p in (HERE, os.path.join(HERE, "snap"), os.path.join(HERE, ".."),
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_G = {}


def _init(arm, level, maxp, topk2):
    import fast_rtl_x as F
    F.warmup_delta(topk2=topk2)
    w, fl = F.variant(arm)
    _G.update(level=level, maxp=maxp,
              d3=F.FastShipD3DeciderEHDelta(w, fl, topk2=topk2))


def _fork(env, seed, src_i):
    """Clone the live env (board WITH link, capsules, counters) and re-anchor the stream."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    e = FaithfulDrMarioEnv(level=_G["level"], seed=0, max_pills=_G["maxp"])
    e.reset()
    e.board = env.board.clone()
    e.cur = env.cur
    e.nxt = env.nxt
    e.pills_placed = env.pills_placed
    e._start_viruses = env._start_viruses
    s = NesPillSource(seed=seed)
    s.i = src_i
    s.attach(e)
    return e


def _roll(env, action):
    """Play `action`, then let d3 finish the game.  Returns (result, pills_from_branch)."""
    d3 = _G["d3"]
    k0 = env.pills_placed
    _o, _r, term, trunc, info = env.step(int(action))
    if term:
        return ("clear" if info["won"] else "topout"), env.pills_placed - k0
    if trunc:
        return "stall", env.pills_placed - k0
    while True:
        a = d3.choose(env.board, env.cur, env.nxt)
        if a is None:
            return "topout", env.pills_placed - k0
        _o, _r, term, trunc, info = env.step(int(a))
        if term:
            return ("clear" if info["won"] else "topout"), env.pills_placed - k0
        if trunc:
            return "stall", env.pills_placed - k0


def adjudicate_seed(args):
    seed, rows = args
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fast_sim_x import board_flat
    d3 = _G["d3"]
    pending = {int(r["k"]): r for r in rows}
    env = FaithfulDrMarioEnv(level=_G["level"], seed=seed, max_pills=_G["maxp"])
    env.reset()
    src = NesPillSource(seed=seed)
    src.attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    out = []
    bad = defaultdict(int)
    while True:
        a3 = d3.choose(env.board, env.cur, env.nxt)
        if a3 is None:
            break
        k = int(env.pills_placed)
        r = pending.pop(k, None)
        if r is not None:
            # ---- five verification gates: the replay must BE the recorded position ----
            col, vir = board_flat(env.board)
            if col.tolist() != r["col"]:
                bad["color"] += 1
            if vir.tolist() != r["vir"]:
                bad["virus"] += 1
            if [env.cur.a, env.cur.b] != r["cur"] or [env.nxt.a, env.nxt.b] != r["nxt"]:
                bad["capsules"] += 1
            if int(src.i) != int(r["src_i"]):
                bad["cursor"] += 1
            if int(a3) != int(r["a3"]):
                bad["action"] += 1
            else:
                res3, p3 = _roll(_fork(env, seed, src.i), r["a3"])
                res4, p4 = _roll(_fork(env, seed, src.i), r["a4"])
                out.append({"seed": seed, "k": k, "vc": r["vc"], "regime": r["regime"],
                            "a3": r["a3"], "a4": r["a4"],
                            "kind": ("orient_only" if (r["a3"] % 8) == (r["a4"] % 8)
                                     else ("col_only" if (r["a3"] // 8) == (r["a4"] // 8)
                                           else "both")),
                            "res3": res3, "res4": res4, "pills3": p3, "pills4": p4})
        _o, _r2, term, trunc, _i = env.step(int(a3))
        if term or trunc:
            break
    bad["unvisited"] += len(pending)
    return out, dict(bad)


def boot_ci(vals, groups, stat=np.mean, n=20000, seed=99):
    """Bootstrap resampling SEEDS (not rows) -- rows inside a game are correlated."""
    if not vals:
        return (float("nan"), float("nan"))
    by = defaultdict(list)
    for v, g in zip(vals, groups):
        by[g].append(v)
    keys = list(by)
    rng = np.random.default_rng(seed)
    outs = np.empty(n)
    for i in range(n):
        pick = rng.integers(0, len(keys), len(keys))
        acc = []
        for j in pick:
            acc.extend(by[keys[j]])
        outs[i] = stat(acc)
    return (float(np.percentile(outs, 2.5)), float(np.percentile(outs, 97.5)))


def report(rows, label, maxp):
    n = len(rows)
    both = [r for r in rows if r["res3"] == "clear" and r["res4"] == "clear"]
    only3 = [r for r in rows if r["res3"] == "clear" and r["res4"] != "clear"]
    only4 = [r for r in rows if r["res4"] == "clear" and r["res3"] != "clear"]
    neither = [r for r in rows if r["res3"] != "clear" and r["res4"] != "clear"]
    print(f"\n--- {label}  (n={n} disagreements) ---")
    if n == 0:
        return {}
    print(f"    outcome: both clear {len(both)}  d4-only {len(only4)}  "
          f"d3-only {len(only3)}  neither {len(neither)}")
    res = {"n": n, "both": len(both), "only4": len(only4), "only3": len(only3),
           "neither": len(neither)}
    if both:
        d = [r["pills4"] - r["pills3"] for r in both]
        g = [r["seed"] for r in both]
        ci = boot_ci(d, g)
        w = sum(1 for v in d if v < 0); l = sum(1 for v in d if v > 0)
        print(f"    paired pills-to-clear (both cleared, n={len(d)}): mean "
              f"{st.mean(d):+.3f} CI95 [{ci[0]:+.3f},{ci[1]:+.3f}]   "
              f"d4 better/worse/tie {w}/{l}/{len(d)-w-l}")
        res.update(mean=st.mean(d), ci=ci, better=w, worse=l, tie=len(d) - w - l)
    dc = [(r["pills4"] if r["res4"] == "clear" else maxp)
          - (r["pills3"] if r["res3"] == "clear" else maxp) for r in rows]
    gc = [r["seed"] for r in rows]
    cic = boot_ci(dc, gc)
    print(f"    censored delta (non-clear = {maxp}): mean {st.mean(dc):+.2f} "
          f"CI95 [{cic[0]:+.2f},{cic[1]:+.2f}]")
    res.update(cens_mean=st.mean(dc), cens_ci=cic)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="disagree_nes_k3-6_corpus.jsonl")
    ap.add_argument("--arm", default="winner")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--topk2", type=int, default=8)
    ap.add_argument("--limit-seeds", type=int, default=0)
    ap.add_argument("--out", default="adjudicate")
    a = ap.parse_args()

    by_seed = defaultdict(list)
    for line in open(os.path.join(HERE, a.corpus)):
        r = json.loads(line)
        by_seed[int(r["seed"])].append(r)
    seeds = sorted(by_seed)
    if a.limit_seeds:
        seeds = seeds[:a.limit_seeds]
    total = sum(len(by_seed[s]) for s in seeds)
    print(f"adjudicating {total} disagreements across {len(seeds)} seeds "
          f"(roll-forward player = d3, deliberately)", flush=True)

    rows = []
    bad = defaultdict(int)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(a.arm, a.level, a.max_pills, a.topk2)) as ex:
        futs = [ex.submit(adjudicate_seed, (s, by_seed[s])) for s in seeds]
        for i, f in enumerate(as_completed(futs), 1):
            got, b = f.result()
            rows.extend(got)
            for k, v in b.items():
                bad[k] += v
            if i % 10 == 0:
                print(f"  {i}/{len(seeds)} seeds  {len(rows)} rows  "
                      f"{time.time()-t0:.0f}s", flush=True)

    with open(os.path.join(HERE, a.out + "_rows.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    print(f"\n=== ADJUDICATION  n={len(rows)}/{total} corpus rows  "
          f"({time.time()-t0:.0f}s) ===")
    print(f"  REPLAY GATES (all must be 0): {dict(bad) if bad else 'CLEAN'}")
    summary = {"all": report(rows, "ALL", a.max_pills), "gates": dict(bad),
               "n_corpus": total}
    print("\n  ---- the mining cut: WHERE do d4's better opinions concentrate? ----")
    for key in ("regime", "kind"):
        for val in (("open", "mid", "end") if key == "regime"
                    else ("both", "col_only", "orient_only")):
            sub = [r for r in rows if r[key] == val]
            summary[f"{key}:{val}"] = report(sub, f"{key} = {val}", a.max_pills)
    json.dump(summary, open(os.path.join(HERE, a.out + "_summary.json"), "w"),
              indent=2, default=float)
    print(f"\nwrote {a.out}_rows.jsonl and {a.out}_summary.json")


if __name__ == "__main__":
    main()
