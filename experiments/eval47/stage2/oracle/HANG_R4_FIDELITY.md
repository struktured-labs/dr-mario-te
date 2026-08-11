# R4 hang fidelity — the historical Python champion is not the cartridge policy

**Date:** 2026-08-11  
**Authority:** retrospective implementation-fidelity audit only; no strength direction  
**Pre-registration:** `PREREG_HANG_R4_FIDELITY.md`  
**Raw output:** `out/hang_r4_fidelity.json` (gitignored)  
**Pilot SHA-256:** `398c4bca66e5554f160c24b3fbd5a923e8b88de4f034bb00fc4c5b71c845319e`

## Result

The function described throughout the offline stack as `FastShipD3DeciderEH` does not
implement the deployed copro's R4 hang term. The difference is policy-material and
oracle-eligibility-material under the frozen thresholds.

| reconstructed treatment states | n | root action changed | top-4 set changed | top-4 order changed |
|---|---:|---:|---:|---:|
| all plies | 14,427 | **1,505 (10.43%)** | **4,261 (29.53%)** | 5,503 (38.14%) |
| oracle-gated plies | 6,215 | **801 (12.89%)** | **2,186 (35.17%)** | 2,592 (41.71%) |
| historical H15 flip plies | 489 | 51 (10.43%) | **157 (32.11%)** | 202 (41.31%) |

Most legal children have no hang term at all (median absolute candidate-value delta 0),
but the affected children move by enough to reorder close root decisions: mean absolute
delta 30.96, p95 120, maximum 500 eval units over 423,242 legal children.

The strongest consequence is eligibility: **65/489 (13.29%) of the actions selected by
the historical H15 oracle are absent from the corrected R4 top four.** A top-4 oracle
cannot choose those actions when its baseline/candidate generator matches the cartridge.

## What is wrong, exactly

The firmware's R4 `eh_terms` implementation correctly requires all three conditions:

1. occupied non-virus half with an empty cell directly below;
2. first occupied landing cell has the same colour as the hovering half;
3. the column contains a virus.

It then credits `40 + 20 * gap_rows`. The Python path uses the older flat
`40 * _g_hang_ship`, which keeps condition 1 and the colour match but omits the virus-
column restriction and depth weighting. The field report that a mismatched colour was
being credited is therefore **not confirmed in firmware**. The audit it prompted still
found a larger simulator-versus-cartridge defect.

## Gates

- Historical trajectory replay: 125/125 endpoints exact; all 489 logged base actions and
  top-4 sets exact.
- R4 mirror: 256/256 deterministic random boards exactly match the copro source golden.
- Killed mutants: missing colour match, missing virus-column restriction, and flat-depth
  variants each fail on their own fixture.
- Replay mutants: changed logged base action and changed candidate list are both rejected.

## Consequence for the running Hetzner oracle

Do **not** discard or stop the run. Its manifest honestly freezes the historical Python
policy, and its result will measure H15/top-4 headroom inside that proxy. But it is no
longer valid to call the result a calibration of the shipped v8 policy or to branch the
firmware evaluator lane solely on its verdict. This is not a small numerical caveat:
candidate membership changes on 35% of the exact states where the oracle gate fires.

The minimum corrective path is:

1. make an explicit `firmware_r4` root-value path rather than silently changing the
   historical mirror;
2. prove its weighted hang term against the copro golden and its complete root decision
   against firmware/py65 on a real-board census;
3. run a small candidate-independent-pressure R4 oracle/null pilot before funding a
   second Tier-A run;
4. preserve the current remote result under the label `legacy_flat_hang` for continuity.

The audit does not establish that R4 is stronger or weaker. That requires an endpoint arm
with a dose-matched label-blind null; implementation fidelity alone has no favorable sign.

## Reproduction

```bash
NUMBA_CACHE_DIR=/tmp/numba-exo \
DR_LULU_FIT=/home/struktured/projects/dr-mario-te/source/experiments/eval47/results/dr_lulu_20260808_fit.json \
/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python \
  experiments/eval47/stage2/oracle/hang_r4_fidelity.py --workers 4
```

Wall time on the local 16-core box: 284.3 seconds with four workers.
