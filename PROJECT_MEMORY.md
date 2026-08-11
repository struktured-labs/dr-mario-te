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
- Oracle work is sealed on `oracle-ceiling` at `29fc72c`. `ORACLE-CLAIR`
  intentionally sees the realized future: it is the unfair ideal-ceiling arm,
  not a candidate implementation. The shuffled-label null is dose-matched by a
  frozen endpoint-blind hash schedule (`q=0.169464`); reserved-seed accepted
  flip-rate ratio was 0.9271. DIST is implemented with collision-free,
  candidate-common pressure keys. Verdict, provenance, fork-leak, keying,
  thinning, and ordered-banking mutants pass. No current Tier-A endpoint run
  has started.

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
2. **DONE at `oracle-ceiling:29fc72c`:** seal the ideal arm, dose-matched null,
   executable verdict, DIST implementation, provenance, and durable runner.
3. Launch Tier-A CLAIR plus its null. The paid CCX23 launch helper is ready;
   this sandbox cannot open SSH sockets. Full gates run before endpoint seeds.
4. Branch on valid calibration evidence. Independently continue the theta-400
   Pocket refit and tuck fall-budget guard rewrite.
5. Use seed 30011 opportunistically to build a real freeze discriminator.

## Adversarial gap audit — resolve before an oracle Tier-A run

These are findings from comparing the plan, preregistration, code, and original
oracle handoff. Resolved findings are marked below. They are not after-the-fact
Tier-A endpoint interpretations; current Tier-A data do not exist yet.

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

### RESOLVED — the oracle null violated the plan's dose law

The raw shuffled arm flipped 16.40% of plies versus CLAIR's 2.96%. Reserved
seeds 42000..42059 calibrated and validated deterministic SplitMix64 thinning;
the first passing fraction was q=0.169464 and produced 2.747% versus 2.963%
(ratio 0.9271). The full-N ratio must remain in [0.90,1.10] or the comparison is
VOID. No endpoint label enters the keep decision.

### RESOLVED — registered prose and executable verdict disagreed

The pre-fix defects were:

- `run_full.sh` ran `gate_identity.py` but not mandatory fork-leak gate G1g.
- `run_full.sh` launched `true` (clairvoyant) plus `shuffle`; it did not
  implement the A2 split (`DIST 9000`, DIST-shuffle 9000, CLAIR 2000).
- `stall_parity.topouts_converted_to_stalls` was a boolean based on aggregate
  signs, not the named paired transition count.
- Imported `verdict()` declared N3 only when the bad-end point estimate was
  nonnegative rather than when the bad-end CI included zero.
- Power adequacy was printed but did not control the returned verdict.

`29fc72c` enforces all of these in executable code, counts paired
topout→stall transitions, includes G1g in the launch path, and has a mutation
test in every verdict direction. A5 supersedes A2's authority split after the
programme lead clarified that the unfair CLAIR ideal is the requested primary
measurement.

### RESOLVED — `ORACLE-DIST` keying collided

The replacement packs `(seed, ply, sample)` injectively. G1h exhaustively
round-trips all 2.7 million registered seed/ply tuples, preserves
candidate-common randomness, and demonstrates an explicit collision in the old
formula.

### RESOLVED — interrupted segments were length-biased

The runner used `as_completed()`, so a kill banked quick games rather than the
registered ascending seed prefix; resumed summaries also described only newly
finished rows. A9 switches to ordered concurrent mapping and rebuilds summaries
from the full de-duplicated segment. The old scheduling mutant fails.

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

## Resume map

- Canonical plan: `v8-rematch:CHAMPION_ITER_PLAN.md`
- Flip provenance: `flip-provenance:experiments/eval47/stage2/rollout/`
- Oracle handoff: `oracle-ceiling:experiments/eval47/stage2/oracle/HANDOFF.md`
- Oracle prereg: `oracle-ceiling:experiments/eval47/stage2/oracle/PREREG_ORACLE.md`
- Required untracked lulu fit:
  `experiments/eval47/results/dr_lulu_20260808_fit.json`
