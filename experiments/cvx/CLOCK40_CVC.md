# CLOCK40_CVC provenance (#18)

- **on-box rbf:** `_Console/NES_clock40_winner08f2_20260921.rbf`
- **md5:** `9e6ed9f54d552b7a83728570bf99e450`
- **build dir:** `tmp/rtl_chain/ship/clock40-winner08f2-seed13/`
- **RTL:** `08f2343` (winner, R_HOLES=20), seed 13
- **firmware:** DRCLOCK=14 (`clock14.hex` md5 `9d1c4b7f…`)
- **slack:** copro **+0.127 ns**, HDMI **+0.140 ns** (bar +0.10; single seed, inside 0.076–0.380 noise)
- **NOT the soak:** `clock40-veto2fixa-seed13` md5 `3925e958…` slack **+0.050 / +0.043** — FAIL bar, never flashed
- Old on-box name `NES_clock40_veto2fixa_20260921.rbf` was this winner08f2 file (same md5). Renamed 2026-09-23.
- Demo-eligible 2–3 seed refit **not** done. No Quartus.

MGL: `/media/fat/CLOCK40_CVC.mgl` → this rbf + `drmario_cvc_tuckguard_08211ef4.nes`
Watcher: `/media/fat/Scripts/freeze_watch_kc40.sh`
