# PREREG STEER11 (2026-10-06): confirm the s10_A16 near-miss on a couch-calibrated race clock

- **Lane:** steersim. **Tree:** h16-wt `experiments/cvx`, branch h16-rollout-gated.
- **Two-stage registration (both before any confirmation game):**
  - **Stage A (this commit):** the whole design and the n RULE, in code (`steer11_sizing.py`, selftest PASS). It is
    committed while the step-1 pilot farm is running and before anyone has analysed it (`steer11/pilot.txt` does not
    exist; the commit message records the pilot row count).
  - **Stage B (a later commit):** the n that the rule outputs on the finished pilot, the pilot's FAIR levels, and the
    `CONFIRM` block in `steer11_jobs.py`. Stage B may change NOTHING else. `steer11/confirm/` holds 0 rows at stage B.

## 1. Question
STEER10 (`RESULT_STEER10.md`, prereg b6194e29) found `s10_A16` (DIST60's dist_target term switched on at ≤ 16 viruses
instead of ≤ 4) a near-miss vs FAIR:
- LULU race +1.35 pp [+0.02, +2.71] raw, Bonferroni [−0.38, +3.06] (4 arms) → FAIL on power.
- The mechanism showed: stall-pills from ≤ 16 viruses −28%, longest stall −6.3 s, LULU tap-out −1.83 pp.

The race clock used there charged 0 s for received garbage and undercharged clears. **Does A16 beat FAIR in the LULU
race on a clock that matches the couch?** Single arm, so no arm-multiplicity correction on the primary.

## 2. The clock (`couch11`, STEER11 step 1, commit cb842760)
- **Fit:** `steer11_clockcal.py`, from 19 couch games / 2,128 AI inter-spawn intervals.
  - 10/04: the owner vs FAIR / FAIR2, 10 games.
  - 10/05: dr. lulu vs FAIR, 9 games.
  - The table is banked: `steer11/clockcal_pills.jsonl`.
- **Model M4** (NES frames), refitted on all 19 games → `steer11/clock_couch11.json`:

  | term | frames |
  |---|---|
  | per pill | 33.3 |
  | per drop row (`15 − hmax`) | + 3.1 |
  | per clear step | + 20.2 |
  | per cascade gravity fall row | + 15.9 |
  | per RELEASED volley | 17.4 |
  | per garbage fall row | + 16.9 |
  | if the garbage sets off a clear | + 44.1 |

  The two gravity rates were fitted independently and agree.
- **Legacy clock:** 39 + 2 × drop + 40 × steps, garbage 0.
  - It undercharges couch game totals by 23% (leave-one-game-out).
  - M4's LOGO game-total mean |error| is 3.1%.
- **Hold-out validation** (fit on the 15 other games, predict the 4 10/05 AI clear games):
  - median 210.8 s vs observed 209.2 s, per-game mean |residual| 1.7 s;
  - the legacy clock gives 157.0 s.
- **Implementation** (`vs_race.pill_frames` / `garbage_drop_timed`, selected by `vs_race.CLOCK`; None = legacy).
  - **Identity:** with the legacy clock the patched code reproduces the banked STEER10 / STEER8 FAIR and A16 rows
    byte-identically (17/17 gate rows), and the positive control differs (`steer11_identity.py`).
  - **Clock tests** (`steer11_clocktest.py`):
    - sim feature code == calibration feature code (190/190 + 1,138/1,138 cascades, 30/30 garbage drops);
    - t_end == Σ traced charges;
    - 0 formula mismatches.
  - Sim FAIR on couch11 runs at 1.72–1.93 s/pill; the couch was 1.74.
- **Validity scope:** the clock is fitted on FAIR-timing silicon, and `steer11_run.py` asserts FAIR's tempo (−6).
  Both arms here use the FAIR driver/timing; A16 changes only a firmware gate constant.

## 3. Arms (`steer11_run.py` → `steer10_run.make` VERBATIM)
| arm | what |
|---|---|
| **FAIR** = `s10_base` | STEER8b `fD_bdepD`: silicon-faithful brain, DIST60 (dist_target W60 vk 4), FAIR driver / timing |
| **A16** = `s10_A16` | the same, with the dist_target gate vk 4 → 16 (W 60, min-D target) |

## 4. Instruments, seeds, n
- **Seeds:** the CONFIRMATION block is even seeds from **41100**, step 2, n seeds (stage B), the same seeds for all
  three instruments. That makes the block 41100 … 41100 + 2(n − 1), at most 41100–49098.
  - **Declared REUSE.** The seed registry is exhausted (51 free streams). This range is registry "champ145 reserve"
    (41100–50099) and, inside it, "gwprice" (42000–45998): other lanes' L20 rigs.
  - It is **DISJOINT from every STEER10 seed** (lulu10b / gate b 39134–40932 + 33000–33598, owner race 39134–40332),
    the block that generated the A16 hypothesis.
  - No registry REUSE note records any steersim STEER use of it.
  - A REUSE note is added to the registry entry at launch.
- **Instruments.** Each runs on both arms, n seeds, 50-game jobs, arms interleaved per block.

  | cell | what | clock |
  |---|---|---|
  | `lulu11` | LULU race: lam 2.84, lulu_fit_202610b sizes (`steer10_run.SIZES["lulu202610b"]`) | couch11 |
  | `gb11` | gate b vs owner202610 (owner_fit_202610) | none: its garbage is keyed on PILLS; rows identical under any clock |
  | `rc11` | owner race: lam 2.36, Hartford sizes | couch11 |

- **Games:** 6 × n (≤ 24,000).
- **Stopping rule:** data-independent. Every pre-registered job runs to completion (farm audit: every job 50 rows).
  - `analyze_steer11.py confirm` WITHHOLDS every arm contrast until all 3 × 2 × n rows exist (R97).
  - No interim look.

## 5. n (rule in `steer11_sizing.py`, selftest PASS, applied at stage B)
**Pilot (step 1):** s10_base + s10_A16 on couch11 on the STEER10 LULU block, 1,200 seeds (plus the owner race, 600).
It is the hypothesis-generating block, so it is **not confirmatory**. It only sizes the confirmation and gives FAIR's
absolute couch11 levels.

**Rule:**
- `r = clamp(d_new / d_old, 0.5, 1)`.
  - `d_new` = the pilot's A16 − FAIR pace-prior delta on couch11.
  - `d_old` = the same seeds on the legacy clock (+1.35).
- `delta = 1.35 × r`.
- `n85 = ((1.96 + 1.036) × sd_new / delta)²`, which is 85% power at two-sided 5%.
- `n = clamp(ceil50(n85), 2400, 4000)`.

**If `n85` > 4,000:** n = 4,000. The run is declared UNDERPOWERED BY DESIGN at stage B, with its power at delta
printed. It still runs, and it is read under rule 13: underpowered ≠ negative.

**Also printed:** power at 0.7 × delta. A16 was the best of 4 STEER10 arms, so some winner's-curse shrink is expected.
It is not used by the rule.

## 6. Endpoints
**PRIMARY:** `lulu11` LULU race WIN averaged over her pace prior M ∈ {80, 100, 120, 140} s.
- δ 2.65 s per tile, σ 0.15, `vs_race.evaluate`.
- Per seed, it is the mean of the four win indicators, each M using the same per-seed pace quantile.
- Measure: A16 − FAIR, paired, seed bootstrap (4,000).
- **Pass:** lower bound of the two-sided 95% CI > 0.

**GUARDS:** no DEMONSTRATED harm, Bonferroni over the 3-guard family, i.e. two-sided 98.33% (percentiles
0.833 / 99.167).

| guard | measure | harm iff |
|---|---|---|
| G1 | `gb11` gate-b tap-out | Bonferroni lower > 0 |
| G2 | `gb11` gate-b tap-out within 100 pills (tap≤100) | Bonferroni lower > 0 |
| G3 | `rc11` owner race win at M 177, δ 2.65 | Bonferroni upper < 0 |

**VERDICT:**
- **PASS** iff PRIMARY lower95 > 0 AND none of G1–G3 shows harm.
- **FAIL** otherwise.
- **incomplete** if any instrument has fewer than n paired seeds.
- Encoded in `analyze_steer11.verdict`. The killed-mutant selftest PASSES: 10 synthetic cases on both sides of every
  threshold, and 7 mutants killed:
  - primary on the mean;
  - primary on the upper CI;
  - each guard dropped;
  - the race guard sign flipped;
  - guards as non-inferiority at 0.

**SECONDARY (reported, not the bar):**
- **LULU win at each M**, with churn (fixed / new).
- **FAIR and A16 absolute levels on couch11:** win, loss = slow + kill, time to clear, s/pill, garbage time.
- **LOSS-TYPE split** per M (slow = alive but later than her, or capped; kill = topped out first), FAIR → A16 with
  fixed / new.
- **LULU-race tap-out.**
- **STALL metrics** (stuck probe), LULU and gate b:
  - stall-pills (act ≥ 10) from ≤ 16 viruses and from ≤ 4;
  - longest stall in pills and in seconds;
  - edge-virus structural-stuck decisions;
  - games with a stall ≥ 36 s.
- **A16 rule activity** (dist term on, target differs).
- A STEER10-comparable post-hoc +3.2 s/release charge on top of couch11. It is labelled double-counting and shown
  only for comparability.

## 7. Prior expectations, written down before the data
- **G2 (tap≤100) is the most likely guard to fire.**
  - STEER10 measured +0.50 pp [+0.17, +0.92] at n = 1,200 (the term turns on early in games that reach 16 viruses
    fast). gate b does not depend on the clock.
  - If that effect is real, a block of n ≥ 2,400 shows it at the Bonferroni level with high probability (SE ≈ 0.13 pp
    at n = 2,850), and A16 FAILS on G2 even if the primary passes.
  - This is the pre-registered bar, and it is stated here so that it cannot be argued away afterwards.
- **The primary may shrink on couch11.** The STEER10 post-hoc +3.2 s/release charge moved A16's delta from +1.35 to
  +0.42. The pilot measures the in-sim effect on the same seeds.

## 8. Null-outcome audit (pass-condition-vs-null-outcomes)
- **Under the null** (A16 ≡ FAIR):
  - The primary passes with probability 2.5% (one-sided).
  - Each guard "shows harm" with probability ≤ 0.83%, so ≤ 2.5% for the family.
  - No outcome the null PREDICTS (a null delta, a guard CI straddling 0) is treated as failure evidence beyond the
    primary's own bar.
- **Guards are "no demonstrated harm", not non-inferiority.** A guard that straddles 0 passes. At these n a real
  +0.5 pp tap≤100 harm is detectable, and that is intended.
- **Clauses read against each other:**
  - "incomplete" can only arise from missing rows, never from a value.
  - The withheld contrast and the fixed stop make the stopping rule independent of the data.

## 9. Deviations
Any deviation is reported in the result next to the number it affects. That includes:
- a crashed job re-run with the same seeds;
- a PAUSE window;
- a code change after stage B. A code change voids the run unless it is identity-gated against stage-B rows.

## STAGE B (2026-10-06, after the pilot, before any confirmation game)
**Rule output** (`steer11_sizing.py` → `steer11/sizing.txt`, the stage-A rule unchanged except a JSON-serialisation
fix of its output line):

| quantity | value |
|---|---|
| d_old (legacy clock, STEER10 block) | +1.354 pp |
| d_new (couch11, same seeds) | **−1.229 pp** |
| sd_new | 24.21 pp |
| r (floored) | 0.5 |
| design delta | 0.675 pp |
| n85 | 11,547 |
| **n** | **4,000** seeds per instrument per arm (24,000 games) |
| power at delta | 0.42 |
| power at 0.7 × delta | 0.23 |

- The run is **UNDERPOWERED BY DESIGN**.
- **Block:** `steer11_jobs.CONFIRM = {"lo": 41100, "n": 4000}`, i.e. even seeds 41100–49098, 4,000 distinct streams.
  - Disjoint from every STEER10 seed (stream keys 20550–24549 vs 16500–16799 / 19567–20466).
  - REUSE notes were added to the registry's "champ145 reserve" and "gwprice" entries.
- **Rows at this commit:** steer11/confirm holds 0 rows; steer11/pilot holds 3,600 (audit OK).

**Pilot, FAIR absolute levels** (STEER10 blocks; `steer11/pilot.txt`):

| | legacy clock | couch11 |
|---|---|---|
| LULU pace-prior win | 87.00% | **40.46%** |
| loss, slow / kill | | 55.56 / 3.98 |
| win at M 80 / 100 / 120 / 140 | | 13.3 / 32.4 / 51.1 / 65.0% |
| time to clear (median) | 147.4 s | **208.4 s** (couch 209) |
| s/pill | | 1.81 (couch 1.74) |
| owner race M 177 | 93.50% | **83.83%** |

**DISCLOSED: the pilot's A16 − FAIR contrast was computed and seen before this commit.** Stage A allows this: the pilot
is the sizing input.

| | value |
|---|---|
| A16 − FAIR, couch11, same 1,200 seeds | −1.23 [−2.58, +0.19] |
| at M 80 | −3.00 |
| at M 140 | +0.83 |
| stall-pills from ≤ 16 viruses | −5.7 |
| LULU tap-out | −2.75 |

It changes NOTHING in sections 1–9: primary, guards, verdict and seeds are as committed at stage A (5afb7816).

**DISCLOSED VALIDITY NOTE, not acted on here.** The pace prior M ∈ {80..140} was set in STEER10 to make races
"couch-shaped" on the too-fast legacy clock.
- On couch11, FAIR wins 13% at M 80 but 65% at M 140. The couch result was 6/9 (67%).
- So on the corrected clock the fast end of the prior describes an opponent much faster than the couch dr. lulu.
- Re-deriving M belongs to a FUTURE prereg, and from FAIR-only levels: never from an arm contrast, which has now been
  seen at every M. The pre-registered primary stays as committed. Per-M results are pre-registered secondaries.

## ABANDONED BEFORE ANALYSIS (2026-10-06 16:14:54Z)
- **Launched** 16:04Z at git 0b79f3d8. **Stopped** on the coordinator's priority ruling: the same-seed pilot was
  negative on couch11 (−1.23), and power at the design effect was 0.42.
- **Partial rows** are banked untouched in `steer11/confirm/` (663 rows, 16 files):

  | cell | FAIR rows | A16 rows |
  |---|---|---|
  | lulu11 | 132 | 113 |
  | gb11 | 132 | 85 |
  | rc11 | 116 | 85 |

  Only these counts were read.
- **No verdict exists.** `analyze_steer11.py confirm` refuses to run.
- A16 is parked. See RESULT_STEER11.md.
