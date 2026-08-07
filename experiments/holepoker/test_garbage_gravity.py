#!/usr/bin/env python3
"""DEFECT PROOF: VS garbage tiles never fall, and that manufactures topouts.

`vs_env_exact.VsMatch._drop_garbage` writes two tiles into ROW 0 and then calls
`board.resolve()` with the comment "settle". But `FaithfulBoard.resolve()` is

    while True:
        mask = self._find_clears()
        if mask.sum() == 0: break        # <-- exits BEFORE any gravity
        ...
        self._apply_gravity()

so gravity runs ONLY after a clear. Freshly dropped garbage almost never
completes a line, so the loop breaks immediately and the tiles are left
FLOATING AT ROW 0 over whatever emptiness is beneath them.

WHY THAT IS FATAL, not cosmetic: `spawn_blocked()` is
`any(color[0, c] for c in (3, 4))`, and `GARBAGE_PAIRS = ((1,5),(2,6),(3,7))`
includes column 3. So one third of all garbage deliveries drop a tile into row 0
of column 3 and top the receiver out INSTANTLY — on any board, at any height,
with any number of legal moves available. The victim is not out-played; it is
hit by a tile that should have fallen 15 rows.

This tests the DEFECT (does an unsupported tile stay up?) and then the FIX
(one explicit `_apply_gravity()` before `resolve()`).
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src")
sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/experiments")
import numpy as np                                   # noqa: E402
from drmario.faithful_game import FaithfulBoard      # noqa: E402


def fresh():
    return FaithfulBoard(16, 8, rng=np.random.default_rng(0))


def test_a_tile_floats():
    b = fresh()
    b.color[0, 3] = 1
    b.link[0, 3] = 0
    b.is_virus[0, 3] = False
    b.resolve()
    floating = b.color[0, 3] != 0
    landed = b.color[15, 3] != 0
    print(f"  A empty board, one tile at row 0 col 3, after resolve():")
    print(f"      still at row 0 : {bool(floating)}   fell to row 15 : {bool(landed)}")
    print(f"      spawn_blocked(): {b.spawn_blocked()}  <-- topout on an EMPTY board")
    return not floating


def test_b_fix():
    b = fresh()
    b.color[0, 3] = 1
    b.link[0, 3] = 0
    b.is_virus[0, 3] = False
    b._apply_gravity()          # the one missing call
    b.resolve()
    landed = b.color[15, 3] != 0
    print(f"  B same, with an explicit _apply_gravity() first:")
    print(f"      fell to row 15 : {bool(landed)}   spawn_blocked(): {b.spawn_blocked()}")
    return bool(landed) and not b.spawn_blocked()


def test_c_rate():
    """How often does a delivery instantly top out a HEALTHY board?"""
    from vs_env_exact import VsMatch, GARBAGE_PAIRS
    n = trials = 0
    for seed in range(60):
        m = VsMatch(seed, level=11, max_pills=300, nes_pills=True)
        b = m.env[1].board
        if b.spawn_blocked():
            continue
        top3, top4 = b.top_occupied_row(3), b.top_occupied_row(4)
        m.pending[1].append((1, 1))
        m.deliver(1)
        trials += 1
        if b.spawn_blocked():
            n += 1
    print(f"  C one delivery onto a HEALTHY fresh board topped it out "
          f"{n}/{trials} times ({n/max(1,trials):.1%})")
    print(f"      GARBAGE_PAIRS={GARBAGE_PAIRS}; column 3 is in 1 of 3 pairs, "
          f"and columns 0 and 4 are immune")
    return n == 0


def main():
    print("=== A/B: raw FaithfulBoard.resolve() semantics (INFORMATIONAL) ===")
    print("    resolve() applies gravity ONLY after a clear. That is unchanged on")
    print("    purpose -- solo play never inserts an unsupported cell, and every")
    print("    solo result in this project depends on resolve()'s current")
    print("    behaviour. The rule it implies: anything that writes a cell NOT at")
    print("    its resting position must call _apply_gravity() itself.")
    a = test_a_tile_floats()
    b = test_b_fix()
    print(f"    raw resolve() settles unsupported cells: {a}   "
          f"explicit _apply_gravity() works: {b}")

    print("\n=== C: the VS harness must not manufacture topouts (MUST PASS) ===")
    c = test_c_rate()
    print()
    if c:
        print("PASS -- vs_env_exact._drop_garbage settles its tiles; a delivery no")
        print("        longer tops out a healthy board.")
        if not a:
            print("NOTE -- raw resolve() still leaves an unsupported cell floating.")
            print("        Any NEW code that writes cells directly (garbage, board")
            print("        injection, test fixtures) must call _apply_gravity().")
        return 0
    print("FAIL -- DEFECT PRESENT. Garbage tiles do not fall, so a delivery into")
    print("        column 3 tops the receiver out instantly regardless of board")
    print("        state. Every VS kill rate measured through this harness is")
    print("        contaminated by a ~1-in-3-per-delivery coin flip.")
    print(f"        The fix is one line ({b}): _apply_gravity() before resolve().")
    return 1


if __name__ == "__main__":
    sys.exit(main())
