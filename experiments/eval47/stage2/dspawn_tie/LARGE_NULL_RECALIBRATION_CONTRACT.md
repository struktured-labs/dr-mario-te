# Contract — large stratified-null recalibration

Frozen 2026-08-11 after the first stratified validation failed, before opening
any seed in the ranges below. This remains mechanism-only and cannot produce a
gameplay verdict.

Diagnosis to test: the 240-seed table overfit small-cell hash order statistics,
and its treatment/null opportunity ratio varied across seed blocks. Preserve
the already validated 5 x 2 x 4 Hamming/timing/value-gap bins and all K4/wq60
candidate semantics.

## Blocks

- Fit: seeds 71000..72199, N=1,200 base trajectories.
- One-shot validation: seeds 72200..72799, N=600 base trajectories.
- Exact `firmware_v8/p2_surrogate`, `exo_lulu`; mechanism fields only.
- Neither block may retain result, clear/topout/stall, pills, dies-ahead,
  viruses-left, or time-to-end.

Fit the same capacity-constrained integer table: exact treatment marginal
counts for Hamming, `ply<=70` versus later, and raw value gap; minimize L1 joint
cell difference. Unlike v1, each cell cutoff is the population-rate estimate

`round(2^64 * selected_count / null_capacity)`

not the training hash order statistic. Empty cells use zero; fully selected
cells use `2^64`. Bank and hash the table before validation.

The validation gates are unchanged from the first contract: >=100 flips per
arm, <=10% aggregate distinct-dose mismatch, <=0.10 TV for Hamming/timing/gap/
K-offset, and first-flip ply differences <=20 at p10/p90 and <=15 at median.
All schema/table/bin mutants must pass. Failure is final for this K4/wq60 null
design; do not fit a third table on validation seeds. PASS authorizes only an
endpoint preregistration draft, not endpoint execution or a cartridge change.

