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

## STEER8b: pending (`steer8b-farm`; analysis → `steer8/analysis_8b.txt`)
