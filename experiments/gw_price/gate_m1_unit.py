#!/usr/bin/env python3
"""G1-M1 adjudication + replacement (rule 5/6 of the gate standard).

HISTORY. The end-to-end closure mutant (make_farm_env(closure_source=True),
i.e. "install the capsule source via NesPillSource.attach()") survived TWO G1
runs — byte-identical games with 1 and then 3 observed ties.  Diagnosis, unit-
verified below: the mutant is EQUIVALENT BY IMPORT CONTEXT, not weak.  Two
divergent copies of nes_pills exist:

    dr_mario_rl/tmp/pillrng/nes_pills.py   attach() installs _PillDraw — FIXED
                                           (deepcopy-safe object; the module's
                                           own docstring records the repair)
    dr-mario-qa-wt/experiments/nes_pills.py  attach() installs the LAMBDA —
                                           the original closure defect

oracle_arm pushes ROOT/tmp/pillrng onto sys.path, so in any process where the
oracle rig is booted — which the pricing instrument requires — `import
nes_pills` resolves to the FIXED copy and attach() cannot express the defect
the mutant was built to reproduce.  (This also means the 2026-08-10 note that
"nes_pills is still unfixed everywhere" is stale: the pillrng copy has been
repaired; the QA copy has not.  Code-skew hazard recorded in memory.)

REPLACEMENT (the A_v precedent: a killable check of the same defect CLASS plus
a direct unit check of the guarded property, not a weakened mutant):

  U1  guarded property, on the REAL constructor: make_farm_env(default) →
      deepcopy → step the clone → the PARENT's stream must be UNMOVED
      (compared against a paired reference env; the exact seed-peeking
      channel the observer must not open).
  M1a defect-class mutant, import-proof: install the RAW lambda directly
      (env._rand_pill = lambda: Pill(*src.next_pill()) — bypassing attach()
      entirely, so no module resolution can silently repair it) → the SAME
      check must detect the theft.  If U1's check cannot see M1a's defect,
      the check is vacuous and this gate fails.

Exit 0 = U1 green AND M1a killed; anything else = 1.
"""
from __future__ import annotations

import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_gw_price as R  # noqa: E402

fail = []


def check(name, ok, detail=""):
    print(f"  {name:34s} {'PASS' if ok else 'FAIL'}  {detail}")
    if not ok:
        fail.append(name)


def parent_perturbed(env_factory, n_prime=4, n_clone_steps=3, n_probe=6):
    """Build two identical envs; deepcopy+step clones of A only; return whether
    A's subsequent draws differ from B's (the theft observable)."""
    import numpy as np
    a, b = env_factory(), env_factory()
    for env in (a, b):
        for _ in range(n_prime):
            act = int(np.flatnonzero(env.action_masks())[0])
            env.step(act)
    for _ in range(n_clone_steps):
        c = copy.deepcopy(a)
        act = int(np.flatnonzero(c.action_masks())[0])
        c.step(act)
    da = [(p.a, p.b) for p in (a._rand_pill() for _ in range(n_probe))]
    db = [(p.a, p.b) for p in (b._rand_pill() for _ in range(n_probe))]
    return da != db


def main():
    print("gate_m1_unit (adjudication of the surviving closure mutant):")
    # boot the ORACLE FIRST — the instrument's real import context, and the
    # context in which the old end-to-end mutant was shown equivalent
    R._boot_oracle()
    import oracle_arm  # noqa: F401
    import nes_pills
    import inspect
    src_attach = inspect.getsource(nes_pills.NesPillSource.attach)
    print(f"  nes_pills resolved to: {nes_pills.__file__}")
    is_fixed = "_PillDraw" in src_attach
    check("context: attach() is the FIXED impl", is_fixed,
          "attach installs _PillDraw" if is_fixed else "attach is the lambda")

    # equivalence demonstration: attach() under this context is deepcopy-safe,
    # so the retired end-to-end mutant could never have diverged
    env = R.make_farm_env(52125, closure_source=True)
    check("retired mutant is a NO-OP here",
          type(env._rand_pill).__name__ == "_PillDraw",
          f"closure_source=True still yields {type(env._rand_pill).__name__}")

    # U1: the real constructor's forks never touch the parent stream
    check("U1 parent stream unmoved (real ctor)",
          not parent_perturbed(lambda: R.make_farm_env(52125)))

    # M1a: raw-lambda defect, attach() bypassed — must be DETECTED
    def raw_lambda_env():
        from drmario.faithful_env import Pill
        e = R.make_farm_env(52125)
        src = e._rand_pill.src          # the underlying NesPillSource
        e._rand_pill = lambda: Pill(*src.next_pill())
        return e

    check("M1a raw-lambda mutant KILLED",
          parent_perturbed(raw_lambda_env),
          "clone steps steal parent draws, check sees it")

    print("RESULT:", "ALL PASS" if not fail else f"FAIL: {fail}")
    sys.exit(0 if not fail else 1)


if __name__ == "__main__":
    main()
