# Preregistration: historical-oracle vs cartridge-faithful policy census

Frozen: 2026-08-11, after the full-candidate co-sim GO and before inspecting seeds 30640 onward.

## Question and non-claim

How often does the historical policy used by the currently running Hetzner oracle disagree with
the now hardware-validated shipped-v8 base policy, especially in its root top four?  This is a
semantic/materiality census, not an outcome arm and not evidence that either policy is stronger.

## Frozen trajectories

Play 40 level-11 `lulu`-pressure games, seeds 30640--30679, for at most 300 pills.  The trajectory
policy is the cartridge-faithful `firmware_v8_policy` with a deterministic representative nonzero
match seed:

`tie_seed = (((73*game_seed + 41) & 255) | 1) ^ 0xA4`.

This schedule is a reproducible P2-like surrogate, not a claim that wall-clock `NAV_T` is determined
by game seed.  Preserve raw seed-zero results and an all-255-nonzero-seeds sensitivity envelope so
the conclusion does not depend on that surrogate alone.

At every pre-placement state compute:

- `historical_compact`: `oracle_arm._champ_values`, strict seed-zero order;
- `firmware_v8`: hardware-validated soft-EH semantics;
- `cap1_r4`: complete v8 weights/features but compact cap-one mechanics and R4;
- `flat_hang`: complete mechanics with flat rather than R4 hang;
- `zero_link`: complete mechanics after erasing the parent link plane;
- `full_child_eh`: the first, wrong offline EH board;
- `linked_replay_eh`: the second, wrong offline EH board.

All v8-family choices use the representative tie seed unless explicitly called `seed0`.

## Frozen metrics

Print separately over all plies and over the unchanged oracle gate
`d_spawn_h >= 12 OR viruses <= 8`:

- historical vs actual action disagreement, for actual seed zero and representative seed;
- actual seed-zero vs representative-seed disagreement;
- actual vs each named semantic mutant action disagreement;
- historical vs actual top-4 set disagreement and ordered-top-4 disagreement, both at seed zero and
  representative seed;
- fraction of actual actions outside the historical top four and historical actions outside the
  actual top four;
- rank of the actual action under the historical policy;
- fraction of states where any of 255 nonzero tie seeds changes the seed-zero action, mean number of
  distinct actions across those seeds, and aggregate fraction of nonzero seeds that change it;
- state counts, gated counts, game outcomes, and per-game plies for coverage context.

Top-four ranking is descending value with the frozen `CHAMP_ORDER` as the stable tie order; seeded
v8 rankings include the deployed 0--3 jitter before sorting.

## Checks capable of failing

- all compared vectors must have the same legal-action mask;
- seed-zero actual selection must equal `choose_from_values`;
- representative selection must equal `choose_seeded`;
- the final co-sim corpus has already killed every named semantic mutant, but this fresh census must
  independently observe at least one candidate-vector difference for each mutant; otherwise report
  that mutant as `not_exercised` rather than zero effect;
- reversing `CHAMP_ORDER` on an all-equal legal vector must change its chosen action.

No pass/fail strength threshold is registered.  Results authorize semantic labeling and future-arm
design only; outcome claims require a separately preregistered paired arm with a dose-matched null.
