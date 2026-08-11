# P2 tracker ceiling-loss repair — instrument pre-registration

**Frozen before the repaired full-window output is generated.** This repairs an observation
instrument; it is not a player-strength arm.

## Observed defect

On dr. lulu match 3, the existing P2 tracker reports 19/93 AI capsules locking at row 0/1.
Frame inspection shows the dominant mechanism: the AI rotates vertically at the ceiling, one
half sits above the bottle for longer than the human-calibrated 12-frame loss threshold, and
the tracker permanently declares the half cleared. When the capsule becomes fully visible
again it is no longer searched for, so its spawn position is emitted as its lock position.

## Frozen repair

- A lost capsule may become `half_cleared` only after its last confirmed anchor is below row 1.
  A capsule last seen at rows 0--1 remains eligible for reacquisition indefinitely.
- If ordinary local search fails while the last anchor is at rows 0--1, retry across all eight
  columns but only rows within the existing vertical radius. This covers lateral steering while
  one vertical half is above the bottle. Existing anchor-grid rejection remains active so a
  static settled pair cannot win merely because search widened.
- No color, virus, grid, spawn, or lock threshold changes.

## Required gates and killed mutant

1. Synthetic state gate: the corrected predicate must not freeze a 12-frame loss at row 0,
   must freeze the same loss below the ceiling, and the old row-blind predicate must fail.
2. Match-3 control: preserve 90--96 tracked capsules and the visually verified late snap at
   t=596.35 s into cells `(8,6)+(8,7)`.
3. The row-0/1 false-lock count must fall from 19 to <=2. If it does not, the repair fails.
4. Emit to a new output directory; never overwrite the historical tracker files.

## Scope

This repair does **not** validate virus identity. The existing dark-pixel classifier undercounts
the on-screen virus counter (28 classified versus 41 displayed on a checked frame). Therefore
declined-clear and pills-per-virus/clear metrics remain blocked even if trajectory tracking passes.
They require a separate counter-calibrated virus instrument.
