# CHAIN540 + REACH + TAP + HSV core — build record (2026-09-26, Claude): ⛔ FAILED TIMING AT SEED 13 (not staged)

**Why (PREP only):** STEER5c. The HSV leaf term (−512 per virus in cols 3..5, row < 9) replicated an early-tap-out
reduction (tap≤100 −2.59 [−4.96, −0.22]) but failed the non-inferiority bars on width. The ship decision waits on
STEER5d's powered check; this build is the hardware prep.

## Inputs
- **RTL:** NES_MiSTer-drmario `claude/hsv-leaf` @ `cce212a` (off the shipping 08f2343; pushed to `fork`, absent
  from `origin`).
  - LeafEval.sv `` `ifdef DRHSV ``: the term is folded into the pre-scaled `matched60` accumulator (15-bit two's
    complement, sign-extended into the unchanged S_DONE2 combine).
  - Flag off: `verilator -E -P` == 08f2343 byte-exact.
- **Firmware:** `77ec742c` (CHAIN540 + DRREACH + DRREACHTAP), unchanged. The term is RTL-only.
- **Settings:** Childproof `NES.qsf.used` + `set_global_assignment -name VERILOG_MACRO "DRHSV=1"`, SEED 13.
  Script: `chain540_reach_tap_hsv_build.sh`.

## Result
| | REACH+TAP (same seed) | **+HSV** |
|---|---|---|
| copro slack | +0.127 | **−0.494 ns (bar +0.10) FAIL**, TNS −5.919 |
| pll_hdmi | +0.140 | +0.045 |
| ALMs | 37,664 | 37,651 |
| FW-in-image | 16/16 | 16/16 == 77ec742c |

- **The HSV logic is in the netlist:** `matched60[14]` 91 refs, `matched60_p[14]` 3, `base_matched[14]` 3.
- rbf `fd2355c98bba86f0cefef6fa216a25e3` is archived for the record only in
  `dr_mario_rl/tmp/rtl_chain/ship/childproof-chain540-reach-tap-hsv-seed13/`. Staging
  (`.../chain540-reach-tap-hsv/`) holds `BUILD_FAILED.md` and deliberately NO rbf.
- **Worst paths:** `quartus_sta` report_timing on the compiled db, 30 worst (`worst_paths.txt` in the archive).
  - **NONE touches the HSV logic.** They are `LeafEval bcell → Mult5/Mult6` (the existing per-virus
    multipliers) and `copro6502 state → bcell` writes.
  - ⇒ This is a placement perturbation of the design's existing tight paths
    ([[dr-mario-leaf-has-no-timing-budget]]: seed noise 0.076-0.380 on positive fits). The new accumulate is not
    itself slow.
  - A −0.49 miss is larger than that recorded noise band, so a seed hunt is not obviously enough.
  - The other lever: a register stage on the bcell → Mult input (a pipeline stage; the memory's standing price for
    any new term).
  - **Not done:** seed-hunting, per the instruction. Owner / coordinator call.

## Gates (dr-mario-te `hsv-leaf` @ `d437be0`, `experiments/hsv/`, all PASS)
- **Bitexact `gate.py rtl --define DRHSV`** with a SPEC-FIXED HSV reference (not parsed, so mutants can't parse into
  agreement):
  - PHASE1 LEAF 948/948, PHASE3 DELTA 4494/4494.
  - PHASE2 4238/4494 = the link-aware by-design set, identical with the flag off.
  - HSV is exercised on 542/948 leaf boards and 2,229/3,890 node children.
- **Mutants killed:**
  - rows < 10 → PHASE1 604/948.
  - cols {2,3,4} → PHASE1 559/948.
  - +512 → PHASE1 406/948.
  - HSV missing from the CMD-6 base latch (delta asymmetry) → PHASE3 2793/4494, with PHASE1 and PHASE2 intact.
- **Delta path:** no change needed. The matched delta is closed-form, and HSV rides `base_matched` because a
  non-clearing child never changes a virus cell. PHASE3 proves it.
- **Firmware golden (py65):** 77ec742c + HSV engine == golden mirror 340/340 (220 real HSV-heaviest boards + 120
  synthetic); HSV moved 92 decisions. This covers the firmware's 16-bit arithmetic on the new negative range.
- **Whole-search:** `cascade_leaf5b_x` (what STEER5c measured, HSV after the wrap) == an RTL-exact twin (HSV inside
  the s16 combine) on 647/647 real-play boards; HSV moved 21. Leaves never reach the wrap.
