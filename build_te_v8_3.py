#!/usr/bin/env python3
"""Reproducible build of Dr. Mario Training Edition v8.3 (STANDALONE) = v8.2 + in-game logo ™ -> TE.

v8.2 already repaints the TITLE logo "™" to "TE".  The playfield-frame "Dr.MARIO ™" logo shown in
the top-right during 1P/2P gameplay and the attract demo is a SEPARATE asset (CHR pages 0/1, tile
$9A = the ™'s "M"; the "T" is $9A's neighbour $99), left untouched by v8.2 so it still read "™".

v8.3 (standalone) = v8.2 with ``ingame_te=True``: additionally repaint tile $9A on CHR pages 0 & 1
from the ™ "M" glyph into an "E", so the in-game logo reads "TE" and matches the title.  One extra
CHR tile per bank (2 tiles); nothing else changes vs v8.2.  See title_screen.apply_ingame_te_mark.
"""
import sys, os, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "tests")
import patch_vs_cpu
from patch_cartridge_copro import apply_study_pause, STUDY_BLOB_CPU, STUDY_BLOB_EVAC
from title_screen import (apply_training_edition_title, footer_routine, footer_hook_patched,
                          footer_metasprite, footer_layout, FOOTER_HOOK_OFFSET, TITLE_CHR_PAGES,
                          TM_TILE_ID, TE_E_HALF, _tile_offset, TITLE_TILEMAP_OFFSET,
                          TITLE_BOTTOM_BASE_TILE_IDS,
                          INGAME_TM_PAGES, INGAME_TM_TILE_ID, INGAME_M_GLYPH, INGAME_E_GLYPH)
from make_bps import make_bps, apply_bps

BASE = "drmario.nes"
BASE_MD5 = "d3ec44424b5ac1a4dc77709829f721c9"

# identical footer relocation to v8.2 ($FB40 / $FB60) — v8.3 changes nothing here
V8_ROUTINE_OFF = 0x7B50   # CPU $FB40
V8_DATA_OFF    = 0x7B70   # CPU $FB60
V8_FOOTER_TEXT = "V8.00 SL"

# the 4 evacuated 2P-tail sites (file offset, length of the DRSTUDY run) -> restored to vanilla base
EVAC_SITES = [(0x2008, 34), (0x2381, 27), (0x3E66, 13), (0x3C36, 18)]  # $9FF8 $A371 $BE56 $BC26

rom_out = sys.argv[1] if len(sys.argv) > 1 else "tmp/drmario_te_v8_3.nes"
bps_out = sys.argv[2] if len(sys.argv) > 2 else "release/drmario_te_v8_3.bps"

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
# 3) title branding: footer relocated to $FB40/$FB60 + title "™"->"TE" + in-game "™"->"TE"
tiles_written = apply_training_edition_title(
    d, routine_off=V8_ROUTINE_OFF, data_off=V8_DATA_OFF, footer_text=V8_FOOTER_TEXT,
    mark_te=True, ingame_te=True)
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
# TITLE TE mark + crash-sensitive tilemap intact
for page in TITLE_CHR_PAGES:
    off = _tile_offset(page, TM_TILE_ID)
    assert tgt[off:off + 16] == TE_E_HALF, f"title TM->TE mark not applied on CHR page {page}"
assert tgt[TITLE_TILEMAP_OFFSET:TITLE_TILEMAP_OFFSET + 10] == bytes(TITLE_BOTTOM_BASE_TILE_IDS), \
    "crash-sensitive title tilemap disturbed"
# IN-GAME TE mark: tile $9A repainted to the E on CHR pages 0 & 1; base really had the "M" there
for page in INGAME_TM_PAGES:
    off = _tile_offset(page, INGAME_TM_TILE_ID)
    assert bytes(src[off:off + 16]) == INGAME_M_GLYPH, f"base in-game ™ 'M' not at page {page} tile $9A"
    assert tgt[off:off + 16] == INGAME_E_GLYPH, f"in-game TM->TE mark not applied on CHR page {page}"

patch = make_bps(src, tgt)
assert apply_bps(patch, src) == tgt, "BPS self-verify failed"
os.makedirs(os.path.dirname(bps_out) or ".", exist_ok=True)
open(bps_out, "wb").write(patch)

print(f"\nTE v8.3 STANDALONE -> {rom_out} ({len(tgt)} B, md5 {hashlib.md5(tgt).hexdigest()})")
print(f"  = v8.2 + in-game logo ™->TE (CHR pages 0/1 tile $9A: M glyph -> E glyph, 2 tiles)")
print(f"  title + study + footer identical to v8.2")
print(f"BPS patch -> {bps_out} ({len(patch)} B, verified)")
