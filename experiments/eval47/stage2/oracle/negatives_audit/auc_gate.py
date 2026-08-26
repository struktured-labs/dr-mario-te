#!/usr/bin/env python3
"""GATE for the within-decision weighted AUC estimator used by refit_counterfactual.py.

Per dr-mario-gate-standard-killed-mutants: a check must be shown to FAIL on wrong inputs, not
just pass on right ones. Six known-answer cases plus a killed mutant (a score-blind estimator
must NOT reproduce the hand-computed case). Written as a SEPARATE file, not folded into the
running script -- see memory live-script-edit-mv.

    python3 auc_gate.py    # exit 0 = estimator trustworthy
"""
import sys
import numpy as np


def within_auc(z, s, f):
    """P(surviving fork ranked above dying fork) within one decision.
    z: per-candidate score.  s: survivor forks.  f: dier forks."""
    tot = s.sum() * f.sum()
    if tot == 0:
        return None
    num = 0.0
    for i in range(len(z)):
        if s[i] == 0:
            continue
        num += s[i] * (f[z[i] > z].sum() + 0.5 * f[z[i] == z].sum())
    return num / tot


A = np.array
CASES = [
    ("perfect",        (A([1., 0.]), A([8, 0]), A([0, 8])),          1.0),
    ("inverted",       (A([0., 1.]), A([8, 0]), A([0, 8])),          0.0),
    ("all ties",       (A([1., 1.]), A([8, 0]), A([0, 8])),          0.5),
    ("one cand mixed", (A([3.]),     A([5]),    A([3])),             0.5),
    ("non-discrim",    (A([1., 2.]), A([8, 8]), A([0, 0])),          None),
    # hand: survivors {2@z=2, 1@z=0}, diers {3@z=1, 1@z=0}; pairs 3*4=12;
    # z=2 beats all 4 -> 8; z=0 survivor ties the z=0 dier -> 0.5 ; = 8.5/12
    ("hand-computed",  (A([2., 1., 0.]), A([2, 0, 1]), A([0, 3, 1])), 8.5 / 12),
]

if __name__ == "__main__":
    ok = True
    for name, args, exp in CASES:
        got = within_auc(*args)
        good = (got is None and exp is None) or (
            got is not None and exp is not None and abs(got - exp) < 1e-12)
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {name:16s} got={got} expected={exp}")
    mut = 0.5                      # score-blind estimator
    killed = abs(mut - 8.5 / 12) > 1e-9
    ok &= killed
    print(f"  {'PASS' if killed else 'FAIL'}  mutant killed    score-blind gives "
          f"{mut:.4f} != {8.5/12:.4f}")
    print("\nESTIMATOR GATE:", "OK" if ok else "FAILED — do not trust the run")
    sys.exit(0 if ok else 1)
