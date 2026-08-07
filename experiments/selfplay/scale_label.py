#!/usr/bin/env python3
"""2x SCALE-UP LABELLER -- resumable, append-only, flock'd, RSS-guarded.

TARGET: 2x Stage-1 signal, which by the pre-registered scaling (stage2_scale.py)
predicts a fitted-linear excess over hand weights of 0.94/2^2 = 0.235 pills, just
inside GATE_TOL 0.25. 2x needs 4x the rollouts: 11,200 -> 44,800, i.e. 560 positions
at Stage 1's identical protocol (10 actions x 8 rollouts).

REUSING STAGE 1's 140 POSITIONS -- and why that is legitimate here.
Common random numbers matter WITHIN a position (the actions of one position must
share pill streams so their comparison is paired). They do NOT need to be consistent
ACROSS positions -- nothing in the estimator compares two different positions'
rollouts to each other. So Stage 1's 140 champion-policy labels can be reused as-is,
with their original enumeration-derived stream bases, and only 420 NEW positions need
labelling. That is a 25% saving on a multi-hour run for zero loss of validity.

New positions use stream_base = f(idx), a function of the corpus index rather than of
enumeration order, so the scheme is stable under any future change to the sample size.
Stage 1's scheme was order-derived and would have silently re-assigned streams if the
sample grew -- worth fixing here rather than inheriting.

RESUMABILITY (the condition this file exists to satisfy). A 6-9 h run that restarts
from zero after any interruption is a materially different risk than one that resumes.
On start this reads the output file, collects the position indices already present,
and skips them. Output is opened APPEND-only and every write takes an flock, so a
concurrent or restarted writer cannot interleave a partial record.

RESOURCE DISCIPLINE. Five OOM kills are on this box's record, all from unbounded
multi-worker jobs. Workers are capped by argument (8 for this run, per allocation),
and a watchdog samples the process tree's RSS every 30 s and aborts the run if it
exceeds --max-rss-gb. Aborting is safe precisely because the run resumes.
"""
from __future__ import annotations

import os
import sys
import json
import time
import fcntl
import random
import argparse
import threading
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np

ROLLOUT_CAP = 200
TOPK_ACTS = 8
RAND_ACTS = 2
_W = {}
_ABORT = threading.Event()


def stream_base_for(idx):
    """Stable per-position stream base. A function of the corpus index, NOT of
    enumeration order, so growing the sample never re-assigns a position's streams."""
    return 20000000 + (int(idx) * 7919) % 9000000


def _init_worker(policy):
    import sp_engine as E
    import fast_rtl_x as FX
    if policy == "d3delta":
        FX.warmup_delta(topk2=8)
    _W["policy"] = policy
    _W["champ"] = E.Champion()
    _W["env"] = E.new_env(level=E.LEVEL, seed=0, cap=ROLLOUT_CAP)


def _choose(col, vir, ca, cb, na, nb):
    import fast_rtl_x as FX
    champ = _W["champ"]
    if _W["policy"] == "champion":
        return champ.choose(col, vir, ca, cb, na, nb)
    return int(FX._choose_d3_ship_eh_delta(
        col, vir, ca, cb, na, nb, 8, int(FX._W_EXCAV_SHIP),
        int(FX._W_HANG_SHIP), champ.w, champ.fl))


def _worker(job):
    import sp_engine as E
    import fast_rtl_x as FX
    from fast_sim_x import NCELL, _expand_core

    idx, col, vir, link, ca, cb, na, nb, M = job
    champ = _W["champ"]
    env = _W["env"]
    hand_act, val, ok = champ.values(col, vir, ca, cb, na, nb)
    val = val.copy()
    ok = ok.copy()
    legal = [a for a in range(32) if ok[a] == 1]
    if len(legal) < 3:
        return None
    topk = sorted(legal, key=lambda a: -val[a])[:TOPK_ACTS]
    rest = [a for a in legal if a not in set(topk)]
    base = stream_base_for(idx)
    rng = random.Random(base)
    acts = sorted(set(topk) | set(rng.sample(rest, min(RAND_ACTS, len(rest)))))

    barr = np.empty(FX.NBASE, dtype=np.int64)
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    terms, wins, leafs = {}, {}, {}
    for a in acts:
        var, cc = a // 8, a % 8
        _o, _nv, _cl = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
        FX._base_scan(c1, v1, champ.fl, barr)
        terms[str(a)] = [int(x) for x in barr[:FX.NT]]
        wins[str(a)] = int(FX._virus_count(v1) == 0)
        leafs[str(a)] = int(FX._leafv_ship(c1, v1, champ.w, champ.fl))

    rec = dict(idx=int(idx), hand_act=int(hand_act), acts=acts, n_legal=len(legal),
               hand_val={str(a): float(val[a]) for a in acts},
               terms=terms, win=wins, leaf_search=leafs, pills={}, outcome={})
    for a in acts:
        pl, oc = [], []
        for m in range(M):
            E.attach_stream(env, base + m)
            E.set_board(env.board, col, vir, link)
            E.set_pills(env, ca, cb, na, nb)
            env.pills_placed = 0
            env._start_viruses = int(env.board.virus_count())
            used = 0
            first = a
            res = "stall"
            for _ in range(ROLLOUT_CAP):
                if env.board.virus_count() == 0:
                    res = "clear"
                    break
                if first is not None:
                    act = first
                    first = None
                else:
                    c, v, _l = E.board_planes(env.board)
                    act = _choose(c, v, env.cur.a, env.cur.b, env.nxt.a, env.nxt.b)
                    if act < 0:
                        res = "topout"
                        break
                _o, _r, term, trunc, info = env.step(int(act))
                used += 1
                if term:
                    res = "clear" if info["won"] else "topout"
                    break
                if trunc:
                    res = "stall"
                    break
            pl.append(used)
            oc.append(res)
        rec["pills"][str(a)] = pl
        rec["outcome"][str(a)] = oc
    return rec


def _rss_watchdog(pid, limit_gb, period=30):
    import subprocess
    while not _ABORT.is_set():
        try:
            out = subprocess.run(
                ["bash", "-c",
                 f"{{ ps -o rss= -p {pid}; ps -o rss= --ppid {pid}; }} 2>/dev/null "
                 f"| awk '{{s+=$1}} END {{print s+0}}'"],
                capture_output=True, text=True, timeout=15)
            gb = int(out.stdout.strip() or 0) / 1048576.0
            if gb > limit_gb:
                print(f"  [RSS WATCHDOG] {gb:.1f} GB > {limit_gb} GB -- ABORTING. "
                      f"The run is resumable; restart when the box is quieter.",
                      flush=True)
                _ABORT.set()
                return
        except Exception:
            pass
        _ABORT.wait(period)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", choices=["champion", "d3delta"], required=True)
    ap.add_argument("--corpus", default="out/corpus.npz")
    ap.add_argument("--out", default="out/scale_labels.jsonl")
    ap.add_argument("--positions", type=int, default=560)
    ap.add_argument("--rollouts", type=int, default=8)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--sample-seed", type=int, default=20260806)
    ap.add_argument("--exclude", default="out/labels_main.jsonl",
                    help="already-labelled positions to REUSE rather than redo")
    ap.add_argument("--max-rss-gb", type=float, default=24.0)
    args = ap.parse_args()

    import sp_engine as E
    prov = E.provenance()
    print(f"policy={args.policy}  workers={args.workers}  "
          f"decide-tree rolled {prov['rolled'][:16]}", flush=True)

    d = np.load(args.corpus)
    C, V, L, P = d["col"], d["vir"], d["link"], d["pills"]
    rng = random.Random(args.sample_seed)
    idxs = list(range(len(C)))
    rng.shuffle(idxs)
    want = sorted(idxs[:args.positions])

    reuse = set()
    if args.exclude and os.path.exists(args.exclude):
        reuse = {json.loads(l)["idx"] for l in open(args.exclude) if l.strip()}
        print(f"reusing {len(reuse)} positions already labelled in {args.exclude} "
              f"(CRN is a within-position property, so their original stream bases "
              f"remain valid)", flush=True)

    done = set()
    if os.path.exists(args.out):
        for l in open(args.out):
            l = l.strip()
            if not l:
                continue
            try:
                done.add(json.loads(l)["idx"])
            except Exception:
                pass
        print(f"RESUMING: {len(done)} positions already in {args.out}", flush=True)

    todo = [i for i in want if i not in reuse and i not in done]
    print(f"target {args.positions} positions; {len(reuse & set(want))} reused, "
          f"{len(done)} resumed, {len(todo)} to do", flush=True)
    if not todo:
        print("nothing to do")
        return 0

    jobs = [(i, C[i].astype(np.int8), V[i].astype(np.int8), L[i].astype(np.int8),
             int(P[i][0]), int(P[i][1]), int(P[i][2]), int(P[i][3]), args.rollouts)
            for i in todo]

    wd = threading.Thread(target=_rss_watchdog,
                          args=(os.getpid(), args.max_rss_gb), daemon=True)
    wd.start()

    t0 = time.time()
    n = 0
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_worker,
                             initargs=(args.policy,)) as ex:
        futs = {ex.submit(_worker, j): j[0] for j in jobs}
        for f in as_completed(futs):
            if _ABORT.is_set():
                for g in futs:
                    g.cancel()
                break
            r = f.result()
            if r is not None:
                # APPEND under flock: a restarted or concurrent writer cannot
                # interleave a partial record into the middle of a line.
                with open(args.out, "a") as fh:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            n += 1
            if n % 20 == 0 or n == len(jobs):
                el = time.time() - t0
                print(f"  {n}/{len(jobs)} {el:.0f}s eta "
                      f"{el/n*(len(jobs)-n):.0f}s", flush=True)
    _ABORT.set()
    print(f"{'ABORTED' if _ABORT.is_set() and n < len(jobs) else 'done'}: "
          f"{n}/{len(jobs)} in {time.time()-t0:.0f}s -> {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
