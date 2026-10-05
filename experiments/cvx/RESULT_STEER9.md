# RESULT (2026-10-04): STEER9 — "don't seal a live column": all three arms FAIL, and all three are HARMFUL

- **Pre-registration:** `PREREG_STEER9.md`, commit `ff30868d`. It was written before any screen game: the commit
  records 0 row files. The exec-bit fix `3e4e509f` came before the first game.
- **Rows:** `steer9/`. **Analyzer:** `analyze_steer9.py` → `steer9/analysis.txt`.
- **Farm:** 7,800 games; audit OK (156 × 50); 0 errors in the err logs. Run under the steer9-throttle PAUSE switch.
- **Baseline FAIR** (= STEER8b `fD_bdepD`):
  - banked rows on 39134–40332;
  - `s9_base` rows on the 600 new gb10 seeds (identity gate 9/9 byte-identical to the banked rows);
  - gb10 tap-out 36/600 banked + 38/600 new = **6.17%**.

## Mechanism check (before any game; `steer9/mech_check.txt`)
Each rule is run on the observed couch boards with the silicon-faithful brain (Leaf6FwDecider, all fw switches on,
DIST60, deployed mask).

| game | own-seal decisions (silicon == brain) | brain would seal the same virus | kept open: V150 | VVETO | CVETO | leaf W60 (not screened) |
|---|---|---|---|---|---|---|
| M5 G2 | 20 (13) | 13 | 8 | 13 | 7 | 3 |
| M4 G2 | 26 (21) | 21 | 14 | 21 | 15 | 5 |
| lulu G1 | 17 (12) | 14 | 9 | 14 | 13 | 3 |

**The named critical moves:**
- **M5 G2 col-6 wall (p4 / p13 / p14): no rule changes it.**
  - All three were silicon ≠ brain (OTHER / LATE-FLIP / OTHER).
  - The brain's own choices on those boards put 0 cells in col 6.
  - p13 and p14 seal nothing new, because (6,6) was already sealed by p4's hanging half. A route predicate cannot
    see deepening.
  - Col 7's six viruses were sealed by garbage (p138).
- **M4 G2's tall-board seals (p78 / p82 / p85):** these were brain choices, and every V rule and CVETO kept them open.
- **lulu G1's (8,2):** sealed at p7 by a move the faithful DIST60 brain would not make (lulu G1 was ANTIBODY).

## Screen result (paired vs FAIR; seed bootstrap; Bonferroni = 99.17%, 3 arms)
| arm | gb10 tap-out (n = 1,200) Δ [95%] {Bonf} | churn fixed / new | rc10 race M177 (n = 600) Δ [95%] {Bonf} | churn | LULU race M140 (n = 600) Δ [95%] {Bonf} | churn | verdict |
|---|---|---|---|---|---|---|---|
| **s9_V150** | 6.17 → 10.08%: **+3.92 [+1.92, +5.92] {+1.50, +6.50}** | 54 / 101 | 93.50 → 90.83%: −2.67 [−5.67, +0.17] {−6.17, +1.00} | 31 / 47 | 92.17 → 86.00%: **−6.17 [−9.67, −2.83] {−10.50, −2.00}** | 39 / 76 | **FAIL (harmful)** |
| **s9_VVETO** | 6.17 → 76.67%: **+70.50 [+67.75, +73.25] {+67.25, +73.75}** | 14 / 860 | 93.50 → 27.33%: **−66.17 {−71.00, −61.17}** | 11 / 408 | 92.17 → 25.17%: **−67.00 {−71.83, −62.17}** | 8 / 410 | **FAIL (catastrophic)** |
| **s9_CVETO** | 6.17 → 93.50%: **+87.33 [+85.33, +89.25] {+84.92, +89.58}** | 5 / 1,053 | 93.50 → 6.67%: **−86.83 {−90.17, −83.17}** | 4 / 525 | 92.17 → 7.33%: **−84.83 {−88.50, −81.00}** | 5 / 514 | **FAIL (catastrophic)** |

- The declared secondary (STEER6r's "no demonstrated loss" form) also fails for every arm.
- The pre-registered null audit (a race-neutral arm fails the race guard about 98% of the time) is **moot**. No arm
  is race-neutral: each loses races significantly, or catastrophically.

**Activity** (rule 26: the treatments ran):

| arm | rule fired | changed the root (vs FAIR's brain on the same board) |
|---|---|---|
| V150 | 86–88% of decisions | 14.1–14.3% (≈ 18–19 per game) |
| VVETO | 83–85% | 31.4–32.5% (≈ 29 per game) |
| CVETO | 85–86% | 38.2–38.9% (≈ 23–24 per game) |

**Stall-pills per game** (gb10; 95% CI):

| arm | endgame stall-pills (act ≥ 10 from ≤ 4 viruses) | all act-stall pills | SEALED (str) stall pills |
|---|---|---|---|
| V150 | 12.9 → 13.7, +0.77 [−1.92, +3.29] | +2.87 [−1.15, +6.63] | +0.87 [−2.91, +4.41] |
| VVETO | 12.9 → 5.9, −7.01 [−9.74, −4.38] | −6.06 | −7.38 |
| CVETO | 12.9 → 1.3, −11.65 [−14.08, −9.53] | −16.91 | −13.96 |

- **⚠ The veto arms' stall drops are CENSORING, not a cure.** Their games end in early tap-outs (median pill 54 /
  45, with 30 / 33 viruses left), before an endgame exists. Per R98 this is post-treatment, and it is NOT evidence of
  fewer stalls.
- **V150, the only arm whose games reach the endgame, does not reduce stall-pills at all.**
- The race and LULU cells show the same pattern.

**Tap-out profile** (descriptive):

| arm | tap-outs | pills at tap-out (median) | viruses left (median) | PROPH fires per game |
|---|---|---|---|---|
| FAIR | 6.2% | 207 | 6 | 1.6 |
| V150 | 10.1% | 136 | 9 | 2.6 |
| VVETO | 76.7% | 54 | 30 | 13.5 |
| CVETO | 93.5% | 45 | 33 | 15.0 |

The PROPH count means the spawn throat is high.

## Why it fails (post-hoc, NOT pre-registered: `steer9_diag.py`, `steer9/diag/`)
**Observed** on 8 replayed losses:
- Few changed roots plug the spawn directly: 1 of 164 changed roots (VVETO 68, CVETO 33, V150 63). So it is not a
  DRVETO ↔ seal-veto tie.
- Instead the bottle fills. VVETO seed 39234 reached heights [8, 8, 16, 15, 15, 15, 15, 6] by pill 53, with 37
  viruses left.

**Hypothesis**, consistent with the mechanism check's p13/p14 finding:
- The route predicate counts only the FIRST seal. Stacking on a column whose viruses are already sealed, or that has
  no virus, is free.
- So the cheapest non-sealing roots pile junk onto dead columns, and the board fills.
- The rule also refuses clears that seal a neighbour.
- **Discriminating test (not run):** the share of changed roots that land in columns with 0 live viruses, vs FAIR's
  choices on the same boards.

**Reading:**
1. **A "don't seal" root rule is the wrong lever, at every dose screened.**
   - The soft penalty (−150 per newly sealed virus) costs +3.9 pp tap-out and −6.2 pp LULU race, while leaving
     stall-pills unchanged.
   - The vetoes are catastrophic.
   - This matches the prior art: always-on shaping of mid-game viruses (STEER6 dist_hsv, the burial-price family) nets
     zero or worse. A threshold "access" notion is that family's sharper form.
2. **The couch stalls that motivated this were not brain decisions.**
   - The M5 G2 col-6 wall was execution (silicon ≠ brain on p4, p13 and p14).
   - Col 7 was sealed by garbage.
   - lulu's (8,2) was sealed by the older ANTIBODY brain's move.
   - The forensics' "common cause" is real on the board, but the actor is mostly the execution layer and the opponent.
     **The execution-fidelity lane is the lever for those**, not a new brain term.
3. Where the brain DOES seal (M4 G2's tall board), keeping one virus open costs more elsewhere than it saves. So a
   brain term that values access needs to see depth: dig cost, not route feasibility. Burial pricing (`buried` −48 per
   cell above the first two viruses of a column) already prices depth linearly; this screen does not test a re-weight
   of it.

**No implementation plan:** nothing passed. The pre-registered cost estimates (PREREG §8) are moot.
- They would have been firmware-only: V150 ≈ 0 answer frames (overlapped); the veto pre-pass 0.08–0.13 f; no RTL.

## Files
- **Code:** `seal_steer9.py`, `steer9_run.py`, `steer9_farm.sh`, `analyze_steer9.py`, `steer9_mech.py`,
  `steer9_mech_report.py`, `steer9_diag.py`.
- **Rows:** `steer9/{gb10,rc10,lulu10}_*.jsonl`, `steer9/gate/`, `steer9/mech_cases.jsonl`, `steer9/diag/`.
- **Reports:** `steer9/mech_check.txt`, `steer9/analysis.txt`.
