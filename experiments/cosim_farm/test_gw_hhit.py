#!/usr/bin/env python3
"""Gate for #124: the co-sim farm's garbage-window field `h_hit`.

The field was wrong in three ways at once (game.py's play_game docstring has the
derivation). Per dr-mario-gate-standard-killed-mutants a gate for it has to do more
than confirm the new number -- it has to be shown FAILING on each wrong variant, and
it has to bind on the object that actually runs, not only on a helper.

★ THE THIRD DEFECT DECIDES THE SHAPE OF THIS GATE. Defect 3 is not "the fallback
fabricated a number when the hit set came up empty" -- that is the loud case. It is
that the hit set was INFERRED FROM THE BOARD at all, so it could come out NON-EMPTY
AND WRONG, never trip the fallback, and yield a plausible number silently. Hence
every implementation below is handed the volley's true column set alongside the four
board planes, so that the SOURCE of the hit set is itself a mutable axis. A mutant
suite that hands every variant the right columns cannot see defect 3 and would have
certified my own first fix, which was wrong.

TIER 1 -- six scenarios, each built to make one wrong implementation impossible:
            TOWER     hit columns of UNEQUAL height -- min != max, so the inversion
                      shows. The case flat synthetic stacks never had.
            FLAT      all hit columns equal, nothing clears -- all definitions
                      coincide, so the number must NOT move. This is the invariant
                      that proves the variable changed rather than the pipeline.
            BURIED    a cell appears inside a stack: occupancy grows, height does not.
            SETTLE    a column moves without gaining: an unhit column, not a hit.
            CLEARING  the binding column is hit and then CLEARS -- it grows in
                      neither height nor occupancy, so BOTH board inferences drop it
                      while leaving a non-empty set. The silent case.
            ALL_EATEN every hit column clears -- both inferences come up empty; the
                      shipped code fabricates max-over-all, and knowing the columns
                      means the true answer is still available.

TIER 2 -- the real play_game() capture site under a stub cosim and a stub volley
          model, asserting what Tier 1 structurally cannot: that the call site takes
          PRE-garbage heights, that its columns are the injector's own draw rather
          than a board difference, and that post_garbage is its own flag.

Run: python3 test_gw_hhit.py       (exit 0 = pass, 1 = fail)
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game as G                                        # noqa: E402

W_BASE, W_PER_H = 264, 16


def window(h):
    return W_BASE - W_PER_H * h


def board(heights, holes=()):
    """A colour plane with the given per-column stack heights.

    `holes` punches cells empty INSIDE a stack, which is how a board gets a cell that
    garbage can occupy without changing the height."""
    color = np.zeros((G.ROWS, G.COLS), dtype=np.uint8)
    for c, h in enumerate(heights):
        for r in range(G.ROWS - h, G.ROWS):
            color[r, c] = 1
    for c, r in holes:
        color[r, c] = 0
    return color


def drop_into(color, cols, n=1):
    """Land `n` garbage cells in each of `cols`, top-empty-cell first, as the injector
    does. Returns a NEW plane."""
    out = color.copy()
    for c in cols:
        for _ in range(n):
            r = 0
            while r < G.ROWS and out[r, c] != 0:
                r += 1
            if r >= G.ROWS:
                break
            out[r, c] = 2
    return out


# --------------------------------------------------------------------------------
# IMPLEMENTATIONS UNDER TEST
# Signature: (h_before, h_after, occ_before, occ_after, cols) -> h
# `cols` is the volley's TRUE column set. A variant that ignores it and re-derives
# the hit set from the planes is exercising defect 3.
# --------------------------------------------------------------------------------

def fixed(hb, ha, ob, oa, cols):
    """The shipped fix: min of PRE heights over the volley's OWN columns."""
    return G.garbage_hit_h(hb, cols)


def _occ_hits(ob, oa):
    return [c for c in range(G.COLS) if oa[c] > ob[c]]


def _height_hits(hb, ha):
    return [c for c in range(G.COLS) if ha[c] != hb[c]]


def m_max(hb, ha, ob, oa, cols):
    """DEFECT 1: max instead of min."""
    return max(hb[c] for c in cols) if cols else -1


def m_after(hb, ha, ob, oa, cols):
    """DEFECT 2: post-settle heights instead of pre-garbage."""
    return min(ha[c] for c in cols) if cols else -1


def m_height_hits(hb, ha, ob, oa, cols):
    """DEFECT 3a: hit set inferred from a HEIGHT change."""
    h = _height_hits(hb, ha)
    return min(hb[c] for c in h) if h else -1


def m_shipped(hb, ha, ob, oa, cols):
    """THE PRE-#124 CODE EXACTLY: height-delta hits, max aggregate, and the
    max-over-ALL-columns fallback when that set comes up empty."""
    h = _height_hits(hb, ha)
    return max(hb[c] for c in h) if h else max(ha)


def m_shipped_verbatim(hb, ha, ob, oa, cols):
    """game.garbage_hit_h_legacy -- the pre-#124 line COPIED FROM main, character for
    character, and now captured alongside the corrected value on every release (#136).

    ⚠ It is NOT the same function as m_shipped above. main's game.py:314-317 is

        hit = [h_after[c] for c in range(COLS) if h_after[c] != h_before[c]]
        pending_gh = max(hit) if hit else max(h_after)

    -- `hit` holds POST-SETTLE HEIGHTS, so the aggregate is over h_after, not h_before.
    m_shipped takes its max over `hb`, which drops defect 2 and therefore models a
    variant that never shipped. Both are legitimate mutants; only this one may be
    quoted as "what the old pilot measured"."""
    return G.garbage_hit_h_legacy(hb, ha)


def m_occ_hits(hb, ha, ob, oa, cols):
    """MY OWN FIRST FIX, which garbage-window-mech caught.

    Hits by occupancy growth repairs the over-inclusion half -- gravity can never ADD
    cells to a column -- but not the under-inclusion half. A column that is hit and
    then clears grows in neither occupancy nor height, so the binding column is
    dropped from a set that stays NON-EMPTY and therefore never trips any fallback.
    CLEARING exists to kill exactly this."""
    h = _occ_hits(ob, oa)
    return min(hb[c] for c in h) if h else -1


def m_first_col(hb, ha, ob, oa, cols):
    """Not a shipped defect -- a lazy 'just take one of them' variant."""
    return hb[cols[0]] if cols else -1


MUTANTS = [("m_max", m_max), ("m_after", m_after), ("m_height_hits", m_height_hits),
           ("m_shipped", m_shipped), ("m_shipped_verbatim", m_shipped_verbatim),
           ("m_occ_hits", m_occ_hits), ("m_first_col", m_first_col)]


# --------------------------------------------------------------------------------
# TIER 1
# --------------------------------------------------------------------------------

def cases():
    """(name, pre, post, cols, expected_h, note)."""
    out = []

    # TOWER: real near-death shape -- one tall hit column, one shallow, both hit.
    pre = board([2, 15, 4, 14, 13, 15, 3, 14])
    out.append(("TOWER", pre, drop_into(pre, [1, 6]), [1, 6], 3,
                "hit cols 1 (h=15) and 6 (h=3): the shallow one binds"))

    # TOWER_SPREAD: a ROM-shaped {c, c+4} volley on an uneven board.
    pre = board([9, 12, 11, 10, 1, 13, 12, 11])
    out.append(("TOWER_SPREAD", pre, drop_into(pre, [0, 4]), [0, 4], 1,
                "{c, c+4} finds the shallow column, as spread sets usually do"))

    # FLAT: the INVARIANT. Equal heights, nothing clears -- every definition of the
    # hit set and every aggregate coincide, so the number must not move at all.
    pre = board([7] * 8)
    out.append(("FLAT", pre, drop_into(pre, [2, 6]), [2, 6], 7,
                "equal heights, no clear: all definitions coincide, must NOT move"))

    # BURIED: a cell appears INSIDE col 3's stack. Occupancy grows, height does not,
    # so a height-keyed hit set misses it. Built by hand: drop_into always lands on
    # top, which is exactly why this case cannot come from the helper.
    pre = board([6, 11, 6, 6, 6, 6, 6, 6], holes=[(3, 12)])
    post = pre.copy()
    post[12, 3] = 2
    out.append(("BURIED", pre, post, [3], 6,
                "col 3 gains a cell at row 12, height stays 6: still a hit"))

    # SETTLE: a column changed height but gained no cells -- not a hit.
    pre = board([5, 12, 5, 5, 5, 5, 5, 5])
    post = drop_into(pre, [0])
    post[G.ROWS - 12:G.ROWS - 9, 1] = 0        # col 1 lost its top 3 to a clear
    out.append(("SETTLE", pre, post, [0], 5,
                "col 1 shrank without gaining: only col 0 (h=5) is a hit"))

    # CLEARING: THE SILENT CASE. The volley hits col 4 (h=1, the binding column) and
    # col 0 (h=9); col 4's landing completes a line and clears, so col 4 ends with
    # FEWER cells and a LOWER height than before. Both board inferences drop it and
    # keep col 0, leaving a NON-EMPTY set and a plausible h=9 -- 128 frames short,
    # with no fallback fired and nothing to notice.
    pre = board([9, 12, 11, 10, 1, 13, 12, 11])
    post = drop_into(pre, [0])
    post[G.ROWS - 1, 4] = 0                    # col 4: hit, then the line cleared
    out.append(("CLEARING", pre, post, [0, 4], 1,
                "col 4 is hit and clears: board inference drops the BINDING column"))

    # ALL_EATEN: every hit column clears. Both inferences come up empty; the shipped
    # code then fabricates max-over-all. Knowing the columns, the answer is still known.
    pre = board([8, 8, 3, 8, 8, 8, 8, 8])
    post = pre.copy()
    post[G.ROWS - 8:G.ROWS - 5, 1] = 0
    out.append(("ALL_EATEN", pre, post, [2, 1], 3,
                "hit set unrecoverable from the board; the volley still knows it"))
    return out


def tier1():
    ok = True
    print("TIER 1 -- garbage_hit_h() on built boards")
    rows = []
    for name, pre, post, cols, want, note in cases():
        hb, ha = G.col_heights(pre), G.col_heights(post)
        ob, oa = G.col_occupancy(pre), G.col_occupancy(post)
        got = fixed(hb, ha, ob, oa, cols)
        good = got == want
        ok &= good
        wtxt = "n/a" if want < 0 else f"{window(want)} f"
        print(f"  [{'PASS' if good else 'FAIL'}] {name:13s} h_hit={got:3d} "
              f"(want {want:3d}, W={wtxt})  -- {note}")
        rows.append((name, hb, ha, ob, oa, cols, want))

    # ---- DIVERGENCE + INVARIANT ------------------------------------------------
    print("\n  vs the SHIPPED implementation -- divergence where it must, and not "
          "where it must not:")
    diverged, agreed = [], []
    for name, hb, ha, ob, oa, cols, want in rows:
        old = m_shipped(hb, ha, ob, oa, cols)
        d = window(want) - window(old)
        (diverged if d else agreed).append(name)
        tag = "DIVERGES" if d else "agrees   "
        print(f"    {name:13s} fixed={want:2d} shipped={old:2d}  "
              f"W {window(old):3d} -> {window(want):3d} f  ({d:+4d} f)  {tag}")
    if not diverged:
        print("    !! NO CASE DIVERGES -- the corpus is vacuous for this fix")
        ok = False
    if "FLAT" not in agreed:
        print("    !! FLAT MOVED -- this is a pipeline perturbation, not a variable "
              "change")
        ok = False
    else:
        print("    invariant holds: FLAT (all definitions coincide) did not move")

    # ---- PAIRED LEGACY CAPTURE (#136) -------------------------------------------
    # The re-run logs garbage_hit_h_legacy beside the corrected h on every release, so
    # the size of the #124 correction becomes a WITHIN-RELEASE measurement instead of
    # a comparison across two files that must not be pooled.
    #
    # ⚠ This is deliberately NOT checked against the Tier-1 scenarios. Their `drop_into`
    # helper parks the garbage cell at ROW 0 (VS garbage floats before it settles), so
    # every hit column reads h_after = 16 there. The pre-#124 line ran on the board the
    # injector had already SETTLED, so a Tier-1 h_after is not the quantity it saw and
    # any divergence/invariant read off these boards would be about the fixture, not the
    # formula. Instead: hand-built SETTLED height pairs, checked against the pre-fix
    # expression transcribed independently from main's game.py:314-317.
    print("\n  paired legacy capture -- pre-#124 formula on SETTLED height pairs:")
    legacy_cases = [
        # (h_before, h_after, corrected_cols, want_legacy, want_corrected, note)
        ([2, 15, 4, 14, 13, 15, 3, 14], [2, 16, 4, 14, 13, 15, 4, 14], [1, 6], 16, 3,
         "uneven hits: legacy takes the MAX post-settle (16), correct takes min pre (3)"),
        ([7] * 8, [7, 7, 8, 7, 7, 7, 8, 7], [2, 6], 8, 7,
         "FLAT: legacy 8 vs correct 7 -- the +1 is defect 2 alone, all that is left"),
        ([9, 12, 11, 10, 1, 13, 12, 11], [10, 12, 11, 10, 0, 13, 12, 11], [0, 4], 10, 1,
         "CLEARING: col 4 hit then cleared; legacy keeps col 0 and misses the binding one"),
    ]
    for hb, ha, cols, want_leg, want_fix, note in legacy_cases:
        got_leg = G.garbage_hit_h_legacy(hb, ha)
        got_fix = G.garbage_hit_h(hb, cols)
        good = got_leg == want_leg and got_fix == want_fix
        ok &= good
        print(f"    [{'PASS' if good else 'FAIL'}] legacy={got_leg:3d} (want {want_leg}) "
              f"corrected={got_fix:3d} (want {want_fix})  "
              f"W {window(got_leg):3d} -> {window(got_fix):3d} f  -- {note}")
    # NOT-INERT is a property of the CORPUS, not of these three cases, so it is not
    # asserted here: it is registered as the population check on the real run
    # (median(h_legacy - h_corrected) >= 1 over live releases). A run where the two
    # agree everywhere would mean the volleys landed on flat stacks and the whole
    # re-capture said nothing -- which is a finding, and must not be silent.

    # ---- MUTANT KILL ------------------------------------------------------------
    print("\n  mutant kill sheet (a mutant must fail at least one case):")
    for mname, fn in MUTANTS:
        killed_by = []
        for name, hb, ha, ob, oa, cols, want in rows:
            try:
                got = fn(hb, ha, ob, oa, cols)
            except Exception as e:                       # noqa: BLE001
                got = f"raised {type(e).__name__}"
            if got != want:
                killed_by.append(name)
        status = "KILLED" if killed_by else "SURVIVED"
        ok &= bool(killed_by)
        print(f"    [{status}] {mname:14s} by {', '.join(killed_by) or '(nothing)'}")
    return ok


# --------------------------------------------------------------------------------
# TIER 2 -- the real capture site
# --------------------------------------------------------------------------------

class StubCosim:
    """Enough of Cosim for play_game: a legal drop, no tuck, a fixed clock cost.

    It drops into the SHALLOWEST column, which is not a strategy -- it just keeps the
    board alive long enough, and flat enough to clear, that volleys actually fire. A
    stub that stacks one column tops out in ~10 pills and the tier is vacuous."""
    fw_md5 = "stub" + "0" * 28

    def decide(self, b128, ca0, cb0, na0, nb0):
        a = np.asarray(b128, dtype=np.uint8).reshape(G.ROWS, G.COLS)
        h = [0] * G.COLS
        for c in range(G.COLS):
            for r in range(G.ROWS):
                if a[r, c] not in (0x00, 0xFF):
                    h[c] = G.ROWS - r
                    break
        return {"clocks": 1000, "col": int(np.argmin(h)), "o4": 0,
                "tcol": G.NO_TUCK, "trow": 0}


class SpreadModel:
    """A volley model that fires on every clear, into a column set that VARIES with
    pills_placed -- so a call site that re-samples with the wrong pills_placed, or
    caches one draw, diverges from the injector instead of coincidentally matching."""
    def fire_probability(self, clear_size):
        return (1.0, 1)

    def sample(self, seed, pills_placed):
        c = (seed + pills_placed) % 4
        return (2, [c, c + 4])


def tier2():
    print("\nTIER 2 -- the real play_game() capture site")
    import bursty_model

    SEEDS = (4242, 7, 99, 1337, 20260819)
    ok = True
    injections, calls = [], []
    orig_inject = bursty_model.inject_bursty_garbage
    orig_hh = G.garbage_hit_h
    orig_min_pills = G.GARBAGE_MIN_PILLS
    # The stub is a weak player and tops out before the production 25-pill floor, so
    # volleys would never fire and every assertion below would pass vacuously.
    # Lowering the floor changes WHEN garbage arrives, not how h_hit is computed.
    G.GARBAGE_MIN_PILLS = 0

    def spy_inject(board_, model_, seed_, pills_, clear_):
        pre_h = G.col_heights(board_.color)
        n = orig_inject(board_, model_, seed_, pills_, clear_)
        if n:
            # the injector's OWN draw, recorded at the moment it drew it
            injections.append((pre_h, list(model_.sample(seed_, pills_)[1])))
        return n

    def spy_hh(hb, cols):
        v = orig_hh(hb, cols)
        calls.append((list(hb), list(cols), v))
        return v

    bursty_model.inject_bursty_garbage = spy_inject
    G.garbage_hit_h = spy_hh
    lat = []
    try:
        for s in SEEDS:
            lat += G.play_game(StubCosim(), seed=s, level=11, max_pills=200,
                               pressure="bursty", model=SpreadModel())["lat"]
    finally:
        bursty_model.inject_bursty_garbage = orig_inject
        G.garbage_hit_h = orig_hh
        G.GARBAGE_MIN_PILLS = orig_min_pills

    pg_rows = [r for r in lat if r[3] == 1]
    print(f"  decisions={len(lat)}  injections={len(injections)}  "
          f"garbage_hit_h calls={len(calls)}  post_garbage rows={len(pg_rows)}")

    # NOT INERT: an arm that never injected would pass everything below vacuously.
    if not injections or not pg_rows:
        print("  [FAIL] no garbage injected / no post_garbage row -- gate vacuous")
        return False
    print(f"  [PASS] not inert: {len(injections)} injections, {len(pg_rows)} flagged")

    # (a) the call site's columns ARE the injector's own draw, and its heights are
    #     PRE-garbage. Kills m_after and any board-inferred column set at the site.
    bad_cols = [i for i, ((_ph, pc), (_hb, cc, _v)) in enumerate(zip(injections, calls))
                if sorted(cc) != sorted(pc)]
    bad_h = [i for i, ((ph, _pc), (hb, _cc, _v)) in enumerate(zip(injections, calls))
             if hb != ph]
    if bad_cols:
        print(f"  [FAIL] {len(bad_cols)} call(s) used columns != the injector's draw")
        ok = False
    else:
        print(f"  [PASS] all {len(calls)} calls used the injector's OWN column draw")
    if bad_h:
        print(f"  [FAIL] {len(bad_h)} call(s) used post-garbage heights")
        ok = False
    else:
        print(f"  [PASS] all {len(calls)} calls used PRE-garbage heights")

    # (b) the volley columns must actually VARY across injections, or a call site that
    #     cached a single draw would pass (a) by coincidence.
    distinct = {tuple(sorted(c)) for _h, c in injections}
    if len(distinct) < 2:
        print(f"  [FAIL] only {len(distinct)} distinct column set(s) -- (a) is weak")
        ok = False
    else:
        print(f"  [PASS] {len(distinct)} distinct column sets across injections")

    # (c) at least one live injection must hit columns of UNEQUAL height, or the run
    #     never exercised the case the bug is about.
    div = sum(1 for hb, cc, _v in calls
              if cc and min(hb[c] for c in cc) != max(hb[c] for c in cc))
    if div == 0:
        print("  [FAIL] no live injection hit columns of unequal height -- vacuous")
        ok = False
    else:
        print(f"  [PASS] {div}/{len(calls)} live injections had unequal hit heights")

    # (d) post_garbage is its OWN flag. Force h_hit to -1: if the flag were derived
    #     from it, every row would go unflagged.
    G.garbage_hit_h = lambda hb, cols: -1
    G.GARBAGE_MIN_PILLS = 0
    lat2 = []
    try:
        for s in SEEDS:
            lat2 += G.play_game(StubCosim(), seed=s, level=11, max_pills=200,
                                pressure="bursty", model=SpreadModel())["lat"]
    finally:
        G.garbage_hit_h = orig_hh
        G.GARBAGE_MIN_PILLS = orig_min_pills
    pg2 = [r for r in lat2 if r[3] == 1]
    if not pg2:
        print("  [FAIL] with h_hit forced to -1 nothing is flagged post_garbage "
              "-- the flag is derived from h_hit")
        ok = False
    else:
        print(f"  [PASS] post_garbage independent of h_hit: {len(pg2)} rows still "
              "flagged when h_hit is forced to -1")
        if any(r[4] != -1 for r in pg2):
            print("  [FAIL] forced h_hit did not reach the record")
            ok = False

    # (e) on a real run every post_garbage row must carry a REAL h. -1 now means "no
    #     column was targeted", which cannot happen when a volley fired -- so a -1
    #     here would mean the column set is not reaching the field.
    unknown = [r for r in pg_rows if r[4] < 0]
    if unknown:
        print(f"  [FAIL] {len(unknown)} post_garbage rows carry h_hit=-1")
        ok = False
    else:
        print(f"  [PASS] all {len(pg_rows)} post_garbage rows carry a real h_hit")
    return ok


def main():
    a = tier1()
    b = tier2()
    print(f"\n{'PASS' if (a and b) else 'FAIL'}: tier1={'ok' if a else 'FAILED'} "
          f"tier2={'ok' if b else 'FAILED'}")
    return 0 if (a and b) else 1


if __name__ == '__main__':
    sys.exit(main())
