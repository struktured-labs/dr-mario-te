#!/usr/bin/env python3
"""STAGE 1c -- HOW MUCH DOES THE LEAF EVAL CONTROL THE MOVE AT ALL?

An independent, rollout-free bound on the same question Stage 1 attacks with
Monte-Carlo. It needs no value labels, so it cannot be wrong in the ways a noisy
oracle can be, and it costs ~200 ms per position per arm instead of ~13 minutes.

THE IDEA
--------
Replace the leaf evaluator inside the SHIPPED depth-3 search and count how often
the chosen root move changes. The decisive arm is FLAT: every leaf weight zeroed,
so the leaf returns a constant for any non-winning board. A flat leaf does not
disable the search -- immediate rewards (viruses cleared, cells cleared, the
2-virus bonus), the win bonus, the excav/hang ply-1 add-on and the g_stranded cost
all still operate. What it removes is precisely the eval's opinion about board
SHAPE.

So the agreement rate between the champion and FLAT is a direct measurement of how
much of the champion's behaviour the leaf eval is responsible for:

    agreement(champion, FLAT) = X%   =>   on X% of decisions the shipped eval's
                                          opinion about shape is irrelevant to the
                                          move, and NO leaf evaluator whatsoever --
                                          learned, oracular, or hand-tuned -- can
                                          change what happens there.

That makes (100 - X)% a hard CEILING on the fraction of decisions any eval work
can touch. It bounds reach, not value: the moves the eval does control could still
be the ones that matter. Read alongside Stage 1's regret, not instead of it.

The other arms (r47, vrdy12, and random weight draws) calibrate that ceiling: they
say how much move-change a LARGE but reasonable eval change actually produces, so
the flat number can be read as "wide" or "narrow" against something real rather
than against intuition.

Every arm keeps the champion's g_stranded ws=20 root cost, and changes only the
leaf weights -- one thing at a time.
"""
from __future__ import annotations

import os
import sys
import json
import random
import argparse
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np


def build_arms(rng, n_random=3):
    import fast_rtl_x as FX
    arms = {}
    arms["winner"] = FX.variant("winner")[0]
    arms["r47"] = FX.variant("r47")[0]
    arms["vrdy12"] = FX.variant("vrdy12")[0]

    # FLAT: leaf returns a constant for every non-winning board. Immediate rewards,
    # win bonus, excav/hang and g_stranded are untouched -- only the eval's opinion
    # about board shape is removed.
    w = FX.variant("winner")[0].copy()
    for i in (FX.R_MAXH, FX.R_HOLES, FX.R_TOPRISK, FX.R_SPAWN, FX.R_SETUP,
              FX.R_MATCHED, FX.R_BURIED, FX.R_RDYEXT, FX.R_VRDY, FX.R_CROSS,
              FX.R_POLL):
        w[i] = 0.0
    arms["flat"] = w

    # random draws at the shipped scale -- "a big arbitrary eval change"
    base = FX.variant("winner")[0]
    idx = [FX.R_MAXH, FX.R_HOLES, FX.R_TOPRISK, FX.R_SPAWN, FX.R_SETUP,
           FX.R_MATCHED, FX.R_BURIED, FX.R_RDYEXT, FX.R_VRDY, FX.R_POLL]
    scale = st.mean(abs(float(base[i])) for i in idx)
    for k in range(n_random):
        w = base.copy()
        for i in idx:
            w[i] = abs(rng.gauss(0.0, scale))
        arms[f"rand{k}"] = w
    return arms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="out/corpus.npz")
    ap.add_argument("--positions", type=int, default=600)
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--out", default="out/leverage.json")
    args = ap.parse_args()

    import sp_engine as E
    champ = E.Champion()
    rng = random.Random(args.seed)
    arms = build_arms(rng)

    d = np.load(args.corpus)
    col_a, vir_a, pills_a = d["col"], d["vir"], d["pills"]
    n = len(col_a)
    idxs = list(range(n))
    rng.shuffle(idxs)
    idxs = idxs[:args.positions]

    val = np.zeros(32, dtype=np.float64)
    ok = np.zeros(32, dtype=np.int8)
    picks = {k: [] for k in arms}
    for i in idxs:
        col = col_a[i].astype(np.int8)
        vir = vir_a[i].astype(np.int8)
        p = pills_a[i]
        for name, w in arms.items():
            a = E.champ_root(col, vir, int(p[0]), int(p[1]), int(p[2]), int(p[3]),
                             champ.topk2, E.W_EXCAV, E.W_HANG, w, champ.fl,
                             champ.ws, val, ok)
            picks[name].append(int(a))

    ref = picks["winner"]
    N = len(ref)
    print(f"positions: {N}\n")
    print("agreement with the champion's root move:")
    out = {"n": N, "agreement": {}}
    for name in arms:
        if name == "winner":
            continue
        agree = sum(1 for x, y in zip(ref, picks[name]) if x == y) / N
        # column-only agreement: same landing column, orientation may differ
        colagree = sum(1 for x, y in zip(ref, picks[name])
                       if x % 8 == y % 8) / N
        out["agreement"][name] = {"exact": agree, "column": colagree}
        print(f"  {name:8s}  exact {agree:6.1%}   same-column {colagree:6.1%}")

    fl = out["agreement"]["flat"]["exact"]
    print()
    print(f"CEILING: the leaf eval's opinion about board shape is irrelevant to the")
    print(f"move on {fl:.1%} of decisions, so at most {1-fl:.1%} of decisions are")
    print(f"reachable by ANY leaf evaluator -- learned, oracular or hand-tuned.")
    print("This bounds REACH, not value: the reachable moves may be the ones that")
    print("matter. Read with Stage 1's regret, not instead of it.")

    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
