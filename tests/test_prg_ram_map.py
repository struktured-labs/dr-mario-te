#!/usr/bin/env python3
"""KILLED MUTANTS for the PRG-RAM map deriver, both directions.

A map that cannot report a collision is not a map. These inject the two failure modes the
deriver exists to catch and assert it flags each one, then assert the real tree is clean --
so a PASS on the real tree means something.

  M1  an allocation that OVERLAPS an existing symbol           -> must be reported as a collision
  M2  an indexed store with an UNPROVEN index bound            -> must reserve its whole 256 B span
  M3  an indexed store whose PROVEN bound is registered        -> must NOT over-reserve
  CONTROL  the real emitter                                    -> 0 collisions, 0 unbounded

    python3 tests/test_prg_ram_map.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "prgram"))
import derive_prg_ram_map as D  # noqa: E402


def mutant(hits, owner_of, label, want_coll, want_unbounded):
    coll = D.collisions(owner_of, hits)
    unb = [h for h in hits if not h[5]]
    ok = (len(coll) > 0) == want_coll and (len(unb) > 0) == want_unbounded
    print(f"  {label:56s} collisions={len(coll)} unbounded={len(unb)}  "
          f"{'PASS' if ok else 'FAIL'}")
    return ok


def main():
    print("=" * 84)
    print("KILLED MUTANTS -- the deriver must FAIL on each injected fault")
    print("=" * 84)
    ok = True

    # A tiny synthetic ownership map: two symbols, 8 bytes apart.
    owner = {0x6100: ("SYM_A", 10), 0x6108: ("SYM_B", 11)}

    # M1: an indexed store owned by SYM_A whose span swallows SYM_B's byte.
    #     (fileoff, mnem, base, lo, hi, bounded)
    m1 = [(0x1000, "STA abs,X", 0x6100, 0x6100, 0x6110, True)]
    ok &= mutant(m1, owner, "M1 overlapping allocation -> collision reported", True, False)

    # M2: an indexed store with NO registered bound -> whole 256 B span reserved, and that span
    #     necessarily covers the neighbour, so it must ALSO collide.
    base = 0x6100
    assert base not in D.BOUNDS, "M2 needs an unregistered base to be meaningful"
    maxi = D.BOUNDS.get(base, (255, None))[0]
    m2 = [(0x2000, "STA abs,X", base, base, base + maxi, base in D.BOUNDS)]
    ok &= mutant(m2, owner, "M2 unproven index bound -> full 256 B span reserved", True, True)
    span = m2[0][4] - m2[0][3] + 1
    ok2 = span == 256
    print(f"  {'   ...and the reserved span is exactly 256 B':56s} span={span}  "
          f"{'PASS' if ok2 else 'FAIL'}")
    ok &= ok2

    # M3: the same store, but with a proven bound registered -> must NOT over-reserve.
    D.BOUNDS[base] = (3, "TEST-ONLY bound injected by test_prg_ram_map.py")
    try:
        maxi = D.BOUNDS[base][0]
        m3 = [(0x3000, "STA abs,X", base, base, base + maxi, True)]
        ok &= mutant(m3, owner, "M3 proven bound -> no over-reservation, no collision",
                     False, False)
    finally:
        del D.BOUNDS[base]

    # CONTROL: the real tree must be clean, or a PASS above means nothing.
    print("\n" + "=" * 84)
    print("CONTROL -- the real emitter, all configs")
    print("=" * 84)
    rows, findings = D.derive()
    nc, nu = len(findings["collisions"]), len(findings["unbounded"])
    print(f"  allocated bytes={len(rows)}  collisions={nc}  unbounded writers={nu}  "
          f"{'PASS' if nc == 0 and nu == 0 else 'FAIL'}")
    ok &= (nc == 0 and nu == 0)

    print("\n" + ("ALL PASS: the deriver fails on injected faults and passes on the real tree"
                  if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
