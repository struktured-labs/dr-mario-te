#!/usr/bin/env python3
"""STAGE 1f -- DECOMPOSE THE CHAMPION'S REGRET: eval error vs horizon error.

THE FORK THIS SETTLES
---------------------
Stage 1 measured that a perfect leaf evaluator is worth ~+3.7 pills per decision.
That number does not say WHAT would capture it. Two very different causes produce
identical regret:

  HORIZON error -- the right move IS identifiable, but only by looking further
                   ahead than depth 3. No evaluator at depth 3 can find it; the
                   remedy is deeper search.
  EVAL error    -- the right move is identifiable at depth 3, and the search misses
                   it because the leaf valuation is wrong. More depth does not help;
                   the remedy is a better evaluator.

The measurement is direct: re-search each position at increasing depth with the
SAME leaf evaluator and value what it picks against the rollout labels.

    regret(d) falling with depth   => horizon-limited
    regret(d) flat or rising       => eval-limited

WHAT THIS PROJECT ALREADY KNOWS (cited, not re-derived)
-------------------------------------------------------
The capsule-lookahead work (dr-mario-capsule-lookahead-negative, n=240 windowed /
n=120 full-game, real NES stream) already answered the information half of this:
  * depth-3 fed the TRUE third capsule:  +0.17 pills [-4.28,+4.62] -- null
  * the same search fed a WRONG capsule: +6.23 pills [+1.17,+11.43] -- so the
    instrument resolves a 6-pill effect and the null is not underpowered
  * a CLAIRVOYANT depth-5 beam search: +20.17 pills WORSE than shipped depth-3,
    clear rate 81.7% vs 95.8%, discordant 2/19, p=0.0002
Its own conclusion: "the binding constraint is EVAL QUALITY, not capsule
uncertainty". So the expected outcome here is NOT news; the job is to QUANTIFY how
heavily, on the same positions and the same ruler as the Stage-1 headroom number.

The clairvoyant result also predicts the SIGN. A deeper search optimises the hand
eval harder. If the eval is wrong, optimising it harder should move AWAY from the
oracle's move, not toward it. That is a sharp falsifiable prediction and this file
tests it: if regret(d4) > regret(d3), search is amplifying eval error.

TWO CEILINGS, NEVER CONFLATED
-----------------------------
A clairvoyant player (full pill sequence known) is an UPPER BOUND and a diagnostic
only -- the seed is recoverable by an analyst after the fact but is NOT in the
agent's information set at decision time, which sees one pill and one preview. The
legitimate ceiling is the expectimax optimum over the pill distribution given
current + preview. Everything measured here is against rollout value under that
(uncertain) regime; nothing in this file uses future-pill knowledge, and no
clairvoyant arm is used as a target.

KEEPING ONLY DEPTH AS THE VARIABLE
----------------------------------
d4_kernel._choose_d4_ship_eh_delta is, by its own docstring, "_choose_d3_ship_eh_delta
with the ply-3 MAX layer replaced by beam+ply-4. Every other line is the d3 original."
So the clean one-variable comparison is d3_nostrand -> d4: same weights, same
excav/hang add-on, same delta-eval leaf, differing ONLY in the extra ply. The
champion additionally carries g_stranded ws=20 root-only, which the d4 kernel has no
hook for; rather than hand-wave that away, the champion is reported as its own arm
and the DEPTH TREND is read off the internally-consistent no-stranded ladder.

Usage:
  stage1_depth.py --labels out/labels_main.jsonl --corpus out/corpus.npz \
                  --workers 4 --out out/depth.jsonl
  stage1_depth.py analyze --depth out/depth.jsonl --labels out/labels_main.jsonl
"""
from __future__ import annotations

import os
import sys
import json
import math
import time
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np

ROLLOUT_CAP = 200
VALUE_CENSOR = 200.0
D4_TREE = "/home/struktured/projects/dr-mario-main-wt/experiments/depth4"

_W = {}


def _init_worker():
    import sp_engine as E
    if D4_TREE not in sys.path:
        sys.path.insert(0, D4_TREE)
    import d4_kernel as K
    K.warmup_d4(topk2=8, topk3=6, pills4="4")
    _W["champ"] = E.Champion()
    _W["K"] = K
    _W["env"] = E.new_env(level=E.LEVEL, seed=0, cap=ROLLOUT_CAP)


def _arms(col, vir, ca, cb, na, nb):
    """Chosen action per ladder arm. Same 'winner' leaf weights throughout."""
    import sp_engine as E
    import fast_rtl_x as FX
    K = _W["K"]
    champ = _W["champ"]
    w, fl = champ.w, champ.fl
    p4x, p4y = K._P4["4"]
    out = {}
    out["d1"] = int(FX._choose_d1_rtl(col, vir, ca, cb, w, fl))
    out["d3_champ"] = int(champ.choose(col, vir, ca, cb, na, nb))
    out["d3"] = int(FX._choose_d3_ship_eh_delta(
        col, vir, ca, cb, na, nb, 8, int(FX._W_EXCAV_SHIP), int(FX._W_HANG_SHIP), w, fl))
    out["d4"] = int(K._choose_d4_ship_eh_delta(
        col, vir, ca, cb, na, nb, 8, 6, 1, p4x, p4y,
        int(FX._W_EXCAV_SHIP), int(FX._W_HANG_SHIP), w, fl))
    # DEGENERACY GATE, per d4_kernel's own contract: with topk3=0 and ply4_mode=0 the
    # extra layer collapses and d4 MUST reproduce d3 exactly. If this ever fails, the
    # d3->d4 comparison is not a one-variable comparison and nothing below is valid.
    out["_d4_degen"] = int(K._choose_d4_ship_eh_delta(
        col, vir, ca, cb, na, nb, 8, 0, 0, p4x, p4y,
        int(FX._W_EXCAV_SHIP), int(FX._W_HANG_SHIP), w, fl))
    return out


def _worker(job):
    import sp_engine as E
    idx, pos, stream_base, M, known = job
    col = np.asarray(pos["col"], dtype=np.int8)
    vir = np.asarray(pos["vir"], dtype=np.int8)
    link = np.asarray(pos["link"], dtype=np.int8)
    ca, cb, na, nb = pos["ca"], pos["cb"], pos["na"], pos["nb"]

    arms = _arms(col, vir, ca, cb, na, nb)
    need = sorted({a for k, a in arms.items()
                   if not k.startswith("_") and a >= 0 and a not in known})
    champ = _W["champ"]
    env = _W["env"]
    p = dict(col=col, vir=vir, link=link, ca=ca, cb=cb, na=na, nb=nb)
    vals = {}
    for a in need:
        pl, oc = [], []
        for m in range(M):
            out, used = E.rollout_value(p, a, stream_base + m, champ,
                                        cap=ROLLOUT_CAP, env=env)
            pl.append(int(used))
            oc.append(out)
        vals[str(a)] = {"pills": pl, "outcome": oc}
    return {"idx": idx, "arms": arms, "new_vals": vals,
            "degen_ok": int(arms["_d4_degen"] == arms["d3"])}


def rebuild_stream_bases(corpus_n, positions, sample_seed):
    """Reproduce stage1.py cmd_label's idx -> stream_base mapping exactly.

    The labelling run did: shuffle(range(n)) with Random(sample_seed), take the first
    `positions`, SORT them, then assign stream_base = 1000000 + k*977 by enumeration
    order. Rebuilding it is what lets new rollouts share pill streams with the old
    ones -- without that the common-random-numbers pairing is broken and every
    comparison below silently loses its variance reduction. Gated in main().
    """
    rng = random.Random(sample_seed)
    idxs = list(range(corpus_n))
    rng.shuffle(idxs)
    idxs = sorted(idxs[:positions])
    return {int(i): 1000000 + k * 977 for k, i in enumerate(idxs)}


def cmd_run(args):
    import sp_engine as E
    d = np.load(args.corpus)
    col, vir, link, pills = d["col"], d["vir"], d["link"], d["pills"]
    recs = [json.loads(l) for l in open(args.labels) if l.strip()]
    bases = rebuild_stream_bases(len(col), args.positions, args.sample_seed)

    prov = E.provenance()
    print(f"decide tree : {prov['decide_tree']}")
    print(f"rolled hash : {prov['rolled'][:16]}")

    # GATE: reproduce one ALREADY-LABELLED rollout and require the pill counts to
    # match exactly. That proves the stream-base reconstruction is right; if it is
    # wrong, new rollouts silently use different pill streams and every paired
    # comparison in this file becomes noise dressed as signal.
    champ = E.Champion()
    env = E.new_env(level=E.LEVEL, seed=0, cap=ROLLOUT_CAP)
    r0 = recs[0]
    i0 = r0["idx"]
    a0 = r0["acts"][0]
    p0 = dict(col=col[i0], vir=vir[i0], link=link[i0],
              ca=int(pills[i0][0]), cb=int(pills[i0][1]),
              na=int(pills[i0][2]), nb=int(pills[i0][3]))
    got = []
    for m in range(len(r0["pills"][str(a0)])):
        _o, used = E.rollout_value(p0, a0, bases[i0] + m, champ,
                                   cap=ROLLOUT_CAP, env=env)
        got.append(int(used))
    want = r0["pills"][str(a0)]
    if got != want:
        print(f"STREAM GATE FAIL idx={i0} a={a0}\n  got  {got}\n  want {want}")
        return 1
    print(f"stream gate : PASS (idx={i0} a={a0} pills {want})")

    jobs = []
    for r in recs:
        i = r["idx"]
        pos = dict(col=col[i], vir=vir[i], link=link[i],
                   ca=int(pills[i][0]), cb=int(pills[i][1]),
                   na=int(pills[i][2]), nb=int(pills[i][3]))
        M = len(r["pills"][str(r["acts"][0])])
        jobs.append((int(i), pos, bases[i], M, set(r["acts"])))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    t0 = time.time()
    done = degen_bad = 0
    with open(args.out, "w") as fh, \
         ProcessPoolExecutor(max_workers=args.workers,
                             initializer=_init_worker) as ex:
        futs = [ex.submit(_worker, j) for j in jobs]
        for f in as_completed(futs):
            rec = f.result()
            degen_bad += (rec["degen_ok"] == 0)
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            done += 1
            if done % 10 == 0 or done == len(jobs):
                el = time.time() - t0
                print(f"  {done}/{len(jobs)}  {el:.0f}s  "
                      f"eta {el/done*(len(jobs)-done):.0f}s", flush=True)
    print(f"d4 degeneracy gate failures: {degen_bad} "
          f"-> {'PASS' if degen_bad == 0 else 'FAIL'}")
    print(f"wrote {args.out}")
    return 0


# ===================================================================== analysis
def _v(pills, outcome):
    return [(-float(p) if o == "clear" else -VALUE_CENSOR)
            for p, o in zip(pills, outcome)]


def boot_ci(xs, n=10000, seed=5):
    if len(xs) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(st.mean([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def _split_regret(vals, acts, a_ref, rng, nsplits, M):
    """Oracle gain over `a_ref`, averaged over random selection/evaluation splits.

    Identical estimator to stage1.py::_split_regret so the depth arms land on the
    SAME ruler as the Stage-1 headroom number (+3.73 pills). Selection and scoring
    use disjoint rollouts, so it is unbiased for an oracle selecting on M/2."""
    half = M // 2
    tot = 0.0
    for _ in range(nsplits):
        idx = list(range(M))
        rng.shuffle(idx)
        sel, ev = idx[:half], idx[half:]
        vs = {a: st.mean(vals[a][i] for i in sel) for a in acts}
        ve = {a: st.mean(vals[a][i] for i in ev) for a in acts}
        tot += ve[max(acts, key=lambda a: vs[a])] - ve[a_ref]
    return tot / nsplits


def cmd_analyze(args):
    split_rng = random.Random(args.split_seed)
    lab = {r["idx"]: r for r in (json.loads(l) for l in open(args.labels) if l.strip())}
    dep = [json.loads(l) for l in open(args.depth) if l.strip()]
    print(f"positions: {len(dep)}")
    degen_bad = sum(1 for r in dep if r["degen_ok"] == 0)
    print(f"d4 degeneracy gate failures (want 0): {degen_bad}")

    arms = ["d1", "d3", "d3_champ", "d4"]
    V = {a: [] for a in arms}
    reg = {a: [] for a in arms}
    agree_oracle = {a: [] for a in arms}
    d4_vs_d3 = []
    oracle_minus_d4 = []
    nfound = 0

    for r in dep:
        i = r["idx"]
        if i not in lab:
            continue
        L = lab[i]
        vals = {int(a): _v(L["pills"][a], L["outcome"][a]) for a in L["pills"]}
        for a, d in r["new_vals"].items():
            vals[int(a)] = _v(d["pills"], d["outcome"])
        if len(vals) < 3:
            continue
        mean = {a: st.mean(v) for a, v in vals.items()}
        M = min(len(v) for v in vals.values())
        if M < 4:
            continue
        acts_here = sorted(vals)
        a_or = max(mean, key=lambda a: mean[a])
        nfound += 1
        for a in arms:
            act = r["arms"].get(a, -1)
            if act < 0 or act not in mean:
                continue
            V[a].append(mean[act])
            # SPLIT-SAMPLE regret, same estimator as stage1.py: the oracle is chosen
            # on one half of the rollouts and scored on the other, averaged over many
            # random partitions. A same-sample argmax here would be winner's-curse
            # inflated exactly as it was in Stage 1 (+6.77 of pure noise under the
            # null), and would overstate the EVAL component of this decomposition.
            reg[a].append(_split_regret(vals, acts_here, act, split_rng,
                                        args.splits, M))
            agree_oracle[a].append(1.0 if act == a_or else 0.0)
        if r["arms"]["d3"] in mean and r["arms"]["d4"] in mean:
            # HORIZON is a DIRECT paired comparison of two arms -- no oracle, so no
            # winner's curse to correct. EVAL uses the split-sample oracle.
            d4_vs_d3.append(mean[r["arms"]["d4"]] - mean[r["arms"]["d3"]])
            oracle_minus_d4.append(_split_regret(vals, acts_here, r["arms"]["d4"],
                                                 split_rng, args.splits, M))

    def line(tag, xs, unit="pills"):
        if not xs:
            print(f"{tag:40s} (no data)")
            return None
        lo, hi = boot_ci(xs)
        print(f"{tag:40s} {st.mean(xs):+8.3f}  [{lo:+.3f},{hi:+.3f}]  n={len(xs)} {unit}")
        return st.mean(xs)

    print()
    print("=" * 78)
    print("REGRET vs the rollout oracle, BY SEARCH DEPTH (same leaf eval throughout)")
    print("=" * 78)
    for a in arms:
        line(f"  regret({a})", reg[a])
    print()
    for a in arms:
        line(f"  P({a} == oracle move)", agree_oracle[a], "")

    print()
    print("=" * 78)
    print("THE DECOMPOSITION")
    print("=" * 78)
    h = line("  HORIZON: V(d4) - V(d3), paired", d4_vs_d3)
    e = line("  EVAL   : V(oracle) - V(d4), paired", oracle_minus_d4)
    print()
    if h is not None and e is not None:
        tot = (h if h > 0 else 0.0) + e
        if tot > 0:
            print(f"  one extra ply of the SAME eval buys : {h:+.2f} pills")
            print(f"  still unreached by that deeper search: {e:+.2f} pills")
            if h <= 0:
                print()
                print("  READ: depth does NOT help. The extra ply moves play AWAY from")
                print("  the oracle -- a deeper search optimises the hand eval harder, and")
                print("  when the eval is wrong that is worse, not better. The regret is")
                print("  EVAL error essentially in full. This matches the capsule-lookahead")
                print("  negative, where a CLAIRVOYANT depth-5 lost to shipped depth-3 by")
                print("  +20.17 pills (clear 81.7% vs 95.8%, p=0.0002).")
            else:
                frac = h / tot
                print()
                print(f"  READ: depth accounts for {frac:.0%} of the reachable gap and the")
                print(f"  evaluator for {1-frac:.0%}. Both levers are live; weight the")
                print("  program accordingly.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", default="run", choices=["run", "analyze"])
    ap.add_argument("--labels", default="out/labels_main.jsonl")
    ap.add_argument("--corpus", default="out/corpus.npz")
    ap.add_argument("--depth", default="out/depth.jsonl")
    ap.add_argument("--positions", type=int, default=140)
    ap.add_argument("--sample-seed", type=int, default=20260806)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="out/depth.jsonl")
    ap.add_argument("--splits", type=int, default=100)
    ap.add_argument("--split-seed", type=int, default=31)
    args = ap.parse_args()
    sys.exit(cmd_run(args) if args.mode == "run" else cmd_analyze(args))


if __name__ == "__main__":
    main()
