#!/usr/bin/env python3
"""Self-test for report_fixed's pairing-efficiency check.

Rule 21's corollary: test-defect-not-fix says simulate the FAULT and assert the outcome;
this adds simulate the NON-FAULT and assert the SILENCE. A check only ever shown to fire
is not yet a check -- and this particular check DID fire falsely on its first run, on the
live benign state (one arm 11 games behind), during the very run whose purpose was seed
alignment. So its silence is the property that actually needs proving.
"""
import sys


def warns(cand_only, ctrl_only):
    """The predicate as report_fixed uses it."""
    return min(cand_only, ctrl_only) > 0


CASES = [
    (0, 11, False, "BENIGN: candidate arm 11 games behind -- the live state that false-fired"),
    (11, 0, False, "BENIGN: control arm behind instead"),
    (0, 0, False, "BENIGN: perfectly in step"),
    (0, 60, False, "BENIGN: extreme skew, still only 'behind'"),
    (1, 1, True, "FAULT: each arm holds one seed the other lacks"),
    (3, 3, True, "FAULT: symmetric divergence"),
    (5, 12, True, "FAULT: genuine divergence with progress skew on top"),
]


def main():
    bad = 0
    for c, k, want, desc in CASES:
        got = warns(c, k)
        ok = got == want
        bad += not ok
        print(f"  {'PASS' if ok else 'FAIL':4s}  cand={c:2d} ctrl={k:2d}  "
              f"warn={str(got):5s} expect={str(want):5s}  {desc}")
    n_quiet = sum(1 for *_, w, _d in CASES if not w)
    print(f"\n{'ALL PASS' if not bad else f'{bad} FAILURES'} -- silence on {n_quiet} "
          f"benign states, fires on {len(CASES) - n_quiet} genuine ones")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
