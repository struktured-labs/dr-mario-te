#!/usr/bin/env python3
"""Fit BurstyPressureModels from footage sources, with two capabilities
bursty_model.py's from_footage() does not have:

1. An EVENT-SIZE CAP (see fit_filtered docstring, unchanged from the first
   style-ensemble pass): filters out scene-artifact-sized "clears"/"volleys"
   (level transitions, replay overlays) before fitting.

2. PER-PLAYER (sender-conditioned) fitting (added for style-ensemble pass 3,
   per task direction): from_footage()/fit_filtered() build ONE model
   pooling BOTH sides' clears and BOTH sides' volleys together -- correct
   for "how does pressure flow in this match generally" but not for "how
   does player X specifically apply pressure," since a pooled fit can't
   separate X's clears from X's opponent's.

   Game-causal direction (per bursty_model.py's own tagging convention: a
   volley event's "side" field is the RECEIVING board, i.e. whose cells
   changed -- see extract_match_events' docstring): when side S clears,
   pressure lands on opponent_of[S]'s board. So player X's SENDING/pressure
   profile is:
     - clears  = events where side == X            (X's own clears)
     - volleys = events where side == opponent_of[X] (garbage that arrived
                 at X's opponent -- attributed to X's clears, since this
                 model has no other generative mechanism for a volley)
   X's RECEIVING context (garbage arriving at X's OWN board, i.e. clears
   where side == opponent_of[X] paired with volleys where side == X) is a
   different, separate quantity -- it characterizes X's opponent's sending
   style, not X's. Not computed here; per task direction, out of scope for
   a player's OWN pressure-style profile.

bursty_model.py itself is untouched by either capability -- both are
data-cleaning / re-aggregation on top of its (correct) primitives
(extract_match_events, BurstyPressureModel), not fixes to it.
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


def collect_events(frames_dir, grids, match_windows, max_size=20, events_csvs=None,
                    vision_mod=None, min_clear_cells=4, col_offset=None):
    """Run extract_match_events per window, tag each event with its match id,
    and filter out events above max_size (scene artifacts). Returns
    (all_volleys, all_clears, dropped_counts) -- the shared raw material for
    both fit_filtered() (pooled) and fit_per_player() (sender-conditioned)
    below, computed once so per-player fits don't re-run vision extraction."""
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
    return all_volleys, all_clears, dropped


def _build_model(all_volleys, all_clears, n_matches, k_seconds=5.0,
                  clear_size_bins=((4, 6), (7, 10), (11, 999)), opponent_of=None, meta_extra=None):
    """Shared p_within_k / volley_sizes / gap_samples aggregation, given
    already-filtered (and, for a per-player fit, already-direction-filtered)
    volley/clear lists. `opponent_of` is only used to look up the receiving
    side for each clear when computing hits -- for a per-player fit, callers
    pre-filter `all_volleys` to one side already, so this still works
    unchanged (the direction is baked into which events were passed in)."""
    opponent_of = opponent_of or dict(BM.DEFAULT_OPPONENT_OF)
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

    meta = dict(clear_size_bins=[list(b) for b in clear_size_bins], k_seconds=k_seconds)
    if meta_extra:
        meta.update(meta_extra)
    return BM.BurstyPressureModel(
        volley_sizes=volley_sizes, gap_samples=gaps, p_within_k=p_within_k,
        k_seconds=k_seconds, n_volleys=len(all_volleys), n_clears=len(all_clears),
        n_matches=n_matches, opponent_of=opponent_of, meta=meta,
    )


def fit_filtered(frames_dir, grids, match_windows, max_size=20, events_csvs=None,
                  vision_mod=None, k_seconds=5.0, min_clear_cells=4, col_offset=None,
                  clear_size_bins=((4, 6), (7, 10), (11, 999)), opponent_of=None,
                  film_review_dir=None):
    """POOLED fit (both sides' clears and volleys combined) -- unchanged
    behavior from style-ensemble pass 1/2. See fit_per_player() for the
    sender-conditioned per-player equivalent."""
    opponent_of = opponent_of or dict(BM.DEFAULT_OPPONENT_OF)
    all_volleys, all_clears, dropped = collect_events(
        frames_dir, grids, match_windows, max_size, events_csvs, vision_mod, min_clear_cells, col_offset)
    return _build_model(all_volleys, all_clears, len(match_windows), k_seconds, clear_size_bins,
                         opponent_of, meta_extra=dict(max_size_cap=max_size,
                                                       dropped_as_scene_artifacts=dropped,
                                                       min_clear_cells=min_clear_cells))


def fit_per_player(all_volleys, all_clears, n_matches, sender_side, opponent_of,
                    k_seconds=5.0, clear_size_bins=((4, 6), (7, 10), (11, 999))):
    """Player `sender_side`'s SENDING/pressure profile: clears where
    side==sender_side, volleys where side==opponent_of[sender_side] (garbage
    that arrived at the opponent, attributed to sender_side's clears -- see
    module docstring for why). Takes already-collected (collect_events())
    event lists so a match's two per-player fits share one extraction pass."""
    recv_side = opponent_of[sender_side]
    volleys = [v for v in all_volleys if v["side"] == recv_side]
    clears = [c for c in all_clears if c["side"] == sender_side]
    return _build_model(volleys, clears, n_matches, k_seconds, clear_size_bins, opponent_of,
                         meta_extra=dict(sender_side=sender_side, receiving_side=recv_side,
                                          profile_kind="sending"))
