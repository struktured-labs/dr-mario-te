#!/usr/bin/env python3
"""STAGE 2 -- SUPERVISED FLOOR: can a LEARNED eval beat hand-tuned coefficients?

WHY THIS RUNS AT DEPTH 2 (the design decision that makes Stage 2 possible at all)
---------------------------------------------------------------------------------
Stage 1 ended with a retraction: my fitting arm could not reproduce the hand weights
over the same features at the same depth, so its negative was about the LABEL BUDGET,
not about features. Training a network on those same 1,400 noisy rows would fail the
same way and teach nothing. The label wall is the critical path, so it gets solved
first rather than worked around.

Measured cost and strength of the candidate rollout policies (L11, this box):

    policy            ms/game     clear rate
    depth-1                71          0%     <- unusable: no signal in the target
    depth-2               395         73%     <- 58x cheaper than the champion
    depth-3 (delta)      4729         75%
    champion (d3)      ~23000         ~90%

Depth-1 is free but never clears, so "pills to clear" is undefined for every rollout
and the value target carries no signal. Depth-2 clears 73% -- close to depth-3's 75%
-- at 58x the champion's speed. So the whole of Stage 2 runs in a DEPTH-2 WORLD:
depth-2 rollouts produce the labels, and the test is depth-2-with-learned-leaf vs
depth-2-with-hand-leaf. Only the leaf differs.

This is a deliberate scientific reduction, not a shortcut:
  * it answers the literal Stage-2 question -- can supervised learning on rollout
    labels beat five hand-tuned coefficients as a leaf evaluator
  * it answers the RETRACTED features-vs-coefficients question with ~20x the
    positions, which is what that question needed and never had
  * a negative here is cheap and strong: if learning cannot beat hand tuning with
    abundant labels in the cheap regime, it will not do so in the expensive one
  * a positive licenses spending real compute to repeat it at depth 3

THE GATE, carried forward from Stage 1 and non-negotiable
---------------------------------------------------------
A fitted LINEAR model over the eleven existing terms must MATCH the hand weights at
the same depth before any conclusion is drawn from a fit. Stage 1 failed this at 140
positions. If it fails again here at ~3000, that failure is then informative rather
than merely limiting -- it would say the label budget is not the obstacle after all.

HONEST CAVEAT to carry into the writeup: the hand weights were tuned for depth-3
play, so at depth 2 they are somewhat off-design. That makes the calibration gate
EASIER to pass, not harder, and it does not corrupt the comparisons that matter --
those are between FITTED models (linear vs nonlinear vs richer features) trained and
scored under identical conditions, with the hand weights as a reference point.

The value scalar, controls (split-sample estimator, permutation null, common random
numbers, cross-validation by position) are all inherited unchanged from Stage 1.
"""
from __future__ import annotations

import os
import sys
import json
import time
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np

ROLLOUT_CAP = 250
TOPK_ACTS = 8
RAND_ACTS = 2
LEVEL = 11

_W = {}


def _build_d2():
    """njit depth-2 root search returning per-action values AND the argmax.

    Self-consistent by construction: the SAME function supplies the corpus policy,
    the rollout policy, contender selection and the evaluation baseline, so there is
    no chance of the policy and its own value ranking drifting apart. It is depth-2
    in the plain sense -- immediate reward, then the best ply-2 reply scored by the
    shipped leaf -- and it is not required to be bit-identical to
    fast_rtl_x._choose_d2_rtl, only to be the policy this stage defines and uses
    everywhere. `selftest_clear_rate` checks it plays like the measured depth-2.
    """
    from numba import njit
    import fast_rtl_x as FX
    from fast_sim_x import NCELL, _expand_core, _virus_count

    VAR_OF_O4 = FX._VAR_OF_O4
    R_WVIR, R_WCELLS, R_VBONUS = FX.R_WVIR, FX.R_WCELLS, FX.R_VBONUS
    WIN = FX._WIN_SHIP
    leafv = FX._leafv_ship

    @njit(cache=True, fastmath=False)
    def d2_root(pcol, pvir, ca, cb, na, nb, w, fl, out_val, out_ok):
        c1 = np.empty(NCELL, dtype=np.int8)
        v1 = np.empty(NCELL, dtype=np.int8)
        c2 = np.empty(NCELL, dtype=np.int8)
        v2 = np.empty(NCELL, dtype=np.int8)
        for i in range(32):
            out_ok[i] = 0
            out_val[i] = 0.0
        best_val = 0.0
        best_act = -1
        have = False
        for o4 in range(4):
            var = VAR_OF_O4[o4]
            for cc in range(8):
                ok, nv, cells = _expand_core(pcol, pvir, var, cc, ca, cb, c1, v1)
                if ok == 0:
                    continue
                imm1 = (float(w[R_WVIR]) * nv + float(w[R_WCELLS]) * cells
                        + (float(w[R_VBONUS]) if nv >= 2 else 0.0))
                if _virus_count(v1) == 0:
                    val = imm1 + float(WIN)
                else:
                    best2 = 0.0
                    have2 = False
                    for o42 in range(4):
                        var2 = VAR_OF_O4[o42]
                        for c2c in range(8):
                            ok2, nv2, cl2 = _expand_core(c1, v1, var2, c2c,
                                                         na, nb, c2, v2)
                            if ok2 == 0:
                                continue
                            imm2 = (float(w[R_WVIR]) * nv2 + float(w[R_WCELLS]) * cl2
                                    + (float(w[R_VBONUS]) if nv2 >= 2 else 0.0))
                            v = imm2 + float(leafv(c2, v2, w, fl))
                            if not have2 or v > best2:
                                best2 = v
                                have2 = True
                    val = imm1 + (best2 if have2 else float(leafv(c1, v1, w, fl)))
                a = var * 8 + cc
                out_val[a] = val
                out_ok[a] = 1
                if not have or val > best_val:
                    best_val = val
                    best_act = a
                    have = True
        return best_act

    return d2_root


class D2:
    def __init__(self, w=None, fl=None):
        import fast_rtl_x as FX
        FX.warmup_ship_eh(topk2=8)
        dw, dfl = FX.variant("winner")
        self.w = dw if w is None else w
        self.fl = dfl if fl is None else fl
        self.f = _build_d2()
        self.val = np.zeros(32, dtype=np.float64)
        self.ok = np.zeros(32, dtype=np.int8)

    def choose(self, col, vir, ca, cb, na, nb):
        return self.f(col, vir, int(ca), int(cb), int(na), int(nb),
                      self.w, self.fl, self.val, self.ok)

    def values(self, col, vir, ca, cb, na, nb):
        a = self.choose(col, vir, ca, cb, na, nb)
        return a, self.val, self.ok


def _play(env, pol, cap, force_first=None):
    import sp_engine as E
    used = 0
    first = force_first
    for _ in range(cap):
        if env.board.virus_count() == 0:
            return "clear", used
        if first is not None:
            a = first
            first = None
        else:
            col, vir, _l = E.board_planes(env.board)
            a = pol.choose(col, vir, env.cur.a, env.cur.b, env.nxt.a, env.nxt.b)
            if a < 0:
                return "topout", used
        _o, _r, term, trunc, info = env.step(int(a))
        used += 1
        if term:
            return ("clear" if info["won"] else "topout"), used
        if trunc:
            return "stall", used
    return "stall", used


def _init_worker():
    import sp_engine as E
    _W["pol"] = D2()
    _W["env"] = E.new_env(level=LEVEL, seed=0, cap=ROLLOUT_CAP)


def _corpus_worker(seed):
    import sp_engine as E
    pol = _W["pol"]
    env = E.new_env(level=LEVEL, seed=seed, cap=300)
    E.attach_stream(env, seed)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    out = []
    for ply in range(300):
        if env.board.virus_count() == 0:
            break
        col, vir, link = E.board_planes(env.board)
        a = pol.choose(col, vir, env.cur.a, env.cur.b, env.nxt.a, env.nxt.b)
        if a < 0:
            break
        out.append(dict(seed=seed, ply=ply, col=col.copy(), vir=vir.copy(),
                        link=link.copy(), ca=int(env.cur.a), cb=int(env.cur.b),
                        na=int(env.nxt.a), nb=int(env.nxt.b),
                        nvir=int(env.board.virus_count()), hand_act=int(a)))
        _o, _r, term, trunc, _i = env.step(int(a))
        if term or trunc:
            break
    return out


def cmd_corpus(args):
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers,
                             initializer=_init_worker) as ex:
        futs = [ex.submit(_corpus_worker, s) for s in range(args.games)]
        for i, f in enumerate(as_completed(futs)):
            rows.extend(f.result())
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{args.games} games {len(rows)} positions "
                      f"{time.time()-t0:.0f}s", flush=True)
    print(f"corpus: {len(rows)} positions from {args.games} games "
          f"in {time.time()-t0:.0f}s", flush=True)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    np.savez_compressed(
        args.out,
        col=np.stack([r["col"] for r in rows]),
        vir=np.stack([r["vir"] for r in rows]),
        link=np.stack([r["link"] for r in rows]),
        pills=np.array([[r["ca"], r["cb"], r["na"], r["nb"]] for r in rows],
                       dtype=np.int8),
        meta=np.array([[r["seed"], r["ply"], r["nvir"], r["hand_act"]] for r in rows],
                      dtype=np.int32))
    print(f"wrote {args.out}", flush=True)


def _label_worker(job):
    import sp_engine as E
    import fast_rtl_x as FX
    from fast_sim_x import NCELL, _expand_core

    pol = _W["pol"]
    env = _W["env"]
    idx, pos, M, base = job
    col = np.asarray(pos["col"], dtype=np.int8)
    vir = np.asarray(pos["vir"], dtype=np.int8)
    link = np.asarray(pos["link"], dtype=np.int8)
    ca, cb, na, nb = pos["ca"], pos["cb"], pos["na"], pos["nb"]

    hand_act, val, ok = pol.values(col, vir, ca, cb, na, nb)
    val = val.copy()
    ok = ok.copy()
    legal = [a for a in range(32) if ok[a] == 1]
    if len(legal) < 3:
        return None
    topk = sorted(legal, key=lambda a: -val[a])[:TOPK_ACTS]
    rest = [a for a in legal if a not in set(topk)]
    rng = random.Random(base)
    extra = rng.sample(rest, min(RAND_ACTS, len(rest)))
    acts = sorted(set(topk) | set(extra))

    base_arr = np.empty(FX.NBASE, dtype=np.int64)
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    terms, wins = {}, {}
    for a in acts:
        var, cc = a // 8, a % 8
        okk, nv, cl = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
        FX._base_scan(c1, v1, pol.fl, base_arr)
        terms[str(a)] = [int(x) for x in base_arr[:FX.NT]]
        wins[str(a)] = int(FX._virus_count(v1) == 0)

    rec = dict(idx=idx, nvir=int(pos["nvir"]), hand_act=int(hand_act), acts=acts,
               n_legal=len(legal), hand_val={str(a): float(val[a]) for a in acts},
               terms=terms, win=wins, pills={}, outcome={})
    p = dict(col=col, vir=vir, link=link)
    for a in acts:
        pl, oc = [], []
        for m in range(M):
            E.attach_stream(env, base + m)
            E.set_board(env.board, col, vir, link)
            E.set_pills(env, ca, cb, na, nb)
            env.pills_placed = 0
            env._start_viruses = int(env.board.virus_count())
            out, used = _play(env, pol, ROLLOUT_CAP, force_first=a)
            pl.append(int(used))
            oc.append(out)
        rec["pills"][str(a)] = pl
        rec["outcome"][str(a)] = oc
    return rec


def cmd_label(args):
    import sp_engine as E
    d = np.load(args.corpus)
    col, vir, link, pills, meta = d["col"], d["vir"], d["link"], d["pills"], d["meta"]
    n = len(col)
    rng = random.Random(args.sample_seed)
    idxs = list(range(n))
    rng.shuffle(idxs)
    idxs = sorted(idxs[:args.positions])
    print(f"corpus {n} positions, labelling {len(idxs)}", flush=True)
    prov = E.provenance()
    print(f"decide tree {prov['decide_tree']}  rolled {prov['rolled'][:16]}", flush=True)

    jobs = []
    for k, i in enumerate(idxs):
        pos = dict(col=col[i], vir=vir[i], link=link[i],
                   ca=int(pills[i][0]), cb=int(pills[i][1]),
                   na=int(pills[i][2]), nb=int(pills[i][3]),
                   nvir=int(meta[i][2]))
        jobs.append((int(i), pos, args.rollouts, 3000000 + k * 977))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    t0 = time.time()
    done = 0
    with open(args.out, "w") as fh, \
         ProcessPoolExecutor(max_workers=args.workers,
                             initializer=_init_worker) as ex:
        futs = [ex.submit(_label_worker, j) for j in jobs]
        for f in as_completed(futs):
            r = f.result()
            if r is not None:
                fh.write(json.dumps(r) + "\n")
                fh.flush()
            done += 1
            if done % 100 == 0 or done == len(jobs):
                el = time.time() - t0
                print(f"  {done}/{len(jobs)} {el:.0f}s "
                      f"eta {el/done*(len(jobs)-done):.0f}s", flush=True)
    print(f"wrote {args.out}", flush=True)


def cmd_selftest(args):
    """Check the njit depth-2 plays like the measured depth-2 (73% clear at L11)."""
    import sp_engine as E
    pol = D2()
    res = []
    for s in range(args.games):
        env = E.new_env(level=LEVEL, seed=s, cap=300)
        E.attach_stream(env, s)
        env.cur = env._rand_pill()
        env.nxt = env._rand_pill()
        res.append(_play(env, pol, 300)[0])
    clr = sum(1 for r in res if r == "clear") / len(res)
    print(f"d2_root self-test: {len(res)} games, clear {clr:.0%} "
          f"(reference _choose_d2_rtl measured 73%)")
    print("PASS" if 0.55 <= clr <= 0.90 else "FAIL -- policy does not match depth-2")
    return 0 if 0.55 <= clr <= 0.90 else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("selftest")
    s.add_argument("--games", type=int, default=40)
    s.set_defaults(fn=cmd_selftest)
    c = sub.add_parser("corpus")
    c.add_argument("--games", type=int, default=1200)
    c.add_argument("--workers", type=int, default=4)
    c.add_argument("--out", default="out/s2_corpus.npz")
    c.set_defaults(fn=cmd_corpus)
    l = sub.add_parser("label")
    l.add_argument("--corpus", default="out/s2_corpus.npz")
    l.add_argument("--positions", type=int, default=3000)
    l.add_argument("--rollouts", type=int, default=8)
    l.add_argument("--workers", type=int, default=4)
    l.add_argument("--sample-seed", type=int, default=20260807)
    l.add_argument("--out", default="out/s2_labels.jsonl")
    l.set_defaults(fn=cmd_label)
    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
