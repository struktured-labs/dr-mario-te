#!/usr/bin/env python3
"""Byte-level census of every absolute WRITE into PRG-RAM $6140-$61FF in a cart image.

Catches an assembler-level off-by-one the source review cannot: scans the whole PRG for
absolute store/RMW opcodes whose 16-bit operand lands in the driver's PRG-RAM state block.
Complete for absolute addressing (no false negatives); indexed forms are reported with their
full reachable span, since STA $61xx,X can reach anywhere in the page.
"""
import sys
from collections import defaultdict

# opcode -> (mnemonic, indexed?)
STORES = {
    0x8D: ("STA abs", None), 0x8E: ("STX abs", None), 0x8C: ("STY abs", None),
    0x9D: ("STA abs,X", "X"), 0x99: ("STA abs,Y", "Y"),
    0xEE: ("INC abs", None), 0xFE: ("INC abs,X", "X"),
    0xCE: ("DEC abs", None), 0xDE: ("DEC abs,X", "X"),
    0x0E: ("ASL abs", None), 0x1E: ("ASL abs,X", "X"),
    0x4E: ("LSR abs", None), 0x5E: ("LSR abs,X", "X"),
    0x2E: ("ROL abs", None), 0x3E: ("ROL abs,X", "X"),
    0x6E: ("ROR abs", None), 0x7E: ("ROR abs,X", "X"),
}

NAMES = {
    0x6143: "ARMED", 0x6147: "NAV_T", 0x6149: "NAV_MAGIC", 0x6152: "TGT_C2", 0x6153: "TGT_O2",
    0x6161: "ARMED2", 0x6164: "MATCH_ACTIVE", 0x616E: "ROT_DONE2", 0x6176: "BUSY",
    0x6179: "TUCK_C2", 0x617A: "TUCK_R2", 0x617B: "EFF_C2",
    0x6190: "SWD_CTL", 0x6191: "SWD_CTH", 0x6192: "BUSYSKP",
    0x6193: "DG_BUDGET", 0x6194: "EFF_DIST2",
    0x6195: "HOLD_ACTIVE", 0x6196: "HOLD_LASTCLK", 0x6197: "HOLD_CNT_LO", 0x6198: "HOLD_CNT_HI",
    0x61B0: "S2P_TTL", 0x61B1: "DG_YC", 0x61B2: "DG_FALL", 0x61B3: "DG_N", 0x61B4: "DG_OFF",
    0x61B5: "DG_LO", 0x61B6: "DG_HI", 0x61B7: "DG_CSPAN",
}

LO, HI = 0x6140, 0x61FF


def scan(path):
    rom = open(path, "rb").read()
    prg = rom[16:16 + 0x10000]
    hits = defaultdict(list)
    i = 0
    while i < len(prg) - 2:
        op = prg[i]
        if op in STORES:
            operand = prg[i + 1] | (prg[i + 2] << 8)
            if LO <= operand <= HI:
                mn, idx = STORES[op]
                hits[operand].append((i + 16, mn, idx))
        i += 1
    return hits


def main():
    tags = sys.argv[1:]
    tables = {}
    for spec in tags:
        tag, path = spec.split("=", 1)
        tables[tag] = scan(path)
    allad = sorted(set().union(*[set(t) for t in tables.values()]))
    print("addr    name           " + "".join("%-28s" % t for t in tables))
    for a in allad:
        row = "$%04X  %-14s " % (a, NAMES.get(a, ""))
        for t in tables:
            h = tables[t].get(a, [])
            forms = sorted(set(m for _, m, _ in h))
            row += "%-28s" % ("%d: %s" % (len(h), ",".join(forms)) if h else "-")
        print(row)
    print()
    for t in tables:
        idxd = [(a, o, m, ix) for a, hs in tables[t].items() for o, m, ix in hs if ix]
        print("%s: INDEXED stores into $%04X-$%04X: %d %s"
              % (t, LO, HI, len(idxd), idxd if idxd else "(none -- no indexed spill possible)"))


if __name__ == "__main__":
    main()
