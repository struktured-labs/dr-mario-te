#!/usr/bin/env python3
"""Reproducible build of Dr. Mario Training Edition v8.2 (STANDALONE) = v8 - the KIL/corruption.

v8's DRSTUDY 2P-study tail (part2 $9FF8 / part3a $A371 / part3b $BE56 / part3c $BC26) was placed on
"dead" filler that is actually LIVE data read by RB6C2_PRINT printing tables (title/settings/$A346)
and an LDA $9FF8,X data table.  Read-as-data every screen draw -> part3c $BC26 mis-parses the TITLE
table -> stack corruption -> jump to $0301 = $02 = KIL (hard freeze); part3b $BE56 = level-select
junk tiles.  Filler is NOT proof of free (see FREE_SPACE_MAP.md / dr-mario-te-freeze-rootcause).

v8.2 (standalone):
  * apply_study_pause(evac=True): keep part1 ($D2CC, STUDY letters + P1 preview) ending RTS; DROP
    the 2P tail; restore $9FF8/$A371/$BE56/$BC26 to VANILLA base -> title + settings draw clean.
    Cost: 2P study = STUDY text + P1 preview only (no P2 preview / no Y-lift).  1P study unchanged.
  * relocate the "V8.00 SL" footer OFF the Settings table ($C0A9/$C0EF) to $FB40/$FB60 — free in the
    standalone (the copro carts use $FBxx for the driver -> they DROP the sprite footer; split-build).
"""
import sys, os, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "tests")
import patch_vs_cpu
from patch_cartridge_copro import apply_study_pause, STUDY_BLOB_CPU, STUDY_BLOB_EVAC
from title_screen import (apply_training_edition_title, footer_routine, footer_hook_patched,
                          footer_metasprite, footer_layout, FOOTER_HOOK_OFFSET, TITLE_CHR_PAGES,
                          TM_TILE_ID, TE_E_HALF, _tile_offset, TITLE_TILEMAP_OFFSET,
                          TITLE_BOTTOM_BASE_TILE_IDS)
from make_bps import make_bps, apply_bps

BASE = "drmario.nes"
BASE_MD5 = "d3ec44424b5ac1a4dc77709829f721c9"

# v8.2 footer -> $FB40 (routine) / $FB60 (metasprite): free in the standalone, outside every print
# table, 0 refs (verified in the audit).  Not shared with the copro carts (driver owns $FBxx).
V8_ROUTINE_OFF = 0x7B50   # CPU $FB40
V8_DATA_OFF    = 0x7B70   # CPU $FB60
V8_FOOTER_TEXT = "V8.00 SL"

# the 4 evacuated 2P-tail sites (file offset, length of the DRSTUDY run) -> restored to vanilla base
EVAC_SITES = [(0x2008, 34), (0x2381, 27), (0x3E66, 13), (0x3C36, 18)]  # $9FF8 $A371 $BE56 $BC26

rom_out = sys.argv[1] if len(sys.argv) > 1 else "tmp/drmario_te_v8_2.nes"
bps_out = sys.argv[2] if len(sys.argv) > 2 else "release/drmario_te_v8_2.bps"

src = open(BASE, "rb").read()
assert hashlib.md5(src).hexdigest() == BASE_MD5, f"{BASE} is not the expected clean USA ROM"
os.makedirs(os.path.dirname(rom_out) or ".", exist_ok=True)

# 1) internal v6 (VS-CPU + STUDY apparatus)
patch_vs_cpu.apply_patches(BASE, rom_out)
d = bytearray(open(rom_out, "rb").read())
# 2) v8.2 study-pause: part1 only (RTS), no 2P tail
n_study = apply_study_pause(d, evac=True)
# 2b) restore the 4 evacuated tail sites to vanilla base (clear any v6 study code -> tables clean)
for off, ln in EVAC_SITES:
    d[off:off + ln] = src[off:off + ln]
# 3) title branding: footer relocated to $FB40/$FB60 + "™"->"TE"
tiles_written = apply_training_edition_title(
    d, routine_off=V8_ROUTINE_OFF, data_off=V8_DATA_OFF, footer_text=V8_FOOTER_TEXT, mark_te=True)
open(rom_out, "wb").write(d)
tgt = bytes(d)

n_tiles, base_x = footer_layout(V8_FOOTER_TEXT)
exp_routine = footer_routine(V8_DATA_OFF, base_x)
exp_meta = footer_metasprite(n_tiles)

# --- self-verify ---
# part1 present + ends RTS
off1 = 16 + (STUDY_BLOB_CPU - 0x8000)
assert tgt[off1:off1 + len(STUDY_BLOB_EVAC)] == STUDY_BLOB_EVAC, "part1 (evac RTS) not at $D2CC"
# the 4 tail sites are byte-identical to vanilla base => title + settings + $A346 tables draw clean
for off, ln in EVAC_SITES:
    assert tgt[off:off + ln] == src[off:off + ln], f"evac site 0x{off:X} not restored to base"
# footer relocated off the Settings table, rendered from $FB40
assert tgt[FOOTER_HOOK_OFFSET:FOOTER_HOOK_OFFSET + 3] == footer_hook_patched(V8_ROUTINE_OFF), "hook not -> $FB40"
assert tgt[V8_ROUTINE_OFF:V8_ROUTINE_OFF + len(exp_routine)] == exp_routine, "footer routine not at $FB40"
assert tgt[V8_DATA_OFF:V8_DATA_OFF + len(exp_meta)] == exp_meta, "footer metasprite not at $FB60"
# the old footer sites $C0A9/$C0EF are vanilla again (Settings table clean)
assert tgt[0x40B9:0x40B9 + 23] == src[0x40B9:0x40B9 + 23], "$C0A9 not restored to base"
assert tgt[0x40FF:0x40FF + 17] == src[0x40FF:0x40FF + 17], "$C0EF not restored to base"
# TE mark + crash-sensitive tilemap intact
for page in TITLE_CHR_PAGES:
    off = _tile_offset(page, TM_TILE_ID)
    assert tgt[off:off + 16] == TE_E_HALF, f"TM->TE mark not applied on CHR page {page}"
assert tgt[TITLE_TILEMAP_OFFSET:TITLE_TILEMAP_OFFSET + 10] == bytes(TITLE_BOTTOM_BASE_TILE_IDS), \
    "crash-sensitive title tilemap disturbed"

patch = make_bps(src, tgt)
assert apply_bps(patch, src) == tgt, "BPS self-verify failed"
os.makedirs(os.path.dirname(bps_out) or ".", exist_ok=True)
open(bps_out, "wb").write(patch)

print(f"\nTE v8.2 STANDALONE -> {rom_out} ({len(tgt)} B, md5 {hashlib.md5(tgt).hexdigest()})")
print(f"  study part1-only (RTS); 2P tail evacuated -> $9FF8/$A371/$BE56/$BC26 == vanilla base (tables clean)")
print(f"  footer '{V8_FOOTER_TEXT}' relocated $C0A9/$C0EF -> $FB40/$FB60 (Settings table clean)")
print(f"BPS patch -> {bps_out} ({len(patch)} B, verified)")
