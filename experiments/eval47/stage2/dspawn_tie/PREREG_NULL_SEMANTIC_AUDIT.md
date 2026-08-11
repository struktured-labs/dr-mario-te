# Preregistration — exact-v8 tie-null semantic-alias audit

Frozen 2026-08-11 before reconstructing or comparing any first-flip post-root
board.  This is a mechanism audit on the already registered d_spawn tie run,
not a new endpoint arm and not a way to change its verdict thresholds.

## Question

The registered null matches treatment's aggregate action-flip rate, but its
first logged flips occur earlier, almost always have zero `d_spawn_h` delta,
and have produced much less trajectory/outcome churn on the disclosed growing
prefix.  Are null action flips often **semantic aliases**—different action IDs
that resolve to the exact same linked-fixpoint root board—while treatment flips
are necessarily state-distinct?

## Frozen population and reconstruction

- Input: the final 9,000-pair evaluation seeds 61000..69999.  A partial run is
  allowed only as an explicitly labeled implementation smoke; only N=9,000 is
  the final audit.
- For each seed and each of treatment/null, take only the minimum logged flip
  ply.  Until that action, the arm is identical to base, so reconstruct the
  exact `firmware_v8/p2_surrogate` base trajectory under `exo_lulu` once per
  seed and inspect the common predecessor.  Later flips are excluded.
- Recomputed exact-v8 base action at the target ply must equal the logged base
  action.  Missing target plies, illegal candidates, or any mismatch fail the
  replay gate.
- Expand logged base and alternative actions with the linked fixpoint root
  primitive used by the treatment sensor.  `semantic_alias` means exact
  equality of all 128 color, virus, and link bytes plus expansion metadata
  `(virus_count, cells_cleared, chain_depth)`.  Action ID or lane-height
  equality alone is insufficient.

## Frozen outputs

Report separately for treatment and null:

1. number of first action flips and exact aliases;
2. alias fraction;
3. color/virus/link Hamming-distance distributions;
4. same-color current-pill fraction, action variant/column transitions, and
   sensor-drop distribution, split by alias versus distinct board;
5. the ratio of distinct-board first flips between treatment and null.

Interpretation is descriptive.  A high null alias fraction would demonstrate
that count-matched action flips are not dose-matched state perturbations and
would explain why the current null is weak for churn attribution.  It would
not change whether treatment beats base.  A low alias fraction falsifies that
specific explanation; timing and action-distance mismatch would remain
separate hypotheses.

## Checks that must fail

- Comparing a board with itself is the positive alias control; changing one
  color byte must make the exact comparator return false.
- A deliberately changed logged base action must fail the same identity check
  used by real targets.
- A deliberately removed target ply must fail target-consumption accounting.

The audit must record source and input hashes.  It may not modify the live arm,
its raw rows, its META, or its registered analyzer/verdict.
