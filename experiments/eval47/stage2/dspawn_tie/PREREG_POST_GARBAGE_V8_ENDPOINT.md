# Preregistration — exact-v8 post-landed-garbage K4/wq60 endpoint

**Sealed 2026-08-11 before endpoint-runner implementation or opening any
endpoint seed. Execution requires an explicit owner launch.**

## Question and frozen candidate

Does a narrow spawn-lane penalty immediately after opponent garbage reduce
dies-ahead without sacrificing the champion's already-strong clean play?

- Base: exact hardware-validated `firmware_v8/p2_surrogate` policy.
- Pressure: candidate-independent `exo_lulu`.
- Gate: exactly the next K=4 decisions after one or more garbage cells
  **actually land**. A new landed pulse rearms K=4.
- Treatment: during the gate, subtract
  `60 * max(0, d_spawn_h_linked - 10)` from every exact unjittered root value,
  then apply unchanged v8 jitter and champion ordering. Outside it, play base.
- Null: assign the same penalty multiset without its real action association,
  normalize exact linked successor aliases to base, then accept canonical
  distinct changes by the frozen 40-cell table in
  `out/post_garbage_large_stratified_null.json`, SHA-256
  `c64ce845e3e7d19242a359f868012bd04623c1bbee21d139202722f686e9c82d`.
  Its bins are exact successor Hamming, ply <=70/later, and champion raw value
  gap. It reads no future, outcome, survival/progress label, or treatment
  endpoint.

K4/wq60 was externally nominated once from the disclosed historical screen;
K, weight, and hinge may not be swept on these data. The exact-tie resolver is
a separate closed NO_GO and is not combined with this arm.

## Population and banking

- Seeds **80000..88999**, N=9,000 paired seeds, disjoint from every fit,
  calibration, validation, stage-2, and oracle block.
- Each work item runs base, treatment, and null for its seed. Arms follow their
  own trajectories after divergence.
- Bank ordered resumable JSONL segments with an immutable runtime manifest and
  embedded per-seed flip provenance. Duplicate, missing, malformed, or changed
  META rows fail closed.
- A topout and a 300-pill stall are both bad ends at parity.

## Null validity gates

Before endpoint interpretation, require:

1. >=100 canonical distinct-state flips in treatment and null;
2. aggregate distinct-state flip-rate mismatch <=10%;
3. treatment/null TV <=0.10 separately for Hamming bin, ply <=70/later, raw
   value-gap bin, and K-offset;
4. absolute first-flip-ply differences <=20 at p10/p90 and <=15 at median;
5. no action alias counts as a flip and every table/runtime hash matches.

Failure returns `NULL_INVALID_NO_GO`. Treatment-versus-base estimates may be
reported as descriptive candidate evidence, but direction versus matched churn
is undecidable and the arm cannot GO.

## Endpoints, adequacy, and verdict

Primary efficacy is paired dies-ahead; clean-play safety is paired bad ends.
Use paired seed bootstrap CIs (B=5,000, RNG 20260812) and exact McNemar tests.

Before the verdict, print observed discordance, analytic paired SE, 95%
half-width, and whether a +1.0pp bad-end non-inferiority margin is reachable.
N=9,000 exceeds the iteration's 7,826 floor, but observed adequacy remains a
mandatory computed gate.

`GO` requires all of:

1. valid null gates above;
2. dies-ahead treatment-base 95% upper bound <0;
3. dies-ahead treatment-null 95% upper bound <0;
4. bad-end treatment-base 95% upper bound <+1.0pp;
5. bad-end treatment-null 95% upper bound <+1.0pp; and
6. the observed bad-end margin is statistically reachable.

Otherwise verdict is `NO_GO`, or the explicit null/adequacy non-verdict label.
Secondary outputs are clear/topout/stall counts and all paired transitions,
common-clear pill difference, landed pressure, active duty, and churn.

## Required implementation gates and killed mutants

- exact base action/outcome identity against the authorized v8 mirror;
- actual-landed K4 pulse; offered-but-zero-landed does not arm; K+1 fails;
- table hash/cell accounting; a one-byte table mutant fails;
- penalty multiset and sensor-association invariance; an association-reading
  null fails;
- exact successor alias normalization; one changed color/link byte fails;
- all Hamming/timing/gap boundary bins; <=5 and <=11 mutants fail;
- null selection on the frozen N=600 validation records reproduces all 616
  selected changes and every registered distribution gate;
- verdict mutations fail in both dies-ahead directions, both bad-end safety
  directions, null dose/shape, adequacy, and missing provenance.

Every endpoint flip logs seed, arm, ply, `t_to_end`, viruses, max height,
pre-board spawn height, landed-gate offset, base/chosen action, raw champion
value gap, base/chosen linked height, plane-wise Hamming, matching cell, and
champion rank. First divergence is derived as the minimum logged ply.

This experiment changes no cartridge, firmware, RTL, Pocket image, or remote
oracle job.

