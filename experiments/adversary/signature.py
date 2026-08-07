#!/usr/bin/env python3
"""signature.py -- cheap, replay-free feature extraction for a seed's OPENING
board + early pill-color stream. Used by census tail characterization.

Deliberately does NOT run the champion decide path -- these features are
computable directly from env.reset() (virus placement, seeded by the same
16-bit `seed`) and a bare NesPillSource(seed) prefix, so pulling them for
thousands of seeds (a matched control group as well as the tail) is O(seeds)
cheap rather than O(seeds * full game search).
"""
from __future__ import annotations

import math
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import adversary_harness as AH


def opening_and_pills(seed, n_pills=20, level=None):
    """Returns dict(seed, opening_board (snapshot), pills_prefix ([(a,b),...]))
    pills_prefix[0] is exactly the pill play_seed's env.cur would be for this
    seed (NesPillSource default skip=1, first next_pill() call == cur)."""
    L = AH._lazy()
    FaithfulDrMarioEnv = L["FaithfulDrMarioEnv"]
    NesPillSource = L["NesPillSource"]
    lvl = AH.LEVEL if level is None else level
    env = FaithfulDrMarioEnv(level=lvl, seed=seed, max_pills=300)
    env.reset()
    opening_board = AH._snapshot(env.board)
    src = NesPillSource(seed=seed)
    pills = [src.next_pill() for _ in range(n_pills)]
    return {"seed": seed, "opening_board": opening_board, "pills_prefix": pills}


def _shannon_entropy(counts):
    total = sum(counts)
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            h -= p * math.log2(p)
    return h


def features_from_opening(rec, rows=16, cols=8):
    """Scalar features for one seed's opening board + pill prefix -- the
    comparable summary used for tail-vs-control characterization."""
    board = rec["opening_board"]
    vir = board["vir"]
    col = board["col"]
    pills = rec["pills_prefix"]

    # virus color histogram (colors 1..3)
    virus_colors = [col[i] for i in range(len(vir)) if vir[i]]
    vc_hist = [virus_colors.count(c) for c in (1, 2, 3)]
    n_virus = len(virus_colors)

    # how close to the spawn (cols 3,4, rows 0..) is the nearest virus?
    # row-major idx = r*8+c
    spawn_cols = (3, 4)
    min_row_near_spawn = rows  # "no virus near spawn" sentinel
    for i in range(len(vir)):
        if vir[i]:
            r, c = divmod(i, cols)
            if c in spawn_cols:
                min_row_near_spawn = min(min_row_near_spawn, r)

    # viruses in the top quarter of the board (rows 0..3) -- proximate danger
    n_virus_top4 = sum(1 for i in range(len(vir)) if vir[i] and (i // cols) < 4)

    # pill-prefix features: flatten to a color sequence (a then b per pill)
    color_seq = []
    for a, b in pills:
        color_seq.append(a)
        color_seq.append(b)
    seq_hist = [color_seq.count(c) for c in (1, 2, 3)]
    entropy = _shannon_entropy(seq_hist)

    n_mono = sum(1 for a, b in pills if a == b)  # single-color pills

    # longest run of the same color in the flattened sequence
    longest_run = 1 if color_seq else 0
    cur_run = 1
    for i in range(1, len(color_seq)):
        if color_seq[i] == color_seq[i - 1]:
            cur_run += 1
            longest_run = max(longest_run, cur_run)
        else:
            cur_run = 1

    n_distinct_first10 = len(set(color_seq[:20]))  # first 10 pills = 20 halves

    return {
        "seed": rec["seed"],
        "n_virus": n_virus,
        "virus_color_hist": vc_hist,
        "min_row_near_spawn": min_row_near_spawn,
        "n_virus_top4": n_virus_top4,
        "pill_color_hist_first20": seq_hist,
        "pill_color_entropy_first20": entropy,
        "n_mono_pills_first20": n_mono,
        "longest_color_run_first20": longest_run,
        "n_distinct_colors_first10pills": n_distinct_first10,
    }
