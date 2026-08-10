# PRE-REGISTRATION — STAGE 2 / SHIPPABLE-MODEL LANE

Subordinate to `PREREG_STAGE2.md @ b9725fc`. Nothing here relaxes that file; this one
only fixes the things it left open: *which* in-class model shapes get fitted, *how* the
8-feature vector is chosen, and *what quantisation actually ships*.

Written and committed **before any model was fitted and before any holdout row was read**.
Author: shippable-model lane, 2026-08-10.

MANDATORY CAVEAT, attached to every number below:
> Corpus `s2lulu`: generating policy = shipped champion (bit-exact), environment = dr.
> lulu fitted bursty pressure, clear rate 79.80% — BELOW the 96.9% label-quality screen.
> Labels are game outcomes broadcast onto decisions; no counterfactual attribution.

---

## 1. WHAT THIS LANE DELIVERS, AND WHAT IT EXPLICITLY DOES NOT

Delivers: for each candidate shape, a **holdout AUC after quantisation to the format that
would actually ship**, a **deployability statement checked against the measured silicon
budget**, and a **within-decision argmax-flip rate** (prereg §6.2 B3).

Does NOT deliver: a reduction in dies-ahead. That is the rollout endpoint in
`PREREG_STAGE2.md` §6.3 and this lane cannot and does not claim it. **An AUC number is
permission to test, never a result.** If every candidate fails B1/B2/B3 the answer is
STOP and it is reported as prominently as a GO would be.

---

## 2. THE TARGET FORM (fixed by recon B; not re-opened here)

    sco = <the 10 champion terms, weights BIT-IDENTICAL> - Delta(x)

`Delta` is evaluated **sequentially** — one comparator, one adder, one cursor — over a
**narrow 8-feature x 8-bit vector**, with parameters in block RAM.

**NO CANDIDATE IN THIS LANE RE-WEIGHTS ANY EXISTING CHAMPION TERM.** This is not a
stylistic preference, it is the memory law `dr-mario-ws20-failure-optimal` (ws=20 is
failure-optimal on a U-curve: do not re-weight, ADD) plus the structural law (at the
population ratio one breakage outweighs ~43 rescues, so `Delta == 0` must remain an
EXACT-IDENTITY control). Every candidate is reported with an explicit
`reweights_existing` field and it must read `false`.

---

## 3. THE FEATURE VECTOR — selection procedure fixed BEFORE it is run

**Eligible set = the PREREG_STAGE2 §8 `FREE_IN_COLWALK` list, and nothing else:**
`MAXH, HOLES, TOPRISK, SPAWN, a_topout_dist, d_spawn_h, d_crit_cols, d_gvuln_mass,
x_jagged, x_hvar, e_escape_routes`.

Two deliberate exclusions, recorded now so neither can be rationalised later:

* `c_das_reach`, `c_d_das_reach`, `e_escape_reach` are `OFF_BUDGET` by §8 and are used
  **only** in the out-of-class CEILING model. NOTE FOR THE DEVIATION LOG: reading
  `feature_battery.das_reach(H)` shows it is a pure prefix-AND over the 8 column heights,
  i.e. it is arguably free given `colh[0..7]`. **This lane does not act on that
  observation.** Honouring the pre-registered tag can only make the in-class result a
  LOWER bound, which is the safe direction; re-tagging after seeing the data is exactly
  the move this project has fooled itself with before.
* `SETUP, MATCHED, BURIED, RDYEXT, VRDY, CROSS, POLL` are champion terms that are NOT on
  the §8 free list; `a_d_maxh, b_spawn_prox, b_spawn_prox_strict, c_nlegal_probe,
  c_d_nlegal` are tagged free by the builder but NOT by §8. §8 wins.

**Selection**: greedy forward selection to exactly 8 features, scored by **5-fold
GroupKFold AUC on TRAIN ROWS ONLY, grouped by seed** (never by decision). Ties broken
toward the cheaper feature in the order the eligible list is written above. The chosen 8
are frozen and used by every in-class candidate, so the candidates differ only in the
shape of `Delta`, not in what it can see.

---

## 4. THE CANDIDATE SHAPES (declared now; exactly these, no others)

| id | shape | why it is here |
|---|---|---|
| **S0** | `d_spawn_h` as ONE added term, 4-segment monotone hinge | the lane's strongest known input, MEASURED at -420 ALM / +1 DSP / **+0 cycles**. It is the null hypothesis for every other candidate: anything more complex must beat it or be refused. |
| **S1** | augmented linear: a 4-segment monotone hinge per selected feature, summed | recon B family (a), measured ALM-NEGATIVE |
| **S2** | 256 depth-1 stumps, sequential, params in 1 M10K | recon B family (b), MEASURED 91 ALMs / 1 RAM / 256 cycles |
| **S3** | 32 depth-4 quantised-threshold trees, sequential | recon B family (c), the closest shippable relative of the stage-1 GBM |
| **CEIL** | unconstrained GBM, all 26 features incl. `OFF_BUDGET` | **CEILING ONLY.** Reported as out-of-class per §6.4 S4. Not a candidate, and it will not be dressed up as one. |

`d` (depth), tree count and stump count may be REDUCED if the budget check fails; they
may not be increased.

---

## 5. QUANTISATION — the exact shipping format, fixed now

Declared before fitting so that "it survived quantisation" cannot become a post-hoc
choice of a friendlier format.

| element | format |
|---|---|
| feature vector | `uint8`, on the feature's own integer grid. Losslessness is **asserted**, not assumed: any feature whose corpus values are not exactly representable in `uint8` is scaled by a fixed power of two declared in the model JSON, and the resulting max absolute error is reported. |
| thresholds | `uint8`, on the SAME grid as the feature, so the comparison is exact integer |
| stump / leaf values | **signed 12-bit**, `round(v / s)` clipped to `[-2048, 2047]`, `s` a single per-model power-of-two scale |
| hinge slopes (S0/S1) | signed 8-bit integer coefficients on integer breakpoints |
| accumulator | `int16`, matching the champion combine's 16-bit wrapping integer arithmetic. **Overflow is checked on every corpus row**, not argued. |
| application | `sco = champ - (acc >> k)`, `k` declared per model |

**REPORTED PRIMARY = the QUANTISED AUC.** The float AUC is reported next to it as a
diagnostic only. A model that loses its edge at 8-bit is not a candidate — discovering
that after a rollout campaign is the specific waste this rule exists to prevent.

**KILLED MUTANT FOR THE QUANTISER** (a check that cannot fail is not a check): a
deliberately-degraded quantiser — leaf values crushed to **signed 3-bit** — must lose
measurably more AUC than the shipping 12-bit format on the same fitted model. If the
3-bit mutant is as good as 12-bit, the quantisation evaluation is not measuring anything
and is reported as vacuous.

---

## 6. WHAT IS COMPUTED ON THE HOLDOUT, IN ONE PASS

The holdout is opened **once**, after §3's 8 features and §4's five models are frozen and
this file is committed.

1. `AUC(Delta_quant)` and `AUC(Delta_float)` vs `y` — MODEL RISK SCORE, higher = riskier,
   the same orientation as `_auc(-champ_eval, y)` in `s2_features.py`.
2. `A_champ = AUC(-CHAMP_EVAL)` on the same rows (prereg B2 comparator).
3. **B1**: `AUC(model) - AUC(model refitted on y_shuf)` >= 0.10. The floor model is a
   genuine REFIT on permuted labels, not the same model scored against a permuted label.
4. **B2**: `AUC(model) > A_champ`, 95% **seed-clustered** bootstrap CI on the PAIRED
   difference excluding 0, and any margin under **+0.01** counts as NOT CLEARED.
5. **B3**: argmax-flip on the `all32` within-decision layer, holdout rows, target class.
   Reported as a dose curve; the pre-registered bar is **>= 2%** at the dose proposed for
   rollout.
6. **B4**: AUC on `end_kind == step_topout` (T_PLACE) and across `since_last_garbage`
   deciles; plus `t_to_end` bands and height bands (§3.2 of the parent prereg forbids
   reporting pooled over `t_to_end` only).
7. Deployability: parameter bits, ops/leaf, cycles/leaf, against §5 of the parent prereg
   (<=250 clocks, <=150 ALMs, <=2 M10K, 0 new whole-board passes).

## 7. RECOMMENDATION RULE — fixed before the numbers exist

Among candidates that are IN CLASS and clear B1, B2 and B3:

1. Rank by **quantised holdout AUC**.
2. **Simplicity tie-break, applied at +0.005**: if a cheaper shape is within 0.005 AUC of
   a more expensive one, the CHEAPER one is recommended. Rationale is the structural law,
   not aesthetics — every added parameter is more clear-game contact, and clear-game
   breakage is ~6.4x as expensive as rescue at the population ratio.
3. If NO in-class candidate clears B1/B2/B3 -> **STOP (S2/S3)**, report the ceiling and
   the reachable fraction, and do not request rollout compute.
4. If the only model clearing B2 is `CEIL` -> **S4, CEILING ONLY**.

## 8. DEVIATION LOG

- 2026-08-10: none at time of commit.
