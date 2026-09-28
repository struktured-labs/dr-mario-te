# ANTIBODY + DRDIST (STEER6b dist_target60) + DRSPAWNEDGE carts — build record (2026-09-28, Claude)

**STATUS: ✅ STAGED (NOT deployed) — seed 21: copro +0.418, pll_hdmi +0.052, rbf `318607aa`, in `dr_mario_rl/tmp/rtl_chain/ship/antibody-dist60/`.** Ship waits on steersim's opponent suite and the fractional-latency sensitivity.

**Why:** STEER6b CONFIRMED dist_target60 (`81c74021`, `RESULT_STEER6*.md`): tap-out −5.40 pp [98.33% CI −7.47, −3.42],
race +6.56.
- It becomes ANTIBODY's successor IF steersim's opponent suite passes, and the fractional-latency sensitivity is
  also pending.
- STEER6c priced answer latency at about +2.7 pp tap-out per frame on every decision. So this is a ZERO-CYCLE route,
  not a sequential one.

## What is built
| layer | change | where |
|---|---|---|
| firmware | once per search, from the ROOT: with 1..4 viruses write LeafEval `$70F5 = $80 \| target` (the smallest-D virus, ties lowest index = Leaf6Decider mode dist_target, vk 4, cap 16, kdig 0), else `$70F5 = 0` | dr-mario-te `dist-target`: `fpga/copro/dist_6502.py` at `$A400`, JSR'd before Pass 0's CMD 6 (env `DRDIST`) |
| RTL | CoproDrMario `$70F5` target register, **cleared by every GO's copro reset** (an older firmware = no target = term 0) | fork `claude/dist-leaf` **3b164c7** (= `claude/dist-target` 14eb0d4 rebased on ANTIBODY's 391afb8) |
| RTL | LeafEval: leaf −60·D(target) on the LEAF board, 0 unless the target is still a virus there | same, `` `ifdef DRDIST `` (requires DRHSV) |
| carts | DRSPAWNEDGE (missed new-pill edge after a Y=$0F lock) | reach-root `cd8a3b4` (+ Mesen real-ROM PASS `2b8b62b7`) |

**Byte-identical before the endgame:**
- With more than 4 viruses the firmware writes 0, so every leaf is ANTIBODY's.
- With the flag off:
  - the firmware reproduces **77ec742c**;
  - both RTL files preprocess identical to fork main, bare and with DRHSV + fallback.

## RTL design: ZERO added cycles
- **The fold:**
  - D is folded into the leaf where `S_DONE` registers `matched60 → matched60_p` (−60·D; S_DONE2 unchanged).
  - This is the same signed 15-bit path DRHSV added.
  - Worst case −13,824 (HSV) − 960 (D) stays above −16,384.
- **FULL leaves (LEAF / NODE):**
  - A 1-deep pipeline off the S_COLWALK cell (one extra load on the walk's existing mux output) latches the target's
    row, its column and the 8 column tops.
  - When the walk ends, a ~20-cycle D-FSM runs: per-cell costs, then 5 horizontal and 13 vertical windows, then 60·D
    as 64D − 4D with no DSP.
  - It runs alongside the ≥ 128-cycle per-virus/setup scans.
- **DELTA leaves (CMD 7):**
  - CMD 6's base walk keeps its latches.
  - `S_DNEW` patches in the two placed cells (a non-clearing child differs from its parent only there: row and
    column cells, and tops as a min).
  - The D-FSM runs alongside the 48-cycle pollution scan.
- **Main FSM:** no transition is touched. A simulation witness (`dt_late`) counts any S_DONE that reads an unfinished
  penalty; it is 0 everywhere.

## Gates (dr-mario-te `dist-target`, `experiments/dist/GATE_DIST.txt`; all PASS)
- **Identity:** RTL 4/4 files × defines; firmware DRDIST=0 → 77ec742c.
- **Bitexact rtl gate with the term:**
  - Per-case targets are spread over EVERY cell: 1/8 none, 1/8 the firmware rule, 1/8 a non-virus cell, the rest
    varied viruses.
  - PHASE1 LEAF 948/948 (693 with an active target, D 0..16 all present).
  - PHASE3 DELTA 4494/4494 (2,340 active, 290 where the placement changes D, i.e. the patch path).
  - Engine **CYCLES identical** with the term on vs off (1278 / 2081 / 1301 / 891 per LEAF / NODE / BASE / DELTA).
  - `DT_LATE 0`.
- **Link-aware NODE (clears, gravity, cascades, a cleared target):** 7282/7282 against cascade_chain_x plus the spec
  HSV and D terms, 5,001 records with D ≠ 0. Latency is identical (mean 3273 / 3888).
- **RTL mutants — 12 killed:**
  - wrong window (h, v);
  - wrong gravity counting;
  - the pocket-under-overhang block (semantic "fillable" form);
  - empty below the virus (fillable);
  - the vertical overhang;
  - sign, weight, cap, missing target-virus test;
  - the delta row / top patch.
  - The plain DELETIONS of the cavity and below checks are EQUIVALENT, for a documented reason: the 5-bit `top − r`
    underflows past the cap, and the virus itself is the overhang.
- **`dist_equiv`:** the gate's spec reference == `cascade_leaf6_x._vdist` on 411,526 viruses, and the target rule ==
  Leaf6Decider on 20,923 boards.
- **Firmware target (py65, the emitted routine):**
  - == the Leaf6Decider rule on 22,646 boards: every real gate-(b) game board, 1,234 couch boards (lulu, 9/27 HSV,
    9/26 control) and 20k synthetic.
  - 7 firmware mutants killed, including the **wrong ≤ 4 gate** (vk5), the tie rule, windows, gap, cavity,
    below-virus and cap.
  - Cost: **~2.4k cycles** per decision with > 4 viruses; **median 11k, max 16k (≤ 0.19 ms)** with ≤ 4. Once per
    decision, never per leaf.
- **Firmware golden (py65 WHOLE search, engine leaf = golden + HSV + D of the target the firmware wrote):**
  - 597/597 == mirror (154 game + 283 couch + 120 synthetic endgame, plus 40 boards with > 4 viruses).
  - Target written == rule 597/597.
  - The term moved **143** decisions, and 0 on the > 4-virus boards.
- **Whole search vs the measured sim** (`cascade_leaf6_x` dist_target60 with the term after the wrap, against an
  RTL-exact twin with the term inside the combine):
  - 2,233/2,233 decisions.
  - This includes the **420 couch regression boards (9/27 lulu G1 stall, 9/27 match-1 G3)**.
  - The term moved 553.
- **Firmware co-sim** (real copro6502 on CoproDrMario, Verilator):
  - DIST RTL + fw 77ec742c == ANTIBODY RTL + fw 77ec742c on the 69 fw co-sim boards, **moves AND GO→DONE clocks
    69/69**. The D engine adds 0 cycles.
  - DIST fw on the > 4-virus boards: same moves 52/52, clocks −3.0k..+0.2k.
- **Endgame decision latency** (437 endgame boards, both firmwares on the DIST RTL):
  - Mean **−0.07 frames**, median +0.005; p90 +1.15, p95 +2.7 (max +12.8, min −7.4). The term changed 120 moves.
  - This spread is **value-dependent search effort**: the term changes leaf values, so the tuck extension and top-k
    do different work. It is not the term's cost; per engine command the cycles are identical.
  - Steersim's fractional-latency sensitivity should use this distribution, not a flat 0.
- **Interface compliance:** unchanged. DRDIST touches no cart, and the paired DRSPAWNEDGE carts passed with 0
  violations (reach-root).

## Fit
The bars are defined in `dr-mario-main-wt/experiments/rtl_chain/fit_verdict.sh` (main @ `160ecaf`): copro ≥ +0.10
(`SLACK_BAR`, l.25), and pll_hdmi ≥ −0.062 (`BASE_HDMI` −0.012 − 0.05, l.24/87). Seed 3 ran first; the ≤ 4-seed
sweep was pre-approved.

| seed | copro slack | pll_hdmi | ALMs | verdict |
|---|---|---|---|---|
| 3 | +0.591 | −0.596 | 37,687 | FAIL (pll_hdmi; worst paths are all the framework `ascal` scaler) |
| 7 | +0.616 | −0.145 | 37,651 | FAIL (pll_hdmi) |
| **21** | **+0.418** | **+0.052** | **37,711** (4,199 free) | **SHIP AS-IS** |

- Seeds 9 and 11 were not needed.
- The copro domain passed at every seed with room. ANTIBODY itself was +0.806 at seed 3.
- The seed-21 copro floor is a pre-existing `bcell → curlen` path (+0.418); no DRDIST register is near the top.
- **FW-in-image:** 16/16 == 1488e158, and ANTIBODY's 77ec742c matches 0/16.
- **Netlist** (seed 21): HSV `matched60[14]` 42 refs, the fallback registers (`vn_hit` 28, `h_waddr` 321), and the
  DRDIST engine (`dt_pen` 95, `dbest` 224, `lev_a_tgt` 643).
- **Staged** in `dr_mario_rl/tmp/rtl_chain/ship/antibody-dist60/`:
  - `NES_antibody_dist60_seed21_20260928.rbf` (md5 `318607aabb0520ec941f578984dd8b9b`) + BUILD.md + proofs + fw hex;
  - couch cart `…spawnedge_c960dd49.nes` and CvC cart `…spawnedge_3b8737a9.nes`.
- Staging is automated by `antibody_dist_stage.sh 21`, which refuses on any miss.
- Not deployed. bluemage and rivalmage were not touched.

## Artifacts
- fw `1488e1583ab7ad8b2011d4c136926faf`.
- RTL fork `claude/dist-leaf` 3b164c7.
- Carts c960dd49 / 3b8737a9.
- Scripts:
  - builds: `chain540_reach_tap_hsv_dist_build.sh <seed> <rtl>`, `chain540_reach_tap_hsv_dist_sweep.sh`;
  - staging: `antibody_dist_stage.sh <seed>`.
- Archives: `dr_mario_rl/tmp/rtl_chain/ship/childproof-antibody-dist-seed<N>/`.
