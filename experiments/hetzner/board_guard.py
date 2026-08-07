#!/usr/bin/env python3
"""board_guard.py -- assert a board contains no floating cells.

THE CLASS OF DEFECT THIS CLOSES. Writing a cell into a board does not make it
fall. `FaithfulBoard.resolve()` runs gravity ONLY after a clear:

    while True:
        mask = self._find_clears()
        if mask.sum() == 0: break     # <-- exits BEFORE any gravity
        ...; self._apply_gravity()

so anything written above its resting position and "settled" with `resolve()`
alone stays where it was put. For VS garbage that was fatal: `spawn_blocked()`
reads columns 3 and 4 of row 0, and one garbage column pair contains column 3,
so ~1 delivery in 3 topped the receiver out instantly (measured 19/60 on fresh
boards). This project has found and fixed that same bug at least three separate
times, in three files, and each time the other copies were left alone.

WHY THIS REUSES THE ENGINE'S OWN PHYSICS. The obvious check -- "every occupied
cell has something beneath it" -- is WRONG. A horizontal pill is rigid, so it
comes to rest when EITHER half is supported and the other half may legitimately
overhang a gap. Hand-rolling that rule is how a guard ends up rejecting legal
boards. Instead this asks the board the only question that matters, in its own
terms: **can any body still fall?** That is exactly `_apply_gravity`'s stopping
condition, so the guard cannot drift from the gravity it is guarding.

USE:
    from board_guard import assert_settled
    assert_settled(board, "after garbage delivery")

    # or non-fatally, e.g. auditing a fixture corpus
    bad = unsettled_bodies(board)

⚠ Do NOT call this inside `FaithfulBoard.resolve()` itself. Solo play never
inserts an unsupported cell and every solo result in the project depends on
resolve()'s current behaviour. This belongs at the WRITE sites and in harness
gates.
"""
from __future__ import annotations

import sys

_SRC = "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src"
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def unsettled_bodies(board):
    """Bodies that would still fall. Empty list == settled.

    A 'body' is the engine's own notion of a rigid group (a linked pill pair or
    a lone cell), and `_can_fall` is the engine's own test, so this agrees with
    `_apply_gravity` by construction rather than by reimplementation.
    """
    return [b for b in board._bodies() if board._can_fall(b)]


def is_settled(board):
    return not unsettled_bodies(board)


def describe(board, limit=6):
    bad = unsettled_bodies(board)
    if not bad:
        return "settled"
    parts = []
    for body in bad[:limit]:
        cells = ", ".join(f"r{r}c{c}(col={int(board.color[r, c])})" for r, c in body)
        parts.append("[" + cells + "]")
    more = f" (+{len(bad) - limit} more)" if len(bad) > limit else ""
    return f"{len(bad)} floating body/bodies: " + "; ".join(parts) + more


def assert_settled(board, where=""):
    """Raise if any body can still fall. `where` names the write site."""
    bad = unsettled_bodies(board)
    if bad:
        raise AssertionError(
            f"UNSETTLED BOARD{' at ' + where if where else ''}: {describe(board)}. "
            f"Whatever wrote these cells must call board._apply_gravity() itself "
            f"-- resolve() only runs gravity AFTER a clear.")
    return board


# ---------------------------------------------------------------- self-check
def _selftest():
    """Tests the DEFECT, not just the guard: build the exact failure the VS
    garbage bug produced and confirm the guard catches it, then confirm a
    legitimately-overhanging horizontal pill is NOT flagged (the false-positive
    a naive 'support beneath every cell' rule would produce)."""
    from drmario.faithful_game import FaithfulBoard, LINK_LEFT, LINK_RIGHT
    ok = True

    # 1. the real defect: a tile written into row 0 over empty space
    b = FaithfulBoard()
    b.color[0, 3] = 1
    caught = not is_settled(b)
    print(f"  [1] garbage floating at row 0 col 3 -> flagged: {caught}  "
          f"({describe(b)})")
    ok &= caught

    # 2. that same board after gravity -> settled
    b._apply_gravity()
    now = is_settled(b)
    print(f"  [2] after _apply_gravity()          -> settled: {now}")
    ok &= now

    # 3. FALSE-POSITIVE GUARD: a horizontal pill resting with one half over a
    #    gap is LEGAL. A naive per-cell rule would reject this.
    b2 = FaithfulBoard()
    b2.color[15, 0] = 1                      # a single support pillar on the floor
    b2.color[14, 0] = 2                      # pillar height 2
    b2.color[13, 0] = 2
    b2.color[13, 1] = 3                      # horizontal pair at r13, c0 is supported
    b2.link[13, 0] = LINK_RIGHT
    b2.link[13, 1] = LINK_LEFT
    legal = is_settled(b2)
    print(f"  [3] horizontal pill overhanging a gap -> settled (not a false "
          f"positive): {legal}")
    ok &= legal

    print(f"[board_guard] {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if _selftest() else 1)
