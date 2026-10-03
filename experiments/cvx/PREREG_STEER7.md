# PREREG (2026-10-03): STEER7 — what is a FASTER answer worth?

Written and committed BEFORE any STEER7 game (see "Data state at commit" at the end).

## 1. Question
STEER6c priced answer latency in the SLOWER direction: +1 frame on every decision cost dist_target60
**+2.67 pp tap-out [+0.33, +5.00]** (`steer6/dlat/analysis.txt`). The owner's #1 metric is AI tap-outs. Before anyone
spends engineering on cutting copro answer time, measure the other direction:
- Is the relation symmetric? Does −1 f buy ≈ −2.7 pp tap-out?
- What is the worth-per-frame curve, so an engineer can price any speedup (+1, 0, −1, −2, −4, zero-latency)?

## 2. Brain and latency model
**Brain:** `s6_dist_target60` (ANTIBODY + dist_target60, the couch build), steering-faithful sim (`steer_model`,
unified DRTAPP=2 tap steering, reach_fw_tap mask, PROPH throat).

**Baseline latency (S = 0):** exactly STEER6d "full" (`steer6_dlat_dist.py`): on every ACTIVE decision (root
viruses ≤ 4), a per-board delta from the 437 measured DRDIST-vs-ANTIBODY co-sim deltas, stochastically rounded.

**Wrapper:** `steer7_dlat.py`. A constant shift S frames is added on EVERY decision: D = S + d_active. It moves the
same four channels STEER6c/6d moved:

| channel | value | clamp |
|---|---|---|
| steer answer frame (first driver action) | x + D (x = sampled silicon latency, n = 384, median 19) | **≥ F0 = 3**, the first frame the ROM processes input (the physical minimum) |
| reach mask T_LAT (the firmware's matched constant) | 19 + D | ≥ F0 + 1 (STEER6d's clamp; never binds for S ≥ −4) |
| vs_race BASE_F (tempo per ply, no overlap credit) | 45 + D | unclamped (as STEER6c/6d) |
| gate-(b) clock | 0.6 s + D / 60.0988 | unclamped |

**Zero-latency ceiling (S = "ceil"):** the answer is available at spawn on EVERY decision. The steer answer frame is
F0 = 3 and the mask T_LAT is 3. Tempo and clock shift by F0 − mean(x) = **−16.25 f** on every decision. The measured
endgame delta does not apply, because the answer is free. Note that the ceiling also removes the pre-answer PROPH window
(PROPH only pulses before the answer). That is part of what "zero latency" means for this driver.

**Clamp accounting.** The silicon latency sample has 14 / 384 (3.6%) values at 4–6 f. Those are the fast answers,
presumably prestart hits. So the steer clamp binds for those at S = −2 / −4, and more often on active decisions whose
measured delta is negative.
- The tempo channel is unclamped, as in STEER6d (required for exact S = 0 identity). It therefore over-credits
  F0 − (x + D) frames on clamped decisions.
- Both the clamp rate and the over-credit (f/decision) are logged per game and reported per arm.
- Measured on the G3 games at S = −4: the clamp bound on 2.2–4.3% of decisions, with an over-credit of 0.07–0.11
  f/decision.

## 3. Arms, cells, seeds (declared reuse, no fresh streams; the seed space is exhausted)
**Arms:** S ∈ {**+1, 0, −1, −2, −4**, **ceil**}.

**Cells** (as STEER6d):

| cell | opponent / setting |
|---|---|
| (gb) gate (b) whole-game | OWNER-0804 |
| (rc6) race lam 6 | M 177 s human, δ 2.65 s/tile (fitted) |
| (rc47) dr. lulu racer | lam 4.7, M 140, δ 2.65 |

**Seeds:**
- **Block A** = the STEER6 screen block 37934–39132 step 2 (600). All 6 arms × 3 cells. Identical to STEER6d, so the
  S = 0 rows must reproduce the banked `steer6/d6/*_full_*` rows.
- **Block B** = 39134–40332 step 2 (600). These are the first 600 seeds of the STEER6b holdout block, already
  consumed, so this is declared reuse. Only S ∈ {0, −1} × {gb, rc6}, to power the primary.
- **Totals:** 6 × 3 × 600 + 2 × 2 × 600 = **13,200 games**. Jobs of 50 seeds.

## 4. PRIMARY BAR (one comparison: S = −1 vs S = 0, blocks A + B, n = 1,200 paired)
**PASS iff BOTH hold:**
1. gate-(b) whole-game tap-out Δ, **upper 95% seed-bootstrap CI < 0** (a cut whose CI excludes 0); AND
2. **no race loss:** race (lam 6, M 177, δ 2.65) win Δ **upper 95% CI ≥ 0**. That is, the race is not demonstrably
   worse.

Otherwise FAIL. It is "incomplete" if either n < 1,200.

**Multiplicity:** a single pre-specified primary comparison. The two conditions are combined by AND
(intersection-union test, level α without adjustment).

**Pass-condition audit** ([[pass-condition-vs-null-outcomes]]):
- The coordinator's suggested "no race loss" could be read as STEER6c's non-inferiority margin, race lower CI ≥ −2 pp.
  **That margin is rejected here.**
- STEER6c measured the race discordance of a whole-game 1-frame shift: latency-cost race CI ±4.4 pp at n = 600, i.e.
  ~31% of race seeds flip.
- At n = 1,200 the race SE is ≈ 1.6 pp. Under a NULL race effect the lower CI sits near −3.1 pp, so the −2 margin
  would **fail the null's own modal outcome ~75% of the time**.
- The guard as written fails a null race outcome 2.5% of the time.
- tap≤100 has no bar for the same reason, since the shift acts on early decisions too. It is reported.

**Power** (SE from STEER6c's latency-cost CI: tap-out SE 1.19 pp at n = 600 → 0.84 at n = 1,200):

| true effect of −1 f | power |
|---|---|
| −2.67 pp (symmetric) | ≈ **89%** |
| −1.33 pp (half the size) | ≈ 35% |

Block A alone (n = 600) would give only ≈ 61%. That is why block B exists.

`analyze_steer7.py --selftest` drives the verdict function with 7 synthetic tables on both sides of every threshold
(including a null race outcome that must PASS, and a CI-spanning tap-out cut that must FAIL). It kills 6 mutants of
the rule (tap lower-CI, tap mean, race guard dropped, the rejected −2 margin, race mean, race lower-CI): **SELFTEST
PASS** before any data.

## 5. Secondary / descriptive (block A, n = 600 per arm, paired vs S = 0)
- **Per arm:** gate-(b) tap-out Δ, tap≤100 Δ, race M177 Δ, LULU M140 Δ, and race-row / LULU-row tap-out Δ, all with
  95% CIs, and with churn (fixed / new) beside EVERY net Δ.
- Arms +1, −2, −4 and ceil are 4 secondary arms. Any significance statement on them uses **Bonferroni 98.75%** CIs
  (also printed).
- **Worth-per-frame curve:** Δ vs the REALISED mean change in answer frame per decision (from the per-game activity
  counters, so clamps are included).
- **Slope** (pp per frame): OLS over arm means with a joint seed bootstrap. Fit over all integer arms (+1..−4) and over
  the faster side only (0..−4).
- **Symmetry statistic:** Δ(+1) + Δ(−1), paired per seed. Its CI spanning 0 means no detectable asymmetry.
- **Reference point:** the banked STEER6c +1 f (nominal latency, not the measured distribution): +2.67 [+0.33, +5.00].

## 6. Gates run BEFORE any data (all pass)
**G1, identity.** S = 0 in `steer7_dlat.py` equals the banked STEER6d "full" rows, every key:
- gb 2/2 and rc6 2/2 on smoke (seeds 37934 and 37936).
- All 1,800 block-A S = 0 rows are re-checked in the analysis. The result must be EXACT, or nothing is read.

**G2, mask validity at the shifted constants.** reach_fw_tap was validated only at T_LAT = 19.
`steer7_mask_validate.py` compared it with the unified-tap frame simulator (strict, answer at the same frame).
- Scope: 522 boards × 32 candidates each, at T_LAT ∈ {3, 7, 11, 15, 17, 18, 19, 20}.
- Result: **100.000% agreement at every T, 0 mismatches.**
- The mask is live: it allows 29.00 candidates per board at T 3 and 27.69 at T 20. So a T-mismatched comparison
  (e.g. mask at 19 vs simulator at 3) would disagree on ≥ 1.18 candidates per board. The checker can fail.

**G3, activity instrument.** The wrapper's replicated steer sample, max(F0, x + D), equals the steer model's own
realised t_act on every decision.
- Covered 10/10 race games: S = 0, −4, −12, ceil, +1 × 2 seeds.
- The mask counter saw T_LAT 19 / 15 / 3 / 20 as intended.

**G4, verdict selftest.** PASS (section 4).

## 7. Readings declared now
- **PASS.** A faster answer buys tap-outs, and copro answer time is a lever worth engineering. The slope prices any
  speedup, and section 2 of the result ranks the candidates.
- **FAIL, with the tap-out point estimate negative but the CI spanning 0.** The −1 f effect is smaller than the +1 f
  cost (asymmetric) or below this n's resolution. Read the −2 / −4 / ceil arms: the lever may exist only at larger
  sizes, which changes which speedups are worth building. This is NOT "latency doesn't matter".
- **FAIL, with the tap-out effect ≥ 0.** Faster is not better in this sim. Cutting latency is not a tap-out lever.
  STEER6c's cost stands as a one-sided penalty: do not slow down, but do not invest in speeding up.
- **Race significantly worse at −1 f.** This is unexpected, because tempo can only help. Investigate the mask /
  PROPH path before any reading.

## 8. Execution
**Where:** local only, under one transient systemd user service (`steer7-farm`).
- MemoryMax 20G, MemorySwapMax 0.
- Every job runs under `nice -n 19`.
- **12 workers** (half of 24 cores). Two other agents share the box.
- A fresh NUMBA_CACHE_DIR per arm (`tmp/steer7/numba_<arm>`), against the stale-cache trap.

**Job order:** primary first (S 0 / −1 on blocks A + B: gb, rc6), then rc47 0 / −1, then −2, −4, ceil, +1.

**Resume and stamping:** a job whose output already has 50 rows is skipped. Every row carries the wrapper sha256, the
git HEAD and its activity counters.

**Completion audit:** 264 files × 50 rows = 13,200 rows. Anything short is FATAL. Only then is `analyze_steer7.py` run,
writing to `steer7/analysis.txt`.

## Data state at commit
- `steer7/A/` and `steer7/B/` do not exist; there are 0 STEER7 result rows.
- The only STEER7-wrapper games played so far are gate checks:
  - `steer7/smoke/` (2 gb + 2 rc6 games at S = 0, the identity check);
  - G3's 10 race games, on seeds 37936 and 38000 at S ∈ {0, −4, −12, ceil, +1}, whose outcomes were printed (n = 2
    per arm, not used in any analysis).
