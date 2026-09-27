# DRVETO=1 Quartus compile -- workflow gate 5 (2026-08-30, blackmage)

Route: `ship_build.sh 13 theta400dblcanon-veto1` (the c0pin/dblcanon pattern), via a
restore-trap wrapper that installed `veto1.hex` into the shared NES_MiSTer-winner fork
and put the theta400 baseline (f78f1e93) back on exit -- fork verified pristine after
(git: only the pre-existing Aug-5 untracked rbfs; NES.qsf reverted after quartus_eda
appended its EDA lines).  db/ + incremental_db/ deleted before the flow; all four
stages ran (Synthesis 3:58, Fitter 16:57, Assembler 0:14, STA 0:13; only Power
Analyzer skipped, the documented normal); niced 19, RTL untouched.

Archive: `/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/theta400dblcanon-veto1-seed13/`
(NES.rbf/.sof, reports, manifest.json, verdict.txt, FW_IN_IMAGE_PROOF.txt, eda.log,
copro_rom.hex, NES.qsf.used with exactly one SEED line).

| item | value |
|---|---|
| seed | 13 (pinned; same as both dblcanon rbfs) |
| RTL commit | 08f23434cac449db7ee5f641958fcc00c616c29d (claude/winner-single-copro) |
| LeafEval.sv / CoproDrMario.sv | 5f062096... / da3e5e80... (identical to c0pin build) |
| firmware in fork at compile | 47edb8952dd3ae10e26c980eda405fd0 (veto1.hex, guard pre+post) |
| **rbf md5** | **70467b5cac4bada8a138d91636dc66c7** (unique across 6 archived builds) |
| sof md5 | dfe8046b66285af218780ed76ebf908c |
| copro slack | **+0.165 ns** (bar +0.10) PASS |
| pll_hdmi slack | +0.381 ns (baseline -0.012) PASS |
| ALMs | 37,664 / 41,910 = **4,246 free** (floor 1,500) PASS |
| fit_verdict | rc=0 "SHIP AS-IS" (freshness gate live) |

Slack/ALM triple is IDENTICAL to theta400dblcanon-c0pin-seed13 (0.165/0.381/37,664)
-- the documented fw-swap-at-pinned-seed placement reproduction (same behaviour as the
3/3 SEED-2 era witness), while the rbf hash moved (4bcd7428 -> 70467b5c), i.e. the ROM
content really changed inside an identical placement.

## fw-in-image bijection (THETA400_BUILD.md pattern): IMAGE-PROOF PASS
`quartus_eda --simulation` re-serialised the post-fit netlist from the same compiled
db; `tools_verify_fw_in_image.py` reassembled the 16 M20K slices:
- EXPECTED veto1.hex: **MATCH 16384/16384 bytes** (half-order unambiguous, wrong order
  differs in 12,440 bytes).
- CONTROL b03a586e (the DRVETO=0 twin): DIFFERS, min 2,699 bytes -- the +179 B
  emission shifts everything behind it; first divergence at addr 44 is the D_VIRF
  init (`85 B5` = STA $B5) at the head of `search`, i.e. the veto bytes themselves.
- CONTROL f78f1e93 (theta400 baseline): DIFFERS (2,710 B); CONTROL th150 (the 2-byte
  theta control that makes the extractor a gate): DIFFERS (2,712 B).

## Explicitly NOT done
No deployment: nothing copied to bluemage/rivalmage/any MiSTer; the rbf sits in the
archive directory only.  Deployment is the team-lead's separate decision.
