#!/usr/bin/env python3
"""Fit a BurstyPressureModel from a footage source, with an EVENT-SIZE CAP
that bursty_model.py's from_footage() does not have.

Why this exists: fitting two new sources for the style ensemble (task:
"one player's fitted pressure model must never be the only exam") surfaced
a failure mode from_footage()'s raw extract_match_events() output doesn't
guard against -- board-wide scene changes (level transitions in a solo
"climb levels N-M" format, replay/highlight overlays, round-boundary scene
cuts) get misdetected as enormous single-second "clears"/"volleys" (40-70
cells) that no real Dr Mario match action produces. Real clears/volleys cap
out well under that (struktured's fitted volley_size_hist tops out at 6
cells; even a maximal cascade clear is a handful of cells, not dozens).

This wrapper filters both event lists to n_cells / cells_removed <= max_size
BEFORE computing the same p_within_k / volley_sizes / gap_samples math
from_footage() does internally, then constructs an equivalent
BurstyPressureModel by hand. bursty_model.py itself is left untouched --
this is a data-cleaning step for specific sources, not a fix to a bug in
the fitter (the fitter's job -- pooling clears/volleys into a P(volley|
clear size) table -- is correct; it was never asked to distinguish a real
clear from a scene cut, and shouldn't silently guess).
"""
from __future__ import annotations

import random
import statistics as st
from collections import defaultdict

import bursty_model as BM


def boot_ci(xs, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = [st.mean([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n)]
    reps.sort()
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def fit_filtered(frames_dir, grids, match_windows, max_size=20, events_csvs=None,
                  vision_mod=None, k_seconds=5.0, min_clear_cells=4, col_offset=None,
                  clear_size_bins=((4, 6), (7, 10), (11, 999)), opponent_of=None,
                  film_review_dir=None):
    opponent_of = opponent_of or dict(BM.DEFAULT_OPPONENT_OF)
    all_volleys, all_clears, dropped = [], [], {"volleys": 0, "clears": 0}
    for mid, window in match_windows.items():
        ecsv = (events_csvs or {}).get(mid, {})
        res = BM.extract_match_events(frames_dir, grids, window, ecsv, vision_mod,
                                       min_clear_cells=min_clear_cells, col_offset=col_offset)
        for v in res["volleys"]:
            v["match"] = mid
            if v["n_cells"] <= max_size:
                all_volleys.append(v)
            else:
                dropped["volleys"] += 1
        for c in res["clears"]:
            c["match"] = mid
            if c["cells_removed"] <= max_size:
                all_clears.append(c)
            else:
                dropped["clears"] += 1

    p_within_k = {}
    for lo, hi in clear_size_bins:
        hit_bits = []
        for c in all_clears:
            if not (lo <= c["cells_removed"] <= hi):
                continue
            recv = opponent_of.get(c["side"])
            mid = c["match"]
            t_clear = c["t"]
            hit = any(v["match"] == mid and v["side"] == recv and t_clear <= v["t"] <= t_clear + k_seconds
                      for v in all_volleys)
            hit_bits.append(int(hit))
        tot, hits = len(hit_bits), sum(hit_bits)
        ci = boot_ci(hit_bits) if hit_bits else (float("nan"), float("nan"))
        p_within_k[f"{lo}-{hi}"] = dict(p=(hits / tot if tot else float("nan")), n=tot, hits=hits, ci95=ci)

    volley_sizes = [v["n_cells"] for v in all_volleys]
    gaps = []
    by_series = defaultdict(list)
    for v in all_volleys:
        by_series[(v["match"], v["side"])].append(v["t"])
    for _key, ts_list in by_series.items():
        ts_list.sort()
        for a, b in zip(ts_list, ts_list[1:]):
            gaps.append(b - a)

    meta = dict(
        clear_size_bins=[list(b) for b in clear_size_bins],
        min_clear_cells=min_clear_cells,
        max_size_cap=max_size,
        dropped_as_scene_artifacts=dropped,
    )
    model = BM.BurstyPressureModel(
        volley_sizes=volley_sizes, gap_samples=gaps, p_within_k=p_within_k,
        k_seconds=k_seconds, n_volleys=len(all_volleys), n_clears=len(all_clears),
        n_matches=len(match_windows), opponent_of=opponent_of, meta=meta,
    )
    return model
