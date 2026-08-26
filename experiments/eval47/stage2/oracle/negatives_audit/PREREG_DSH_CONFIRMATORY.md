# PRE-REGISTRATION — `d_spawn_h` as a SUBSTITUTE for H12's rollouts
**DRAFT for team-lead sign-off. NO COMPUTE SPENT.** Written 2026-08-26.

---

## 0. WHERE THIS COMES FROM, AND THE ONE THING IT MUST NOT REPEAT

The LUT arm returned **6.8% [5.1, 8.5]** — S3, function-class wall. In the same run, as a
**comparator**, `d_spawn_h` alone returned **30.0% [28.5, 31.6]**, clearing the bar the LUT missed.
That is a lead, not a result: it was never the registered arm.

**★ THE MIRAGE THIS DESIGN EXISTS TO AVOID.** Both the LUT's original 0.7220 AUC and its
+0.0105-over-`d_spawn_h` offline edge were measured **off-policy** — ranking candidates on a
trajectory somebody else generated. Blind and on-policy, the LUT collapsed and the sign of the
comparison **reversed**. The 30.0% figure is measured the *same off-policy way*: it scores
`d_spawn_h`'s ranking **at H12's tie plies, on H12's trajectory**. So it is the same species of
number that has now misled this program twice.

> **THE DISTINCTION THE DESIGN MUST MAKE, STATED PLAINLY:**
> **COMPARATOR** = at a tie H12 reached, would `d_spawn_h` have ranked the candidates as H12 did?
> The state distribution is **H12's**, one decision is scored, nothing compounds.
> **DECIDER** = `d_spawn_h` *makes* the choice, the game continues **from its move**, and the
> state distribution **diverges from H12's** thereafter. Errors compound, the tie population
> itself changes, and the endpoint is a played outcome rather than a ranking.
> **30% as a comparator does not imply 30% as a decider, and the LUT is the proof.**

## 1. TWO TIERS, AND ONLY ONE OF THEM ANSWERS THE QUESTION

### TIER 1 — off-policy REPLICATION (cheap, and NOT sufficient)
Repeat the exact registered statistic on **fresh streams**: does 30.0% replicate out of sample?
**Sized from the REALISED SE, not a prior:** d_spawn_h's CI half-width was 1.55pp at 1,665 seeds
⇒ **SE = 0.791pp**. For 90% power at 30% against the 20% floor, need SE ≤ 3.085pp ⇒
> **N = 110 seeds · ~16 core-h · ~1.4 h wall @12 · ~€0.34**

⚠ **A Tier-1 pass licenses NOTHING on its own.** It only rules out "the 30% was a fluke of one seed
block". Reporting Tier 1 as the answer would repeat the LUT's error exactly.

### TIER 2 — the PLAYED DECIDER arm (this is the question)
An arm identical to certified H12 except that **at gated exact ties it picks `argmin d_spawn_h`
instead of forking**. Paired against H12 on shared seeds, CRN. **No forks on the treatment side —
that is the entire point: it is what silicon could actually run.**
Endpoint: **dies-ahead**, McNemar, seed-clustered; clear-rate non-inferiority as co-primary guard.

**Sizing from the program's realised discordance (ψ = 452/3,000 = 15.07%), 90% power:**

| effect to detect | N pairs | core-h | wall @16 | € |
|---|---|---|---|---|
| **−1.43pp** (30% of H12's −4.78pp — the projection) | **7,743** | 1,161 | 72.6 h | **17.80** |
| −2.00pp | 3,958 | 594 | 37.1 h | 9.10 |
| −1.00pp | 15,832 | 2,375 | 148.4 h | 36.39 |

⚠ **Non-inferiority (d_spawn_h no worse than H12 by >0.5pp) needs ~63,000 pairs / ~9,500 core-h —
prohibitive. Do not frame it that way.**

**⇒ RECOMMENDATION: Tier 1 first (€0.34, 1.4 h). If it replicates, Tier 2 at N = 7,743 (~€18, ~3 days
wall at 16 cores).** Tier 2 is ~3.5× the cost of everything this lane has spent to date, which is
why it needs your sign-off rather than my judgement.

## 2. SEEDS — from the registry, not by hand

`seed_registry.py --suggest 2000` → free stream keys **8720..12231**.
> **REGISTERED: raw EVEN seeds 17440 step 2**, Tier 1 taking the first 110, Tier 2 the first 7,743
> (extending into the same free run; re-check before Tier 2 launches).
Startup assertion on **stream keys** (fold mod 65536, `>>1`), distinct-count == N, alias triple
excluded — the same gate that **failed as required** on the 80000 block.

⚠ **REGISTRY DEFECT FOUND, worth fixing before this run:** `--check 33000 1666 2` evaluates the
naive arithmetic range 33000..36330, which **includes 35208** (the alias, which my run skipped) and
**excludes 36332** (which my run used). The registry's consumed record is therefore off by one seed
at each end versus what was actually consumed. **Generation skips-then-extends; the checker does
not.** Small now, a future collision later.

## 3. WHAT CARRIES OVER UNCHANGED

**Control panel as the FIRST table** — H12's pick (must be +100%), oracle, champion, random (~0),
worst — on the final population; **if any lands off construction the treatment number is void.**
**Discriminating-ties predicate = "candidate labels not all identical"** (never `margin_sum > 0`,
which deletes the typical duplicate-board case). **Degenerate share reported as a count.**
**Recurring interim gate wired from the start** (not one-shot: rule 55), **two-sided plausibility
band** (stops on implied_N < 20 as well as > registered), **schema assertion per file on read**
(rule 54), per-seed atomic writes, resumable, producer-directory reads only.

## 4. VERDICT TABLE — Tier 2, every branch

| # | condition (dies-ahead, paired, seed-clustered) | verdict |
|---|---|---|
| **D1** | CI excludes 0 favourably **and** clear-rate guard passes | **SUBSTITUTION VIABLE AS A DECIDER.** Licenses a silicon-port feasibility study — nothing more. |
| **D2** | CI excludes 0 favourably, clear-rate guard **fails** | **churn-limited**; report as such, no promotion (the `vocab-wall-2` structural law). |
| **D3** | CI includes 0 | **NOT RESOLVED AT THIS n** — never "the substitution fails". |
| **D4** | CI excludes 0 **adversely** | **decider is HARMFUL**; the comparator/decider gap is the finding, and it closes the route. |

★ **FORBIDDEN PREDICTION:** the hypothesis (30% comparator ⇒ ~30% decider) **forbids the played arm
landing at or below zero effect while Tier 1 replicates at 30%.** If Tier 1 says 30% and Tier 2 says
zero, the hypothesis is falsified **and** we will have measured the comparator/decider gap directly
— which is worth more than the arm itself and should be reported as the headline.

## 5. WHAT EACH OUTCOME LICENSES
**D1** licenses a feasibility study, not a ship — proxies rule OUT, never IN.
**D4/D3** close the substitution route at the *decider* level and **redirect the cascade's middle
step**, which given the full chip is the more consequential half. **A negative here is reported as
loudly as a positive.**

## 6. COST DISCIPLINE
Fresh burst node, `/cloud` pattern: ledger row on create **and** delete, PROVISIONING.md pinned
venv, **bit-exactness gate re-run on the new CPU before any row counts**, byte-verified pull with
row counts matched **before** teardown, wasted-uptime kept as a distinct ledger line.

---

# AMENDMENT 1 — 2026-08-26, BEFORE ANY COMPUTE

## A1.0 WHY THIS AMENDMENT EXISTS
Team-lead asked one blocking question: **"which arms does the McNemar pair?"** — because
§1's power target (**−1.43pp = 30% of H12's −4.78pp**) is the expected effect of treatment
**vs CHAMPION**, while §1's text said *"Paired against H12"*. Forcing the −1.43pp to name its
comparison required checking what the **champion itself** scores on the capture scale. It does not
score zero. **The clarification exposed a sign error, not a labelling error.**

## A1.1 ★ THE ARMS, THE SIGN, AND WHICH COMPARISON OWNS THE EFFECT — as demanded

| | | |
|---|---|---|
| **CHAMP** | certified champion; at a gated exact tie it uses its own tiebreak | the baseline the treatment REPLACES |
| **TRT** | CHAMP, except at gated discriminating ties it plays `argmin d_spawn_h`. **No forks.** | the shippable arm |
| **H12** | certified champion + top-4 rollouts at the same gated ties | the target being substituted FOR |

**Sign convention: Δ = rate(TRT) − rate(CHAMP) on dies-ahead. Dies-ahead is a rate where LOWER IS
BETTER, so a NEGATIVE Δ means the treatment is BETTER.** H12's certified endpoint is
12.52% → 7.74% = **Δ = −4.78pp**, i.e. rate(H12) − rate(CHAMP).

> **PRIMARY = TRT vs CHAMP.** The −1.43pp belongs to **this** pair and to no other.
> **SECONDARY = TRT vs H12** (what the forks were worth). Under the old projection it is
> **+3.35pp**, treatment worse; it is NOT the pair the primary is powered for.
> **BLOCKING POSITIVE CONTROL = H12 vs CHAMP** on the same seed block, which must reproduce
> ≈ −4.78pp or the block is void rather than the treatment. Sized at **N = 665 seeds** (90% power)
> / 817 (95%) from ψ = 15.07%, p_favor = 0.6586 — which the machinery reproduces against the
> endpoint's own observed 896/1362 = 0.6579.

## A1.2 ★★★ AND THE ANSWER IS ALREADY IN THE DATA: TIER 2 IS DEAD PRE-COMPUTE

The §1 projection assumed `cap(DSH) = 30.0%` is an increment the treatment **adds** to the champion.
It is not. The registered control panel of the completed substitution run already contains the
baseline, and it was a **pre-committed** panel entry:

| picker | transfer | |
|---|---|---|
| H12's own pick | 100.0% | by construction |
| ORACLE | 115.8% | |
| **CHAMPION's own tiebreak** | **37.3%** | ← **the baseline TRT would replace** |
| **d_spawn_h** | **30.0%** | ← **BELOW the champion** |
| random | −1.2% | |

> ### `cap(DSH) − cap(CHAMP) = −7.3 points · 95% CI [−8.2, −6.3]` · seed-clustered, B=4000, n=1,665 seeds · **EXCLUDES ZERO ADVERSELY**

**Substituting `argmin d_spawn_h` for the champion's own tiebreak DESTROYS 7.3 points of H12's tie
value.** Under §1's own linear-transfer assumption this maps to

> ### projected dies-ahead **Δ = +0.55pp [+0.48, +0.63]** — treatment **WORSE** than the plain champion.

**The registered projection was −1.43pp (better). The sign is opposite.**

**Estimator validated before use:** the reconstruction reproduces **all six** registered panel
entries exactly (100.0 / 115.8 / 37.3 / −116.0 / 6.8 / 30.0) and reproduces the registered
forbidden-prediction contrast `cap(DSH) − cap(LUT) = +23.2% [+21.2, +25.2]` against its
registered [+21.2, +25.3]. Random recomputes as 0.0% vs the registered −1.2% because this uses the
expectation rather than one sampled draw — inside the registered CI [−2.8, +0.5].

## A1.3 THE MECHANISM, MEASURED — why a 30% comparator is a negative decider
Value-level joint table over all 41,063 discriminating ties (picks compared by the **progress label
they land**, never by slot index — §0.1's duplicate-slot hazard; slot-level and value-level are
reported side by side and they differ):

| | ties | share |
|---|---|---|
| A neither diverges from champion | 29,327 | 71.42% |
| B H12 flips, TRT does not (**value forgone**) | 7,471 | 18.19% |
| C both flip, same value (**value captured**) | 733 | 1.79% |
| D both flip, different value | 106 | 0.26% |
| **E TRT flips where H12 did NOT (UNPRICED)** | **3,426** | **8.34%** |

- TRT reproduces only **8.8%** of H12's 8,310 value-flips.
- **80.3% of TRT's own flips (category E) have no H12 precedent**, and they are harmful on the
  label: mean progress **−3.26**, worse **73.2%** of the time.
- TRT divergence dose is **51.3%** of H12's — the treatment does not merely rank worse, **it fires
  at a different and worse-chosen set of plies.**

**★ THE GENERAL LAW, which is the real product:** a comparator is scored on the target's trigger
set; a decider **chooses its own**. `d_spawn_h` was scored at H12's tie plies and never had to
decide *whether* to act. Given that choice it acts at 3,426 ties H12 deliberately left alone, and
loses more there than it gains everywhere else. **Scoring a substitute against the TARGET while
never scoring it against the BASELINE IT REPLACES is what manufactured the 30%.**

## A1.4 NO STRATUM RESCUES IT (in-sample; triage only, licenses nothing)
Registered margin strata, `cap(DSH) − cap(CHAMP)` in each: 0-3 (95.2% of value) **[−8.6, −6.5]** ·
3-6 [−5.7, +2.6] · 6-12 [−3.9, +9.9] · 12+ [−19.9, +0.0]. **Not one stratum's CI excludes zero
favourably**, and the three that include zero hold 4.8% of the value between them. A gated
"act-only-when-confident" descendant has **no support in the registered strata** and would need its
own held-out registration; in-sample best-of-4 climbs when the truth is flat.

## A1.5 REVISED STATUS OF EACH TIER

**~~TIER 2 — N = 7,743 pairs, ~€18, ~3 days.~~ WITHDRAWN. Do not spend the €18.** The arm it would
play is projected **worse than doing nothing**, from a pre-committed control in a blind confirmatory
run. Playing it would cost €18 and ~3 days to measure a harm we can already bound.
*(Kept visible: the sizing machinery itself was sound and is retained — it reproduces the registered
N=7,743 at ψ=15.07% to 0.4%, and it showed the borrowed ψ was the CONSERVATIVE end of
ψ ∈ [8.1%, 15.1%] — N is monotone increasing in ψ, so **N=7,743 was the worst case, not a lucky
guess**. The sizing was never the defect. The effect's sign was.)*

**TIER 1 — GO, UNCHANGED IN COST, SEEDS AND RUNNER; VERDICT RULE CORRECTED HERE BEFORE LAUNCH.**
§3 already required the control panel as the first table, so the run **already produces
`cap(CHAMP)`**. Only what it is scored against changes:

> **~~OLD verdict rule: does `cap(DSH) = 30.0%` replicate out of sample?~~** — superseded: replicating
> 30.0% would confirm a number that sits **below** the 37.3% baseline, and would read as good news.
>
> **★ NEW REGISTERED VERDICT RULE, two-sided, committed before the fresh block is generated:**
> primary statistic **`cap(DSH) − cap(CHAMP)`**, seed-clustered bootstrap B=4000, N=110 seeds.
> - **T1-a** CI excludes zero **adversely** → the pre-compute kill **REPLICATES on fresh streams**;
>   Tier 2 stays withdrawn and the substitution route closes at the decider level.
> - **T1-b** CI includes zero → **NOT RESOLVED AT n=110**; the 1,665-seed result still stands as the
>   better-powered estimate and Tier 2 stays withdrawn on it.
> - **T1-c** CI excludes zero **favourably** → the two blocks **disagree**; that is a block-level
>   defect, not a licence. Nothing is promoted; the disagreement is diagnosed first.
>
> Power check: at n=110 the SE inflates by √(1665/110) = 3.89×, giving ≈ [−11.0, −3.6] around
> −7.3 — **n=110 is sufficient to replicate the kill**, which is why the block is not resized.
> **Full panel reported first, all five construction controls; if any lands off construction the
> treatment number is void.**

---

# TIER 1 EXECUTED — RESULT, 2026-08-26

**T1-a. `cap(DSH) − cap(CHAMP) = −8.3 pts [−11.9, −4.7]`**, 110/110 seeds, all five construction
controls landing, gates passed before any row counted. cap(DSH) = 29.9%, cap(CHAMP) = 38.2%.
The registered kill **replicates on fresh streams**; reference block was −7.3 [−8.2, −6.3].

⚠ **The superseded rule would have PASSED on the same data**: cap(DSH) replicated at 29.9% against
the old 30.0% target. **Same number, opposite meaning, because the baseline changed.** Recorded here
as the justification for having re-registered the verdict rule before the block existed.

**Tier 2 remains WITHDRAWN.** €18 unspent. Tier 1 cost **€0.74** (incl. a 57-min G-IDENTITY gate).
