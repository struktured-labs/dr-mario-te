# Audit of the program's closed negatives — premature-closure review
**Date:** 2026-08-25 · **Scope:** zero-compute desk review. No experiments run, no systemd unit touched.
**Method:** read every closed-negative memory in the store, then followed into the experiment
worktrees for the registrations and result artifacts wherever a closure's key number lived only in
a memory. Numbers I read out of a result file myself are marked **[ARTIFACT-VERIFIED]**; numbers I
am relaying from a memory are marked **[MEMORY-ONLY]**.

---

## TL;DR — ranked

| # | Closure | Verdict | Cheapest distinguishing test |
|---|---|---|---|
| 1 | **Stage-2 LUT distillation** (supergod→coproc cascade step) | **SUSPECT — strongest finding in the audit. Its own artifacts contain the refutation.** | Zero new rollouts. Re-fit on the labels-146 counterfactual labels; run the single-feature `d_spawn_h` arm the lane never ran. |
| 2 | **The regime-gated / conditional evaluator shape** | **NEVER TESTED, and three independent closed lanes each name it as the one shape that would evade their law** | Already-banked data in two lanes; one dose screen. |
| 3 | **cascade-resolve NEGATIVE (n=10)** | **SUSPECT + its memory file is GONE** | Re-test at n=120, the same move that overturned its twin. |
| 4 | **H14a NO-GO** | **MIS-LABELLED** — it is "underpowered", not "the null matched"; the null was not population-matched | Nothing to spend. Re-word the memory. |
| 5 | Self-play VS negative — `toprisk` / `spawn` knobs | Narrow **dose-starvation** inside a sound closure | Already documented; do not re-run these two knobs. |
| — | tuck case-2 null | **I flagged this and then refuted my own flag. Correctly closed.** | none — do not spend |

---

# SUSPECT CLOSURES

## 1. ★★★ Stage-2 LUT distillation — the closure's own evidence refutes it

**What was concluded.** A learned 64-level additive per-feature LUT beat the hand-tuned champion
on sealed holdout (AUC **0.7220 vs 0.6645**) and then went **rollout NO_GO** (dies-ahead
−0.80pp [−2.20,+0.60], McNemar p=0.28, N=3,000 paired seeds), with a **dose-matched label-blind
null doing just as well** (DiD −0.27pp). Filed as: the AUC edge did not transfer. This is the
supergod→coproc step of the distillation cascade, and it is the step the cascade memory already
identifies as the weak link.

**First, a correction to the premise the audit was commissioned on.** The "~5 Bernoulli samples per
finalist, SE 0.21, ±42pp" measurement is a property of **supergod's arm**, measured 2026-08-25 over
19 games (`dr-mario-supergod.md:406-414`). It is **not** the Stage-2 teacher. Stage-2 had no rollout
teacher at all. The real defect is worse than sampling noise and it is structural.

**The actual label, verbatim from the registration** —
`/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/stage2/PREREG_STAGE2.md` §3.2, written
and sealed **before** the fit: **[ARTIFACT-VERIFIED]**

> ### 3.2 The label defect, stated up front
> The label is a GAME outcome broadcast onto that game's decisions. There is no counterfactual: a
> decision 40 plies before the end carries the same label as the last one.

and §7:

> **And the bigger defect, which the law does not cover:** the label is a game outcome pasted onto a
> whole game's decisions with no counterfactual (§3.2). **Fixing ATTRIBUTION (per-candidate
> forced-rollout labels) buys more than fixing the clear rate would.** The corpus stores boards + all
> 32 candidate values precisely so that an attribution layer can be added on the same seeds without
> re-running the census.

**A label-blind null matching your treatment is the exact signature of a label carrying no
per-decision credit.** The registration predicted this failure mode, named the fix, and had the
corpus built so the fix could be applied without re-running anything. The rollout NO_GO was then
filed as evidence against the *method*.

**The lane's own counterfactual test was run, and it says the fit is the problem, not the idea.**
`/home/struktured/projects/dr-mario-qa-wt/tmp/stage2_ceiling/ceiling_counterfactual.json` measures
within-decision AUC of "this action survives" — the attribution-correct endpoint: **[ARTIFACT-VERIFIED]**

| ranker | within-decision AUC | vs champion |
|---|---|---|
| **fitted LUT** | 0.5319 | **+0.0133, CI [−0.0170, +0.0432] — includes zero** |
| champion value | 0.5187 | — |
| **`d_spawn_h` alone (one raw feature)** | **0.6195** | **+0.1008, CI [+0.0769, +0.1253], frac_pos 1.000** |

and directly: **`d_spawn_h` beats the fitted 8-feature LUT by +0.0875 [+0.0631, +0.1118],
frac_pos 1.000.** `d_spawn_h` is *inside* the LUT's own 8-feature set. The fit took a feature that
carries the signal and produced something indistinguishable from the champion.

This is the project's own rule #1 from the vocabulary-wall retraction, applying verbatim: *"if your
fitting procedure cannot reproduce a KNOWN-GOOD solution, you may draw no conclusion from its failure
to find a better one."* There is a known-good solution here (`d_spawn_h` alone, +0.10, frac_pos 1.0)
and the fit does not reproduce it. **The rollout NO_GO therefore licenses no conclusion about learned
evaluators.**

**The prereg-mandated slice table was computed and never reported.** §3.2 required *"the primary
analysis is reported at every t_to_end band … Nothing here is allowed to be reported pooled over
t_to_end only."* The bands are in
`.../stage2/shippable/out/holdout_result.json` and the memory quotes only the pooled number.
For the best in-class shape (S3): **[ARTIFACT-VERIFIED]**

| band | n | model AUC | champion AUC |
|---|---|---|---|
| t≤2 | 1,971 | 0.9507 | **0.9841 — the champion WINS** |
| t3–9 | 4,599 | 0.9295 | 0.9313 |
| t10–30 | 13,797 | 0.8922 | 0.8601 |
| **t>30** | **84,584 (81% of holdout)** | **0.6370** | 0.6109 |

The champion is better than every learned model where attribution is tightest, and the model's edge
lives almost entirely in the band where the label is least attributable. The pooled 0.7220 is partly
a "which band is this row in" discriminator.

**And the closure's own designated decisive follow-up was run — and came back GO.** The memory
pre-registered: *"P0 NEXT: an ORACLE-CEILING ARM … Decisive both ways: oracle NO_GO ⇒ root re-ranking
is structurally dead … Oracle GO at −2 to −3pp ⇒ the AUC gap becomes priceable for the first time."*
Five days later Tier-A returned **dies-ahead 12.00% → 0.43% (−11.57pp)** at N=9,000 with its shuffled
mutant **killed clean (DiD −15.0pp [−15.7,−14.2])** — four times beyond the top of its own GO band.
[MEMORY-ONLY, `dr-mario-tiera-go-verdict`]. The program acted on that by shipping H12 (root
re-ranking by *rollout*). **The learned-evaluator branch specifically was never re-opened, although
its pre-registered precondition passed decisively.**

**Lens items:** 1 (label-blind null matched ⇒ labels carried no signal), 2 (offline win → rollout
loss), 5 (closed on a proxy — AUC — while the mandated band-level proxy analysis went unreported),
7 (the residual tracked a different disease: the LUT was scored on outcome-broadcast labels while the
question was per-decision choice quality).

**What would distinguish genuinely dead from prematurely closed.** If the LUT features, re-fit on
*counterfactual* per-(state,candidate) labels, still cannot beat the champion within-decision — and
still cannot reproduce `d_spawn_h`'s +0.10 — the method is dead and the closure is right. If the
re-fit reaches or passes `d_spawn_h`, the original NO_GO was a label artefact.

**Cheapest test — zero new rollouts, all inputs already banked:**
1. Re-fit the 8 frozen features on the **labels-146 counterfactual label bank** (1,344 states,
   per-(state,candidate) forced-rollout labels, pilot GREEN, `dr-mario-labels146-campaign`) and score
   within-decision AUC against the champion and against `d_spawn_h`. Pure CPU on banked data.
2. Re-run the `ceiling_counterfactual.py` design **away from the near-death window** — its own
   caveat string reads *"fork windows are the last W=6/12 plies of TOPOUT games … NEAR-DEATH ONLY"*,
   76 seeds / 662 discriminative plies, so it is not a whole-distribution result.
3. Only if (1) passes, spend a rollout — and make the first arm **`d_spawn_h` alone at matched dose**,
   the known-good solution the lane never played. `lut_rescreen.py` (commit 631f220, staged and
   approved at 6 workers) already measures ~2.8% flip dose for the LUT at the current L20 champion
   regime, above the 2% testability floor, so a re-test is dose-viable.

**Epistemic status:** the prereg text, the counterfactual JSON and the slice table I read myself.
The Tier-A numbers and the labels-146 bank status are memory-only. The near-death restriction on the
counterfactual test is a real limit on how far item (2) above can be skipped.

---

## 2. ★★ The regime-gated / conditional evaluator shape — never tested, and three closed lanes each point at it

Not a suspect closure so much as **a door that three separate closures each explicitly left open and
nobody walked through.** [MEMORY-ONLY throughout]

- **H15 / garbage-labels** closed the linear-additive integration at *every* dose (monotone
  d **+0.125 @ structural parity → +0.575 @ λ=0.3**, i.e. +12.5pp to +57.5pp worse; n=40 paired
  pressured games per λ). Its own routing note says this is *"evidence about the FUNCTION CLASS, not
  the features — center burial is lethal only UNDER CONTAMINATION, and a static linear term cannot
  express a conditional."* The features themselves **passed**: within-state Spearman **+0.0568
  [+0.0353,+0.0779]** on 319 held-out states, and **+0.0623 [+0.0413,+0.0833]** against matched-noise
  features.
- **vocab-wall-2** closed the penalty family on a structural law and flags: *"A **REGIME-GATED**
  version — penalty active only under pressure/garbage-pending — was **NOT tested** and is the one
  shape that could evade the structural law."*
- **regime-weights** is a *powered* negative at depth-3 (n=120 held-out, −0.358 clears/seed,
  CI [−0.525,−0.192], p=0.0001, neg-controls 0.00% vs 6.0% real movement) — but carries a
  pre-registered scope bound saying it does **not** license "regime weights don't work at d3": the
  structural "shape" term was unmappable and its effect **unmeasured**.

So: the conditional shape is named as the surviving hypothesis by two lanes, and the one lane that
looks like it already killed it explicitly says it did not test the relevant part. **Lens item 6** —
a real measured mechanism (linear-additive integration fails) is being carried as if it explained an
outcome it does not cover (conditional integration).

**Cheapest test:** H15's own machinery plus its 1,344-state bank; gate the g_center term on
pressure/garbage-pending and re-run the Stage-A 6-point λ screen (420 games total for the original
sweep, so a single-gate variant is well under a day). If the monotone-worse curve survives gating,
the family is closed for real.

---

## 3. ★★ cascade-resolve NEGATIVE (n=10) — suspect, and its memory file no longer exists

**What was concluded.** Cascade-resolve inside the search was rejected on a single block of
**n=10 seeds** (clear rate 100% → 50%), 2026-07-12/15 era. [MEMORY-ONLY]

**Why it is suspect — the strongest structural argument in the store, and the store makes it itself.**
`dr-mario-sample-size-audit` names cascade-resolve and depth-4 as the two thinnest door-closing
negatives, both n=10, both same era, same single-block design. **Depth-4 was re-tested at n=120 and
the NO-GO was OVERTURNED — the sign flipped.** The audit's own conclusion: *"a thin negative is not
merely under-evidenced — it is roughly a coin flip on whether it is even directionally right,"* and
it names cascade-resolve *"now the highest-value unexamined negative in the store."* That was
2026-08-01. It appears never to have been re-tested.

**⚠ And the file is gone.** `dr-mario-smarter-experiments.md` is linked from **nine** memories
(sample-size-audit, depth4-memo, regime-weights, e1-endgame-negative, combo-gap, native-ai-program,
paper-lane, player-data, pocket-shipped) and **does not exist** in the memory directory. It is not
in `MEMORY.md` nor in either dated backup (`.bak_20260823`, `.bak_20260824` — zero references in
both), and no copy exists anywhere under `/home/struktured`. **[ARTIFACT-VERIFIED]** The evidence
behind this negative is not recoverable from the store. This is literally the failure the owner is
worried about.

**Partial mitigations already on record, neither of which closes the door:** the *cheap* cascade
override was separately refuted at n=120 (2.8% of decisions, ~1.0 move/game, median +0.0 pills,
30/28) — but `dr-mario-endgame-planner-win` records that *"a genuine cascade-aware depth-3 search is
untested,"* and its 2026-08-01 correction adds that **compact no-link gravity inflates cascade
potential ~4.5x — 70% of modelled chains are phantoms**, which means the original n=10 harness may
have been scoring phantom cascades.

**What would distinguish:** a paired n=120 re-test on the modern leaf, exactly the design that
overturned depth-4. **Cheapest test:** that re-test — the audit estimated the depth-4 equivalent at
"one afternoon once the delta landed."

---

## 4. ★ H14a NO-GO — correctly a no-promotion, incorrectly worded as "the null matched"

**What was concluded.** H12+`trigger_eps=2.0` does not beat certified H12: **−1.5pp
[−4.0,+1.17], McNemar p=0.3135, N=600 paired seeds**, with the stated reason *"the −1.5pp sits
inside what the dose-matched null produces."* [MEMORY-ONLY for the verdict wording]

**The defect.** The two arms' base failure rates are not the same population. Memory reports
TRUE base 0.3867 vs MUTANT base 0.500. I aggregated the run summaries under
`/home/struktured/projects/dr-mario-champ145-wt/experiments/champ145/out/endpoint/`:
**e1_true base fail 0.389, e2_mutant 0.485, e2b_mutant 0.502** — on a nominally shared seed block
(53100+). **[ARTIFACT-VERIFIED]** The mutant was auto-thinned 671/1000 to dose-match, so it ran a
different (harder) seed subset. **No DiD was computed anywhere.** A null-match claim across
non-identical populations is not a null-match claim.

**This does not overturn the NO-GO** — the primary CI includes zero on its own and no promotion was
warranted. **Lens item 1/3:** the verdict should read *"underpowered at N=600; not distinguishable
from zero"*, not *"the null matched."* The distinction matters because H14a's increment is the
yardstick H13-v2 was then measured against ("H13-v2's increment is 0.45× that"), so a
mis-characterised H14a propagates into a second closure.

**Cheapest test:** none needed. Re-word the memory, and compute the DiD from the existing artifacts
if the comparison is ever quoted again.

---

## 5. ★ Self-play VS negative — sound overall, but two knobs inside it are dose-starved

The self-play VS closure is **sound** and I verified its rig: the severed-channel control shows
`OFF arm delivered nothing 200/200 OK` vs `ON arm actually delivered: 8593 releases total OK`, with
win rate OFF 78.2% → ON 59.0%, paired shift **−19.2% [−25.5,−13.0], n=200**
(`/home/struktured/projects/dr_mario_rl/tmp/vs_aware/logs/garbage_pb_n200.log`). **[ARTIFACT-VERIFIED]**
The probe6 CvC zero-garbage defect does **not** touch this lane, and arm-select ran offline on
delivery-verified JSONL, so it is unaffected too.

**But** the memory's own lever-strength table shows `toprisk` changes a decision in **15%** of games
and `spawn` in **20%** — both far below every other knob (90–100%). Their flat readings are the
closest thing in the surviving VS corpus to a no-dose result, and the memory says so:
*"a tight CI at 51% can mean 'barely tested', not 'precisely measured as good'."* Re-running under
`--rule rom` fixed the regime; it could not fix an inert lever.

**Also on record and untested:** both attack levers swept are **simultaneity** levers, while
**85% of real ROM attacks are cascade-formed**. "Attack-shaping refuted" should never be quoted
unqualified. Corroboration that the narrow reading is right: `lnk1`, a *physics-fidelity* change,
later became the first holdout-confirmed VS win at 60.2% [56.9,63.4].

**Cheapest test:** do not re-run `toprisk`/`spawn`. If the attack channel is revisited, the untested
lever is the cascade one.

---

# ⚠ A FLAG I RAISED AND THEN REFUTED — tuck case-2 is correctly closed

I am reporting this because it is the audit going wrong, caught before it cost you anything.

An extraction pass found that in every result file under
`/home/struktured/projects/dr-mario-forcedmove-wt/experiments/forced_move/results/`, the stored
`ref` is the **played** move — which ranks 33–34/34 (M1) and 12–14/16 (M2) — and that against that
reference the tucks look overwhelmingly positive (up to **+6.19 [+4.98,+7.40]**). That reads like a
reopenable closure. **It is not.** I recomputed the comparison that actually answers "is tuck
*capability* worth anything", namely best tuck vs **best available non-tuck alternative**:
**[ARTIFACT-VERIFIED, computed by me from the row-level data]**

| cell | best tuck | best non-tuck | tuck − best alternative |
|---|---|---|---|
| M1 solo | 17.92 | 18.67 | **−0.75 [−1.90, +0.46]** |
| M1 drip8 | 16.90 | 17.71 | **−0.81 [−2.00, +0.44]** |
| M1 drip4 | 15.56 | 15.08 | **+0.48 [−0.83, +1.73]** |
| M2 solo | 18.54 | 18.08 | **+0.46 [−0.50, +1.46]** |
| M2 drip8 | 17.42 | 16.94 | **+0.48 [−0.46, +1.44]** |
| M2 drip4 | 16.27 | 15.17 | **+1.10 [−0.06, +2.27]** |

All six CIs include zero. **The "tuck value ≈ 0 at both owner-named moments" verdict stands.**
Comparing a tuck to a move ranked 33/34 flatters it; so does almost any other legal move.

**Two smaller caveats that are real and unflagged in that memory**, worth one line if it is ever
cited: (a) the *registered primary* endpoint is saturated — `d_topout` is `−0.0208` or `0` with
CI `[−0.0625, 0]` and `dies_ahead == 0` for **every arm in every cell**, so the verdict rests
entirely on the 30-pill `viruses_cleared` proxy, the same shape the GW-void memory files correctly
and this one does not; (b) the **+6.33 viruses/30 pills** orientation number is real but is attached
to the RELATCH fix by inference — RELATCH was never run on that board.

---

# CANNOT TELL WITHOUT A FILE I COULD NOT FIND

- **`dr-mario-smarter-experiments.md`** — the cascade-resolve negative's evidence. Referenced by nine
  memories, absent from the store and from both index backups, no copy on disk. See item 3.
- **`dr-mario-blunder-battery-priced-neutral`** — weakest provenance of anything I reviewed: session
  scratchpad scripts only (`scan_backwards_horiz.py`, `price_battery.py`, `battery_*.json`), no
  commit, no repo path, no pre-registration, and no CI on any delta. Its numbers are not
  reconstructible. The closure is probably fine (dose is healthy at 8.09% of plies, 12.8/game, and
  the detector's "98% value-PREFERRED, not ties" check is a genuine control) but it cannot be audited.
- **`dr-mario-vocab-wall-2`** ends with *"Screen verdict pending → update this file when
  screen_result.json + lulu land."* It is not clear the lulu arm ever landed; the file may be
  reporting an interim state as final.

---

# SOUNDLY CLOSED — do not spend here

Short list, with the one thing that makes each safe.

- **gate-v2 / #110 (H12 gate expansion)** — the model of a real null: 446 v2-only flips × 17 unseen
  streams, +0.012 viruses/flip [−0.058,+0.085], **wins exactly equal losses**, and a firing negative
  control at **−0.559** proves the instrument discriminates.
- **H13-v2 re-screen** — correctly closed *and correctly labelled*: closed on **dose starvation**
  (always-open supremum +0.72pp vs a 2% floor), explicitly "NOT TESTABLE AT THIS DOSE, never null",
  zero seeds spent.
- **GW pricing void (both files)** — the template for how to file an instrument ceiling. States
  *"structurally unsatisfiable … not merely underpowered, IMPOSSIBLE"*, runs a reader mutant to prove
  the zeros are data, and keeps the distinction *"the deepening has customers; the instrument can't
  see their value."* Verdict is saturation, not absence, and it says so.
- **H15 / garbage-labels linear-additive family** — a loud, well-dosed negative (+49.17pp worse at
  L20, 396:0 one-sided discordance on the clean guard), with the controls themselves mutant-tested.
  Correctly scoped to the function class. (See item 2 for the shape it leaves open.)
- **side-asymmetry refuted** — best power statement in the store: original n=80 had a CI half-width
  (±5.39pp) *wider than the effect claimed* (5.33pp); re-run at n=1500/arm with a board-swapped
  mirror control, and a pre-registered mutant prediction that **failed and was diagnosed**.
- **clean-failure geometry** — four proposed mechanisms, four killed by within-board matched
  controls (virus cells 61/68 = 89.7% vs random matched cells 61/68 = 89.7%, sign p=1.0000).
- **A_v reach refuted** — the scale-matched control flipped 3.92% of decisions vs the treatment's
  3.83%; dose-identical, so "beats baseline" was proven uninformative. Honest inverse: a provably
  wrong term whose correction is worth nothing.
- **self-seal refuted** — dose swept across three orders of magnitude (0.05%→31.33%) with monotone
  harm, and the sub-floor arms explicitly ruled *un-testable, not null*.
- **capsule lookahead negative** — carries a **misinformed** control that resolves 6.2 pills, so the
  null is demonstrably not an inert instrument. Dose measured at 18–35% of in-window moves.
- **ws=20 failure-optimal** — extreme arms hurt decisively (+18.7 and +14.0 pts) while neighbours
  are indistinguishable; ~75–85 discordant pairs per arm.
- **greedy-vs-defer** — closed in *both* directions, with `W_DEFER=0` collapsing bit-identically to
  ship (267/267) and a pre-registered falsifier that did not trigger.
- **joint-dig refuted** — catastrophic at full dose (clear 94.2→60.0 drip, 80.8→35.4 lulu, p<1e-4).
- **arm-select negative** — three controls including a planted-signal positive control at +43.2%
  captured, and the train column (65–69% against a 63.8% base) proves absence of signal rather than
  a fitting failure.
- **regime-weights at d3** — powered negative with clean guards; note the registered scope bound
  (item 2).
- **nes pill retune** — a train/holdout split that overturned its own tuning-block result.
- **missed-clear decomposition**, **decline-vs-human**, **imitation fails**, **plan avoidance**,
  **eval-hacking trap** — all fine for what they claim; see the two small errata below.

**Two small errata worth fixing in place, no compute:**
- `dr-mario-decline-vs-human-earlygame` says moving ship toward more human-level deferral "is
  untested." It was tested the same day — `greedy-vs-defer-garbage`'s defer-MORE complement (n=80,
  W_DEFER sweep) — and it lost at every cadence. Anyone chaining those two memories inherits a false
  open door.
- `dr-mario-armselect-negative` reports a decisive set of 307/800 with baseline 63.8%; the live
  `armselect_feas.py` docstring says 195/304 = 64.1%. Version skew; direction unaffected.

---

# CROSS-CUTTING

**The program's controls are good — good enough that the failure mode has moved.** Almost every
lane here runs a null, and the nulls are usually validated (killed mutants, positive controls,
firing controls). The remaining risk is not missing controls; it is **reading a matched null as
evidence about the hypothesis when it is evidence about the instrument**. The store already contains
this rule three times over (`spawn-lane-gate-probe`: "below ~2% flip, report 'not testable at this
dose' — never a null"; `garbage-labels`: "killed-mutant the CONTROL before trusting a tie";
`gw-pricing-void`: "structurally unsatisfiable, not underpowered"). The Stage-2 LUT is the one
significant place where that rule was available and not applied.

**One number worth keeping in view:** certified H12 — the current champion — itself sits at a
**~2.0% flip dose**, right at the floor now used to reject its successors. The floor is a rule of
thumb tied to n=200–400 and is decider-specific; `spawn-lane-gate-probe` says both caveats itself.

**The cascade's weak link is the one item that is both suspect and cheap.** MAIN = coproc champion,
SIDE = supergod-as-teacher, THIRD = NES-only, with distillation between them. The one attempted
distillation step failed on labels that had no credit assignment, its registration said so in
advance, the fix (counterfactual per-candidate labels) has since been built and validated GREEN in
labels-146, and the corpus was deliberately constructed so the fix could be applied without
re-running the census. That is the thread most worth picking back up.

---
---

# ADDENDUM (same session) — two lens items added by team-lead after the main audit

## LENS 8: STALE SUPERSESSION — a closure wrong because a later result overturned it and the headline was never updated

Swept all 330 memory files: extracted every `description:` line, flagged the 54 carrying a status word
(BLOCKED / NOT PASSED / OPEN / PENDING / STAGED / AWAITING / REFUTED / NO_GO / VOID / FAILED), then
compared each against its siblings and the files it links to. **Seven confirmed instances.** All index
links resolve — zero dead hooks — so this is purely a headline-freshness failure, and it is the more
common failure mode, exactly as suspected.

Ranked by cost:

**S1 — the same bug that just cost six days, still live one level up, on the most-read memory in the store.**
`dr-mario-three-lane-distill-cascade.md` is the **#1 Read-first entry in MEMORY.md**. Its lane table says:
> `next core DBLCANON 974de3ed / fw b03a586e built + silicon-tested Aug 19, **blocked on ONE unexplained sample**`

Contradicted by the memory it links to, written **16 minutes later** (`dr-mario-dblcanon-tuck-residual.md`):
> `The lone survivor (i=256) was logged "unexplained" and blocked the core. **It is now explained. The 30x effect stands.**`

and by `dr-mario-dblcanon-driver-closed-benign.md`: `CLOSED-BENIGN … k=0/39,667`. The archive hook was
fixed; **the cascade memory was not.** Anyone reading the program's organizing frame today is still told
the MAIN lane is blocked.

**S2 — the H16 trial that is on the critical path right now reads as unstarted.**
`dr-mario-h16-program.md` description: `registered DRAFT … awaiting team-lead approval, NO evaluation
compute spent`. Its own body: `INTERIM #2 (registered, n=400) 2026-08-25 ~14:45 EDT: d=−0.0275
CI[−0.0525,−0.0025] futility=CONTINUE` and `GUARD ARM COMPLETE 2026-08-25 15:25 — NO TRIP … ledger
1000/1000, GUARD_OK`. `MEMORY.md:8` repeats `DRAFT registered`.

**S3 — `dr-mario-clean-failure-geometry.md`: the headline states a claim the body formally self-refutes,
and it is the claim that would send someone to build the wrong feature.** [verified by me]
Description: `the last virus … **buried under ~5 cells. 12/12 buried, 0 open.**`
Body §41: `⚠⚠ SELF-REFUTED: "12/12 BURIED" WAS THE BENIGN STATE — AND THE TRUTH INVERTS IT` … `the last
virus is in an unusually SHORT column and is LESS buried than its row-mates` … `★ THIS REVERSES THE
STRATEGIC READING. It is **NOT an excavation problem.**` The same body notes that route-potential and
the endgame planner **both failed because they were built for that wrong obstacle** — so this stale
headline has already misdirected two lanes.

**S4 — `dr-mario-prestart-play-coverage-hole.md`**: description `NO play-level gate has EVER observed
DRPRESTART fire, on any cart`. Closed 11 minutes later by `dr-mario-cvc-harness-never-delivers-garbage.md`:
`7 pokes → 7 release edges, and the SYNCHRONOUS prestart committed 5 of 7 — first play-level evidence in
the repo that it fires at all`. Stale in three places: this description, that file's *own* description,
and `MEMORY.md:41`.

**S5 — `dr-mario-competitive-play-is-the-main-gap.md`**: description still says `The selfplay-dead negative
may be VOID (ran on the no-garbage harness?)` and the body still says `Do NOT cite the old self-play
negative as a door-closer until the audit clears it`. The audit cleared it 1.5 days earlier —
`dr-mario-selfplay-negative-audit.md`: `the negative STANDS … My stale-negative theory was WRONG.`
(The directive itself — competitive play is the main gap — is current; only the VOID clause is stale.)

**S6 — `dr-mario-tuck-miss-verdict.md`**: `do NOT build tuck support — declined on COST/RISK` (2026-07-27),
still hooked from the archive with no reversal marker, and overturned three times since — tucks PAY on
the real NES stream (3/3 levels, every paired CI excludes zero), the executor-restricted win is real
(−5.20 pills [−8.92,−1.47]), the owner directed it be built, and
`dr-mario-cart-no-tuck-executor.md` records `THE FIRST TUCK EVER EXECUTED ON REAL HARDWARE`.

**S7 — `dr-mario-endgame-planner-win.md`**: the inverse layering. Description: `ENDGAME-GATED planner
WINS … finally proven`. Body: `★★★ DO NOT BUILD — killed by the REAL NES capsule stream`. Here the
index hook is correct and the description is the stale layer.

**Four more stale INDEX hooks** (wording contradicts the target's current description):
`[H16 PROGRAM: … DRAFT registered]`, `[PRESTART NEVER OBSERVED IN PLAY]`,
`[DRPRESTART×DRTUCK ⚠ REOPENED #115]` (target says RETRACTED, exonerated 12/12),
`[MiSTer BUSTED for play]` (the new unit arrived 2026-08-20 and the 3-1 owner set was played on it),
`[VOD: 2 of 4 real orient faults]` (mechanism clause contradicted by
`dr-mario-vod-orientation-fault-localized.md`: `the 60fps "extra 180" … is benign. The rotation executor
is CLEAN.`).

**Checked and CURRENT** (do not touch): tuck-mailbox-vacuous-gate (correctly scoped to the stock
probe3/fieldplay brains, and names its own fix), the Aug-25 VOD extractor pair, prestart-variant-staged,
opening-stall-silicon, eval-headroom-stage1's OPEN question, and the whole START-press retraction cluster.
**CANNOT TELL:** `navdwell-rootcause` — a "validated 2-hunk fix" with no memory recording whether it landed.

**Recommended fix, cheap:** the tell is mechanical. A status word in a `description:` line that a
later-modified sibling contradicts. The extraction I ran (54 of 330 files carry one) can be a standing
check — treat any status word in a description as carrying an expiry date.

## LENS 9: AN ACCEPTANCE BAR UNMEETABLE — or undecidable — BY CONSTRUCTION

One confirmed instance, and it is the *undecidable* variant rather than the unmeetable one.

**`dr-mario-garbage-labels-campaign.md`, claims secondary (C-deep): declared NOT MET on a bar the
experiment had no power to resolve.** Reported as `Rescue 38/269 = 0.141 < 0.15 bar (missed by 0.009,
within binomial noise of the bar; the bar is the bar)`. Computed: **p = 0.1413, SE = 0.0212, so the bar
sits 0.41 SE from the point estimate and the 95% CI is [0.0996, 0.1829] — the bar is INSIDE the interval.**
Refusing to move a pre-registered bar after seeing data is correct discipline and I am not asking for it
to be moved. The problem is the *reporting*: "NOT MET" reads as a substantive failure of the claim
mechanism when the correct statement is **"not decidable at n=269."** This matters because the claim
mechanism is the thing the labels-146 lane exists to evaluate.

This does **not** disturb the H15 closure — its primary was +49.17pp worse [+45.0,+53.3] with 396:0
one-sided discordance, which is decisive by an enormous margin.

**Two related shapes already correctly handled in-store, worth naming as the good examples:** the
labels-146 promotion gate (≥150 fresh k≥8 claims) was itself found **unreachable from the registered
window** and filed as such — *"A promotion gate inherited across a WINDOW change must be re-derived, not
restated"*; and the Stage-2 rollout's **+1.0pp clear-rate non-inferiority margin was UNREACHABLE at
N=3,000 BY CONSTRUCTION** (611 discordant clears ⇒ CI half-width ±1.58pp), which that lane worked out and
recorded. So the program already knows this failure mode; the C-deep case is where it slipped.

**Absence claims with no upper bound stated** — the same family — appear twice more and both are
already flagged in-store: labels-146's `0/12` claim-rule firing (correctly given a 95% upper bound of
22%), and gate-standard rule 8's "third false zero" incident.

---
---

# ACTION LOG — corrections applied 2026-08-25 (team-lead approved)

House convention followed throughout: **the wrong version is kept visible above each correction.**

## Stale headlines corrected in place (7 files + 1 sibling)

| file | was | now |
|---|---|---|
| `dr-mario-three-lane-distill-cascade` | "next core … blocked on ONE unexplained sample" | **fixed by team-lead** (his own file) |
| `dr-mario-clean-failure-geometry` | "buried under ~5 cells. 12/12 buried, 0 open" | "**NOT an excavation problem** … SHORT column, LESS buried … COLOUR-MATCH failure"; superseded-headline box added quoting the old text and naming the two lanes it misdirected |
| `dr-mario-h16-program` | "DRAFT … NO evaluation compute spent" | "**TRIAL IS RUNNING** … interim#2 n=400 d=−0.0275, GUARD COMPLETE NO TRIP"; body's stale status paragraph replaced with a box pointing at the live INTERIM/GUARD sections |
| `dr-mario-prestart-play-coverage-hole` | "NO play-level gate has EVER observed DRPRESTART fire" | "the prestart HAS since been observed to fire (7 pokes → 7 release edges, 5 of 7 committed)"; the narrower self-play coverage claim retained as what still stands |
| `dr-mario-cvc-harness-never-delivers-garbage` | "…everything downstream is UNTESTED by every play-level gate" | that clause explicitly **RETIRED**, pointing at this file's own forcing rig |
| `dr-mario-competitive-play-is-the-main-gap` | "the selfplay-dead negative may be VOID" + body "Do NOT cite … until the audit clears it" | both corrected; audit cleared it 2026-08-23, negative STANDS at its **narrow** scope, with the scope spelled out. **The owner directive itself is untouched and current.** |
| `dr-mario-tuck-miss-verdict` | "do NOT build tuck support" | "**THE VERDICT IS OVERTURNED**"; detection stands, the COST/RISK decline reversed by owner directive and by measurement, first tuck executed on silicon 2026-08-09 |
| `dr-mario-endgame-planner-win` | "planner WINS … finally proven" | "**DO NOT BUILD** (killed by the REAL NES capsule stream, −13.6%/−18% → −1.4%)" |
| `dr-mario-navdwell-rootcause` | implied shipped | "**SHIP STATUS UNVERIFIED AS OF 2026-08-25**" — an honest unknown, per instruction, not a guess |

## Stale index hooks corrected (6)
`MEMORY.md`: H16 "DRAFT registered" → "TRIAL RUNNING"; "PRESTART NEVER OBSERVED IN PLAY" →
"self-play gates blind; it DOES fire"; VOD hook annotated that its mechanism clause is refuted.
`dr-mario-index-archive.md`: tuck "miss verdict" marked OVERTURNED; "MiSTer BUSTED for play"
marked superseded (new unit arrived 2026-08-20); "DRPRESTART×DRTUCK ⚠ REOPENED #115" →
"RETRACTED, pair EXONERATED 12/12".

## Errata (2)
- `dr-mario-decline-vs-human-earlygame`: the "that direction is untested" line replaced with the
  erratum — defer-MORE **was** tested ~100 minutes later the same day (n=80, W_DEFER sweep) and
  **lost at every cadence**. Deferral is closed in both directions.
- `dr-mario-armselect-negative`: erratum appended recording the 307/800 (63.8%) vs 195/304
  (64.1%) drift between memory and live script; **the conclusion is unaffected** because it rests
  on the control structure (positive control +43.2%, side-leak 0.0%, TRAIN column 65-69% vs a
  63.8% base), but the baseline figure should not be quoted until reconciled.

## New standing check
`tmp/negatives_audit/stale_check.py` + memory `dr-mario-stale-supersession-check` (indexed in
MEMORY.md). Checks **A/B** dangling `[[link]]` targets (exact), **C** body reversal the headline
does not acknowledge, **D** status word + later-modified sibling.
**Positive control (`--self-test`) plants three known-stale mutants and asserts the check FIRES on
each — it PASSES**, so a zero from the script is meaningful. C/D are explicitly labelled a SCREEN,
not a decider, per this project's "proxies rule OUT, never rule IN".

**First live run found 18 dangling link targets**, not one: `dr-mario-smarter-experiments`
(9 inbound — the cascade-resolve evidence), `dr-mario-tuck-action-space-gap` (5),
`dr-mario-v18-rom-ready` (3), `dr-mario-tuck-executor` (2), plus singletons including a few prose
false positives (`[[links]]`, `[[MEMORY]]`, a line-wrapped link, two written with a `.md` suffix).

## Instrument gates for the Stage-2 recheck (run BEFORE the result is read)

- `auc_gate.py` — the within-decision weighted AUC estimator is gated on **six known-answer cases
  plus a killed mutant**: perfect separation → 1.0, inverted → 0.0, all-ties → 0.5, a single
  candidate carrying both outcomes → exactly 0.5 (self-pair tie), non-discriminative → `None`, and
  a hand-computed asymmetric case → 8.5/12. A **score-blind** estimator returns 0.5 and therefore
  fails the hand case, so the gate is not vacuous. **PASSES.**
- `stale_check.py --self-test` — plants three known-stale mutants and asserts the check fires on
  each. **PASSES**, so the 18 dangling targets and the empty C/D lists are meaningful.
- In-run controls (pre-registered, §3 of the prereg): a **LEAK** feature (`p_hat` + noise) must
  read ≈1.0 or the harness is broken and the run is VOID; a **label-blind NULL** (surv vectors
  permuted across candidates *within* each state) must read ≈0.5.
  ⚠ Committed in advance: if NULL lands **above 0.55**, that is the H15 trap
  ([[dr-mario-garbage-labels-campaign]] — "a control whose statistic retains the phenomenon's
  channel cannot test what it claims; killed-mutant the CONTROL before trusting a tie"), and the
  run must be reported as **VOID**, not as evidence.

---
---

# STAGE-2 RECHECK RESULT — **VOID ON MY OWN PRE-REGISTERED GATES**

Ran 2026-08-25. Held-out: **88 seeds / 6,908 candidates / 319 discriminative decisions.**
Fit and controls: `refit_v2.py`, result `refit_result.json`, estimator gated by `auc_gate.py`.

## ⚠⚠ THE VERDICT IS VOID, AND BOTH VOID TRIGGERS ARE DEFECTS IN MY PRE-REGISTRATION

I wrote two VOID conditions. **Both fired. Neither indicates a problem with the data — both are
acceptance bars that were UNMEETABLE BY CONSTRUCTION.** That is lens item 9, handed to me by
team-lead this afternoon, and I committed it twice within the hour of being taught it.

**1. "LEAK must read > 0.95."** LEAK read **0.8404**. I then computed the estimator's true
ceiling — rank candidates by their exact realised `p_hat` — and it is **0.8404, to four decimals.**
LEAK was performing *perfectly*; my bar was above the arithmetic maximum. The ceiling is below 1.0
because a candidate with intermediate survival contributes both survivor-forks and dier-forks that
tie against each other at 0.5, and those self-pairs are irreducible. **A zero-tolerance-style bar
set without measuring the instrument's own ceiling.**

**2. "NULL must read inside [0.45, 0.55]."** The within-state-permutation null read **0.6429**.
I had pre-committed that >0.55 means the H15 trap. It is exactly that trap
([[dr-mario-garbage-labels-campaign]]: *"within-state permutation preserves state means ⇒
between-state feature-label covariance survives training"*) — but the deeper error is that
**I assumed a fitted arm's null is 0.5.** It is not. A **globally**-permuted null — which destroys
between-state covariance too — reads **0.5527**, still not 0.5. Only a *constant* score reads
0.5000 (verified exactly). So the floor for any FITTED arm on this estimator is ≈0.55, not 0.5.

⇒ **The whole gate band was calibrated against an imagined instrument.** Floor and ceiling are
**0.55 and 0.8404**, not 0.5 and 1.0.

## What the run shows, EXPLORATORY ONLY — this licenses nothing until re-registered

Normalised against the measured floor/ceiling (headroom CHAMP→CEILING = 0.2047):

| arm | held-out AUC | Δ vs CHAMP [95% CI] | headroom captured |
|---|---|---|---|
| CEILING (exact `p_hat`) | 0.8404 | — | 100% |
| **LUT_z1** (champ + Δ) | 0.6712 | **+0.0355 [+0.0219, +0.0501]** | 17.3% |
| **LUTONLY** (Δ alone) | 0.6637 | **+0.0281 [+0.0091, +0.0483]** | 13.7% |
| **DSH** (`−d_spawn_h` alone) | 0.6607 | **+0.0251 [+0.0069, +0.0440]** | 12.2% |
| CHAMP | 0.6357 | — | 0% |
| NULL, within-state perm | 0.6429 | +0.0073 [−0.0146, +0.0306] | 3.5% |
| NULL, global perm | 0.5527 | — | below champion |

**LUT_z1 − DSH = +0.0105 [+0.0010, +0.0198]** · **LUTONLY − DSH = +0.0030 [−0.0047, +0.0106]**.
`len(slots)`-weighted sensitivity is identical to three decimals.

**The one substantive observation, stated at its true strength:** on counterfactual labels the
fitted LUT **matches or slightly exceeds** `d_spawn_h` alone. That is the *opposite* of the
near-death counterfactual result, where the single raw feature beat the fitted model by
**+0.0875 [+0.0631, +0.1118]**. If it survives a corrected registration, the reading is that the
fitted model's failure to reproduce its own best feature **was a property of the outcome-broadcast
labels, not of the model class** — i.e. branch B1/B2 territory rather than B3.

**I am not declaring a branch.** The registered run is void; a void diagnosed after the fact is not
a result. Declaring B1 here would be converting a failed gate into a pass by reinterpretation,
which is the exact move this program refuses.

## ⚠ AND THE DEATH-CONDITIONING WAS NOT ESCAPED

The instruction was to re-run away from the near-death window. **Only partially achieved.**
Held-out states per band: **k=8: 83 · k=12: 83 · k=16: 83 · k=20: 83 · k=30: 5 · k=40: 5 · k=50: 5.**
So **332 of 344 held-out state-bands sit at k ≤ 20**, and the three genuinely-distant bands carry
five states each — no power at all. Per-band AUCs are reported in `refit_v2.log`, and the k=30/40/50
rows must not be quoted. A real escape needs a fork source that forks games which do **not** die;
`recon_c_fork.analyse()` returns early on `real == "clear"`, so it structurally cannot supply one.

## WHAT A CORRECTED RE-REGISTRATION NEEDS (cheap — the run is 5.6 seconds)

1. Gates expressed against the **measured** floor (≈0.55, global-permutation null) and **ceiling**
   (0.8404, exact-`p_hat` rank), not 0.5 and 1.0. Both are now measured and can be pre-committed.
2. Primary statistic = **difference-in-differences** (treatment Δ minus dose-matched null Δ), not an
   absolute AUC band — absolute AUC on this estimator has no fixed null.
3. The null must be the **global** permutation; the within-state permutation is documented-defective
   for this family and I should have used the documented form from the start.
4. Powered bands, or drop per-band reporting and state the death-conditioning as a hard scope limit
   rather than pretending the bank escapes it.

## ⚙ OPERATIONAL FINDING WORTH KEEPING

The first launch ran **62 threads at ~640% CPU for 11+ minutes without finishing**. Capped to
**4 threads**, the identical job — same data, same `n_iter=800`, same cache — completed in
**5.6 seconds end to end** (2.0 s per LUT fit). That is a ~100x difference from thread
oversubscription on a contended 24-core box, and it is why my "seconds-to-minutes" ETA was wrong:
I was estimating the *algorithm* while measuring a *thrash*.
⇒ **Cap threads explicitly on shared boxes; an uncapped scikit-learn/OpenMP job on a loaded host is
not slow-because-big, it is slow-because-contended.** And: **`hostname` before any compute launch —
a local working directory is not evidence about which machine you are on.**

---
---

# FINAL ACTIONS (2026-08-25, team-lead approved)

## Deleted memories restored — 4 of 4 that were recoverable
`dr-mario-smarter-experiments` (9 inbound — **the cascade-resolve negative, the last open n=10
door-closer**) · `dr-mario-tuck-action-space-gap` (5) · `dr-mario-v18-rom-ready` (3) ·
`dr-mario-dies-ahead-endpoint` (1). Each carries a banner marking it a **transcript
reconstruction, not original bytes**, with its inbound-link list and the instruction to verify
numbers against the cited rig. Six others (1 inbound each) had no transcript copy and are **gone
for good**: personality-select, strength-regression, dblcanon-i256, mode4-stall-131,
vod-audit-20260815, cart-identity-registry.

**⚠ The three restored after 17:15 are UNTRACKED in the new memory git repo** (`?? ` in
`git status`). They are not protected by the mechanism that was just created until someone
commits them. Left for the repo owner rather than committed by me.

## Corrected re-registration — WRITTEN, HELD FOR GO
`PREREG_STAGE2_RECHECK_v2.md`. Gates stated as fractions of **measured** headroom (floor 0.5527
global-permutation · champion 0.6357 · ceiling 0.8404), primary statistic is
**difference-in-differences**, null is the **global** permutation with the reason the within-state
one is not a null for a fitted arm, k=30/40/50 **struck entirely**, and a **prediction the
hypothesis forbids**: H forbids `d_spawn_h` beating the fitted LUT — the exact ordering the
near-death test found (+0.0875 [+0.0631,+0.1118]). If it reproduces, H is dead and the Stage-2
closure is vindicated on the merits. §7 states what a clean win licenses (one rollout arm, on
death-conditioned states within 20 plies of a topout) and what it does not (anything about healthy
play; anything general about learned evaluators; any promotion; any reopening of H15).

## ⚠ A CORRECTION TO MY OWN EARLIER CLAIM — the blocker is smaller than I said
I reported death-conditioning as structurally inescapable because `recon_c_fork` returns early on
`real == "clear"`. **True of that script, false as a statement about the program** — labels-146's
harvest machinery is a different and more capable path. Measured on the bank:

| k | discriminative decisions | mean `p_hat` | candidates at 8/8 |
|---|---|---|---|
| 8 | 92.0% | 0.568 | 20.2% |
| 20 | 94.7% | 0.728 | 37.9% |
| 50 | **84.0%** | 0.869 | 62.2% |

**The endpoint does not collapse away from death.** The k=30/40/50 weakness is **sample size, not
saturation** — the harvest took 25 states there against 300 at k≤20.
⇒ **Cheap fix: harvest ~900 more C-stratum states at k=30/40/50 from the SAME 1,500-game bank,
≈120 cpu-s/state ⇒ ~30 cpu-h (~7.5 h on Hetzner's 4 cores), pure labelling on games that already
exist.** That buys powered distant bands.
⚠ It still does **not** buy healthy states — every bank game is a topout. Harvesting from *cleared*
games is mechanically possible, but the trend above points at the **GW-void shape** ("a clean arm
can only measure speed, never survival"); going there requires changing the label to a
non-saturating one, which changes the estimand and needs its own registration.

---
---

# v2 RUN RESULT — **VOID AGAIN, ON THE SAME CLASS OF ERROR, FOR THE THIRD TIME**

Gates: CEILING 0.8404 **PASS** · constant 0.5000 **PASS** · discriminative decisions 307 ≥ 250
**PASS** · **`NULL_global` 0.4104 against a bound of 0.5527 ± 0.03 → VOID.**

## The cause, and the project had already written the fix down

I set the v2 null bound from **ONE draw** of the global permutation (0.5527). The v2 run drew a
different permutation and got **0.4104**. So I measured the null's distribution over **20
independent draws** (k≤20 held-out, 2.3 s per fit):

> **mean 0.5092 · sd 0.0401 · min 0.4333 · max 0.5597 · range spans 0.1264 AUC**

**The null is centred essentially at 0.5.** My "0.5527" was a +1.1 sd draw. My v1 band [0.45,0.55]
would have failed 7 of 20 draws; my v2 band 0.5527±0.03 would have failed about 14 of 20.
**Both null gates were miscalibrated because each was set from a single draw of a random variable.**

⚠ **`PREREG_STAGE2.md` had already made exactly this amendment, for exactly this statistic:**
*"the corpus's single `y_shuf` draw is +2.5 sd unlucky … a shuffled control is itself a random
variable and one draw is not a floor. Over 20 independent game-level permutations the null mean is
0.4960-0.5005."* The lane I am auditing solved this and I repeated the error anyway. That is the
third instance in this lane of **setting a gate against an unmeasured property of the instrument** —
after the LEAK ceiling and the fitted-arm floor.

## The substantive numbers — STABLE ACROSS BOTH RUNS, and still EXPLORATORY

k≤20, held-out, 82 seeds / 307 discriminative decisions. CEILING 0.8391 · CHAMP 0.6358 ·
headroom **H = 0.2033**.

| arm | AUC | headroom captured |
|---|---|---|
| **LUT_z1** | 0.6711 | **17.4%** |
| **DSH** (`d_spawn_h` alone) | 0.6597 | **11.8%** |
| null (mean of 20 draws) | 0.5092 | −62.3% |

**★ THE FORBIDDEN PREDICTION WAS NOT VIOLATED — and it went the other way.**
`cap(DSH) − cap(LUT) = −5.57% of headroom [−9.83, −1.36]`: **the fitted LUT BEATS `d_spawn_h`
alone, CI excluding zero.** In the near-death counterfactual test on outcome-broadcast labels, the
single raw feature beat the fitted model by **+0.0875 [+0.0631, +0.1118]**. The ordering reverses
on attributable labels.

⚠ **This is exploratory and I am not declaring V1.** The run is void on a registered gate.

## ⚠⚠ AND A FURTHER PROBLEM WITH RUNNING A v3: THE STATISTICS ARE NO LONGER BLIND

I have now seen these numbers twice. A v3 offline registration that reads the same statistics on
the same held-out rows **cannot be confirmatory** — it would be a gate fitted to a result I have
already seen, which is the precise move this audit exists to catch. Saying so is more useful than
running it.

Also, **`DiD` vs the null was a weak choice of primary**: a randomly-fitted LUT sits far *below*
the champion, so `cap(LUT) − cap(NULL)` is positive almost by construction and tests little. The
informative statistics are `LUT vs CHAMP` and the forbidden `DSH vs LUT` — both of which are stable
across both runs.

**⇒ RECOMMENDATION: stop re-registering offline. The offline test has now given what it can.**
The decisive next step is one of:
1. **The rollout arm** — the endpoint that was always the deliverable, on seeds disjoint from this
   bank. This is what a V1 would have licensed anyway.
2. **A fresh label harvest** (the ~30 cpu-h burst) giving *untouched* rows, on which a v3 gate
   calibrated from the now-measured null distribution (mean 0.5092, sd 0.0401) would be genuinely
   blind.
Option 2 before option 1 if the owner wants an offline gate that actually means something; option 1
directly if the goal is the endpoint.

**What is now solid and reusable regardless:** the instrument is fully characterised —
floor **0.5092 ± 0.0401** (20 draws), champion **0.6358**, ceiling **0.8404** — and any future gate
on this estimator can be stated against measured quantities instead of imagined ones.

---
---

# OPTION 2 (DIAGNOSTIC ONLY) — is PROGRESS learnable from the LUT's 8 features?

Framing adopted from team-lead: **diagnostic, never confirmatory.** I have read this bank
repeatedly; a further offline read cannot confirm anything. Its only job is to say whether progress
is learnable at all before spending on the blind agreement test.

## Sample size in DISTINCT BOARDS, as asked

The labels-146 bank is **already board-dedup'd**: **27,000 distinct boards**, 1,275 decisions,
325 seeds, median **22 distinct boards per decision**. Mean **1.190 slots per board** (2.000 on
double capsules), so the duplicate-slot collapse is largely already handled here.
⚠ **Do not conflate this with the H12 flip records**, which are SLOT-level: there the 4 "candidates"
collapse to ~2 distinct boards (88.7% of tie sets carry only two distinct outcome vectors). Two
different representations of the same hazard.

## Progress is discriminative — the mirror image of survival

| | flat / non-discriminative |
|---|---|
| **survival**, across H12's tied candidates (3,005 flips) | **90.8%** |
| **progress**, across bank decisions (1,275) | **17.2%** |
| progress, inside exact champion-value tie groups (2,107) | 46.1% (discriminates in **53.9%**) |

## ⚠ MY FIRST CUT MEASURED THE WRONG SUBSET — correcting before reporting

Over the **full** candidate set the champion's own value is the best progress ranker
(within-decision Spearman **+0.2927**), ahead of `d_spawn_h` (+0.2485) and the LUT fitted on
progress (+0.1939), with the permuted-label null at −0.0586. Read alone that kills the idea.

**It is the wrong test.** H12 acts only where the champion's top values are **EXACTLY TIED**, and
inside a tie the champion's value has **zero ranking power by construction**. The relevant subset is
the tie groups: **4,523 of 27,000 boards (16.8%) sit inside an exact-value tie**, 2,107 groups,
median size 2.

## THE RIGHT TEST — pairwise concordance inside champion-value ties

Median group size 2 makes Spearman degenerate (my first attempt found only 13 usable groups —
**not testable at that n**, and the null sat at +0.1942 against the LUT's +0.3077, i.e. noise).
Pairwise concordance uses all of them and matches the binary decision shape.

**Held-out, k ≤ 20: 296 discordant tie pairs across 66 seeds. Chance = 50%.**

| ranker | concordance | 95% CI | |
|---|---|---|---|
| **LUT fitted on PROGRESS** | **55.5%** | [51.5, 59.3] | **above chance** |
| `d_spawn_h` alone | 53.6% | [51.1, 56.3] | above chance |
| NULL (permuted labels) | 48.7% | [45.2, 52.3] | includes 50% ✓ |
| slot-order tiebreak | 49.2% | [42.7, 56.0] | includes 50% ✓ |

**Both pre-committed baselines behave**, so the 55.5% is signal rather than artefact.

## READING — alive, weak, and not resolved

**Progress IS learnable from these features inside exact champion-value ties, but weakly:
~5.5 points of concordance above chance.** The LUT edges `d_spawn_h` (55.5 vs 53.6) but the CIs
overlap heavily — not distinguishable at n=296.

**What this does NOT tell us:** whether 55.5% concordance is enough to reproduce H12's −4.78pp.
H12 measures progress directly by forking; a static delta recovering a few points above chance may
capture only a small fraction of its tie-resolution quality. **That is exactly the agreement test
(Option 1), and it is blind because those flip records do not exist yet.**

⇒ **Option 2's verdict: do not stop. The target is live, the features carry some of it, and the
question is now a quantitative one that only the blind test can answer.**

---

# VALUE-TRANSFER ARITHMETIC (pre-prereg gate) — team-lead's naive estimate was low by ~3x

**Naive (team-lead):** (55.5−50)/(100−50) ≈ 11% of H12's advantage ⇒ ~−0.5pp. **Two material errors.**

**Error 1 — concordance is not linear in value.** Computing the transfer directly in PROGRESS units
(fraction of the oracle's achievable progress-gain over a random tie pick, margin-weighted by
construction) gives **22.8%**, not 11%. Value is concentrated in high-margin ties:

| margin stratum | n | LUT transfer | share of total value |
|---|---|---|---|
| 0-3 | 114 | 7.4% | 13.1% |
| 3-6 | 63 | 15.9% | 16.5% |
| 6-12 | 53 | 1.7% | 28.4% |
| **12+** | 29 | **44.6%** | **41.9%** |

**Error 2, the bigger one — H12 IS NOT A 100% ORACLE.** It draws 5 forks and applies a margin≥3
gate, so simulating its own procedure it achieves only **73.4%** of the achievable progress-gain
(**83.2%** on the subset where it actually fires). Dividing by 100% understates the LUT's share.

**CORRECTED, both cuts agreeing:**

| | all discriminating ties (n=259) | where H12 fires, margin≥3 (n=145) |
|---|---|---|
| H12's own achieved transfer | 73.4% | 83.2% |
| LUT fitted on progress | **22.8%** CI [4.1, 41.8] | **25.1%** CI [4.4, 46.0] |
| `d_spawn_h` alone | 17.8% | 20.8% |
| **LUT as a fraction of H12** | **31.0%** | **30.2%** |
| **projected endpoint** | **−1.48pp** | **−1.44pp** |

## VERDICT ON THE GATE: the arithmetic SUPPORTS proceeding, but does NOT resolve the question

The point estimate **−1.45pp** sits at the bottom edge of the −1.5 to −2.0pp band I called worth
detecting, and clearly above the ~1pp floor below which I argued we should not care. **But the CI
on the transfer [4.1%, 41.8%] maps to an endpoint range of roughly −0.2pp to −2.7pp** — it spans the
decision boundary. An offline projection that cannot separate "not worth it" from "clearly worth it"
is exactly the case where the experiment earns its cost, and my power analysis gives MDE **0.99pp at
N=12,000**, which resolves a −1.45pp effect comfortably.

⚠ **Load-bearing modelling assumption, stated:** this projects H12's −4.78pp as scaling linearly
with the fraction of tie-progress-gain captured. That is an assumption, not a measurement, and it
could be wrong in either direction. It is also diagnostic and non-blind. **The projection justifies
running the blind test; it cannot substitute for it.**

---

# FORK-COUNT / MARGIN-GATE SWEEP (zero new games) — and a correction to my own projection

## 1. FORK COUNT PLATEAUS AT ~4-5. More samples do NOT buy transfer.

Split-sample (decide on k forks, score on the remaining 8−k), 259 held-out tie groups, margin ≥3:

| forks | 1 | 2 | 3 | 4 | **5 (H12)** | 6 | 7 |
|---|---|---|---|---|---|---|---|
| transfer | 30.8% | 37.8% | 37.3% | 39.5% | **39.6%** | 34.5% | 31.4% |

Flat from k=4. (The apparent fall at 6-7 is estimator degradation — fewer evaluation forks remain —
not a real decline.) **⇒ H12's fork count sits AT the plateau. The "improve the teacher by adding
samples" branch is CLOSED.**

**⚠⚠ AND THE IN-SAMPLE VERSION WOULD HAVE SAID THE OPPOSITE:** deciding and scoring on all 8 forks
gives **47.2% at k=1 → 65.6% at k=3 → 81.0% at k=5 → 86.7% at k=8** — a steeply climbing curve that
would have recommended buying more forks. It is pure winner's curse. This is the project's own
standing rule (*"never quote a best-of-N gain without a split-sample estimator or a permutation
null"*) paying for itself on the first use.

## 2. THE MARGIN GATE COSTS TRANSFER — but transfer does not price what the gate is for

At 5 forks, split-sample: margin **0 → 44.6%** · 1 → 40.9% · 2 → 39.6% · **3 (H12) → 39.7%** ·
4 → 35.3% · 6 → 32.9% · 8 → 29.5% · 12 → 23.4%. **Monotone: the gate costs ~5 points of transfer.**

⚠ **But the margin gate is a CHURN control, and transfer is blind to churn.** Stage-2 measured that
perturbing 1.8% of plies reshuffles ~20% of game outcomes. Opening the gate raises flip count and
therefore breakage. **This is a real lead and NOT a free win — it trades progress-capture against
churn, and only an endpoint can price that trade.**

## 3. ⚠ CORRECTION TO MY OWN −1.45pp PROJECTION — it was wrong in the LUT's disfavour

My earlier H12 baseline (73.4%) was **in-sample**: H12 chose using 5 of 8 forks and was scored on
all 8, including the 5 it chose with. The LUT uses no forks so its number was unbiased; H12's was
not. Apples-to-apples, split-sample:

| | transfer |
|---|---|
| H12 (5 forks, margin ≥3) | **39.1%** (sd 6.0) |
| LUT (static, no forks) | **18.8%** (sd 5.6) |
| **LUT as a fraction of H12** | **48.0%** (was 31.0%) |
| **projected endpoint** | **−2.29pp** (was −1.48pp) |

**The projection nearly doubles and now sits ABOVE the −1.5 to −2.0pp band.**
⚠ **Read the RATIO, not the levels** — the split-sample denominator is upward-biased and deflates
both. `PREREG_H12_SUBSTITUTION.md` is amended accordingly, before any flip record exists, with the
struck value kept visible.

## ⚠ HORIZON MISMATCH — a third assumption under the projection (found after the sweep)

**Certified H12 forks at `H=15`; the labels-146 bank's forks are `H=25`** (verified both sides).
Every "simulated H12" number here ranks **H=25** progress — not what H12 optimises. The **ratio**
remains like-for-like (both rankers scored on the same target); the **mapping to H12's −4.78pp** now
stacks three assumptions: linearity, the split-sample denominator, and this horizon substitution.
⇒ **−2.29pp is a rough prior, not a commitment.** The confirmatory test is immune — it generates
fresh records from real H12 at H=15.

## ⚠ AND THE REQUESTED k ∈ {5,8,12,16} SWEEP IS NOT RUNNABLE

**The bank stores exactly 8 forks per candidate.** k=12 and k=16 cannot be measured from it at all,
and k=8 has no forks left to score on split-sample. The measurable range is k=1..7.
**Stating the ceiling rather than extrapolating past it**, as instructed.

---

# ⚠ PROVENANCE TRAP HIT DURING EXECUTION — `h12_arm.py` DIFFERS ACROSS WORKTREES

The sanctioned deploy script (`deploy_hetzner_oracle.sh`) ships **`dr-mario-te/oracle-source`**.
That tree's `h12_arm.py` is **not the same file** as the one that produced the flip records this
experiment is built on. Measured md5:

| worktree | md5 `h12_arm.py` |
|---|---|
| **dr-mario-champ145-wt** (has `SEALED_H12_MANIFEST.json`; produced the 3,005 records) | `dd5358191b824d38ac144f5d3594bd0b` |
| dr-mario-te/oracle-source (what the deploy script ships) | `3421c27967f8d51c9e42199c6055e5ac` |
| dr-mario-h16-wt | `4e0803d7831249cd97d96d1fa7560268` |

**Diffed rather than assumed.** The differences are the H14 amendment:
· te/oracle-source is the original: `if fv[0] != fv[1]` — exact tie only, **no `trigger_eps` at all**;
· champ145 adds `trigger_eps`, with `fv[0] - fv[1] > self.trigger_eps`;
· h16 adds a further candidate filter **gated on `trigger_eps > 0`**.

**At the certified setting `trigger_eps = 0.0` all three are behaviourally identical** — `fv` is sorted
descending so `fv[0] - fv[1] > 0.0` ≡ `fv[0] != fv[1]`, and the h16 block is inert at eps=0. The flip
records carry `arm: "h12_true_m0.5_e0.0"`, confirming eps=0.

⇒ **No harm done, but the trap is real and general:** *the sanctioned deploy script points at a
different worktree than the one holding the sealed manifest and the data.* Following it blindly
would have shipped a different file than the one under analysis. **Deployed champ145 deliberately
and pinned its md5 on the remote as a check.** Same family as
[[dr-mario-base-rom-collision]] and [[dr-mario-clean-clone-repro]].

---

# YIELD / COST / BOUNDARY — measured on the burst node (drm-burst-7)

**Yield, n=20 seeds, instrumented arm only, cap 300, 12 workers:**
flips/seed **mean 4.15 · median 4.0 · sd 1.85 · min 1 · max 8** · **zero-yield 0/20 = 0%** ·
stall-at-cap **4/20 = 20%** · res mix clear 13 / topout 3 / stall 4 · **planes on 83/83 flips**.

⚠ **BOTH earlier estimates were wrong, in the same direction, and both came from n=2.** My "50%
zero-yield" and the derived "129 core-s/flip ⇒ ~36 core-h ⇒ 1.8x over" were built on two seeds, one
of which happened to be a zero-yield stall. **Measured: 82 core-s/flip ⇒ 22.8 core-h per 1,000 flips
⇒ 1.14x §9's ~20 core-h.** Essentially on estimate. Throughput 96.1 seeds/h wall at 12 workers.

**Boundary/differential censoring (banked paired H14, n=1,816, cap 400):** at-cap base **9.47%** vs
trt **9.20%**, Δ **−0.28pp** against McNemar SE **0.56pp** — no evidence of net differential
censoring. ⚠ But **105 pairs (5.8%) boundary-discordant, 5.5x the clear-rate effect (+1.05pp)** in
the same data: **the cancellation is empirical, not structural.** Pre-registered as §11.

---

# RUN LAUNCHED — and a program-level resource finding

**`drm-subst` active 2026-08-26 00:23:01Z** on drm-burst-7: N=1,666 · cap 400 · L20 · 12 workers ·
resumable, per-seed atomic. ETA ~14 h. Blocking 200-seed interim SE check armed.

## The seed-block defect, and which half of it was real

Team-lead flagged two defects in my proposed block 80000+. **Checked both rather than accepting.**
- **FOLD COLLISION — REAL.** 80000..83330 folds mod 65536 to stream keys 14464..17794:
  **1,000 of 1,666 keys collide = 60.0%** (their estimate 68%; substance right, arithmetic off).
  A literal integer-range assertion cannot represent this — rule 16, and mine was the blind kind.
- **DEAD-LOW-BIT HALVING — NOT REAL.** The runner already emits `seed_lo + 2*i`, so every seed is
  even and every seed is its own stream: **1,666 seeds → 1,666 distinct keys, verified.** The
  proposed remedy (3,332 raw seeds, ~28 h) would have **doubled a 14-hour run to fix nothing.**

**Fixed assertion:** fold mod 65536 → reduce to stream key `>>1` → assert key-disjointness →
assert `len(distinct keys) == N`. Alias triple `{0, 35208, 35209}` excluded by construction —
**35208 sat inside the range otherwise chosen.**
**Gated by its own negative control:** chosen block PASSES; old block **FAILS** with
`STREAM-KEY COLLISION: 1000 keys`.

## ★ PROGRAM-LEVEL CONSTRAINT, not a footnote of this run

Searching stream-key space for a free block produced a number nobody had quantified:
**52.5% of all 32,768 distinct pill streams are already consumed**, and the **longest contiguous
free run is 4,050 streams** (keys 16500..20549). Large future experiments must be planned against a
**shrinking pool**, and per-lane "reserved block" notes are no longer adequate — a **stream-key
registry** is the right fix. Team-lead has banked this as a program constraint.

---

# TIMELINE OF THE INTERIM GATE — recorded from mtimes, with the inference limits stated

| file | mtime (UTC) |
|---|---|
| `h12_boards.py` | 02:56:04 |
| `subst_run.py` | 03:03:53 |
| **run relaunched** | **03:03:58** |
| `interim_gate.py` | **03:08:17** |

**Team-lead's correction is accepted on the substance:** there was a window after the relaunch in
which the interim gate's degenerate-exclusion logic was not on the box. Their grep at ~03:07 found
no `prog.max` / `n_degen` anywhere, which is direct evidence.

⚠ **But the mtime argument they offered does not by itself support it, and I am recording that
rather than letting a convenient inference stand.** `mtime` is **last modification, not creation** —
`interim_gate.py` was rsynced with the relaunch bundle and then re-shipped twice (flips anchor, then
degenerate counting), so 03:08:17 is the last write. **An mtime cannot establish absence.** Their
grep can; my mtime cannot. Neither of us can now recover the exact file state at 03:07.

⇒ **My earlier phrasing — "implicit when you grepped" — asserted more than I could show, and the
honest version is: the gate's degenerate logic was demonstrably not present at 03:07, and I cannot
establish from mtimes whether an earlier version of the file was.** Nothing was harmed either way:
n=200 was not reached until long after, and no interim ever ran against the un-filtered logic.

---

# THE `implied_N = 1` DEFECT — cause, fix, and a near-miss

**Cause (mine).** The interim's variance proxy was `(median − mean)/(max − mean)`. For a tie of
shape `[a,a,b,b]` the median **equals** the mean, so the statistic is **identically zero** — and
that shape is **5,274 of 5,689** discriminating ties. Measured: **exactly 0 on 89.8% of ties**,
per-seed sd 0.031, SE 0.19pp. A near-constant statistic, whose variance had nothing to do with the
transfer estimator's. **`implied_N = 1` was that artefact.**

★ **This is the duplicate-board pairing for the THIRD time in one night** — it killed
`margin_sum > 0`, explained the 9× tie-rate puzzle, and produced this degenerate variance. **It
should be the first thing checked when any statistic in this codebase behaves oddly.**

**Diagnosis, three steps, in the order team-lead specified.** (1) The clustering was fine — the
statistic was broken. (2) Per-seed distribution was decisive: sd **0.1487** broken vs **0.2938**
correct, spanning the full ±1, so per-seed transfers do *not* barely vary. (3) Bootstrap **1.86pp**
vs plain `std/√n` **1.83pp** — agreement localised the fault to the input, not the estimator.

**Fix.** Proxy is now the transfer statistic under a blind random pick (right variance structure,
no ranker scored). **And the gate is two-sided**: it now also stops on `implied_N < 20`, the
direction it was structurally unable to fail in.

## ⚠ THE NEAR-MISS — a stale mirror produced a CONVINCING false STOP

The first corrected run printed `flips_ok=False verdict=STOP_AND_REPORT` at **4.35 ± 0.23**.
**Not reported, because the format was checked first.** Cause: **34 of 257 LOCAL files were stale
old-format** (flip-only, no `is_flip`) from the stopped run, contributing **zero** flips each. On
new-format files only: **flips/seed 5.013 ± 0.230, upper 95% 5.464 ≥ 5.05 → PASSES.**

⇒ **A missing file throws; a STALE file in an older schema returns a number in range, in the right
units, in the direction you were told to fear.** 4.35 was precisely the record-loss signal we had
pre-registered to watch for. **Purge or version the analysis mirror when a capture format changes,
assert the schema per file, and prefer the producer's own directory over a mirror.** Sibling of
"silence is not success" — here the failure mode is not silence but **a convincing lie**.

---

# ★ WHY THE RUN IS STILL GOING — precision, not validity

Two independent read-only checkpoints on the producer's directory:
**implied_N = 63 at 223 seeds · implied_N = 56 at 342 seeds.** Converging, and both far below the
registered N=1,666. **The run is already ~6× past its own sufficiency threshold.**

⇒ **The remaining ~12 hours and ~€3 buy PRECISION, not VALIDITY.** Recorded because it changes
three things:
1. **If anything goes wrong later — node fault, schema surprise, checkpoint failure — stopping
   early is a SAFE option, not a compromise.** The registered power requirement is already met
   several times over. That comfort did not exist twelve hours ago.
2. The extra data materially improves the **secondaries**, which were always the thin part:
   per-band breakdowns, at-cap fraction, degenerate share, boundary-discordance.
3. **Nobody should read "1,666" as required.** It is conservative by design and now demonstrably
   so — sized on a 15.5pp prior that the corrected instrument measures at ~2.8pp.

# DEFECT NINE — a correct check with no path to execution

`subst_run.py:99` = `if n == 200:` — **one-shot**. It fired at **04:49:17Z** with the broken
statistic; `interim_gate.py` was corrected at **05:02:23Z**, **13 minutes later**; and the live
process holds the old file in memory, so editing it changes nothing. **The remaining ~80% of the
run had zero variance coverage.**

The other eight defects were wrong values, wrong populations, or checks that could not FAIL.
**This was a correct check that could not RUN** — and a one-shot trigger that has already fired is
indistinguishable from a working gate in every log line and every summary.
⇒ **Rule: a check must be able to RUN, not merely able to fail. Verify it has a live trigger, not
just correct logic. Fixing a check and wiring a check are two different jobs.**

**Remedy, no restart:** `drm-gatewatch` polls the producer's directory and invokes the corrected
gate with `--stop-on-fail` at **n = 400, 800, 1200**, exits if `drm-subst` goes inactive, and aborts
remaining checkpoints on any failure. Three real self-stopping opportunities where there were zero.

⚠ **Credit correction:** team-lead noted the script uses `set -u` without `set -e`, which matters
because `[ $rc -ne 0 ] && {…}` as the last statement in a loop body returns false on success — under
`set -e` that would kill the watcher every time a checkpoint PASSED. **That was luck, not design.**
I used `set -u` deliberately and did not reason about `set -e` at all. Recording it as accidental so
the next person hardens it on purpose rather than trusting a habit that happened to be right.

---

# THE `set -e` HAZARD WAS REFUTED — four layers, every one wrong until measured

1. team-lead praised `set -u` without `set -e` as a subtle correct choice.
2. I declined the credit, calling it **luck**.
3. team-lead said documenting luck is step one — **remove it**.
4. **I tested it and there was no luck.** bash 5.2.37:
   `[ ] && { }` last in a loop body, condition false, `set -e` → **exit 0** ·
   same at script level → **exit 0** ·
   **CONTROL**, bare `false` in that position → **exit 1**.
   `set -e` is exempt for a command failing as a **non-final part of an AND-OR list**, so the
   `[ … ]` never triggers errexit. **Both forms are safe.**

⚠ **I nearly shipped a confident comment explaining the non-existent mechanism.** That would have
been worse than the non-bug: **a false comment is more durable than a false line of code** — code
gets refactored, a confident explanation becomes inherited fact and the next person hardens *back
toward* the phantom on its authority. Caught only by running the demonstration **before** shipping.

⇒ **RULE: documenting luck is right, but CHECK THE LUCK IS REAL before removing it.** Sibling of
"verify the premise, not just the task" — pointed at **praise** rather than instruction.

⇒ **AND ONE FROM THE VERIFICATION ITSELF:** team-lead's first attempt piped each case through
`sed` for indentation, so `$?` was **sed's** status — a **vacuous control inside a test about
whether controls can fail.** Caught only because its result contradicted mine.
**`cmd | sed` destroys the exit code you are trying to measure — capture to a file or use
`PIPESTATUS` whenever the status is the observable.**

---
---

# ★★★ SUBSTITUTION ARM — FINAL RESULT (run complete, 1,666/1,666)

**Population:** 41,063 discriminating champion-value tie groups over **1,665 seeds** · 70,074 tie
plies of which **29,011 degenerate (41.4%)**, excluded per Amendment 5 · cap 400 · L20 lulu ·
seeds 33000-36332, stream-key disjoint · 71,740 records verified identical remote and local.

## 1. CONTROL PANEL FIRST — all five land where construction demands

| picker | transfer | 95% CI |
|---|---|---|
| **H12's own pick** (must be +100% by construction) | **100.0%** | [100.0, 100.0] |
| ORACLE (max progress) | 115.8% | [115.2, 116.4] |
| CHAMPION's pick | 37.3% | [35.8, 38.7] |
| **random tie-break** (must be ~0) | **−1.2%** | [−2.8, +0.5] |
| WORST candidate | −116.0% | [−116.7, −115.3] |

**The estimand is sound.** Note the champion at **+37.3%**, not the −93.7% of the flip-selected
population — the selection defect is gone, exactly as the corrected capture was meant to achieve.

## 2. ★ PRIMARY, AS REGISTERED (§4)

> **LUT transfer = 6.8% of H12 · 95% CI [5.1, 8.5]** (seed-clustered, B=4000)

**S1 requires the CI lower bound > 20%. Lower bound = 5.1%. S1 DOES NOT FIRE.**
**§6 S3 requires the CI upper bound < 15%. Upper bound = 8.5%. ★ S3 FIRES:
FUNCTION-CLASS WALL, HONESTLY LOCATED.**

## 3. ★★ THE FORBIDDEN PREDICTION IS VIOLATED — H falsified by its own registered test

§5 registered: *"H forbids `cap(DSH) − cap(LUT) > 0` with a CI excluding zero."*

> **cap(DSH) − cap(LUT) = +23.2% · 95% CI [+21.2, +25.3]**
> LUT **6.8%** · **d_spawn_h alone 30.0% [28.5, 31.6]**

**A single raw feature beats the fitted 8-feature LUT by 4.4×, CI excluding zero.** That is exactly
what the hypothesis forbade, committed in advance. **H is falsified on its own terms.**

⚠ **And it REVERSES the offline diagnostic that motivated this experiment.** Offline the LUT
matched-or-beat `d_spawn_h` (+0.0105 [+0.0010,+0.0198]); on blind confirmatory data it loses 4.4×.
**The offline result was not merely optimistic — it had the sign of the comparison wrong.**

## 4. SECONDARIES

**Per within-game quartile — flat**, no band effect: Q1 6.6% · Q2 7.3% · Q3 7.0% · Q4 6.6%.
**Margin strata:** 0-3 → 6.8% (95.7% of value) · 3-6 → 3.2% · 6-12 → 8.1% · 12+ → 17.2%; all but
the first have CIs including zero. **Games:** 1,666 — clear 1,051 / topout 487 / stall 128;
**at-cap 7.7%**, median 224 plies.
⚠ **At-cap PER ARM and boundary-discordance are NOT APPLICABLE**: this design plays ONE arm and
scores the LUT offline on H12's own trajectory, so both "arms" are the same games and differential
censoring cannot arise. §11's diagnostics belong to a rollout A/B.

## 5. ⚠ A CONFLICT BETWEEN TWO REGISTERED CLAUSES — declared, not resolved unilaterally

§9 says a point below ~27% should be reported **"NOT RESOLVED AT THIS n."** §6 S3 says an upper
bound below 15% is a **function-class wall**. Both conditions are met.

**S3 governs, and here is why:** §9's clause exists to protect against *insufficient power* — it
was written assuming SE ≈ 15.5pp/√n, under which a point below 27% would carry a CI straddling
everything. **The realised CI is ±1.7pp, roughly 9× tighter than the design assumed.** The result
is not ambiguous; it is **precisely measured and small**. "Not resolved" would misdescribe a
tightly-bounded estimate as noise. **Flagged for adjudication rather than settled by me.**

## 6. WHAT THIS LICENSES

**★ The Stage-2 closure is VINDICATED ON THE MERITS — but not for its original reasons.** The
original closure's *reasoning* was genuinely defective: outcome-broadcast labels, a mandated band
analysis computed and never reported, and a decisive oracle GO never used to reopen the branch.
**The audit was right that the closure was unsound; the confirmatory test says the conclusion was
nevertheless correct.** Those are different things, and keeping them apart is the point.

**★★ AND A LIVE LEAD, WHICH IS THE REAL PRODUCT:** `d_spawn_h` ALONE transfers **30.0%
[28.5, 31.6]** of H12 — landing exactly on the pre-registered expected effect and clearing S1's
bar. **One raw feature, no fit, no 288-entry table, no training data.**
⚠ **This is NOT a promotion.** `d_spawn_h` was a COMPARATOR, not the registered arm; it gets no
verdict from this design and needs its own registration. But it says the **substitution IDEA is
alive while the FITTED LUT is dead**, which is more useful than either a flat pass or a flat fail.

---

# ★★★ PRE-COMPUTE KILL — `d_spawn_h` AS A DECIDER IS WORSE THAN DOING NOTHING (2026-08-26)

**Found for €0, from data already banked, between Tier-2 sign-off and Tier-1 launch.** It came out
of the team-lead's single clarification question — *"which arms does the McNemar pair?"* — because
forcing the −1.43pp target to name its comparison forced me to ask what the **champion** scores on
the same scale. **Defect twelve was real and one level deeper than flagged: not a mis-pointed
comparison, a SIGN ERROR, because the baseline arm's own capture was never subtracted.**

## The number
The completed substitution run's **pre-committed** control panel already contained the baseline:

| picker | transfer |
|---|---|
| H12's own pick | 100.0% |
| **CHAMPION's own tiebreak** | **37.3%** |
| **d_spawn_h** | **30.0%** |
| random | −1.2% |

> ### `cap(DSH) − cap(CHAMP) = −7.3 points · 95% CI [−8.2, −6.3]` — seed-clustered B=4000, n=1,665 seeds, **EXCLUDES ZERO ADVERSELY**
> ### projected played effect **Δ = +0.55pp [+0.48, +0.63]** dies-ahead — **treatment WORSE than the plain champion**, against a registered projection of **−1.43pp better**.

**Estimator validated before use, against two independently registered results:** it reproduces all
six registered panel entries exactly (100.0 / 115.8 / 37.3 / −116.0 / 6.8 / 30.0) and reproduces the
registered forbidden-prediction contrast `cap(DSH) − cap(LUT) = +23.2% [+21.2, +25.2]` against its
registered [+21.2, +25.3]. A gate that has only ever passed is not a gate — this one had to
reproduce numbers it could have missed, and did.

## The mechanism, measured at the VALUE level (not slots — §0.1's duplicate hazard)
| | ties | share |
|---|---|---|
| B H12 flips, TRT does not (value forgone) | 7,471 | 18.19% |
| C both flip, same value (captured) | 733 | 1.79% |
| **E TRT flips where H12 did NOT (unpriced)** | **3,426** | **8.34%** |

TRT reproduces **8.8%** of H12's value-flips; **80.3% of TRT's own flips have no H12 precedent** and
are harmful on the label (mean progress **−3.26**, worse **73.2%** of the time); TRT's divergence
dose is **51.3%** of H12's. **It does not merely rank worse — it fires at a different and
worse-chosen set of plies.** No margin stratum rescues it: 0-3 (95.2% of value) [−8.6, −6.5]; the
three strata whose CIs include zero hold 4.8% of the value between them.

## ★ THE LAW — the generalisable product, and the third time this program has paid for it
> **A comparator is scored on the target's trigger set; a decider CHOOSES ITS OWN.**
> `d_spawn_h` was scored at H12's tie plies and never had to decide *whether* to act. Given that
> choice it acts at 3,426 ties H12 deliberately left alone, and loses more there than it gains
> everywhere else.
> **Scoring a substitute against the TARGET while never scoring it against the BASELINE IT REPLACES
> is what manufactured the 30%.** Same family as the LUT's 0.7220 AUC and its +0.0105 offline edge —
> one collapsed, one reversed sign. **Off-policy capture is an UPPER bound on decider quality**
> (the substitute is evaluated on states the better policy produced and never has to recover from
> its own mistakes), so −7.3 is the optimistic end.

## Consequences
- **Tier 2 (N=7,743, ~€18, ~3 days): WITHDRAWN before launch.** The €18 is not spent.
- **Tier 1: GO, unchanged in cost/seeds/runner, verdict rule corrected and re-registered first** —
  primary is now `cap(DSH) − cap(CHAMP)`, two-sided, N=110 sufficient (SE inflates 3.89× ⇒ ≈[−11.0,
  −3.6], still excludes zero).
- **The sizing machinery was never the defect** and is retained: it reproduces the registered
  N=7,743 at ψ=15.07% to 0.4%, and shows N is **monotone increasing** in ψ over the plausible range
  ψ ∈ [8.1%, 15.1%] — so the borrowed ψ was the **conservative** end and N=7,743 was the worst case,
  not a lucky guess. **The effect's sign was the defect.**

## Robustness of the kill — direction and magnitude carry DIFFERENT caveats

**Assumption-free per-seed sign test** (no capture normalisation, no linear map, no bootstrap):
**899 seeds land worse progress under `argmin d_spawn_h` than under the champion's own tiebreak,
446 land better, 320 never diverge — two-sided exact binomial p = 1.49e-35, 66.8% of decided seeds
against the treatment.**

⚠ **The caveat belongs on the MAGNITUDE, not on the direction.** Dropping the 5% most adverse seeds
moves the estimate from **−7.3 pts to −4.1 pts** — so the tail inflates *how big* the harm is, while
the *sign* is carried by two-thirds of all decided seeds independently of any tail. **Still adverse,
still excluding zero, on every cut tried.**

---

# ★★★ THE ROUTE, NOT JUST THE FEATURE — NO STATIC TIE-DECIDER BEATS THE CHAMPION

Follow-on triage once the baseline was in view. All 12 shipped candidate features, **both
directions**, scored as tie-deciders on the same 41,063 discriminating ties. Machinery validated by
the known answer first: it reproduces `argmin(d_spawn_h)` at **30.0%, −7.3 pts [−8.3, −6.2]** and
the champion at **37.3%** exactly.

**NOT ONE OF THE 24 BEATS THE CHAMPION'S OWN TIEBREAK.** Best in sample:
`argmin(b_spawn_prox_strict)` at **37.2%**, −0.1 pts [−0.2, −0.0] — CI excludes zero *adversely*.

> **⇒ The inference is one-sided and multiplicity-immune: in-sample best-of-N is biased UPWARD, so
> an in-sample best that still LOSES cannot be rescued by correcting for the 24 looks.**

## ★ And the mechanism, which is the part that generalises

| decider | transfer | override dose | harm per override |
|---|---|---|---|
| argmin(b_spawn_prox_strict) | 37.2% | **0.1%** | −142.8 pts |
| argmax(c_das_reach) | 36.5% | 1.0% | −74.7 pts |
| argmin(d_crit_cols) | 35.0% | 2.7% | −85.8 pts |
| **argmin(d_spawn_h)** | **30.0%** | **10.4%** | −70.2 pts |
| argmin(x_hvar) | −1.8% | 48.2% | −81.0 pts |

> ### `corr(transfer, override dose) = −0.987` across all 24 · **harm per override is NEGATIVE for 24 of 24**
>
> **The deciders that come closest to the champion are exactly the ones that override it least.
> The apparent near-misses are INACTIVITY, NOT SKILL — the only way for a static rule to look good
> here is to not act.**

⚠ **Caveat sits on the per-override magnitude, not the sign:** for the sub-1%-dose deciders that
ratio has a tiny denominator and is unstable (hence −142.8 for a rule that acts 0.1% of the time).
**The robust facts are the sign (24/24) and the correlation (−0.987).**

## What this closes, and what it explains
- The **static-substitute route is dead at the function-class level**, in both forms this program
  tried: the *fitted* 8-feature additive LUT (**6.8%**, i.e. **−30.5 pts** vs the champion) and now
  every *raw* single feature in both directions. **The fitted model is worse than almost every raw
  feature it was built from** — an indictment of its training target (survival, when H12 keys on
  progress) rather than of the feature set.
- It **explains H12** rather than merely losing to it: the rollouts are worth +62.7 points over the
  champion precisely because they can tell **which ties are worth overriding**. No static function
  of the post-placement board can, and every one tested that tries, loses in proportion to how often
  it tries. **That is the cascade's middle step failing for a structural reason, and it is a more
  useful finding than any single arm's number.**

---

# ★★★ TIER 1 RESULT — T1-a, THE KILL REPLICATES ON FRESH STREAMS

**drm-burst-8, 110/110 seeds [17440..17658 step 2], keys 8720..8829, cap 400, L20, wall 1.15h,
€0.74.** Gates before results: bit-exactness digest **identical to drm-burst-7**; G-IDENTITY
**20/20**; G-MUTANT differs on **19/20** (the gate can fail); interim checkpoint at n=50
**CONTINUE** (flips/seed 4.54±0.41 vs the 5.05 anchor); final flips/seed **5.07**; pull
**byte-identical**, 4,982 rows both sides.

## 1. CONTROL PANEL FIRST — all five land

| picker | fresh block | reference block |
|---|---|---|
| H12's own pick | 100.0% | 100.0% |
| ORACLE | 117.5% | 115.8% |
| **CHAMPION's own tiebreak** | **38.2%** | **37.3%** |
| random | 0.0% | −1.2% |
| WORST | −116.7% | −116.0% |

## 2. PRIMARY, AS REGISTERED IN AMENDMENT 1

> ### `cap(DSH) − cap(CHAMP) = −8.3 pts · 95% CI [−11.9, −4.7]` — **EXCLUDES ZERO ADVERSELY**
> cap(DSH) = **29.9%** · cap(CHAMP) = **38.2%** · 2,899 discriminating ties over 110 seeds
> projected dies-ahead **Δ = +0.64pp [+0.36, +0.92]** — worse than the plain champion.
>
> **VERDICT: T1-a.** The reference block gave −7.3 [−8.2, −6.3]; the fresh block gives
> −8.3 [−11.9, −4.7]. **Two independent blocks, same sign, overlapping intervals.**

## ★★ AND THE POINT OF CORRECTING THE VERDICT RULE, DEMONSTRATED

> **The 30.0% DID replicate — 29.9%, to one tenth of a point.**
> Under the **original** Tier-1 rule that is a clean PASS, and it would have been reported as
> *"the lead holds"*. Under the corrected rule the identical number is a **confirmed kill**, because
> the baseline it must beat is 38.2%. **The same measurement, read against the right comparator,
> reverses its meaning.** Registering `cap(DSH) − cap(CHAMP)` before the block existed is the only
> reason this run answers a question instead of manufacturing a headline.

## 3. THE ROUTE-LEVEL FINDING, NOW HELD OUT

Block A's in-sample best-of-24 was `argmin(b_spawn_prox_strict)` (37.2%). **Tested on block B as a
single pre-selected hypothesis — no multiplicity — it lands −0.2 pts [−0.5, +0.0]: it does not beat
the champion.** Block B's own best is `argmax(b_spawn_prox_strict)` at +0.0 pts [−0.8, +0.9] — also
not a win, and **the winning DIRECTION FLIPPED between blocks**, which is the signature of noise
rather than signal. `argmin(d_spawn_h)` reproduces at 29.9% / −8.3 pts.

**⇒ On two independent blocks, no static single-feature tie-decider beats the champion's own
tiebreak, and the apparent leader does not survive being held out.**
