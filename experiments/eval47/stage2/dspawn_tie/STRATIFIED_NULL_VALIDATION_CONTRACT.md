# Validation contract — stratified post-garbage null

Frozen 2026-08-11 before fitting the cutoff table or running validation seeds.
This repairs the disclosed successor-distance mismatch in
`POST_GARBAGE_CALIBRATION_RESULT.md`; it may not change K=4, wq=60, hinge=10,
the exact-v8 policy, pressure, or treatment.

## Fit on the disclosed mechanism calibration

Use only the raw distinct-state records from seeds 70400..70639. Bin every
treatment and null opportunity by:

- exact successor total Hamming: `0..4`, `5..7`, `8..11`, `12..19`, `20+`;
- decision ply: `<=70`, `>70`;
- champion raw value gap: `<=10`, `11..30`, `31..60`, `61+`.

Choose an integer count from each of the 40 null cells, bounded by available
opportunities, so selected-null marginal counts equal treatment exactly for
all five Hamming, both timing, and all four gap bins. Among feasible tables,
minimize L1 distance from the treatment's 40 joint-cell counts. Within each
cell, the selected count defines a uint64 cutoff at the corresponding ordered
label-blind hash. Bank the complete cutoff table before validation.

The fitter must reject endpoint fields, duplicate seeds, a wrong aggregate
cutoff, infeasible capacity, or non-exact fitted margins. It reads no outcome.

## One-shot fresh validation

- Seeds: 70700..70939, base trajectories under exact
  `firmware_v8/p2_surrogate` and `exo_lulu`.
- Return mechanism fields only; no result, clear/topout/stall, pills,
  dies-ahead, viruses-left, or time-to-end.
- Apply the banked cutoff for each null opportunity's fixed cell. No refit,
  alternate salt, or bin change is permitted on validation seeds.

Validation PASS requires:

1. at least 100 treatment and 100 selected-null distinct-state flips;
2. aggregate distinct-state dose mismatch <=10%;
3. treatment/null total-variation distance <=0.10 separately for Hamming-bin,
   early/late-bin, raw-value-gap-bin, and K-offset distributions;
4. selected-null minus treatment first-flip ply absolute differences <=20 at
   p10 and p90 and <=15 at the median;
5. all mechanism schema, ordered seed accounting, hash table, and killed-mutant
   checks pass.

Failure is `NOT_TESTABLE_STRATIFIED_NULL`; it blocks endpoint play and does not
permit another fit on these validation seeds. PASS authorizes drafting a new
N=9,000 endpoint preregistration only; it is not an endpoint or cartridge GO.

