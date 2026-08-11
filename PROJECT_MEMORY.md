# Project memory — next champion iteration

**As of 2026-08-11.** This is a compact resume point for humans and agents.
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
  mutation-gated, and landed in this writable clone at `200ab36`.
- Oracle work is sealed on `oracle-ceiling` at `29fc72c`. `ORACLE-CLAIR`
  intentionally sees the realized future: it is the unfair ideal-ceiling arm,
  not a candidate implementation. The shuffled-label null is dose-matched by a
  frozen endpoint-blind hash schedule (`q=0.169464`); reserved-seed accepted
  flip-rate ratio was 0.9271. DIST is implemented with collision-free,
  candidate-common pressure keys. Verdict, provenance, fork-leak, keying,
  thinning, and ordered-banking mutants pass. No current Tier-A endpoint run
  has started locally.

## 2026-08-11 progress and corrections

### Remote oracle

The project owner manually launched the 9,000-pair ORACLE-CLAIR Tier-A job on
Hetzner at `root@178.104.197.190` from `oracle-source` commit `29fc72c`, four
workers.  Projected wall time was roughly 82 hours.  This sandbox cannot open
SSH sockets, so the launch is **user-reported and currently unobservable** from
here; do not claim a completion or endpoint result without the remote files.
The shuffled-label null has not been reported as launched.

**Critical semantic label:** that remote job is
`historical_compact_cap1_flat_seed0`, not the shipped-v8 policy.  Do not call
its result a cartridge-v8 oracle ceiling, do not silently change its code or
META, and do not use a historical NO_GO to close root re-ranking for the cart.

### RESOLVED — exact shipped-v8 offline policy

The old py65 comparator cannot validate shipped v8.  Its engine shim calls the
stale cap-one golden, has no CMD-6/7 delta-engine semantics, omits link/fixpoint
gravity and chain-180, and discards the parent link plane.  Two prospective
py65 gates correctly banked NO_GO rather than blessing it.

The actual cart base policy is an unusual hybrid:

- main RTL search: parent links, link-aware fixpoint gravity, chain-180,
  complete depth-3 mechanics, R4 hang, and strand-20;
- root EH helper: the 6502 reconstructs the root child separately with its old
  targeted cap-one resolver and **cellwise** gravity, then scores
  `24*g_excav + R4_hang_credit`;
- EH is skipped on winning roots and roots with zero legal second placements;
- a nonzero per-match tie seed adds 0..3 before root argmax.  The offline
  `p2_surrogate` seed schedule is reproducible but is not a claim that wall-
  clock `NAV_T` is determined by game seed.

A dedicated writable clone, `cosim-source:firmware-v8-cosim`, runs the real
`CoproDrMario + LeafEval + 6502` under Verilator.  The first registered gate
matched 15/15 winners but only 14/15 candidate rings and banked NO_GO.  It
localized six losing actions exactly 100 points too high in the first mirror.
The no-ply2 and link-aware-replay explanations each failed their own frozen
localization.  The source-exact soft/cellwise EH replay fixed exactly those six
values.

Final registered result at `cosim-source:1cfb200`:

- non-debug action/winner 19/19 exact;
- debug action/winner 19/19 exact;
- **542/542 legal candidate values exact**;
- all full-child-EH, linked-replay-EH, no-ply-EH, compact-mechanics, flat-hang,
  no-link, seed-zero, byte-swap, +1-value and +1-count mutants killed;
- exact deployed firmware restored before/after:
  `e970e9ab0208cdbce1d39ed33e2f51ee`.

The fixed synthetic no-ply boundary board had only actions 19/27 legal;
hardware reproduced raw values -7128/-7048 and selected 27/-7046 after jitter.
Use `champion-source:firmware_v8_policy.py` at `3ad99ad` plus the no-ply helper
at `07dd629` as the authorized offline **base-policy** mirror.  This does not
validate the independent tuck extension.

### The running oracle and the cart are far apart

A frozen 40-game census on 5,081 actual-v8 trajectory states
(`champion-source:c409b39`) quantified the semantic drift.  At the unchanged
oracle gate (2,491 states):

- historical vs actual action disagreement is **31.59%** with both at seed
  zero and **44.64%** with the representative nonzero seed;
- historical vs actual seed-zero top-4 sets differ **59.69%**;
- representative-seed top-4 sets differ **64.35%** and orders differ 85.99%;
- the actual action is outside the historical top four **11.64%** of gated
  states.

Largest isolated action drift is complete mechanics vs cap-one R4: 26.62% at
the gate.  Flat hang adds 7.87%, links 3.85%, full-child EH 1.00%, and linked-
replay EH 0.20%.  Tie jitter is also material: some nonzero seed changes the
seed-zero action on 38.66% of gated states; a uniform nonzero draw changes it
19.64% of the time.

Future oracle infrastructure now has an explicit opt-in path:

```
--policy-semantics firmware_v8 --tie-seed-mode p2_surrogate
```

It controls root action, top-four ranking, and every fork ply.  The old path
remains the default.  Direct replay 6/6, historical and seed-zero mutants 6/6,
real root/fork routing, provenance, manifest hashing, resume locks, runner
banking, verdict mutations and fork-leak regressions all pass.  Durable record:
`champion-source:dbecb23`.  This is infrastructure GO only; a new outcome arm
still needs a fresh prereg, adequate N, and a dose-matched shuffled-label null.

### The historical Lulu pressure rig is policy-coupled

The old `lulu` solo proxy does **not** give candidates a fixed opponent attack
schedule.  Its fire probability is keyed to the receiver AI's **own clear
size**, then its RNG is keyed by `(seed, pills_placed)`.  A policy can therefore
change or suppress its own incoming pressure.  The fitted probabilities are
0.407643 for clear sizes 4--6 (`n=157`), 0.5625 for 7--10 (`n=16`), and 0 for
11+ (`n=2`).  This was documented in old bursty results but contradicted later
oracle prose claiming pressure was purely `(seed,pill)`.

Consequences:

- the running oracle still measures ideal headroom inside the historical proxy;
- a NO_GO there cannot close root re-ranking for real head-to-head play;
- after first treatment divergence, later self-coupled pressure is not a shared
  counterfactual schedule.

`champion-source:champion-next` now contains `exo_lulu_v1`, a complete pressure
offer frozen by `(version, seed, pills_placed)` before seeing the receiver board.
Its registered 60-seed E1--E5 gate passed: landed-dose ratio to coupled Lulu
0.982806, offer rate 0.181221, and all killed mutants passed.  Commits:
`5f0b431`, `c3bea64`, `a26ae00`, `ace203e`.  Use `exo_lulu` for future
candidate-sensitive science; keep legacy `lulu` only for continuity.

### What the historical oracle actually chooses

The available 125-pair ORACLE-CLAIR pilot was replayed exactly: 125/125
endpoints, all 489 logged flips and all top-4 sets reproduced.  Of 489 flips,
**478 selected greater 15-pill virus progress** and only 11 changed the binary
survival component.  Progress deltas were +1 on 325 flips, +2 on 96, +3 on 29,
+4 on 16, +5 on 5, +6 on 3, +8 on 5, and zero on 10.  Among bad-end→clear
rescues, 130/131 flips were progress choices and only one was survival-driven.
The missing faculty is therefore long-horizon clearing efficiency / sequential
myopia much more than a final-height veto.

A naïve candidate classifier stayed champion on every fold because 92.13% of
gated decisions are no-flips.  The correct structured question—first predict
*whether* to leave champion, then select ranks 2--4—does contain exploratory
signal: grouped-CV HGB trigger AUC/AP 0.7758/0.2336 versus shuffled-label
0.4846/0.0750; alternative accuracy 0.4949 versus 0.3333.  A depth-2 version
retained AUC 0.7563 and alternative accuracy 0.5399 versus null 0.4945/0.3088.

That compact policy then **failed to transfer** under candidate-independent
pressure.  Registered E0 seeds 51300..51359 passed every implementation/dose
gate (399 true flips, 401 null; flip-rate ratio 0.908; pressure ratio 1.016),
but true worsened bad ends +5.00 pp and clear -5.00 pp while the shuffled null
improved them -6.67/+6.67 pp.  Bad-end DiD was +11.67 pp, wrong direction; all
three nomination checks failed.  Verdict: **NO_NOMINATE this compact policy**,
not a lane closure.  Future teacher work needs temporal/trajectory vocabulary
or a real small rollout, not a more confident one-ply classifier.  Durable
record: `champion-source:263f23a`, `DISTILLED_TEACHER_E0.md`.

The historical oracle's own 489 flip states also show that short rollout
horizons are not a substitute for H15.  Exact agreement with H15 is H1 4.7%,
H2 7.6%, H3 9.8%, H5 14.9%, H8 23.9%, H12 48.9%, H15 100%; a random
alternative null is 33.1%.  Horizons through eight are worse than random at
reproducing the H15 choice.  Durable record: `champion-source:eb802d2` and
`ORACLE_HORIZON_SENSITIVITY.md`.

### Film telemetry did not expose a free opponent decoder

The repaired field tracker and two independently frozen counter-decoder
variants all returned registered **NO_GO** before any behavioural claim was
authorized.  The held-out V2 counter lane did not validate a reliable Lulu
attack-state signal.  Keep the reports
`P2_TRACKER_CEILING_RESULT.md` and `COUNTER_DECODER_RESULT.md`; do not promote
film-derived opponent state without a new measurement model and fresh holdout.
The result commit is `champion-source:361a7ca` (V2 prereg `9468a84`).

### Execution-fidelity lanes

- **Theta-400 Pocket: FIT/IMAGE-PROOF PASS.** `pocket-source:d30b52c` banks
  `NES_theta400_pocket_20260811.rbf` (SHA256
  `68d0d41f9a987c64742b7d625bf45c2ba0826db3f7469494da9c84fa30026b4b`).
  Quartus 23.1std.1 seed 8 used 18,262/18,480 ALMs, leaving 218 free against
  the frozen 200-ALM floor; worst and copro setup slack were both +1.682 ns.
  The post-fit ROM extractor found one valid half ordering and matched theta400
  16,384/16,384 bytes; wrong ordering differed 12,062 bytes and theta150/theta4000
  controls were each rejected by the expected two bytes.  This proves fit and
  image content, not Pocket runtime behavior or Pocket-specific value.  The
  cart-level value anchor remains -4.16 pills, not -11.
- **Tuck fall-budget guard: mechanism NO_GO.** `v8-source:e414e72` banks the
  six-arm 108,000-frame Mesen replay.  The unguarded controls reproduced 23
  completable synthetic tucks and four Pocket-v1 approach mislands.  Both the
  rewritten approach guard and the exact old/final-column mutant suppressed
  all four mislands.  Every control event had equal free-row readings in the
  two columns (`0/0` or `1/1`), so the stream contained zero
  predicate-discriminating faults and the killed mutant survived.  Do not run
  Gate 4 or claim the approach sensor caused the rescue.  Mesen's upstream
  built-in test runner was used because the sandbox denies Xvfb socket binds;
  it executes the real native core and Lua without Avalonia/X11.
- **Freeze discriminator: controls VOID the preregistration.**
  `freeze-source:0a0ac0e` banks the headless-Mesen control record and
  `freeze-source:9148bf5` makes the target runner stop after a failed control.
  The intended pause-positive control was classified `UNPAUSED_WEDGE`, while
  the intended healthy/unpaused control was classified `PAUSE_LOOP`; therefore
  seed 30011 was deliberately not inspected under this gate.  The runner used
  `probe_soak_fixed.lua`, which has no implementation for injection mode 3,
  and a natural mode-4 hold can exceed the frozen 600-frame threshold.  A
  fresh preregistration needs a proven START/pause fixture (the separate
  `probe_startpause.lua` does implement mode 3) and an independently proven
  CPU-loop fixture.  Do not reinterpret or rerun this prereg to obtain a
  target label.
- The theta fit and tuck replay are complete; do not rerun them merely to seek
  a friendlier result.  The freeze prereg is closed as `VOID_CONTROLS`; do not
  run its seed-30011 target stage.

The theta-400 Pocket image still needs actual Pocket runtime verification and a
Pocket-specific value A/B before promotion.

### Exact-v8 `d_spawn_h` tie-only arm is running

`champion-source:32bff12` preregistered a narrower resolution test than the
closed always-on penalty family: linked-fixpoint `d_spawn_h` may replace the
enumeration/jitter choice only inside an exact unjittered evaluator tie, and
never changes a strict decision.  The dose-matched null chooses another tied
action from `(seed,ply,T,base)` hashes without reading the board or sensor.

Implementation/gates are `25c9edc` / `ee3cfba`: 160/160 real legal masks
matched, four exogenous-Lulu base games were action/outcome exact, and clipped
sensor, gap-one, sensor-reading-null, legality and seed-zero mutants were all
killed.  Disjoint calibration seeds 60000..60239 found 200 flips / 33,409 plies
(0.599%), passing the 100-flip / 0.25% floors; null keep was frozen at
16,767/1,000,000 (`ae3019f`).  The 9,000 paired evaluation seeds 61000..69999
are running under candidate-independent `exo_lulu`, three arms per seed.  Do
not treat a partial prefix as a verdict; final dose must match within 10% and
both bad-end CIs (treatment-base and treatment-null) must exclude zero in the
beneficial direction for GO.

### `d_spawn_h` is already partly priced

The exact shippable S0 experiment (`d_spawn_h` alone, four-segment monotone
hinge) already exists: holdout float AUC 0.654299 versus champion 0.664504;
combined AUC 0.666965 (only +0.00246); B2 delta -0.0102 with CI spanning zero,
FAIL.  It was never rolled out at endpoints, so “never tested alone” is true
only for rollout, not for feature/value evidence.  SPAWN is primarily a dead-
zone sensor (zero for heights <=12 on 98.13% of cleared decisions), not merely
clipped at the top.  Do not fund a broad `d_spawn_h` sweep without accounting
for this prior negative and a dose-matched null.

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
8. After the first action divergence, later treatment events are not paired
   counterfactuals against the baseline trajectory.  A causal later-event
   comparison requires saved-state replay from the common predecessor.

## Immediate sequence

1. **RUNNING, user-reported:** historical Tier-A CLAIR on Hetzner. Preserve and
   analyse it as `historical_compact_cap1_flat_seed0`; its shuffled null still
   needs a reported launch. This sandbox cannot monitor SSH.
2. Do **not** let that result close the cartridge root lane.  If a new oracle
   arm is funded, preregister it separately with `firmware_v8`, explicit tie
   semantics, candidate-independent pressure, a killed dose-matched null, and
   N=9,000 or a declared undecidable clear co-primary.
3. The strongest new policy gap is sequential myopia: H15 choices are mostly
   greater virus progress, short horizons fail to reproduce them, and the
   compact one-ply teacher failed transfer.  Seek a shippable temporal/tempo
   vocabulary or a genuinely small rollout rather than another leaf reweight.
4. Preserve the completed theta400 image and tuck NO_GO.  The remaining Mesen
   execution lane is the freeze discriminator.
5. Do not promote film telemetry or compact DT2; both failed their registered
   screens.  `d_spawn_h` alone also has prior negative feature/value evidence.

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

This is no longer only a theoretical caveat: on actual-v8 trajectories the
cart's representative-seed top four differs from the running historical
oracle's set on 64.35% of gated states, and the cart action is outside that
historical top four on 11.64%.  The running arm therefore cannot be interpreted
as the maximum over the deployed cart's candidate set or continuation policy.

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
2. What is the empirical distribution and lifetime of the cart's `NAV_T`-based
   P2 tie seed on actual match hardware?  Until measured, keep `seed0`,
   `p2_surrogate`, and the all-seed envelope distinct.
3. Was the remote dose-matched shuffled-label null actually launched, and what
   output directories/META hashes identify the true and null jobs?  Do not
   infer this from the true-arm launch alone.

## Resume map

- Canonical plan: `v8-rematch:CHAMPION_ITER_PLAN.md`
- Flip provenance: `flip-provenance:experiments/eval47/stage2/rollout/`
- Oracle handoff: `oracle-ceiling:experiments/eval47/stage2/oracle/HANDOFF.md`
- Oracle prereg: `oracle-ceiling:experiments/eval47/stage2/oracle/PREREG_ORACLE.md`
- Exact cart policy result:
  `cosim-source:fpga/copro/FIRMWARE_V8_SOFT_EH_FINAL_RESULT.md`
- Cart-vs-historical census:
  `champion-source:experiments/eval47/stage2/oracle/POLICY_SEMANTICS_CENSUS_RESULT.md`
- Future cart-oracle mode:
  `champion-source:experiments/eval47/stage2/oracle/FIRMWARE_V8_ORACLE_MODE_RESULT.md`
- Required untracked lulu fit:
  `experiments/eval47/results/dr_lulu_20260808_fit.json`
