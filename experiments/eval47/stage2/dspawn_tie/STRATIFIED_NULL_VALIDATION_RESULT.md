# Result — stratified post-garbage null validation

**Final 2026-08-11: `NOT_TESTABLE_STRATIFIED_NULL`. Endpoint play remains
blocked.** The frozen table must not be refit on validation seeds 70700..70939.

The 40-cell table was sealed at `champion-source:34b8cbd`, SHA-256
`17d657d13946eec81cf28d7041ce5a0d8175b3c7983b044742da5be550e4a310`,
before the validator and fresh trajectories ran. The validator retained no
game outcome, tempo, dies-ahead, or time-to-end fields. All table/schema/bin
mutants passed.

## Frozen-gate result

| check | treatment | selected null | verdict |
|---|---:|---:|---|
| distinct-state dose | 327 | 258 | **21.10% mismatch — FAIL** |
| Hamming-bin TV | | | 0.0480 — pass |
| early/late timing-bin TV | | | 0.0035 — pass |
| raw-value-gap-bin TV | | | 0.0840 — pass |
| K-offset TV | | | 0.0893 — pass |
| first-flip ply p10 | 33.0 | 35.7 | pass |
| first-flip ply p50 | 56.5 | 63.0 | pass |
| first-flip ply p90 | 122.1 | 114.0 | pass |

There were 581 canonical null opportunities, so the failure is not lack of
possible distinct states. The fitted cell cutoffs selected too few of them on
the new block. Conditional on selection, the correction did solve the original
perturbation-shape problem: all four registered distribution distances passed.
But directionality still cannot be interpreted with a 21% dose deficit.

A disclosed post-result mechanism calculation localizes two causes. Applying
the frozen order-statistic cutoff probabilities to the validation cell counts
predicts 259.23 selected flips, essentially the observed 258. Thus the run did
not suffer a hash anomaly: small training cells encoded noisy order statistics.
Replacing them arithmetically with fitted `selected/capacity` rates would predict
281.49, still 14% below treatment's 327, exposing additional seed-block rate
heterogeneity. Neither calculation changes or rescues the registered verdict.

## Decision

- Do not open or name endpoint seeds for K4/wq60 yet.
- Do not multiply the cutoff by `327/258` or otherwise refit using this block;
  the contract explicitly makes it validation-only.
- The next defensible step is a fresh, larger mechanism-only calibration that
  estimates stratum acceptance rates with an independently registered dose
  prediction interval, or a null construction whose distinct-state count is
  intrinsically coupled to its own opportunity process. Preserve the validated
  40-cell shape controls rather than returning to uniform action flips.
- This is a null-design failure, not evidence for or against the treatment's
  gameplay value. No treatment endpoint was observed.

Machine-readable authority:

- `out/post_garbage_stratified_null.json`
- `out/post_garbage_stratified_validation.json`
- `STRATIFIED_NULL_VALIDATION_CONTRACT.md`

