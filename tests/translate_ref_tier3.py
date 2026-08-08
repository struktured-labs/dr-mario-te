#!/usr/bin/env python3
"""Python reference for TIER-3 CANDLIST translation (task #17, tier-3 mission,
2026-08-05): extends the tier-1 (target-1/target+1, first_occ-bounded) and tier-2
(target-1/target+1, unbounded trigger row) derivations to ANY approach column, at
most one lateral direction change -- the vocabulary translatable.py's tier_of()
calls tier 3.

DRIVER INVESTIGATION (this is what makes tier 3 possible at all): the real
executor (dr-mario-mods-wt/driver-nav/patch_cartridge_copro.py, mv_p2 at line
~1919) does NOT enforce target+/-1 anywhere. Its steering primitive is a plain
compare-and-hold: while row < TUCK_R2 (trigger), hold toward TUCK_C2 (approach);
once row >= trigger, hold toward TGT_C2 (target) instead. This is EXACTLY a
2-phase, at-most-one-direction-change motion, and it is already general over ALL
8 columns -- nothing in the driver restricts approach to be adjacent to target.
The target+/-1 restriction that tier 1/2 inherit is purely a property of
tuck_scan_v3's own enumerator (fpga/copro/tuck_v3.py, the TS_SIDE loop hardcoded
to {target-1, target+1}), not a driver limitation. So the CANDLIST FORMAT does not
change for tier 3 -- (target, approach, trigger, rest, orient) is already general
enough. Only the DERIVATION (which (approach, trigger) pairs are safe to publish)
needs to widen.

SAFETY, the axis tier 1/2 never actually checked: tier 1/2's geometric rule
(first_occ-bounded, or BFS-visited-bounded for tier 2) verifies column `approach`
is "empty enough" or "visited via SOME path", but never verifies the DRIVER'S OWN
SPECIFIC monotonic-hold-from-spawn can actually reach it -- this is a silent
approximation the existing tuck_scan_v3 already ships with (fine for adjacent
columns, where a 1-column slide is trivially achievable almost always, but
increasingly risky the farther `approach` is from spawn). Tier 3 makes this
explicit and REAL rather than implicit and assumed: phase 1 must be provably
reachable via a path using ONLY ONE lateral direction (plus free rotation, plus
gravity/down-propagation) from spawn -- `mono_reach()` below computes exactly
that, as a restricted variant of row_bfs_visited's own row-monotonic fixed point
(same algorithm, just with one of the two lateral edges disabled). Phase 2 (the
final entry into `target` and fall to `rest`) reuses tier 1/2's own geometric
derive_vert/derive_horiz acceptance test verbatim (same accepted approximation
already shipping there) -- tier 3 is not attempting to solve full frame-accurate
gravity timing (tuck_scan_v3's own module docstring already calls that
"deliberately NOT generalised... unmeasured territory"); it is closing the ONE
specific gap (phase-1 reachability) that widening the approach-column set to ALL
8 columns makes newly consequential.

VALIDATED COVERAGE (test_translate_tier3.py, 200-board real-L11 corpus, cascade =
tier1 [translate_ref.derive_verified, unchanged] then this module as fallback):
1456/1490 (97.7%) of translatable.py's tier_of()<=3 population gets a descriptor;
ZERO over-accepts (nothing tier_of() classifies as tier>3 is ever accepted --
the safety-critical direction). The 34 misses (2.3%, concentrated at tier_of()==2)
share ONE root cause, confirmed by hand on several: the real free-mode path
involves a ROTATION happening late, INTERLEAVED with or after the final lateral
move (e.g. the pill settles into its landing orientation via a second or third
rotation near the very end of the fall, sometimes with a kick that shifts its
column too) -- tier_of()'s own <=1-direction-change metric only counts Left/Right
reversals and is silent on WHEN rotation happens, so it can classify a candidate
as tier<=2 even when its actual path requires rotation timing this module's
2-phase-in-a-FIXED-final-orientation model cannot safely represent. This is a
real, structural limitation of the (approach, trigger) descriptor format itself,
not an implementation bug -- publishing a guessed descriptor for these would risk
exactly the "permissive direction" tuck_scan.py's own docstring warns is
dangerous, so they are correctly left untranslated (dropped, same as any other
CANDLIST miss) rather than force-matched. Coverage still more than DOUBLES the
currently-shipped tier-1-only baseline (668/1490 = 44.8%) at zero cost to safety.
"""
from __future__ import annotations

import translate_ref as TR

ROWS, COLS, EMPTY = TR.ROWS, TR.COLS, TR.EMPTY
_IS_H = TR._IS_H
occ, first_occ, is_legal = TR.occ, TR.first_occ, TR.is_legal

SPAWN_X, SPAWN_Y, SPAWN_O = 3, 0, 0


def mono_reach(board, direction):
    """Same row-wise fixed-point algorithm as translate_ref.row_bfs_visited, with
    ONE lateral edge disabled: direction='L' allows only x->x-1 (never x->x+1),
    direction='R' allows only x->x+1 (never x->x-1). Rotation and down-propagation
    are unrestricted (a "direction change" is a LATERAL reversal only -- matches
    translatable.py's _direction_changes, which also ignores rotate/down tokens).
    Returns the full visited[y][32] plane, same shape/indexing as row_bfs_visited."""
    assert direction in ("L", "R")
    visited = [[False] * 32 for _ in range(ROWS)]
    if not is_legal(board, SPAWN_X, SPAWN_Y, SPAWN_O):
        return visited
    visited[SPAWN_Y][SPAWN_X * 4 + SPAWN_O] = True
    for y in range(ROWS):
        row = visited[y]
        changed = True
        while changed:
            changed = False
            for s in range(32):
                if not row[s]:
                    continue
                x, o = s >> 2, s & 3
                if direction == "L" and x > 0 and is_legal(board, x - 1, y, o):
                    s2 = (x - 1) * 4 + o
                    if not row[s2]:
                        row[s2] = True
                        changed = True
                if direction == "R" and x < COLS - 1 and is_legal(board, x + 1, y, o):
                    s2 = (x + 1) * 4 + o
                    if not row[s2]:
                        row[s2] = True
                        changed = True
                for no in range(4):
                    if no == o:
                        continue
                    tx = x - 1 if (_IS_H[no] and x == COLS - 1) else x
                    if is_legal(board, tx, y, no):
                        s2 = tx * 4 + no
                        if not row[s2]:
                            row[s2] = True
                            changed = True
                    elif _IS_H[no] and tx >= 1 and is_legal(board, tx - 1, y, no):
                        s2 = (tx - 1) * 4 + no
                        if not row[s2]:
                            row[s2] = True
                            changed = True
        if y < ROWS - 1:
            for s in range(32):
                if not row[s]:
                    continue
                x, o = s >> 2, s & 3
                if is_legal(board, x, y + 1, o):
                    visited[y + 1][x * 4 + o] = True
    return visited


def _mono_test(plane, x, y, o):
    return plane[y][x * 4 + o]


def _phase2_ok(board, approach, target, rest, orient, r):
    """Same per-row acceptance test as translate_ref.derive_vert/derive_horiz
    (the tier 1/2 geometric rule, verbatim), just factored to take an arbitrary
    trigger row `r` and approach column directly rather than looping (a,r) itself
    -- the caller (derive_tier3) already found `r` via mono_reach and only needs
    this function to check phase 2 (enter target at row r, fall to rest)."""
    is_vert = orient in (1, 3)
    if is_vert:
        fc = first_occ(board, target)
    else:
        fc = min(first_occ(board, target), first_occ(board, target + 1))
    if fc == 0:
        return False
    sd = fc - 1
    if is_vert:
        if occ(board, r, target):
            return False
        if r - 1 < 0 or occ(board, r - 1, target):
            return False
        rf = r
        while rf + 1 < ROWS and not occ(board, rf + 1, target):
            rf += 1
    else:
        if occ(board, r, target) or occ(board, r, target + 1):
            return False
        rf = r
        while (rf + 1 < ROWS and not occ(board, rf + 1, target)
               and not occ(board, rf + 1, target + 1)):
            rf += 1
    return rf == rest and rf > sd


def derive_tier3(board, target, rest, orient, mono_L=None, mono_R=None):
    """(approach, trigger) for the TIER-3 vocabulary, or None. `mono_L`/`mono_R`:
    optional precomputed mono_reach(board,'L')/mono_reach(board,'R') planes (pass
    them in when translating many candidates on the same board -- same caching
    pattern as translate_ref's own `visited` parameter).

    Tries approach columns nearest-to-target-first (both directions interleaved)
    for a deterministic, tier-1/2-consistent tie-break -- prefers the SHORTEST
    phase-1 slide when multiple valid descriptors exist, same spirit as tier 1/2
    preferring target-1 before target+1 in ascending-row order."""
    if mono_L is None:
        mono_L = mono_reach(board, "L")
    if mono_R is None:
        mono_R = mono_reach(board, "R")

    is_vert = orient in (1, 3)
    max_a = COLS if is_vert else COLS - 1

    # candidate approach columns ordered by distance from target (nearest first,
    # d=0 i.e. approach==target FIRST): a 0-lateral-reversal path can still land a
    # pill somewhere other than target-adjacent via a ROTATION KICK mid-fall (the
    # kick is a same-row, free-rotation edge in mono_reach's own model, not a
    # lateral move) -- when the kick alone does the positioning, approach==target
    # is the right descriptor: TUCK_C2==TGT_C2 makes the tuck steering a no-op
    # relative to plain single-target steering, which is always safe to publish
    # (it can only ever behave identically to, never conflict with, ordinary
    # steering) and is what recovers these candidates instead of silently
    # dropping them for want of a "real" approach column.
    order = [target] if 0 <= target < max_a else []
    for d in range(1, COLS):
        for a in (target - d, target + d):
            if 0 <= a < max_a and a not in order:
                order.append(a)

    # Tested as mono_L OR mono_R per (a,r) -- NOT "try the expected-direction plane
    # first, fall back to the other" -- a column can be reached by either hold
    # direction depending on board shape (e.g. a detour), and this symmetric form
    # is what the 6502 port implements (one combined test per row, not a nested
    # per-plane retry), so keeping the two bit-exact means not adding an ordering
    # distinction here that doesn't exist over there.
    for a in order:
        for r in range(ROWS):
            if not (_mono_test(mono_L, a, r, orient) or _mono_test(mono_R, a, r, orient)):
                continue
            if _phase2_ok(board, a, target, rest, orient, r):
                return (a, r)
    return None


def derive_tier3_verified(board, target, rest, orient, visited, mono_L=None, mono_R=None):
    """derive_tier3 PLUS the same defensive cross-check translate_ref.derive_verified
    uses for tier 1/2: the (approach, trigger, orient) intermediate state must also
    be in the FULL (unconstrained) BFS-visited plane. For a genuinely monotonic
    phase-1 path this is automatically true (mono_reach's planes are subsets of the
    full visited plane by construction -- fewer edges allowed can only find a
    subset of what the full search finds) -- kept anyway as a second independent
    check in the same defense-in-depth spirit as tier 1/2, and because it's nearly
    free (the plane already exists)."""
    got = derive_tier3(board, target, rest, orient, mono_L, mono_R)
    if got is None:
        return None
    approach, trigger = got
    if not TR.visited_test(visited, approach, trigger, orient):
        return None
    return got
