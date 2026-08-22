# labels-146 — ROLLOUT-LABELED FAILURE-REGIME COUNTERFACTUAL CAMPAIGN (H15 foundation)

Branch `labels-146` off `v8-rematch`; oracle machinery imported by content from
`champion-145` @ d3cb836 (`git checkout champion-145 -- experiments/eval47/stage2/oracle`),
so this branch is self-contained (dr-mario-clean-clone-repro lesson).
Bank read IN PLACE (data, not code):
`/home/struktured/projects/dr-mario-champ145-wt/experiments/champ145/out/states/`
(1,500 games, seeds even 30000-32998, L20 honest-bursty lulu, champion-const,
364,052 plies, per-ply 32-candidate values + child spawn heights; 576 topout /
163 stall / 761 clear).

## The one-sentence mission

Convert correlational knowledge into COUNTERFACTUAL labels — per-state,
per-candidate rollout-adjudicated survival values, harvested where failure is
abundant (home regime, 49.3% fail) — with a built-in held-out test that the
labels predict OUTCOMES (forced-move rescue), not champion agreement.

## Why every prior label effort failed, and what this design does about it

| prior failure | design answer |
|---|---|
| stage-2 LUT: labels predicted champion PREFERENCES (AUC .72), rollout NO_GO, label-blind null matched it | label = counterfactual OUTCOME (P(survive H) per candidate from N independent rollouts), and the acceptance test is a forced-move OUTCOME A/B, which a preference-mimicking labeler fails BY CONSTRUCTION (it makes zero counterfactual claims → FAIL_NO_CLAIMS; absence-is-not-pass) |
| label-quality-law: depth-2 labels 4.7x noisier, bimodal catastrophe = noise | in the failure regime the catastrophe IS the target. The label is the binomial survival rate itself, SE = sqrt(p(1-p)/N) ≤ 0.5/sqrt(N), and CRN (same dist_seed per sample index across candidates) makes the DIFFERENCES paired. The law's noise term was pills-to-clear polluted by rare failure; here failure is the measurand |
| clean-failure-rate: L11 failures unobtainably scarce (0.08%) | home regime L20+honest-bursty: 49.3% failure in the banked corpus — 576 deaths already on disk |
| gw-pricing-void: outcome deltas 0 by saturation; tie plies carry little value | no tie-triggered sampling. States are sampled by failure adjacency, labels priced in a regime where the baseline fails half the time — deltas cannot saturate at 0 or 1 |
| couch Q7: the real gap is invisible to humans and to the eval | labels come FROM rollouts (H12 fork lineage, sealed `_fork_label`), not from any eval or human judgment |
| stage-2 admissibility: features must be silicon-computable | each labeled candidate stores its full post-placement resolved board (color+virus planes, base64 in the row) — ANY future feature set, silicon-admissible or not, is computable offline later; admissibility is enforced at fit time, raw rows are never discarded (vocab-wall lesson: dump rows) |
| 301 broken games undiagnosable (no per-ply provenance) | every row carries seed/ply/replay-gate hash; every validation game logs the forced ply, action, and divergence outcome |

## Label spec (v1)

State = (seed, ply) in a banked game. Harvest unit = one seed (per-seed atomic,
resumable): replay the banked game ONCE under the replay gate (every ply's
computed 32-value vector and argmax must equal the banked row after round-3 —
cell-for-cell provenance that the state I label is the state the game had),
labeling at the seed's target plies during the pass.

Per target ply:
1. enumerate the 32 candidate placements (`_expand_core`, champion order);
2. de-dup by resulting-board sha1 (rule-7: double capsules make ~2x slots);
   keep the full slot list per unique board;
3. for sample s in 0..N-1: fork_seed = dist_seed(seed, ply, s) — identical
   across candidates (CRN); for each unique candidate run the sealed
   `oracle_arm._fork_label(env, slot, C, fork_seed, bmodel, ..., horizon=H)`
   → (survived, progress);
4. row = state metadata + champion vals + per-candidate: slots, board key,
   board planes (b64 of 128B color + 128B virus, post-resolution), per-sample
   (survived, progress) lists.

Headline counterfactual per state: dsurv = (max_c surv_c − surv_champ)/N with
paired CRN samples.

Pilot doses: N=8, H ∈ {15, 25, 40} on a subset to pick campaign H by the
pre-stated stability rule (PREREG §4). Prior cost: 1.07 cpu-s/fork @ H=15
(measured tonight in drm-champ-endpoint's SEGMENT SUMMARY: 3806 cpu-s / 3560
forks); replay 12 cpu-s/game (bank_run.log). Estimated pilot label cost at
H=25: ~18 uniq cands x 8 x 1.8s ≈ 260 cpu-s ≈ 4.3 cpu-min/state — re-measured
in the pilot; the ratio is the invariant, not the hours.

## Sampling rule (v1) — failure-preceding windows + contrast, NOT tie-triggered

- S-death: topout games, plies end−k for a k-window. Kill classification says
  97.5% of pre-death plies are already no-escape and the real decision sits at
  the TRANSITION into lock-in — so the pilot measures the dsurv-vs-k profile
  (k ∈ {1,3,6,10,15,20}) and the campaign window is chosen by the registered
  rule, not by eye.
- S-clear (contrast): plies from CLEARED games matched on the failed games'
  (vir, dsh) strata. Without this, a fitted evaluator can learn "this state
  came from a failed game" — a selection artifact, not a value.
- S-mid (campaign only): uniform plies from failed games outside the death
  window, small share, to anchor the easy end of the scale.
- Conditioning on the trajectory reaching the state is legitimate because the
  label is computed by FRESH rollouts from the state (never the observed
  outcome); what is biased is only the state DISTRIBUTION, which is exactly
  the distribution the evaluator will be asked to act on.

## Outcome validation (built in from day 1) — the anti-mimicry construction

CLAIM: a labeled state where dsurv ≥ delta (pilot: best−champ survival count
≥ 3 of N=8) — "the champion's choice loses ≥delta of survival vs the labeled
better candidate".

TEST per claim, on the claim's own game: arm A = the banked champion game
(outcome already on disk); arm B = replay to the ply under the replay gate,
force the labeled-best action, then the UNMODIFIED champion plays on under the
TRUE injection to game end. Paired failure outcomes; sign test on discordant
pairs (rescued vs newly-broken) + calibration (realized rescue rate vs
predicted dsurv). Note the transfer being tested is exactly the one that
matters: labels are computed under SAMPLED futures (dist), the validation game
runs the TRUE future.

Mutants (13-rule standard, each must FAIL the validation):
- M-mimic: labels = the champion's own candidate values → argmax = champion's
  pick at every state → ZERO claims → verdict FAIL_NO_CLAIMS. This is the
  preference-mimicking labeler failing by construction — proven by running it.
- M-shuffle: per-state permutation of the true candidate labels (dose-matched
  claim count) → its claimed "better" candidates must show no rescue.
- M-stale: replay desynchronized by one action → the replay gate must abort.
- M-dedup-off (population mutant, rule 7): unique-candidate count must GROW by
  the measured slot/board ratio; plus an unconditional never-same-board assert
  inside the dedup'd set.

## Budget math (priors; pilot re-measures)

- Campaign labels at N=8, H=25: ~4.3 cpu-min/label → 20 workers ≈ 4.6
  labels/min ≈ 280/h ≈ 2,200 labels overnight (8 h). Validation ~1 game/claim
  ≈ 15 cpu-s — noise.
- Signal sizing: per label-budget-rules signal ~ sqrt(R)/SE; here the target
  is a probability, SE ≤ 0.177 at N=8. A future fit consumes (state,
  candidate, surv/N) rows: pilot ~80 states ≈ 1,400 candidate rows; campaign
  first batch ~2,000 states ≈ 36,000 candidate rows with per-sample detail.

## Compute discipline

Local box only, $0. drm-champ-endpoint exited 20:56 EDT (G2 NOT-INERT gate
failure — champ lane's to fix); poll `systemctl --user is-active
drm-champ-endpoint` before every launch: active → ≤4 workers; not active → up
to 20. Units `drm-labels-<step>` via systemd-run --user, `set -eo pipefail`,
marker-gated stages, per-seed atomic, startup list-length asserts. No fresh
endpoint seeds are consumed: harvest + validation live entirely on the
already-consumed 30000-32998 even block (validation replays those same games —
no new seed material; the campaign's future fit/holdout split is declared in
the prereg WITHOUT consuming anything new).
