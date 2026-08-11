# Result — exact-v8 post-garbage K4/wq60 pre-endpoint calibration

**2026-08-11: structural calibration PASS; endpoint arm remains BLOCKED on
successor-distance matching.** No endpoint outcome was retained or inspected.

This is the one externally nominated post-landed-garbage candidate from
`NEXT_EXACT_REGIME_DESIGN.md`, not another sweep. It uses exact
`firmware_v8/p2_surrogate`, `exo_lulu`, K=4 decisions after garbage actually
lands, and the frozen penalty `60 * max(0, d_spawn_h_linked - 10)`.

## Engineering gate

All prospective checks passed on current code:

- a landed pulse armed exactly the next four decisions; a K+1 mutant exposed
  a fifth active decision;
- the wq60 arithmetic changed a constructed strict decision and preserved the
  exact penalty multiset;
- permuting the real sensor association left the null unchanged, while a null
  that retained the association changed and was killed;
- an action alias was normalized to base, a distinct successor was retained,
  and a one-color-byte comparator mutant was rejected;
- four real exact-v8 base trajectories were action/outcome/pressure identical;
  220 actual-landed gated decisions exercised 11 treatment and 10 null
  distinct-state choices.

## Mechanism-only calibration

Seeds 70400..70639 were frozen before execution and followed base trajectories
only. Worker results deliberately omit result, clear, topout, stall, pill,
dies-ahead, and viruses-left fields.

| quantity | result |
|---|---:|
| seeds / plies | 240 / 33,664 |
| actual-landed active plies | 15,175 (45.08%) |
| landed pulses / cells | 5,109 / 11,366 |
| treatment distinct-state flips | 233 |
| shuffled-null distinct-state opportunities | 466 |
| alias normalizations | 218 |
| selected null distinct-state flips | 233 |
| realized aggregate dose mismatch | 0.00% |

The outcome-blind uint64 cutoff is
`9603181124656207259 / 18446744073709551616`. There were no hash collisions.
The null therefore clears the opportunity and aggregate canonical-dose
requirements; this is what `CALIBRATION_PASS` in the JSON means. It is not an
endpoint GO.

## Matching diagnostics

| diagnostic | treatment | selected null |
|---|---:|---:|
| games with a distinct flip | 96 | 109 |
| first-flip ply p10 / p50 / p90 | 29 / 56 / 115.5 | 30 / 58 / 115.0 |
| first-flip K-offset p10 / p50 / p90 | 0 / 1 / 2.5 | 0 / 1 / 3 |
| raw champion value gap p10 / p50 / p90 | 3 / 24 / 65.8 | 4 / 28 / 87 |
| successor Hamming p10 / p50 / p90 | 7 / 8 / 19 | 2 / 8 / 12.8 |

Timing and the medians are close, but the successor-distance tails are not:
the uniform null overproduces tiny perturbations and underproduces large ones.
That is the same kind of mechanism mismatch that invalidated the tie arm's
action-count null, although much smaller than its 10.82x distinct-dose defect.

## Decision

- Do not open endpoint seeds with this null yet. Aggregate dose equality alone
  is insufficient under the iteration's design laws.
- The next null revision may stratify its frozen hash cutoff by disclosed
  successor-Hamming, value-gap, K-offset, and timing bins. It must preserve the
  label-blind shuffled penalty assignment and re-pass alias, association, and
  base-identity mutants.
- Freeze quantitative distribution bands in a fresh endpoint preregistration
  only after that revision passes on new disjoint mechanism-only seeds. Do not
  change K, wq, or the hinge using this calibration.

Authority:

- `out/post_garbage_gate.json`
- `out/post_garbage_calibration.json`
- `out/post_garbage_calibration_audit.json` — endpoint-leak, duplicate-seed,
  and wrong-cutoff mutants all rejected
- `CALIBRATION_CONTRACT_POST_GARBAGE_V8.md`
