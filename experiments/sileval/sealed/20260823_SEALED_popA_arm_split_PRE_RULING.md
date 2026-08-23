# SEALED — population A arm-split, computed 2026-08-23 BEFORE the arm-blind ruling

**STATUS: SEALED. Do not extend, recompute, or act on. Do not delete.**

## Why this file exists

These per-arm numbers were computed by the sileval-scorer lane on 2026-08-23 as part of
demonstrating that the E1 endpoint was recoverable from the banked population-A artifacts
at all, and were sent to team-lead in the same report. They were computed and transmitted
**BEFORE** team-lead's ruling that all circulated statistics must be pooled and arm-blind
until population B's measurand is registered. They were not computed in defiance of the
ruling; the ruling did not exist yet.

They are sealed rather than deleted because destroying an inconvenient computation is
worse than disclosing it: the record should show exactly what was known, by whom, and
when. Per team-lead, the leak is to be stated in the write-up's methods section, not
omitted.

## Containment (team-lead's assessment, 2026-08-23)

- Population A was **already ruled exploratory** — it was never the confirmatory test, so
  an arm-split look at A does not compromise a confirmatory claim that never rested on it.
- Population B is **uncollected**, so no one has seen its arm split; B's registration is
  genuinely blind.
- The live risk is the SPEC being tuned to A's arm-split. Mitigation: **swap authors the
  endpoint spec and stays blind to these numbers.** They have NOT been sent to swap.

## The numbers (source: e1_winner.py over out/, 255 OK rows, 4,589 samples)

Paired-only subset (126 seeds with both arms OK):

    ship  : 462/480 P2 wins = 0.9625
    slice : 485/496 P2 wins = 0.9778
    per-seed sign test: slice better 11, ship better 5, tie 110
    two-sided sign test on the 16 discordant seeds: p = 0.2101

All OK rows (129 ship / 126 slice, unpaired):

    ship  : P1=18  P2=473   P2 win rate 0.9633
    slice : P1=11  P2=485   P2 win rate 0.9778

## What this is NOT

Not an endpoint reading. No pre-registered analysis was run, no measurand was registered
at the time, and the population-A prereg treats these rows as exploratory. The pooled,
arm-blind figure — the one that IS authorised for circulation and for the power
calculation — is:

    n = 987 adjudicated matches, P1 = 29, P2 = 958
    pooled P2 share 0.9706, cluster-bootstrap 95% CI [0.9597, 0.9806]

Sealed by: sileval-scorer lane, 2026-08-23.
