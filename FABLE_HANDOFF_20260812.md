# Fable handoff — champion Dr. Mario programme

**Checkpoint: 2026-08-12 06:57 EDT.** This is a cross-lane resumption document,
not a replacement for preregistrations. Read `PROJECT_MEMORY.md` for the longer
audit trail and each linked preregistration before changing or interpreting an
experiment.

## The objective, stated correctly

Build the best Dr. Mario player in the world on original NES hardware.
**Beating dr. lulu is the next important human milestone, not the final
objective.** Dies-ahead, fitted-Lulu pressure, evaluator AUC, clear rate, and
even beating lulu are proxies. There is not yet one trusted scalar metric for
world-best play.

The champion is already very strong over most states and occasionally does
something conspicuously myopic. Broad perturbations are dangerous: changing
1.8% of plies in stage 2 reshuffled about 20% of game outcomes. The programme
should isolate rare faculties the champion lacks, demonstrate that the
instrument can represent them, and add directed behavior without disturbing
the rest of its play.

## What is running right now

Exactly one long experiment is still running.

| machine | job | checkpoint |
|---|---|---|
| Hetzner `rbm-train-2`, 4 vCPU/15 GiB, four workers | historical-policy `ORACLE-CLAIR`, true labels, N=9,000 | active; 1,148/9,000 ordered pairs at 2026-08-12 06:57 EDT |

Command to inspect it without changing it:

```bash
cd /home/struktured/projects/dr-mario-te/oracle-source
bash experiments/eval47/stage2/oracle/monitor_hetzner_oracle.sh \
  root@178.104.197.190 /home/struktured/.ssh/hetzner_rbm status
```

The unit is `drm-oracle-clair-a.service`, invocation
`24bc4c4abc4c4d1e889145c2c80435f0`. It passed the complete behavioral gate set
and is producing endpoint rows under sealed runtime manifest
`a67f47f15d4f82c125956dc2b37cc3c1bc1a0c84877310d5dfd27b96345b3bd8`.

This oracle is deliberately unfair: at registered danger/endgame plies it
forks the historical champion's top four candidates 15 pills forward through
the realized future and selects survivor-with-virus-progress. It measures
ideal sequential-decision headroom inside the historical fitted-Lulu rig. It
is **not** the shipped-v8 policy, not a shippable cart algorithm, not a direct
match against lulu, and not permission to close the cartridge root lane on a
NO_GO. The historical pressure model is also receiver-policy-coupled after a
trajectory divergence.

Only the true oracle arm is running. The registered dose-matched shuffled-label
null is not running. Do not issue a verdict from partial true rows or from the
true arm alone. At the observed speed, expect roughly another 65--75 hours for
true; measure rather than trusting that estimate.

## Result that completed at this checkpoint

The local `blackmage` exact-v8 post-landed-garbage K4/wq60 experiment completed
all 9,000 paired seeds and returned a registered **`NO_GO`**.

It used exact hardware-validated `firmware_v8/p2_surrogate`, exogenous
candidate-independent `exo_lulu` pressure, and base/treatment/matched-null arms
on seeds 80000..88999. Treatment penalized linked spawn-lane height for the
next four decisions after garbage actually landed.

| endpoint | treatment − comparator | paired 95% CI | result |
|---|---:|---:|---|
| dies-ahead vs base | **+0.1667 pp** | [-0.1222, +0.4556] pp | efficacy FAIL |
| dies-ahead vs null | -0.1556 pp | [-0.5003, +0.1889] pp | efficacy FAIL |
| bad ends vs base | **+0.3444 pp** | [-0.1222, +0.8000] pp | safety PASS |
| bad ends vs null | -0.5444 pp | [-1.0778, -0.0333] pp | safety PASS |

Counts were base 8,433 clears / 261 topouts / 306 stalls / 165 dies-ahead;
treatment 8,402 / 271 / 327 / 180; null 8,353 / 302 / 345 / 194. The point
estimates against base were worse, and neither dies-ahead efficacy comparison
excluded zero.

The null was valid and adequacy passed: 9,667 treatment versus 9,795 null
canonical state-changing flips, 1.046% dose mismatch, all four distribution
TVs below 0.10, and first-flip p10/median/p90 differences 0/2/4 plies. This is
not the earlier action-alias failure. Close this exact K=4/weight=60/hinge=10
functional form; do not tune it on seeds 80000..88999.

Durable result: `champion-next:3268774`,
`experiments/eval47/stage2/dspawn_tie/RESULT_POST_GARBAGE_V8_ENDPOINT.md`.
Machine result SHA-256:
`4a14c0c162c98c75f5164878c722e8b4a9ae2052695678de07fd1398b76e62b0`.

## What is already established

- v8 REMATCH shipped successfully but added crash-hardening and execution
  fidelity, not playing strength. Cart MD5:
  `c0082cb34259007854120d3d4ab9fa27`.
- The seed-30011 freeze is pre-existing: it reproduces at identical frames on
  the unhardened cart. The attempted discriminator is `VOID_CONTROLS`; its
  target stage was correctly not interpreted.
- Stage-2 learned evaluator is `NO_GO`. Dies-ahead moved -0.80 pp
  [-2.20,+0.60], while a dose-matched label-blind null did just as well; DiD
  -0.27 pp. Offline AUC did not establish directed endpoint transfer.
- Exact-v8 `d_spawn_h` tie-only resolution is `NO_GO`: it made dies-ahead worse
  by +0.200 pp [+0.022,+0.378]. The treatment-base negative stands; its null
  DiD was invalid because action IDs hid a 10.82x canonical-state dose gap.
- The compact one-ply/distilled teacher did not transfer under exogenous
  pressure and is `NO_NOMINATE`, not a lane closure.
- Film-derived opponent telemetry and both counter-decoder variants failed
  their registered screens. There is no free reliable Lulu state decoder.
- Theta-400 Pocket firmware **fit/image proof passed**. The banked image is
  `NES_theta400_pocket_20260811.rbf`, SHA-256
  `68d0d41f9a987c64742b7d625bf45c2ba0826db3f7469494da9c84fa30026b4b`.
  This is not Pocket runtime validation or a Pocket-specific value result.
- The tuck fall-budget replay was mechanism `NO_GO`: approach and old/final
  guards both suppressed the observed faults because the corpus never made
  their sensor readings differ. Do not claim the rewritten predicate caused
  the rescue.
- The exact shipped-v8 offline policy mirror is now source-exact against the
  real coprocessor plus 6502 helper: 542/542 legal candidate values matched and
  all registered mutants were killed. Use this mirror for future cart-policy
  science; the historical oracle differs materially from it.

## The most useful remaining clue

The historical H15 oracle pilot's 489 flips were overwhelmingly about clearing
progress, not last-moment survival: 478 chose greater 15-pill virus progress;
only 11 changed the survival component. Of 131 bad-end-to-clear rescues, 130
were progress choices. Short rollouts do not approximate this faculty: exact
choice agreement with H15 was H1 4.7%, H2 7.6%, H3 9.8%, H5 14.9%, H8 23.9%,
H12 48.9%; a random alternative scored 33.1%.

That points to **sequential clearing efficiency / tempo myopia**, not merely a
height veto. A one-ply classifier and two spawn-height interventions have now
failed to transfer. A promising next mechanism should add temporal vocabulary
available on the real target, or a genuinely useful compact rollout, and must
explain why it can represent the H15 faculty before spending another 9,000
seeds.

## Oracle integrity incident—do not rediscover it

A11 found the Hetzner service burning deterministic gate retries because G1c's
historical wrong lambda had been fixed upstream. The gate now constructs its
bad input inline, and mandatory preflight failure exits 125 with systemd
restart prevention.

A12 then caught a remote runtime-manifest mismatch after a stop was requested
at 42 rows; 13 in-flight results flushed, leaving 55. The only differing file
was `nes_pills.py`, selected differently because of host-path-dependent
`sys.path` order. All 55 rows are void and quarantined both remotely and at:

```text
/mnt/data/dr-mario-te/hetzner/quarantine_wrong_manifest_75e36d0e_20260811/
```

Seeds 30000..30054 replayed from a clean registered directory. A12 preloads
the sealed QA module in an oracle-scoped Python bootstrap and now checks the
rolled runtime hash before the hour-long gates. Repair commit:
`oracle-ceiling:e306177`. Never merge quarantined rows into the valid run.

## When the true oracle finishes

1. Confirm the service is complete, true rows are exactly 9,000, seeds are the
   ordered block 30000..38999, and META contains rolled hash `a67f47f...`.
2. Fetch a final snapshot; do not analyse the live partial directory:

   ```bash
   cd /home/struktured/projects/dr-mario-te/oracle-source
   bash experiments/eval47/stage2/oracle/monitor_hetzner_oracle.sh \
     root@178.104.197.190 /home/struktured/.ssh/hetzner_rbm fetch \
     /mnt/data/dr-mario-te/hetzner/oracle_clair_true_final_202608
   ```

3. Run the registered dose-matched shuffled-label null on the same seed block
   and same sealed decision runtime before a verdict. Frozen keep fraction is
   169464/1000000; full-N null/true flip-rate ratio must be [0.90,1.10]. The
   null is slower than true. Local `blackmage` is now free, but launching it is
   an explicit compute decision; do not silently change workers, paths, source,
   pressure, or semantics.
4. Analyse only after both complete. A true GO with a GO null is `VOID`; dose
   mismatch is `VOID`; stalls count at parity with topouts; clear adequacy must
   be printed before the verdict.
5. Phrase the conclusion narrowly: ideal headroom in the historical coupled
   proxy. It is calibration evidence about sequential myopia, not cart-v8
   headroom and not proof of match strength against dr. lulu.

Authoritative oracle files are on `oracle-ceiling`:
`experiments/eval47/stage2/oracle/PREREG_ORACLE.md` and `HANDOFF.md`.

## Design laws that survive every handoff

1. Every intervention carries a dose-matched, association/label-blind null.
   For policies, dose means canonical exact successor-state changes, not action
   integers; also match timing, champion value gap, state distance, and duty.
2. Every important gate must fail on a deliberately wrong input in every
   relevant direction.
3. Preregister verdicts, features, quantization, seeds, and power before
   endpoint data. At stage-2 discordance, +1 pp non-inferiority requires at
   least 7,826 pairs; register 9,000 or declare it undecidable.
4. Topouts and 300-pill stalls are equally bad ends. Report paired transitions,
   especially topout-to-stall conversion.
5. Save per-flip mechanism data. After first divergence, later treatment events
   are not paired counterfactuals unless replayed from a common predecessor.
6. Ask whether the model can represent the observed fault before sweeping a
   threshold. Do not use endpoint seeds to tune a failed arm.
7. Promotion ultimately requires OG-NES-representative execution and converging
   evidence across direct opponent results, identifiable blunders, and
   clean-play non-regression. No proxy silently becomes the north star.

## Branch and artifact map

| purpose | branch / commit |
|---|---|
| durable cross-lane memory and this handoff | `flip-provenance` (handoff commit follows this file) |
| exact-v8 post-garbage final NO_GO | `champion-next:3268774` |
| historical oracle and A12 repair | `oracle-ceiling:e306177` |
| public current README | GitHub `main:5ddc320` |
| exact cart-policy cosimulation proof | `firmware-v8-cosim:1cfb200` |
| theta-400 Pocket fit | `pocket-source:d30b52c` |
| tuck-guard mechanism result | `v8-source:e414e72` |
| freeze controls/void result | `freeze-source:9148bf5` |

Local worktrees under `/home/struktured/projects/dr-mario-te/`:

- `source/` → `flip-provenance`, durable memory;
- `champion-source/` → `champion-next`, exact-v8 science and final local result;
- `oracle-source/` → `oracle-ceiling`, live remote oracle source;
- `readme-main/` → current public README branch.

The required Lulu fit is intentionally untracked in several worktrees:
`experiments/eval47/results/dr_lulu_20260808_fit.json`. Do not delete it merely
to obtain a clean status.

## Questions still worth answering

- What temporal state or compact computation can recover the H15 progress
  faculty on original NES hardware without broad churn?
- What is the actual distribution/lifetime of the cart's `NAV_T` P2 tie seed
  in match hardware? Until measured, keep seed-zero, `p2_surrogate`, and an
  all-seed envelope distinct.
- What direct head-to-head or hardware-representative instrument should become
  the promotion gate beyond the fitted-Lulu proxy?
- Can first-divergence saved-state replay create a causal corpus of the rare
  dumb decisions, instead of training on treatment trajectories after they
  have already diverged?

Do not restart completed theta, tuck, film, tie-height, compact-teacher, or
post-garbage arms to seek friendlier results. Their negative/void outcomes are
useful constraints. The live oracle plus the sequential-myopia evidence are
the current forward edge.
