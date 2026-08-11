# Oracle horizon sensitivity — no small-rollout nomination

**Run 2026-08-11 under `PREREG_ORACLE_HORIZON_SENSITIVITY.md`.** Exploratory
mechanism audit on the previously seen, legacy self-coupled 125-game pilot; no
endpoint or ship authority.

## Exactness gate

- 125/125 treatment trajectories replayed exactly.
- All 489 logged intervention states recovered.
- All four recomputed H15 labels and the selected H15 action matched the log at
  every state.
- Changing one logged H15 label and changing one logged teacher action each
  failed the replay gate as intended.
- Four workers, 695.8 seconds wall for the seven-horizon audit.

## Result

All-state metrics (the rescued-game slice points the same way):

| H | exact H15 action | H15-label equivalent | chooses champion/no intervention | mean progress regret | median regret |
|---:|---:|---:|---:|---:|---:|
| 1 | 4.70% | 5.11% | 90.80% | 1.464 | 1 |
| 2 | 7.57% | 7.77% | 86.71% | 1.419 | 1 |
| 3 | 9.82% | 10.43% | 85.07% | 1.342 | 1 |
| 5 | 14.93% | 15.34% | 78.73% | 1.235 | 1 |
| 8 | 23.93% | 24.95% | 67.28% | 1.037 | 1 |
| 12 | 48.88% | 50.31% | 47.24% | 0.589 | 0 |
| 15 | 100% | 100% | 0% | 0 | 0 |
| random rank 2--4 null | 33.13% | 46.22% | 0% | 1.108 | 1 |

The 131 intervention states in base-bad-end→treatment-clear games are not an
easier subset.  H8 action/equivalence is 22.14%/22.90%, below the random
alternative's 29.77%/38.93%.  H12 reaches 48.09%/48.85%, but still has median
progress regret 1 and chooses the champion on 45.80% of these known H15-flip
states.

Survival is not the separation: random alternatives have positive H15 survival
regret on only 1.02% of states.  The hard part is the same mechanism identified
from the original logs—sequential virus progress.

## Decision

**No horizon below H12 met the preregistered mechanism rule.  Do not propose
H3/H5/H8 as a cheap firmware approximation to the H15 oracle.** H<=8 is worse
than the dose-matched random-alternative null at recognizing the intervention
action and its H15-equivalent label.  H12 is the first horizon that sees useful
direction, and it remains inadequate precisely in rescued games.

This sharpens the programme branch: a firmware candidate needs a different
long-horizon abstraction, not a few more ordinary closed-loop plies.  The full
H15 oracle remains a legitimate ideal-headroom measurement, but its mechanism
does not collapse into a small rollout that fits the known copro frame budget.

Full ignored output:
`out/oracle_horizon_sensitivity.json`.  Implementation commit: `ed1560c`.

