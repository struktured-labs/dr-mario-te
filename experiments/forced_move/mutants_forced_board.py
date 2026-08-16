#!/usr/bin/env python3
"""KILLED-MUTANT SHEET for the forced-move gate.

A gate that passes is worth nothing until it is shown to FAIL on inputs that are
wrong in the specific ways this harness can be wrong. Each mutant below breaks
one mechanism and must be KILLED (gate exits non-zero).

Mutants are applied by MONKEYPATCHING the imported module in this process. No
file is edited and nothing is restored from git -- see
`mutation-harness-git-checkout-destroys-work`: `git checkout --` during a
mutation run deletes uncommitted instrumentation and manufactures a fake kill
sheet.

  M1 WRONG CONTINUATION  -- pill source wound to 0 instead of the reference's
     cursor. This is the `dr-mario-deepcopy-pill-closure` failure mode in its
     observable form: plausible boards, deterministic, wrong capsules. MATCH
     must die.
  M2 FORCED MOVE IGNORED -- move 1 comes from the decider instead of
     `forced_action`. MATCH still passes (the decider picks the reference's own
     action); only the CONTROL can catch this, which is why the control exists.
  M3 LINK PLANE DROPPED  -- every non-virus cell imported as an unlinked single.
     This is the exact fidelity concession a video-transcribed board forces, so
     the mutant doubles as its MEASUREMENT: whether it is killed says whether
     the missing link plane can change a trajectory at this horizon.
  M4 VIRUS PLANE NOT COPIED -- viruses left as whatever reset() generated.
     A crude positive control: if this is not killed, nothing is being compared.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import forced_board as FBM        # noqa: E402
import gate_forced_board as GATE  # noqa: E402

SEEDS = [2, 3, 4]
PLIES = [20, 35]
HORIZON = 15

_ORIG_ENV_FROM_SNAP = GATE._env_from_snapshot
_ORIG_MAKE_ENV = FBM.make_env
_ORIG_ROLLOUT = FBM.rollout


def _restore():
    GATE._env_from_snapshot = _ORIG_ENV_FROM_SNAP
    FBM.make_env = _ORIG_MAKE_ENV
    FBM.rollout = _ORIG_ROLLOUT


# ------------------------------------------------------------------- mutants

def m1_wrong_continuation():
    def patched(s, seed, level, max_pills, cur=None, nxt=None):
        s2 = dict(s, src_i=0)     # capsules from the top of the buffer, not the cursor
        return _ORIG_ENV_FROM_SNAP(s2, seed, level, max_pills, cur, nxt)
    GATE._env_from_snapshot = patched


def m2_forced_ignored():
    def patched(env, decider, horizon, forced_action=None, record=True):
        return _ORIG_ROLLOUT(env, decider, horizon, forced_action=None, record=record)
    FBM.rollout = patched


def m3_links_dropped():
    def patched(planes, *a, **kw):
        import numpy as np
        color, is_virus, link = planes
        return _ORIG_MAKE_ENV((color, is_virus, np.zeros_like(link)), *a, **kw)
    FBM.make_env = patched


def m4_virus_plane_not_copied():
    def patched(planes, *a, **kw):
        color, is_virus, link = planes
        env, src, meta = _ORIG_MAKE_ENV(planes, *a, **kw)
        env.board.is_virus[:] = False     # every virus becomes ordinary junk
        env._start_viruses = 0
        return env, src, meta
    FBM.make_env = patched


MUTANTS = [
    ("M1 wrong continuation (src_i -> 0)", m1_wrong_continuation, "MATCH"),
    ("M2 forced move ignored", m2_forced_ignored, "CONTROL"),
    ("M3 link plane dropped", m3_links_dropped, "MATCH"),
    ("M4 virus plane not copied", m4_virus_plane_not_copied, "MATCH"),
]


def main():
    print(f"=== forced-move KILLED-MUTANT SHEET  seeds={SEEDS} plies={PLIES} "
          f"H={HORIZON} ===\n", flush=True)

    print("BASELINE (unmutated harness) -- must PASS:", flush=True)
    ok, rows = GATE.run_gate(SEEDS, HORIZON, PLIES, verbose=False)
    n = len(rows)
    print(f"  {sum(r['match_ok'] for r in rows)}/{n} MATCH, "
          f"{sum(bool(r['control_ok']) for r in rows)}/{n} CONTROL -> "
          f"{'PASS' if ok else 'FAIL'}\n", flush=True)
    if not ok:
        print("BASELINE FAILED -- the sheet is meaningless. Stop.")
        return 1

    results = []
    for name, apply_mut, arm in MUTANTS:
        _restore()
        apply_mut()
        try:
            mok, mrows = GATE.run_gate(SEEDS, HORIZON, PLIES, verbose=False)
        finally:
            _restore()
        nm = sum(r["match_ok"] for r in mrows)
        nc = sum(bool(r["control_ok"]) for r in mrows)
        killed = not mok
        results.append((name, arm, killed, nm, nc, len(mrows)))
        print(f"  {name:38s} -> {'KILLED' if killed else 'SURVIVED':8s} "
              f"(MATCH {nm}/{len(mrows)}, CONTROL {nc}/{len(mrows)}; "
              f"expected to die on {arm})", flush=True)

    all_killed = all(r[2] for r in results)
    print(f"\n  mutants killed : {sum(r[2] for r in results)}/{len(results)}")
    print(f"\nSHEET {'PASS' if all_killed else 'FAIL'}"
          + ("" if all_killed else "  <- a surviving mutant means the gate is blind to it"))

    print("\nBASELINE RE-RUN (proves the mutants left nothing behind):", flush=True)
    ok2, rows2 = GATE.run_gate(SEEDS, HORIZON, PLIES, verbose=False)
    print(f"  {'PASS' if ok2 else 'FAIL'} ({len(rows2)} snapshots)")
    return 0 if (all_killed and ok2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
