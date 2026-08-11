# Compact oracle-teacher E0 — NO_NOMINATE

**Run 2026-08-11 under `PREREG_DISTILLED_TEACHER.md`.** This was an N=60
implementation/dose screen, not a powered endpoint verdict and not a lane
closure.  Frozen policy SHA-256:
`9ae58f0d9c0d69dfc3d781fbca16b126bed254517589a7ae8a1d6312b10b9b32`.

## Gates first

All E0 gates passed before endpoints were displayed:

- complete seeds 51300..51359, triple-paired champion/true/null;
- candidate-independent `exo_lulu_v1` pressure;
- zero forks; 399 true flips and 401 null flips;
- flip count ratio 0.9950; per-ply flip-rate ratio 0.9080;
- true/null garbage-per-ply ratio 1.0159;
- flip rates 3.939% true and 4.338% null, below the 15% ceiling;
- 399/399 and 401/401 provenance records present;
- high-churn, low-dose-count, low-dose-rate and wrong-policy-hash mutants all
  failed as intended.

## Exploratory endpoints

| arm | clear | bad end | dies-ahead | topout | stall |
|---|---:|---:|---:|---:|---:|
| champion | 73.33% | 26.67% | 20.00% | 23.33% | 3.33% |
| true teacher | 68.33% | 31.67% | 25.00% | 25.00% | 6.67% |
| shuffled teacher | 80.00% | 20.00% | 15.00% | 16.67% | 3.33% |

True versus champion changed 19 bad-end outcomes: 11 clean→bad and 8
bad→clean.  Null changed 14: 5 clean→bad and 9 bad→clean.  Bad-end effects:

- true minus champion: **+5.00 pp** (worse);
- null minus champion: **-6.67 pp** (better);
- true-minus-null difference-in-differences: **+11.67 pp**, wrong direction.

Topout/stall parity does not rescue the candidate.  True includes one
base-topout→stall and one base-stall→topout; null includes one
base-topout→stall and no stall→topout.

## Decision

**NO_NOMINATE.** All three preregistered nomination checks failed.  Do not run
this compact DT2 policy at larger N and do not port it into firmware.

This does **not** prove teacher distillation structurally dead.  It establishes
something narrower and useful: grouped-CV recoverability of decisions from the
old self-coupled oracle trajectory (trigger AUC 0.756 versus null 0.495,
alternative accuracy 0.540 versus 0.309) did not transfer directionally to
unseen endpoint play under independent pressure.  The compact trigger reduced
mostly to game phase and the alternative tree to champion rank/gap plus height
variance; that is too little of the H15 progress mechanism.  A future teacher
lane must add trajectory/temporal vocabulary or retain a small real rollout,
not merely fit a more confident one-ply classifier to these labels.

Ignored full artifacts live in `out/distilled_e0/`; the fail-closed durable
summary is this file.  Runtime: `185942f`; frozen prereg: `f16cb56`; compact
runtime and killed mutants: `43a5f7c`.

