#!/usr/bin/env python3
"""Python reference for the CANDLIST translation step (task #17, next increment).

DERIVATION RULE for (approach, trigger) given a (target, rest, orient) that MY BFS has
ALREADY proven reachable: literally re-run tuck_scan_v3's own geometric rule (same fc/fa/
ra bounds, same row-ascending-then-side-order tie-break), restricted to just that one
(target, rest) query, so a match (when found) is BYTE-IDENTICAL to what tuck_scan_v3's own
enumerator would have emitted for that geometric candidate (validated separately, 0/257
mismatches over 300 boards).

REFINEMENT found necessary during investigation: tuck_scan_v3's own rule uses ONLY
first_occ(approach) as its depth bound for valid trigger rows -- it does NOT verify the
approach column is actually REACHABLE at that shallow row (only that it's *empty* down to
that depth). This is a real, pre-existing over-approximation in the shipped v1/v3 firmware:
found a concrete board where scan_v3 claims target=7,rest=5,approach=6,trigger=5 is valid,
but column 6 is only enterable by passing through column 5's wall, which doesn't open until
row 8 -- so a pill reaching column 6 at all is already past row 5, and there's no Up move to
get back. scan_v3's own module docstring already flags this class of limitation
("deliberately NOT generalised... going further would be unmeasured territory"), so this is
a known, accepted approximation in the existing model, not a regression this port introduces.

Because this translation only ever queries derive() for (target,rest,orient) triples MY BFS
independently proved reachable (not arbitrary geometry), the above bug class can't leak in
through the "is (target,rest) reachable" side. The DEFENSIVE addition here closes the other
side: after derive() finds a candidate (approach,trigger), verify the INTERMEDIATE entry
state (approach, trigger, orient) is ALSO in my BFS's own VISITED set (not just "empty") --
this reuses the exact bitplane the 6502 tuck_bfs routine already built (BFS_VIS is still
live after tuck_bfs returns; the real 6502 translation routine calls tb_vis_test directly,
no extra computation). If that check fails, the candidate has no *verified* simple
descriptor and is dropped from CANDLIST translation (not silently accepted).
"""
from __future__ import annotations

ROWS, COLS, EMPTY = 16, 8, 0xFF
_IS_H = (True, False, True, False)


def occ(board, r, c):
    return board[r * COLS + c] != EMPTY


def first_occ(board, c):
    for r in range(ROWS):
        if occ(board, r, c):
            return r
    return ROWS


def is_legal(board, x, y, o):
    if _IS_H[o]:
        if x > COLS - 2:
            return False
        return not occ(board, y, x) and not occ(board, y, x + 1)
    if occ(board, y, x):
        return False
    return y == 0 or not occ(board, y - 1, x)


def row_bfs_visited(board):
    """Same row-wise fixed-point algorithm as tuck_bfs_6502.py / proto_rowbfs.py --
    returns the FULL visited[y][s] plane (not just resting states), which is what the
    reachability cross-check needs."""
    visited = [[False] * 32 for _ in range(ROWS)]
    if not is_legal(board, 3, 0, 0):
        return visited
    visited[0][3 * 4 + 0] = True
    for y in range(ROWS):
        row = visited[y]
        changed = True
        while changed:
            changed = False
            for s in range(32):
                if not row[s]:
                    continue
                x, o = s >> 2, s & 3
                if x > 0 and is_legal(board, x - 1, y, o):
                    s2 = (x - 1) * 4 + o
                    if not row[s2]:
                        row[s2] = True
                        changed = True
                if x < COLS - 1 and is_legal(board, x + 1, y, o):
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


def visited_test(visited, x, y, o):
    return visited[y][x * 4 + o]


def derive_vert(board, target, rest, visited):
    fc = first_occ(board, target)
    if fc == 0:
        return None
    sd = fc - 1
    for a in (target - 1, target + 1):
        if not (0 <= a < COLS):
            continue
        fa = first_occ(board, a)
        if fa == 0:
            continue
        ra = fa - 1
        for r in range(fc, ra + 1):
            if occ(board, r, target):
                continue
            if r - 1 < 0 or occ(board, r - 1, target):
                continue
            rf = r
            while rf + 1 < ROWS and not occ(board, rf + 1, target):
                rf += 1
            if rf != rest:
                continue
            if rf <= sd:
                continue
            if rf - 1 < 0 or occ(board, rf - 1, target):
                continue
            return (a, r)
    return None


def derive_horiz(board, target, rest, visited):
    c = target
    fc = min(first_occ(board, c), first_occ(board, c + 1))
    if fc == 0:
        return None
    sd = fc - 1
    for a in (c - 1, c + 1):
        if a < 0 or a + 1 >= COLS:
            continue
        fa = min(first_occ(board, a), first_occ(board, a + 1))
        if fa == 0:
            continue
        ra = fa - 1
        for r in range(fc, ra + 1):
            if occ(board, r, c) or occ(board, r, c + 1):
                continue
            rf = r
            while rf + 1 < ROWS and not occ(board, rf + 1, c) and not occ(board, rf + 1, c + 1):
                rf += 1
            if rf != rest:
                continue
            if rf <= sd:
                continue
            return (a, r)
    return None


def derive_verified(board, target, rest, orient, visited):
    """derive_vert/derive_horiz PLUS the reachability cross-check on the found
    (approach, trigger, SAME orient) intermediate state."""
    is_vert = orient in (1, 3)
    got = derive_vert(board, target, rest, visited) if is_vert \
        else derive_horiz(board, target, rest, visited)
    if got is None:
        return None
    approach, trigger = got
    if not visited_test(visited, approach, trigger, orient):
        return None
    return got


def translate_candidates(board, bfs_candidates, capacity=14):
    """bfs_candidates: [(x, y, o, ca, cb), ...] in MY BFS's priority order (depth-
    descending, already how tuck_bfs_6502.py emits). Returns (candlist, dropped) where
    candlist is up to `capacity` (target, approach, trigger, rest, orient) tuples."""
    visited = row_bfs_visited(board)
    candlist = []
    dropped = 0
    for (x, y, o, ca, cb) in bfs_candidates:
        if len(candlist) >= capacity:
            dropped += 1
            continue
        got = derive_verified(board, x, y, o, visited)
        if got is None:
            dropped += 1
            continue
        approach, trigger = got
        candlist.append((x, approach, trigger, y, o))
    return candlist, dropped
