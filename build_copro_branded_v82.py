#!/usr/bin/env python3
"""TE v8.2 branded copro cart = v28cs -> TE branding (SUBTITLE + TE mark, sprite footer DROPPED)
-> driver (evac study) -> expand.

Two v8.2 differences vs build_copro_branded.py:
  1. FOOTER DROP: the "V8.00 SL" sprite footer sits on the Settings printing table ($C0A9/$C0EF)
     and can't relocate to $FBxx (that's the copro DRIVER blob), so the copro carts drop it and keep
     the CHR subtitle ("Dr. MARIO TE / TRAINING EDITION") + TE mark.  User-cleared (no veto).
  2. EVAC study: the driver's apply_study_pause runs evac=True (part1-only) + restores the 4 tail
     sites -> the title/settings tables draw clean (no $BC26 KIL, no $BE56 level-select junk).

  usage: TE_DIR=~/projects/dr-mario-te-v8.2 DRHUMAN=1 DRPOCKET=1 DRSLAM=1 \
             python $TE_DIR/build_copro_branded_v82.py <clean_v28cs.nes> <cart_out.nes>
"""
import os, sys
TE_DIR = os.environ.get("TE_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TE_DIR)
sys.path.insert(0, os.getcwd())      # canonical driver (evac'd patch_cartridge_copro) -> FIRST
from title_screen import apply_training_edition_title, FOOTER_HOOK_OFFSET

V28CS_CLEAN = sys.argv[1]
CART_OUT    = sys.argv[2]
V8_ROUTINE_OFF, V8_DATA_OFF, V8_FOOTER_TEXT = 0x40B9, 0x40FF, "V8.00 SL"

core = bytearray(open(V28CS_CLEAN, "rb").read())
assert core[4] == 2, "expected a clean 32 KB-PRG v28cs core"
# footer=False: subtitle + TE mark only, NO sprite footer (it collides with the Settings printing
# table, and $FBxx is the copro driver so it can't relocate) -> the footer sites stay stock.
clean_footer = [(o, bytes(core[o:o + l])) for o, l in
                [(FOOTER_HOOK_OFFSET, 3), (V8_ROUTINE_OFF, 24), (V8_DATA_OFF, 24)]]
apply_training_edition_title(core, routine_off=V8_ROUTINE_OFF, data_off=V8_DATA_OFF,
                             footer_text=V8_FOOTER_TEXT, mark_te=True, draw_footer=False)
for o, orig in clean_footer:
    assert bytes(core[o:o + len(orig)]) == orig, "footer=False left footer bytes on the Settings table"
os.makedirs("tmp", exist_ok=True)
branded_core = "tmp/_v28cs_te82_core.nes"
open(branded_core, "wb").write(core)

import patch_cartridge_copro as drv    # from cwd = evac'd driver worktree
drv.V28CS = branded_core
drv.OUT = CART_OUT
drv.main()
import hashlib
print(f"\nTE v8.2 branded copro cart -> {CART_OUT}  md5 {hashlib.md5(open(CART_OUT,'rb').read()).hexdigest()}")
print("  study EVAC (part1-only) + sprite footer DROPPED (subtitle + TE mark kept)")
