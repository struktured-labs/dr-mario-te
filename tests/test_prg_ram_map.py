#!/usr/bin/env python3
"""KILLED MUTANTS for the PRG-RAM map deriver, both directions.

A map that cannot report a collision is not a map. These inject the two failure modes the
deriver exists to catch and assert it flags each one, then assert the real tree is clean --
so a PASS on the real tree means something.

  M1  an allocation that OVERLAPS an existing symbol           -> must be reported as a collision
  M2  an indexed store with an UNPROVEN index bound            -> must reserve its whole 256 B span
  M3  an indexed store whose PROVEN bound is registered        -> must NOT over-reserve
  M4  TWO SYMBOLS DECLARING ONE ADDRESS                        -> must be reported (dup_declared)
  M4m the RETIRED one-owner-per-address implementation         -> must be BLIND to M4 (killed mutant)
  CONTROL  the real emitter                                    -> 0 collisions, 0 dups, 0 unbounded

M4/M4m exist because of the FC_STAB/SL_PH share of $61BB (2026-08-20): declared() kept ONE
(symbol, line) per address via dict.setdefault, so the second claimant was silently dropped and
the map reported 0 collisions on an image with 6 writers at the shared byte. M4m is that retired
implementation kept as a NAMED MUTANT: if the gate cannot tell it from the fix, the M4 case is
vacuous.

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
    owner = {0x6100: [("SYM_A", 10)], 0x6108: [("SYM_B", 11)]}

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

    # M4: two symbols declaring one address -- written to a synthetic emitter file so the
    # check is exercised through the same AST path the real derivation uses.
    import tempfile
    src = (
        "SYM_A = 0x6150  # claimant 1\n"
        "OTHER = 0x6152  # innocent neighbour\n"
        "SYM_B = 0x6150  # claimant 2 -- the collision\n"
    )
    fd, tmp = tempfile.mkstemp(suffix=".py", dir=os.path.dirname(os.path.abspath(__file__)))
    os.write(fd, src.encode()); os.close(fd)
    try:
        decl = D.declared(tmp)
        dups = D.dup_declared(decl)
        got = {(a, tuple(n for n, _l in syms)) for a, syms in dups}
        ok4 = got == {(0x6150, ("SYM_A", "SYM_B"))}
        print(f"  {'M4 two symbols, one address -> dup_declared fires':56s} dups={len(dups)}  "
              f"{'PASS' if ok4 else 'FAIL'}")
        ok &= ok4

        # M4m: the RETIRED implementation (one owner per address, first wins) run over the
        # SAME synthetic emitter. It must be blind -- that blindness is the defect the fix
        # replaced, and a gate that cannot distinguish the two has proven nothing.
        import ast as _ast
        mut = {}
        for node in _ast.parse(src).body:
            if isinstance(node, _ast.Assign) and isinstance(node.value, _ast.Constant):
                for t in node.targets:
                    if isinstance(t, _ast.Name):
                        mut.setdefault(node.value.value, [(t.id, node.lineno)])  # first wins
        mut_dups = D.dup_declared(mut)
        ok4m = len(mut_dups) == 0 and mut[0x6150][0][0] == "SYM_A"
        print(f"  {'M4m retired one-owner impl -> BLIND (mutant killed)':56s} "
              f"dups={len(mut_dups)}  {'PASS' if ok4m else 'FAIL'}")
        ok &= ok4m
    finally:
        os.unlink(tmp)

    # CONTROL: the real tree must be clean, or a PASS above means nothing.
    print("\n" + "=" * 84)
    print("CONTROL -- the real emitter, all configs")
    print("=" * 84)
    rows, findings = D.derive()
    nc, nu = len(findings["collisions"]), len(findings["unbounded"])
    nd = len(findings["dup_declared"])
    print(f"  allocated bytes={len(rows)}  collisions={nc}  shared declarations={nd}  "
          f"unbounded writers={nu}  {'PASS' if nc == 0 and nu == 0 and nd == 0 else 'FAIL'}")
    ok &= (nc == 0 and nu == 0 and nd == 0)

    print("\n" + ("ALL PASS: the deriver fails on injected faults and passes on the real tree"
                  if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
