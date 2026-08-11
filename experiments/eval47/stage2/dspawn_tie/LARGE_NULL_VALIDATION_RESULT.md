# Result — large population-rate stratified-null validation

**Final 2026-08-11: `VALIDATION_PASS`. This authorizes an endpoint
preregistration draft, not endpoint execution or a cartridge change.**

The 1,200-seed fit block and 600-seed validation block were frozen in
`LARGE_NULL_RECALIBRATION_CONTRACT.md`. Both retained mechanism fields only.
The table at `champion-source:a749aa2` has SHA-256
`c64ce845e3e7d19242a359f868012bd04623c1bbee21d139202722f686e9c82d`
and uses fitted population cell rates rather than noisy training hash order
statistics.

## Fit

- seeds 71000..72199, N=1,200;
- 161,986 plies, 73,112 actual-landed active plies;
- 1,140 treatment distinct changes and 2,114 null opportunities;
- fitted expected null count 1,140 with exact treatment Hamming,
  early/late-timing, and raw-value-gap marginal counts.

## One-shot validation

| registered check | treatment | selected null | result |
|---|---:|---:|---:|
| canonical distinct-state dose | 585 | 616 | 5.30% mismatch — pass |
| Hamming-bin TV | | | 0.0270 — pass |
| early/late timing TV | | | 0.0388 — pass |
| raw-value-gap TV | | | 0.0600 — pass |
| K-offset TV | | | 0.0367 — pass |
| first-flip ply p10 | 30 | 32 | pass |
| first-flip ply p50 | 59 | 60 | pass |
| first-flip ply p90 | 118 | 112 | pass |

All minimum-dose, <=10% dose, four distribution, three first-timing, and three
killed-mutant checks passed. Validation seeds were 72200..72799, N=600. No
validation refit occurred.

## Meaning

The post-garbage candidate now has a label-blind null that is empirically
matched on canonical state dose, timing, champion value gap, successor-state
distance, and gate phase. This removes the known action-alias and random-churn
confounds from a future outcome arm.

It says nothing yet about whether K4/wq60 improves play. The treatment has only
been evaluated on base trajectories for mechanism calibration; no clear,
topout, stall, pills, or dies-ahead outcome was retained from any fit or
validation block.

Machine-readable authority:

- `out/post_garbage_large_null_training.json`
- `out/post_garbage_large_stratified_null.json`
- `out/post_garbage_large_null_validation.json`

