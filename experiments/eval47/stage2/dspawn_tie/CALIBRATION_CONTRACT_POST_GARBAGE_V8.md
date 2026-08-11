# Calibration contract — exact-v8 post-garbage K4/wq60 prototype

Frozen 2026-08-11 before running seeds 70400..70639. This is a mechanism-only
calibration under the design record, not an endpoint preregistration. Game
outcomes, pills-to-clear, and dies-ahead are neither returned nor inspected.

- Follow exact `firmware_v8/p2_surrogate` base trajectories under `exo_lulu`.
- Arm K=4 only from a positive change in the cumulative **landed** garbage
  counter. Offered volleys that land zero cells do not arm it.
- At active decisions, compute the frozen treatment and the shuffled-penalty
  null, normalize exact linked successor-board aliases to base, and record only
  canonical distinct-state opportunities.
- Seeds are 70400..70639, disjoint from the tie calibration/evaluation, the
  engineering smoke, the stage-2 corpus, and the remote oracle block.
- Structural calibration fails as `NOT_TESTABLE_NULL_OPPORTUNITY` if the null
  has fewer distinct-state opportunities than treatment. Otherwise freeze a
  label-blind uint64 hash cutoff selecting exactly the treatment count (ties at
  the cutoff fail closed). The realized calibration mismatch must be zero.
- Fewer than 100 treatment distinct-state flips is
  `NOT_TESTABLE_LOW_DOSE`; do not infer matching from a smaller sample.
- Report common gate duty and treatment/null distributions for first-flip ply,
  K-window offset, champion raw value gap, and exact successor-plane Hamming
  distance. These are the disclosed source for numerical matching bands in a
  later endpoint preregistration; they are not endpoint results and cannot be
  used to select a different K, hinge, or weight.
- The engineering gate must already pass. Runtime and gate hashes are recorded.

No endpoint seed range or GO rule is authorized by this contract.
