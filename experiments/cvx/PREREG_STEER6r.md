# PREREG (2026-10-03): STEER6r — does DIST60's gain survive at HALF the incoming garbage?

Written and committed BEFORE any STEER6r game (see "Data state at commit").

## 1. Why
A couch tracker bug read same-colour consecutive spawns as garbage volleys (`couch_forensics/RESULT_SENDS_REFIT_202610.md`).
The opponent send fits behind every STEER6 opponent number are therefore inflated:

| player | old fit (202609) | corrected fit (202610) | sizes, corrected |
|---|---|---|---|
| owner | 4.87 volleys/min | **2.36** | 89/8/3% |
| dr. lulu | 4.73 | **2.56** (provisional, n = 2 games) | 77/13/10% |

- The VS-race instrument (lam 6) is about 2.5× the owner, not "+23%".
- DIST60 (`s6_dist_target60`, ANTIBODY + dist_target60) was CONFIRMED on OWNER-0804 / lam 6 (STEER6b): tap-out
  25.4 → 20.0%, race +6.6.
- **Question:** does its tap-out/race gain over ANTIBODY survive under the corrected, roughly halved, garbage?

## 2. Arms (nominal answer latency; unified DRTAPP=2 steering; reach_fw_tap mask)

| arm | what it is |
|---|---|
| **DIST60** `s6_dist_target60` | the candidate. STEER6d priced its measured latency at −0.17 [−1.67, +1.33] tap-out, so nominal is the brain comparison. |
| **ANTIBODY** `s5b_hsv512` | the baseline, = Leaf6 mode off. |
| **TAP-only** `s4_base` | the 9/26 CHAIN540 + REACH + TAP build (no HSV). Secondary reference. |

## 3. Cells (corrected fits; runner `steer6r_run.py` = the stuck_probe code path; opponents via `refit_opp.py`)

| cell | setting |
|---|---|
| (gb10) gate (b) | opponent `owner202610` = the Owner202609 class on `owner_fit_202610.json` |
| (rc10) race vs the owner | lam **2.36**, M 177, δ 2.65 s/tile |
| (lulu10) LULU race | lam **2.56**, M 140, δ 2.65 |

**Known residual:** only gaps / size pmf / p_double come from the fit. The 2-cell COLUMN model is unchanged (23%
same column); the refit says always 4 apart.

## 4. Seeds (declared reuse; the seed space is exhausted)
- **gb10, DIST60 and ANTIBODY:** the full STEER6b confirm gate-(b) block, **1,500** seeds (39134–40932 + 33000–34198,
  step 2). Banked OWNER-0804 rows exist for both arms on exactly these seeds (`steer5d/`, `steer6/holdout/`), so the
  old-vs-new levels are on identical seeds.
- **gb10 TAP-only, and every race cell:** the first 600 of that block (39134–40332). These are the same seeds as
  STEER7 block B.
- **Totals:** gb 1,500 + 1,500 + 600; rc10 3 × 600; lulu10 3 × 600 = **7,200 games**.
- **Power** (gb10, n = 1,500): discordance is assumed to halve with the base rate (≈ 6%), giving SE ≈ 0.63 pp.

| true effect | power |
|---|---|
| −2.5 pp (relative effect held at half the base) | ≈ 98% |
| −1.25 pp | ≈ 50% |

## 5. PRIMARY BAR: DIST60 vs ANTIBODY, paired, 95% seed-bootstrap CIs
**GAIN SURVIVES iff all hold:**
1. gb10 tap-out Δ **upper CI < 0**;
2. rc10 race-win Δ **upper CI ≥ 0** (no demonstrated race loss);
3. lulu10 race-win Δ **upper CI ≥ 0** (no demonstrated race loss).

**Pass-condition audit:** under the null of no race effect, each race guard false-fails 2.5%. The −2 pp lower-CI
margin used in STEER6 would fail a null outcome ~50% of the time at brain-vs-brain race discordance (CI ±2.7 at
n = 600), so it is not used.

**Also stated:**
- **RACE GAIN SURVIVES** iff the rc10 lower CI > 0 (and the same for lulu10). These are descriptive.
- tap≤100 is reported. DIST is off above 4 viruses, so it should be ≈ 0.

**Multiplicity:** one primary comparison. Its 3 conditions are combined by AND (intersection-union test, no
adjustment). The 2 secondary comparisons (DIST60 vs TAP-only, ANTIBODY vs TAP-only) get 95% CIs plus Bonferroni
97.5%.

**Churn** (fixed / new) is printed beside every net Δ.

**Verdict code:** `analyze_steer6r.py`. `--selftest` kills mutants of the rule on synthetic tables before any data.

## 6. Also reported (the coordinator's ask)
**Absolute tap-out levels, old vs new, on identical seeds:**
- ANTIBODY and DIST60 under OWNER-0804 (banked) vs owner202610.
- The old Δ (−5.40 on these seeds) vs the new Δ, with a paired difference-in-differences CI.
- The old race Δ (lam 6) vs the new Δ (lam 2.36) on the 600 race seeds.
- LULU: the old screen-block number (lam 4.7, a different seed block, labelled as such) vs the new one.

**Couch context** (coordinator, not sim data):
- 9/27 ANTIBODY: 0 AI tap-outs in 9 games vs the owner.
- 10/03 ANTIBODY_DIST: 1 in 4 (G2, at 10 viruses left). Forensics attributes it to EXECUTION (late flips).

## 7. Readings declared now
- **SURVIVES:** DIST60 stays the candidate under realistic garbage. The size of the gain is reported, not assumed.
- **Tap-out CI spans 0 but the point estimate is < 0:** the gain shrinks with the garbage. DIST60 is not shown
  better at couch-realistic pressure, though it is not shown worse either. The ship decision falls back to the
  race endpoints and the couch.
- **A race guard fails:** DIST60 costs race at realistic garbage. Investigate before shipping.

## Identity gates before launch (2 + 2 smoke games each)
- `steer6r_run.py` with owner0804 / lam 4.7 reproduces the banked rows:
  - `steer6/measure` gb s5b_hsv512;
  - `steer6/opp` rc47 s6_dist_target60;
  - `steer6/measure` rc47 s5b_hsv512.
- The owner202610 opponent runs and delivers less garbage per game than OWNER-0804 on the same seeds.

## Execution
- Local, `nice -n 19`, 12 workers, MemoryMax 20G.
- Queued by `steer7b_farm.sh` after the STEER7 primary farm and the STEER7 secondary.
- Fresh NUMBA_CACHE_DIR per arm.
- Completion audit: 144 files × 50 rows.

## Data state at commit
`steer6r/` holds only `smoke/` identity rows (≤ 2 seeds per arm/cell). There are 0 STEER6r result rows.
