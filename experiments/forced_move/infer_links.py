#!/usr/bin/env python3
"""Recover a LINK PLANE for a board transcribed from video.

WHY THIS IS NECESSARY. A still frame shows colours, not pairings, and a board
imported as all-unlinked-singles usually is not even STABLE: in the death_1321
position the red at (3,3) sits over an empty (4,3) and only stands because it is
still capsuled to the blue at (3,2), which in turn rests on an immovable virus
seven rows down. Import that board without links and gravity rearranges it on
the way in -- the harness reports `settle_moved=True` and the position you priced
is not the position you saw.

THE CONSTRAINT. Nothing on a settled board can fall, and FaithfulBoard gravity
moves rigid bodies (a single half, or a still-linked pair) only when EVERY cell
of the body has an empty cell beneath it. So a link assignment is admissible iff
every body it induces has at least one supported cell. That is a matching
problem on the pill cells, and it is usually not unique -- so this module
enumerates admissible assignments rather than returning one and calling it the
truth. A pricing that changes its verdict across the admissible set is a pricing
of the transcription, not of the move.
"""
from __future__ import annotations

ROWS, COLS = 16, 8
LINK_NONE, LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT = 0, 1, 2, 3, 4


def _supported(color, r, c):
    """True if (r,c) rests on something: the floor, or an occupied cell below."""
    return r == ROWS - 1 or color[r + 1][c] != 0


def admissible(color, is_virus, link):
    """Would this board be stable under FaithfulBoard gravity? (no body can fall)"""
    seen = [[False] * COLS for _ in range(ROWS)]
    delta = {LINK_UP: (-1, 0), LINK_DOWN: (1, 0), LINK_LEFT: (0, -1), LINK_RIGHT: (0, 1)}
    for r in range(ROWS):
        for c in range(COLS):
            if color[r][c] == 0 or is_virus[r][c] or seen[r][c]:
                continue
            lk = link[r][c]
            body = [(r, c)]
            if lk != LINK_NONE:
                dr, dc = delta[lk]
                body.append((r + dr, c + dc))
            for cell in body:
                seen[cell[0]][cell[1]] = True
            bs = set(body)
            # a body falls only if EVERY cell has an empty, non-body cell below
            if all(rr + 1 < ROWS and (rr + 1, cc) not in bs and color[rr + 1][cc] == 0
                   for rr, cc in body):
                return False
    return True


def enumerate_links(color, is_virus, limit=20000):
    """All admissible link planes, as flat 128-lists. May be large; capped.

    Only cells that NEED a partner drive the search -- a cell that is already
    supported can be a single, and pairing it changes nothing about stability,
    so pairing every such cell would blow the space up with assignments that are
    physically indistinguishable here. The enumeration therefore covers the
    STABILITY-RELEVANT links; cells left unlinked are the conservative choice
    (they fall alone after a clear, they never hold anything else up).
    """
    pill = [(r, c) for r in range(ROWS) for c in range(COLS)
            if color[r][c] != 0 and not is_virus[r][c]]
    pillset = set(pill)
    need = [p for p in pill if not _supported(color, *p)]

    link = [[LINK_NONE] * COLS for _ in range(ROWS)]
    used = set()
    out = []

    def partners(r, c):
        """Neighbours (r,c) could still be capsuled to, that would hold it up."""
        for dr, dc, lk, opp in ((0, -1, LINK_LEFT, LINK_RIGHT),
                                (0, 1, LINK_RIGHT, LINK_LEFT),
                                (1, 0, LINK_DOWN, LINK_UP)):
            # LINK_UP is never useful for the cell that needs support: its
            # partner would be ABOVE it and could not hold it up.
            pr, pc = r + dr, c + dc
            if (pr, pc) in pillset and (pr, pc) not in used:
                yield pr, pc, lk, opp

    def rec(i):
        if len(out) >= limit:
            return
        if i == len(need):
            if admissible(color, is_virus, [row[:] for row in link]):
                out.append([link[r][c] for r in range(ROWS) for c in range(COLS)])
            return
        r, c = need[i]
        if (r, c) in used:            # already paired by an earlier cell
            rec(i + 1)
            return
        for pr, pc, lk, opp in partners(r, c):
            link[r][c], link[pr][pc] = lk, opp
            used.add((r, c)); used.add((pr, pc))
            rec(i + 1)
            used.discard((r, c)); used.discard((pr, pc))
            link[r][c], link[pr][pc] = LINK_NONE, LINK_NONE
    rec(0)
    return out


def describe(color, is_virus):
    pill = [(r, c) for r in range(ROWS) for c in range(COLS)
            if color[r][c] != 0 and not is_virus[r][c]]
    need = [p for p in pill if not _supported(color, *p)]
    return {"pill_cells": len(pill), "unsupported_cells": need}
