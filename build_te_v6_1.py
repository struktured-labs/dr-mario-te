#!/usr/bin/env python3
"""TE v6.1 = the PUBLISHED v6 (romhacking.net) with the DRSTUDY 2P-tail EVACUATED — fixes the KIL
freeze (part3c $BC26 on the TITLE printing table) AND the level-select junk (part3b $BE56 on the
SETTINGS table).  v6 has no footer/branding, so v6.1 is v6 minus the 2P-tail collisions only.
1P study byte-identical; 2P study = STUDY text + P1 preview only (no P2 preview / no lift).
See FREE_SPACE_MAP.md + dr-mario-te-freeze-rootcause.

  usage: build_te_v6_1.py [rom_out=tmp/drmario_te_v6_1.nes] [bps_out=release/drmario_te_v6_1.bps]
"""
import sys, os, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "tests")
import patch_vs_cpu
from patch_cartridge_copro import apply_study_pause, STUDY_BLOB_CPU, STUDY_BLOB_EVAC
from make_bps import make_bps, apply_bps

BASE = "drmario.nes"
BASE_MD5 = "d3ec44424b5ac1a4dc77709829f721c9"
EVAC_SITES = [(0x2008, 34), (0x2381, 27), (0x3E66, 13), (0x3C36, 18)]  # $9FF8 $A371 $BE56 $BC26
rom_out = sys.argv[1] if len(sys.argv) > 1 else "tmp/drmario_te_v6_1.nes"
bps_out = sys.argv[2] if len(sys.argv) > 2 else "release/drmario_te_v6_1.bps"

src = open(BASE, "rb").read()
assert hashlib.md5(src).hexdigest() == BASE_MD5, f"{BASE} is not the expected clean USA ROM"
os.makedirs(os.path.dirname(rom_out) or ".", exist_ok=True)

patch_vs_cpu.apply_patches(BASE, rom_out)
d = bytearray(open(rom_out, "rb").read())
n = apply_study_pause(d, evac=True)
for off, ln in EVAC_SITES:
    d[off:off + ln] = src[off:off + ln]
open(rom_out, "wb").write(d)
tgt = bytes(d)

off1 = 16 + (STUDY_BLOB_CPU - 0x8000)
assert tgt[off1:off1 + len(STUDY_BLOB_EVAC)] == STUDY_BLOB_EVAC, "part1 (evac RTS) not at $D2CC"
for off, ln in EVAC_SITES:
    assert tgt[off:off + ln] == src[off:off + ln], f"evac site 0x{off:X} not restored to base"

patch = make_bps(src, tgt)
assert apply_bps(patch, src) == tgt, "BPS self-verify failed"
os.makedirs(os.path.dirname(bps_out) or ".", exist_ok=True)
open(bps_out, "wb").write(patch)
print(f"\nTE v6.1 ROM -> {rom_out} ({len(tgt)} B, md5 {hashlib.md5(tgt).hexdigest()}, study edits {n})")
print(f"  2P tail evacuated -> $9FF8/$A371/$BE56/$BC26 == vanilla base (KIL + level-select fixed)")
print(f"BPS patch -> {bps_out} ({len(patch)} B, verified)")
