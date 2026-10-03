# RESULT (2026-10-03): STEER8 — the SILICON-FAITHFUL brain under the corrected send fits

**Preregs:**
- STEER8a (`94a7f82e`).
- STEER8b (`94a7f82e`), amended `efc32b32` and `a77f0ecd`. Both amendments were made before any 8b game.

**Brain:** `experiments/braingap` `Leaf6FwDecider` with every switch on. Its per-root V1 equals py65 on 9,689/9,689
roots, and its finals equal the co-sim on 326/326.

**Cells:** owner202610 gate (b); race lam 2.36, M 177; LULU lam 2.56, M 140; all at δ 2.65.

**Seeds:** STEER6r's (gb10 1,500, races 600; declared reuse).

**Runner:** `steer8_run.py`.

## STEER8a (5,400 games; audit 5,400/5,400; `steer8/analysis_8a.txt`)
**Identity:** with every switch off, the runner reproduces the banked python rows: 8/8 smoke, plus re-checks after
every model edit.

### Block 1 (descriptive): how far did the brain gap move the levels? Faithful − python, paired, same seeds

| cell | ANTIBODY: python → faithful | Δ [95%] | churn | DIST60: python → faithful | Δ [95%] | churn |
|---|---|---|---|---|---|---|
| gb10 tap-out (n = 1,500) | 8.93 → 9.47% | +0.53 [−1.27, +2.40] | 91/99 | 5.13 → **6.87%** | **+1.73 [+0.27, +3.20]** | 55/81 |
| race M177 | 87.50 → 86.17% | −1.33 [−4.67, +2.00] | 48/56 | 91.33 → 91.50% | +0.17 [−2.67, +3.00] | 37/36 |
| LULU M140 | 83.83 → 83.17% | −0.67 [−4.17, +3.00] | 58/62 | 90.67 → 89.17% | −1.50 [−4.50, +1.50] | 36/45 |

- **ANTIBODY:** the gap swaps ~6% of gate-(b) outcomes each way (91/99) but nets to no detectable level change.
- **DIST60:** the python brain FLATTERED the candidate by ~1.7 pp of tap-out.

### Block 2 (PRIMARY): faithful DIST60 vs faithful ANTIBODY → **GAIN SURVIVES** (STEER6r's rule)

| cell | fA → fD | Δ [95%] | churn (fixed / new) |
|---|---|---|---|
| gb10 tap-out (n = 1,500) | 9.47 → **6.87%** | **−2.60 [−3.67, −1.60]** | 51 / 12 |
| race M177 | 86.17 → 91.50% | **+5.33 [+3.33, +7.33]** | 35 / 3 |
| LULU M140 | 83.17 → 89.17% | **+6.00 [+4.00, +8.17]** | 39 / 3 |

- The race gains survive on their own (lower CI > 0).
- tap≤100: Δ +0.00.
- **Faithful gain vs python gain on the same seeds:**

| endpoint | python Δ | faithful Δ | difference |
|---|---|---|---|
| tap-out | −3.80 | −2.60 | DiD +1.20 [−0.27, +2.67], n.s. |
| race | +3.83 | +5.33 | |
| LULU | +6.83 | +6.00 | |

**Reading:** on silicon's own brain, DIST60 is still a clear win on all three endpoints. The tap-out cut is somewhat
smaller (−2.6 vs −3.8 pp) and the race gain somewhat larger.

## STEER8b (amended twice before any game; 12,000 games; audit 12,000/12,000; `steer8/analysis_8b.txt`)
**Setup:**
- **Brain:** faithful DIST60.
- **Seeds:** 600 paired per cell, 39134–40332.
- **Driver model:** PROPH stops at the first publication (p_end 10 today and in (c), 4 under fair (b)).
- **Fix D (DRPROPHFIRST)** as specified by the settle lane.
- **Every arm vs `fD_a2` (today):** 6 gb10 comparisons, Bonferroni 99.17%.

**Today's arm under the corrected PROPH window:**
- `fD_a2` vs 8a's `fD` differs on **45 / 54 / 50 rows** (gb10 / rc10 / lulu10, any key).
- Outcomes change on **0 / 3 / 0**.
- So the PROPH-window correction barely moves today's pinned cart: PROPH runs inside the frozen-gravity settle either
  way.

| arm vs (a2) today, 7.50% gb10 tap-out | gb10 tap-out Δ [95%] | churn (fixed / new) | race M177 Δ | LULU Δ |
|---|---|---|---|---|
| (b) fair DRSETTLE, DEPLOYED fw mask | −0.50 [−1.67, +0.67] | 8/5 | +1.00 | +1.83 |
| (b) fair DRSETTLE, REFIT mask | −0.33 [−1.83, +1.17] | 11/9 | +2.00 | +2.33 |
| **(c) fair, NO settle cut** | **+2.50 [+0.33, +4.67]** | 15/30 | **−9.50 [−12.50, −6.67]** | **−5.67 [−8.33, −3.00]** |
| **(b-ref) + fix D** | **−1.67 [−3.33, −0.17]** (Bonferroni [−3.83, +0.33]) | 17/7 | +2.33 | +2.67 [+0.00, +5.33] |
| **(b-dep) + fix D, DEPLOYED fw mask** | **−1.50 [−2.83, −0.33]** (Bonferroni [−3.17, +0.00]) | **12/3** | +2.33 | **+3.00 [+0.33, +5.67]** |

**Decomposition:**

| comparison | gb10 tap-out | race | LULU |
|---|---|---|---|
| **pin worth** (c − a2) | today's pin is worth 2.5 pp | 9.5 | 5.7 |
| **settle cut under fair gravity** (bref2 − c2) | **−2.83 [−5.17, −0.67]** | **+11.5 [+8.2, +14.8]** | +8.0 |
| **mask refit** (bref2 − bdep2) | +0.17 [−1.00, +1.33] | | |
| **fix D, deployed mask** (bdepD − bdep2) | **−1.00 [−1.83, −0.33]**, churn **6/0** | +1.33 [+0.17, +2.50] | +1.17 [+0.17, +2.17] |
| **fix D, refit mask** (brefD − bref2) | −1.33 [−2.50, −0.33], churn 9/1 | | |
| **mask under D** (brefD − bdepD) | −0.17 [−1.50, +1.00] | | |

- **Settle cut:** removing the pin WITHOUT the settle cut loses all of that.
- **Mask refit:** no detectable difference, so **keep the deployed fw constants (status quo).**
- **Mask under D:** no difference, so **D can ship on the current fw.**

**Block 4 (eh on the TRUE b1, `ehb1=0`, vs 8a fD):** tap-out −1.50 [−3.50, +0.33], race −1.00 [−3.17, +1.00]. No
detectable difference, so **no fw change is needed**. (Block 5 was dropped.)

**Reading (the sim's price for the fairness fix):**
- The fair DRSETTLE cart (b) is **no worse than today's pinned cart** on any endpoint. Its point estimates are slightly
  better.
- **Adding fix D makes the fair cart BETTER than today's:** −1.5 pp tap-out, +2.3 race, +3.0 LULU on the DEPLOYED fw
  mask. The D increment itself is clean (churn 6/0) and significant on all three endpoints at 95%.
- **Shipping no-pin without the settle cut (c) would be a real regression:** +2.5 tap-out, −9.5 race.
- **Model limitation:** rotation still starts at t_act. The ship decision rests on the settle lane's Mesen replay
  bar plus the gravity-fidelity gate; these arms price it.
