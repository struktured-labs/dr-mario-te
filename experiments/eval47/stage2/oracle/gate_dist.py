#!/usr/bin/env python3
"""G1h: DIST pressure keys are candidate-common and collision-free."""
from __future__ import annotations

import sys

import oracle_arm as O


def old_mutant(seed, ply):
    """The preregistered-but-broken A1 key; retained only to kill it."""
    return seed + 7919 * (ply + 1)


def main():
    ok = True

    # Explicit in-block collision in the abandoned formula.  If this stops
    # colliding, the red side of the gate is no longer testing the named fault.
    mutant_breaks = old_mutant(30000, 1) == old_mutant(37919, 0)
    print(f"  old-key mutant collision is visible       {mutant_breaks}")
    ok &= mutant_breaks

    # New packing separates the same pair and round-trips every registered
    # (seed, ply) tuple.  Round-trip is an exhaustive injectivity proof without
    # allocating a 2.7-million-entry Python set.
    separates = O.dist_seed(30000, 1) != O.dist_seed(37919, 0)
    print(f"  new key separates the killed collision    {separates}")
    ok &= separates
    roundtrips = True
    for seed in range(30000, 39000):
        for ply in range(300):
            key = O.dist_seed(seed, ply, 0)
            if (key >> 32 != seed
                    or ((key >> 16) & 0xFFFF) != ply + 1
                    or (key & 0xFFFF) != 0):
                roundtrips = False
                break
        if not roundtrips:
            break
    print(f"  all 2,700,000 registered keys round-trip  {roundtrips}")
    ok &= roundtrips

    # There is deliberately no candidate argument: every candidate at one ply
    # receives this same pressure key (common random numbers).
    common = all(O.dist_seed(30000, 17, 0) == O.dist_seed(30000, 17, 0)
                 for _candidate in range(O.TOPK))
    print(f"  candidate-common pressure key             {common}")
    ok &= common

    print("G1h DIST KEY GATE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
