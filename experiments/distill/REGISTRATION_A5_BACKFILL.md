# AMENDMENT A5 — DANGER BACK-FILL (registered 2026-08-28, distill-coproc lane)

> # ⛔ READ THIS BLOCK BEFORE ANY OTHER LINE OF THIS FILE
>
> **APPEND-ONLY (R25): the front is the oldest text, the binding text is at the
> end.** Four revisions follow the original §§1-5, and each supersedes numbers
> above it. Build the void list here FIRST.
>
> | superseded / void | replaced by | what changed |
> |---|---|---|
> | §2 sizing (held-danger STATES; "1.40x clears it") | **R1.1** | ⚠ wrong AXIS — the CI is seed-CLUSTERED. Real power **34%**, not 80%; the signed n=273 was the **50%** point |
> | §3 procedure (W=30 window, **topout-only** games) | **R1.1 (PHASE 1)** | superseded: outcome selection + density distortion. Now a whole-game census of **held-out** games |
> | §2 cost model (`369 + 0.869·forks`) | **R1.2 → R2.1** | ⚠ TWICE wrong. R1.2 over-corrected to 0.227 (death-window). **Firm: 0.805 s/fork, PHASE 1 ≈ 100 core-h** |
> | §4 density rider (1.9x enrichment correction) | **R3** | the census has **NO composition difference** — 100% of held-danger is trigger-class ⇒ post-stratification is provably inert |
> | §5.1 arm P as PRIMARY / base-only leading | **R4.3** | the **pooled census GATES**; base-only is the continuity check |
> | §2 "no new seeds" for the top-up | **R4.1** | the top-up SPENDS this lane's own reserve (19900-20898, 128 held-hashed seeds). Registry records it CONSUMED |
>
> **UNCHANGED THROUGHOUT — the bars.** GO ≥0.129 with clustered CI LB >0.099;
> KILL if UB <0.099. No revision relaxed a criterion; R1.1 made the estimand
> *stricter*.
>
> ⚠ **The L11M arm is scoped separately (§1, §5.3): it re-measures the L11M
> INSTRUMENT and does NOT contribute to the M2 fit verdict.** Its result (a
> retraction) lives in `REGISTRATION_M3_AB.md` S7.1.

Amends `REGISTRATION_M1_LABELS.md` (label production) and
`REGISTRATION_M2_SCREENS.md` (the fit that consumes it). Approved in principle
by the team-lead 2026-08-28 with a power calc and a density rider; **this
document is the registered form, and it corrects the stratum the approval
named.** No bar is changed. Nothing here is a slide.

---

## 0. PROOF OF TIMING (R28)

At the moment this file was committed:

- `out/labels_m1/L20_backfill/` — **does not exist**
- `out/labels_m1/L11M_backfill/` — **does not exist**
- `out/m2_features/` contains **`L20` only** (base-bank features)
- The only M2 fit reading in existence is the pre-A5 one: g_lin held-out danger
  capture **0.0645 CI [0.0123, 0.1305]**, g_feat1 **0.0538 CI [−0.0575,
  0.1667]**, held-danger **n=93**.

Every decision rule in §5 therefore predates the data it will judge. The
projections in §2 are computed from the **already-banked** height traces and a
cost model fitted on the **already-banked** base bank — they consume no new
labels and commit no verdict.

---

## 1. THE CORRECTION: A5 RUNS ON L20, NOT ONLY L11M

**The approved text says "the same 63 banked topout games". 63 is L11M's
topout count. The M2 fit is L20-only** (`m2_screens.stage_fit()` calls
`assemble("L20")`), and the `held-danger n=93` that binds it is L20's.

The committed `stage_backfill` (commit 21d0af4) is hardcoded to L11M
(`BF_OUT = out/L11M_backfill`, `M1HarvestArm("L11M", ...)`,
`load_segments("L11M")`). **Run as literally specified it would add zero rows
to the bank the M2 fit reads**, and the re-fit would reproduce the identical
BETWEEN verdict at the identical n.

The approval's *per-game* projection was sound (+15–20 danger states/game; I
measure **18.4 trigger plies/game** on L20). Only the game count came from the
wrong stratum. **L20 has 254 topout games, not 63.**

⇒ A5 is registered here as **two arms with two different jobs**:

| arm | job | decides |
|---|---|---|
| **A5-L20** (new, pivotal) | enlarge the L20 danger bank | the M2 GO/KILL/BETWEEN verdict — the thing the power calc sized |
| **A5-L11M** (as committed) | enlarge the L11M **instrument** n | whether "teacher verdict not distillable at L11M" is a program finding or an n=55 artifact |

A5-L11M is retained deliberately: M2 is L20-only precisely *because* L11M
showed no measured headroom at n=55, and the M2 instruments memo made A5's
re-measure the decider on that question. It is not a consolation arm.

---

## 2. MEASURED PROJECTION (recomputation, not assertion — R25)

Producer: `tmp/distill/scratch/a5_project.py`. Trigger plies counted from
banked height traces with the stratum's own trigger; degeneracy, danger rate
and forks/adjudication measured on the base bank's **own late-trigger states**
(the population A5 will sample), not on the bank average; held/train split is
the fit's own `crc32(seed) % 4 == 0`.

| arm | topout games | adjudications | non-degen | held-out | **new held-danger** | core-h |
|---|---|---|---|---|---|---|
| **A5-L20** | 254 | 4,671 | 4,363 | 933 | **≈289** | 122 |
| A5-L11M | 63 | 1,709 | 1,215 | 351 | ≈25 | 42 |

Rates behind the table:

| | L20 | L11M |
|---|---|---|
| degenerate, late-trigger | 0.066 | 0.289 |
| danger \| non-degenerate, late-trigger | **0.310** | 0.072 |
| danger \| all trigger states (base bank) | 0.161 | 0.034 |
| forks/adjudication | 89.8 | 96.2 |

**The death window is ≈1.9× danger-enriched on L20** (0.310 vs 0.161). That
enrichment is A5's entire mechanism and it is also the density change the rider
is about — see §4.

**Sizing check against the team-lead's requirement (~273 held-out danger
states):** A5-L20 takes held-danger **93 → ≈382, clearing at 1.40×**. A5-L11M
takes L20's held-danger **93 → 93**, and L11M's danger n **55 → ≈142 (2.6×)**.

**Cost model**, fitted on the base bank in the same script that spends it:
`L20 secs = 369 + 0.869·forks − 0.368·plies` (R² 0.702);
`L11M secs = 126 + 0.900·forks − 0.251·plies` (R² 0.803).
Total **≈164 core-h** labels + **≈25 core-h** feature derivation = **≈190
core-h, EUR 0** (blackmage local). No new seeds.

**Seeds:** A5 replays seeds already consumed by this lane's M1 campaign
(L20 17700–19098 step 2, L11M 19100–19898 step 2).
`tools/seed_registry.py --check 17700 700 2` returns the expected
**self-collision against `distill-coproc M1 labels`** — the correct reading for
a replay. **No stream is newly consumed and no block is claimed.**

---

## 3. PRODUCTION PROCEDURE (unchanged from the approved design except stratum)

For each **topout** game in the base bank of the named stratum:

1. Replay the game with `M1HarvestArm(stratum, seed, mode="backfill",
   window_start = max(0, n_plies − 30))` — the **same producer path** as the
   campaign (`m1_harvest.py`, schema `m1v1`), label path untouched.
2. Adjudicate **every** trigger-firing ply with `ply >= window_start`.
   **No thinning, no cap, no band/healthy/random classes.** Class tag is
   `["backfill"]`.
3. **REPLAY GATE**: the replayed 8-column height trace must equal the banked
   trace **exactly**, or the game banks nothing and is reported FAILED.
   Champion-const determinism is asserted, never assumed. A non-zero fail count
   exits 3.
4. Segments land in a **separate directory** (`out/labels_m1/<STRATUM>_backfill/`)
   with the density rider in `META.json`. **They are never written into the base
   bank directory.**

**FORMAT-IDENTITY GATE (new here, required by the team-lead: "verify by
hash/schema, don't assume").** Before any backfill segment is consumed, assert
against the base bank:
- `schema == "m1v1"`;
- the top-level key set equals the base bank's **plus exactly**
  `{backfill, window_start, replay_gate}`;
- the adjudication-record key set is **identical** to the base bank's;
- the per-candidate record key set is **identical** to the base bank's;
- `sha256` of `m1_harvest.py` matches the value frozen in the base bank's
  `META.json` runtime manifest — i.e. **the label producer did not move**.
Any mismatch is a hard stop, not a warning.

**SMOKE FIRST**: 4 games per arm, format-identity gate + replay gate green,
before the full arm launches. 122 core-h is not spent on an unverified path.

---

## 4. THE DENSITY RIDER (team-lead's condition, stated numerically)

Backfill states differ from base-bank states in **three** measured ways, not
one:

1. **Position**: 100% lie in the final 30 plies; the base bank's trigger states
   are spread across the game (uniform `THIN_P` thinning, so the base bank's
   position distribution is unbiased for the deployed trigger).
2. **Danger density**: 0.310 vs 0.161 — **1.9× enriched**.
3. **Class composition**: 100% trigger-class; the base bank also carries
   band / healthy / random states. The random-quota sample that makes E-M1c
   trigger-independent **has no backfill counterpart** — backfill can never
   contribute to a trigger-independent estimate.

⇒ **Consumers stratify or weight. Pooling silently is forbidden.** Any statistic
computed on the enlarged bank must declare which population it targets.

⚠ **Second-order consequence the approval did not state, and it is the bigger
one:** the train/held split is **by seed**, so backfill adds to **TRAIN as well
as HELD** — train-danger goes ≈260 → ≈1,323 (≈5×). **The re-fit therefore
changes the fitted guard, not only the precision of its evaluation.** A movement
in held-out capture cannot be attributed to added precision alone. §5 separates
the two effects rather than leaving them confounded.

---

## 5. PRE-STATED READING OF THE RE-FIT (bars unchanged)

**Bars, unchanged and not renegotiable here:** danger capture **GO ≥ 0.129 with
clustered CI LB > 0.099**; **KILL if UB < 0.099**; measured shuffle floor 0.069,
tribunal ceiling 0.269. Statistic, ruler (eval-half `s2[3:6]`), decision shape
and seed-clustered bootstrap are `m2_screens.py`'s existing ones — unchanged.

### 5.1 Arms reported (all four, always, in one emission)

| # | arm | population | purpose |
|---|---|---|---|
| **P** | **PRIMARY** — pooled, **re-weighted to the base bank's ply-position density** | targets the registered estimand | **gates the verdict** |
| S1 | pooled, unweighted | robustness to the weighting choice | **co-gates** (see 5.2) |
| S2 | base-only (n=93, untouched) | continuity | is the estimate SETTLED or MOVING (R13 corollary)? |
| D | backfill-only | diagnostic | does the death window behave differently? |

Plus one decomposition arm, pre-stated to keep §4's confound out of the verdict:

| **F** | **`g_lin_frozen`** — the *pre-A5* fitted weights, unchanged, evaluated on the enlarged held-out set | isolates **added evaluation precision** from **added training data**. A move in P that F does not share is a training-data effect, not a precision effect. |

### 5.2 The verdict rule (anti-cherry-pick, two-sided per R53)

- **GO** iff **P and S1 both** satisfy `capture ≥ 0.129` **and** `CI LB > 0.099`.
- **KILL** iff **P and S1 both** satisfy `CI UB < 0.099`.
- **Otherwise BETWEEN** — and if P and S1 disagree on the verdict, **the
  disagreement is the reported finding**: the weighting is load-bearing, which
  is itself a result about the population, and no verdict is claimed.

S2 (base-only) **does not gate**. It cannot: at n=93 its UB is 0.1305, so a
base-only kill is arithmetically impossible and requiring it would make the
KILL path vacuous — the exact defect A5 exists to remove. S2 is reported for
continuity only.

**Registered in advance so it cannot be chosen later:** if the enlarged P lands
in BETWEEN *again*, that is a **STOP on M2's fit question**, not a third
back-fill. A5 was sized to be decisive at 1.40× margin; if it is not, the
binding constraint was never n, and the next spend belongs to M3's on-policy
question, not to more offline labels.

### 5.3 What this amendment does NOT cover (R24)

- It does **not** re-open E-M1a/b/c. Backfill states are excluded from every M1
  endpoint; the traces they replay are byte-identical to the banked ones (that
  is what the replay gate asserts), so no M1 number can move.
- It does **not** change the deployed trigger, the wide12 labeling ruling (R1),
  or the false-veto re-scoping. Those are M3's.
- It does **not** extend M2's scope beyond the tribunal's **shortlist**;
  unrestricted deployment remains M3's question, as originally registered.
- A5-L11M **re-measures the L11M instrument**; it does **not** license an L11M
  fit. Whether L11M enters M2 at all is a separate decision on the re-measured
  ceiling.

---

## 6. STATUS

Registered 2026-08-28 by the distill-coproc lane. Team-lead notified of the
stratum correction with the §2 numbers **before** any compute was spent.
Launch proceeds on the smoke gate; the full arms follow only if the
format-identity and replay gates are green.

---

# REVISION 1 — 2026-08-28, same day, BEFORE any arm was scored

Two corrections to §2 and §3, both found by measurement rather than review.
The bars in §5 are **unchanged**. Nothing below relaxes a criterion; the
design change makes the estimand *stricter*, not looser.

## R1.1 — THE SIZING WAS ON THE WRONG AXIS (the material one)

§2 sized A5 by the number of held-out DANGER STATES. **The M2 CI is
seed-clustered, and back-fill adds states to games that already contribute —
it adds no GAMES.** Both the team-lead's approval calc and this amendment's
first draft scaled a clustered SE by `n_states`. That is the R47/R48 family
and it inflates the projected power badly.

**Measured law** (subsampling the banked danger states on each axis
independently, `scratch/se_law.py`):

> **Var = (0.0524 + 0.0712 / s) / n_games**,  s = danger states per game

`0.0524` is a between-game floor no back-fill can remove. In the sweep, at 175
games tripling s moved SE 0.0257 -> 0.0240 (7%); going 20 -> 175 games moved it
0.0643 -> 0.0240 (2.7x). The law overpredicts absolute SE by 1.54x at the
reference point, so **only its ratio is used**, calibrated to the observed
held-out reading (R62's habit applied to a variance model).

Corrected power for a KILL at today's point estimate (0.0645 vs the 0.099
line):

| design | held games | held danger | SE | power |
|---|---|---|---|---|
| pre-A5 (today) | 38 | 93 | 0.0301 | 21% |
| A5 as approved (W=30, topout-only) | 54 | 383 | 0.0221 | **34%** |
| **PHASE 1 — un-thin ALL trigger plies in held-out games** | 119 | 785 | 0.0150 | **63%** |
| PHASE 1 + 175 fresh held-hashed games | 246 | 1,623 | 0.0104 | 91% |

⇒ **§3's procedure is superseded by PHASE 1** (`--select held --window` unset).
Beyond the power, PHASE 1 removes three defects the approved design carried:
- **outcome selection** — "topout games only" conditions the evaluation
  population on the game's eventual result, which the deployed guard cannot
  see ([[dr-mario-flip-capture-selected-on-outcome]]);
- **position-density distortion** — a census of held-out trigger states needs
  no reweighting, so §4's rider becomes a robustness check rather than a
  correction the verdict depends on;
- **the training confound of §4** — train is untouched, so arm F ≡ arm P and
  the result is cleanly "same guard, measured better".

**Power depends on the true capture, not only on n** — PHASE 1 is ~100%
powered against capture ≤0.032 and 52% at the floor, i.e. decisive against
"this guard is worthless" and weak only in the narrow band just below the bar.

## R1.2 — THE COST MODEL WAS 3.8-5x TOO HIGH

§2's `secs = 369 + 0.869*forks` was regressed on M1 **campaign** games and
applied to **back-fill** games — a different regime. Smoke actuals: 7,120
forks in 1,615 s = **0.227 s/fork**; pure fork-free replay measured over all
696 m2_features games = **11 s/game**, not a 369 s intercept. Campaign games
amortise a large fixed cost over ~669 forks; back-fill games run 3-4x more
forks over the same fixed cost. R25: the number was only ever printed.

| design | as filed | **corrected** |
|---|---|---|
| A5 as approved | 120 core-h | **24** |
| PHASE 1 | 114 core-h | **24** |
| PHASE 2 (un-thin train) | 378 core-h | **80** |
| L11M arm | 42 core-h | **9** |
| PHASE 1 + 175 fresh | — | **50** |

⇒ **R45 now binds: when full power is cheap, budget must not pick N.** The
whole option range is under ~EUR 12 equivalent and under a day of wall, all
EUR 0 actual. The 63%-power arm is therefore not defensible *on cost*, and
the fresh-seed top-up is requested rather than deferred.

## R1.3 — PHASE 2, and why it is not optional for a KILL

Train-danger is 260. **Rule 1's corollary: only a NEGATIVE can be manufactured
by a thin label budget**, so a KILL from this fit is not licensed until the
fit is shown not to be label-limited. PHASE 2 (`--select train`, 80 core-h)
takes train-danger to ~2,669 (10.3x). Sequenced AFTER PHASE 1 so PHASE 1 stays
readable alone (R23). A GO needs no such gate — a starved fit that clears the
bar anyway is the stronger result.

## R1.4 — WHAT THE SMOKE ALREADY ESTABLISHED

- **Replay gate PASS** on every smoke game.
- **LABEL-IDENTITY PASS**: 10 shared `(seed, ply)` states between the base-bank
  producer and the back-fill producer agree **bit-for-bit**. Fork seeds are
  `dist_seed(seed, ply, s)`, so shared states are an exact behavioural test of
  the label path — strictly stronger than the schema/hash check §3 specified.
- The bare producer-hash check **did** fire, correctly and benignly:
  `m1_harvest.py` gained the back-fill branch after the bank was frozen, so
  the hash *must* differ. Per R60 the gate was rebuilt to let the shared-state
  label check adjudicate the hash, and to **refuse to clear an unadjudicated
  case** rather than wave it through. Both branches exercised: L20 PASS with
  10 shared states, L11M FAIL (exit 3) with 0.
- `test_fit2_gates.py`: the verdict machinery driven on both sides of every
  threshold, with a killed mutant (a corrupted duplicate is caught) and a
  silence control (identical duplicates stay quiet) — R21/R28-corollary.

## R1.5 — WHAT THIS REVISION DOES NOT CHANGE

Bars, statistic, ruler, decision shape, bootstrap, the §5.2 P-and-S1 verdict
rule, the §5.3 scope limits, and the pre-registered "a BETWEEN at the enlarged
n is a STOP, not a third back-fill". The held/train split rule is
**unchanged** and was not re-chosen after seeing any result — `m1_run`
asserts at launch that its copy still agrees with `m2_screens.held`.

---

# REVISION 2 — 2026-08-28, cost only. No bar, estimand or design changes.

**R2.1 — THE FIRM PRICE, measured in-regime.** R1.2 replaced the original
cost model with `0.227 s/fork` measured on the A5 **smoke**, which ran the
W=30 **death-window** design. PHASE 1 forks whole-game. **That correction was
itself a regime transfer — the error R1.2 was written about — and it was the
wrong one of the two.**

Constants now measured on PHASE 1's own banked games:

> **0.805 s/fork · 95 forks/adjudication · 16.1 s/game replay**

The replay figure comes from PHASE 1 games with **zero** trigger plies — the
degenerate case is the clean intercept measurement. Two independent methods
agree: fork-count projection **100 core-h**, observed completion rate (6 games
/ 20 min / 12 workers) **~115 core-h**.

⚠ **0.805 sits next to the ORIGINAL campaign regression's 0.869**, so the
campaign constant was approximately right for whole-game work all along and
R1.2's "5x cheaper" was an over-correction off three games of the cheapest
possible work. The death-window smoke was the outlier regime, not the campaign.
The single 3.17 s/fork reading was a worker's **first** game, carrying rig
initialisation — early-sample cost readings run high.

| filed | figure | fault |
|---|---|---|
| §2 | A5 approved, 120 core-h | campaign constant + fitted intercept absorbing fixed cost |
| R1.2 | PHASE 1, 24 core-h | death-window constant on whole-game work |
| **R2.1** | **PHASE 1, 100 core-h** | **in-regime, two methods agreeing** |

| option | core-h | wall @12w | held games | KILL power |
|---|---|---|---|---|
| **PHASE 1** | **100** | 8.3 h | 119 | 63% |
| L11M arm | 37 | 3.0 h | — | instrument |
| PHASE 1 + 175 fresh held-hashed | 208 | 17.3 h | 246 | 91% |
| PHASE 2 (un-thin train) | **333** | 27.7 h | — | fit convergence |

**R2.2 — PHASE 2 IS CONDITIONAL, and that is now worth 333 core-h.** Its only
job is Rule 1's corollary: *a KILL from a label-starved fit is not licensed,
while a GO from one would be stronger*. **It is therefore needed only if PHASE
1 returns a KILL.** Sequencing it after PHASE 1 is not tidiness — it can save
the entire spend. It will not be started before PHASE 1 reports.

**R2.3 — the pipeline defect this revision's validation caught.**
`m2_features.py` inferred the rig level as `20 if src == "L20" else 11`, an
exact string match, so every A5 segment (`L20_unthin_held`) was replayed at
**L11** while its labels came from L20 — features derived from a different game
and joined by `(seed, ply)` without complaint. **The replay gate failed 3/3 and
banked nothing.** Fixed to a stratum-prefix test with an assert on unknown
prefixes. Found only because the downstream chain was exercised on the first
3 banked games instead of waiting for all 173.

**R2.4 — the recurring shape, named once.** Every A5 defect this pass was a
**PROXY standing in for the PROPERTY it represents**: the exact string for the
stratum (R2.3); a file hash for label behaviour (R67); one regime's cost
constant for another's (R66); held-out DANGER STATES for held-out CLUSTERS
(R64); and a topout filter for "states where the guard matters" (the outcome
selection R1.1 removed). Five instances, one shape.

---

# REVISION 3 — 2026-08-28. The census has NO composition difference. Measured.

Rev 1 argued PHASE 1 removes the position-density distortion but noted one
residual difference: the census covers **trigger** plies only, while the base
bank also carries band / healthy / random quota states. **Measured, that
difference is zero where it matters.**

| class | all states | danger | **held-danger** |
|---|---|---|---|
| trigger | 2,161 | 348 | **93** |
| band | 877 | 0 | 0 |
| healthy | 279 | 0 | 0 |
| random | 267 | 5 | 0 |
| band+random | 3 | 0 | 0 |

**All 93 held-out danger states are trigger-class (100%).** Non-trigger states
contribute 5 of 353 danger states overall (1.4%) and **0 of the held-danger
set**. The reason is structural, not luck: `band` is `dsh ∈ [10,12]`, below the
trigger, and `healthy` is defined as non-danger — so the danger population *is*
the trigger population.

⇒ **PHASE 1's pooled held-danger set is a strict superset of the base one, in
the same class, at the same positions.** Base-only is a uniform ~12% subsample
of exactly what the census enumerates. Consequences:
1. The §5.1 post-stratification (arm P) is **provably inert** here, not merely
   observed to be small — it is retained as a robustness display, and its
   agreement with S1 is a check on the machinery rather than a correction.
2. **Base-only cannot be the gating arm under PHASE 1.** It estimates the
   identical estimand from 12% of the data, and at n=93 its UB is 0.1305, so it
   **cannot return a KILL by construction** — gating on it would void the A5
   spend. Reported as the continuity check; the census gates.
   (The team-lead's "lead with base-only" rider was set against the W=30
   design's 1.9x danger enrichment, which the census does not have. Flagged for
   ruling rather than assumed.)

---

# REVISION 4 — 2026-08-28. Rulings recorded. The top-up spends the lane's OWN reserve.

**R4.1 — SEED RULING: spend the reserve, claim nothing from the commons.**
Team-lead ruling. The PHASE-1 top-up takes the **128 held-hashed seeds** of
`19900–20898` — this lane's own M1 reserve, registered at M1 launch and
verified never played (the highest banked seed anywhere is 19898). That lifts
the held-out census from 119 to ~212 contributing games ⇒ **87% KILL power**,
at **zero cost to the free pool**.

The fresh block `24996..26394` **is NOT approved and stays unclaimed**; the
earlier fresh-seed approval is superseded.

⚠ **Why the fresh option was worse than it looked:** the registry allocates
*contiguous blocks* and only ~25% of any block hashes to held-out, so buying
175 held-hashed seeds means claiming a **700-seed block — 5.1% of the free
pool, not the 1.3% the approval was reasoned on.** Paying 700 streams for 4
points of power on a *screen* is the wrong side of the trade being reserved
for M3's on-policy A/B (~6,000 pairs), which is the decision that deserves the
commons.

**The reserve is SPENT, not borrowed.** It was held as M1's reserve, M1 is
closed, and it is being spent on M1's own follow-up measurement — the purpose
it was held for. `tools/seed_registry.py` now records it as consumed rather
than available, so the block reads correctly to the next lane.

Receipts: `--check 19900 500 2` → FAIL, 500 keys, all self-collision against
this lane's own entry — **a receipt of ownership, not a blocker**.
`--check 24996 700 2` → PASS (left unclaimed, and re-verified PASSing after
the registry edit, so the edit did not break the tool).

**R4.2 — the top-up is FRESH GAMES, so the replay gate MOVES rather than
vanishing.** These seeds have never been played, so there is no banked trace to
compare against and `stage_census` records `replay_gate: "N/A_FRESH"` — never a
silent `"PASS"`. The integrity check is not skipped, it is **relocated**:
`m2_features` replay-gates every census game before deriving features, and a
game whose replay diverges contributes no features and therefore **cannot enter
the fit**. Champion-const determinism is still asserted, one stage later, by
the consumer that a violation would corrupt.

**R4.3 — §6(a) RULING: the base-only requirement is REVERSED for PHASE 1.**
The gating arm is the **pooled census**; base-only is the continuity check; all
three arms still reported, with the class-composition table printed beside the
verdict. The original rider was derived against the W=30 design's 1.9× danger
enrichment, which the census does not have — and gating on base-only (n=93,
UB 0.1305) could not have returned a KILL by construction.

**R4.4 — the M3 §4 ruling (DECOMPOSE) is recorded in
`REGISTRATION_M3_AB.md`**, closing its §8 item 3. Method banked as R70, the
**perfect-imitation test**: before gating a distillation, score the *teacher*
against your own gate; if a bit-perfect copy fails, the gate is measuring
something other than the student.
