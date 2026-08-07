#!/usr/bin/env python3
"""REUSABLE GARBAGE-GRAVITY GATE — point it at YOUR delivery path.

Any lane that delivers garbage should run this against its own function rather
than trusting a module name. Tonight proved why: the same defect existed in
three modules under two different names (`VsMatch._drop_garbage` in `vs_env` and
`vs_env_exact`, guarded correctly in `vs_harness.drop_garbage`,
`adversary_harness._inject_drip` and `pressure_rig._inject_garbage`), and
"lane X imports module Y" turned out not to be "lane X executes the defect" —
`vs_harness` imports the defective `VsMatch` and never calls its garbage path.

THE DEFECT IT CATCHES
  `FaithfulBoard.resolve()` runs gravity ONLY after a clear step. A delivery
  that writes tiles into row 0 and then calls `resolve()` to "settle" them
  leaves them FLOATING when they complete no line. `spawn_blocked()` tests row 0
  of columns 3 and 4, so a floating tile in a spawn column is an INSTANT topout
  on any board, at any stack height, with a full set of legal moves.

USAGE

    from gravity_gate import assert_delivery_settles, tripwire

    # 1. does YOUR delivery leave tiles unsupported?
    assert_delivery_settles(lambda board: my_deliver(board, size=2))

    # 2. which code actually ran? make the suspect path fatal, then play.
    with tripwire(SomeClass, "_drop_garbage"):
        play_a_few_matches()          # raises if the defective path is reached

Both are DEFECT-FIRST: they try to catch the fault, not confirm the guard.
"""
from __future__ import annotations
import sys, contextlib

sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src")


def fresh_board(rows=16, cols=8, seed=0):
    import numpy as np
    from drmario.faithful_game import FaithfulBoard
    return FaithfulBoard(rows, cols, rng=np.random.default_rng(seed))


def floating_cells(board):
    """Cells with empty space directly beneath them and no linked partner
    holding them up — i.e. cells that gravity should have moved."""
    out = []
    R, C = board.rows, board.cols
    for r in range(R - 1):
        for c in range(C):
            if board.color[r, c] == 0 or board.is_virus[r, c]:
                continue
            if int(board.link[r, c]) != 0:      # part of a body; skip
                continue
            if board.color[r + 1, c] == 0:
                out.append((r, c))
    return out


def assert_delivery_settles(deliver, n_boards=20, raise_on_fail=True):
    """`deliver(board)` must leave NO unsupported single cell, and must not
    spawn-block an otherwise-empty board. Returns a dict; raises on failure
    unless raise_on_fail=False."""
    bad_float = bad_block = 0
    examples = []
    for i in range(n_boards):
        b = fresh_board(seed=i)
        deliver(b)
        fl = floating_cells(b)
        if fl:
            bad_float += 1
            if len(examples) < 3:
                examples.append(fl[:4])
        if b.spawn_blocked():
            bad_block += 1
    res = {"boards": n_boards, "left_floating": bad_float,
           "spawn_blocked_empty_board": bad_block, "examples": examples,
           "pass": bad_float == 0 and bad_block == 0}
    if raise_on_fail and not res["pass"]:
        raise AssertionError(
            f"GARBAGE GRAVITY DEFECT: {bad_float}/{n_boards} deliveries left "
            f"unsupported cells {examples}; {bad_block}/{n_boards} spawn-blocked "
            f"an EMPTY board. Call board._apply_gravity() before resolve().")
    return res


@contextlib.contextmanager
def tripwire(obj, attr, label=None):
    """Make a suspected code path FATAL for the duration, so a run proves which
    implementation it actually used. Answers 'which code ran?' by measurement
    instead of by import graph."""
    label = label or f"{getattr(obj, '__name__', obj)}.{attr}"
    orig = getattr(obj, attr)
    hits = {"n": 0}

    def _boom(*a, **k):
        hits["n"] += 1
        raise AssertionError(f"TRIPWIRE: {label} was called")

    setattr(obj, attr, _boom)
    try:
        yield hits
    finally:
        setattr(obj, attr, orig)


def _selftest():
    """Prove the gate catches the real defect and passes the real fix."""
    from drmario.faithful_game import LINK_NONE

    def broken(board):
        board.color[0, 3] = 1
        board.link[0, 3] = LINK_NONE
        board.is_virus[0, 3] = False
        board.resolve()

    def fixed(board):
        board.color[0, 3] = 1
        board.link[0, 3] = LINK_NONE
        board.is_virus[0, 3] = False
        board._apply_gravity()
        board.resolve()

    b = assert_delivery_settles(broken, n_boards=5, raise_on_fail=False)
    f = assert_delivery_settles(fixed, n_boards=5, raise_on_fail=False)
    print(f"  known-BROKEN delivery -> pass={b['pass']} "
          f"(floating {b['left_floating']}/5, blocked {b['spawn_blocked_empty_board']}/5)")
    print(f"  known-FIXED  delivery -> pass={f['pass']}")
    ok = (not b["pass"]) and f["pass"]
    print(f"  gate self-test: {'PASS -- it catches the defect and clears the fix' if ok else 'FAIL -- the gate itself is broken'}")
    return 0 if ok else 1


if __name__ == "__main__":
    print("=== gravity_gate self-test ===")
    sys.exit(_selftest())
