# RESULT (2026-10-03): STEER6r — DIST60's gain SURVIVES at half the garbage (PREREG_STEER6r.md `6da47f12`)

**Setup:**
- **Cells (the corrected 2026-10 send fits):**
  - gate (b) `owner202610`: 2.36 volleys/min, placement-clocked;
  - race vs the owner: lam 2.36, M 177, δ 2.65;
  - LULU race: lam 2.56, M 140.
- **Seeds:** the STEER6b confirm block, declared reuse. gb10 1,500 seeds for DIST60 and ANTIBODY, and 600 for
  TAP-only; races 600.
- **Brain and latency:** the python brain (`Leaf6Decider` family) at nominal latency.
- **Scale and analysis:** 7,200 games; audit 7,200/7,200 (with the STEER7 secondary 10,800/10,800). `analyze_steer6r.py`
  → `steer6r/analysis.txt`.

**Identity:** `steer6r_run.py` with the old opponents reproduces the banked steer6/measure and steer6/opp rows (6/6
smoke).

## PRIMARY: DIST60 vs ANTIBODY → **GAIN SURVIVES**

| cell | ANTIBODY → DIST60 | Δ [95%] | churn (fixed / new) |
|---|---|---|---|
| gb10 tap-out (n = 1,500) | 8.93% → **5.13%** | **−3.80 [−5.00, −2.73]** | 67 / 10 |
| race M177 (n = 600) | 87.50% → 91.33% | **+3.83 [+2.17, +5.67]** | 27 / 4 |
| LULU M140 (n = 600) | 83.83% → 90.67% | **+6.83 [+4.67, +9.17]** | 46 / 5 |

- tap≤100: Δ +0.00.
- The race gain itself also survives on both races (lower CI > 0).
- **The churn is clean:** 67 tap-outs fixed for 10 new.

## Old vs new garbage, on identical seeds (n = 1,500 gate b; 600 race)

| | OWNER-0804 / lam 6 | owner202610 / lam 2.36 |
|---|---|---|
| ANTIBODY gate-b tap-out | 25.40% (66.6 garbage cells/game) | **8.93%** (19.8) |
| DIST60 gate-b tap-out | 20.00% (57.7) | **5.13%** (16.1) |
| DIST60 − ANTIBODY tap-out | −5.40 [−7.00, −3.80] | **−3.80 [−5.00, −2.73]** (DiD +1.60 [−0.40, +3.53], n.s.) |
| ANTIBODY race win M177 | 69.17% | 87.50% |
| DIST60 − ANTIBODY race | +8.50 [+5.83, +11.33] | +3.83 [+2.17, +5.67] |
| ANTIBODY race-row tap-out | 30.17% | 11.67% |

**LULU, old:** lam 4.7, on the SCREEN block (a different seed block): +12.5. **New:** lam 2.56 on these seeds: +6.83.

**Reading:**
- **Absolute levels fall about 3×.** At couch-realistic garbage, ANTIBODY taps out in ~9% of gate-(b) games, not
  25%.
- **DIST60's absolute gain shrinks** from −5.4 to −3.8 pp. Its RELATIVE cut grows from 21% to 43% of tap-outs.
- **It still clears the bar decisively,** and it wins both races.

**Secondary vs the 9/26 TAP-only build** (600; Bonferroni 97.5% also printed):

| comparison | tap-out Δ [95%] | race Δ [95%] | LULU Δ [95%] |
|---|---|---|---|
| DIST60 − TAP | **−5.00 [−7.67, −2.33]** | +7.00 [+3.83, +10.50] | +7.67 [+4.17, +11.17] |
| ANTIBODY − TAP | −1.17 [−4.17, +1.83] | +3.17 [−0.33, +7.00] | +0.83 [−2.83, +4.50] |

The HSV step alone (ANTIBODY − TAP) is not significant under realistic garbage. DIST60 carries the gain.

**Caveats:**
- **Brain gap:** this is the PYTHON brain, which picks differently from silicon on ~5% of decisions
  (braingap 87ba445b). STEER8a re-runs both arms on the silicon-faithful brain on these exact seeds.
- **Column model:** the opponent column model is unchanged (2-cell sends in one column 23% of the time; the refit
  says always 4 apart).
- **LULU fit:** provisional, n = 2 games.
