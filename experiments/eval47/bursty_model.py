#!/usr/bin/env python3
"""Bursty pressure model v1 -- human-style combo-timed garbage volleys, fit
from footage (phase "Bursty", task #47 follow-on).

Why this exists
----------------
pressure_rig.py's `_inject_garbage` is a uniform DRIP: 2 halves, every 8th
placement, once pills_placed>=25. That drip gets 94.2% clear vs. control
(PRESSURE_TAX_RESULTS.md) -- i.e. it does NOT reproduce the field disease,
where the AI (P2) dies ahead of a human (P1) despite being mechanically
faster. film_review_20260804/analysis/m1_verdict.md shows why: real human
pressure is NOT a drip. It arrives in discrete VOLLEYS -- 2-4 single-color
half-cells appearing simultaneously at the top of 2+ distinct, usually
non-adjacent columns, that fall in lockstep and settle -- and those volleys
cluster around the SENDER's own clears rather than firing on a fixed
placement cadence.

This module is a *fitter*, not a table of hardcoded constants. Call
`BurstyPressureModel.from_footage(...)` with a frames dir, a {side: grid}
dict, a {match_id: (t0, t1)} window map, and (optionally) per-side per-match
tracker CSVs, and it re-derives every number from those frames. It is
expected to be re-run tomorrow against a second capture set (dr_lulu
footage) with different paths/windows/grids and produce a *different* fitted
model from the same code -- see the __main__ block for the exact call used
to fit the v1 numbers reported against the 20260804 struktured set.

Determinism convention (matches pressure_rig.py exactly)
----------------------------------------------------------
Every stochastic decision in `sample()` / `inject_bursty_garbage()` seeds
from `random.Random(seed * 1000 + pills_placed)` -- the same convention as
pressure_rig._inject_garbage. No wall-clock, no global RNG, no hidden
mutable state carried between calls. Two calls with the same (seed,
pills_placed) always return the same thing.

Method (generalizes film_review_20260804/analysis/m1_verdict.md + its
scratch/m1_verdict/{build_ledger,analyze,volleys}.py from a single hardcoded
P1-in-m1 pass into a reusable, two-sided, four-match function)
------------------------------------------------------------------
1. build_ledger(): classify_cells() (vision.py) on every 1fps frame in a
   match window, for a given side's grid dict. -> per-second {colors,
   isvirus} 16x8 grids.
2. detect_flash_frames(): m1_verdict.md found one full-board rendering-flash
   frame (f0213: 0/128 cells occupied vs 41/27 neighbors) that must be
   excluded from diffs rather than counted as a 8-column "volley". Detected
   generically here as a near-empty frame sandwiched between two much fuller
   ones.
3. extract_volleys(): a real volley is a second where a PAIR of columns
   exactly `col_offset` apart (default NCOLS//2 -- the board splits into
   matching left/right quadrants) BOTH grow a new, non-virus top cell
   SIMULTANEOUSLY, landing in the SAME row. This is the exact geometric
   signature m1_verdict.md identified by eye ("two single-color half-cells
   appear in the same row simultaneously, in two columns exactly 4 apart...
   structurally impossible to produce from a single player capsule (max span
   = 1 adjacent column)"), turned into a closed-form filter instead of a
   per-event manual crop review.
     VALIDATION: this filter, run on the same P1/m1 ledger m1_verdict.md was
     built from, recovers the exact same 12 volley onset-seconds and column
     pairs the human-curated table reports (t=177/186/276/280/293/303/312/
     315/329/355/366/370, cols (0,4)/(1,5)/(2,6).../(3,7) matching row-for-
     row) -- 12/12 -- with a close total cell count (30 vs. the doc's
     hand-counted 26; the ~15% overcount is a couple of adjacent-cell
     classification edges, not a different set of events). An earlier
     "any >=2 columns grow a new top cell" version (no offset/same-row
     constraint) was tried first and produced 47 candidates up to 36 cells
     each on this same match -- it was catching mid-air FALLING PILLS
     sampled at 1fps (a still-unlocked piece's transient position, which
     vacates a cell once the piece moves past it, versus landed material
     which never vacates except via a clear) as well as coincidental
     same-second locks from different pills. The offset+same-row pairing is
     physically exclusive to a 2-source delivery (no single 2-cell capsule
     can span half the 8-column board) and was kept as the sole detector;
     the noisier adjacency-only version was NOT kept in this module.
     CAVEAT: because the pairing itself is what proves opponent-origin, this
     detector needs no per-pill lock CSV at all -- it runs identically on P1
     and P2 even though the 20260804 tracker (tracker.py) only ever logged
     P1 (there is no per-pill lock CSV for P2/the AI). `locks`/`tol` are
     still accepted and, when available, recorded on each event as an
     informational cross-check: `same_side_lock_nearby` lists any own-side
     pill locked within `tol`s that touches ONE of the paired columns (this
     is common and expected -- 6/12 of the m1/P1 validation volleys have a
     nearby lock -- because the player keeps playing while garbage lands;
     it is NOT disqualifying, since one capsule still can't touch BOTH
     mirrored columns 4 apart). It is NOT used to filter anything.
4. extract_clears(): a clear is a second where a side's occupied-cell count
   drops by >=4 (this task's stated threshold); bigger drops are labeled
   double/cascade by size, not separately re-classified.
5. from_footage() fits three things from the pooled event list:
     a. P(receiver gets a volley within k_seconds | opponent clear of size s)
        -- binned by clear size, per clear_size_bins.
     b. the empirical volley-size distribution (n_cells per volley).
     c. inter-volley gap distribution per (match, receiving-side) series.
   Every fitted number carries its n (see fit_summary()).

Small-n honesty
----------------
This is 4 matches. Expect low double-digit volley counts and clear counts
pooled across all 8 (side, match) series, and correspondingly WIDE bootstrap
CIs on anything binned further (e.g. per clear-size-bin firing probability).
fit_summary() reports n alongside every parameter and boot_ci() (bootstrap,
same style as pressure_rig.compare's own boot_ci) rather than a bare point
estimate. Treat v1 as directional, not load-bearing, until the dr_lulu
refit either confirms or moves these numbers.
"""
from __future__ import annotations

import os
import sys
import csv
import json
import random
import statistics as st
from collections import defaultdict
from dataclasses import dataclass, field

FILM_REVIEW_DIR_DEFAULT = "/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804"

NROWS = 16
NCOLS = 8

DEFAULT_OPPONENT_OF = {"P1": "P2", "P2": "P1"}


# --------------------------------------------------------------------------
# vision / ledger plumbing
# --------------------------------------------------------------------------

def _import_vision(film_review_dir):
    """Import the film-review vision.py module by path (it is not an
    installed package -- it lives alongside the frames it was calibrated
    against)."""
    if film_review_dir not in sys.path:
        sys.path.insert(0, film_review_dir)
    import vision  # noqa: E402  (deliberate late import, path-dependent)
    return vision


def build_ledger(frames_dir, grid, t0, t1, vision_mod, frame_pattern="f{:04d}.jpg"):
    """Classify every 1fps frame in [t0, t1] (inclusive) against `grid` (a
    vision.py grid dict: x0, y0, W, H). Missing frames are skipped (not
    zero-filled) so gaps show up as non-contiguous seconds downstream.

    Returns {t: {'colors': [16 x 8-char str, row-major], 'isvirus': [16x8
    bool]}}.
    """
    import numpy as np
    from PIL import Image

    ledger = {}
    for t in range(t0, t1 + 1):
        fp = os.path.join(frames_dir, frame_pattern.format(t))
        if not os.path.exists(fp):
            continue
        im = Image.open(fp).convert("RGB")
        arr = np.asarray(im)[..., :3].astype(int)
        colors, isvirus = vision_mod.classify_cells(arr, grid)
        ledger[t] = {
            "colors": ["".join(row) for row in colors],
            "isvirus": [[bool(x) for x in row] for row in isvirus],
        }
    return ledger


def _col_heights(colors):
    hs = []
    for c in range(NCOLS):
        top = NROWS
        for r in range(NROWS):
            if colors[r][c] != ".":
                top = r
                break
        hs.append(NROWS - top)
    return hs


def _occ_count(colors):
    return sum(1 for row in colors for ch in row if ch != ".")


def detect_flash_frames(ledger, ts, blank_thresh=5, recover_thresh=15):
    """A rendering-flash frame is a near-empty board sandwiched between two
    much fuller frames (m1_verdict.md: f0213 in m1, 0/128 cells vs 41/27 at
    its neighbors -- a screen-flash effect, not a real clear). Returns the
    set of t's to exclude from diffs on both sides."""
    flash = set()
    for i in range(1, len(ts) - 1):
        t = ts[i]
        occ = _occ_count(ledger[t]["colors"])
        occ_prev = _occ_count(ledger[ts[i - 1]]["colors"])
        occ_next = _occ_count(ledger[ts[i + 1]]["colors"])
        if occ <= blank_thresh and occ_prev >= recover_thresh and occ_next >= recover_thresh:
            flash.add(t)
    return flash


def load_locks(events_csv, window_start):
    """Parse a tracker.py-style per-pill CSV (m1.csv etc.) into lock events
    in absolute video-seconds. Convention (matches
    scratch/m1_verdict/analyze.py exactly): lock_t = window_start +
    lock_frame / 60.0.

    Returns [] if events_csv is None / doesn't exist (e.g. P2, which the
    20260804 tracker never logged) -- callers must treat that as "no
    lock-based cross-check available", not "zero pills happened".
    """
    locks = []
    if not events_csv or not os.path.exists(events_csv):
        return locks
    with open(events_csv) as f:
        for r in csv.DictReader(f):
            try:
                lock_frame = float(r["lock_frame"])
            except (KeyError, ValueError, TypeError):
                continue
            lock_t = window_start + lock_frame / 60.0
            fc = r.get("final_cells", "") or ""
            cells = []
            for part in fc.split("+"):
                part = part.strip().strip("()")
                if not part:
                    continue
                rr, cc = part.split(",")
                cells.append((int(rr), int(cc)))
            cols = sorted(set(c for (_rr, c) in cells))
            locks.append(dict(pill_id=r.get("pill_id"), lock_t=lock_t, cols=cols, cells=cells))
    return locks


def _locks_touching(locks, cols, t, tol):
    out = []
    for L in locks:
        if abs(L["lock_t"] - t) <= tol and set(L["cols"]) & set(cols):
            out.append(L)
    return out


# --------------------------------------------------------------------------
# event extraction (generalized from scratch/m1_verdict/{build_ledger,
# analyze,volleys}.py -- see module docstring step 3 for the validation that
# picked this exact filter over a noisier "any new top-of-column" candidate)
# --------------------------------------------------------------------------

def extract_volleys(ledger, col_offset=None, locks=None, tol=3.0):
    """Paired-column settled-cover volley detector.

    A volley is a second t1 where a column c and its mirror c+col_offset
    (default NCOLS//2) BOTH gain a new, non-virus top cell simultaneously,
    landing in the SAME row -- the signature m1_verdict.md identified by eye
    and confirmed structurally impossible from a single 2-cell capsule (see
    module docstring). Multiple independent pairs landing in the same second
    are merged into one event (cols = union, n_cells = sum).

    `locks`/`tol`, if supplied, are attached to each event as an
    informational cross-check only (`same_side_lock_nearby`) -- they do NOT
    filter anything here, because the pairing geometry alone already proves
    opponent-origin. Pass a side's tracker CSV via load_locks() if you want
    that annotation; omit it (default) and detection is unaffected -- this
    is what makes the detector work identically on P2, which the 20260804
    tracker never logged.

    Returns a list of dicts: t, cols, n_cells, col_offset, rows (the landing
    row per pair), same_side_lock_nearby (None if no locks supplied).
    """
    if col_offset is None:
        col_offset = NCOLS // 2
    ts = sorted(ledger.keys())
    flash = detect_flash_frames(ledger, ts)
    events = []
    for i in range(1, len(ts)):
        t0, t1 = ts[i - 1], ts[i]
        if t1 - t0 != 1:
            continue  # non-contiguous seconds (missing frame) -- no diff
        if t0 in flash or t1 in flash:
            continue
        c0, c1 = ledger[t0]["colors"], ledger[t1]["colors"]
        iv1 = ledger[t1]["isvirus"]
        h0, h1 = _col_heights(c0), _col_heights(c1)
        new_top = {}  # col -> (top0, top1)
        for c in range(NCOLS):
            top0 = NROWS - h0[c]
            top1 = NROWS - h1[c]
            if top1 < top0 and not iv1[top1][c]:
                new_top[c] = (top0, top1)
        used = set()
        pairs = []
        for c in sorted(new_top):
            c2 = c + col_offset
            if c in used or c2 in used or c2 not in new_top:
                continue
            if new_top[c][1] != new_top[c2][1]:
                continue  # must land in the same row to count as one volley
            pairs.append((c, c2, new_top[c][1]))
            used.add(c)
            used.add(c2)
        if not pairs:
            continue
        cols_here, rows_here, n_cells = [], [], 0
        for (c, c2, row) in pairs:
            for col in (c, c2):
                new_cells = sum(1 for r in range(NROWS) if c0[r][col] == "." and c1[r][col] != ".")
                n_cells += new_cells
                cols_here.append(col)
            rows_here.append(row)
        cols_here = sorted(cols_here)
        lock_note = None
        if locks:
            near = _locks_touching(locks, cols_here, t1, tol)
            lock_note = [L["pill_id"] for L in near] if near else []
        events.append(dict(t=t1, cols=cols_here, n_cells=n_cells, col_offset=col_offset,
                            rows=rows_here, same_side_lock_nearby=lock_note))
    return events


def extract_clears(ledger, min_cells=4):
    """Multi-cell removal events: occupied-cell count drops by >=min_cells
    second-over-second (task's stated threshold). Bigger drops are just
    reported with a larger cells_removed -- callers bin by size themselves.
    Excludes flash frames and non-contiguous second-gaps.

    Returns a list of dicts: t, cells_removed.
    """
    ts = sorted(ledger.keys())
    flash = detect_flash_frames(ledger, ts)
    events = []
    for i in range(1, len(ts)):
        t0, t1 = ts[i - 1], ts[i]
        if t1 - t0 != 1:
            continue
        if t0 in flash or t1 in flash:
            continue
        occ0 = _occ_count(ledger[t0]["colors"])
        occ1 = _occ_count(ledger[t1]["colors"])
        d = occ1 - occ0
        if d <= -min_cells:
            events.append(dict(t=t1, cells_removed=-d))
    return events


def extract_match_events(frames_dir, grids, window, events_csvs, vision_mod, tol=3.0,
                          min_clear_cells=4, col_offset=None):
    """Run volley+clear extraction for both sides of one match.

    grids:       {side: grid_dict}
    events_csvs: {side: path_or_None} -- used only as an informational
                 cross-check annotation on volley events (see
                 extract_volleys); a side with events_csvs[side] is None
                 (P2 in the 20260804 set) still gets full-strength volley
                 detection, just without that annotation.
    window:      (t0, t1) in frames_dir's own numbering.

    Returns dict(volleys=[...], clears=[...]); each event dict is tagged
    with 'side' (the side whose board received the volley / lost the cells).
    """
    t0, t1 = window
    all_volleys, all_clears = [], []
    for side, grid in grids.items():
        ledger = build_ledger(frames_dir, grid, t0, t1, vision_mod)
        ecsv = (events_csvs or {}).get(side)
        locks = load_locks(ecsv, t0) if ecsv else None
        vs = extract_volleys(ledger, col_offset=col_offset, locks=locks, tol=tol)
        for v in vs:
            v["side"] = side
            all_volleys.append(v)
        cs = extract_clears(ledger, min_cells=min_clear_cells)
        for c in cs:
            c["side"] = side
            all_clears.append(c)
    return dict(volleys=all_volleys, clears=all_clears)


# --------------------------------------------------------------------------
# bootstrap CI (same style as pressure_rig.boot_ci, kept independent so this
# module has no import dependency on pressure_rig)
# --------------------------------------------------------------------------

def boot_ci(xs, stat=st.mean, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = [stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n)]
    reps.sort()
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


# --------------------------------------------------------------------------
# the fitted model
# --------------------------------------------------------------------------

@dataclass
class BurstyPressureModel:
    volley_sizes: list          # pooled n_cells per volley (all sides/matches)
    gap_samples: list           # pooled inter-volley gaps, seconds, per (match,side) series
    p_within_k: dict            # {"lo-hi": {"p":..., "n":..., "hits":...}}
    k_seconds: float
    n_volleys: int
    n_clears: int
    n_matches: int
    opponent_of: dict = field(default_factory=lambda: dict(DEFAULT_OPPONENT_OF))
    meta: dict = field(default_factory=dict)

    # ---- fitting ----

    @classmethod
    def from_footage(cls, frames_dir, grids, match_windows, events_csvs=None,
                      vision_mod=None, film_review_dir=FILM_REVIEW_DIR_DEFAULT,
                      k_seconds=5.0, min_clear_cells=4, tol=3.0, col_offset=None,
                      clear_size_bins=((4, 6), (7, 10), (11, 999)),
                      opponent_of=None):
        """Fit a BurstyPressureModel from a footage set. Pure function of its
        arguments -- no hardcoded frame numbers or paths beyond the default
        `film_review_dir` used only to locate vision.py (grids/windows/CSVs
        are all caller-supplied).

        frames_dir:    dir of 1fps full-frame images (e.g. .../frames).
        grids:         {side: grid_dict} (vision.py-style x0/y0/W/H dicts).
                       Same dict is used for every match; pass per-match
                       overrides by calling from_footage per match and
                       merging with `combine()` if a capture set's grid
                       calibration drifts between matches.
        match_windows: {match_id: (t0, t1)}.
        events_csvs:   {match_id: {side: path_or_None}}. A side with no CSV
                       for a given match still gets FULL-STRENGTH volley
                       detection (the pairing geometry proves opponent-origin
                       on its own); the CSV only adds an informational
                       same_side_lock_nearby annotation.
        opponent_of:   {side: opposing_side}; defaults to the 2-player
                       P1<->P2 map.
        col_offset:    forwarded to extract_volleys (default NCOLS//2).

        Stores the raw per-match event lists in .meta['raw_events'] so a
        report can cite (t, side, match, cols) for every fitted number.
        """
        if vision_mod is None:
            vision_mod = _import_vision(film_review_dir)
        opponent_of = opponent_of or dict(DEFAULT_OPPONENT_OF)

        raw = {}
        all_volleys, all_clears = [], []
        for mid, window in match_windows.items():
            ecsv = (events_csvs or {}).get(mid, {})
            res = extract_match_events(frames_dir, grids, window, ecsv, vision_mod,
                                        tol=tol, min_clear_cells=min_clear_cells,
                                        col_offset=col_offset)
            for v in res["volleys"]:
                v["match"] = mid
            for c in res["clears"]:
                c["match"] = mid
            raw[mid] = res
            all_volleys.extend(res["volleys"])
            all_clears.extend(res["clears"])

        # --- P(receiver volley within k_seconds | sender clear of size s) ---
        p_within_k = {}
        for lo, hi in clear_size_bins:
            hit_bits = []
            for c in all_clears:
                if not (lo <= c["cells_removed"] <= hi):
                    continue
                recv = opponent_of.get(c["side"])
                mid = c["match"]
                t_clear = c["t"]
                hit = any(
                    v["match"] == mid and v["side"] == recv and t_clear <= v["t"] <= t_clear + k_seconds
                    for v in all_volleys
                )
                hit_bits.append(int(hit))
            tot, hits = len(hit_bits), sum(hit_bits)
            ci = boot_ci(hit_bits) if hit_bits else (float("nan"), float("nan"))
            p_within_k[f"{lo}-{hi}"] = dict(
                p=(hits / tot if tot else float("nan")), n=tot, hits=hits, ci95=ci
            )

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
            raw_events=raw,
            clear_size_bins=[list(b) for b in clear_size_bins],
            grids={side: dict(g) for side, g in grids.items()},
            match_windows=dict(match_windows),
            tol=tol,
            min_clear_cells=min_clear_cells,
        )
        return cls(
            volley_sizes=volley_sizes,
            gap_samples=gaps,
            p_within_k=p_within_k,
            k_seconds=k_seconds,
            n_volleys=len(all_volleys),
            n_clears=len(all_clears),
            n_matches=len(match_windows),
            opponent_of=opponent_of,
            meta=meta,
        )

    # ---- reporting ----

    def fit_summary(self):
        """Human-readable dict of every fitted parameter + its n, honest
        about small-n width (bootstrap CIs where a distribution exists)."""
        size_ci = boot_ci(self.volley_sizes) if self.volley_sizes else (float("nan"), float("nan"))
        gap_ci = boot_ci(self.gap_samples) if self.gap_samples else (float("nan"), float("nan"))
        size_hist = dict(sorted(
            ((s, self.volley_sizes.count(s)) for s in set(self.volley_sizes)),
            key=lambda kv: kv[0]
        ))
        volleys_by_match_side, clears_by_match_side = defaultdict(int), defaultdict(int)
        lock_annotated, lock_total = 0, 0
        for mid, res in self.meta.get("raw_events", {}).items():
            for v in res["volleys"]:
                volleys_by_match_side[f"{mid}/{v['side']}"] += 1
                lock_total += 1
                if v.get("same_side_lock_nearby") is not None:
                    lock_annotated += 1
            for c in res["clears"]:
                clears_by_match_side[f"{mid}/{c['side']}"] += 1
        return dict(
            n_matches=self.n_matches,
            n_volleys=self.n_volleys,
            n_clears=self.n_clears,
            volleys_by_match_side=dict(sorted(volleys_by_match_side.items())),
            clears_by_match_side=dict(sorted(clears_by_match_side.items())),
            volley_size_hist=size_hist,
            volley_size_mean=(st.mean(self.volley_sizes) if self.volley_sizes else float("nan")),
            volley_size_ci95=size_ci,
            inter_volley_gap_mean_s=(st.mean(self.gap_samples) if self.gap_samples else float("nan")),
            inter_volley_gap_ci95_s=gap_ci,
            inter_volley_gap_n=len(self.gap_samples),
            p_volley_within_k_by_clear_size=self.p_within_k,
            k_seconds=self.k_seconds,
            lock_crosscheck_annotated_of_total=f"{lock_annotated}/{lock_total}",
        )

    # ---- sampling / pressure_rig injection hook ----

    def fire_probability(self, clear_size):
        """P(a volley fires within k_seconds) given an opponent clear of
        `clear_size` cells, read off the fitted table. Falls back to the
        pooled rate across all bins if `clear_size` doesn't land in a fitted
        bin (or the exact bin has n=0)."""
        for key, d in self.p_within_k.items():
            lo, hi = (int(x) for x in key.split("-"))
            if lo <= clear_size <= hi and d["n"] > 0:
                return d["p"], d["n"]
        allb = [d for d in self.p_within_k.values() if d["n"]]
        if not allb:
            return 0.0, 0
        hits = sum(d["hits"] for d in allb)
        tot = sum(d["n"] for d in allb)
        return (hits / tot if tot else 0.0), tot

    def sample(self, seed, pills_placed):
        """Deterministic draw of (n_cells, columns) for a volley, given it
        fires. Matches pressure_rig's seeding convention exactly:
        random.Random(seed * 1000 + pills_placed) -- no wall-clock, no
        instance-level RNG state.

        v1 column model: draws n_cells from the empirical volley-size
        histogram, then n_cols = max(1, round(n_cells/2)) distinct random
        columns (the m1 data shows volleys are usually 2 cells across 2
        columns, occasionally 4 cells/2 columns double-height -- see
        fit_summary()['volley_size_hist']; n=12 volleys total in m1, this is
        NOT yet fit to a column-offset distribution because 12 events is too
        few to bin a second dimension -- flagged in fit_summary, to be
        revisited on the dr_lulu refit).

        Returns (n_cells, columns) or (0, []) if there's no fitted size pool
        to draw from.
        """
        rng = random.Random(seed * 1000 + pills_placed)
        if not self.volley_sizes:
            return 0, []
        n_cells = rng.choice(self.volley_sizes)
        n_cols = max(1, min(NCOLS, round(n_cells / 2)))
        cols = rng.sample(range(NCOLS), n_cols)
        return n_cells, cols

    def to_json(self, path):
        d = dict(
            volley_sizes=self.volley_sizes,
            gap_samples=self.gap_samples,
            p_within_k=self.p_within_k,
            k_seconds=self.k_seconds,
            n_volleys=self.n_volleys,
            n_clears=self.n_clears,
            n_matches=self.n_matches,
            opponent_of=self.opponent_of,
            meta={k: v for k, v in self.meta.items() if k != "raw_events"},
        )
        with open(path, "w") as f:
            json.dump(d, f, indent=2, default=str)


# --------------------------------------------------------------------------
# pressure_rig.py injection-hook wiring
# --------------------------------------------------------------------------

def inject_bursty_garbage(board, model, seed, pills_placed, opponent_clear_size, rng=None):
    """Drop-in replacement for pressure_rig._inject_garbage's decision step.

    Where the current rig fires unconditionally on a fixed period
    (pills_placed % GARBAGE_PERIOD == 0), call this once per placement,
    passing the SIMULATED OPPONENT's most recent clear size for that
    placement (0 if the opponent didn't clear this step) -- it decides
    whether a volley fires (model.fire_probability), and if so draws its
    size/columns (model.sample) and drops the halves exactly like
    pressure_rig._inject_garbage does (first-empty-row-from-top, random
    color 1..3, no link partner, gravity + resolve after).

    Determinism: `rng` defaults to random.Random(seed*1000+pills_placed),
    the same convention _inject_garbage and model.sample() use. Pass an
    explicit rng only if the caller needs to consume it for something else
    first and wants the draws to chain rather than restart.

    Returns the number of halves actually placed (0 if no volley fired, or
    every candidate column was already full to row 0).
    """
    from drmario.faithful_game import EMPTY, LINK_NONE

    rng = rng or random.Random(seed * 1000 + pills_placed)
    p_fire, _n = model.fire_probability(opponent_clear_size)
    if rng.random() >= p_fire:
        return 0
    n_cells, cols = model.sample(seed, pills_placed)
    if not cols:
        return 0
    rows_per_col = max(1, n_cells // max(1, len(cols)))
    placed = 0
    for c in cols:
        if board.color[0, c] != EMPTY:
            continue  # column full to the top -- skip silently (matches _inject_garbage)
        for _ in range(rows_per_col):
            r = 0
            while r < board.rows and board.color[r, c] != EMPTY:
                r += 1
            if r >= board.rows:
                break
            color = rng.randint(1, 3)
            board.color[r, c] = color
            board.is_virus[r, c] = False
            board.link[r, c] = LINK_NONE
            placed += 1
    if placed:
        board._apply_gravity()
        board.resolve()
    return placed


# --------------------------------------------------------------------------
# struktured 20260804 footage: the exact from_footage() call used to fit v1.
# Re-run this (or the equivalent with dr_lulu's paths/windows/grids) to
# refit -- nothing here is a hardcoded constant, it's the call, not the
# result, that's committed.
# --------------------------------------------------------------------------

def fit_struktured_20260804(film_review_dir=FILM_REVIEW_DIR_DEFAULT, **kw):
    vision_mod = _import_vision(film_review_dir)
    grids = {"P1": vision_mod.P1, "P2": vision_mod.P2}
    match_windows = {
        "m1": (120, 385),
        "m2": (798, 892),
        "m3": (953, 1122),
        "m4": (1163, 1492),
    }
    events_dir = os.path.join(film_review_dir, "events")
    events_csvs = {
        mid: {"P1": os.path.join(events_dir, f"{mid}.csv"), "P2": None}
        for mid in match_windows
    }
    frames_dir = os.path.join(film_review_dir, "frames")
    return BurstyPressureModel.from_footage(
        frames_dir, grids, match_windows, events_csvs=events_csvs,
        vision_mod=vision_mod, film_review_dir=film_review_dir, **kw
    )


if __name__ == "__main__":
    model = fit_struktured_20260804()
    print(json.dumps(model.fit_summary(), indent=2, default=str))
