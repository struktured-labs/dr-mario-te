# Complete v8 offline policy mirror — pre-registration

**Frozen after the cap-one R4 gate failed on seed 30000, and before any assembled-firmware
decision from seed 30001 or later was observed.** The failed gate established that R4 hang
alone is insufficient: the offline oracle policy also omitted link-aware fixpoint resolution
and the shipped `DRCHAIN=180` cascade reward.

## Path under test

The new explicit path is named `firmware_v8`. It combines only mechanics and constants already
present in the shipped base firmware:

- `winner` RTL leaf weights and flags;
- link-aware body gravity and resolve-to-fixpoint at every searched placement;
- immediate `180*viruses + 10*cells + 180*(chain_rounds-1)`;
- full 32-action root, top-K2=8, four-pill third-ply expectation, discount shift 1;
- excavation weight 24 and R4 weighted/virus-column-only hang;
- root-only stranded-half cost 20;
- strict keep-first action order `[2,3,0,1] x columns 0..7`.

It does not add tucks. Historical `FastShipD3DeciderEH`, `firmware_r4`, corpora, and the
running Hetzner result retain their existing meanings.

## Implementation lockstep

With R4 disabled in the new candidate-valued implementation, its argmax must match the
pre-existing `cascade_stranded_x._choose_d3_chain_s` action on 200 deterministic boards.
An order-reversed implementation must disagree on at least one deliberately tied fixture.

## Prospective complete-decision gate

Play the frozen legacy champion through real Lulu-pressure states, starting at seed 30001.
Before querying firmware, retain the first three otherwise-unused states in each stratum:

1. **mechanics-sensitive:** `firmware_v8` action differs from cap-one `firmware_r4`;
2. **hang-sensitive:** `firmware_v8` action differs from the identical full-mechanics path
   with legacy flat hang;
3. **control:** `firmware_v8`, cap-one R4, and full-mechanics flat-hang actions all agree;
4. **tie-control:** a fixed empty-board equal-pill case where reversing scan order must change
   the selected tied action (if the empty board is not tied, deterministically scan reachable
   states for the first exact top-value tie before seed 30064).

For strata 1--3, refuse to run if three cases cannot be found by seed 30063 or 300 plies per
seed. The assembled tuck-off `DRFIX=1`, `DRCHAIN=180`, `DRSTRAND=20` firmware must match
`firmware_v8` exactly on chosen action and signed 16-bit winning value for all nine real-game
cases. The firmware source revision and image hash are recorded.

## Checks that must fail

- cap-one R4 must disagree with firmware on every mechanics-sensitive case;
- full-mechanics flat hang must disagree on every hang-sensitive case;
- a +1 predicted-value mutant must fail exact value comparison;
- reverse tie order must fail the tie-control;
- the R4 term gate must continue to kill missing-color, missing-virus-column, and flat-depth
  mutants.

Any required-stratum shortage, action mismatch, value mismatch, or surviving mutant is NO_GO.
A pass authorizes the path as a v8 observation/simulation instrument only; strength still
requires a separately preregistered paired endpoint arm.

