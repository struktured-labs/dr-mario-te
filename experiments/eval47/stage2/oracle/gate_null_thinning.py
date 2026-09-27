#!/usr/bin/env python3
"""G1i: deterministic null thinning can go red in both directions."""
from __future__ import annotations

import sys

import oracle_arm as O


def main():
    keys = [(seed, ply) for seed in range(30000, 39000)
            for ply in range(0, 300, 10)]
    all_kept = all(O.null_keeps_flip(s, p, 1, 1) for s, p in keys)
    none_kept = not any(O.null_keeps_flip(s, p, 0, 1) for s, p in keys)
    deterministic = all(
        O.null_keeps_flip(s, p, 371293, 1_000_000)
        == O.null_keeps_flip(s, p, 371293, 1_000_000)
        for s, p in keys)
    realised = sum(O.null_keeps_flip(s, p, 371293, 1_000_000)
                   for s, p in keys) / len(keys)
    tracks = abs(realised - 0.371293) < 0.005

    # Killed mutant: invert the acceptance result. It must break BOTH extreme
    # endpoint checks, proving neither side is a vacuous assertion.
    inverted = lambda s, p, n, d: not O.null_keeps_flip(s, p, n, d)
    mutant_breaks_zero = any(inverted(s, p, 0, 1) for s, p in keys)
    mutant_breaks_one = not all(inverted(s, p, 1, 1) for s, p in keys)

    checks = {
        "keep_1_keeps_all": all_kept,
        "keep_0_rejects_all": none_kept,
        "same_key_is_deterministic": deterministic,
        "large_grid_tracks_registered_fraction": tracks,
        "inverted_mutant_breaks_keep_0": mutant_breaks_zero,
        "inverted_mutant_breaks_keep_1": mutant_breaks_one,
    }
    for name, value in checks.items():
        print(f"  {name:42s} {value}")
    ok = all(checks.values())
    print("G1i NULL-THINNING GATE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
