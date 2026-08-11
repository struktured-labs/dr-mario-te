# Pre-registration — exact-v8 `d_spawn_h` tie-resolution arm

**Sealed 2026-08-11 before implementing the arm, opening calibration seeds, or running any
endpoint game.** This is a new functional form, not another dose in the closed always-on
`d_spawn_h` penalty family.

## Question and scope

Can the unclipped spawn-lane height sensor remove harmful enumeration/jitter choices while
leaving every move the deployed v8 evaluator decides strictly unchanged?

The base policy is the hardware-validated `firmware_v8` mirror: link-aware fixpoint mechanics,
cascade reward, cap-one cellwise soft-EH helper, R4 hang credit, `WS=20`, and the explicitly
labeled `p2_surrogate` match tie seed. It does not claim to know the cartridge's live `NAV_T`.

`d_spawn_h_linked(a)` is `max(H_post[3], H_post[4])` on candidate `a`'s link-aware,
fixpoint-resolved root board. It is deliberately named `_linked`: the older AUC instrument used
the compact/cap-one feature expander, so its 0.929 AUC motivates this vocabulary but is not
silently transferred to this exact-mechanics sensor.

## Frozen treatment

For each decision, compute the unjittered exact-v8 value of every legal action and the ordinary
base action after `p2_surrogate` jitter. Let `T` be the actions tied at the maximum **unjittered**
value. The treatment changes the base action if and only if:

1. `|T| >= 2`;
2. the ordinary base action is in `T` (so jitter did not override a strict value gap); and
3. some action in `T` has strictly lower `d_spawn_h_linked` than the base action.

It chooses minimum `d_spawn_h_linked` in `T`. If several actions share that minimum, retain the
base action when possible, otherwise use champion enumeration order. Thus the intervention has
no scalar dose, cannot change a strict evaluator decision, and cannot churn an equal-sensor tie.

## Label-blind null and calibration

The null sees only `(seed, ply, T, base_action)`. It never reads the board, sensor, colours,
outcome, candidate features, or future. On any raw tie with the base action in `T`, it chooses a
non-base member of `T` by a fixed SplitMix64 hash and accepts that flip by a second independent
hash threshold.

Calibration uses exogenous-Lulu seeds **60000..60239** on **base trajectories only**. The fixed
threshold is

`round(1e6 * treatment_flips / null_flip_opportunities) / 1e6`, clipped to `[0,1]`.

This algorithm and quantisation are frozen now; the measured number is not. Calibration is
adequate only if there are at least 100 treatment flips and treatment dose is at least 0.25% of
base plies. Otherwise verdict is `NOT_TESTABLE_LOW_DOSE` and no endpoint arm runs. The null must
be exactly invariant when all `d_spawn_h` values are changed.

In evaluation, treatment and null follow their own diverged trajectories. Their realised flip
doses must match within 10% relative. A mismatch voids endpoint interpretation; it does not
permit threshold retuning on evaluation seeds.

## Environment, seeds, and size

- Environment: `exo_lulu`, whose complete pressure offer is a function of `(seed, pill_index)`
  and not receiver clears. This prevents a slow/no-clear policy from suppressing its own attack
  schedule.
- Evaluation seeds: **61000..69999**, 9,000 paired seeds, disjoint from calibration, the stage-2
  corpus/rollout, and the 30000-series oracle block.
- One work item runs base, treatment, and null for the same seed. Results are banked in ascending
  seed order in resumable segments.
- Topouts and 300-pill stalls are both bad ends. Stalls are never treated as rescued topouts.

The 9,000 size obeys the iteration's 7,826 paired-seed floor for making a +1.0pp clear-rate
margin reachable at the stage-2 discordance. Before any verdict, print observed discordance,
paired standard errors and 95% half-widths for bad ends and dies-ahead. If a 1.0pp bad-end margin
is not reachable under observed discordance, that endpoint is explicitly `NOT DECIDABLE`.

## Endpoints and verdict

Primary:

1. paired bad-end difference `treatment - base`;
2. directionality / difference-in-differences
   `(treatment-base) - (null-base) = treatment-null`.

Secondary: dies-ahead differences on the same two contrasts; clear/topout/stall counts; paired
pill difference among seeds clearing in both arms; per-ply flip provenance and timing.

Use paired seed bootstrap CIs (`B=5000`, RNG 20260811) and exact McNemar tests for binary
discordance. `GO` requires both primary upper 95% CI bounds below zero. A favorable point
estimate, a comparison only to base, or an insignificant harm test is not a GO. Otherwise the
verdict is `NO_GO`; if dose or adequacy gates fail, use their explicit non-verdict labels.

## Mandatory gates and killed mutants

Before calibration results are read:

1. legal masks from the linked post-board sensor equal exact-v8 candidate-value legal masks on
   at least 100 real decisions;
2. a synthetic equal-value pair with different lane heights makes treatment choose the lower
   height, while a clipped/dead-zone sensor mutant cannot distinguish it;
3. a synthetic one-point strict value gap is unchanged by treatment, while a deliberately wrong
   `gap<=1` mutant changes it;
4. the null choice is unchanged after arbitrary sensor permutation (label blindness), while a
   deliberately sensor-reading mutant changes;
5. the new base runner reproduces `OracleArm(const, firmware_v8, p2_surrogate)` action-for-action
   and outcome-for-outcome on a separate smoke set.

Every evaluation flip logs: seed, arm, ply, `t_to_end`, viruses, max height, pre-board
`d_spawn_h`, raw tie size, base action, chosen action, base/chosen linked post heights, and the
chosen action's champion rank. Checks must be shown to fail on their declared wrong inputs.

This experiment changes no cartridge, firmware, RTL, shipped artifact, or remote oracle job.
