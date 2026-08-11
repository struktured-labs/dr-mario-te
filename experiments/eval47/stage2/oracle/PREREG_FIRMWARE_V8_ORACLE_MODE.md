# Preregistration: explicit cartridge-faithful oracle policy mode

Frozen: 2026-08-11, after the semantic census and before modifying `oracle_arm.py` or its runner.

## Scope

Add an opt-in `firmware_v8` base-policy mode for **future** oracle arms.  The existing default must
remain `historical_compact`, byte/action compatible with every banked and currently running arm.
No outcome experiment is authorized here.

`firmware_v8` must use the hardware-validated soft-EH evaluator for:

- the root base action;
- root candidate ranking and top-four selection;
- every policy action inside every forward fork.

Tie behavior must be explicit:

- `seed0`: no jitter;
- `p2_surrogate`: constant per game,
  `(((73*game_seed + 41) & 255) | 1) ^ 0xA4`.

`historical_compact` may only use `seed0`.  No mode may silently infer or relabel the actual NES
wall-clock `NAV_T` distribution.

## Runner and provenance

Add frozen CLI/meta fields `policy_semantics` and `tie_seed_mode`.  They must be included in every
row, `META.json`, console launch line, and resume-compatibility check.  The runtime manifest for
`firmware_v8` must hash the exact mirror and its chain/link/strand dependencies.  Reusing an output
directory under a different policy or tie mode must fail.

Every flip-provenance record in the new mode must carry `policy_semantics`, `tie_seed_mode`, and the
numeric tie seed.

## Required gates and killed mutants

1. Default construction and explicit `historical_compact/seed0` must produce identical action
   sequences and outcomes on the same seeds.
2. A `firmware_v8/p2_surrogate` const arm must reproduce a separate direct-policy loop
   action-for-action and outcome-for-outcome on at least six fresh seeds.
3. The same direct check with the wrong historical policy must differ; the same firmware policy
   with seed zero must differ from the surrogate on at least one seed.
4. Instrument a real gated oracle decision with horizon >=2.  Every policy evaluation observed at
   the root and in forks must request `firmware_v8`; a deliberately supplied historical mode must
   fail that semantic assertion.
5. Legal masks and direct seed selectors remain exact; the reversed-order tie mutant must still
   fail on an equal-valued vector.
6. Runner banking tests must show that changing either new field prevents resume.

The infrastructure is GO only if all gates pass.  This does not authorize a Tier-A run: a
cartridge-faithful oracle still needs a new outcome preregistration, killed shuffled-label null,
adequate sample size, and an explicit tie-seed interpretation.
