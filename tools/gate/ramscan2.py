#!/usr/bin/env python3
"""Reach analysis: can ANY store instruction land on $61B0 (S2P_TTL) or the DG scratch?

ramscan.py only caught stores whose 16-bit OPERAND was already inside $6140-$61FF. That
misses the case team-lead's clobber hypothesis actually needs: an INDEXED store whose base
sits below the window but whose 8-bit index walks into it (STA $60C0,X with X=$F0 hits
$61B0). Since X/Y are 8-bit, any indexed store with base in [target-255, target] can reach
a given target.

So: enumerate every store/RMW in PRG, compute its full reachable byte span (base for
absolute, base..base+255 for indexed), and report every instruction whose span covers the
watch set. Complete for absolute+indexed addressing; indirect ((zp),Y) stores are reported
separately since their target is not statically known.
"""
import sys
from collections import defaultdict

ABS = {0x8D: "STA", 0x8E: "STX", 0x8C: "STY", 0xEE: "INC", 0xCE: "DEC",
       0x0E: "ASL", 0x4E: "LSR", 0x2E: "ROL", 0x6E: "ROR"}
IDX = {0x9D: "STA abs,X", 0x99: "STA abs,Y", 0xFE: "INC abs,X", 0xDE: "DEC abs,X",
       0x1E: "ASL abs,X", 0x5E: "LSR abs,X", 0x3E: "ROL abs,X", 0x7E: "ROR abs,X"}
INDIRECT = {0x91: "STA (zp),Y", 0x81: "STA (zp,X)"}

WATCH = {
    0x61B0: "S2P_TTL  (STUDY2P heartbeat -- the owner's random-STUDY observable)",
    0x61B1: "DG_YC", 0x61B2: "DG_FALL", 0x61B3: "DG_N", 0x61B4: "DG_OFF",
    0x61B5: "DG_LO", 0x61B6: "DG_HI", 0x61B7: "DG_CSPAN",
    0x6195: "HOLD_ACTIVE", 0x6164: "MATCH_ACTIVE",
}


def scan(path):
    rom = open(path, "rb").read()
    prg = rom[16:16 + 0x10000]
    reach = defaultdict(list)   # target -> [(fileoff, mnem, span)]
    indirects = 0
    i = 0
    while i < len(prg) - 2:
        op = prg[i]
        if op in INDIRECT:
            indirects += 1
        elif op in ABS or op in IDX:
            base = prg[i + 1] | (prg[i + 2] << 8)
            lo, hi = (base, base) if op in ABS else (base, base + 255)
            mnem = ABS[op] + " abs" if op in ABS else IDX[op]
            for t in WATCH:
                if lo <= t <= hi:
                    reach[t].append((i + 16, mnem, (lo, hi)))
        i += 1
    return reach, indirects


def main():
    for spec in sys.argv[1:]:
        tag, path = spec.split("=", 1)
        reach, ind = scan(path)
        print("=== %s ===" % tag)
        for t in sorted(WATCH):
            hits = reach.get(t, [])
            mark = "  <-- REACHABLE" if hits else ""
            print("  $%04X %-58s %d writer(s)%s" % (t, WATCH[t], len(hits), mark))
            for off, mnem, (lo, hi) in hits:
                span = "$%04X" % lo if lo == hi else "$%04X-$%04X" % (lo, hi)
                print("        file 0x%05X  %-12s span %s" % (off, mnem, span))
        print("  (indirect stores in PRG, target not statically known: %d)" % ind)
        print()


if __name__ == "__main__":
    main()
