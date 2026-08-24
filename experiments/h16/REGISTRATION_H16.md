# REGISTRATION — H16: THE ROLLOUT-GATED CHAMPION (function-class program, candidate 1)

**Status: DRAFT FOR TEAM-LEAD REVIEW — registered upon lead approval + commit.
Nothing beyond the design-side bank analyses in this directory has computed.**

Branch `h16-rollout-gated` (off `labels-146` @ 2ed5a02 — inherits the certified
rollout engine, the sealed oracle lineage, `h12_arm.py`, and `run_h14.py`).
Author: champion-design lane, 2026-08-24. Owner GO for the program; lead
reviews this registration before any evaluation compute.

**Timing proof:** at commit time this branch contains zero H16 game rows; the
registered seed block (§6.2) is untouched by any run (on-disk audit in §6.2).

---

## 0. Thesis and ancestry (the function-class argument)

Static linear evaluation cannot express the conditional "center use is
essential clean AND lethal when buried under contamination" — proven three
ways by the H15 family close (monotone worse at ALL doses down to structural
parity; see the three-line fit ledger in §6.7, which travels with this
document). Rollouts under the home-regime pressure model ARE conditional by
construction: they price the actual position, garbage and all. Full-width
rollouts at every decision are unaffordable (~176 forks x ~1 cpu-s at every
ply). H16 = **selective rollout adjudication**: certified H12 everywhere,
except when a cheap registered TRIGGER fires; then the candidates are
adjudicated by short CRN rollouts under the home-regime pressure model, and a
decisive rollout verdict — and only a decisive one — overrides the evaluator.

The label bank built by the garbage-labels campaign (1,344 states, per-
candidate N=8 CRN fork survival labels at H=25 under L20 lulu) is used ONLY
to set design parameters (trigger threshold, shortlist width, fork split,
decision thresholds) and to predict operating characteristics. **Firewall:
no banked state, banked seed, or banked label appears anywhere in the
evaluation of §6.** (Bank seeds 30000-32998 are disjoint from the §6.2 block
by construction.)

## 1. The candidate, exactly

H16Arm = certified H12Arm (topk 4, horizon 15, fork_samples 5,
theta_margin 0.5, future=dist, gate `d_spawn_h>=12 OR viruses<=8`, exact-tie
trigger — all knobs bit-identical) **plus one additive pre-pass** run before
H12's own logic at every decision ply:

1. **Trigger** (§2): fire iff `d_spawn_h >= 13` AND cooldown admits (§2.3).
2. **Adjudication** (§4): on fire, enumerate the dedup'd-by-resulting-board
   candidate set, screen ALL of them with 2 CRN forks, confirm a shortlist
   of 8 (+ champion's pick) with 6 fresh CRN forks, horizon 25, under the
   same lulu home-regime pressure model the game runs.
3. **Override rule** (§4): replace H12's action only on a decisive survival
   verdict. Otherwise (and on every non-fired ply) behaviour is **exactly
   H12Arm's**, its certified tie machinery untouched.

Observation set (ceiling-arm discipline): current board, cur+next capsules,
`(seed, ply)` for `dist_seed` CRN keys. Identical to H12's certified
observation set — no true-future access, no capsule clairvoyance.

## 2. Trigger — design data and registered choice

All numbers computed by `trigger_roc.py` / `trigger_roc2.py` /
`trigger_roc3.py` (this dir; outputs in `out/*.json`) from two existing
banks, read-only:

- **garbage label bank** (labels-146): 1,344 states; 274 CLAIM states under
  the registered claim rule (champ_surv<=5 & best-champ>=3 of 8 forks) =
  269 C-deep + 1 A + 4 C-mid — the certified "a materially better move
  exists" death-gateway states.
- **champ145 state bank**: 1,500 champion-const L20 home-regime games,
  364,052 plies, per-ply dsh/maxh/vir + per-candidate child spawn heights.

### 2.1 Registered primary trigger: `d_spawn_h >= 13`

`d_spawn_h = max(H[3], H[4])` on the current board (identical convention to
the sealed `heights()` / `gate_fires`). The spawn lane is the game's actual
top-out mechanism — a game ends when the spawn is blocked — and the measured
ROC bears it out at the home regime:

| statistic (bank) | value |
|---|---|
| catch: fraction of 274 claim states fired | **0.861** |
| catch by death-distance k=8/12/16/20 (C-deep claims) | 0.905 / 0.822 / 0.862 / 0.830 |
| fire rate, all plies (1,500-game bank) | 0.1195 |
| fire rate, cleared-game plies (healthy play) | **0.0655** |
| fire rate, healthy C-mid states (champ_surv>=7) | 0.138 |
| topout games with >=1 fire in the pre-lock-in window k in [10,25] | **0.812** (468/576) |
| lead-time: fire rate at k=1-5 / 6-10 / 11-15 / 16-25 / 26-40 before death | 0.91 / 0.73 / 0.62 / 0.48 / 0.36 |

The catch is flat across the k=8-20 death path, i.e. the trigger opens well
BEFORE the ~6-10 ply lock-in boundary — the prophylaxis window the C-deep
claims-secondary demanded (rescue converts poorly once deeply lost).

### 2.2 Alternatives measured and rejected (data, not taste)

- **maxh (any-column height): REJECTED — saturates at L20.** maxh>=12 fires
  on 0.74 of cleared-game plies (the L20 board is congenitally tall); it is
  not a trigger at the home regime. (`out/trigger_roc.json`)
- **vir>=9 conjunct (exclude endgame): REJECTED — halves the catch** (0.861
  -> 0.431): about half the claim states sit at <=8 viruses, where H12's
  gate is open but its exact-tie condition almost never fires. H16
  supersedes trigger-first there; H12 tie machinery still runs on
  fall-through.
- **min-child-dsh ("every placement leaves the lane tall"): REJECTED** —
  dominated by plain dsh at every threshold (fire 0.23 all-plies at >=12 for
  catch 0.942; worse knee than dsh>=13).
- **uncertainty / near-tie trigger: REJECTED BY MEASUREMENT** — see §5
  (H14a): 0.0% of claim states have the rollout-best candidate within
  H14a's trigger_eps=2.0 of the champion value (median gap 405 value
  units). A near-tie trigger structurally cannot reach this prize.

### 2.3 Cooldown (budget shaper, registered exactly)

Adjudication state per game: `(last_adj_ply, last_adj_dsh)`, initialised
(-inf, -1). On a ply with `d_spawn_h >= 13`, adjudicate iff
`ply - last_adj_ply >= 5 OR d_spawn_h > last_adj_dsh`; after EVERY
adjudication (override or not) set `last_adj_ply = ply,
last_adj_dsh = d_spawn_h`. Bank-simulated on the 1,500-game ply sequences:
mean **8.3 adjudications/game** (p90 19) vs 29.0 uncooled. The re-fire-on-
growth clause keeps the trigger live while a tower is actively building.

### 2.4 Scope caveat that travels (registered, honest)

The silicon pre-death boards (strata A/B — the L11 CvC autopsy taxonomy's
grind kill chain, which runs through EDGE towers) fire dsh>=13 at only
**0.18 / 0.11**. The registered trigger is tuned to and validated for the
**L20 lab home-regime endpoint of §6**, whose own death path it catches at
0.86. Porting H16 to L11/silicon regimes requires re-running this ROC in
that regime (regime-transfer trap, cf. the h13 gate lesson) — a maxh clause
is affordable there (max(H)>=13 = 13.6% of L11 plies per the 400-seed
census) but is NOT part of this candidate. The A/B strata are also nearly
claim-free (1/69) — mostly still-survivable boards — so this is a sensor-
scope note, not a lost-prize accounting.

## 3. Rollout budget (k x m x H), justified from the bank

- **Horizon H=25** — the bank's validated label horizon (split-half
  calibration rho +0.66-0.72 across strata at N=8). Keeping H fixed keeps
  the claim rule's validated semantics.
- **Screen: m1=2 forks x ALL dedup'd candidates** (median width 22 at claim
  states). Rationale: the H12 value ranking does NOT contain the prize — the
  value-top-5 contains ANY delta>=3 candidate in only 61% of claims (top-8:
  76%), and the rollout-best candidate's value rank is <=5 in only 28%. A
  cheap rollout screen over the full width is the only shortlister the bank
  certifies.
- **Confirm: m2=6 fresh forks x top-8 of the screen (+ champion's pick if
  not already in it)** => ~98 forks per adjudication.
- **Fork cost anchors** (labels campaign, measured): 0.718 cpu-s/fork
  blackmage unloaded / 1.11 redmage / 1.917 blackmage at load~50.
- **Per-game B-arm surcharge** (8.3 adj/game x ~98 forks): **~10 / 15 / 26
  min/game** at the three anchors. 600 B-games: **~97-260 core-h**. Games
  run slower than the lab baseline; that is acceptable and will be REPORTED
  (per-pair cpu_s is banked). Guard games (L11 clean) are expected to
  trigger rarely (no L11 clean bank exists — the realized guard trigger
  rate is a REPORTED quantity; the cost risk is bounded by the same
  cooldown).
- CRN keying: `fseed = dist_seed(seed, ply, sample)`, samples 0-1 screen,
  2-7 confirm — candidate-independent, so CRN holds across candidates
  (the bank's own construction).

## 4. Decision rule (registered exactly) and its simulated operating point

At an adjudicated ply, with `surv_m1(c)` = screen survival sum (0..2) and
`surv_m2(c)` = confirm survival sum (0..6):

1. Candidates = `labelcore.enumerate_candidates(env, dedup=True)` (unique
   post-placement resolved boards; unconditional never-same-board assert).
2. Screen every candidate: 2 forks each, `_fork_label` at H=25.
3. Shortlist = top-8 by `(surv_m1 desc, H12 value desc)`, plus the entry
   containing H12's chosen action if absent.
4. Confirm shortlist: 6 fresh forks each.
5. Let `champ` = the entry containing H12's action; `best` = argmax over the
   shortlist of `(surv_m2, H12 value)`.
6. **Override iff `surv_m2(champ) <= 3 AND surv_m2(best) − surv_m2(champ)
   >= 3`.** Play `best`'s representative slot. Otherwise fall through to
   H12Arm's unmodified decision (including its own tie-rollout machinery).

This is the bank's registered claim rule transported to decision time, in
conservative form (the confirm thresholds champ<=3-of-6, delta>=3-of-6 are
strictly tighter than the 8-fork claim rule's champ<=5, delta>=3). Simulated
EXACTLY on the bank's stored per-fork labels (fork indices 0-1 = screen,
2-7 = confirm — the same index split the online arm uses):

| operating characteristic | value |
|---|---|
| claims recovered (override fires and rule met) | **65.0%** (178/274) |
| good choices among recoveries (chosen candidate's full-8 gain >=3) | **98.3%** |
| false overrides on 1,070 non-claim states | **4 (0.37%)** |
| false overrides on 58 healthy (champ_surv>=7) states | **0** |

The knee sweep (m1 in {2,3} x keep in {5,8,12} x threshold variants,
`knee_sweep.py` -> `out/knee_sweep.json`) shows this is the best
precision/recovery corner: every looser rule (e.g. m1=3 with scaled
delta>=2: 82.8% recovery) pays 5.7% false overrides (61/1070) —
the churn profile that killed H14a and H15. H16 buys fewer, surer flips.
Expected flip character: ~0.5-1.5 overrides per doomed B-game, ~0.05 per
healthy game (adjudication rate x per-adjudication override rates above).

## 5. Prior-negative compatibility (each read, each distinguished)

- **[[dr-mario-capsule-lookahead-negative]]** closed capsule-information
  arms: clairvoyant/misinformed CAPSULE streams, deterministic deeper beams
  with the same evaluator ("any revival must beat the shipped brain with a
  BETTER EVAL, not with more capsules"). H16 adds no capsule information
  (dist futures only, cur+next observation set unchanged); its rollouts add
  a PRESSURE-CONDITIONED value signal — exactly the "better eval at the
  moment it matters" that negative demanded. No overlap.
- **[[dr-mario-depth4-memo]]** closed blanket and endgame-gated
  DETERMINISTIC depth (22.9x always, 23.2x endgame — branching ~30
  everywhere), and priced pressure-gated d4 at ~12x for ~38% coverage. Two
  distinctions: (a) H16's rollouts run the pressure model inside `_advance`
  — they see garbage ARRIVE, an event "no search depth can see" (that
  memo's own architectural finding: the champion's search has NO garbage
  model); (b) H16's cost is trigger-shaped (~8 adjudications/game), not a
  per-decision multiplier on every ply. The depth4 memo's open idea ("same
  trigger, different response — spend only where it pays") is what this
  registration operationalises, with a measured-ROC trigger.
- **[[dr-mario-h14-program]] (H14a NO-GO)** is the nearest prior art:
  rollout adjudication with the SAME engine, but triggered on near-ties
  (gate AND value margin <= 2.0). Measured on the claim states: the
  rollout-best candidate is NEVER within 2.0 value units (median gap 405;
  frac <= 2.0 = 0.0000). H14a widened a tie; the prize was never in ties.
  H16 fires on a danger signature and may override the evaluator's
  CONFIDENT choice — under a decisive-gap rule H14a lacked, on a shortlist
  chosen by rollout screening rather than by the (measured-blind) value
  ranking.
- **[[dr-mario-stage2-shippable-lut]] / [[dr-mario-eval-hacking-trap]] /
  H15's on-policy-blindness lesson**: those closed OFFLINE-FITTED artifacts
  promoted by label-side statistics. H16 fits NOTHING to the bank: the bank
  sets design constants; the decision signal at play time is a FRESH rollout
  of the actual position — on-policy by construction, and a non-decisive
  verdict plays H12 exactly, so there is no static dose to compound.
- **[[dr-mario-garbage-labels-campaign]] (H15 family close)** itself names
  the successor class: "a different INTEGRATION (search-coupled,
  conditional, or rollout-based) would be a new program". This is that
  program, first candidate.

## 6. Evaluation registration (house standard = H15's, inherited riders)

### 6.1 Arms and instrument

`run_h16.py` = additive delta on the sealed `run_h14.py` lineage
(level=20, max_pills=400, model=lulu honest bursty, provenance ON, per-seed
atomic + resumable segments, frozen META + runtime manifest):
- **A (base)** = H12Arm, certified knobs — the champion being challenged.
- **B (trt)** = H16Arm (§1).
Matched-index control: one work item = one seed = both arms.

### 6.2 Seeds (freshness audited on disk, 2026-08-24)

- The champion lane owns block **53100-59999** (PREREG_H14; minus the 20
  SILEVAL_EXCL seeds). On-disk audit of every endpoint dir in
  `champ145/out/endpoint/`: e1_true / e2_mutant / e2b_mutant span
  **53100-53700 only** (600 pairs each, same seeds — the dose-matched
  design); g1 used 30000-30007. **53701-59999 has never been played.**
- **Primary: the first 600 eligible seeds ascending from 53701** (eligible =
  in-block, not in SILEVAL_EXCL). **Guard: the next 1,000 eligible after
  the primary block.** Never pooled.
- **H15b/H15c's returned blocks 42000-43198 / 44000-45998 FAIL the
  freshness check and are NOT reused**: they lie inside the H12 endpoint's
  PLAYED block 41100-50099 (PREREG_ORACLE §A-14). Verified against the
  registration text; noted per lead instruction.
- Parity note: the block is consumed in plain ascending order (house
  convention, as H14 did). 2k/2k+1 share a capsule stream but not a garbage
  stream; pairing is within-seed, so the paired estimate is unaffected.

### 6.3 Primary endpoint

Failure (topout|stall) rate at L20 honest-lulu, 600 pairs. McNemar exact
one-sided + 10k seed-bootstrap CI. **GO requires p < 0.05 with d < 0.**

**Runner-level futility interims** (the H15 round-1 lesson: interims live
INSIDE the runner): in-process checks at n=200 and n=400 on ascending-seed
prefixes; STOP iff bootstrap CI lower bound > −0.01; a STOP halts the
primary AND stops the guard unit. Futility-only (alpha unaffected).

### 6.4 Guard (rider, unchanged trip rule)

1,000 clean L11 pairs (level=11 defaults, no injection). **Trip iff
d > +1.0pp OR one-sided 95% LB > 0 => automatic NO-PROMOTION**, readout led
by the trip. B-arm realized trigger/override rates at L11 are REPORTED.

### 6.5 Killed-mutant sheet (all must pass before E1; gate the object that
actually runs — the sheet drives H16Arm through `run_h16.py`'s own path)

1. **m-neverfire**: H16Arm with the trigger threshold forced unreachable =>
   full action-trace identity with H12Arm, 20 seeds (the H16 analog of
   m-dose0) — PLUS liveness: the same 20 seeds through true H16 must
   produce >0 adjudications, else the identity check is vacuous.
2. **m-ident**: A vs A, zero discordance, traces equal.
3. **G2 not-inert**: sheet seeds must show adjudications > 0 AND
   overrides > 0 (an arm that never binds tests nothing).
4. **m-swap**: scorer negation on a synthetic ledger (d -> −d exactly).
5. **m-nodedup** (population mutant, gate-standard #7): de-dup disabled =>
   screened population grows to the raw legal-slot count on the same
   boards; the never-same-board assert must trip on a constructed
   duplicate.
6. **m-cooldown**: cooldown disabled => adjudications/game grows by ~3.5x
   (bank-predicted 29.0/8.3) on the sheet seeds — the budget model is live.
7. **pressure-live**: injection counters > 0 in BOTH the game path and the
   fork path.
8. **E2 dose-matched null** (the endpoint's mutant arm): confirm-label
   shuffle across the shortlist at adjudicated plies, auto-thinned to match
   the true arm's FULL-N realized override RATE in [0.9, 1.1] (H14's
   anchor procedure verbatim, rate not count). The mutant must not read GO.
9. Runtime-manifest freeze per outdir + self-containment: the branch must
   rebuild the arm from its own tree (clean-clone lesson).

### 6.6 Power honesty

H14's realized geometry at these coordinates (600 pairs, 63 discordant)
resolved ~+/−2.6pp; the registered MDE statement is recomputed from
REALIZED discordance and travels with the verdict (achieved-MDE rule).
Expectation sketch, stated not promised: ~0.8 pre-lock-in opportunity rate x
~0.65 recovery x C-deep's measured 14% per-move rescue conversion, compounded
over ~1 override per doomed game against fail_A ~0.39, puts a plausible
effect at −3 to −6pp; the futility interims make a flat arm cheap.

### 6.7 Ancestry ledger (travels with any citation of this candidate)

H12 GO (+8.5pp clear, N=9,000; tie-only gated rollout) -> H13/gate-v2
declined at price, flip-screen route (center-blind framing dissolved) ->
H14a (near-tie widening eps=2.0) **NO-GO** (−1.5pp, p=0.31, inside the
dose-matched null) -> H15 fit ledger, inseparable three lines: (1)
A2-as-registered NO PASS (control mutant-proven defective); (2)
A5-as-computed NO PASS (unpassable-by-construction); (3) A5-corrected PASS
(design gate only) -> H15 round-1 GUARD TRIPPED / PRIMARY NO_GO
(slope-ratio dose explosion) -> H15b not registered (label-side selection
structurally blind to compounding) -> H15c STAGEA_NO_QUALIFIER — **the
linear-refit family is CLOSED** (monotone dose-response, function-class
verdict) -> **H16 (this document)**: the rollout-based integration the
close pointed to. The 1,344-state bank + claim rule are that campaign's
standing yield, used here as design fuel only.

## 7. Implementation plan (after approval; no evaluation compute before the
sheet)

- `experiments/h16/h16_arm.py` — H16Arm(H12Arm): the §1 pre-pass;
  `trigger_dsh` (13), `cooldown` (5), `screen_forks` (2), `keep` (8),
  `confirm_forks` (6), `rollout_horizon` (25), plus `never_fire` for the
  mutant. Reuses `_fork_label`, `dist_seed`, `enumerate_candidates`
  verbatim — no new rollout engine.
- `experiments/h16/run_h16.py` — additive `--trt-arm h16` delta on
  run_h14; runner-level futility per §6.3; guard stage per §6.4.
- `experiments/h16/gate_h16.py` — the §6.5 sheet.
- Compute: blackmage primary (systemd-run units, drm-h16-*); redmage may
  take gated work only after a fresh byte-equal whole-game trace check at
  the H16 code state (cross-box gate, same procedure as the campaign's).
- **OUT OF SCOPE: the FPGA/copro port.** A GO here defines a distillation
  problem, not a patch: the silicon home for this compute is the garbage
  window (264−16·h_min frames, median ~200f on real kill boards; the copro
  is measurably idle for 100% of it), and the §2.4 regime caveat means the
  silicon trigger must be re-derived in-regime. None of that work is
  licensed by, or a condition of, this evaluation.

## 8. Design-data provenance

`trigger_roc.py`, `trigger_roc2.py`, `trigger_roc3.py`, `knee_sweep.py` +
`out/*.json` (committed with this document) — bank-only, read-only,
reproducible from
the labels-146 label bank at
`~/projects/dr-mario-labels146-wt/experiments/labels146/garbage/out/labels/`
(1,344 segments) and the champ145 state bank at
`~/projects/dr-mario-champ145-wt/experiments/champ145/out/states/` (1,500
games). Known estimate-level caveats: (a) fire/budget rates come from
champion-CONST trajectories (H12's ~2% tie-flip dose shifts them slightly);
(b) B-arm trajectories diverge after the first override, so
adjudications/game in play is an estimate — the realized number is banked
and reported; (c) the bank's `tile`-class voids travel with the bank's own
registration.
