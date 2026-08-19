#!/usr/bin/env python3
"""FIXTURE TEST: the closed form for what the tie-break jitter does to a pair.

This is the load-bearing arithmetic behind #123's tempo claim, promoted out of
the report so it is a thing that FAILS when the firmware changes, rather than a
number somebody once wrote down.  Four properties, all exhaustive over the whole
domain (256 seeds x 4 orientations x 8 columns = 8,192 points):

  1. The jitter formula re-implemented FROM THE 6502 agrees with the golden
     model's `_jitter` everywhere.  (Independent second implementation, written
     from `test_search_d3.py`'s emitted instructions, not transliterated.)
  2. A duplicate pair's two jitters differ by exactly XOR 1 -- so one member
     ALWAYS outranks the other and an exact value tie can never survive.
  3. Which member wins is `bit0(seed) ^ bit3(seed) ^ bit0(col) == 0`: fixed per
     column, half the columns each way, no dependence on the board.
     ⚠ The cart derives `SEED2 = (NAV_T | 1) ^ $A4`, and `$A4` has bit 0 clear,
     so a REAL seed always has `bit0 = 1` and the rule collapses to
     `bit3(seed) ^ bit0(col) == 1`.  That reduced form is what the measurement
     rig used (3157/3157 agreement) and what the report quotes -- but it is
     ONLY valid for odd seeds, and this fixture caught the general statement
     being written as though it held for all 256.
  4. Therefore the EXPENSIVE member wins on exactly half of (seed, column)
     pairs -- the origin of the measured 48.94%.

Run: python test_jitter_pairing.py   (exit 0 = all pass)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import dblcanon as DC  # noqa: E402


def jitter(seed, o4, col):
    """Re-implemented from the emitted 6502, `test_search_d3.py` o_cand:

        LDA D_SEED; BEQ off
        LDA D_O1; ASL; ASL; ASL; ORA D_C1; EOR D_SEED; STA D_JT
        LSR; LSR; LSR; EOR D_JT; AND #3
    """
    if seed == 0:
        return 0
    t = (int(seed) ^ ((int(o4) << 3) | int(col))) & 0xFF
    return (t ^ (t >> 3)) & 3


def main():
    fails = []

    # 1 -- agreement with the golden, exhaustively
    try:
        import nes_d3_golden as G
        bad = [(s, o, c) for s in range(256) for o in range(4) for c in range(8)
               if jitter(s, o, c) != G._jitter(s, o, c)]
        print(f"1 golden agreement  : {'PASS' if not bad else f'FAIL ({len(bad)})'}"
              f"  [8192 points]")
        if bad:
            fails.append("golden")
    except ImportError as e:                      # never silently skip
        print(f"1 golden agreement  : ERROR -- could not import nes_d3_golden ({e})")
        fails.append("golden-import")

    # 2 -- a pair's jitters differ by exactly XOR 1
    bad = []
    for s in range(1, 256):
        for o in range(4):
            p = DC.PAIR_PARTNER_O4[o]
            for c in range(8):
                if jitter(s, p, c) != jitter(s, o, c) ^ 1:
                    bad.append((s, o, c))
    print(f"2 pair differs XOR 1: {'PASS' if not bad else f'FAIL ({len(bad)})'}"
          f"  [7140 points]")
    if bad:
        fails.append("xor1")

    # 3 -- the winner is predicted by bit3(seed) ^ bit0(col)
    bad = []
    for s in range(1, 256):
        for c in range(8):
            for o in range(4):
                if DC.is_canonical_o4(o):
                    continue                       # iterate over EXPENSIVE members
                cheap = DC.canonical_o4(o)
                expensive_wins = jitter(s, o, c) > jitter(s, cheap, c)
                pred = (((s & 1) ^ ((s >> 3) & 1) ^ (c & 1)) == 0)
                if expensive_wins != pred:
                    bad.append((s, o, c))
                # and the reduced form, valid ONLY for the odd seeds a cart makes
                if (s & 1) and expensive_wins != bool(((s >> 3) & 1) ^ (c & 1)):
                    bad.append(("reduced", s, o, c))
    print(f"3 winner formula    : {'PASS' if not bad else f'FAIL ({len(bad)})'}"
          f"  [general b0^b3^col0==0 over 4080; reduced form over odd seeds]")
    if bad:
        fails.append("predict")

    # 4 -- and that is exactly half of (seed, column)
    n = wins = 0
    for s in range(1, 256):
        for c in range(8):
            n += 1
            wins += (((s & 1) ^ ((s >> 3) & 1) ^ (c & 1)) == 0)
    frac = wins / n
    ok4 = abs(frac - 0.5) < 1e-9
    print(f"4 expensive share   : {'PASS' if ok4 else 'FAIL'}  {100*frac:.4f}% "
          f"of (seed, col)  [measured on real plies: 48.94%]")
    if not ok4:
        fails.append("share")

    # 5 -- the rotation cost table, derived rather than asserted
    ok5 = (DC.ROT_COST_O4 == {0: 1, 1: 3, 2: 0, 3: 2}
           and all(DC.ROT_COST_O4[DC.canonical_o4(o)]
                   < DC.ROT_COST_O4[DC.PAIR_PARTNER_O4[DC.canonical_o4(o)]]
                   for o in range(4))
           and all(DC.rotations_saved(o) == (2 if not DC.is_canonical_o4(o) else 0)
                   for o in range(4)))
    print(f"5 rot cost + saving : {'PASS' if ok5 else 'FAIL'}  "
          f"{DC.ROT_COST_O4}, saving 2 on every expensive member")
    if not ok5:
        fails.append("rotcost")

    print(f"\nFIXTURE: {'PASS' if not fails else 'FAIL ' + ','.join(fails)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
