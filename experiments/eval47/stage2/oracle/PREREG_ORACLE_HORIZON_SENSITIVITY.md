# Preregistration: oracle horizon sensitivity at intervention states

**Frozen 2026-08-11 before recomputing any short-horizon fork label.**

## Question and authority

At the 489 historical ORACLE-CLAIR plies where H15 actually left the champion,
what is the shortest closed-loop horizon that selects the same action or an
H15-equivalent action?

This is exploratory mechanism work on a previously seen, legacy self-coupled
pilot.  It cannot establish endpoint value and cannot authorize a cart change.
Its job is to price whether the missing faculty becomes visible after a few
real policy steps or only near the full 15-pill horizon.

## Frozen corpus and replay

- Input: the 125-game true-oracle pilot at seeds 30000..30124 (completion
  order in the JSONL is irrelevant).
- Reconstruct the exact treatment trajectory and evaluate only its 489 logged
  flip states.
- Top four candidates, champion ordering, pressure model, capsule stream and
  lexicographic `(survived, virus_progress)` label are unchanged.
- Horizons: **H in {1, 2, 3, 5, 8, 12, 15}**, where H includes the candidate
  placement.  No horizon may be added or removed after seeing results.
- Recomputed H15 labels must equal every logged candidate label and must pick
  the logged treatment action.  Any mismatch makes the audit VOID.

## Metrics, fixed in advance

For each horizon, over all 489 flip states and separately over flips belonging
to base-bad-end→treatment-clear games, report:

1. exact action agreement with H15;
2. fraction that still chooses champion rank 1 (no intervention);
3. fraction whose selected action has the exact same H15 label as H15's action;
4. H15 survival regret and virus-progress regret of the selected action;
5. selected champion-rank distribution.

The label-blind null chooses one of champion ranks 2--4 by a frozen deterministic
hash at every state, preserving the H15 arm's 100% intervention dose on this
flip-only corpus.  Report the same agreement/regret metrics for it.

## Interpretation

- A short horizon is **mechanistically promising** only if exact action
  agreement and H15-label equivalence both exceed the null, its median progress
  regret is zero, and this also holds in rescued games.
- This is not a formal GO.  A nominated horizon still needs cost measurement,
  an implementability check against the coprocessor's frame budget, and an
  unseen endpoint test with a dose-matched label-blind null.
- If no horizon below H12 is promising, stop proposing a small rollout as a
  cheap firmware fix.  H15 headroom would then be genuinely long-horizon.

## Killed checks

Before reporting, the analyser must demonstrate that changing one logged H15
candidate label and changing one logged treatment action each fail the exact
replay gate.  A check that accepts either mutant has no authority.

