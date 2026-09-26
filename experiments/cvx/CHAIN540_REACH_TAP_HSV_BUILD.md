# CHAIN540 + REACH + TAP + HSV core — build record (2026-09-26, Claude): ⛔ NOT STAGED. The fallback CLOSES copro (+0.760) but fails pll_hdmi (−0.176) at seed 13

**Why:** HSV512 passed STEER5d's powered check (`71970ba`):
- tap≤100 −2.26 [−3.35, −1.21]
- whole-game tap-out −1.64 [−3.86, +0.70]
- race +2.35 [+0.23, +4.44]

This record covers the hardware side. The plain HSV fit at seed 13 missed copro timing. The coordinator then approved two things:
1. a limited seed sweep (2, 7, 21, 42);
2. a principled register-stage fallback, to be designed and gated now and fitted only if the sweep failed.

The sweep failed, and so did the fallback fit.

## HOW THE TERM IS BUILT — the fold WAS used
- DRHSV is folded into LeafEval's pre-scaled **`matched60` accumulator** at ONE accumulate site in **`S_COLWALK`**.
  - The −512 per virus in cols 3..5 at row < 9 is subtracted in the same NBA as the existing +48 matched-cover term.
  - Two NBAs to `matched60` in one cycle would drop one of them.
  - `matched60` widens to 15-bit two's complement.
- **`S_DONE2` is untouched.** Its combine only sign-extends `matched60_p` (`{matched60_p[14], matched60_p}`); there is no
  new combine term.
- **Delta path:** HSV rides `base_matched`. The matched delta (`dd_matched`) is closed-form, and a non-clearing child
  never changes a virus cell. PHASE3 proves it.
- Steersim had assumed the term might sit elsewhere. It does not: it is inside the fold. The netlist confirms it —
  `matched60[14]` 87–93 refs, `matched60_p[14]` 3, `base_matched[14]` 3 in every build below.

## Inputs (all builds)
- **Firmware:** `77ec742c` (CHAIN540 + DRREACH + DRREACHTAP), unchanged. FW-in-image bijection is 16/16 in every build.
- **CoproDrMario.sv:** `da3e5e80`, identical to the shipped REACH+TAP build.
- **RTL:** the only file that differs from the shipping `08f2343` is `rtl/mappers/LeafEval.sv`.
- **⇒ HSV is RTL-only. The TAP carts are UNCHANGED:** couch `198a95e3`, CvC `33062615`, staged in
  `chain540-reach-tap/`.
- **Settings:** Childproof `NES.qsf.used` + `VERILOG_MACRO`s. The fork is NES_MiSTer-drmario `claude/hsv-leaf`, pushed to
  `fork` only, never `origin`.

## 1. Plain HSV (`cce212a`, DRHSV=1): seed 13 + the limited sweep — NO SEED PASSED
| seed | copro slack (bar +0.10) | pll_hdmi (bar ≥ −0.062) | ALMs | worst class |
|---|---|---|---|---|
| 13 | **−0.494** | +0.045 | 37,651 | bcell→Mult5/6 ENA_DFF0 (12); copro6502→bcell (18) |
| 2 | **−0.808** | −0.131 | 37,641 | bcell→Mult5 ENA; bcell→wr_/wc/run_v (the vo-indexed virus read) |
| 7 | **−0.355** | +0.216 | 37,575 | bcell→Mult ENA; bcell→p/wc |
| 21 | **−0.756** | +0.381 | 37,585 | bcell→Mult ENA; bcell→p; st; copro6502→bcell |
| 42 | **−0.465** | −0.249 | 37,555 | bcell→Mult ENA; copro6502→bcell |

- The five seeds have mean −0.58. This is a design shift, not noise: the recorded seed noise is 0.076–0.380.
- The same three path classes recur on every seed, all starting at `bcell`:
  - a 128:1 cell read → enable of the sq() DSP input registers;
  - the vo-indexed virus read → walk-control enables;
  - the host write into bcell.
- Per-seed artifacts are in `dr_mario_rl/tmp/rtl_chain/ship/childproof-chain540-reach-tap-hsv-seed{2,7,13,21,42}/`.
  - For seeds 7, 21 and 42, `tmp/chain540_reach_tap_hsv/worst_paths_seed*.txt.wide` holds per-endpoint reports
    (3000 endpoints each), classified by `classify_wide_paths.py`.
  - Scripts: `chain540_reach_tap_hsv_sweep.sh`, `chain540_reach_tap_hsv_seed_build.sh`.

## 2. The fallback: three register stages, each behind its own define (fork `391afb8`)
Every stage keeps the LeafEval FSM cycle-exact: **0 added engine cycles**.

| define | removes | how | why exact |
|---|---|---|---|
| `DRLEV_SQREG` | bcell → Mult5/Mult6 ENA_DFF0 | sq() reads enable-free copies of run_h/run_v, loaded every clk | run_h/v settle ≥ 2 clk before S_VFIN/S_DRVFIN (measured: a 2-deep copy passes, a 3-deep copy fails PHASE3) |
| `DRLEV_WRREG` | copro6502 state → bcell | host board-window write (cell, link, slot port) registered 1 clk_cpu | a 6502 store is the last cycle of its instruction, so the write lands while the FSM is idle, before any engine read |
| `DRLEV_VNPF` | bcell → vir_of[vo] → run_v/wr_/wc/p/st | S_VNEXT's virus test prefetched into a flop (`vn_hit`) | S_VNEXT is always entered with vo = 0 or vo+1, and the leaf walk never writes bcell |

**Gates** (dr-mario-te `hsv-leaf` @ `3756966`, `experiments/hsv/run_fallback_gates.sh` → `GATE_FALLBACK.txt`, all PASS):
- **Identity:** no define == `cce212a`, and DRHSV-only == `cce212a` DRHSV (preprocessed).
- **Bitexact rtl gate with all defines:**
  - PHASE1 948/948, PHASE3 4494/4494.
  - PHASE2 = the by-design link-aware set.
  - The fallback without DRHSV gives the same result.
- **Link-aware NODE gate (linknode):** 7282/7282 at doses 0/180/360, 9/9 mutants.
- **Mutants:**
  - HSV's own row, col, sign and delta mutants all still die.
  - The fallback's own mutants all die: unregistered data, swapped sq inputs, unregistered link, 3-deep sq copy,
    vo instead of vo+1, and a missing COLWALK arm.
- **Throughput:**
  - Engine CYCLES are identical with and without the fallback: 1278 / 2081 / 1301 / 891 per LEAF / NODE / BASE / DELTA.
  - **Firmware co-sim** (real copro6502 + fw 77ec742c, 69 real boards): moves AND GO→DONE clocks match HSV-only on
    69/69 boards. That is **0 cycles per node**; the mean is 65.9 M clocks/board (0.767 s at 85.9 MHz).

## 3. The fallback fit (seed 13, DRHSV + DRLEV_SQREG + DRLEV_WRREG + DRLEV_VNPF): ⛔ FAIL on pll_hdmi only
| | REACH+TAP | HSV | **HSV + fallback** |
|---|---|---|---|
| copro slack | +0.127 | −0.494 | **+0.760 PASS** |
| pll_hdmi | +0.140 | +0.045 | **−0.176 FAIL** (bar ≥ −0.062) |
| ALMs | 37,664 | 37,651 | 37,512 |
| FW-in-image | 16/16 | 16/16 | 16/16 == 77ec742c |

- **Copro is CLOSED with room:** a +1.25 ns swing, and the fallback build beats REACH+TAP by +0.63.
  - The only copro endpoints below +0.80 are bcell→p (+0.760).
  - Every targeted class is gone: DSP ENA, host write, and the vo virus read.
- **The pll_hdmi failure is not ours.** The worst 20 paths are all in the framework scaler, `ascal
  o_v_poly_t → o_v_poly_pix` (`hdmi_paths_pipe_seed13.txt`).
  - This is the known seed-placement pattern: holes80 seed 13 had copro +0.498 / pll_hdmi −0.148, and seeds 3 and 9
    of the same RTL passed both.
- **Netlist:**
  - `vn_hit` has 28 refs and `h_waddr` 334, so both defines were active.
  - `sq_h_in` / `sq_v_in` have 0 refs by name. They were absorbed into the DSP input registers, as intended; the
    DSP-ENA endpoints are gone from the timing report.
  - The four macros are in the archived `NES.qsf.used`.
- rbf `b8790802` is archived for the record only, in
  `dr_mario_rl/tmp/rtl_chain/ship/childproof-chain540-reach-tap-hsv-pipe-seed13/`.
  - That directory also holds the per-endpoint wide report, the floor paths and the pll_hdmi paths.
  - Scripts: `chain540_reach_tap_hsv_pipe_build.sh`, `chain540_reach_tap_hsv_pipe_after_sweep.sh`.
- **Not done: a fallback seed sweep.** The instruction was "do NOT seed-hunt without asking." With copro at +0.760,
  only pll_hdmi is left to hit, and that is a coin flip per seed on this project's history. The next ask is a
  2–4 seed sweep of the fallback build.

## Staging
`dr_mario_rl/tmp/rtl_chain/ship/chain540-reach-tap-hsv/` holds `BUILD_FAILED.md` only. There is deliberately NO rbf.

## HSV gates carried over (dr-mario-te `hsv-leaf` @ `d437be0`)
- Bitexact with a spec-fixed reference: PHASE1 948/948, PHASE3 4494/4494.
- Mutants: row, col and sign die in PHASE1; delta asymmetry dies in PHASE3.
- py65 firmware golden: 340/340.
- Search-level: `cascade_leaf5b_x` == RTL-exact twin on 647/647.
