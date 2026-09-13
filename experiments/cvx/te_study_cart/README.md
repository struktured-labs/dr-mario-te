# TE + full study cart `81f2e8bf` (2026-09-12) — Childproof + TE branding + study mode, NO tuckguard, NO sprite footer
Recipe (reproduces byte-for-byte; the same script with TE_FOOTER unset reproduces the successor 9736cb87):
    env $(cat flags_b_control.env) DRSTUDY=1 DRSTUDY2P=1 DRSTUDY2P_INV=1 DRSTUDYCOUNTS=1 TE_FOOTER=0 \
      TE_DIR=~/projects/dr-mario-te-v8.2 python $TE_DIR/build_copro_branded_env.py drmario_v28cs.nes out.nes   # from dr-mario-tempo-wt
`flags_b_control.env` = the Childproof flag snapshot (rebuilds 30c92183 exactly).
ROOT CAUSE of the settings-screen garble: the branding's sprite FOOTER routine/metasprite (0x40B9/0x40FF)
collide with the Settings printing table. title_screen.py already documents this and offers draw_footer=False;
build_copro_branded.py never passed it. Isolated on silicon: study-only cart clean, TE+study garbled, TE+study
without footer clean. Verified on bluemage (frames here): title branded (TE mark + subtitle), settings clean,
study pause = STUDY banner + LEVEL + VIRUS counts + preview + frozen board.
Deployed to rivalmage as TE_HOLES80.mgl (holes80 seed-9 core + this cart).

## v2 `6c3c3168` (2026-09-13): STUDY banner relocated — add `DRSTUDY_Y=0x98` to the recipe (emitter commit f5508e3)
Owner's hotel TV trimmed the banner at the top (default Y=$08 survives only an 8-line trim). $C2 (below
the VIRUS box) was INVISIBLE: shares scanlines with the 8 STUDYCOUNTS digit sprites (slots 8-15, Y=$BF);
the PPU's 8-sprites-per-scanline limit drops slots 32-36. $94 rendered but touched the magnifier border;
$98 = centred in the magnifier→VIRUS gap, verified on bluemage (frame here). One byte differs from
`81f2e8bf`. Deployed to rivalmage as TE_HOLES80.mgl.
