# DRVETO Fix A (veto2fixa) Quartus compile -- 2026-08-30, blackmage

Route: restore-trap wrapper (veto1 pattern) installed `veto2_fixa.hex` into the
shared NES_MiSTer-winner fork, `ship_build.sh 13 theta400dblcanon-veto2fixa`,
baseline f78f1e93 restored on exit (verified).  RTL untouched, niced 19.
Archive: `/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/theta400dblcanon-veto2fixa-seed13/`

| item | value |
|---|---|
| seed | 13 (pinned; same as all three dblcanon rbfs) |
| RTL commit | 08f23434 (claude/winner-single-copro), rtl/ clean |
| firmware at compile | a2b2e4ac056df06a89c1e3acecbfa2ee (veto2_fixa, guard pre + archived copy) |
| **rbf md5** | **cd1fa38916cad5f8869a3b4cefdea9f6** (unique across 7 archived builds) |
| copro slack | **+0.165 ns** (bar +0.10) PASS |
| pll_hdmi slack | +0.381 ns PASS |
| ALMs | 37,664 / 41,910 = **4,246 free** (floor 1,500) PASS |
| fit_verdict | rc=0 "SHIP AS-IS" |

Slack/ALM triple is IDENTICAL to theta400dblcanon-veto1-seed13 AND -c0pin-seed13
(0.165 / 0.381 / 37,664) -- the documented fw-swap-at-pinned-seed placement
reproduction, third occurrence; rbf hash moved (70467b5c -> cd1fa389), i.e. the
ROM content changed inside an identical placement.

## fw-in-image bijection: PASS, and in the STRONG form
Fresh `quartus_eda --simulation=on --tool=modelsim --output_directory=output_files/simnet`
against the compiled db, run AFTER the baseline hex was restored to disk:
- EXPECTED veto2_fixa a2b2e4ac: **MATCH 16384/16384**
- CONTROL veto1 47edb895: DIFFERS (min 1,315 B -- the +4 B insertion's shift)
- CONTROL veto0/b03a586e: DIFFERS (2,715 B) · th400 f78f1e93: DIFFERS (3,478 B)
  · th150: DIFFERS (the 2-byte extractor gate pair held)
Because the DISK file at eda time was f78f1e93 and the image extracted as
a2b2e4ac, this run proves BOTH that the bitstream carries Fix A AND that the
extractor reads the COMPILED DB, not the current file -- a provenance question
the morning proof (eda before restore) could not separate.

## ⚠ Instrument incident (the gate caught it)
First proof attempt FAILED with image == b03a586e: `nice -n 19 quartus_eda`
died on exec (quartus_eda not on PATH; uutils nice error swallowed in the log)
and the script's netlist glob then picked `simulation/questa/NES.vo` -- an
Aug-21 leftover that really does contain the dblcanon-era b03a586e.  The
verifier refused (its control discipline is the reason it exists).  Fix: full
tool path, rc-gated, stale simnet deleted before regeneration.

## Explicitly NOT done
No deployment.  Nothing copied to bluemage/rivalmage/any MiSTer.  The rbf sits
in the archive only; deployment is a separate team-lead decision (bluemage
currently soaks veto1 70467b5c -- per the repro verdict that soak COUNTS and
must not be restarted).
