# P2 ceiling-loss tracker result

**Registered verdict: NO_GO.** The repair in commit `9d6e063` passed its synthetic
predicate checks and killed the row-blind mutant, but failed the frozen m3 film gates:

- reported pills: 99 (gate 90--96)
- row-0/1 locks flagged by the gate: 3 (gate <=2)
- registered late-snap validator: failed

The output is retained under `out/p2_tracker_ceiling/` and the historical tracker output
was not overwritten. These trajectories are **not authorized for behavior metrics**.

## Post-verdict diagnosis

The failure does not support reverting the ceiling repair. It exposed three errors in the
validation assumptions:

- The expected late horizontal lock is present as pill 23: spawn 595.667 s, lock frame
  2494, cells `(8,6)+(8,7)`. The validator searched near 596.35 s, which was a later
  lateral event rather than the spawn.
- Suspicious pills 18 and 57 were visually checked and are real high-stack locks. Pill 99
  is the incomplete capsule at the end of the capture, not a false lock.
- The repaired tracker separates six real capsules that the old tracker merged after a
  ceiling half disappeared and a consecutive capsule reused its colors. The full repaired
  counts are internally rate-consistent: m1 118/215 s, m2 150/284 s, m3 99/184 s.

This is useful mechanism evidence, but it is post-hoc. A fresh independent control is required
before the repaired tracks can support conclusions about play quality.

