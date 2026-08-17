"""temporal_accum.py — CAUSAL, LOCK-TIME ACCUMULATORS (owner spec, 2026-08-17).

WHY
---
The certified gap families are TEMPORAL: burial debt accrues over placements and
cascades build across them.  A static one-ply feature vector compresses that
history away, which is a plausible reason the earlier attempts stalled
(proto_cvd flipped 1 of 7 certified fixtures).  The rollout recovers history by
simulating FORWARD; a counter recovers it by remembering BACKWARD, at O(few
integers) per lock.

SILICON CONTRACT — every field here obeys all four, or it does not belong:
  1. SMALL INTEGER state.  No floats, no history buffers beyond a 10-slot ring.
  2. Updated at LOCK TIME ONLY, from the lock delta.  Never per frame.
  3. STRICTLY CAUSAL.  Nothing here may read a future capsule, a future garbage
     volley, or the game's outcome.  The update sees only boards already played.
  4. Candidate deltas are computable from the candidate's POST board plus the
     current state — which is exactly what a cart has after its own expander.

STRUCTURAL WARNING, and it drives how these are consumed
--------------------------------------------------------
The learnability design scores candidates by FEATURE DIFFERENCE, x_d - x_A.  Any
quantity that is candidate-INVARIANT (all the running state: burial totals, the
cascade window, staleness, drought counters) cancels EXACTLY to zero in that
difference and can contribute nothing.  So the state is exposed as EVENT-LEVEL
CONTEXT (undifferenced), and only the per-candidate DELTAS enter the differenced
block.  Getting this backwards would have produced a temporal-only arm that was
mathematically guaranteed to score 0.5 and would have read as "the owner's
hypothesis is refuted".
"""
from __future__ import annotations

from collections import deque

import numpy as np

WIN = 10            # ring-buffer depth for trend terms (10 locks)
ROWS, COLS = 16, 8
SEGMENTS = ((0, 2), (2, 4), (4, 6), (6, 8))     # 2-column regions

# Per-candidate deltas: these ARE differenced against the champion's board.
CAND_TEMPORAL_NAMES = [
    "tc_d_burial_total", "tc_d_burial_max", "tc_d_covered_cols",
    "tc_d_adj_v", "tc_d_adj_h",
    "tc_stale_touched_max", "tc_clears_virus", "tc_viruses_cleared"]

# Running state: candidate-invariant, so consumed as CONTEXT, never differenced.
STATE_TEMPORAL_NAMES = [
    "ts_burial_total", "ts_burial_max", "ts_covered_cols",
    "ts_adj_v_growth_win", "ts_adj_h_growth_win", "ts_maxh_trend_win",
    "ts_stale_max", "ts_stale_mean",
    "ts_pills_since_virus_clear", "ts_pills_since_any_clear", "ts_locks"]


# ------------------------------------------------------------------ kernels
def _grid(col):
    return np.asarray(col, dtype=np.int16).reshape(ROWS, COLS)


def covered_virus_cols(col, vir):
    """Per column: is there a virus with ANY occupied cell above it?

    'Burial' in this game is access denial — a virus you cannot reach with a
    matching half until the material above it clears.  The predicate is
    therefore 'virus strictly below the column's top occupied cell'.
    """
    c = _grid(col)
    v = _grid(vir) != 0
    occ = c != 0
    out = np.zeros(COLS, dtype=np.int64)
    for j in range(COLS):
        rows = np.flatnonzero(occ[:, j])
        if rows.size == 0:
            continue
        top = rows[0]
        if v[top + 1:, j].any():
            out[j] = 1
    return out


def adjacency(col):
    """Same-colour orthogonal adjacency counts (vertical, horizontal).

    Not a clear predicate — a PRESSURE proxy.  Growth in same-colour adjacency
    is material being staged into line-forming position, which is the thing a
    cascade is built out of.
    """
    c = _grid(col)
    occ = c != 0
    v = int(np.count_nonzero(occ[:-1, :] & occ[1:, :] & (c[:-1, :] == c[1:, :])))
    h = int(np.count_nonzero(occ[:, :-1] & occ[:, 1:] & (c[:, :-1] == c[:, 1:])))
    return v, h


def segment_sigs(col):
    """One integer per 2-column region; changes iff that region changed."""
    c = _grid(col)
    return tuple(int(c[:, a:b].tobytes().__hash__()) for a, b in SEGMENTS)


def touched_segments(pre_col, post_col):
    c0, c1 = _grid(pre_col), _grid(post_col)
    return [s for s, (a, b) in enumerate(SEGMENTS)
            if not np.array_equal(c0[:, a:b], c1[:, a:b])]


def max_height(col):
    occ = _grid(col) != 0
    rows = np.argmax(occ, axis=0)
    h = np.where(occ.any(axis=0), ROWS - rows, 0)
    return int(h.max())


# ------------------------------------------------------------------- state
class TemporalState:
    """Per-GAME accumulators.  `observe` is called once per ply, before the
    placement, and derives the previous lock's delta by differencing boards."""

    def __init__(self):
        self.burial_age = np.zeros(COLS, dtype=np.int64)
        self.stale = np.zeros(len(SEGMENTS), dtype=np.int64)
        self.pills_since_virus_clear = 0
        self.pills_since_any_clear = 0
        self.adj_v_hist = deque(maxlen=WIN)
        self.adj_h_hist = deque(maxlen=WIN)
        self.maxh_hist = deque(maxlen=WIN)
        self.locks = 0
        self._prev = None       # (sigs, adj_v, adj_h, maxh, nvir, occ)

    def observe(self, col, vir):
        """Fold in the lock that produced the CURRENT board."""
        cov = covered_virus_cols(col, vir)
        adj_v, adj_h = adjacency(col)
        mh = max_height(col)
        nvir = int(np.count_nonzero(_grid(vir)))
        occ = int(np.count_nonzero(_grid(col)))
        sigs = segment_sigs(col)

        if self._prev is not None:
            p_sigs, p_v, p_h, p_mh, p_nvir, p_occ = self._prev
            self.locks += 1
            # burial age: +1 while the column still hides a virus, 0 on uncover
            self.burial_age = np.where(cov > 0, self.burial_age + 1, 0)
            for s in range(len(SEGMENTS)):
                self.stale[s] = 0 if sigs[s] != p_sigs[s] else self.stale[s] + 1
            cleared_virus = nvir < p_nvir
            # a clear removes material; garbage only ADDS, so a drop in
            # occupancy is a sound clear witness even under injection
            cleared_any = cleared_virus or occ < p_occ
            self.pills_since_virus_clear = (
                0 if cleared_virus else self.pills_since_virus_clear + 1)
            self.pills_since_any_clear = (
                0 if cleared_any else self.pills_since_any_clear + 1)
            self.adj_v_hist.append(adj_v - p_v)
            self.adj_h_hist.append(adj_h - p_h)
            self.maxh_hist.append(mh - p_mh)
        else:
            # first ply: the board has no predecessor, so start every counter at
            # 0 rather than inventing a delta against an empty board
            self.burial_age = np.where(cov > 0, 1, 0)

        self._prev = (sigs, adj_v, adj_h, mh, nvir, occ)
        self._cur = {"cov": cov, "adj_v": adj_v, "adj_h": adj_h,
                     "nvir": nvir, "maxh": mh}

    def state_features(self):
        return {
            "ts_burial_total": int(self.burial_age.sum()),
            "ts_burial_max": int(self.burial_age.max()),
            "ts_covered_cols": int((self._cur["cov"] > 0).sum()),
            "ts_adj_v_growth_win": int(sum(self.adj_v_hist)),
            "ts_adj_h_growth_win": int(sum(self.adj_h_hist)),
            "ts_maxh_trend_win": int(sum(self.maxh_hist)),
            "ts_stale_max": int(self.stale.max()),
            "ts_stale_mean": float(self.stale.mean()),
            "ts_pills_since_virus_clear": int(self.pills_since_virus_clear),
            "ts_pills_since_any_clear": int(self.pills_since_any_clear),
            "ts_locks": int(self.locks)}

    def candidate_features(self, pre_col, post_col, post_vir):
        """What this placement would DO to the accumulators — one lock ahead.

        Deliberately excludes the garbage the injector may add afterwards: a
        cart evaluating a candidate does not know the volley yet, and a feature
        that peeked at it would not be causal.
        """
        cov_post = covered_virus_cols(post_col, post_vir)
        new_age = np.where(cov_post > 0, self.burial_age + 1, 0)
        adj_v, adj_h = adjacency(post_col)
        nvir_post = int(np.count_nonzero(_grid(post_vir)))
        touched = touched_segments(pre_col, post_col)
        return {
            "tc_d_burial_total": int(new_age.sum() - self.burial_age.sum()),
            "tc_d_burial_max": int(new_age.max() - self.burial_age.max()),
            "tc_d_covered_cols": int((cov_post > 0).sum()
                                     - (self._cur["cov"] > 0).sum()),
            "tc_d_adj_v": int(adj_v - self._cur["adj_v"]),
            "tc_d_adj_h": int(adj_h - self._cur["adj_h"]),
            # how stale is the region this placement disturbs?  High = the
            # placement is finally touching material nobody has moved in a while
            "tc_stale_touched_max": int(max((self.stale[s] for s in touched),
                                            default=0)),
            "tc_clears_virus": int(nvir_post < self._cur["nvir"]),
            "tc_viruses_cleared": int(self._cur["nvir"] - nvir_post)}


def selftest():
    """Assert the properties the silicon contract claims, rather than assume."""
    ok = True
    st = TemporalState()

    # an empty board buries nothing
    empty = np.zeros(128, dtype=np.int8)
    st.observe(empty, empty)
    s = st.state_features()
    ok &= s["ts_burial_total"] == 0 and s["ts_covered_cols"] == 0
    print(f"  empty board -> no burial: {s['ts_burial_total'] == 0}")

    # a virus with a pill on top is buried, and the age GROWS while it stays so
    col = np.zeros((ROWS, COLS), dtype=np.int8)
    vir = np.zeros((ROWS, COLS), dtype=np.int8)
    col[15, 0] = 1
    vir[15, 0] = 1
    col[14, 0] = 2
    st2 = TemporalState()
    ages = []
    for _ in range(4):
        st2.observe(col.ravel(), vir.ravel())
        ages.append(st2.state_features()["ts_burial_max"])
    grows = ages == [1, 2, 3, 4]
    print(f"  buried virus age grows 1,2,3,4: {grows} ({ages})")
    ok &= grows

    # uncovering resets it
    col[14, 0] = 0
    st2.observe(col.ravel(), vir.ravel())
    reset = st2.state_features()["ts_burial_max"] == 0
    print(f"  uncover resets age: {reset}")
    ok &= reset

    # adjacency counts a same-colour vertical pair once, and not a mixed pair
    c = np.zeros((ROWS, COLS), dtype=np.int8)
    c[15, 3] = 1
    c[14, 3] = 1
    v_, h_ = adjacency(c.ravel())
    ok &= (v_, h_) == (1, 0)
    print(f"  same-colour vertical pair -> (v,h)=(1,0): {(v_, h_) == (1, 0)}")
    c[14, 3] = 2
    v_, h_ = adjacency(c.ravel())
    ok &= (v_, h_) == (0, 0)
    print(f"  mixed-colour pair -> (0,0): {(v_, h_) == (0, 0)}")

    # staleness rises for untouched regions and resets for the touched one
    st3 = TemporalState()
    b = np.zeros((ROWS, COLS), dtype=np.int8)
    for _ in range(3):
        st3.observe(b.ravel(), np.zeros(128, dtype=np.int8))
    before = int(st3.stale.max())
    b[15, 7] = 1
    st3.observe(b.ravel(), np.zeros(128, dtype=np.int8))
    after = st3.stale.copy()
    good = after[3] == 0 and after[0] == before + 1
    print(f"  staleness resets touched seg, others +1: {good} ({list(after)})")
    ok &= good

    # a candidate that buries a virus must report a POSITIVE burial delta
    st4 = TemporalState()
    pre_c = np.zeros((ROWS, COLS), dtype=np.int8)
    pre_v = np.zeros((ROWS, COLS), dtype=np.int8)
    pre_c[15, 2] = 1
    pre_v[15, 2] = 1
    st4.observe(pre_c.ravel(), pre_v.ravel())
    post_c = pre_c.copy()
    post_c[14, 2] = 3
    d = st4.candidate_features(pre_c.ravel(), post_c.ravel(), pre_v.ravel())
    burying = d["tc_d_burial_total"] > 0
    print(f"  candidate that covers a virus -> d_burial>0: {burying} "
          f"({d['tc_d_burial_total']})")
    ok &= burying

    print("TEMPORAL SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if selftest() else 1)
