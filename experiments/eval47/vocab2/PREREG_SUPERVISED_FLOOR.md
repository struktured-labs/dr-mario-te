# PRE-REGISTRATION — #84 supervised floor with d_spawn_h

**Written and committed before any model was trained.** Date: 2026-08-09.
Data: `fatal_windows.npz` / `controls.npz` / `features.npz` (vocab2 extraction, 890 fatal
games' last-10 decisions, census-fidelity-gated, `gates_result.json` pass).
Machinery: `feature_battery.py`'s own `make_contrast` + `stratified_auc_machinery` +
`boot_weights`, imported unchanged — the floor must be measured on the same instrument that
produced the 0.9002 / 0.9290 numbers, or it measures rig disagreement instead.

## The question, sharpened

The routing decision says d_spawn_h is a FEATURE for the learned-evaluator lane. The naive
version of that question ("does a learned model beat the hand-tuned eval?") is already
answered by the battery: a single un-clipped feature does (0.9290 vs 0.9002). So it is not
the decision-relevant question.

**The decision-relevant question is whether LEARNING adds anything beyond un-clipping the
sensor.** If a model trained over the whole vocabulary cannot beat `d_spawn_h` used alone,
then the correct action is to fix the sensor's resolution, not to run a stage-2 training
programme — and stage 2 is not justified by this evidence.

> **PRIMARY:** held-out stratified AUC of the best learned model **minus** held-out
> stratified AUC of `d_spawn_h` alone. Justifies stage 2 iff the paired bootstrap CI of that
> difference **excludes 0** on the positive side.

## Split — by GAME, not by row

890 fatal games contribute 10 decisions each; rows within a game are strongly correlated, so
a row-level split leaks. **Seeds are partitioned; every decision from a seed goes to exactly
one side.** 70% train / 30% holdout, partitioned on `seed % 10` (0-6 train, 7-9 holdout) so
the split is deterministic, inspectable, and independent of any feature value.

## Arms (all evaluated on the SAME held-out decisions)

| arm | what it tests |
|---|---|
| `SPAWN` alone | the champion's own clipped term — the floor |
| `d_spawn_h` alone | the un-clipped sensor, no learning |
| linear, 11 hand features | can re-weighting the existing vocabulary do it? (expected no — the wall) |
| linear, 11 + d_spawn_h | does the feature help a linear model beyond itself? |
| linear, all features | full vocabulary, RTL-plausible model class |
| gradient boosting, all features | reference ceiling: how much is left for a non-linear model |

Linear (regularized logistic) is the PRIMARY model class because the eventual target is a
firmware-implementable evaluator; the GBM is reported as a ceiling, not as a candidate.

## Controls, fixed now

- **Shuffled-label control**: labels permuted within stratum, refit end to end, must land at
  AUC ≈ 0.5 (accept 0.45-0.55). If it does not, the pipeline leaks and no arm is read.
- **Seed-disjointness assertion**: train ∩ holdout seeds must be empty, asserted in code.
- Contrast = PRIMARY topout (`outcome == 1`), the battery's own primary.

## Declared in advance

- A learned arm that merely MATCHES `d_spawn_h` alone is a **negative** result for stage 2,
  and will be reported as such. Matching is the expected outcome if the wall holds.
- No feature selection on the holdout. No threshold tuning on the holdout.
- Rank agreement (Spearman of predicted risk vs outcome, and top-decile lift) is reported
  alongside AUC because AUC alone can hide a model that orders the extremes badly — but the
  PRIMARY is the AUC difference above.
