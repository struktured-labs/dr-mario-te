# R4 hang-term fidelity audit — pre-registration

**Frozen before running `hang_r4_fidelity.py`.** This is a retrospective implementation-
fidelity audit on the already-seen historical oracle pilot. It is not an endpoint efficacy
arm and makes no strength claim.

## Question

The deployed copro firmware scores a qualifying ply-1 hang as

```
40 + 20 * gap_rows
```

and credits it only when (a) the hovering half matches the first occupied landing cell's
colour and (b) that column contains a virus. The Python decision path called
`FastShipD3DeciderEH` instead uses the weekend-era flat `40 * g_hang`, with no virus-column
restriction. Does that known semantic difference materially change the champion root action
or the top-4 candidate set used by the oracle-ceiling arm?

## Frozen corpus and replay

- Input: `out/pilot_true/seg_030000.jsonl`, 125 paired games, identified by SHA-256 in output.
- Reconstruct the historical treatment trajectory exactly from seed and logged treatment
  actions. Require all 125 endpoints and all logged base actions/top-4 lists to replay exactly.
- Evaluate both semantics at every reconstructed treatment ply. Never use the R4 result to
  alter the replay trajectory.
- Report all plies, oracle-gated plies, and the 489 historical oracle-flip plies separately.

## Only changed quantity

For each legal root child, keep immediate reward, depth-2/3 search, leaf weights, temporal
blend, `g_excav`, `g_tower`, and `g_stranded` unchanged. Replace only

```
40 * fast_rtl_x._g_hang_ship(child)
```

with the firmware R4 weighted hang credit. Candidate enumeration and strict keep-first tie
breaking remain the champion's `[2,3,0,1] x columns 0..7` order.

## Required gates and killed mutants

1. The legacy recomputation must reproduce every logged base action and logged top-4 list.
2. A direct R4 mirror must agree with `nes_d3_golden._hang_credit` on deterministic random
   boards after the deployed R4 flags are set.
3. Three deliberately wrong mirrors must each disagree with ground truth on a purpose-built
   fixture: missing colour match, missing virus-column restriction, and flat rather than
   depth-proportional credit.
4. A changed logged base action and a changed logged candidate list must each make the replay
   gate fail.

No result is interpretable unless all four gates pass.

## Frozen interpretation

- **SEMANTIC MISMATCH**: any root-action or top-4-set difference. The Python arm is not an
  exact cartridge oracle under this condition.
- **MATERIAL FOR POLICY**: root-action difference on >=1% of all reconstructed plies.
- **MATERIAL FOR ORACLE ELIGIBILITY**: top-4 set difference on >=5% of gated plies, or any
  historical H15-selected treatment action absent from the R4 top-4.
- Otherwise record the defect as numerically negligible on this corpus. Do not tune the
  thresholds after seeing results.

Regardless of direction, this audit cannot say whether R4 is stronger than the legacy mirror.
An endpoint arm with a dose-matched null would be required for that claim.
