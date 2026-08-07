#!/usr/bin/env python3
"""TREE-WIDE AUDIT: run the gravity gate against every real delivery path.

The lesson that produced this: the same defect lived in three modules under two
different names, one lane's fix was never propagated to the others, and
"lane X imports module Y" was not "lane X executes the defect". So this does not
grep for a call — it CALLS each delivery function on a fresh board and checks
whether the tiles end up supported.

Every path is exercised, not inspected. A path that cannot be exercised here is
reported as UNTESTED rather than silently counted as clean.
"""
from __future__ import annotations
import sys, traceback

HERE = "/home/struktured/projects/dr-mario-qa-wt/experiments/holepoker"
ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (HERE, "/home/struktured/projects/dr-mario-qa-wt/experiments",
          "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47",
          "/home/struktured/projects/dr-mario-qa-wt/experiments/adversary",
          ROOT + "/tmp/vs_aware", ROOT + "/tmp/champion", ROOT + "/tmp/combo_term",
          ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

from gravity_gate import assert_delivery_settles   # noqa: E402


def probe_vs_env(mod_name):
    mod = __import__(mod_name)
    m = mod.VsMatch(0, level=11, max_pills=300, nes_pills=True)

    def deliver(board):
        m.env[1].board = board
        m._drop_garbage(1, (1, 1))
    return deliver


def probe_vs_harness():
    import vs_harness
    return lambda board: vs_harness.drop_garbage(board, 2, (1, 2), 0)


def probe_pressure_rig():
    import pressure_rig
    return lambda board: pressure_rig._inject_garbage(board, 0, 0, k=2)


def probe_adversary_harness():
    import adversary_harness as AH
    fn = getattr(AH, "_inject_drip", None) or getattr(AH, "inject_drip", None)
    if fn is None:
        raise ImportError("no _inject_drip")
    return lambda board: fn(board, 0, 0, 2)


PATHS = [
    ("vs_env.VsMatch._drop_garbage", lambda: probe_vs_env("vs_env")),
    ("vs_env_exact.VsMatch._drop_garbage", lambda: probe_vs_env("vs_env_exact")),
    ("vs_harness.drop_garbage", probe_vs_harness),
    ("pressure_rig._inject_garbage", probe_pressure_rig),
    ("adversary_harness drip", probe_adversary_harness),
]


def main():
    print("=== TREE-WIDE GARBAGE-GRAVITY AUDIT (exercised, not inspected) ===")
    bad = untested = 0
    for name, make in PATHS:
        try:
            deliver = make()
        except Exception as e:
            untested += 1
            print(f"  {name:42s} UNTESTED ({type(e).__name__}: {e})")
            continue
        try:
            r = assert_delivery_settles(deliver, n_boards=12, raise_on_fail=False)
            status = "PASS" if r["pass"] else "**FAIL**"
            if not r["pass"]:
                bad += 1
            print(f"  {name:42s} {status}  floating={r['left_floating']}/12 "
                  f"blocked-empty={r['spawn_blocked_empty_board']}/12")
        except Exception:
            untested += 1
            print(f"  {name:42s} UNTESTED (raised during probe)")
            traceback.print_exc(limit=1)
    print(f"\n{bad} defective, {untested} untested, "
          f"{len(PATHS)-bad-untested} clean")
    print("UNTESTED is not CLEAN -- exercise it or state it as unknown.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
