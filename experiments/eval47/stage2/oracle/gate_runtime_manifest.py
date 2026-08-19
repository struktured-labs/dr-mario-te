#!/usr/bin/env python3
"""Fail fast unless the resolved oracle decision tree matches the sealed run."""
import json

from run_oracle import runtime_manifest


EXPECTED = "a67f47f15d4f82c125956dc2b37cc3c1bc1a0c84877310d5dfd27b96345b3bd8"


def main():
    manifest = runtime_manifest("lulu")
    actual = manifest["rolled"]
    print(json.dumps(manifest, indent=1, sort_keys=True))

    good_accepts = actual == EXPECTED
    # Deliberately wrong expected input: flip one hexadecimal nibble.  The
    # comparator must reject it, proving the gate is capable of going red.
    mutant = ("0" if EXPECTED[0] != "0" else "1") + EXPECTED[1:]
    mutant_rejected = actual != mutant
    print(f"expected={EXPECTED}")
    print(f"actual={actual}")
    print(f"correct manifest accepted={good_accepts}")
    print(f"one-nibble mutant rejected={mutant_rejected}")
    if good_accepts and mutant_rejected:
        print("RUNTIME MANIFEST GATE: PASS")
        return 0
    print("RUNTIME MANIFEST GATE: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
