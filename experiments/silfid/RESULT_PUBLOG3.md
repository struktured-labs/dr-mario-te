# RESULT (silicon-fidelity lane, 2026-10-07): PUBLOG capture #3, the anytime-commit fix on silicon

## Why
- **Capture #2's finding** (cart d84436ff, FAIR driver, fw 1488e158):
  - The copro's answers equal Verilator in the tall-endgame cell: 0 DIVERGED of 408 pills at ≤ 20 viruses on height 14–16.
  - Yet the cart lands something other than the copro final on **24.0%** of them (97 / 404).
  - 17.6% land the cart's OWN committed target.
- **The steersim lane's anytime-commit model explains it.** The cart commits to the RUNNING answer at the gate
  (MINTHINK 12 hooks = 6 f after GO), and 1488's at-gate answer is final only ~55–64% of the time.
- **On silicon the split is sharp** (h16 `experiments/silfid/predict_v11_20261007.txt`):
  - at-gate == final → 6.8% of landings are ≠ final;
  - at-gate ≠ final → 45.1%.
- **V11** (fw c51d2e21 = 1488 + DRTUCKREACH + DRTUCKLIVE + DRROOTORD + DRLEFLUSH) publishes the final much earlier.
- **Capture #3 tests the fix on silicon:** the FAIR2PLUS P2 driver on the V11 rbf, with the same seat and pump as capture #2.

## Prediction (before any hardware)
**Method:** capture #2's CELL uploads are co-simulated on V11, using the same RTL 3b164c7 and the same vsim_pub2 binary
with fw c51d2e21.
- The 1488 co-sim's at-gate answer equals silicon's logged at-gate answer on 396 / 404 pills.
- **At-gate == final:**
  - 1488: 55.0%;
  - V11: 91% on the first replayed subset (the paired 1488 rate on the same pills is 73.8%);
  - so the V11 non-final rate is ~0.33× 1488's.
- V11's final equals 1488's on every replayed pill. It is the same answer, only reached earlier.

**Predicted landing ≠ copro-final rate in the tall-endgame cell on V11: ~12.5%** (90% band ~9.7–16.2%), vs **24.0%** on
1488. That is the provisional figure from the partial V11 run; h16 `predict_v11_20261007.txt` carries the final one.

**Caveat:** the conditionals are measured on FAIR. FAIR2PLUS (ABORTSTALE + LGPRESTART + DISTROW=2) changes how the cart
follows a late change, so the at-gate ≠ final arm is an upper-side estimate.

## The cart (dr-mario-te `claude/silfid-publog3`, stacked on `claude/silfid-publog2` / PR #41)
`c3_cvcp2` = **437cd6aa**, built as the cvcp2 seat + DRP1AIHI + DRSLICEGUARD2 + **DRABORTSTALE + DRLGPRESTART +
DRDISTROW=2** + DRPUBLOG + DRPUBLOG_PDW + DRP1HOLD + DRGPUMP + three new flags. All flags are default-off and
byte-identical when off.
- The P2 flag snapshot was diffed against FAIR2PLUS 5a1695da: it differs only in seat, menu and logging flags.
- **`DRP1DRAIN`:** zeroes P2's outgoing attack $0398 inside the hold. Capture #2 let it reach 87; its freeze began at 41.
- **`DRNAVESC_NOPLAY`:** the stuck-screen escape never fires in a LIVE round (mode 4, P2 viruses ≠ 0).
  - Capture #2 saw the counter reach 617–1197 of 1200 inside live play, and it fired at +49 min.
- **`DRP1HOLDFIRST`:** the hold runs before the spectator search, so the P1 AI never runs.
  - Without it the census is **OVER by 226** (30,006). With it: **28,745, +1,035**.

## Gates (`GATES_PUBLOG3.txt`, `MESEN_PUBLOG3.txt`)
- **Negative controls:** every shipped / staged cart rebuilds identically, as do capture #1's 8355ddc7 and capture #2's
  d84436ff / 9841ba14. T 27 explicit = the default build.
- **NMI census:** capture #2 cart 29,672 (+108); capture #3 without hold-first 30,006 (OVER); **capture #3 28,745 (+1,035)**.
- `run_cart_gates.sh`: ALL PASS.
- **Gravity fidelity** (seeds 5/11/23, 3000 frames each):
  - cvcp2_c3 PASS with 0 dead-pill uploads (an abort arm);
  - cvcp2_pump and cvc_fair_abort PASS;
  - couch_464a4b75 KILLED.
- **lgcut** on the capture #3 overlay: PASS, 5 mutants killed.
- **`test_publog --pdw`** on the capture #3 flags:
  - RING 110 GOs exact (13 prestart);
  - LIVE, DONE, LOCK and ZP PASS;
  - PDW: 8/8 single-read and 5/5 frame-long false DONEs caught, 0 flags on genuine DONEs.
- **`test_gpump`**, new checks:
  - **DRAIN:** $0398 seeded at 7 before every hook reads 0 after every play hook.
  - **NOPLAY:** the escape is primed to fire. It must not inject in a live round, and must inject in a round-end wait
    (the positive control).
  - Mutants M_nodrain and M_escplay are KILLED; M_overwrite and M_nohold are still killed.
- **Mesen**, free-running 36,000 frames, stand-in brain:
  - 22 rounds, P1 held throughout;
  - deliveries == releases == GP_N (25), 3.14 per play-minute;
  - **$0398 at most 2, nonzero on only 2 frames** (transient within a frame);
  - **0 escape presses inside a live round**;
  - the ring decodes 25 consecutive pills with no gaps.

## Kit
`dr_mario_rl/tmp/couch_kit/publog3_20261007/`:
- cart 437cd6aa;
- **V11 seed-3 rbf 43aa62d5, which must be installed on bluemage**;
- `PUBLOG3_V11.mgl` de943c99;
- BUILD.md with the install, load, verify, capture and offline-on-V11 steps.
