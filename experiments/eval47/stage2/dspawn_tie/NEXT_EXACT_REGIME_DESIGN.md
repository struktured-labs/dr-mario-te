# Next candidate design — exact-v8 post-garbage `d_spawn_h` gate

Status: **design record, not a preregistration and not authorized to run yet**.
Freeze a separate prereg only after the null below passes a disjoint base-trajectory
calibration and its killed mutants.

Update 2026-08-11: the exact arm and association-blind null are implemented and
passed their structural engineering gate. Mechanism-only seeds 70400..70639
provided 233 treatment distinct-state flips and 466 null opportunities; a
label-blind cutoff matched aggregate dose exactly. The selected null's first
timing and medians were close, but its successor-Hamming tails were not
(p10/p90 2/12.8 versus treatment 7/19). Therefore endpoint play remains
blocked pending a newly calibrated stratified null. See
`POST_GARBAGE_CALIBRATION_RESULT.md`.

Second update: a 40-cell Hamming/timing/value-gap table was frozen before fresh
seeds 70700..70939. It generalized every registered distribution and first-flip
timing gate, but selected only 258 distinct flips against treatment's 327
(21.10% dose mismatch, limit 10%). Registered result:
`NOT_TESTABLE_STRATIFIED_NULL`. Per contract it may not be refit on that block;
endpoint play remains unauthorized. See
`STRATIFIED_NULL_VALIDATION_RESULT.md`.

Third update: the registered larger correction closed the estimator defect
without using the failed validation block for refitting. N=1,200 fit seeds
produced 1,140 treatment changes / 2,114 null opportunities; population-rate
cutoffs were frozen before a one-shot N=600 validation. That validation passed
all gates: 585 versus 616 distinct changes (5.30% mismatch), distribution TVs
0.027--0.060, and first-flip median 59 versus 60. The null blocker is cleared
for an endpoint preregistration **draft only**. See
`LARGE_NULL_VALIDATION_RESULT.md`.

## Why this candidate remains alive

The old compact/drip screen's literal verdict is no-graduate under its frozen
43:1 clear:topout weighting.  It nevertheless measured a strong conditional
mechanism: K4/wq60 rescued 148/240 selected topouts, reduced dies-ahead
234 -> 60, broke 5/240 selected clears, and had the best current-objective
sensitivity when arithmetically repriced at the later Lulu 6.4:1
clear:dies-ahead ratio.  This is disclosed selection, so K4/wq60 is one
externally nominated candidate—not permission to sweep K/wq again.

This is distinct from the in-flight tie resolver.  The tie arm only chooses
among exact raw-value ties and tests resolution.  This candidate applies a
strict score correction for a short period after opponent garbage and tests a
garbage-reactive policy mechanism.

On the first 2,829 registered exact-v8 evaluation trajectories, a purely
schedule-derived check found candidate-independent offered-pressure duties of
15.2%, 27.5%, 37.5%, and 45.4% for K=1..4 including the 25-pill opening.  Thus
K4 is below the historical 54% mostly-on boundary; an actual-*landed* gate can
only be sparser.  These are descriptive pre-design numbers, not an endpoint.

## Candidate semantics

- Base: exact `firmware_v8/p2_surrogate`, including link/fixpoint mechanics,
  cascade-180, source-exact soft-EH helper, R4 hang, strand-20, and jitter.
- Pressure: candidate-independent `exo_lulu`; track the cumulative garbage
  counter before/after every `_advance` to identify actual landed cells.
- Gate: active for the next K=4 decisions after at least one garbage cell
  actually lands.  Freeze the off-by-one convention against the historical
  runner with a synthetic pulse gate.
- Treatment: while active, for every legal exact linked root subtract
  `60 * max(0, d_spawn_h_linked - 10)` from the unjittered exact-v8 root value,
  then apply the unchanged v8 jitter/tie order.  Outside the gate, play base.
- Stalls and topouts are bad ends at parity.  The final arm must use 9,000
  paired seeds or declare clear non-inferiority undecidable.

## The null is the blocking design problem

Do not reuse the current tie null.  Its semantic audit was created because an
action-ID flip can be an identical successor board.  Dose for this candidate
means a **distinct linked successor state**, not a different integer action.

Candidate null construction:

1. At every active-gate decision, compute the same legal actions, exact root
   boards, and multiset of treatment penalty magnitudes.
2. Assign that exact multiset across legal action IDs by a frozen `(seed, ply)`
   permutation.  Separately canonicalize actions by exact linked successor-board
   equality; aliases cannot count as distinct-state flips.
3. Score with the identical wq60 arithmetic and jitter.  If the chosen board is
   identical to base, normalize the action to base and count no intervention.
4. On disjoint base trajectories, measure treatment distinct-board flips and
   shuffled-null distinct-board opportunities.  A frozen hash thinning may
   reduce excess null opportunities; if the null has fewer opportunities, the
   design fails and must not open endpoint seeds.
5. Before endpoint play, require matched first-flip timing, champion value-gap,
   successor-board Hamming distance, and active-gate duty bands in addition to
   aggregate flip rate.  Freeze numerical bands from calibration, not outcomes.

The null may read current-board features and gate state; it may not read future
pressure, survival/progress labels, arm endpoints, or treatment outcomes.  A
sensor-permutation mutant must fail if it accidentally preserves the real
action-to-sensor association, and an action-alias mutant must fail the distinct-
successor dose check.

## Minimal sequence

1. Finish and bank the tie arm and its final semantic-alias audit.
2. Implement only the K4/wq60 exact arm plus shuffled-feature null.
3. Run synthetic gate pulse/off-by-one, exact base identity, sensor association,
   successor-alias, and null-label-blind mutants.
4. Calibrate duty and distinct-state dose on seeds disjoint from 61000..69999.
5. If calibration passes, freeze N=9,000 seeds and the ordinary dies-ahead,
   clear non-inferiority, bad-end, dose, and directionality verdict.  If it
   fails, report `NOT_TESTABLE_NULL_OR_DUTY`; do not tune another K/wq from the
   calibration endpoints.
