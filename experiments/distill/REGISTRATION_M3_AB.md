# REGISTRATION M3 — on-policy A/B of the distilled danger guard
distill-coproc lane · **DRAFT 2026-08-28 · HELD FOR TEAM-LEAD SIGN-OFF ·
NOTHING LAUNCHED · NO SEEDS CLAIMED**

Implements DESIGN.md §D under the R1 riders. Two dependencies are open and
named in §8 — this document is complete enough to review and to argue with,
and it is **not** launchable until they close.

---

## 0. Status and proof of timing (R28)

At the time of writing: **M2's verdict does not exist** (A5 PHASE 1 is running;
the only fit reading in existence is the pre-A5 BETWEEN at held-danger n=93).
**No guard `g` has been fitted on the enlarged bank.** Every bar in §3 and §4
is therefore derived on reference data that predates the object it will judge,
which is the whole point of R62 — and the derivations are in
`scratch/fvr_bar.py` and `scratch/fvr_ref.py`, recomputable.

DESIGN.md §E sequences M3 drafting after A5's L11M ceiling re-measure. That
re-measure has **not** run. This draft is written now because the team-lead
asked for it and because the two riders required real derivation work; §8
records what must land before launch.

---

## 1. Arms, baseline, endpoint

- **A (baseline) = champion-const.** The software mirror of what the chip
  plays. This is the baseline the guard replaces, per
  [[dr-mario-score-against-the-baseline-you-replace]]. **H16 is the TEACHER
  and the reference ceiling, never the baseline** — scoring against H16 would
  measure a different question and would be the error that killed a signed-off
  arm for EUR 0.
- **B (candidate) = champion-const + the frozen distilled guard.** Guard
  constants hash-pinned in the runtime manifest; both arms fork-free.
- ~~**PRIMARY endpoint**: failure (topout | stall) rate on **L20 honest-drlulu**,~~
  **⚠ DEMOTED TO SECONDARY 2026-08-29 — it is a DEATH property and R81 says the
  software rig's death class is not silicon's. See §S1.1 at the end of this file.**
  Original text retained:  failure (topout | stall) rate on **L20 honest-drlulu**,
  paired seeds, **McNemar exact one-sided; GO iff p < 0.05 AND d < 0.**
  L20 keeps comparability with H16's own registration and every banked
  reference number.
- No autopromote. Verdict counts by **direct file count**, never by a printed
  prefix (the H16 verdict-night rule).

## 2. Power and N — effect chosen first, N follows (R45/R47)

ψ prior 0.08 from H16's realized 7% discordance; the guard's dose runs hotter.
MDE quoted at **80% power = 2.8·SE**, not 1.96·SE — the error A5's own sizing
made and that this lane has now paid for twice.

| MDE @80% | N pairs | note |
|---|---|---|
| −1.34pp (50% of H16's effect) | ~3,500 | minimum honest run |
| **−1.09pp** | **~6,000** | **recommended** |
| −1.00pp | ~7,900 | seed-space heavy |

Achieved MDE is recomputed from realized discordance and **travels with the
verdict**. ⚠ **N is an owner-visible seed-space decision** — only ~13,781
streams remain free and the recommended N consumes a large share. The block is
registered at launch via `tools/seed_registry.py`, never before.

**Futility interims**: wired IN the runner, **recurring** at n=1,500 / 3,000
(never one-shot — R55), greppable stat+decision line, able to stop the unit.
Futility-only: there is **no efficacy stopping rule**, so a CI excluding zero
at an interim is not a GO.

## 3. RIDER (a) — THE FALSE-VETO CEILING, STATED NUMERICALLY

**Definition.** A *false veto* is the guard overriding at a state the teacher
itself calls non-danger: `champ_s2 >= 5` (the champion's own pick survives ≥5
of 6 confirm forks). **H16 has FVR = 0 on this population by construction** —
its rule requires `champ_s2 <= 3` — so every false veto is pure distillation
error, not inherited from the teacher.

**FVR = (# non-danger states where the guard overrides) / (# non-danger
states)**, measured on the **held-out** M1 bank, reported with a seed-clustered
CI.

**Derivation of the bar (reference data only — no fitted guard involved).**
The cost of a false veto was measured directly: at each non-danger state,
force a veto to the deployed fallback (best non-champion candidate by the
champion's own value ordering) and read the realized eval-half survival loss.

| L20 non-danger reference (n = 2,914) | |
|---|---|
| harm per forced veto | **−0.0491** eval-half surv pts (0–3 scale) |
| forced vetoes costing **nothing** | **89.4%** |
| fully saturated states (all candidates identical) | 49.9% |

(L11M, n=1,772: harm −0.0277, 93.6% cost nothing, 65.7% saturated. **False
vetoes are cheap because survival saturates off the danger set** — the same
saturation finding that makes H16 coherent, now working in the guard's favour.)

Net per-ply survival effect = `d·capture − nd·FVR·harm`, with the population
fractions `d = 0.0984`, `nd = 0.8124` measured on the same bank:

| capture | break-even FVR |
|---|---|
| at the signed GO bar (0.129) | **31.8%** |
| at the KILL line (0.099) | 24.4% |
| at today's point estimate (0.0645) | 15.9% |

> ### **CEILING: FVR ≤ 0.106 (10.6%) on held-out non-danger states.**
> Derived as the FVR at which the guard still keeps **≥ 2/3 of its gain** at
> the signed GO bar (break-even 31.8% × 1/3). Stated before any guard exists.

Two-sided reporting (R53): the break-even is reported alongside, so a reader
can see both that the ceiling has 3× margin and that a guard near break-even
would be net-useless rather than merely imperfect. **A guard that clears the
M2 GO bar but exceeds FVR 10.6% is NOT promoted** — it is reported as
"captures the verdict, cannot be deployed at this operating point", and the
operating point is re-tuned on TRAIN only and re-scored once.

⚠ **Scope of this bar (R24 — state what the check does not cover):** it is a
*survival* accounting. It does **not** price tempo/progress cost, and 49.9% of
its population is saturated on survival while progress is non-saturating. The
quantity that actually gates promotion is the §1 primary endpoint plus the §5
clean guard rider; FVR is the *pre-registered exposure ceiling*, not a
substitute for either.

## 4. RIDER (b) — g's OWN CONTRIBUTION TO SILICON CATCH ⚠ THIS IS NEARLY BINDING

M0's gate was "the trigger catches ≥ 2/3 of the silicon death class". The
deployed object is the **composite trigger × g**, so the catch requirement
must bind on the composite and g needs its own measured gate, never an
assumption riding on E-M1a's 63/63.

```
composite catch = trigger catch × P(g fires | death state)
wide12 raw catch on the M0 silicon corpus = 21/31 = 0.677   (CI [0.50, 0.81])
M0 gate                                   = 0.667
⇒ g must fire on ≥ 0.667/0.677 = 98.4% of the death states the trigger catches
⇒ headroom = 0.33 of 31 corpus deaths — effectively ZERO
```

**⚠ FLAGGED FOR DECISION, NOT SLID.** Applying M0's own 2/3 bar to the
composite leaves g essentially no room to miss a single death state. Three
honest dispositions, and the choice is the team-lead's:

1. **Recall-first operating point.** Tune g's threshold for near-total recall
   on the death class and spend the resulting false positives against the §3
   FVR budget. Coherent *only if* the measured FVR at that threshold still
   clears 10.6% — this is a measurable question, answered on the bank, before
   any M3 game is played.
2. **Re-derive the composite bar explicitly**, acknowledging that 2/3 was
   calibrated for a trigger alone and that the corpus CI is [0.50, 0.81] —
   i.e. the raw trigger's own margin over the bar is not statistically real.
   A registration amendment with its own reference derivation. **Not a slide.**
3. **Accept a mechanism gap**: report composite catch honestly and let the §1
   primary decide, with the silicon claim explicitly withheld.

My recommendation is **1, with 2 held in reserve** — but I am not choosing it
unilaterally, because option 2 changes a bar.

## 5. Guard rider (clean play) and the mutant sheet

- **GUARD**: 1,000 clean L11 pairs. **Trip iff d > +1.0pp or 95% LB > 0 ⇒
  NO PROMOTION.** Activity counters ship with every number (R26): override
  count on the pressured sheet must be > 0 (a null A/B is uninformative unless
  the treatment is proven active — R26), and the clean-play override *rate* is
  the number quoted, not the failure comparison, since with ~0 failures in
  both arms the statistical half has no power (the H16 guard-arm lesson).
- **Mutants, all green before e1**: `m-neverfire` ⇒ bit-identity with arm A
  **plus a liveness check** · `m-ident` · `m-swap` · **dose-matched
  label-shuffle guard at the matched realized override rate must NOT read GO**
  · R51/52 explicit + counted degeneracy filter · R53 two-sided plausibility
  bands on every gate statistic · at-cap fraction **per arm** as a primary
  diagnostic with a length-matched sensitivity arm (differential censoring).
- **Verdict script is an instrument**: driven by synthetic tables on both sides
  of every threshold, including one built against each banned amendment, and
  shown to stay **silent** on the benign states, before real data exists
  (R21/R28-corollary). The A5 battery `test_fit2_gates.py` is the template.

## 6. Spawn-plug suite (pre-registered mechanism secondary, design-gate only)

The 2 owner-match death boards + loss-corpus competitive losses + pop-A
pre-death states. The guard must veto the fatal placement on a pre-registered
fraction, **and** a matched healthy-tall control set must show false-veto below
§3's bound — the half that can fail. Passing never substitutes for the primary;
**failing it while the primary passes is a reportable mechanism gap**, not a
quiet footnote.

## 7. Secondary (silicon-facing, reported with honest power, NOT gated)

600 L11-MED pressured pairs — the regime the chip actually dies in. Reported
with its achieved MDE. ⚠ Its interpretation depends on A5's L11M ceiling
re-measure (§8).

## 8. WHAT MUST CLOSE BEFORE THIS IS LAUNCHABLE

1. **M2 must return a GO.** A KILL or a BETWEEN does not license M3 — the
   off-policy screen can only kill, never promote, and a BETWEEN at the
   enlarged n is a pre-registered STOP, not a licence.
2. **A5's L11M ceiling re-measure** (DESIGN.md §E sequencing rule). If L11M's
   ceiling stays at zero, §7's secondary is measuring a regime where the
   teacher's verdict is not distillable at this dose, and that must be said in
   the registration rather than discovered in the readout.
3. ~~The §4 disposition~~ — **CLOSED 2026-08-28: DECOMPOSE. See the ruling section at the end of this document.**
4. **Seed block**: registry-checked and registered at launch, with N as an
   explicit owner decision (§2).
5. **The fitted guard frozen and hash-pinned**, with its FVR measured on
   held-out data and reported against §3 **before** any game is played.

---

**Nothing in this document has been launched. No seeds are claimed. No bar
signed off elsewhere has been changed here; §4 names a bar that may need
re-derivation and explicitly refuses to move it unilaterally.**

---

# APPENDED CORRECTION — 2026-08-28, §4 rider (b). Nothing launched.

**§4's arithmetic was wrong and its conclusion is superseded.** Appended, not
edited: the document is evidence of what was believed when (R25).

**The error.** §4 read "g must fire on ≥98.4% of the death states the trigger
catches". **98.4% is a per-LOSS quantity, not per-state** — M0's catch is
*per-loss ANY-fire*, so the guard gets several chances per loss. The M0 corpus
banks **32 fired boards across 21 caught losses = 1.52 chances/loss**, which
converts the 98.4% per-loss requirement to a **per-state action rate of 93.4%**.

**The finding this exposes — the gate would reject the teacher.** Measured on
the M1 bank, **H16 overrides on 153/353 = 43.3% of L20 danger states**, and
even at `champ_s2 = 0` (the champion's pick dies in all six forks) it stands
**63.6%** of the time — because its rule requires `best_s2 − champ_s2 ≥ 3`,
i.e. a materially better alternative must exist. Standing on a lost board is
correct behaviour, not a miss. Therefore:

```
g == H16 exactly       -> per-state action 0.433
P(acts >=once/loss, corpus cadence k=1.52) = 0.579
composite corpus catch = 0.677 x 0.579     = 0.392   vs the 0.667 bar -> FAILS
```

**A guard reproducing the promoted champion bit-for-bit fails the gate**, which
would demand g be **2.2x more aggressive than the object it distills**.

**Why: the gate reads the instrument's cadence, not the guard.**

| cadence | chances/loss | P(teacher-perfect g acts) | composite |
|---|---|---|---|
| M0 corpus (20.4 s samples) | 1.52 | 0.579 | **0.392** |
| deployment, conservative | 8 | 0.989 | 0.670 |
| deployment (~20 fired plies) | 20 | 1.000 | 0.677 |

At deployment cadence a teacher-perfect g recovers the trigger's own catch and
**passes**. ⇒ **The M0 corpus structurally cannot measure this quantity.** Two
of our rules at once: R62 (2/3 was derived for a *static trigger's per-loss
any-fire on 20.4 s samples*; the composite is a *per-ply gated action*) and
"a counter's WINDOW is part of its definition". M0's own caveat 3 already
scoped its gate to the trigger — *"Catch != save … that is M2/M3's question"*.
Rider (b) extended a trigger gate onto an action quantity; the extension is
the entire bind.

**RECOMMENDATION (supersedes §4's three options): DECOMPOSE, don't compose.**
1. Keep M0's 2/3 gate on the **trigger**, where it was derived and is
   measurable (provisionally passed at 21/31).
2. Give **g its own bar on the ACTION question**, derived on reference data for
   the statistic actually computed: g's recall against **the teacher's own
   overrides** on held-out danger states. The teacher's 43.3% is the reference,
   not a target to exceed.
3. **REPORT** the composite with its cadence stated; **do not gate on it**.
4. Keep the **spawn-plug suite (§6)** as the mechanism check, where "did it
   refuse the fatal placement" is answerable per-placement.

⚠ Standing context: the trigger's own pass is knife-edge — **21/31, 95% CI
[50%, 81%], spanning the bar** ("CONSISTENT with ≥2/3, not established").
The composite was being asked to clear a bar its own input clears by one loss.

**AWAITING TEAM-LEAD RULING. This is a design change, not a threshold change,
which is why the lane is not making it.**

---

# §4.R2 — THE ACTION BAR: RECIPE AND SPLIT, PRE-COMMITTED TOGETHER

Team-lead ruling 2026-08-28. The **method** is registered here; the **number**
is computed once on the enlarged bank before the fit runs. The split is
pre-committed in the same sentence as the recipe so the two cannot drift apart:

> **`g`'s action bar is `floor + 0.30 × (ceiling − floor)` on the statistic
> `recall = P(g fires | the TEACHER fires)` over danger states — with the
> ceiling, the floor and therefore the bar DERIVED ON THE TRAIN SPLIT, and the
> guard JUDGED ON THE HELD-OUT SPLIT.**

Definitions, fixed now:
- **target** ("the teacher fires") = the half-scaled promoted rule on the
  **eval** half `s2[3:6]`; **predictor** = the same rule on the **dec** half
  `s2[0:3]`. Predictor and target never share a fork.
- **CEILING** = the tribunal predicting *itself* across those independent
  halves. **FLOOR** = the same predictor with dec-half sums permuted across
  candidates within state, 20 draws.
- **Precision and dose are reported beside recall, always** — a recall bar
  alone is gameable by an always-fire decider (R53).
- Producer: `scratch/m3_action_instruments.py`.

**Why the split had to be pinned now, not later.** Today's candidate bars at
0.30 of headroom are **train 0.2581 / held 0.1763 / full 0.2422** — a ~46%
spread that is pure researcher choice. Deferring the *number* is correct
(the floor is population-dependent and the bank is still growing); deferring
the *split* would have handed back everything the deferral buys. TRAIN is also
the more conservative of the two live options and keeps the bar structurally
independent of the evaluation it gates.

### ★★★ Context every downstream number must be read against (R72)

> **You cannot distil past the teacher's own self-agreement, and H16 reproduces
> only 36.7% of its own verdicts across independent fork halves** (precision
> 0.377, against a dose-matched shuffle floor of 0.2115 ± 0.0314).

Read every agreement figure in this registration against **0.37, not 1.0**.
This also retro-justifies the §4 DECOMPOSE ruling twice over: a gate demanding
**93.4%** action from a student of a **37%-self-consistent** teacher was
unreachable **by construction**, not by difficulty.

---

# §7 REVISED — THE REGIME-TRANSFER QUESTION IS PART OF THE REGISTRATION, NOT A FOLLOW-UP

**⚠⚠ THE CHIP PLAYS L11-MED. THIS GUARD IS DISTILLED AT L20.** A GO at L20 is
therefore **not** a licence to ship — it crosses exactly the regime boundary
that two independent instruments now say is hostile, and it is the same shape
as M0's finding that H16's *trigger* does not transfer to the silicon death
regime (dsh≥13 catching only 9/31 there).

**Program finding, on two independent statistics** (both on banked L11M data):

| statistic | ceiling | floor | headroom |
|---|---|---|---|
| capture (M2 instruments) | −0.036 | +0.021 | **−0.057** |
| action recall (§4.R2) | 0.125 | 0.1875 | **−0.0625** |

**In both, the ceiling sits BELOW its own floor.** Two statistics built on
different halves of the label, agreeing, is what promotes this from a small-n
suspicion to a finding. The running A5 L11M arm may still move it and is
reported honestly either way — but the deployment consequence is written down
**now**, before any GO exists to create pressure on it:

> **REGISTERED CONSEQUENCE: if PHASE 1 returns a GO at L20, the next question
> is NOT "ship it" — it is "does it transfer to the regime the silicon
> actually plays". No silicon claim is licensed by an L20 GO alone.** M3's §7
> L11-MED secondary is the first evidence on that question and is reported
> with its achieved power; it does not settle it.

⚠ And if the L11M ceiling stays below its floor at the enlarged n, the honest
statement is about **the teacher, not the student**: *the teacher's own verdict
does not self-transfer at L11M at this dose*, which means there is no target to
distil there — a fact about H16 and the label budget, not a failure of `g`.

---

# ⚠⚠ §7 SUPERSEDED — 2026-08-29. Two corrections. Appended, never edited (R25).

## S7.1 — THE "L11M NOT DISTILLABLE" PROGRAM FINDING IS RETRACTED

The §7 table above reported L11M as showing no headroom on two independent
statistics, with both ceilings below their own floors. **The completed A5 L11M
arm (63/63, 0 replay failures, format gate PASS on 105 shared states, 0
diverged) reverses the capture reading:**

| L11M danger states | n | ceiling | floor | headroom | verdict |
|---|---|---|---|---|---|
| base only (what §7 reported) | 55 | −0.036 | +0.021 | **−0.057** | no headroom |
| **pooled (base + A5)** | **531** | **+0.301** | +0.093 | **+0.209** | **USABLE** |

**+0.209 is comparable to L20's +0.200.** Decomposed, because n *and*
population both moved:

| population | n danger | headroom |
|---|---|---|
| base, **outside** the death window | 35 | −0.146 |
| base, **inside** the death window | 20 | +0.085 (no direction claimable) |
| backfill, death window | 491 | **+0.230** |

Inside the death window, base and backfill share the **sign**, and only n
separates "no direction" from "usable". The original n=55 verdict pooled 20
death-window states with 35 negative outside-window ones, and the outside
states dominated a tiny sample. ⇒ **At L11M the distillable signal is
concentrated in the death window — where a danger guard acts — and "not
distillable" was a composition artifact, not a property.**

## S7.2 — R81: THE M1 RIG IS THE SOFTWARE EXECUTOR

Confirmed two ways: **`oracle_arm.py` contains zero `exec_mode` occurrences** —
there is no firmware executor on the path any M1 game took — and viruses-left
at topout:

| | n | median | ≤3 viruses | ≥20 (silicon-like) |
|---|---|---|---|---|
| **L11M** (E-M1a's stratum) | 63 | **2** | **77.8%** | 7.9% |
| **L20** (this fit's stratum) | 254 | 9 | 28.7% | **35.0%** |
| real-firmware reference | | 35-36 | 1.7-2.6% | |
| software-lab reference | | 2 | 59.6% | |

> **E-M1a's 63/63 catch and its 191-ply median lead were validated on the
> LAST-VIRUS death class, not the midgame class the silicon exhibits.** Catch,
> lead, and E-M1b's false-fire rate all describe a population the deployed
> guard will not meet. This is stated in the verdict, not after it.

**M0 is unaffected** — it used the banked silicon loss corpus, not a lab rig.

⚠ **S7.1 INHERITS S7.2.** The L11M headroom is measured on those same 63 topout
games, 77.8% of which are last-virus deaths. It establishes distillability *in
the death window of software-executor last-virus deaths*; it does **not**
establish it for the midgame class the chip dies in, and must not be quoted as
if it did.

## S7.3 — THE REGISTERED CONSEQUENCE, NOW WITH TWO LEGS

> **An L20 GO licenses NO silicon claim, for two INDEPENDENT reasons:
> (a) the L20 → L11-MED regime gap (M0: H16's trigger catches only 9/31 of the
> silicon death class), and (b) the software-executor → real-firmware DEATH-CLASS
> gap (this section). Either alone would block the inference; both hold.**

## S7.4 — DEATH-CLASS HETEROGENEITY DIAGNOSTIC (reported, NEVER gating)

L20's topouts are genuinely mixed — **35.0% are silicon-like (≥20 viruses
left)**, so ~89 silicon-class deaths are already banked in the stratum this fit
uses. The verdict therefore reports capture split by the death class of the
game each danger state came from.

⚠ **This conditions on an outcome the deployed guard cannot observe** — the
exact defect removed from A5's design — so it is a **diagnostic that is reported
and never gates**, in the same posture as the composite catch (§4.R3). Its value
is that it is the cheapest available evidence on whether the software-rig
concern actually bites, on data already banked.

---

# ⚠⚠ §1/§2 SUPERSEDED — 2026-08-29. THE BASELINE RULING. Appended, never edited.

Team-lead ruling. **The two laws were never in conflict; they apply to
different halves of the rig.**

> The **COPROCESSOR mirrors the software champion's DECISION** — same
> evaluator, same ranking. So for any endpoint that is a property of
> **decisions**, champion-const-on-software is a faithful mirror and **is the
> baseline being replaced**.
> The **CART FIRMWARE, not the coprocessor, performs EXECUTION** — and R81
> says execution determines the death class. So for any endpoint that is a
> property of **outcomes reached through execution**, the software rig is
> measuring a different world.

## S1.1 — THE PRIMARY ENDPOINT CHANGES. THE BASELINE DOES NOT.

**Baseline stays champion-const-on-software** (§1 unchanged on that point).

**⚠ §1's primary endpoint — "failure (topout | stall) rate" — is a DEATH
property and is hereby DEMOTED TO SECONDARY**, carrying the executor caveat.
Under R81 the software rig's topouts are last-virus deaths while silicon dies
mid-game, so a failure-rate primary would have been measuring the wrong world
with full statistical ceremony.

> **NEW PRIMARY (decision-property, measured ON-POLICY at the guard's own
> firing set): the paired decision-quality endpoint —
> (i) RECALL against the teacher's own overrides ≥ the §4.R2 bar, AND
> (ii) FALSE-VETO RATE ≤ 0.106 (§3).**
> Two-sided by construction (R53): (i) alone is gameable by an always-fire
> decider, (ii) alone by a never-fire one. Both must hold.

★ **On-policy is what makes this worth running at all.** The substitution
closure established that *a decider chooses its own trigger set, so off-policy
capture is an upper bound*. M2 can therefore only kill. Measuring recall and
false-veto **on the guard's actual live firing set** is precisely the thing the
offline screen cannot deliver — so M3 still contributes the evidence only M3
can contribute, even with the outcome endpoint demoted.

## S1.2 — ⚠ THE HONEST COST OF THIS RULING, STATED PLAINLY

**M3 can no longer establish that the guard HELPS.** It can establish that the
guard *acts defensibly* — firing where the teacher fires, not firing where it
should not. Whether that translates into fewer deaths is an **outcome**
question, and this rig cannot answer it for the executor the chip uses.

Nobody should read a decision-endpoint GO as "the guard works". It means "the
guard's decisions survive on-policy scrutiny against the baseline it replaces".

## S1.3 — ⚠ §2's POWER TABLE IS VOID AS WRITTEN

§2 sized ~6,000 pairs for MDE −1.09pp on the **failure-rate** endpoint. That
endpoint is now **secondary**, so the table sizes a secondary and must not be
quoted as sizing the trial. The new primary is a **per-ply decision rate**, not
a per-game outcome, with different variance and clustering.

Per the §4.R2 precedent: **the METHOD is registered here, the NUMBERS are
computed on the enlarged bank before the run** — sizing for both halves,
stated as POWER at the true-effect values that matter, never as bare n.

## S1.4 — NARROW REAL-FIRMWARE TRANSFER CHECK (added, not a relocation)

A full A/B at real-firmware rates is unaffordable: **1,413 s median per game**
(endgame lane's measurement), so buying power at that rate would be the worst
spend in the program. This program's own pattern applies — cheap-and-wide for
the primary, expensive-and-narrow for transfer.

**Registered size: 30 games per arm.** It answers exactly one question: *does
the guard's veto behaviour differ between software-executor and real-firmware
games?*

| games/arm | core-h | wall @6w | MDE (80%) on a ~4% veto rate |
|---|---|---|---|
| 20 | 15.7 | 2.6 h | 2.24 pp |
| **30** | **23.6** | **3.9 h** | **1.83 pp (≈0.5× relative)** |
| 60 | 47.1 | 7.9 h | 1.29 pp |

> ⚠ **HONEST POWER: at 30/arm this sees only a LARGE difference — roughly a
> 46% relative change in veto rate or bigger. A null here is NOT evidence of
> transfer**; it is evidence against a gross difference only, and must be
> reported in those words. (Clustering by game is priced in at a design effect
> of 4.)

## S1.5 — ★ SAY THE QUIET PART: M3 IS A SCREEN, NOT THE FINAL WORD

**The deployment test is M4 on silicon.** M3 is the best affordable screen,
with a stated and measured transfer gap. Framing it as the verdict would be
indefensible, and with §7 now carrying **two independent transfer gaps** — the
L20→L11-MED regime gap and the software-executor→real-firmware death-class gap
— no reader should be able to.

**A GO in M3 licenses M4. It licenses nothing on silicon by itself.**
