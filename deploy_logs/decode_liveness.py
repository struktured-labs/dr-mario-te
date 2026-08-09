#!/usr/bin/env python
"""Liveness decode for theta400 bring-up: NAV_T, BUSY, NAV_MAGIC, mode, P2 virus count.
Re-verifies bases by signature (dr-mario-savestate-layout): hint IRAM=0x102B08, WRAM=0x103308.
"""
import sys

IRAM_HINT = 0x102B08
WRAM_HINT = 0x103308

def find_bases(b):
    # WRAM base: NAV_MAGIC $A5 at $6149 relative to base
    cands = []
    for off in range(0x100000, min(len(b), 0x110000)):
        if b[off + 0x149] == 0xA5:
            cands.append(off)
    # prefer the hint if it qualifies
    wram = WRAM_HINT if WRAM_HINT in cands else (cands[0] if cands else None)
    iram = wram - 0x800 if wram is not None else None
    return iram, wram, len(cands)

def bcd(x):
    return (x >> 4) * 10 + (x & 0x0F)

def board_virus_count(b, base):
    return sum(1 for v in b[base:base+128] if v in (0xD0, 0xD1, 0xD2))

def main(path):
    b = open(path, 'rb').read()
    iram, wram, ncand = find_bases(b)
    if wram is None:
        print(f"{path}: NAV_MAGIC signature NOT FOUND (driver cold or layout moved)")
        # fall back to hints for raw dump
        iram, wram = IRAM_HINT, WRAM_HINT
    nav_t   = b[wram + 0x147]
    nav_mag = b[wram + 0x149]
    busy    = b[wram + 0x176]
    busyskp = b[wram + 0x192]
    match_a = b[wram + 0x164]
    mode    = b[iram + 0x46]
    m0727   = b[iram + 0x727]
    m04     = b[iram + 0x04]
    p1v_ctr = b[iram + 0x324]
    p2v_ctr = b[iram + 0x3A4]
    p1v_brd = board_virus_count(b, iram + 0x400)
    p2v_brd = board_virus_count(b, iram + 0x500)
    print(f"{path}: wram_base={wram:#x} (cands_w_magic={ncand}) iram_base={iram:#x}")
    print(f"  NAV_T=${nav_t:02X} NAV_MAGIC=${nav_mag:02X} BUSY=${busy:02X} BUSYSKP=${busyskp:02X} MATCH_ACTIVE=${match_a:02X}")
    print(f"  mode$0046=${mode:02X} $0727=${m0727:02X} $04=${m04:02X}")
    print(f"  P1 virus ctr(bcd $0324)={bcd(p1v_ctr)} board$0400={p1v_brd} | P2 virus ctr(bcd $03A4)={bcd(p2v_ctr)} board$0500={p2v_brd}")

for p in sys.argv[1:]:
    main(p)
