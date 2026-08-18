# PREREG — fork-free N=9,000 endpoint A/B for the distilled θ-gate term

Registered 2026-08-18, before any A/B game. Frozen artifacts:
`results_distill/frozen_gate_model.pkl` (sha256 `a8d31602ccb7b3205ce2c8863ac721ea…`)
and `results_distill/frozen_gate_threshold.json`.

**REGISTERED RECOMMENDATION: DO NOT LAUNCH.** The power and operating-point
analysis below was run *before* the threshold was frozen and *before* any seed of
the A/B was played. It says the experiment as approved cannot answer the question
it was approved to answer. Registering that, with the artifact that would have
been launched, is the point of writing this down.

---

## 1. What was approved

A paired N=9,000 endpoint A/B of a distilled term that fires only in the top
~0.5–1% tail of a classifier for H12's own dose gate (`margin_sum >= 3`).
Primary dies-ahead, co-primary clear, dose-matched shuffled-label mutant, dose
anchored on full-N flip rates, seed block disjoint from every registered range.
Fork-free, so ~30 core-h / ~3 h wall / $0.

## 2. The frozen candidate (registered even though the recommendation is not to run)

Fitted on ALL 838 banked seeds (60000–60499 pilot + 62000–62337 extension),
which are disjoint from any A/B block, so no A/B seed informs the model.

* model: `StandardScaler + LogisticRegression(max_iter=5000)`, 51 features
  (27 static incl. `d_champ_val`, 5 event context, 8 temporal candidate deltas,
  11 temporal running-state context)
* target: `margin_sum >= 3` — H12's own θ gate, not a proxy
* frozen cutoffs: top-0.5% ⇒ score ≥ **0.36504052**; top-1.0% ⇒ ≥ **0.33719365**

No tuning after launch. Had it launched, these bytes decide every flip.

## 3. Why not to launch — two independent blockers

### 3a. The SHIPPABLE model is HARMFUL, not merely weak

Held-out operating points (fit on train seeds, evaluated on held-out seeds).
Reference: a random alternative has mean margin **−0.51** and is ≤ −3 in
**15.4%** of cases.

| model | AUC | dose | precision(margin≥3) | mean margin | % margin ≤ −3 |
|---|---|---|---|---|---|
| **logit** | 0.7476 | 0.5% | 0.356 | **−1.96** | **37.8%** |
| **logit** | 0.7476 | 1.0% | 0.374 | **−1.45** | **35.2%** |
| **logit** | 0.7476 | 2.0% | 0.319 | **−1.68** | **36.8%** |
| gbm | 0.7578 | 0.5% | 0.356 | +1.04 | 26.7% |
| gbm | 0.7578 | 1.0% | 0.308 | +0.10 | 28.6% |
| gbm | 0.7578 | 2.0% | 0.275 | −0.28 | 30.8% |

The logistic model — **the only silicon-feasible shape**, and the one whose
near-equal AUC I cited as evidence a linear term would do — has **negative mean
margin at every dose** and more than **doubles** the rate of picking a board that
is ≥3 *worse* (35–38% vs a 15.4% base rate). Its confident picks are
systematically bad. Deploying it would be expected to *harm* the endpoint.

The GBM's tail is benign, but a boosted ensemble is not the shippable artifact,
which is what makes 3b decisive rather than academic.

### 3b. Even the benign (GBM) arm is ~8× below the detection floor

Effective dose, held-out, versus H12's certified 2.74 accepted flips/game at
margin ≥ 3 by construction:

| dose | flips/game | precision | E[margin]/game | vs H12's effective dose |
|---|---|---|---|---|
| 0.5% | 0.179 | 0.356 | +0.187 | **2.3%** |
| 1.0% | 0.363 | 0.308 | +0.036 | 4.1% |
| 2.0% | 0.725 | 0.275 | −0.203 | 7.3% |
| 8.2% (H12's own dose) | 2.988 | 0.253 | −1.757 | 27.6% |

Only the 0.5% and 1.0% doses have positive expected margin at all, and 0.5%
carries **2.3% of H12's selection-quality-weighted dose**. H12 itself moved
dies-ahead −4.78pp. Assuming effect scales roughly with dose × selection quality
— crude, but the arms share endpoint and machinery, so it is a fair first-order
estimate — the expected movement is **≈0.11pp**.

MDE at N=9,000 paired (McNemar-style, 80% power, α=0.05):

| endpoint | SE | MDE |
|---|---|---|
| dies-ahead (discordance ≈0.08) | 0.298pp | **0.84pp** |
| clear (discordance ≈0.12) | 0.365pp | **1.02pp** |

Expected ≈0.11pp against an MDE of 0.84pp: **underpowered by ~7.6×**. Detecting
it would need N ≈ 525,000 paired seeds (~1,750 core-h even fork-free). Raising
the dose to buy power moves the mean margin negative — the knob trades the
effect's *sign* for its size.

A null here would be **guaranteed by design**, not informative. This project's
own standard is that a check which cannot fail is not a check; the symmetric
rule is that an experiment which cannot detect is not an experiment.

## 4. The methodological finding, which is the durable part

**AUC misled about deployability three separate times in this lane**, each time
in a different costume:

1. Phase 1: a signed-linear regression could not represent a V-shaped target;
   I read its failure as a property of the data ("magnitude is anti-learnable").
2. The retraction: a direct gate classifier scored AUC 0.73–0.76, and I inferred
   the gate was reproducible — true as ranking, false as a decision, because the
   top of the list is still mostly wrong at an 8% base rate.
3. Here: logit ≈ gbm in AUC (0.7476 vs 0.7578) while their *operating points* are
   opposite in sign (−1.96 vs +1.04 mean margin). I had already cited that AUC
   near-equality as evidence a linear term would ship.

The rule earned: **for a deployable gate, never report AUC without the
operating-point table** — realized value and tail-risk at the actual firing rate.
Rank quality and decision quality are different measurements and this lane paid
three times to learn it.

## 5. What would make an A/B worth funding later

Not more data — signal is established. A model whose *confident* predictions are
good, which is a different objective than AUC:

* train against realized margin with an asymmetric loss that penalises firing on
  margin ≤ −3, rather than against the binary gate label;
* or restrict to a sub-population where the linear model's tail is clean, if one
  exists (untested).

If either produces a linear rule with positive held-out mean margin at ≥2% dose,
the N=9,000 A/B becomes both cheap and adequately powered, and this prereg's
frozen-threshold procedure applies unchanged.

## 6. Seed block (registered, unused — the A/B is not launching)

**72000–80999**, released to this lane by h13-gate and confirmed 2026-08-18.

The originally proposed 70000–78999 was WRONG and was caught by asking before
freezing: it overlapped h13-gate's spent dose census (70000–70399) and ran
straight through its **live** pilot block (71000–71999). Registering it would
have collided with a running job, not merely a reservation.

72000–80999 is a contiguous 9,000-seed block, disjoint from every block held by
either lane: 41000–41099 and 41100–50099, 42000–42059, 60000–60499,
61000–61999 (this lane's gate seeds, in perpetuity), 62000–62999,
70000–70399, 71000–71999, 90000–90499.

This block is recorded for auditability only. **The A/B is not being run** (sec
3), so the block is not consumed and h13-gate should not hold compute for it.
