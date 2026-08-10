# STAGE 2 — LEARNED LEAF EVALUATOR vs DIES-AHEAD

## VERDICT: NULL. NO-GO.

**The learned evaluator did not reduce dies-ahead.** In a 3,000-seed paired rollout under dr.
lulu's fitted pressure, it moved dies-ahead by **−0.80 pp [−2.20, +0.60]**, McNemar p = 0.2793 —
and a **dose-matched, label-blind null** (the same lookup tables with their rows randomly
permuted, offline AUC 0.4746) moved it **−0.53 pp [−1.93, +0.87]**. Difference-in-differences
**−0.27 pp [−1.73, +1.13]**, 60.5 % of bootstrap reps negative.

A **+0.0575 offline AUC edge with 100 % of 2,000 bootstrap reps positive produced a rollout
effect indistinguishable from randomly shuffling the model's own numbers.** That is not an
underpowered null. That is a refutation of the AUC→rollout bridge for this class of term.

**Do not spend silicon on this.** The recommended LUT is refused.

**d_spawn_h does not rescue it either** — but see §9: as an additive term it is the strongest
single input in the lane, it is *free* in RTL (measured), and **it was never rolled out**. That
is the one loose end worth closing, and it costs ~3 hours.

The genuinely valuable output of this lane is negative-result infrastructure, and it is
reusable: §11.

---

## 1. THE QUESTION

The champion's signature failure is **dying while ahead** — winning on virus count, then topping
out. Clean solo play fails < 0.20 % of the time; under garbage pressure 16.7 % (82×). Diagnosis
on the record: *the evaluator is risk-neutral near an absorbing state.*

Stage 1 measured a **ceiling**: a GBM over all features scored AUC 0.956 vs the champion
evaluator's 0.926 on 5,824 held-out decisions. The verdict was "justifies stage 2".

**Stage 2's question, in one sentence:** *is any part of that ceiling reachable by something that
fits in a few hundred FPGA cycles, and does it reduce dies-ahead in actual rollouts without
breaking clear games?*

Two ways this lane could fail, both named in advance:

1. **AUC is a proxy.** Project law: *signal ~ sqrt(R)/SE; proxies rule OUT only.* An AUC win is
   permission to test, never a result. **The deliverable is a measured reduction in dies-ahead in
   rollouts.** — *This is the failure mode that occurred.*
2. **Deployability.** A 500-tree GBM cannot ship. The budget had to be established in phase 1 and
   designed against, not discovered at the end. — *This one was handled: the shipped candidate
   costs 18 of 250 clocks and 0.34 of one M10K.*

---

## 2. THE PRE-REGISTERED VERDICT RULE

Three pre-registrations, all committed on branch `copro-qa-harness` in
`/home/struktured/projects/dr-mario-qa-wt`, each **before** the thing it governs existed:

| File | Commit | Committed (local) | Governs |
|---|---|---|---|
| `experiments/eval47/stage2/PREREG_STAGE2.md` | **`b9725fc`** | **2026-08-10 07:15:44 −0400** | corpus, gates A/B, primary endpoint, GO/STOP/NO-GO |
| `experiments/eval47/stage2/PREREG_SHIPPABLE.md` | **`2d4d5d0`** | **2026-08-10 09:31:27 −0400** | model shapes, feature selection, quantisation format |
| `experiments/eval47/stage2/rollout/PREREG_ROLLOUT.md` | **`f5f58f0`** | **2026-08-10 10:13:46 −0400** | arms, seed sets, breakage accounting, early stop |

`b9725fc` predates the corpus. `2d4d5d0` predates any fit. `f5f58f0` predates any A/B game (the
scope launched 10:24; `ab_lulu.jsonl` finished 12:01).

### The rule as written

**GATE A — corpus admissible.** A1 fidelity vs census row *and* the real rig's trace-derived
fields; A2 killed mutants (`ws=0`, garbage-rng, tie-break) must BREAK A1; A3 shuffled-label floor
+ leak positive control; A4 per-decision cross-checks. *Any failure ⇒ the corpus is not evidence.*

**GATE B — offline, holdout, PROXY (can only RULE OUT).**
- B1: holdout AUC(model) − AUC(y_shuf refit) ≥ 0.10
- B2: holdout AUC(model) > AUC(CHAMP_EVAL), 95 % **seed-clustered** bootstrap CI on the paired
  difference excluding 0; **any margin under +0.01 counts as NOT CLEARED**
- B3: within-decision argmax-flip ≥ 2 % on target-class decisions, else the arm is untestable
- B4: eval-hacking holdout on `end_kind` and `since_last_garbage` deciles

**PRIMARY ENDPOINT.** Paired rollout base vs treatment, **N = 3,000 seeds drawn uniformly from
20000..22999** (disjoint from every corpus seed), lulu regime, 6,000 games. Uniform population
sampling was mandated deliberately — it prices breakage at the true ratio automatically instead
of sampling failures and clears separately and re-weighting, *which is how the always-on penalty
family got its net-harm number wrong.*

**GO requires:** `DA_trt − DA_base < 0` with a 95 % seed-bootstrap CI excluding 0 **AND** McNemar
exact two-sided p < 0.05.

**CO-PRIMARY GATING clear-rate non-inferiority:** the **upper** bound of the 95 % CI on
`(clear_base − clear_trt)` must be **< +1.0 pp**. If clear rate falls more, it is **NO-GO
regardless of dies-ahead** (at 9,576 clears : 1,501 dies-ahead = 6.4 : 1, breakage is 6.4× as
expensive as rescue).

**SHIPPABLE CLASS, fixed BEFORE fitting** from the measured silicon budget: ≤ 250 added
clocks/leaf, ≤ 150 added ALMs, ≤ 2 M10K host-uploadable, **zero new whole-board passes**; the ten
champion terms stay bit-identical so `Delta = 0` is an exact-identity control.

**STOP:** S1 gate A fails or a mutant survives · S2 no in-class model clears B1/B2 · S3
argmax-flip < 2 % · S4 the only model clearing B2 is out of class ⇒ **report as CEILING ONLY**.

**NO-GO:** N1 clear-rate loss upper bound ≥ +1.0 pp · N2 dies-ahead CI includes 0 · N3 dies-ahead
falls but net bad-ends do not · N4 rollout identity or liveness gate fails ⇒ void.

**A STOP or NO-GO is reported with the same prominence as a GO.** This document is that.

### Was the rule edited after results?

One real red flag, checked rather than assumed. `PREREG_ROLLOUT.md` has an mtime of 13:39, *after*
the lulu primary read out at 12:01. The 150-line version committed at `f5f58f0` is a **byte-exact
strict prefix** of the final 199-line file (verified programmatically: `b[:len(a)] == a`). All 49
added lines are appends to the §6 deviation log declaring two null-control arms explicitly marked
**"NO VERDICT AUTHORITY"**.

Mechanical deletion counts since first commit: `PREREG_STAGE2` **0 deletions / 74 additions**;
`PREREG_SHIPPABLE` **0 / 80**; `PREREG_ROLLOUT` **0 / 49**. §4 (the GO conditions) is untouched.

**The rule can emit GO.** `rollout/test_verdict.py` is mutant-tested: synthetic true win → GO; big
DA win with a 4 pp clear collapse → NO_GO; null → NO_GO; regression → NO_GO; N = 800 →
INCONCLUSIVE. *A rule that could only say NO_GO would be vacuous.*

---

## 3. THE CORPUS AND ITS LABEL QUALITY

**Artifacts:** `experiments/eval47/stage2/results/` — `s2lulu_fail_local.npz` (306,882 rows /
1,686 topout games), `s2lulu_ctrl_local.npz` (168,233 / 1,200 cleared), `s2lulu_stall_local.npz`
(75,000 / 250 stalls, **never pooled**), `s2feat_local.npz` (26-feature matrices + the 32-sibling
within-decision layer). **550,115 decisions across 3,136 games.**

**Split:** by game/seed, `hold = seed % 10 ∈ {7,8,9}`, deterministic and feature-independent.
Measured, not assumed: `seed_overlap_train_holdout = 0` (asserted at build time). Contrast rows
360,844 → **train 255,893 / holdout 104,951** across **657 holdout games** (297 positive + 360
control). Twin-seed aliasing measured: 410 twin pairs present, 81 straddling the split, only 22
straddling **and** same-class.

**Holdout sealed stricter than required:** every label-associated statistic — gate A3, all
per-feature AUCs, the 400-permutation null — ran on **train rows only**.

**Rollout seeds are a third, disjoint tier:** 20000..22999. Corpus seeds are 2..12001.
**Intersection measured = 0**, from the actual seed arrays, not from the claim.

### The label-quality screen: FAILED, and stated up front

> **The lulu census clear rate is 79.80 %** (9,576 clear / 1,686 topout / 738 stall of 12,000) —
> **far below the > 96.9 % bar** of the label-quality law.

This is written into `PREREG_STAGE2.md` §7, into `s2lulu_meta_local.json`, into the builder's own
stdout, and into **every result JSON this lane produced** as a mandatory caveat string. It rides
on every number in this document.

**The written justification, three checkable legs:**

1. **The mechanism the threshold prices is not the one operating.** The 96.9 % bar was derived to
   choose between *rollout policies* labelling positions with a pills-to-clear **regression**
   target, where a bimodal clear/fail outcome inflates per-label SE. Here the label **is** the
   binary game outcome and the failures **are** the signal.
2. **The policy is not degraded — the environment is adversarial.** Fidelity gate: 24/24 gate
   seeds reproduce both the census row and the real rig's trace-derived fields (which pin the
   whole action sequence, not just the outcome); **0 / 3,136 bulk census-row mismatches**. Three
   killed mutants fire 4/4 each: `ws=0`, `garbage_rng+1`, and a tie-break flip. Under this same
   policy with no pressure, clean solo failure is < 0.20 %.
3. **The memory records the 96.9 % threshold as REFUTED as a decider** — *"rule OUT, never rule
   IN"*. Nothing is being ruled in by it.

### The bigger defect, which the screen does not cover

**The label is a game outcome broadcast onto a whole game's decisions with no counterfactual.**
A decision 92 plies from the end carries a label it cannot possibly have determined. This is why
`t_to_end` is stored and why the primary analysis is reported at **every** `t_to_end` band (§4),
and it is why a within-decision counterfactual test was added (§5, §9) — the only endpoint in the
offline work with a true per-decision label.

**The shuffled-label control is built into the pipeline** and it demonstrably fails: every corpus
file ships `y_shuf` (permuted across **games** — stage 1's was decision-level and
anti-conservative) and `f_leak = y + N(0, 0.1)`. **Gate A3 FAILED as pre-registered** (0.5291 vs
a guessed band [0.48, 0.52]) and **is reported as a failure, not retuned**; a 400-permutation
measurement then showed the permutation unbiased (max bias 0.00056) and the true null band wider
than the guessed one. Measured detection limit: the floor **catches a 20 % game-level label leak
and misses 10 %** — so it can fail, and its sensitivity is known.

**Coverage fix (stage 1's biggest defect):** stage 1 had **zero** fatal decisions below
`max_height` 13. Here **46.9 %** of target-class decisions are below it (h0–9 7.51 %, h10–12
39.36 %), and 182,061 of 192,611 sit at `t_to_end > 9` — decisions stage 1's last-K = 10 window
could not see at all.

### Two properties of the corpus generator that must travel with these numbers

- **The garbage trigger is causally inverted vs a real VS game.** `pressure_rig.py:240-243` fires
  the volley when **we** clear (`if clear_size > 0`), standing in for the opponent's clear. In a
  real 2P game garbage arrives when the **opponent** clears. This is not merely the documented
  "not-clearing is garbage-immune" exploit surface — it makes the arrival process
  *anti-correlated with reality*: the rig punishes tempo where the real game rewards it.
- **There is no opponent board anywhere in this lane.** All 12,000 census games and all 15,000
  rollout games are **solo** with a scripted injection proxy. The north star is a two-player
  match; this lane optimises a solo surrogate for it.

---

## 4. THE CEILING — UNCONSTRAINED, NOT SHIPPABLE, NOT A RESULT

> **Everything in this section is a ceiling measurement.** The model is a ~500-tree GBM, roughly
> four orders of magnitude over the cycle budget, and needs a second board pass. **Per prereg S4
> it is reported as CEILING ONLY.** Do not read any number here as an achievement.

**Instrument check:** the AUC function reproduces `s2_features.py`'s independently written `_auc`
bit-for-bit on train rows (CHAMP_EVAL `0.6686903491720213` vs `0.6686903491720213`, Δ = 0.00e+00).

### Headline

| arm | holdout AUC |
|---|---|
| CHAMP_EVAL (champion depth-3 root value) | **0.6645** |
| GBM over all 26 features | **0.7327** |
| paired seed-clustered bootstrap | **+0.0685 [+0.0562, +0.0805]**, 400/400 reps positive |
| shuffled-label refit (10 independent game-level permutations) | **0.5057** mean, range [0.4946, 0.5282] |

Clears B1 (0.7327 − 0.5057 = 0.227 ≥ 0.10) and B2 (margin ≫ +0.01).

**Not comparable to stage 1's 0.956 / 0.926.** Stage 1 kept only the last 10 decisions of failure
games with height-matched controls. This corpus keeps *every* decision (median `t_to_end` 92). On
the equivalent near-death slice this corpus reads **0.9816 / 0.9841** at `t_to_end ≤ 2`.

**Instrument spread, stated because it matters later:** three independent fits of "the ceiling"
disagree by **0.0111** — 0.7343 (150-iter attribution refit), 0.7327 (primary), 0.7232 (the
shippable lane's own refit).

### The single most actionable finding: 81 % of the gain is *not* new features

Exact decomposition of the +0.0682 total (primary instrument, 100 iterations):

| step | AUC | share of total gain |
|---|---|---|
| champion's **linear** evaluator | 0.6645 | — |
| **GBM over the champion's OWN 11 terms** | **0.7195** | **80.8 %** |
| + `d_spawn_h` (12 features) | 0.7289 | +13.7 % |
| + the other 14 candidates (26 features) | 0.7327 | +5.5 % |

**Four fifths of the entire ceiling is a nonlinear recombination of sensors the champion already
computes** — no new board pass, no new sensor, nothing to add to the column walk. The lever is
the *linear combine*, not the sensor set.

Corroborating: **permutation importance** ranks `BURIED` (+0.0353), `d_gvuln_mass` (+0.0257),
`POLL` (+0.0229), `RDYEXT` (+0.0157) at the top — all **existing champion terms** whose
single-feature AUC is at or below chance. They carry the gain purely through interaction, which
is precisely why the linear combine leaves 81 % of it on the table.

The three **OFF_BUDGET** features (needing a whole extra board traversal) contribute **+0.0033 in
total**. Honouring that tag cost essentially nothing.

Greedy forward selection from the champion's 11 (chosen on the inner train fold, holdout
untouched during selection) picks **`d_spawn_h` first** out of all 15 candidates, reaches 94.2 %
of the ceiling gain at 12 features and 98.0 % at 13, then plateaus. **There is no long tail.**

### Where the gain lives — the best structural news in the report

The mandate warned that a model winning only where games are already lost is worth nothing. **The
opposite is true here.**

| `t_to_end` | n | model | champ | Δ [95 % CI] |
|---|---|---|---|---|
| ≤ 2 | 1,971 | 0.9816 | 0.9841 | **−0.0025 [−0.0093, +0.0044]** |
| 3–9 | 4,599 | 0.9565 | 0.9313 | +0.0253 [+0.0105, +0.0423] |
| 10–30 | 13,797 | 0.9220 | 0.8601 | +0.0619 [+0.0404, +0.0840] |
| 31–90 | 38,548 | 0.7669 | 0.6743 | **+0.0926 [+0.0691, +0.1180]** |
| > 90 | 46,036 | 0.5681 | 0.5912 | −0.0231 [−0.0467, +0.0018] |

The model is **tied with the champion at the deathbed** and wins hardest **10–90 plies from the
end** — the window where there is still time to act. This corroborates the independent finding
that at the deathbed `d_spawn_h` is already **exhausted**: the champion takes a minimum-spawn-lane
action on 91.3 % of the last 12 plies before a garbage-topout, and in 49.8 % of those games there
is not one ply where any legal action would have produced a lower spawn lane.

**By pressure — the entire gain is in the pressured regime:**

| slice | n | model | champ | Δ [95 % CI] |
|---|---|---|---|---|
| clean, no garbage yet | 18,462 | 0.5235 | 0.5281 | −0.0046 [−0.0357, +0.0253] |
| pressured, garbage seen | 86,489 | 0.7615 | 0.6919 | +0.0696 [+0.0555, +0.0854] |

On clean boards **both rankers sit at chance** and the difference is zero. That is the 82×
clean-vs-pressured ratio showing up as a ranking property, and it is the right sign for the
structural law — a term carrying no signal on clean boards has less contact with the 9,576-clear
population where breakage is priced. **It does not prove low breakage. Only the rollout can, and
it did not** (§6).

**By height** (stage 1 had zero fatal rows below h = 13): positive and CI-excluding-0 at every
band — h ≤ 9 +0.0867, h10–12 +0.0684, h13–14 +0.0846, h15–16 +0.1150.

**By viruses left:** +0.0820 at v ≤ 8, +0.0216 at v9–24, −0.0111 at v > 24. Dies-ahead means few
viruses left; the gain is correctly targeted.

**Stratum-matched** (stage 1's key, 501 strata): model 0.6539 vs champion 0.6182. The margin
attenuates from +0.070 to **+0.036** under matching but survives it. Roughly half the pooled
margin is board congestion the stratum key also captures.

### The badness-detector limitation — a real one

Target-class decisions vs **stall** decisions (both from bad games; only one tops out): **model
0.4395, champion 0.4133**. *Both rankers score stall boards as MORE fatal than about-to-top-out
boards.* A substantial part of what is being measured is "this game is going badly", not "this
game is about to end" — which is the label-broadcast defect operating, now measured. The model is
*less* confused than the champion, so it is not a new exploit; but neither is a clean survival
ruler, and it made prereg **N3 (topouts converted into stalls) a live rollout risk** — a risk that
duly showed up (§6).

Counter-evidence on the same question: an imminence probe (within positive games, AUC of "this
decision is within 9 plies of the topout") reads **model 0.855, champion 0.755, `d_spawn_h`
0.900**. All three do carry proximity information. It is not *purely* a badness detector — but its
ordering across game *types* is wrong.

### Leak interrogation — every check stated with the wrong input that makes it fail

| # | check | result |
|---|---|---|
| L1 | **Future-feature dependence.** Killed mutant: refit with `t_to_end` injected as a 27th feature → AUC 0.7327 → **0.8126**. The detector sees a future feature loudly, so its silence on the real 26 is informative. Direct probe: Spearman(model score, `t_to_end`) = **−0.045**; the **champion's own** evaluator reads **−0.139** — the learned model is *less* aligned to the clock than the evaluator it is compared against. | **CLEAN** |
| L2 | **Shuffled-label floor.** The single pre-registered draw (seed 20260810, not re-rolled) is a ~2.5σ unlucky permutation; 10 independent game-level permutations, each refit end to end, give mean **0.5057** vs their own labels. The pipeline that reads 0.7327 with real labels reads 0.5057 when labels are destroyed. **The control fails, by 0.23 AUC.** | **CLEAN** |
| L3 | **Mechanism transfer (B4).** Trained on garbage-blocked spawn only; on the structurally different *self-inflicted* `step_topout` mechanism it reads 0.7539 vs champion 0.6862, **+0.0679 [+0.0551, +0.0797]**. A volley-schedule reader would collapse here. | **CLEAN** |
| L4 | **`since_last_garbage` deciles (B4).** Margin +0.06 to +0.07 and **flat** across deciles 2–9; the only exception is the never-any-garbage decile where both sit at 0.52–0.53. Not reading the volley clock. | **CLEAN** |
| L5 | **Different-generation corpus, no refitting.** Applied unchanged to the stage-1 `vocab2` corpus (different pressure model, different extraction), restricted to seeds > 12001 so seeds are **disjoint**: model 0.9763 vs champion 0.9443, **+0.0324 [+0.0169, +0.0528]**. This **reproduces stage 1's independently measured +0.031 almost exactly on stage 1's own data.** | **CLEAN** |
| L6 | **Within-decision sibling ranking (B3).** Tie-aware, on the 32-sibling layer: ceiling GBM flips **71.7 %** of target-class holdout decisions, `d_spawn_h` **26.0 %** — both ≫ the 2 % untestability floor. *(First-pass 99.3 % for `d_spawn_h` was an `argmin` enumeration-order artifact on a feature with 74 % ties. Found and fixed before reporting.)* | **CLEAN** |
| **L7** | **The counterfactual test — the one that most nearly refutes the win.** See §5. | **DOES NOT SURVIVE** |

**Could not rule out, stated plainly:** (a) badness-vs-imminence, above; (b) roughly half the
pooled margin is board congestion the stratum key already captures; (c) the corpus fails the
literal clear-rate screen.

---

## 5. THE COUNTERFACTUAL TEST — the only true per-decision label available

The corpus's stated biggest defect is that the label is a game outcome with no counterfactual.
The fork data from the anatomy lane supplies real per-**action** forked rollouts: at each ply,
every legal action is forked onto a clone and continued with the **real champion policy** and the
**real lulu injection schedule**.

**Join validated:** the fork's own champion choice equals the corpus's stored action on
**852 / 864** plies; the 12 disagreements are exactly the documented naive-vs-champion
enumeration-order defect (1.39 % here vs 1.71 % measured by the corpus builder) and are dropped.
Expander legality vs stored `cand_vals`: **0 mismatches over 852 × 32 slots.**

**RAW survival** (662 discriminative plies / 76 seeds), within-decision AUC of "this action
survives":

| ranker | within-decision AUC |
|---|---|
| `d_spawn_h` | **0.6195** |
| MAXH | 0.5448 |
| ceiling GBM | 0.5319 |
| champion | 0.5187 |
| SPAWN | 0.3924 |

- `d_spawn_h` − champion: **+0.1008 [+0.0769, +0.1253]**, 100 % of reps positive
- **GBM − champion: +0.0133 [−0.0170, +0.0432] — CI INCLUDES 0**

*On the actual job of a leaf evaluator — ranking 32 siblings of one parent against a real survival
label — the unconstrained ceiling model does not beat the champion at all, and the single free
feature beats it by +0.088.*

**AND NOW THE DEFLATION, reported with equal prominence.** A rescue that stops clearing is not a
rescue, and this rig makes the exploit free (the volley is gated on `clear_size > 0`, so a fork
that never clears is garbage-immune). Re-running with a **progress gate** (survives **and**
viruses actually went down), 232 discriminative plies / 44 seeds:

| ranker | AUC | vs champion |
|---|---|---|
| `d_spawn_h` | 0.5714 | **+0.0256 [−0.0092, +0.0603]** — CI includes 0 |
| MAXH | 0.5609 | — |
| ceiling GBM | 0.5525 | **+0.0068 [−0.0299, +0.0424]** — CI includes 0 |
| champion | 0.5459 | — |

**Under the progress gate nothing separates from the champion, and `d_spawn_h` is statistically
tied with MAXH — a term the champion already has.** Most of the raw counterfactual advantage is
the rescue-by-not-clearing confound.

**And the design is biased in favour of the challengers:** the fork windows are the last 6–12
plies of games the champion *lost*, so the champion's chosen move is fatal by construction. Under
a bias that flatters them, gated, they tie.

**This was the warning the rollout then confirmed.** It is on the record that the offline case was
an AUC case and that the rollout, not the AUC, would decide it.

---

## 6. THE SHIPPABLE RESULT — clearly separated from the ceiling

> **Ceiling ≠ shippable.** §4 describes a model that cannot run. This section describes models
> that can. They are different objects and the numbers are not interchangeable.

Pre-registered at **`2d4d5d0`** before any fitting: the shapes, the train-only GroupKFold-by-seed
feature-selection procedure, and the exact fixed-point format. Features frozen and models fitted
at `5bb4097`, holdout still sealed. **Holdout opened exactly once.**

### Round 1 — the CLEAN, uncontaminated result

`A_champ = 0.6645`. All AUCs are the ship-dose quantised value.

| shape | holdout AUC | B2 paired diff | cycles | params | fits budget |
|---|---|---|---|---|---|
| **S0** `d_spawn_h` hinge alone | 0.6543 | **−0.0102, 18.9 % reps pos → FAILS B2** | 4 | 204 bits | yes |
| S1 8× 4-segment monotone hinge | 0.6974 | +0.0329 [+0.0169, +0.0487] | 18 | 3,132 bits | yes |
| **S1b additive per-feature LUT** | **0.6976** | **+0.0331 [+0.0176, +0.0491]** | **18** | 3,132 bits | yes |
| S2 256 sequential stumps | 0.6974 | +0.0328 [+0.0164, +0.0493] | **512** | 8,960 bits | **NO — over the 250-clock budget** |
| S3 32 sequential depth-4 trees | 0.6983 | +0.0338 [+0.0178, +0.0498] | 160 | 11,286 bits | yes |
| *CEIL — 26-feat 500-tree GBM (out of class)* | *0.7232* | — | *~3,000* | *> 1 Mbit* | ***NO*** |
| *CEIL8 — unlimited capacity, SAME 8 in-class features* | ***0.6910*** | — | — | — | ***NO*** |

All four multi-feature shapes clear B2 with 100 % of reps positive; B3 clears 2 % for every shape.

**The model shape is not the constraint; the feature set is.** `CEIL8` — an unconstrained 500-tree
depth-6 GBM on the *same 8 in-class features* — reads **0.6910, lower than every shippable
shape**. Unlimited capacity on these features buys nothing; it overfits. **Chasing a bigger model
is refuted.**

**B1 had to be corrected, and it is reported as a failure first.** Read against the corpus's single
pre-registered `y_shuf` draw, B1 **failed** for 4 of 5 shapes. Diagnosis: that draw is a +2.5σ
unlucky permutation. Refitting each shape on 20 independent game-level permutations puts the null
mean at 0.4960–0.5005 for every shape; B1 margins vs the measured null are +0.154 to +0.204, all
clearing 0.10 by ~2×. This is the same amendment `PREREG_STAGE2` §10 already made for A3.
**Limitation reported: the null is wide (p95 0.60–0.63) and a 20 % game-level leak lands at
0.593–0.630, so B1's 0.10 bar is worth about a 20 % leak. B1 is a weak test.**

**Quantisation-aware, as demanded.** 12-bit quantisation is **lossless** (identical to 4 dp on
every model), so the check would have been **vacuous** without the pre-registered 3-bit killed
mutant. The mutant fires: S1 0.6989 → 0.5485, S1b 0.6996 → 0.6322, recommended 0.7225 → 0.6737.
It fires only weakly on S2 (0.7002 → 0.6954) because 256 small additive terms average the error
down — **reported, not hidden.** 7 of 8 features are exactly representable in uint8; `x_hvar`
rounds with max error 0.5.

### Round 2 — CONTAMINATION-FLAGGED, and this is the arm that was rolled out

**The largest offline finding of the lane, and its flaw, together.**
`PREREG_STAGE2` §8's `FREE_IN_COLWALK` list **omitted SETUP, MATCHED, BURIED, RDYEXT, VRDY and
POLL — the champion's own combine operands.** Verified directly in `fpga/copro/LeafEval.sv`
`S_DONE2`: all ten are already-registered `*_p` values at the instant the combine runs, so reading
them as Delta inputs costs **0 new board passes, 0 new cycles, 0 new accumulators.**

Admitting them lifts the best in-class holdout AUC from **0.6983 to 0.7268** — *past the
out-of-class 26-feature ceiling.*

> **CONTAMINATION FLAG, stated up front:** the decision to look at that category came **after** a
> holdout-scored diagnostic ranked `BURIED` first. **Every round-2 number is optimistically biased
> and is INDICATIVE ONLY.** Mitigating and measured: round 2's own train-only selection picks
> `BURIED` second unprompted, so the holdout pointed at the *category*, not the feature.
> **Round 1 remains the clean result.**

| round-2 shape | ship-dose AUC | B2 diff | cycles | params |
|---|---|---|---|---|
| S1r2 hinge8 | 0.7110 | +0.0465 | 18 | 8,904 bits |
| S1br2 lut8 (255-level) | 0.7231 | +0.0586 | 18 | 8,904 bits |
| **S1br2_lut8_q64 ← RECOMMENDED** | **0.7220** | **+0.0575 [+0.0458, +0.0686]**, 100 % reps pos | **18** | **3,456 bits** |
| S3r2 tree32d4 | 0.7268 | +0.0623 | 160 | 11,056 bits |

**Why the LUT and not the trees** — the pre-registered tie-break decided it: S3r2 beats the LUT by
+0.0048, **under the +0.005 simplicity threshold fixed in `PREREG_SHIPPABLE` §7 before any number
existed.** Cheaper wins. Reinforcing: at matched dose the LUT flips 2.12 % of target-class and
1.65 % of *cleared-game* decisions; the trees flip 3.20 % / 2.49 % — **35 % less clear-game contact
for the same discrimination**, which is the entire structural-law argument. And the trees have a
**dose deadband** (literally inert at low dose, every leaf value rounding to zero), so they cannot
be tuned; the LUT doses smoothly from Δ_sd = 2.

### THE NUMBER NOBODY SHOULD MISS

At the ship dose the **combined deployed score's** AUC moves only **+0.001 to +0.002**, not
+0.033 to +0.058 — because Delta's sd (~10 points) is deliberately tiny against the champion
score's sd (~1,038):

| shape | champion | deployed `champ − Delta` |
|---|---|---|
| S0 | 0.6645 | 0.6670 |
| S1 | 0.6645 | 0.6657 |
| S1b | 0.6645 | 0.6657 |
| S3 | 0.6645 | 0.6667 |

**The B2 margin says the model carries independent signal. The actual deployed effect at the
minimum testable dose is a 2.1 % argmax flip.** That is exactly why the deliverable was the
rollout and not this table — and it is the clearest early warning, visible before the rollout ran,
of the null that followed.

### Two standing observations

- **The flip lands disproportionately on TIES:** 3.80 % of tied decisions vs 1.13 % of decisions
  the champion actually decided. Holdout tie rate **36.95 % (fail) / 35.90 % (control)**. At low
  dose this term is mostly breaking ties the champion currently resolves **by enumeration order**
  — the safest possible mode, and the mechanism `PREREG_STAGE2` §8 explicitly hoped for.
- **B4 eval-hacking:** the model's AUC swings 0.225 across `since_last_garbage` deciles — but the
  **champion swings 0.188** across the same deciles, so most of that is the slice, not the model.

---

## 7. THE ROLLOUT

**Arms.** BASE = shipped champion, unchanged (`ws=20`, `wt=0`, `variant("winner")`, depth-3,
`pressure_rig._choose_base` enumeration). TRT = `sco_i = cand_val_i − Delta(features(post-placement
board of candidate i))`, Delta = `S1br2_lut8_q64` at ship dose Δ_sd = 10. **The ten champion
weights are BIT-IDENTICAL; nothing is re-weighted; `Delta = 0` is an exact-identity control.**

**DEVIATION, declared in the prereg before the run:** Delta is applied at the **ROOT re-rank**, not
at every leaf. That is the form every offline gate scored and the only form whose dose is
calibrated. **Consequence, stated in advance: a NO-GO here is a NO-GO for the validated rule at the
validated dose, not a proof that a leaf-level application must also fail.**

15,000 games total, all local, ≤ 6 workers, `systemd-run --user --scope`, waited in-turn.

### PRIMARY — dr. lulu bursty, N = 3,000 paired seeds 20000..22999 (6,000 games)

| metric | BASE [95 % CI] | TRT [95 % CI] | paired diff (trt − base) [95 % CI] |
|---|---|---|---|
| **dies-ahead** | **12.13 % [11.00, 13.30]** (364) | **11.33 % [10.23, 12.47]** (340) | **−0.800 pp [−2.200, +0.600]** |
| **clear** | **80.67 % [79.23, 82.03]** (2,420) | **80.97 % [79.57, 82.37]** (2,429) | **+0.300 pp [−1.301, +1.867]** |
| topout | 13.80 % [12.57, 15.03] (414) | 12.87 % [11.70, 14.10] (386) | −0.933 pp [−2.334, +0.467] |
| stall | 5.53 % [4.70, 6.40] (166) | 6.17 % [5.33, 7.10] (185) | +0.633 pp [−0.433, +1.701] |
| bad-ends (topout + stall) | 19.33 % (580) | 19.03 % (571) | −0.300 pp [−1.867, +1.301] |
| mean pills | 155.41 [153.21, 157.73] | 154.91 [152.63, 157.27] | −0.500 [−2.651, +1.663] |
| pills, both-clear (n = 2,119) | 136.71 | 136.31 | −0.403 [−2.217, +1.476] |

**McNemar exact two-sided:** dies-ahead **p = 0.2793** (238 rescued / 214 newly caused); clear
**p = 0.7462** (310 / 301); topout p = 0.2110; stall p = 0.2759.

**Realised flip rate 1.78 % of plies** (offline predicted 2.12 % target / 1.65 % cleared — the dose
transferred exactly). 2,473 / 3,000 games touched; **760 pairs identical**; **611 discordant clear
outcomes**; **452 discordant dies-ahead outcomes**.

### BREAKAGE — measured explicitly, and it is not near zero

| | count |
|---|---|
| **clears BROKEN** (base cleared, trt did not) | **301** = 12.4 % of the base arm's clears |
| clears RESCUED (base did not clear, trt did) | 310 |
| **net clears** | **+9** (p = 0.7462) |
| dies-ahead RESCUED | 238 |
| **dies-ahead NEWLY CAUSED** | **214** |
| **net dies-ahead** | **+24** (p = 0.2793) |

Of the 364 base dies-ahead games, **only 126 stayed dies-ahead.**

**The structural law that closed the always-on penalty family — *an always-on change loses at
population scale unless breakage is essentially zero* — is not satisfied. Breakage is 301 games.
It is survivable here only because an almost identical number of coin-flips landed the other
way.**

**Churn is the real story.** A 1.78 % per-ply flip reshuffles **22.5 % of game outcomes**
(675 / 3,000): only 167 of 414 base topouts stayed topouts; only 39 of 166 stalls stayed stalls.

**Consequence for the endpoint itself:** with 611 discordant clears the paired 95 % CI half-width
on clear rate is **± 1.58 pp**, so **the pre-registered ± 1.0 pp non-inferiority margin was
unreachable at N = 3,000 by construction.** Any future arm at this flip rate needs **N ≳ 4,500**
paired seeds merely to be *able* to pass the clear-rate gate.

**N3 trend, flagged though it did not fire:** of the 28 net topouts avoided, 19 reappeared as
300-pill **stalls**. Net bad-ends still fell (−0.30 pp), so N3 did not fire — but that is exactly
the mechanism N3 exists to catch. *(Pair-level, the transitions are topout→stall 35 vs stall→topout
29, and the bulk of the net stall rise is clear→stall 111 vs stall→clear 98 — so the "68 %
conversion" framing is net arithmetic, not a pair-level fact.)*

### NET POPULATION EFFECT — essentially zero, bought with 611 coin flips

Uniform population sampling prices breakage at the true ratio automatically (this is why the
prereg mandated it).

- net clears = 310 − 301 = **+9 games**
- net dies-ahead = 238 − 214 = **+24 games**
- at the census ratio 9,576 clears : 1,501 dies-ahead = **6.4 : 1**
- **net in clear-equivalents = 9 + 24/6.4 = +12.75 per 3,000 games = +0.43 % of one game each**

Every component's CI comfortably spans zero.

### SECONDARY — generic drip, N = 1,500 paired seeds 20000..21499. NO VERDICT AUTHORITY.

| metric | BASE | TRT | diff [95 % CI] |
|---|---|---|---|
| dies-ahead | 2.53 % (38) | 1.80 % (27) | −0.733 pp [−1.667, +0.200] |
| clear | 94.93 % (1,424) | 95.73 % (1,436) | +0.800 pp [−0.535, +2.133] |
| bad-ends | 5.07 % (76) | 4.27 % (64) | −0.800 pp [−2.133, +0.535] |
| mean pills | 129.82 | 128.81 | −1.009 [−3.453, +1.440] |

McNemar dies-ahead p = 0.1524 (30 / 19); clear p = 0.2807 (58 / 46). Flip 1.66 %.

Same sign, same magnitude, same non-significance. Two things this buys: the term is **not
lulu-specific** and does not read the volley schedule (corroborating L3/B4); and it is equally
unable to move the endpoint there. *(Had it carried verdict authority it would also read NO_GO.)*

### THE CONTROL THAT DECIDES THE INTERPRETATION

Null arm = the identical LUT with each feature's table **row-permuted** (rng 20260810): same 288
int12 entries, same value multiset, same silicon cost, **holdout AUC 0.4746** vs the fitted
model's 0.7220. Scaled by k, chosen **on the sealed holdout's 32-sibling layer** to match the
fitted arm's 2.12 % target-class flip, **using no rollout outcome at all**.

| arm | ply-flip | dies-ahead vs base | clear vs base | discordant clears |
|---|---|---|---|---|
| **fitted** (AUC 0.7220) | **1.78 %** | **−0.80 pp [−2.20, +0.60]** | +0.30 pp [−1.30, +1.87] | 611 |
| **dose-matched null** (AUC 0.4746, k = 0.2) | **1.96 %** | **−0.53 pp [−1.93, +0.87]** | +0.17 pp [−1.43, +1.83] | 657 |
| *value-matched null (k = 1, 4.09× dose — BIASED)* | *7.28 %* | *+1.13 pp [−0.40, +2.77]* | *−2.00 pp [−3.87, −0.10]* | *854* |

**Difference-in-differences (fitted − dose-matched null): −0.27 pp [−1.73, +1.13], only 60.5 % of
bootstrap reps negative.** A head-to-head McNemar on dies-ahead between the two arms gives
**p = 0.7533**.

The null was if anything **1.10× over-dosed**, which flatters the fitted arm, and it still cannot
separate.

**I report my own first control as defective:** the un-scaled k = 1 null flips 4.09× the fitted
dose, so its favourable DiD (−1.93 pp [−3.53, −0.33]) is **biased in favour of the fitted arm and
must not be quoted as evidence.** It does establish something real: a 4×-overdosed random term
**raises** dies-ahead by 1.13 pp and **costs 2.00 pp of clear rate (CI excludes 0)**. Churn is not
free — it is just not *directed* by this model.

### IDENTITY AND LIVENESS GATES — all pass, and all can fail

**GATE 0 — provenance.** Re-scoring the sealed 104,951-row / 657-game holdout through the deployed
uint8 → int12 → int16 path reproduces the shippable lane's reported numbers exactly: AUC
**0.7219890** (reported 0.7220), `A_champ` **0.6645043** (0.6645), argmax-flip **2.1178 % /
1.6524 %** (2.12 / 1.65), |Δ|max 52, sd 9.594, int16 safe. **Four killed mutants all fire:**
sign-flipped tables 0.2780; row-shuffled 0.4746; feature-permuted 0.4160; reversed enumeration
order makes the base argmax disagree with the corpus's stored action on 36.95 % of decisions.

**GATE 1 — OFF-identity in both directions, 12 seeds, both regimes.**
- **G1a OFF:** with Delta zeroed, the arm reproduces **both** `pressure_rig.play()` **and**
  `p0_ab.play_one(forced=False)` on res/pills/garbage/dies_ahead — 12/12 lulu, 12/12 drip — **and
  the identical per-ply action sequence**, 12/12 and 12/12. *(Outcome equality alone could hide a
  compensating divergence.)*
- **G1b — the mutant that makes G1a capable of failing:** zero Delta, but the argmax scans the
  champion's enumeration order **reversed**. That changes nothing except tie resolution (~36 % of
  decisions) and it **breaks G1a on 12/12 lulu, 11/12 drip.** This is the specific check that
  distinguishes "correctly wired and inert" from "never consulted".
- **G1c:** sign-flipped tables break identity 12/12 and 10/12; row-shuffled 12/12 and 12/12.
- **G1d liveness:** treatment differs on 12/12 lulu and 11/12 drip; flips 63/2,438 and 34/1,727.
- **G1e prune exactness:** the exact-bound pruning yields byte-identical action sequences to
  scoring all 32 candidates, 12/12 both regimes.

**Three further checks that could have failed and did not:** the BASE arm on the disjoint seed
block reproduces the 12,000-seed census composition with **every census value inside the base
arm's 95 % CI**; the 527 games where the term never flipped a ply agree on **every field**
(`must_be_zero: true`); base re-derivation inside the control runs, 25 seeds from scratch, **0
mismatches**.

### VERDICT — the pre-registered rule applied verbatim

> ## **NO_GO**
>
> - **N1 FIRES** — clear-rate non-inferiority: upper 95 % bound on `(clear_base − clear_trt)` =
>   **+1.30 pp ≥ +1.00 pp**. *(The point estimate favours the treatment by 0.30 pp; the gate fails
>   on **WIDTH** — 611 discordant clears make the CI ± 1.58 pp.)*
> - **N2 FIRES** — dies-ahead 95 % CI **[−2.200, +0.600] pp includes 0**.
> - **N2 FIRES** — McNemar exact two-sided **p = 0.2793 ≥ 0.05**.
> - N3 does not fire (bad-ends fell 0.30 pp) — but see the stall-conversion flag above.
> - N4 does not fire — all identity and liveness gates pass.

**Power, for the record and NOT a re-opening:** at the observed point estimates the gates would
have needed **N ≈ 9,044** (dies-ahead McNemar) and **N ≈ 4,453** (clear non-inferiority). The
dose-matched null says more N would most likely buy a precisely-measured null.

---

## 8. THE ADVERSARIAL VERDICT — verbatim

An independent pass was run whose job was to **break** this result. Six attacks. **Five CLEARED
(the methodology held), one REFUTES (the effect is dead).** No attack returned WEAKENS.

### Attack 1 — "Verdict rule genuinely pre-registered BEFORE results, and applied as written" → **CLEARED**

> Timeline from git: parent prereg `PREREG_STAGE2.md` @ `b9725fc` committed 2026-08-10 07:15:44
> −0400, before any corpus or model existed; `PREREG_SHIPPABLE.md` @ `2d4d5d0` 09:31:27 before any
> fitting; `PREREG_ROLLOUT.md` @ `f5f58f0` 10:13:46. The A/B scope did not launch until 10:24 and
> `ab_lulu.jsonl` finished 12:01. So the rule predates every game.
>
> THE ONE REAL RED FLAG AND ITS RESOLUTION: `PREREG_ROLLOUT.md` has mtime 13:39, i.e. it WAS edited
> after the lulu primary read out at 12:01 — exactly the 'prereg edited mid-flight' hazard. I
> diffed it. The 150-line version committed at `f5f58f0` is a BYTE-EXACT STRICT PREFIX of the final
> 199-line file (verified programmatically: `b[:len(a)]==a`, no divergence within common length).
> All 49 added lines are appends to the §6 deviation log declaring two null-control arms explicitly
> marked 'NO VERDICT AUTHORITY'. Mechanical deletion counts across all three preregs since their
> first commits: PREREG_STAGE2 0 deletions / 74 additions; PREREG_SHIPPABLE 0 / 80; PREREG_ROLLOUT
> 0 / 49. §4 (GO requires DA CI excluding 0 AND McNemar p<0.05; co-primary clear-rate upper bound
> < +1.0pp) is untouched.
>
> APPLIED AS WRITTEN: I re-derived the verdict from raw JSONL with my own bootstrap and my own
> exact-binomial McNemar, not their code. N1 clear_loss_upper = +1.301pp >= +1.00 → FIRES. N2 DA CI
> [-2.200,+0.600] includes 0 → FIRES; McNemar p=0.2793 >= 0.05 → FIRES. N3 bad-ends fell -0.300pp →
> does not fire. Verdict NO_GO, identical to reported.
>
> AND THE RULE CAN EMIT GO — I ran `rollout/test_verdict.py`: 'big DA win, clear up' → GO; 'big DA
> win, clear -4pp' → NO_GO; null → NO_GO; DA worse → NO_GO; N=800 → INCONCLUSIVE. A rule that could
> only say NO_GO would be vacuous; this one is mutant-tested and hand-checks McNemar 238/214 →
> 0.2793, matching my independent value.

### Attack 2 — "OFF-identity gate real, or vacuously passing" → **CLEARED**

> NOT VACUOUS, and I proved it two ways rather than reading the JSON.
>
> WHAT IT COMPARES: `gate1_identity.py:55-66 ref_row()` plays each seed through TWO independent
> pre-existing harnesses — `pressure_rig.play(seed)` and `p0_ab.play_one(seed, forced=False)` — and
> asserts they agree with each other before using either as reference. G1a then requires the
> Delta-zeroed arm to match on res/pills/garbage/dies_ahead AND (G1a-strict) to reproduce the
> identical PER-PLY ACTION SEQUENCE, since outcome equality alone could hide compensating
> divergence. It also asserts `arm.stats['flips']==0`.
>
> I RE-RAN IT LIVE (not stale JSON): systemd-run --user --scope, pinned venv, `gate1_identity.py
> --seeds 3` → '[lulu] G1a OFF-identity 3/3 (action-seq 3/3) G1b tiebreak-mutant differs 3 ... PASS'
> and the same for drip. Reproduced.
>
> WHAT WRONG INPUT IT CATCHES: G1b is the answer — zero Delta but the argmax scans the champion
> enumeration order REVERSED. That changes NOTHING except tie resolution, and the holdout tie rate
> is 35.8-37.2%. It breaks G1a 12/12 lulu, 11/12 drip (3/3 in my re-run). G1c sign-flipped tables
> break it 12/12 and 10/12; row-shuffled 12/12 and 12/12.
>
> MY OWN NOVEL MUTANT (one the lane never ran) on the SEALED 32-sibling holdout layer: zeroed
> tables give EXACTLY 0.0000% argmax flips and |Delta|max = 0 on both fail (n=8,405) and ctrl
> (n=9,199) — so OFF is exactly inert. Setting exactly ONE int12 table entry to 1 perturbs 22,084
> (d_spawn_h idx13) and 30,267 (a_topout_dist idx5) candidate Delta cells and produces real argmax
> flips (0.0238%, 0.0238%, 0.0761%). So the Delta is genuinely consulted per candidate at
> single-entry granularity — the gate is sensitive to a one-bit change, not merely to gross ones.
>
> Also non-vacuous downstream: the 527 games where the term never flipped a ply have base-vs-trt DA
> difference EXACTLY 0.

### Attack 3 — "Dies-ahead improvement inside noise / garbage-channel variance between identical arms" → **REFUTES**

> THE IMPROVEMENT IS INSIDE NOISE — I recomputed everything from raw JSONL with my own bootstrap
> (B=2000, rng 20260810) and my own exact-binomial McNemar, reproducing their numbers to the digit.
>
> lulu N=3,000: DA base 12.13% (364) vs trt 11.33% (340), paired -0.800pp [-2.200,+0.600], McNemar
> p=0.2793 on 452 discordant (238 rescued / 214 caused). With 452 discordant pairs the SD of the
> paired difference is sqrt(452)/3000 = 0.709pp, so the observed -0.800pp is 1.13 SIGMA. MDE at 80%
> power needs |b-c| ~ 60 pairs = 1.98pp; observed |238-214| = 24.
>
> IDENTICAL-ARM VARIANCE IS EXACTLY ZERO HERE, which I checked rather than assumed — this rig is
> deterministic in the seed, so the memory's '37.2% winner flip between IDENTICAL evals' (a VS-mode
> phenomenon) does not apply. Evidence: base rows re-derived from scratch in two separate control
> processes hours later reproduce the stored base rows with 0 mismatches on 25 seeds each, my own
> gate1 re-run reproduced the reference 3/3, and untouched games diff exactly 0. So all churn is
> caused by the intervention.
>
> THE CORRECT NOISE MODEL IS PERTURBATION CHURN, AND THE LANE'S OWN CONTROL KILLS THE EFFECT. I
> computed the transition matrix: 675 of 3,000 games (22.5%) changed outcome from a 1.78% per-ply
> flip. Only 167 of 414 base topouts stayed topouts; only 39 of 166 stalls stayed stalls. Against
> the DOSE-MATCHED LABEL-BLIND null (row-permuted tables, holdout AUC 0.4746, k=0.2 chosen offline
> on the sealed sibling layer to match the 2.12% flip bar using no rollout outcome): null DA
> -0.533pp [-1.933,+0.867] vs fitted -0.800pp; DiD -0.267pp [-1.733,+1.133], only 60.5% of reps
> negative. I added a head-to-head test the lane did not run: fitted-vs-null McNemar on DA, 252 vs
> 244, p=0.7533. The fitted model is statistically indistinguishable from a random permutation of
> its own table values at the same dose. Realised flip 1.961% (null) vs 1.778% (fitted) — the null
> was if anything 1.10x OVER-dosed, which flatters the fitted arm, and it still cannot separate.
>
> The 4x-overdosed k=1 null does move things (DA +1.133pp, clear -2.000pp [-3.867,-0.099] excluding
> 0) — proving churn is genuinely harmful at scale and that the control is capable of showing an
> effect. It just is not directed by this model.

### Attack 4 — "Breakage honestly counted at the right population ratio" → **CLEARED**

> COUNTED HONESTLY AND AT THE TRUE RATIO; I recomputed it independently. lulu N=3,000: BREAKAGE
> (base cleared, trt did not) = 301; RESCUE = 310; net clears +9. DA rescued 238 / newly caused 214,
> net +24. Breakage is 12.44% of the base arm's 2,420 clears and 10.03% of the whole population.
>
> THE RATIO IS RIGHT BECAUSE THE SAMPLE IS A POPULATION SAMPLE, NOT A FAILURE-ENRICHED ONE — this is
> the exact error that produced the always-on penalty family's bogus net number, and it was avoided
> by design (PREREG_ROLLOUT §5, fixed before the run). I verified the sampling: base arm on the
> disjoint block 20000..22999 reads clear 80.67%, topout 13.80%, stall 5.53%, DA 12.13% against the
> 12,000-seed lulu census 79.80% / 14.05% / 6.15% / 12.51% — every census value inside the base
> arm's 95% CI. So no re-weighting is applied or needed; breakage is priced automatically.
>
> Against the STRUCTURAL LAW ('essentially zero breakage or it loses at population scale'), 301
> broken clears is emphatically not zero, and the lane says so in its own words rather than burying
> it. Census ratio 9,576:1,501 = 6.38:1; net clear-equivalents = 9 + 24/6.38 = +12.76 per 3,000
> games, with every component's CI spanning zero.
>
> ONE SMALL OVER-ATTRIBUTION I FOUND (does not change the verdict): the narrative 'of the 28
> topouts avoided, 19 reappeared as 300-pill stalls — 68% converted' is NET arithmetic, not a
> pair-level fact. Pair-level transitions are topout→stall 35 vs stall→topout 29 (net +6), while the
> bulk of the net stall rise is clear→stall 111 vs stall→clear 98 (net +13). The N3 risk is real but
> is less attributable to topout conversion than stated. It errs toward flagging a risk, not hiding
> one, and N3 correctly did not fire.

### Attack 5 — "Was the rollout run on the quantised model or the float version" → **CLEARED**

> THE ROLLOUT RAN THE QUANTISED INTEGER ARTIFACT, and I verified this at three levels instead of
> taking the claim.
>
> ARTIFACT: `shippable/out/RECOMMENDED_lut64.json` holds 8 tables of sizes [9,60,44,17,41,49,15,53]
> = 288 entries; I checked every value is an integer and inside int12 [-2048,2047] (mins/maxes
> -22..+19). Summed extremes give Delta ∈ [-67,+60], span exactly 127 — which is precisely the
> constant the exact prune bound uses, so the two are consistent.
>
> CODE PATH: `arm_lut.py:123-140` is `q = int(np.clip(np.rint(x[j]*scale),0,255))`, saturate to
> table size, `acc += int(t[q])`. No float anywhere in Delta. `Arm.choose` does `adj[slot] =
> vals[slot] - delta_from_feats(...)`, an integer root value minus an integer Delta. `run_ab.py:39`
> loads `AL.load_recommended()`, which reads `table_int12` — not the float pickle, not the round-1
> model.
>
> EQUIVALENCE TO THE QUOTED OFFLINE NUMBERS: gate0_provenance re-scored the sealed 104,951-row /
> 657-game holdout THROUGH THAT INTEGER PATH and got AUC 0.7219890 (reported 0.7220), champ
> 0.6645043 (0.6645), flip 0.02117787 target / 0.01652354 cleared (2.12% / 1.65%). I reproduced the
> flip numbers myself from the npz sibling layer: 2.1178% (fail, n=8,405) and 1.6524% (ctrl,
> n=9,199).
>
> QUANTISATION IS NOT COSMETIC — I tested it. Replacing the int lookup with a float, linearly-
> interpolated Delta changes the argmax on 0.1309% (fail) and 0.3153% (ctrl) of decisions. So an
> int-vs-float substitution would have been detectable, and the rolled-out arm's flip rate matches
> the INT computation to 4 decimal places.

### Attack 6 — "Could the corpus and the rollout share seeds (in-sample result)" → **CLEARED**

> DISJOINT, MEASURED FROM THE ACTUAL SEED ARRAYS rather than from the claim. I loaded all four
> corpus npz files and unioned every integer seed array. Union = 3,136 unique seeds, min 4, max
> 12,000. Rollout lulu = 20000..22999 (3,000 seeds, verified from `ab_lulu.jsonl`); rollout drip =
> 20000..21499. INTERSECTION WITH THE CORPUS = 0 in both cases.
>
> COROLLARY THAT STRENGTHENS THE REFUTATION: the arm tested is the CONTAMINATION-FLAGGED round-2
> model, whose eligible feature set was corrected after a holdout-scored diagnostic ranked BURIED
> first. That contamination inflates its OFFLINE AUC only; the rollout seeds are disjoint from
> everything used to fit or select. So the programme rolled out its most optimistically-biased
> candidate on clean seeds and it still failed — **contamination cannot be invoked to rescue the
> result.**

### Overall adversarial verdict: **REFUTED**

> Stage 2 has NOT produced a real, shippable improvement — and, importantly, the lane already says
> so. My job was to break the result; what I found is that the process is sound and the improvement
> claim is dead.
>
> WHAT SURVIVED EVERY ATTACK (the methodology): the verdict rule was committed at 07:15:44 before
> any corpus, model or game existed, and the 150-line rollout prereg is a byte-exact strict prefix
> of the final file — zero deleted lines across all three preregs, all edits append-only deviation
> entries with 'NO VERDICT AUTHORITY'. The verdict function is mutant-tested and demonstrably CAN
> emit GO. The OFF-identity gate compares against two independent harnesses on outcomes AND full
> per-ply action sequences, and dies to a mutant that changes nothing but tie resolution; I re-ran
> it live and added my own single-entry-table mutant that it also detects. The rolled-out arm is the
> genuine 288-entry int12 artifact, whose integer path reproduces the quoted offline AUC and flip
> rates to four decimals, and float-vs-int would have been detectable. Corpus and rollout seeds
> intersect in exactly 0 elements. Breakage is counted at the true population ratio because the
> sample is uniform, verified against the census.
>
> WHAT IS REFUTED (the effect): dies-ahead moved -0.800pp with a 95% CI of [-2.200,+0.600] and
> McNemar p=0.2793 — 1.13 sigma, against an MDE of 1.98pp. The killer is not the width but the
> positive control: a dose-matched, LABEL-BLIND arm (the same tables row-permuted, offline AUC
> 0.4746) moved dies-ahead -0.533pp with the same churn. Difference-in-differences -0.267pp
> [-1.733,+1.133], 60.5% of reps negative, and a head-to-head McNemar I ran myself gives p=0.7533. A
> +0.0575 offline AUC edge with 100% of bootstrap reps positive produced a rollout effect
> indistinguishable from randomly shuffling the model's own numbers. **That is a refutation, not
> mere absence of power.**
>
> The mechanism is now measured: a 1.78% per-ply flip reshuffles 22.5% of game outcomes (675/3,000;
> only 167 of 414 base topouts stay topouts), and it breaks 301 clears while rescuing 310. The
> structural law's 'breakage essentially zero' is nowhere near satisfied. It also made the
> co-primary gate unpassable by construction — the clear-rate CI half-width is 1.61pp against a
> 1.0pp margin, so N1 fired on WIDTH, not on measured harm.
>
> TWO SCOPE LIMITS ON HOW FAR THE NO_GO REACHES, both declared in advance: the term was applied at
> the ROOT re-rank, not at every leaf as the silicon target requires (the leaf form is untested and
> no dose is calibrated for it), and the whole corpus sits at 79.80% clear rate, below the 96.9%
> label-quality screen. So this refutes the validated rule at the validated dose in the tested form;
> it does not prove no leaf-level term can work.
>
> The genuinely useful residue is negative-result infrastructure: the AUC→rollout bridge is now
> measured as broken for this class of term, every future candidate needs a dose-matched
> label-blind null (AUC + argmax-flip gates are provably insufficient — this arm cleared both by
> wide margins), and N>=4,500 paired seeds is a hard floor at this perturbation size. The honest
> report is a well-instrumented NO_GO, reported with the prominence a GO would have had.

---

## 9. IS IT ALL JUST `d_spawn_h`? — NO. And that is the wrong question now.

The mandate asked to lead with `d_spawn_h` **if it alone carries the result**. It does not — and
more importantly, **nothing carries the result**, so the question is downstream of a null. But the
evidence is worth stating precisely, because it determines what to do next.

### Against "stage 2 reduces to unclipping the spawn sensor"

1. **81 % of the entire ceiling gain is a nonlinear recombination of the champion's OWN 11 terms**
   (0.6645 → 0.7195). No new sensor. `d_spawn_h`'s marginal share is 13.7 %; the other 14
   candidates 5.5 %.
2. **Drop-column:** removing `d_spawn_h` from the 26 costs **+0.0009 [−0.0013, +0.0032]**, 77.5 % of
   reps positive. It is **redundant** given `b_spawn_prox` / `d_crit_cols` / MAXH / `x_hvar`.
3. **Permutation importance ranks it 8th of 26** (0.0060), behind BURIED, `d_gvuln_mass`, POLL,
   RDYEXT, VRDY, `e_escape_routes`, MAXH.
4. **Standalone it LOSES.** S0 = 0.6543 vs champion 0.6645; paired **−0.0102**, only 18.9 % of reps
   positive. **It fails B2.** Stage 1's 0.9290 came from last-K = 10 near-death windows and does
   *not* transfer to a full-decision corpus.
5. **The one true per-decision test kills it.** Progress-gated within-decision counterfactual:
   **+0.0256 [−0.0092, +0.0603]** vs the champion — CI includes 0, and **statistically tied with
   MAXH, a term the champion already has** — under a design biased *in its favour*.
6. **It is exhausted where it matters:** the champion already takes a minimum-spawn-lane action on
   **91.3 %** of the last 12 plies before a garbage topout, and its argmax-flip decays to **5.1 %**
   at `t_to_end ≤ 2`.

### In its favour, and it is real

- It is the single best **incremental** add over the champion's 11: **+0.0095 [+0.0041, +0.0147]**,
  100 % of reps positive, and it is chosen **first** by unguided greedy forward selection out of
  all 15 candidates.
- On near-death windows (stage 1's own slice, seeds disjoint) `d_spawn_h` **alone** reads 0.9640 vs
  the champion's 0.9443 — 61 % of the full model's gain by itself.
- **It is genuinely free in silicon** (§10), with a live killed-mutant correctness gate.

### THE ACTUAL BURIED ITEM — a gap, not a result

**`d_spawn_h` alone was NEVER rolled out.** `ls rollout/out/` shows exactly three arms ever run:
the fitted 8-feature LUT and two label-blind nulls.

The lane went from "S0 fails an offline AUC gate" straight to spending all 15,000 games on the
8-feature contaminated LUT. **That offline rejection was the wrong test for an additive term:** S0
was scored as a *standalone replacement ranker* against the whole depth-3 champion root value, not
in the form it would ship (`sco = champ − w·hinge(d_spawn_h)`).

Given that the 8-feature arm then produced a null indistinguishable from random churn, **the
cheapest, freest, lowest-churn arm in the lane remains untested at the only endpoint that
matters.** It should be run — not because the evidence predicts it wins (it predicts it will not)
— but because it costs ~3 hours on hardware already idle for it, the base arm is already on disk,
and *"the free sensor was never tried"* is an indefensible place to leave this lane.

---

## 10. THE SILICON PATH — what would have to change, and whether it fits

Measured, not estimated. Recorded here so the budget survives the null.

### The current leaf

`fpga/copro/LeafEval.sv` (md5 `5f06209642d1547e99cea077523662dc`) is **not a datapath** — it is a
~62-state FSM that sequentially walks a 128-cell board register file. Ten pure-integer terms,
16-bit wrapping:

```
sco = 5000 - 12*maxh - 20*holes - 90*toprisk - 150*spawn
          + 32*setup + 48*matched - 48*buried + 8*rdy_ext + 8*vrdy - 6*pollution
```

Nine constant multiplies in ONE registered pipeline stage (`S_DONE` latches → `S_DONE2` computes).
No division, no LUT nonlinearity. **In the deployed build the leaf runs 100 % in RTL**; the copro
6502 is pure control. *(Provenance trap: the `fpga/copro` copy carries OLD r47 constants; the
shipped copies under `dr_mario_rl/tmp/rtl_chain/ship/` carry the winner constants. Quote the ship
copy for any budget claim.)*

### The budget

| resource | measured | free |
|---|---|---|
| **Pocket ALM** (`nes_pocket.fit.summary`) | **18,262 / 18,480 (99 %)** | **218** |
| Pocket M10K | 50 / 308 | **258** (2.64 Mbit) |
| Pocket DSP | 15 / 66 | **51** |
| MiSTer ALM (`NES.fit.summary`) | 37,575 / 41,910 (90 %) | 4,335 |
| MiSTer DSP | 58 / 112 | 54 |

**Fitter-seed spread at fixed design: 194 ALMs** — comparable to the entire free pool. *Every
Pocket build is already a fit lottery; a zero-ALM change can still fail to fit.*

**Leaves per decision: 29,730** (instrumented golden, TOPK1 = 32 full, TOPK2 = 8, 4-pill stratified
third ply; constant across 15 boards spanning occupancy 13–76). **All-in clocks per leaf today:
median 1,625, p95 2,133.** Pocket copro 54.669 MHz × ~80 frames = 72.9 M clocks ⇒ **design number
+250 clocks/leaf** (Pocket-binding, ~20 % margin on a +310 floor). **Every 100 clocks added to the
leaf costs 4.1 % of the Pocket budget.**

**The lopsidedness is the key design fact: time is abundant, gates are not.** Hence strictly
sequential evaluation, one comparator + one adder + a cursor, parameters in block RAM. Never a
parallel ensemble.

### What would have to change to ship the pick (`S1br2_lut8_q64`)

**RTL — `LeafEval.sv`:**
1. **`S_COLWALK`, zero new cycles.** It already computes each column's height at the first-occupied
   cell. Capture `max(h₃,h₄)` for `d_spawn_h`, plus `e_escape_routes` / `a_topout_dist` /
   `x_hvar` accumulators, in that **same cycle**. *Measured: +0 cycles.*
2. **No new inputs needed for BURIED, RDYEXT, POLL, VRDY** — they are already-registered `*_p`
   values at the instant the combine runs. *(This is the round-2 finding: the pre-registered free
   list was wrong, and correcting it was worth more than any model-shape change.)*
3. **New: one 8-deep sequential Delta unit** — a cursor, an 8:1 feature mux, an 8-bit quantiser
   (`clip(round(x*scale), 0, 255)` then saturate to table length), one M10K read, one int add.
   **8 iterations = ~18 cycles.** Subtract from `sco` in `S_DONE2`.
4. **One M10K** holding 288 int12 entries = **3,456 bits = 0.34 of one block** (17 % of the 2-M10K
   bound; 258 blocks free).
5. **Zero multiplies, zero DSP, zero new whole-board passes.** The ten champion weights stay
   bit-identical, so **`Delta = 0` is an exact-identity control in silicon too.**

**Firmware:** the deployed 6502 is pure control and needs no per-leaf change. **But the parameters
MUST be host-uploadable.** `CoproDrMario.xlate` today maps only 128 board bytes + 4 colours +
DONE/col/orient + 2 tuck bytes. Extend it with a 432-byte parameter window. Otherwise every retune
is a `$readmemh` change resolved at **synthesis**, costing a full ~40-minute Quartus compile **and
re-rolling the Pocket fit lottery at 218 free ALMs with 194 ALMs of seed noise**
(`quartus_cdb --update_mif` is a documented no-op here).

### Does it fit?

**On time and memory: comfortably.** 18 of 250 clocks (7 %); 0.34 of 258 free M10K; 0 DSP of 51
free; 0 new board passes. `|Delta|max = 52`, int16-safe.

**On ALMs: probably, but this is an ESTIMATE, not a fit verdict.** Every ALM figure for the
recommended model is bounded above by the **measured** 91-ALM 256-stump sequential head
(`head_stump256s`: 91 ALMs, 1 M10K, 5,888 bits) — and this model is strictly smaller (no threshold
comparator, an 8-deep cursor instead of 256). It was **not synthesised inside `nes_pocket`.**

**Encouraging measured side-result:** folding `d_spawn_h` into the existing walk came out
**ALM-negative** in standalone sizing — `LeafEval_dsh` measured **7,031 / 7,042 / 7,387 ALMs**
against a baseline `LeafEval` of **7,444 / 7,465 / 7,473** (seed-noise floor 29 ALMs), with **+0
cycles** and a **948/948 correctness gate** whose deliberately-wrong cols-2/5 mutant agrees on only
183/948. Mechanism: adding terms pushed Quartus to move the combine's constant multiplies out of
ALM shift-add logic into **idle DSP blocks**. Pocket has 51 free DSPs, so that trade is favourable.

**Three standing hazards before any `.rbf`:**
1. **Standalone-with-virtual-pins sizing is a DELTA INSTRUMENT, not a fit verdict.** One full
   Pocket fit inside `nes_pocket` is required. *Do not stage an `.rbf` on the standalone number.*
2. **Timing is a separate gate and is untested.** MiSTer copro setup slack is +0.391 ns against a
   +0.10 ns ship bar, and this design has cliffed **+0.118 → −3.241 ns on a single change**.
   Moving combine multiplies into DSPs rewrites critical paths.
3. **Dead silicon may be reclaimable.** `CMD 6 (BASE)` / `CMD 7 (DELTA)` and ~10 FSM states are
   compiled into `LeafEval` but `USE_DELTA=False` in the deployed firmware, so **nothing issues
   them.** That is plausibly several hundred ALMs. *Nobody should conclude "the Pocket is full"
   until that is measured — it may be a larger win than anything the modelling phase produced.*

**None of this is needed now.** The arm is refused. The budget is recorded so the next candidate
starts from a measured box rather than re-deriving it.

---

## 11. GO / NO-GO, AND WHAT IS ACTUALLY WORTH KEEPING

## **NO-GO.**

Not "promising but underpowered". **Refuted by its own positive control.** Do not ship
`S1br2_lut8_q64`. Do not spend a Quartus compile, an `.rbf`, or a cart build on it.

### What is worth keeping — and it is not nothing

1. **The AUC→rollout bridge is now MEASURED as broken for this class of term.** An arm cleared B1,
   B2 and B3 by wide margins and delivered a rollout effect indistinguishable from a random
   permutation of its own numbers. **Every future candidate in this lane must be read against a
   dose-matched, label-blind null, not against the champion alone.** AUC + argmax-flip gates are
   provably insufficient. This is a permanent tightening of the project's standard and it was
   bought with 15,000 games.
2. **A hard N floor.** At a ~1.8 % ply-flip rate this rig churns ~20 % of game outcomes, so
   **N ≳ 4,500 paired seeds** is the floor merely to be *able* to pass the ±1.0 pp clear-rate gate,
   and **N ≈ 9,000** to resolve a sub-1 pp dies-ahead effect. The pre-registered N = 3,000 was too
   small for the perturbation size. That is now a measured number, not a guess.
3. **Where the lever probably is: the TIE SET.** 36–37 % of champion decisions have the top value
   tied among ≥ 2 legal actions and are currently decided by **enumeration order**, not by the
   evaluator. The flip already lands disproportionately there (3.80 % of tied decisions vs 1.13 %
   of decided ones). **A term restricted to the tie set would churn far less clear-game behaviour
   and would be testable at a feasible N.** A term that flips 1.8 % of *all* plies is a policy
   rewrite priced at 611 coin-flipped clears — the highest-breakage-risk shape this lane could have
   picked.
4. **The corrected free list.** SETUP / MATCHED / BURIED / RDYEXT / VRDY / POLL are already-
   registered combine operands and cost **nothing** to read. `PREREG_STAGE2` §8 was wrong to
   exclude them. Any successor should declare the corrected set in advance.
5. **The silicon budget, measured** (§10): 218 free Pocket ALMs, 258 free M10K, 51 free DSP,
   +250 clocks/leaf, 29,730 leaves/decision, and the fact that **`d_spawn_h` is free**.
6. **Reusable, gated instruments:** `gate0_provenance.py`, `gate1_identity.py` (with the tie-break
   mutant that makes it able to fail), `test_verdict.py` (mutant-tested, can emit GO),
   `calib_null.py` (blind dose matching on the sealed sibling layer), `analyse.py`.

### The four things worth doing next, in order

| P | item | action | cost |
|---|---|---|---|
| **P0** | **No calibration point exists for AUC → dies-ahead.** The lane spent 15,000 games without establishing that *any* evaluator improvement moves the endpoint. | Run an **ORACLE-CEILING ARM** under the unmodified verdict rule: fork the top-4 champion candidates at high-risk plies, continue with the real champion policy and real injection, pick the survivor-with-virus-progress; play the champion elsewhere. This measures the **maximum** dies-ahead reduction reachable by ANY root re-ranker, in endpoint units. **Decisive both ways:** if the oracle also reads NO_GO, root re-ranking is structurally dead and no leaf evaluator should be funded for dies-ahead — close the lane on evidence. If it reads GO at −2 to −3 pp, the AUC gap becomes priceable for the first time. | ~18,000 game-equivalents, ~8.6 h Hetzner behind the queue |
| **P0** | **The 301 broken clears are UNDIAGNOSABLE.** Per-game records log `flips` as a bare integer — no ply index, no `t_to_end`, no tie-vs-decided tag. 15,000 games produced a NO_GO with zero mechanism. | Add per-ply flip provenance to `arm_lut.py` and re-run the treatment arm on the same 3,000 seeds; attribute every discordant outcome to its **first** divergent ply. **Make this mandatory for every future arm.** | ~1.4 h + ~30 lines |
| **P0** | **The whole regime rests on a 3-match, 59-volley fit** with **0/59** lock cross-check and a **±7.6 pp** CI on `p(volley \| clear 4-6)`. Base dies-ahead is 12.13 % under lulu vs 2.53 % under drip — a 4.8× swing produced purely by this model. | Run the BASE arm at both CI bounds (0.331 / 0.484), same seeds, and report base dies-ahead, clear rate and mechanism split. If base DA moves by more than the 1.4 pp endpoint CI half-width, the prize size, the power calculation **and the verdict** are parameter-artifacts and must carry a sensitivity range. Separately, re-derive the 59 volleys **with** the lock cross-check applied to the other player. | ~2–3 h compute + ~2 h re-analysis |
| **P1** | **`d_spawn_h` alone was never rolled out** (§9). | Roll out `sco = champ − w·hinge(d_spawn_h)` on the same 3,000 lulu seeds at **two doses** (Δ_sd = 2 and 10) against a dose-matched label-blind null at each. Expect a null; run it anyway — it converts "never tried" into a number. | ~2.8 h local, zero new instrument work |

**Also standing, cheap, and important to state rather than fix:** the shipping form (leaf-applied
Delta) was never tested — it changes which 8 ply-2 children survive TOPK2 pruning, i.e. it is a
*search-shaping* change, not a rank-1 perturbation. Quantify the divergence **offline at zero
rollout cost** before any further silicon work: if the leaf-applied and root-applied policies agree
> 95 % of the time, this NO_GO transfers and the shippable class can be closed on this evidence.

---

## 12. THE HONEST SUMMARY, FOR SEPTEMBER

The champion still dies while ahead 12.1 % of the time under dr. lulu's fitted pressure, and
**stage 2 did not change that.** The evaluator is genuinely improvable *as a ranker* — the ceiling
is +0.068 AUC and ~96 % of it sits in an 8-feature model that costs 18 of 250 clocks — but ranking
better on a corpus of broadcast game-outcome labels **did not translate into surviving more
games.**

The single most useful thing learned is that **this rig is chaotic in the action sequence**:
perturbing 1.8 % of plies reshuffles 22.5 % of game outcomes. Any always-on evaluator change of a
testable size is, at population scale, a coin-flip generator — which is the structural law from the
always-on penalty family, now confirmed on a completely different intervention. **The next
candidate should be a term that fires only where the champion is currently indifferent**, i.e. on
the 36 % of decisions the evaluator does not actually decide. That is the one shape with a large
surface, low clear-game contact, and a feasible N.

Two scope limits, declared in advance, on how far this NO-GO reaches:
- **Form.** The term was applied at the root re-rank. A leaf-level application is untested and no
  dose is calibrated for it.
- **Regime.** The corpus sits at **79.80 % clear rate**, below the 96.9 % screen, and the rig has
  **no opponent board** and fires garbage when *we* clear — the causal inverse of a real VS match.
  **No claim about beating dr. lulu follows from this lane.**

---

### ARTIFACT INDEX

| what | where |
|---|---|
| Pre-registrations | `experiments/eval47/stage2/PREREG_STAGE2.md` @ `b9725fc` · `PREREG_SHIPPABLE.md` @ `2d4d5d0` · `rollout/PREREG_ROLLOUT.md` @ `f5f58f0` |
| Corpus (550,115 decisions / 3,136 games) | `experiments/eval47/stage2/results/s2lulu_*.npz`, `s2feat_local.npz` |
| Corpus builder + features + null | `stage2/build_s2_corpus.py`, `s2_features.py`, `s2_a3_null.py` |
| Ceiling | `stage2/ceiling_{fit,probe,regime,attrib,counterfactual}.py` → `tmp/stage2_ceiling/*.json` |
| Shippable | `stage2/PREREG_SHIPPABLE.md`, `stage2/shippable/{s2_shippable,models,b1_null,flip_anatomy,round2}.py` → `shippable/out/*.json` |
| Deployed artifact | `stage2/shippable/out/RECOMMENDED_lut64.json` (288 int12 entries, 3,456 bits) |
| Rollout | `stage2/rollout/{run_ab,arm_lut,analyse,gate0_provenance,gate1_identity,calib_null,test_verdict}.py` |
| Rollout data | `rollout/out/{ab_lulu,ab_drip,ctrl_lulu_shuf,ctrl_lulu_shuf_k02}.jsonl` |
| Rollout results | `rollout/out/{rollout_result,addendum_lulu,calib_null,gate0_provenance,gate1_identity}.json` |
| Silicon budget | `tmp/silicon_budget/` (Verilated cycle rig, 6 candidate heads, sizing runs, `count_leaves.py`) |
| Census | `experiments/eval47/jointdig/results_hetzner/lulu_census.jsonl` (12,000 games) |

**MANDATORY CAVEAT, attached to every number in this document:**
> Corpus `s2lulu`: generating policy = shipped champion (bit-exact), environment = dr. lulu fitted
> bursty pressure, clear rate **79.80 % — BELOW the 96.9 % label-quality screen**. Labels are game
> outcomes broadcast onto decisions; no counterfactual attribution.

**SECOND CAVEAT:** the arm that was rolled out is **round-2 / CONTAMINATION-FLAGGED**
(`PREREG_SHIPPABLE` deviation 7). Its offline AUC is optimistically biased. The rollout endpoint is
unaffected (seeds disjoint from everything used to fit or select) — but the *reason this arm was
tested rather than the clean round-1 arm* is contaminated.
