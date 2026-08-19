#!/usr/bin/env python3
"""Gate for #124: the co-sim farm's garbage-window field `h_hit`.

The field was wrong in three ways at once (game.py's play_game docstring has the
derivation). A gate for it therefore has to do more than confirm the new number --
per dr-mario-gate-standard-killed-mutants it has to be shown FAILING on each wrong
variant, and it has to bind on the object that actually runs, not only on a helper.

TIER 1 -- garbage_hit_h() on hand-built boards, four of which are chosen so that a
          specific wrong implementation cannot survive them:
            TOWER   hit columns of UNEQUAL height -- min != max, so the inversion
                    shows. This is the case flat synthetic stacks never had.
            FLAT    all hit columns equal -- min == max, so a fix that merely
                    changed the number everywhere would be caught here instead.
            BURIED  garbage lands in a hole: occupancy grows, HEIGHT DOES NOT.
            SETTLE  a column's height moves without occupancy growth (gravity after
                    an unrelated clear) -- it is NOT a hit.
            EATEN   the volley cleared itself: no column grew -> -1, never a number.

TIER 2 -- the real play_game() capture site, driven by a stub cosim and a stub
          volley model, asserting what the unit test cannot: that the call site
          passes PRE-garbage heights, and that post_garbage is its own flag rather
          than `h_hit >= 0`.

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

    `holes` is a list of (col, row) cells punched empty INSIDE a stack, which is how
    a board gets a cell that garbage can fall into without changing the height.
    """
    color = np.zeros((G.ROWS, G.COLS), dtype=np.uint8)
    for c, h in enumerate(heights):
        for r in range(G.ROWS - h, G.ROWS):
            color[r, c] = 1
    for c, r in holes:
        color[r, c] = 0
    return color


def drop_into(color, cols, n=1):
    """Land `n` garbage cells in each of `cols`, top-empty-cell first, like the
    injector does. Returns a NEW plane."""
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
# MUTANTS -- each is a plausible wrong implementation, three of them the actual
# pre-#124 code. A mutant that survives every case means the cases are vacuous.
# --------------------------------------------------------------------------------

def m_max(h_before, occ_b, occ_a, h_after=None):
    """DEFECT 1 as shipped: max over hit columns."""
    hits = [c for c in range(G.COLS) if occ_a[c] > occ_b[c]]
    return max(h_before[c] for c in hits) if hits else -1


def m_after(h_before, occ_b, occ_a, h_after=None):
    """DEFECT 2 as shipped: post-settle heights instead of pre-garbage."""
    hits = [c for c in range(G.COLS) if occ_a[c] > occ_b[c]]
    return min(h_after[c] for c in hits) if hits else -1


def m_height_hits(h_before, occ_b, occ_a, h_after=None):
    """DEFECT 3a as shipped: hit set inferred from a HEIGHT change."""
    hits = [c for c in range(G.COLS) if h_after[c] != h_before[c]]
    return min(h_before[c] for c in hits) if hits else -1


def m_fallback(h_before, occ_b, occ_a, h_after=None):
    """DEFECT 3b as shipped: fabricate max() over ALL columns when hits is empty."""
    hits = [c for c in range(G.COLS) if occ_a[c] > occ_b[c]]
    return min(h_before[c] for c in hits) if hits else max(h_after)


def m_first_hit(h_before, occ_b, occ_a, h_after=None):
    """Not a shipped defect -- a lazy 'just take one of them' variant."""
    hits = [c for c in range(G.COLS) if occ_a[c] > occ_b[c]]
    return h_before[hits[0]] if hits else -1


MUTANTS = [("m_max", m_max), ("m_after", m_after), ("m_height_hits", m_height_hits),
           ("m_fallback", m_fallback), ("m_first_hit", m_first_hit)]


# --------------------------------------------------------------------------------
# TIER 1
# --------------------------------------------------------------------------------

def cases():
    """(name, pre_plane, post_plane, expected_h, note)."""
    out = []

    # TOWER: real near-death shape -- one tall column, one shallow, both hit.
    pre = board([2, 15, 4, 14, 13, 15, 3, 14])
    out.append(("TOWER", pre, drop_into(pre, [1, 6]), 3,
                "hit cols 1 (h=15) and 6 (h=3): the shallow one binds"))

    # TOWER_SPREAD: the ROM's own {c, c+4} volley on an uneven board.
    pre = board([9, 12, 11, 10, 1, 13, 12, 11])
    out.append(("TOWER_SPREAD", pre, drop_into(pre, [0, 4]), 1,
                "{c, c+4} finds the shallow column, as spread sets usually do"))

    # FLAT: min == max. A 'fix' that shifted every value would fail HERE.
    pre = board([7] * 8)
    out.append(("FLAT", pre, drop_into(pre, [2, 6]), 7,
                "equal hit heights: min and max agree, by construction"))

    # BURIED: a cell appears INSIDE col 3's stack (gravity/resolve after the volley
    # settled it into a hole). Occupancy grows, height does NOT -- so a hit set keyed
    # on height misses it entirely. Built by hand: drop_into() always lands on top,
    # which is exactly why this case cannot be produced by the helper.
    pre = board([6, 11, 6, 6, 6, 6, 6, 6], holes=[(3, 12)])
    post = pre.copy()
    post[12, 3] = 2
    out.append(("BURIED", pre, post, 6,
                "col 3 gains a cell at row 12, height stays 6: still a hit"))

    # SETTLE: a column changed height but gained no cells -- not a hit.
    pre = board([5, 12, 5, 5, 5, 5, 5, 5])
    post = drop_into(pre, [0])
    post[G.ROWS - 12:G.ROWS - 9, 1] = 0        # col 1 lost its top 3 cells to a clear
    out.append(("SETTLE", pre, post, 5,
                "col 1 shrank without gaining: only col 0 (h=5) is a hit"))

    # EATEN: nothing grew. The honest answer is 'unknown', not a number.
    pre = board([8, 8, 8, 8, 8, 8, 8, 8])
    post = pre.copy()
    post[G.ROWS - 8:G.ROWS - 5, 4] = 0
    out.append(("EATEN", pre, post, -1,
                "volley cleared itself: hit set unidentifiable -> -1"))
    return out


def tier1():
    ok = True
    print("TIER 1 -- garbage_hit_h() on built boards")
    rows, expected = [], {}
    for name, pre, post, want, note in cases():
        hb, ha = G.col_heights(pre), G.col_heights(post)
        ob, oa = G.col_occupancy(pre), G.col_occupancy(post)
        got = G.garbage_hit_h(hb, ob, oa)
        good = got == want
        ok &= good
        expected[name] = (hb, ha, ob, oa, want)
        wtxt = ("n/a" if want < 0 else f"{window(want)} f")
        print(f"  [{'PASS' if good else 'FAIL'}] {name:13s} h_hit={got:3d} "
              f"(want {want:3d}, W={wtxt})  -- {note}")
        rows.append((name, hb, ha, ob, oa, want))

    # ---- DIVERGENCE, stated as the quantity the bug actually distorted -----------
    print("\n  divergence from the shipped max() -- the thing #124 is about:")
    any_div = False
    for name, hb, ha, ob, oa, want in rows:
        mx = m_max(hb, ob, oa)
        if want < 0 or mx < 0:
            continue
        d = window(want) - window(mx)
        any_div |= d != 0
        tag = "DIVERGES" if d else "agrees   "
        print(f"    {name:13s} min={want:2d} max={mx:2d}  "
              f"W {window(mx):3d} -> {window(want):3d} f  ({d:+4d} f)  {tag}")
    if not any_div:
        print("    !! NO CASE DIVERGES -- the corpus is vacuous for this fix")
        ok = False

    # ---- MUTANT KILL ------------------------------------------------------------
    print("\n  mutant kill sheet (a mutant must fail at least one case):")
    for mname, fn in MUTANTS:
        killed_by = []
        for name, hb, ha, ob, oa, want in rows:
            try:
                got = fn(hb, ob, oa, ha)
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
    board alive long enough, and flat-ish enough to clear, that volleys actually fire.
    A stub that stacks one column tops out in ~10 pills and the tier is vacuous."""
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


class AlwaysFireModel:
    """A volley model that fires on every clear, into a fixed spread column set."""
    def __init__(self, cols=(0, 4)):
        self.cols = list(cols)

    def fire_probability(self, clear_size):
        return (1.0, 1)

    def sample(self, seed, pills_placed):
        return (len(self.cols), self.cols)


def tier2():
    """Drive play_game and check the two things Tier 1 structurally cannot."""
    import bursty_model

    print("\nTIER 2 -- the real play_game() capture site")
    ok = True

    SEEDS = (4242, 7, 99, 1337, 20260819)
    injections, calls = [], []
    orig_inject = bursty_model.inject_bursty_garbage
    orig_hh = G.garbage_hit_h
    orig_min_pills = G.GARBAGE_MIN_PILLS
    # The stub is a weak player and tops out well before the production 25-pill floor,
    # so volleys would never fire and every assertion below would pass vacuously.
    # Lowering the floor changes WHEN garbage arrives, not how h_hit is computed.
    G.GARBAGE_MIN_PILLS = 0

    def spy_inject(board_, *a, **k):
        pre = (G.col_heights(board_.color), G.col_occupancy(board_.color))
        n = orig_inject(board_, *a, **k)
        if n:
            injections.append((pre[0], pre[1],
                               G.col_occupancy(board_.color),
                               G.col_heights(board_.color)))
        return n

    def spy_hh(hb, ob, oa):
        v = orig_hh(hb, ob, oa)
        calls.append((list(hb), list(ob), list(oa), v))
        return v

    bursty_model.inject_bursty_garbage = spy_inject
    G.garbage_hit_h = spy_hh
    lat = []
    try:
        for s in SEEDS:
            lat += G.play_game(StubCosim(), seed=s, level=11, max_pills=200,
                               pressure="bursty", model=AlwaysFireModel())["lat"]
    finally:
        bursty_model.inject_bursty_garbage = orig_inject
        G.garbage_hit_h = orig_hh
        G.GARBAGE_MIN_PILLS = orig_min_pills

    pg_rows = [r for r in lat if r[3] == 1]
    print(f"  decisions={len(lat)}  injections={len(injections)}  "
          f"garbage_hit_h calls={len(calls)}  post_garbage rows={len(pg_rows)}")

    # NOT INERT: an arm that never injected would pass everything below vacuously.
    if not injections or not pg_rows:
        print("  [FAIL] no garbage was injected / no post_garbage row -- gate vacuous")
        return False
    print(f"  [PASS] not inert: {len(injections)} injections, {len(pg_rows)} flagged rows")

    # (a) the call site feeds PRE-garbage heights and the true before/after occupancy.
    #     This is what kills m_after at the site rather than only in the unit test.
    bad = [i for i, ((hb, ob, oa, _v), (phb, pob, poa, _pha))
           in enumerate(zip(calls, injections))
           if hb != phb or ob != pob or oa != poa]
    if bad:
        print(f"  [FAIL] call site passed the wrong planes at {len(bad)} injection(s)")
        ok = False
    else:
        print(f"  [PASS] all {len(calls)} calls got pre-garbage heights + true occupancy")

    # (b) at least one real injection must land on columns of UNEQUAL height, or the
    #     end-to-end run never exercised the case the bug is about.
    div = 0
    for hb, ob, oa, v in calls:
        hits = [c for c in range(G.COLS) if oa[c] > ob[c]]
        if hits and min(hb[c] for c in hits) != max(hb[c] for c in hits):
            div += 1
    if div == 0:
        print("  [FAIL] no live injection hit columns of unequal height -- vacuous")
        ok = False
    else:
        print(f"  [PASS] {div}/{len(calls)} live injections had unequal hit heights")

    # (c) post_garbage is its OWN flag. Force h_hit to -1 everywhere: if the flag were
    #     derived from it, every row would go unflagged.
    G.garbage_hit_h = lambda hb, ob, oa: -1
    G.GARBAGE_MIN_PILLS = 0
    lat2 = []
    try:
        for s in SEEDS:
            lat2 += G.play_game(StubCosim(), seed=s, level=11, max_pills=200,
                                pressure="bursty", model=AlwaysFireModel())["lat"]
    finally:
        G.garbage_hit_h = orig_hh
        G.GARBAGE_MIN_PILLS = orig_min_pills
    pg2 = [r for r in lat2 if r[3] == 1]
    if not pg2:
        print("  [FAIL] with h_hit forced to -1, no row is flagged post_garbage "
              "-- the flag is derived from h_hit")
        ok = False
    else:
        print(f"  [PASS] post_garbage independent of h_hit: {len(pg2)} rows still "
              "flagged when h_hit is forced to -1")
        if any(r[4] != -1 for r in pg2):
            print("  [FAIL] forced h_hit did not reach the record")
            ok = False
    return ok


def main():
    a = tier1()
    b = tier2()
    print(f"\n{'PASS' if (a and b) else 'FAIL'}: tier1={'ok' if a else 'FAILED'} "
          f"tier2={'ok' if b else 'FAILED'}")
    return 0 if (a and b) else 1


if __name__ == '__main__':
    sys.exit(main())
