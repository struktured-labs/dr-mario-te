# Exogenous-pressure gate result

**Date:** 2026-08-11  
**Pre-registration:** `PREREG_EXOGENOUS_PRESSURE.md` at `c3bea64`  
**Implementation:** `a26ae00` plus the multi-height correction described below

## Verdict

**E1--E5 PASS.** `exo_lulu_v1` is a dose-matched, candidate-independent
pressure environment suitable for an oracle sensitivity pilot.  It does not
change or supersede the sealed coupled ORACLE-CLAIR run.

The registered E4 block was seeds 50,000--50,059, N=60, with the const-label
champion in both environments:

| measure | coupled Lulu | `exo_lulu_v1` |
|---|---:|---:|
| eligible plies | 7,453 | 8,531 |
| landed cells | 2,993 | 3,367 |
| landed cells / eligible ply | 0.401583 | 0.394678 |
| offered events / eligible ply | policy-dependent, not logged | 0.181221 |
| offered cells / eligible ply | policy-dependent, not logged | 0.405345 |

Exogenous/coupled landed-dose ratio = **0.982806**, inside the frozen
**[0.90, 1.10]** gate.

Other gates:

- E1 deterministic/exogenous PASS.  The coupled mutant was killed at seed
  50,000, pill 26: clear sizes 4 and 7 fired while 11 did not under the same
  random key.
- E2 colour precommitment PASS.  Its apply-time-colour mutant changed a later
  column's offered colour from 3 to 1 when an earlier column was full.
- E3 repeated const-policy identity 3/3; reversed tie-order mutant broke 3/3.
- E5 paired offer hashes match; arm-keyed schedule mutant killed.

The source fit was SHA-256
`7b4e564c2aae05d646d591682828dd7fc4e80c68b5aa20d45d413aee7a4e999b`.
The full ignored gate artifact is
`stage2/oracle/out/gate_exogenous_pressure.json` in the producing worktree.

## A gate caught a real bug

The first registered execution failed E4: exogenous landed dose was only
0.6091x coupled.  Inspection showed that the applicator rechecked row 0 between
two cells offered to the same column.  The first inserted cell occupied row 0,
so the second was incorrectly vetoed; 4-cell volleys were capped to one cell
per column.

The applicator was corrected to perform the capacity check once per column,
matching `inject_bursty_garbage`, and a new regression requires a two-column,
two-high offer to land all four cells on an empty board.  The unchanged
registered block was then rerun and passed at 0.9828x.  No oracle treatment
endpoint was read during this repair.

## End-to-end integration smoke (no endpoint authority)

Seed 50,060 completed through `run_oracle.py --model exo_lulu --future clair
--label true`: one pair in 82.65 core-seconds, 256 forks, 7/134 treatment
plies flipped, both arms cleared.  Base/trt landed 40/40 garbage cells.  N=1
has no strength interpretation; it establishes that the sealed runner shape,
runtime manifest, fork deepcopy, provenance, and exogenous hook work together.

## Interpretation boundary

The historical solo-Lulu arm is an upper bound inside a receiver-clear-coupled
proxy.  `exo_lulu_v1` repairs pairing but samples a marginal volley cadence per
receiver pill; it is not a literal simulation of dr. lulu's board or timing.
ROM-true, side-swapped head-to-head against a fixed opponent remains the
north-star gate.
