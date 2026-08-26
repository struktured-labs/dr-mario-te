# PRE-REGISTRATION — Can a static LUT SUBSTITUTE for H12's rollouts at its own trigger plies?
**Written 2026-08-25 BEFORE generating any flip record. HELD FOR TEAM-LEAD GO.**
Confirmatory. The records this scores against **do not exist yet**, which is what makes it blind.

---

## 0. WHY THIS IS THE CASCADE'S MIDDLE STEP

Owner's frame: *"distil from supergod → coproc → nes only."* The coproc step now has a hard
constraint: **the chip is full** (a +231 ALM write-only tap broke timing on a clock it does not
touch). **H12 and H16 are fork-based and can never be ported.** A LUT-shaped substitute can —
288 int12 entries, 8 BRAM reads + 8 adds, ~18 of 250 cycles, zero DSP, zero new board passes.
**So this is the only known route to rollout-quality decisions on silicon.**

## 0.1 ⚠ TWO REPRESENTATIONS OF THE DUPLICATE-PLACEMENT HAZARD — DO NOT MIX THE NUMBERS

| | unit | duplicate collapse |
|---|---|---|
| **labels-146 bank** | already **board-dedup'd**: 27,000 distinct boards, median 22/decision | mean **1.190 slots per board** |
| **H12 flip records** | **SLOT-level**: `cands` is always 4 slots | **88.7%** of tie sets carry only **2 distinct outcome vectors** ⇒ ~2 distinct boards |

**Sample sizes in this document are stated in DISTINCT BOARDS or in FLIPS, never in slots.**

## 1. HYPOTHESIS

**H_sub:** at H12's own trigger plies, a static additive LUT over the 8 shipped features selects the
same candidate H12's forks select, materially more often than chance and than the trivial baselines.

**Established, and not re-litigated here** (from certified-H12 provenance, n=3,005 flips):
H12's choice is the **progress**-argmax in **100.0%** of flips; survival is flat across tied
candidates in **90.8%**. H12 keys on progress. The Stage-2 LUT was trained on **survival** — a
target mismatch, which is why this arm re-fits on `prog`.

## 2. DESIGN

**Generate fresh certified-H12 games** (`h12_true_m0.5_e0.0`, tie_margin 0.5, trigger_eps 0.0),
provenance ON, L20 lulu home regime, on **seeds disjoint from the labels-146 bank, from every
Stage-2 corpus seed, and from the H14 endpoint block** — asserted at startup, not commented.
For every flip ply record H12's `trt_action`, the champion's `base_action`, `cands`, `labels`,
`margin_sum`, **and the post-placement board for each candidate** (see §2.1).
Score the LUT (fit on `prog`, on the labels-146 bank, train units only) over the same `cands`.

### 2.1 ⚠ THE ONE ENGINEERING PROBLEM, AND ITS GATE
`h12_arm.py` is **SEALED** and its `flip_log` does not store boards. I will **not modify it**.
Instead: a subclass that adds board capture and **changes no decision**. This is only admissible
behind a gate:

> **G-IDENTITY (blocking):** the instrumented arm must produce **byte-identical action sequences**
> to sealed H12 on ≥20 gate seeds, and a deliberately mutated copy (e.g. margin gate off) **must
> fail** that check. A gate that has only ever passed is not a gate.

## 3. ★ PRE-COMMITTED BASELINES — the result is worthless without all three

| baseline | expected | why it must be pre-committed |
|---|---|---|
| **binary chance** | **50%** | 88.7% of tie sets are 2 distinct boards ⇒ the real decision is binary |
| **always-index-2** | **~90.6%** | H12 picks `champ_rank_chosen==2` in 2,724/3,005 flips. **A rule that learns NOTHING scores ~90% at slot level.** Any headline agreement must be read against THIS, not against 50%. |
| **permuted-label LUT** | ~50% | the fit machinery is not leaking |

**Report agreement over DISTINCT BOARDS, not slots**, which removes the index-2 artefact at source;
the slot-level number is reported beside it only to show the artefact.

## 4. PRIMARY STATISTIC AND THE PRE-REGISTERED EXPECTED EFFECT

**PRIMARY: value transfer** — fraction of H12's own achieved tie-progress-gain that the LUT's pick
captures, seed-clustered bootstrap. (Agreement rate is secondary; transfer is what maps to the
endpoint, and concordance is demonstrably **not** linear in value.)

> **⚠⚠ AMENDMENT 1 (2026-08-25, BEFORE any flip record was generated — no confirmatory data
> exists yet). The original expected effect is kept visible and struck.**
>
> ~~PRE-REGISTERED EXPECTED EFFECT: transfer = 30% of H12, projecting −1.45pp. Derived from
> LUT transfer 22.8% of oracle; H12's own achieved transfer 73.4%; 22.8/73.4 = 31.0%
> × −4.78pp = −1.48pp.~~
>
> **REASON FOR AMENDMENT — a methodological error, not a result-driven adjustment.** Both figures
> were computed IN-SAMPLE: H12 chose using 5 of the bank's 8 forks and was then scored on all 8,
> including the 5 it chose with. That is the winner's-curse inflation this project already has a
> standing rule about (*"never quote a best-of-N gain without either a split-sample estimator or a
> permutation null"*). The LUT uses no forks, so its score was unbiased; **H12's was not**, and the
> ratio was therefore wrong in the LUT's disfavour.
>
> **Re-measured apples-to-apples, split-sample (decide on 5 forks, score on the other 3), n=259
> held-out tie groups:** H12 transfer **39.1%** (sd 6.0) · LUT transfer **18.8%** (sd 5.6).
>
> **★ AMENDED PRE-REGISTERED EXPECTED EFFECT: transfer = 48% of H12, projecting −2.29pp on
> dies-ahead.** The result is scored against this number, committed in advance of any flip record.
>
> ⚠ **Read the RATIO, not the levels.** The split-sample denominator (max over 3 eval forks minus
> their mean) is upward-biased, which deflates BOTH transfers; the ratio is far more robust than
> either. And the same in-sample/split-sample gap applies to §5's per-margin table, whose absolute
> numbers are in-sample — **its stratum ORDERING stands, its levels do not.**

## 5. MARGIN STRATIFICATION (mandatory, not optional)

**25.1% of H12's flips sit exactly at its acceptance threshold `margin_sum == 3`** — near-indifferent,
cheap to get wrong. Value concentrates at high margin: offline, the `margin ≥ 12` stratum carries
**41.9%** of all value and the LUT captured **44.6%** of it, while `margin 6-12` (28.4% of value)
captured **1.7%**. **Report transfer per margin stratum {0-3, 3-6, 6-12, 12+} and pooled. A pooled
number alone is not a result.**

## 6. VERDICT TABLE — every branch exercised

| # | condition (transfer, held-out, seed-clustered) | verdict |
|---|---|---|
| **S1** | CI lower bound **> 20%** of H12 | **SUBSTITUTION VIABLE.** Licenses ONE endpoint rollout arm at N=12,000 (MDE 0.99pp). |
| **S2** | CI includes 30% but lower bound ≤ 20% | **CONSISTENT WITH THE PROJECTION, UNDERPOWERED TO ACT.** Report as such; do not fund the endpoint on it. |
| **S3** | CI upper bound **< 15%** of H12 | **★ FUNCTION-CLASS WALL, HONESTLY LOCATED.** See §7. |
| **S4** | agreement ≤ the always-index-2 baseline | **INSTRUMENT/ARTEFACT verdict** — the LUT is not beating a rule that learns nothing. Report, do not interpret. |
| **VOID** | G-IDENTITY fails · mutant survives · <350 flips · permuted null outside 45-55% | fix, re-register, re-run |

## 7. WHAT EACH OUTCOME LICENSES — including the negative, per team-lead

**S1 licenses:** funding one endpoint rollout arm. **Not** a ship, **not** a silicon port — per
`dr-mario-label-budget-rules`, proxies rule OUT, never rule IN, and H15 is the standing proof that
offline power can survive while integration fails at every dose.

**★ S3 — the negative — licenses something genuinely valuable and should be reported as loudly as a
win:** *"H12's tie-resolution is not recoverable by a static additive delta over these 8 features."*
That closes the **distil-the-rollout-arm route at the FUNCTION-CLASS level** rather than leaving it a
maybe. Given the chip is full and rollout arms cannot be ported, **that redirects the whole cascade
rather than just this experiment** — it tells the owner the coproc step needs a richer function class,
more features, or a different target, and stops anyone re-attempting a LUT in four weeks.


## 10b. ⚠⚠ AMENDMENT 5 — DEGENERATE TIES ARE EXCLUDED FROM THE PRIMARY

**36.1% of tie plies are DEGENERATE** — every candidate carries an identical label
(measured: 52 of 144 on the smoke; example `labels = [[5,55],[5,55],[5,55],[5,55]]`,
`margin_sum = 0`). **On such a ply the LUT, the champion, H12, a random tie-break and the
worst move all score identically, necessarily.** They carry zero information about the question.

⇒ **Including them DILUTES the effect toward whatever value the code assigns them.** At the
measured 36% rate, a zero-transfer treatment shrinks the estimate by ≈**0.64×**: a true 30%
transfer would read ≈19%, **below the pre-registered 27% floor**, and the design would report
**NOT RESOLVED for a substitution that genuinely worked.** That is a live way to lose the
experiment and it is invisible in any summary statistic.

**REGISTERED:**
1. **The primary runs over DISCRIMINATING ties only** — plies where the candidate labels are not
   all identical. This is the same definition used by the earlier refit ("319 **discriminative**
   decisions"), kept consistent deliberately.
2. **Degenerate ties are reported as a COUNT, never folded into the denominator.** A reader sees
   23/36, not 36.
3. **The interim SE is computed on the discriminating subset**, otherwise it measures the variance
   of a diluted quantity and the implied N is wrong in the optimistic direction.
**Implemented:** `interim_gate.py` excludes `prog.max() <= prog.mean()` and now reports
`ties=… discriminating=… degenerate=… (…%)` on its greppable line.

### ⚠⚠ DO NOT RE-DERIVE THIS AS `margin_sum > 0` — it deletes the TYPICAL case

`margin_sum = best − second`. When the **best board occupies two slots** — the duplicate-slot
collapse — the top two entries are the same board, so `margin_sum = 0` **even though the ply is
fully discriminating.** Counterexample from the live run:

```
seed 33002  ply 18  is_flip 0   base_action 16  trt_action 16
labels  [[5,51], [5,51], [5,42], [5,42]]      <-- TWO distinct progress values
margin_sum 0
```
Choosing the 42-group over the 51-group is measurably wrong, and this is a **discriminating KEEP**
— the record type the estimand rests on. At the measured **88.7%** two-distinct-outcomes rate,
`margin_sum > 0` would exclude the majority of informative plies. **The test is "candidate labels
are not all identical."**

★ **CROSS-REFERENCE — this is [[dr-mario-duplicate-placements-two-lottery-tickets]] from the other
end.** That memory records the same underlying fact as a *selection* effect: a double capsule's
placement draws the max of two tie-break jitter values while a unique placement draws one, *"which
is exactly why de-duplicating CANDIDATES is not board-neutral."* Here the same duplication shows up
as a *margin* artefact. **A reader hitting duplicate slots in either context should land on both.**

★ **AND THE SECOND-ORDER RULE, which outlives this arm:** the interim's SE was *accidentally*
correct — `prog.max() <= prog.mean()` already skipped degenerates before anyone noticed. **That was
not good enough.** An implicit filter is one refactor away from silently changing the estimand, and
no reader of the output could tell it had been applied. **A filter that matters to the estimand must
be EXPLICIT and REPORTED even when the implicit behaviour is already right.**

## 10c. THE VARIANCE PROXY ERRS IN THE SAFE DIRECTION — stated precisely

The interim's variance proxy is the transfer statistic under a **blind random pick**: same
normalisation and denominator as the primary, no ranker scored, so the interim stays blind.

**Why that is conservative.** Per-seed transfer is bounded on [−1, +1]. For a variable on [m, M]
with mean µ, Bhatia-Davis gives `Var ≤ (M − µ)(µ − m)` = **1 − µ²** here. That cap is **maximised
at µ = 0 — exactly where a blind random pick sits** (measured: −0.0066). At a true transfer of
0.30 the cap is 0.91.

⇒ **`implied_N` from this proxy is an upper bound, not a point estimate**, so a reduction taken on
it is conservative.

⚠ **Stated at its true strength, which is weaker than "the variance is lower":** the bound on
variance shrinks as |µ| grows; that is not a proof that the *actual* variance of a real ranker is
smaller, only that it **cannot exceed a smaller cap**. The proxy is measured at the point where
variance *can* be largest. Conservative under the bound — not proven conservative pointwise.

## 11. ⚠ BOUNDARY / CENSORING ANALYSIS PLAN — pre-registered, not discovered

`max_pills = 400`, matching the reference. **This matches the reference's truncation; it does not
remove truncation** — all 338 reference stalls sit at exactly 400 plies. The production run
therefore inherits a 400-ply scope limit, and with a measured **1.57x late-flip hazard in clearing
games** that is a real scope statement, not a formality.

**Why this is a threat and not a nicety:** a game's `res` is the OBSERVED outcome. Capping does not
merely thin the sample of late decisions — **it reclassifies late-clearing games as stalls, censoring
the LABEL.** Clear rate is a co-primary here, so the cap can move the headline number itself. And
because the substitution arm exists precisely to CHANGE decisions, it changes game lengths, so the
two arms can be censored at DIFFERENT rates — a component of the measured difference would then be
pure boundary artifact. Same disease as [[dr-mario-champ-loss-autopsy]], where 10 of 29 spurious
champion losses were boundary artifacts.

**MEASURED IN ADVANCE on the banked paired H14 data (n=1,816 pairs, cap 400):**
at-cap **base 9.47% vs trt 9.20%, Δ −0.28pp against a McNemar SE of 0.56pp** — **no evidence of net
differential censoring**. ⚠ But **105 pairs (5.8%) are boundary-discordant** (exactly one arm at cap),
which is **5.5x the size of the clear-rate effect** (+1.05pp) in that same data. **The cancellation is
empirical, not structural** — a different arm can break the symmetry, so it must be re-checked, never
assumed.

**REQUIRED, as primary diagnostics rather than footnotes:**
1. **At-cap fraction PER ARM**, reported beside the primary. If the arms differ materially, the
   clear-rate comparison is confounded and must be reported as confounded.
2. **Boundary-discordant pair count** (exactly one arm at cap), against the effect size.
3. **Two pre-specified sensitivity analyses:** (a) treat at-cap games as their own category, neither
   clear nor stall; (b) a length-matched subset. **If sign and magnitude survive both, the finding is
   robust to the boundary; if not, we learned it before publishing.**
4. **The reference is censored too.** Its −4.78pp was produced under the same 400 cap. Matching at 400
   buys **comparability, not correctness**, and the write-up says so in those words.

## 8. ⚠ NAMED RISK — THE LINEARITY ASSUMPTION IS THE FIRST SUSPECT

The −1.45pp projection assumes H12's −4.78pp scales **linearly** with the fraction of tie-progress-gain
captured. **This is an assumption, not a measurement.** Registered in advance: **if the measured
transfer lands far from 30% in EITHER direction, or if a later endpoint disagrees with the projection,
the linearity assumption is the first thing to suspect** — not the LUT, not the labels. Saying so
before the data is the point.

**⚠⚠ THIRD NAMED RISK — AMENDMENT 2 (2026-08-25, still before any flip record). HORIZON MISMATCH,
caveat only: the expected-effect NUMBER is NOT changed, because chasing it further would be
fitting a prior to my own diagnostics.**
**Certified H12 forks at `H=15`. The labels-146 bank's forks are `H=25`** (verified: bank `H` is
25 for all 1,344 rows; H12's registered config is `fork_samples=5 H=15`). So every "simulated H12"
figure I have produced — 39.1% transfer, the 48% ratio, the −2.29pp projection — ranks **H=25**
progress, which is **not the quantity H12 optimises.**
· The **RATIO is still like-for-like** (both rankers scored against the same H=25 target), so
  "who ranks long-horizon progress better" is a sound comparison.
· The **mapping onto H12's measured −4.78pp is not**: it now carries three stacked assumptions —
  linearity (§8), the split-sample denominator, and this horizon substitution.
⇒ **Treat −2.29pp as a ROUGH PRIOR, not a precise commitment.** A result landing well away from it
does not by itself indict the LUT.
★ **THE CONFIRMATORY TEST IS IMMUNE TO THIS.** §2 generates fresh records from certified H12 at its
own settings (5 forks, H=15, margin 3), so the agreement/transfer measured there is against real
H12. Only the offline prior inherits the mismatch.

**Second named risk, added by Amendment 1:** the ratio 48% rests on a split-sample estimator with
only 3 evaluation forks per candidate. If a future bank stores more forks, re-derive it rather than
carrying this number across.

Secondary risks: the offline fit was non-blind on the bank (its *features* and *fit* are, its
*evaluation here* is not); the bank is death-conditioned (all topout games); H12's own transfer was
estimated by simulating 5-of-8 forks, an approximation of its real fork draw.

## 9. N AND COST — **SIZED BY POWER, NOT BY BUDGET**

⚠ **This program has already lost 15,000 games to a guard that needed 7,824 pairs and was run at
3,000. N here is chosen by the effect we are willing to be unable to detect, and that choice is
recorded BEFORE the run.**

**The primary is VALUE TRANSFER, seed-clustered — not clear rate**, so a clear-rate McNemar SE is
the wrong basis. Measured on the banked held-out tie groups: **SE(transfer) = 15.5pp at 66 seeds**
(~3.9 tie groups/seed), scaling 1/√n. S1 fires iff the CI lower bound exceeds 20% of H12.

| if true transfer is | seeds | flips | core-h | wall h @12 | € |
|---|---|---|---|---|---|
| 48% (the amended prior) | 78 | 324 | 7.9 | 0.7 | 0.16 |
| 40% | 153 | 635 | 15.5 | 1.3 | 0.32 |
| 35% | 271 | 1,125 | 27.5 | 2.3 | 0.56 |
| **30% ← REGISTERED** | **610** | **2,532** | **62.0** | **5.2** | **1.27** |
| 27% | 1,244 | 5,163 | 126.4 | 10.5 | 2.58 |
| 25% | 2,437 | 10,114 | 247.6 | 20.6 | 5.06 |

**N swings ~30× across the plausible range, and the whole range costs under €6. Budget is not the
binding constraint and is not allowed to pick N.**

> **⚠⚠ AMENDMENT 3 — THE TABLE ABOVE WAS 50% POWER, NOT 80%. Corrected before launch.**
> ~~REGISTERED: N = 610 paired seeds, powered for a true transfer of 30%~~ — **STRUCK.**
> That table gave the n at which the EXPECTED CI lower bound just *touches* the threshold, which is
> by definition **50% power**: at N=610, SE = 15.5·√(66/610) = **5.10pp** and the expected lower
> bound is 30 − 1.96×5.10 = **20.01**, sitting exactly on the 20% bar. A coin flip is not a
> confirmatory run. The error was mine and it is the same species as sizing by budget: **a
> convention quietly picked N.**
>
> **z IS STATED EXPLICITLY: `z_α = 1.959964` (two-sided 95%), `z_β` per the power column.**
> `n = 66 · (0.155 / ((t − 0.20)/(z_α + z_β)))²`
>
> | true transfer | 50% | **80%** | **90%** |
> |---|---|---|---|
> | 48% | 78 | 159 | 213 |
> | 35% | 271 | 554 | 741 |
> | **30%** | 610 | **1,245** | **1,667** |
> | 27% | 1,244 | 2,540 | 3,401 |
>
> **★★ REGISTERED: N = 1,666 paired seeds — 90% power at a true transfer of 30%.**
> SE 3.09pp · ~6,914 flips · ~169 core-h · **12 workers, ~14.1 h wall, ~€3.46**.
> **Running at 12 workers, not 14, deliberately:** 96.1 seeds/h is *measured* at 12 and *unmeasured*
> at 14 on a shared-tenant box. Two hours of wall-clock is not worth introducing an unmeasured
> assumption on the night I spent removing them.
> **★ STATED IN ADVANCE: a true transfer below ~27% leaves S1 unable to fire. If the result lands
> there the correct report is "NOT RESOLVED AT THIS n", never "the substitution fails."**
>
> **⚠⚠ AMENDMENT 4 (2026-08-26) — CAPTURE DEFECT + N HELD AT 1,666.**
>
> **(a) The capture was SELECTED ON THE OUTCOME and is fixed.** `h12_arm.py:113` guards its log
> with `if a != base_a:`, so the first run banked **only flips**. On that population the champion's
> move is by construction the one H12 rejected — measured over 259 seeds: **champion −93.7%,
> worst −97.4%, random 0%, H12 +100%, LUT −24.4%.** The LUT's number was measuring
> **champion-correlation, not decision quality.** §4's estimand is transfer over champion-value
> **TIE GROUPS**; the **keeps** are what make it unbiased and they were never recorded.
> **Fixed** by observing `oracle_arm._fork_label` — which H12 calls only inside the fork loop, i.e.
> only at tie plies — and recording every candidate's labels, flips and keeps alike. The observer
> forwards and returns verbatim, so the decision path is still untouched.
>
> **(b) N STAYS AT 1,666 — the 6.30pp SE MUST NOT be used to re-size.** That SE was measured on the
> flip-only population, i.e. **the very population just proven wrong**. Sizing the superset from a
> statistic computed on a selected subset is the same error with the sign reversed: there the
> *estimate* was contaminated, here the *variance* is. Flip plies are the contested, homogeneous,
> high-signal slice; adding the keeps changes both mean and spread. **The correct prior is the
> 15.5pp measured on the offline bank's champion-value tie groups — the same population the fixed
> capture now produces — so the registered N=1,666 stands.**
>
> **(c) RE-SIZING RULE, fixed in advance:** the n=200 interim **MAY REDUCE N** if the SE measured on
> the **corrected tie-group population** justifies it, and **MUST STOP AND REPORT** if it implies an
> N above 1,666.
> ⚠ **The re-size looks ONLY at the VARIANCE. The effect estimate stays BLIND until the run ends.**
> Re-sizing on a peeked effect inflates the false-positive rate; re-sizing on variance alone does not.

> **★ INTERIM SE CHECK (blocking):** at **200 seeds**, recompute the realised seed-clustered SE. The
> registered N assumes SE = 15.5pp at 66 seeds scaling 1/√n, measured on the *offline bank's* tie
> groups (~3.9/seed) — the run measures H12's *actual flip plies* (~4.15/seed). **Different
> population.** If the realised SE implies an N materially above 1,666, **stop and report before
> continuing** — an N that is itself underpowered must surface at the interim, not at the end.
>
> ~~superseded sizing below~~ **★ REGISTERED: N = 610 paired seeds, powered for a true transfer of 30%** — the pessimistic end
> of the measured CI [4.1, 41.8], **not** the 48% prior, which rests on three stacked assumptions.
> **STATED IN ADVANCE: a true transfer below ~27% leaves S1 unable to fire. If the result lands
> there the correct report is "NOT RESOLVED AT THIS n", never "the substitution fails."**

**Cost basis, all measured not quoted:** 4.15 flips/seed (n=20) · 82 core-s/flip (n=20) · ×1.075
for cap 400 (measured from the real ply distribution, §11).

⚠ **CAP 400 IS 4.2% DEARER PER FLIP, NOT CHEAPER.** Measured on 3,632 reference games: +7.5%
compute (mean 226.4 → 243.3 plies/game) buys only **+3.2%** flips (2,913 → 3,005). **The
within-game Q4 hazard does NOT translate into absolute-ply density**, because only the minority of
games that run past 300 contribute there. **Cap 400 is justified on VALIDITY — label censoring —
and not on cost.** The earlier "+6% compute for +8% flips, so it is cheaper" reasoning is refuted.

## 9b. ORIGINAL COST NOTE (superseded, kept visible)


Certified-H12 provenance yields **~5 flips/game** (3,005 flips from ~600 paired seeds). To separate
57.5% from 50% at 80% power needs **~350 flips**; **1,000 flips ⇒ ~200 games** gives comfort.
Endpoint anchor from the H14 segment summaries: ~723 core-s per paired seed; a base-arm-only census
is roughly half ⇒ **~20 core-h ⇒ ~1.25 h on a 16-core cpx62 ⇒ ~€0.31.**
⚠ Per rule 39 that anchor is quoted, not measured here — **smoke 20 seeds and re-derive the rate
before committing.**

## 10. COMPUTE DISCIPLINE
**Burst node, not blackmage** (champion trial 481/600 + null arm overnight) and **not the legacy
Hetzner box** (NES lane; never resize or rebuild it). `/cloud` pattern exactly: ledger row on create
**and** on delete · PROVISIONING.md with the pinned venv · the lane's bit-exactness gate re-run on
the new CPU **before any row counts** · fetch and verify row counts locally **before** teardown ·
then delete. All runs `nice -n 19`, threads capped.
