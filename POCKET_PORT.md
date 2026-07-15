# Analogue Pocket openFPGA Port — Plan (ON HOLD as of 2026-07-15)

**Status: paused by user decision — resume from "Milestones" below.** Feasibility CONFIRMED,
milestone 1 (baseline fitter) DONE. Local clone at ~/projects/pocket-nes (agent WIP branch
`mapper100-copro` may exist there). Interim playable: v28cs in-cart AI runs on the STOCK
agg23 NES core — SD bundle at /mnt/data/drmario/pocket/drmario-pocket-sd.zip
(SELECT x2 at title = AI mode, 2P GAME, human P1 vs AI P2).

# Feasibility Report (2026-07-15)
(single-coprocessor Dr. Mario AI NES core; researched by agent, verdict: FEASIBLE)

See git history / session logs for full report. Load-bearing facts:
- Pocket openFPGA part: Cyclone V E 5CEBA4F23C8 — 49K LE / 18,480 ALMs / 308 M10K (~3.4Mbit) / 66 DSP / 4 PLLs
- agg23/openfpga-NES (GPL-3.0, Copybara-mirrored from NES_MiSTer): PLL already emits clk_85_9 = 85.909 MHz (our copro clock!), uses 2/4 PLLs
- me[100] one-hot mapper slot FREE in rtl/upstream/cart.sv (~line 2467) — our mapper number
- 2x 16MB PSRAM (AS1C8M16) + 256KB SRAM UNUSED by NES core; SDRAM carries PRG/CHR
- T65 6502 (BSD) already in-tree — reuse as the 2nd 6502
- Same-part precedents: SNES+SA-1+SuperFX+CX4, NeoGeo dual-CPU, VexRiscv litex (31% BRAM)
- Custom edits go in upstream_patches/ (Copybara keeps rtl/upstream 1:1 with MiSTer)
- Ship: .rbf bit-reversed to bitstream.rbf_r + JSON pack in Cores/<Author>.<Name>/ + Platforms/;
  distribute via GitHub Release zip + openfpga-cores-inventory PR (Pocket Sync/pupdate auto-fetch)
- Dock/HDMI automatic via video.json; zero-input core boots fine (input.json can be stub)
- No savestates/sleep expected (SNES core skips them too)

## Milestone 1 RESULT (2026-07-15, measured on this machine)
Baseline agg23 NES on 5CEBA4F23C8: **18,230/18,480 ALMs = 99% FULL** (agg23 wasn't kidding).
BRAM 183k/3,154k bits = 6% (94% FREE — BoardEngine slots are unconstrained). DSP 15%, PLL 2/4.
Per-entity: PPU 7,299 (OAMEval 6,014), **cart_top mapper farm 5,203 <- reclaim zone**,
T65 655 (a 2nd copro 6502 costs this), APU+audio ~1,700, savestates 310, zapper 153.
TRIM PLAN: Dr-Mario-only build keeps MMC1 + mapper-100 -> reclaims ~4,800 ALMs; +zapper/savestates ~400.
Free after trim ~5,400 vs copro cost ~4-4.5K (T65 0.7K + BoardEngine/LeafEval ~3K + glue). VIABLE, tight.

## Milestones
1. ~~Baseline fitter number~~ DONE: 99% ALM / 6% BRAM -> trim is REQUIRED, not optional
2. TRIM to Dr-Mario-only (keep MMC1+100, strip mapper farm/zapper/savestates) + mapper me[100] + $5000-$51FF window + stub copro; fitter re-run must show >=4.5K ALMs free
3. T65 @ clk_85_9 + BoardEngine/LeafEval (BRAM; spill to PSRAM if needed); zero-input autonomous play on hardware

## Risks (ranked)
1. Fit on 18,480 ALMs / 308 M10K (fitter run resolves; agg23 already trims mappers to fit)
2. LeafEval BRAM budget (M10K contention; PSRAM only for latency-tolerant data)
3. Copybara sync friction (upstream_patches/ or fork-and-abandon)
