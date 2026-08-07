#!/usr/bin/env python3
"""Why do seeds 0-119 and 120-399 disagree about the executor? Zero new games.

The arm-D effect is absent on seeds 0-119 (+0.033, p=0.57) and present on
120-399 (-0.089, p=0.0026), permutation p=0.023 on a boundary specified
externally before I looked. The clean champion arm is flat across the same
split (119/120 vs 280/280), so it is not board difficulty moving the baseline
— it is the TREATMENT EFFECT that varies. Either seed blocks are not
interchangeable, which threatens every paired experiment in this project, or
it is one test in twenty.

Five analyses, all on the 400 games already played:

  1. INPUT FEATURES. Characterise the two blocks on the opening board and the
     capsule stream — the things a seed determines before a single pill is
     placed. A systematic input difference would be a mechanism; no
     difference pushes toward fluke.
  2. SHAPE. Split 120-399 into thirds. A smooth gradient and a cliff at 119
     mean different things: a gradient suggests something varying with seed
     index, a cliff with flat thirds suggests 0-119 is simply the odd one.
  3. SPLIT-POINT SCAN. The p=0.023 is honest for a pre-specified boundary, but
     it says nothing about how much apparent block structure this data has in
     general. Scanning every contiguous split calibrates that.
  4. STRUCTURAL SPLIT. `NesPillSource` maps seed -> LFSR state as
     s0=(seed>>8)&0xFF, s1=seed&0xFF, so ALL seeds below 256 share s0=0 and
     seeds 256+ have s0=1. That is a real discontinuity in the seed space at
     256 — not at 119 — and it is the one structural boundary that exists
     independently of anything I chose.
  5. DIRECT PREDICTION. Correlate the per-seed treatment effect against every
     input feature. This is the one that can actually find a mechanism: if
     nothing predicts the effect, block membership is not doing work either.

Usage: block_forensics.py
"""
from __future__ import annotations

import json
import os
import random
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS = os.path.dirname(HERE)
EVAL47 = os.path.join(EXPERIMENTS, "eval47")
for _p in (HERE, EXPERIMENTS, EVAL47):
    if _p not in sys.path:
        sys.path.insert(0, _p)

N_BOOT = 20000
RESULTS = os.path.join(HERE, "results")


# --------------------------------------------------------------------------
def per_seed_effect(fname="bursty_theta150.json", ctrl="v1_drop", arm="t3_tuck"):
    """d_s = bad_end(arm, s) - bad_end(ctrl, s), in {-1, 0, +1}."""
    d = json.load(open(os.path.join(RESULTS, fname)))
    rows = {k: {x["seed"]: x for x in v} for k, v in d["rows"].items()}
    A, B = rows[ctrl], rows[arm]
    ss = sorted(set(A) & set(B))
    return {s: (B[s]["topout"] + B[s]["stall"]) - (A[s]["topout"] + A[s]["stall"])
            for s in ss}


def seed_features(seed):
    """Everything a seed fixes BEFORE play: the opening virus layout and the
    capsule stream. No games, no policy, no outcome."""
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource

    env = FaithfulDrMarioEnv(level=11, seed=seed, max_pills=300)
    env.reset()
    b = env.board
    vr, vc = np.nonzero(b.is_virus)
    colours = [int(b.color[r, c]) for r, c in zip(vr, vc)]
    per_col = [int((vc == c).sum()) for c in range(8)]
    cnt = [colours.count(k) for k in (1, 2, 3)]

    src = NesPillSource(seed=seed)
    caps = [src.next_pill() for _ in range(100)]
    doubles = sum(1 for a, bb in caps if a == bb)
    pcnt = [sum(1 for a, bb in caps for x in (a, bb) if x == k) for k in (1, 2, 3)]
    switches = sum(1 for i in range(1, len(caps)) if caps[i] != caps[i - 1])

    return {
        "n_virus": len(colours),
        "virus_min_row": int(vr.min()) if len(vr) else 16,     # highest virus
        "virus_mean_row": float(vr.mean()) if len(vr) else 16.0,
        "virus_col_spread": int(sum(1 for x in per_col if x)),
        "virus_col_max": max(per_col),
        "virus_colour_imbalance": (max(cnt) - min(cnt)) / max(1, sum(cnt)),
        "pill_doubles_frac": doubles / len(caps),
        "pill_colour_imbalance": (max(pcnt) - min(pcnt)) / max(1, sum(pcnt)),
        "pill_distinct": len({c for c in caps}),
        "pill_switch_rate": switches / (len(caps) - 1),
        "lfsr_s0": (seed >> 8) & 0xFF,
    }


def perm_p(vals, n1, obs, seed=20260807, reps=N_BOOT):
    """Two-sided permutation p for a difference of means between a size-n1
    prefix and the rest, shuffling LABELS with every game held fixed."""
    rng = random.Random(seed)
    v = list(vals)
    hit = 0
    for _ in range(reps):
        rng.shuffle(v)
        if abs(st.mean(v[:n1]) - st.mean(v[n1:])) >= abs(obs) - 1e-12:
            hit += 1
    return hit / reps


def block_delta(eff, seeds_a, seeds_b):
    a = [eff[s] for s in seeds_a]
    b = [eff[s] for s in seeds_b]
    return st.mean(a) - st.mean(b), len(a), len(b)


# --------------------------------------------------------------------------
def main():
    eff = per_seed_effect()
    ss = sorted(eff)
    print(f"per-seed arm-D effect on {len(ss)} seeds "
          f"(negative = D better than A)\n")

    # ---- 1. input features ------------------------------------------------
    print("=" * 78)
    print("1. INPUT FEATURES -- do the two blocks differ before a pill is placed?")
    print("=" * 78)
    import reach_root as RR
    RR._lazy()
    feats = {s: seed_features(s) for s in ss}
    keys = [k for k in feats[ss[0]] if k != "lfsr_s0"]
    blkA = [s for s in ss if s <= 119]
    blkB = [s for s in ss if s > 119]
    print(f"{'feature':<26} {'0-119':>10} {'120-399':>10} {'diff':>9} {'perm p':>8}")
    n_sig = 0
    for k in keys:
        va = [feats[s][k] for s in blkA]
        vb = [feats[s][k] for s in blkB]
        obs = st.mean(va) - st.mean(vb)
        p = perm_p([feats[s][k] for s in ss], len(blkA), obs, reps=5000)
        flag = "  <-- differs" if p < 0.05 else ""
        n_sig += p < 0.05
        print(f"{k:<26} {st.mean(va):>10.3f} {st.mean(vb):>10.3f} "
              f"{obs:>+9.3f} {p:>8.4f}{flag}")
    print(f"\n  {n_sig} of {len(keys)} input features differ at p<0.05 "
          f"(expected by chance at this many tests: {0.05 * len(keys):.1f})")

    # ---- 2. shape: thirds -------------------------------------------------
    print("\n" + "=" * 78)
    print("2. SHAPE -- is 120-399 uniform, or is there a gradient?")
    print("=" * 78)
    thirds = [(120, 212), (213, 306), (307, 399)]
    print(f"{'block':<14} {'n':>4} {'mean effect':>13}  (negative = D better)")
    print(f"{'0-119':<14} {len(blkA):>4} {st.mean([eff[s] for s in blkA]):>13.4f}")
    for lo, hi in thirds:
        sub = [s for s in ss if lo <= s <= hi]
        print(f"{f'{lo}-{hi}':<14} {len(sub):>4} "
              f"{st.mean([eff[s] for s in sub]):>13.4f}")
    tvals = [st.mean([eff[s] for s in ss if lo <= s <= hi]) for lo, hi in thirds]
    print(f"\n  spread across the three thirds: "
          f"{max(tvals) - min(tvals):.4f}   "
          f"gap from 0-119 to the nearest third: "
          f"{min(abs(st.mean([eff[s] for s in blkA]) - t) for t in tvals):.4f}")

    # ---- 3. split-point scan ---------------------------------------------
    print("\n" + "=" * 78)
    print("3. SPLIT-POINT SCAN -- how much apparent block structure is there?")
    print("=" * 78)
    vals = [eff[s] for s in ss]
    scan = []
    for k in range(40, len(ss) - 40 + 1):
        obs = st.mean(vals[:k]) - st.mean(vals[k:])
        scan.append((k, obs))
    obs119 = st.mean(vals[:120]) - st.mean(vals[120:])
    # calibrate: null distribution of the MAXIMUM |split stat| over all k
    rng = random.Random(99)
    v = list(vals)
    maxima = []
    for _ in range(2000):
        rng.shuffle(v)
        maxima.append(max(abs(st.mean(v[:k]) - st.mean(v[k:]))
                          for k in range(40, len(v) - 40 + 1, 8)))
    p_scan = sum(1 for m in maxima if m >= abs(obs119)) / len(maxima)
    best_k, best_v = max(scan, key=lambda x: abs(x[1]))
    print(f"  split at 119 (pre-specified)   |stat| = {abs(obs119):.4f}")
    print(f"  largest split anywhere         |stat| = {abs(best_v):.4f} at k={best_k}")
    print(f"  P(max |split stat| over ALL k >= the k=119 value) under the null: "
          f"{p_scan:.3f}")
    print("    ^ this is the number that matters if the boundary had been CHOSEN.")
    print("      It was not -- it was handed to me -- so the pre-specified")
    print("      p=0.023 is the honest test and this is the sanity context.")

    # ---- 4. the one real structural boundary ------------------------------
    print("\n" + "=" * 78)
    print("4. STRUCTURAL SPLIT -- the LFSR high byte changes at seed 256")
    print("=" * 78)
    lo_s0 = [s for s in ss if s < 256]
    hi_s0 = [s for s in ss if s >= 256]
    obs, na, nb = block_delta(eff, lo_s0, hi_s0)
    p = perm_p(vals, len(lo_s0), obs)
    print(f"  seeds <256 (LFSR s0=0, n={na}) mean effect "
          f"{st.mean([eff[s] for s in lo_s0]):+.4f}")
    print(f"  seeds >=256 (LFSR s0=1, n={nb}) mean effect "
          f"{st.mean([eff[s] for s in hi_s0]):+.4f}")
    print(f"  difference {obs:+.4f}, permutation p={p:.4f}")
    print("    The seed->LFSR map is s0=(seed>>8)&0xFF, so 256 is the ONE")
    print("    boundary in this range that exists independently of my choices.")
    print("    My split is at 119, which does not align with it.")

    # ---- 5. does any input feature PREDICT the effect? --------------------
    print("\n" + "=" * 78)
    print("5. DIRECT PREDICTION -- does any input feature predict the effect?")
    print("=" * 78)
    print("   (the analysis that can actually find a mechanism; block membership")
    print("    only matters if something the block determines matters)")
    print(f"{'feature':<26} {'corr with effect':>18} {'perm p':>9}")
    n_pred = 0
    for k in keys:
        xs = [feats[s][k] for s in ss]
        if len(set(xs)) < 2:
            print(f"{k:<26} {'constant':>18} {'--':>9}")
            continue
        r = _corr(xs, vals)
        rng2 = random.Random(7)
        y = list(vals)
        hits = 0
        for _ in range(5000):
            rng2.shuffle(y)
            if abs(_corr(xs, y)) >= abs(r):
                hits += 1
        pp = hits / 5000
        n_pred += pp < 0.05
        print(f"{k:<26} {r:>+18.4f} {pp:>9.4f}"
              + ("  <-- predicts" if pp < 0.05 else ""))
    print(f"\n  {n_pred} of {len(keys)} features predict the per-seed effect "
          f"at p<0.05 (chance: {0.05 * len(keys):.1f})")
    return 0


def _corr(x, y):
    n = len(x)
    mx, my = st.mean(x), st.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = sum((a - mx) ** 2 for a in x) ** 0.5
    dy = sum((b - my) ** 2 for b in y) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0


if __name__ == "__main__":
    sys.exit(main())
