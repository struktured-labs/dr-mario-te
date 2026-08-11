# Project memory — next champion iteration

**As of 2026-08-10.** This is a compact resume point for humans and agents.
The full plan of record is `CHAMPION_ITER_PLAN.md` on the `v8-rematch` branch.
When this note and that plan differ, the plan wins except where this note marks
a subsequently discovered defect.

## Strategic frame

North star: **build the best Dr. Mario player in the world on original NES
hardware.** Beating dr. lulu is an important near-term comparator, but dr. lulu
is itself a proxy rather than the final objective. There is not yet one trusted
scalar evaluation metric for world-best play.

The champion is already an excellent Dr. Mario player. It is strong over most
of the state distribution and occasionally makes conspicuously dumb decisions;
those tail failures currently appear to be what prevent it from beating lulu
or stronger opponents. The programme is therefore not searching for a
generally different player. It is finding those myopias, proving an instrument
can represent each one, and adding narrow directed behaviour while preserving
clean-game decisions.

This framing matters because churn is expensive: stage 2 changed only 1.8% of
plies but reshuffled roughly 20% of outcomes. An undirected always-on change can
erase a lot of already-good play.

Until a better scalar metric is established, evaluation is necessarily a
portfolio: opponent outcomes, rare-decision/blunder diagnosis, clean-play
non-regression, and behaviour on an OG-NES-representative execution path. No
single proxy gets to silently redefine the objective.

## Verified state

- v8 REMATCH is crash-hardening and execution fidelity, not a strength gain.
  The plan records the shipped cart as
  `c0082cb34259007854120d3d4ab9fa27`.
- Seed 30011's freeze is pre-existing and reproduces at the same frames on the
  unhardened cart.
- Stage-2 learned evaluator is **NO_GO**: dies-ahead moved -0.80 pp
  `[-2.20,+0.60]`; the dose-matched shuffled LUT did just as well; DiD was
  -0.27 pp. No directed endpoint transfer was established.
- Per-flip provenance began on `flip-provenance` at `5312267`. The shared
  evaluator/oracle schema convergence, including `d_spawn_h`, is completed,
  mutation-gated, and landed in this writable clone.
- Oracle work is on `oracle-ceiling` at `48cd4f6`. Identity, liveness, capsule
  independence, and fork-leak gates passed. `ORACLE-CLAIR` intentionally sees
  the realized future: it is the unfair ideal-ceiling arm, not a candidate
  implementation. `ORACLE-DIST`, the distribution-aware comparison arm, is
  preregistered but not yet implemented.

## Non-negotiable laws

1. Every arm has a **dose-matched, label-blind null**.
2. Every important check is demonstrated red on a deliberately wrong input;
   positive and null directions are both exercised.
3. Verdict rules, features, quantisation, seeds, and sample size are registered
   before outcome data.
4. Before threshold sweeps, prove the model or rig can represent the fault.
5. Stalls count at parity with topouts. Report paired topout-to-stall
   transitions, not only aggregate signs.
6. At stage-2 clear discordance, a +1.0 pp non-inferiority gate needs at least
   7,826 paired seeds; register 9,000 or declare the co-primary NOT DECIDABLE.
   The `N>=4,500` line in the plan's GO branch is stale and must not be used.
7. Per-flip mechanism data is mandatory and cheap: ply, time to end, viruses,
   height, spawn height, champion tie/rank/gap, and both actions.

## Immediate sequence

1. **DONE locally:** shared per-flip schema, clean gate, eight killed mutants,
   and a real 24-seed multiprocessing emission.
2. Resolve the oracle design gaps below **before** spending Tier-A compute.
3. Preserve `ORACLE-CLAIR` as the deliberately unfair ideal ceiling; implement
   and gate `ORACLE-DIST` to show how much of that ceiling survives without
   realized-garbage knowledge.
4. Branch on valid calibration evidence. Independently continue the theta-400
   Pocket refit and tuck fall-budget guard rewrite.
5. Use seed 30011 opportunistically to build a real freeze discriminator.

## Adversarial gap audit — resolve before an oracle Tier-A run

These are findings from comparing the plan, preregistration, code, and final
oracle handoff. They are not after-the-fact endpoint interpretations; the
headline `ORACLE-DIST` data do not exist yet.

### Structural-closure claim is currently too strong

`TOPK=4`, a fixed gate, a 15-pill horizon, and the lexicographic
`(survived, virus_progress)` label define one strong probe, not the maximum over
all root re-rankers. A finite-horizon probe can miss actions outside the top
four, delayed benefits, tempo/attack benefits, and faults already irreversible
when the gate fires. A NO_GO safely bounds this probe; it does not by itself
prove every root re-ranker structurally dead.

`ORACLE-DIST` with one sampled pressure future per ply is noisier than
expectimax. The prereg says this makes a NO_GO conservative. That direction is
reversed for a lane-closing claim: understating the attainable benefit makes a
false NO_GO more likely. K=1 may be a cheap screening arm, but structural
closure needs a preregistered K-sensitivity or an expectation-quality check in
the **NO_GO** direction as well as the GO direction.

The fork also sees future capsules, while the target sees only current `cA/cB`
and preview `nA/nB` at `$5080-$5083`. That unfairness is intentional in
`ORACLE-CLAIR`: an ideal ceiling should be as strong as possible. A GO measures
total headroom, not a directly shippable policy. Keep the foresight and label it
plainly; the follow-on work is to determine which fraction of that headroom can
be recovered with information available to the target.

### The oracle null violates the plan's dose law

The shuffled-label oracle is explicitly expected to flip more often than the
true arm. Calling the resulting DiD an upper bound does not make it
dose-matched. Before Tier A, calibrate a deterministic thinning/scale rule on
reserved, outcome-blind gate seeds and freeze it so the shuffled arm matches
the true arm's flip opportunity dose without using endpoint labels.

### Registered prose and executable verdict currently disagree

- `run_full.sh` runs `gate_identity.py` but not mandatory fork-leak gate G1g.
- `run_full.sh` still launches `true` (clairvoyant) plus `shuffle`; it does not
  implement the A2 split (`DIST 9000`, DIST-shuffle 9000, CLAIR 2000).
- `stall_parity.topouts_converted_to_stalls` is a boolean based on aggregate
  signs, not the named paired transition count.
- Imported `verdict()` declares N3 only when the bad-end point estimate is
  nonnegative. The oracle prereg says N3 also fires when the bad-end CI includes
  zero.
- Power adequacy is printed but does not control the returned verdict. A
  NOT-DECIDABLE clear co-primary can still flow through the ordinary GO/NO_GO
  function.

The verdict implementation and its killed-mutant tests must be extended before
the long run; prose alone is not a gate.

### `ORACLE-DIST` keying needs a collision audit

The registered key `seed + 7919*(ply+1)` collides across the 9,000 contiguous
seeds (for example seeds separated by 7,919 at adjacent plies). That creates
cross-seed dependence while the bootstrap treats seeds as independent. Use a
documented collision-resistant mix of `(seed, ply)` and prove candidate-common
random numbers plus cross-seed uniqueness on the registered block.

### Provenance durability still has two edges

- The plan calls out a missing first-divergence marker. It can be derived as
  the first flip per seed, but making that contract explicit avoids confusing
  later flips on the treatment trajectory with matched-base divergences.
- The evaluator runner flushes the JSON result before the separate flips CSV.
  A kill in that window causes resume to skip the seed forever with provenance
  missing. Embed flips in the atomic per-seed record or add a recoverable
  per-seed sidecar/journal. Also fail closed if an existing CSV header has an
  older schema.

### Endpoint relevance remains a final gate

The fitted lulu-pressure rig has about 80% base clear rate, below the 96.9%
label-quality screen, and dies-ahead is a proxy rather than an actual match win.
Dr. lulu is also a proxy for the real objective: best-in-world play on original
NES hardware. Use these endpoints to discover and price myopias, but promote on
converging evidence: fewer identifiable blunders, no broad clean-play
regression, stronger opponent results, and hardware-representative execution.
The project does not yet claim to know the perfect weighting of those signals.

## Questions whose answers change the experiment

1. How much K/horizon/action-coverage sensitivity is required before a NO_GO on
   the fixed top-4/H15/gated probe is allowed to close the broader root
   re-ranking lane? This question is about whether the probe reaches the ideal,
   not about making the ideal fair.
2. For dose-matching the shuffled oracle, is deterministic thinning calibrated
   on reserved gate seeds acceptable, or should both arms be matched online by
   a label-blind hash schedule fixed before endpoint runs?

## Resume map

- Canonical plan: `v8-rematch:CHAMPION_ITER_PLAN.md`
- Flip provenance: `flip-provenance:experiments/eval47/stage2/rollout/`
- Oracle handoff: `oracle-ceiling:experiments/eval47/stage2/oracle/HANDOFF.md`
- Oracle prereg: `oracle-ceiling:experiments/eval47/stage2/oracle/PREREG_ORACLE.md`
- Required untracked lulu fit:
  `experiments/eval47/results/dr_lulu_20260808_fit.json`
