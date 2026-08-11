# Historical-oracle vs cartridge-faithful policy census

Date: 2026-08-11  
Status: **complete descriptive census; all registered checks exercised**

Forty untouched cartridge-faithful trajectories (seeds 30640--30679) produced 5,081 pre-placement
states, including 2,491 states where the unchanged oracle gate fired.  Every legal-action mask
matched, every named semantic mutant changed at least one candidate vector, both seed selectors
passed, and the reversed-tie-order mutant was killed.

The result changes how the currently running Hetzner arm must be interpreted: it is **not an oracle
ceiling for shipped v8**.  It is a ceiling for the older compact/cap-one/seed-zero policy.

## Primary materiality

| comparison | all 5,081 states | 2,491 oracle-gated states |
|---|---:|---:|
| historical action vs actual v8, both seed zero | 24.38% | **31.59%** |
| historical action vs actual v8, representative nonzero seed | 37.98% | **44.64%** |
| historical vs actual seed-zero top-4 set | 49.71% | **59.69%** |
| historical vs actual representative-seed top-4 set | 52.77% | **64.35%** |
| historical vs actual representative top-4 order | 79.57% | **85.99%** |
| actual v8 action outside historical top four | 7.64% | **11.64%** |
| historical action outside actual v8 top four | 9.03% | **14.09%** |

The seed-zero comparison already isolates evaluator/mechanics drift from tie jitter and is large.
At the gate, almost one in three base actions differ and almost three in five top-four sets differ
even with jitter disabled.  With the frozen representative nonzero seed, the actual action is not
even available to the historical oracle on 290/2,491 gated states (11.64%, about one in 8.6).

## Component action churn against exact v8

| deliberately wrong semantic | all states | gated states |
|---|---:|---:|
| compact cap-one mechanics with R4 | 21.75% | **26.62%** |
| flat rather than R4 hang | 6.91% | 7.87% |
| erased parent links | 4.41% | 3.85% |
| EH on main fixpoint child | 1.89% | 1.00% |
| EH on link-aware cap-one replay | 0.69% | 0.20% |

Complete mechanics are the largest isolated source of action drift.  R4 is independently material;
links and the odd soft-EH auxiliary path are smaller but nonzero and were all exercised on these
fresh trajectories.

## Tie-seed envelope

Across all 255 nonzero seeds, at least one seed changes the seed-zero v8 action on 36.61% of all
states and 38.66% of gated states.  A uniformly drawn nonzero seed differs from seed zero on 18.45%
and 19.64%, respectively.  The mean number of distinct actions across seed zero plus all nonzero
seeds is 1.394 overall and 1.436 at the gate.

The deterministic per-game seed used to generate trajectories is explicitly a P2-like surrogate,
not a claim that NES `NAV_T` is a function of game seed.  The all-seed envelope is retained so the
materiality conclusion does not depend on that surrogate.

## Coverage and scope

The 40 actual-policy trajectories ended in 39 clears and one topout, totaling 5,081 plies; those
outcomes are coverage context only, not a paired strength comparison.  The machine-readable output
from the frozen script had SHA-256
`3714b416c2b9663d661dfd9a446841ab921f0b9e7d41f9dae86524d7ecc10d9e`.

Future root-oracle work needs an explicit `firmware_v8` policy mode for base ranking **and every
forward rollout**.  It also needs an explicit tie-seed model.  Do not silently mutate or relabel the
running 9,000-pair historical arm; its result remains useful under the semantic label
`historical_compact_cap1_flat_seed0` but cannot close the root-reranking lane for the shipped cart.

No strength verdict is drawn here.  An outcome claim requires a separately preregistered paired
arm with a dose-matched label-blind null.
