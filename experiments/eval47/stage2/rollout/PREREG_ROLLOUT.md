# PRE-REGISTRATION — STAGE 2 ROLLOUT (the primary endpoint)

Subordinate to `PREREG_STAGE2.md @ b9725fc` §6.3/§6.4 and `PREREG_SHIPPABLE.md @ 2d4d5d0`.
**Nothing here relaxes either.** This file only fixes what they left open: the exact arm
binary, where in the search the term is applied, the exact seed sets, the secondary
regime, the breakage accounting, and the early-stop rule.

Written and committed **before any A/B game was played**. Author: stage-2 rollout lane,
2026-08-10.

MANDATORY CAVEAT, attached to every number this lane produces:
> Corpus `s2lulu`: generating policy = shipped champion (bit-exact), environment = dr.
> lulu fitted bursty pressure, clear rate 79.80% — BELOW the 96.9% label-quality screen.
> Labels are game outcomes broadcast onto decisions; no counterfactual attribution.

SECOND MANDATORY CAVEAT: the model under test is **round-2 / CONTAMINATION-FLAGGED**
(`PREREG_SHIPPABLE.md` deviation-log entry 7 — the eligible feature set was corrected
after a holdout-scored diagnostic ranked BURIED first). Its offline AUC is optimistically
biased. **This rollout is not affected by that bias** — the endpoint is a rollout on seeds
that appear in no corpus file and were never used to fit or select anything — but the
*reason we are testing this arm rather than the clean round-1 arm* is contaminated, and
that is reported wherever the arm is named.

---

## 1. THE ARMS (exactly two; declared now)

**BASE** — the shipped champion, unchanged. `ws=20`, `wt=0`, `fast_rtl_x.variant("winner")`,
depth-3, `pressure_rig._choose_base` semantics: enumerate `o4 = 0..3`,
`var = _VAR_OF_O4[o4] = [2,3,0,1]`, `cc = 0..7`, keep strictly-greater, so a tie keeps the
first in that order.

**TRT** — identical, plus a single subtracted term:

    sco_i = cand_val_i − Delta(features(post-placement board of candidate i))

`Delta` = `S1br2_lut8_q64`, the model recommended by the shippable lane:
additive per-feature LUT over the 8 features
`{e_escape_routes, BURIED, RDYEXT, d_spawn_h, POLL, VRDY, a_topout_dist, x_hvar}`,
288 int12 table entries = 3,456 bits, 8 BRAM reads + 8 int adds, 0 multiplies, 0 DSP,
0 new whole-board passes, ~18 of the 250-clock budget. **The ten champion weights are
BIT-IDENTICAL; nothing is re-weighted.** Ship dose `Delta_sd = 10` champion score points
(the smallest dose on the pre-registered grid reaching the 2% argmax-flip bar).
Artifact: `shippable/out/RECOMMENDED_lut64.json`, integer pipeline only.

**WHERE THE TERM IS APPLIED — DEVIATION, STATED UP FRONT.** The silicon target
(`PREREG_STAGE2` §5) puts `Delta` in `LeafEval` `S_DONE2`, i.e. at *every leaf* of the
depth-3 search. **This rollout applies it at the ROOT re-rank only.** That is deliberate
and it is the honest choice: *every* offline gate this programme ran on this model — B2's
AUC, B3's argmax-flip, the entire dose curve, the ship-dose selection — was computed on
the root re-rank over post-ROOT-placement features (`shippable/round2.py:149`). Testing a
leaf-level application would be testing an intervention for which no gate was ever run and
for which the dose is uncalibrated. **Consequence, stated in advance: a NO-GO here is a
NO-GO for the validated decision rule at the validated dose, not a proof that a
leaf-level application must also fail.**

---

## 2. IDENTITY / LIVENESS GATES (must pass, or the rollout is VOID — §6.3 ROLLOUT GATES)

- **G1a OFF-identity**: with the `Delta` tables zeroed, TRT must reproduce
  `pressure_rig.play()` and `p0_ab.play_one(forced=False)` exactly — same res, pills,
  garbage, dies_ahead — **and the same per-ply action sequence**, on ≥12 seeds under BOTH
  pressure models.
- **G1b killed mutant (this is what makes G1a capable of failing)**: zero `Delta`, but the
  argmax scans the champion's enumeration order REVERSED. This changes only tie
  resolution (≈36% of decisions). It MUST break G1a.
- **G1c killed mutants**: sign-flipped tables and row-shuffled tables must break G1a.
- **G1d liveness**: the real term must differ from BASE on ≥1 seed with flips > 0.
- **G1e prune exactness**: the exact-bound candidate pruning must yield byte-identical
  action sequences to scoring all 32 candidates.
- **G0 provenance**: the deployed integer pipeline must reproduce the shippable lane's
  own reported holdout numbers for this artifact (AUC 0.7220, A_champ 0.6645, flip 2.12%
  target / 1.65% cleared), with sign-flip / shuffle / feature-permute / wrong-enum-order
  mutants all firing.

---

## 3. SEEDS, N, AND THE EARLY-STOP RULE (fixed now)

- **PRIMARY REGIME — dr. lulu bursty**: `N = 3,000` paired seeds, `20000..22999`,
  a contiguous block of the pre-registered `20000..29999` range, disjoint from every
  corpus seed (corpus = 2..12001). 2 arms = 6,000 games.
- **SECONDARY REGIME — generic drip** (the rig default, `GARBAGE_PERIOD=8`, `k=2`):
  `N = 1,500` paired seeds, `20000..21499`. 2 arms = 3,000 games. **This regime carries
  NO verdict authority** — the pre-registered endpoint is the lulu regime. It is reported
  to answer "does the term behave differently under a pressure model it was not fitted
  against", i.e. it is a generalisation check, not a decider.
- **MATCHED-INDEX CONTROL**: one work item = one seed = BOTH arms. A completed item is a
  COMPLETE PAIR, so an early stop yields a balanced prefix of the seed block, not a
  lopsided one. Seeds are consumed in ascending order.
- **EARLY-STOP RULE, declared before any result exists**: this is a wall-clock-bounded
  local run (≤6 workers, hard cap). If the run does not reach N, the analysis uses **all
  completed pairs** and reports the achieved N against the pre-registered N. Seeds are
  exchangeable and pairs complete atomically, so a prefix is a uniform sample.
  **If the lulu arm completes fewer than 1,500 pairs the primary verdict is reported as
  INCONCLUSIVE (underpowered), not as a GO or a NO-GO.** Nothing else about the verdict
  rule changes with N.

---

## 4. ENDPOINTS AND THE VERDICT RULE (copied from `PREREG_STAGE2` §6.3/§6.4; unchanged)

**PRIMARY: dies-ahead count** (all mechanisms pooled — `res == "topout"` and
`viruses_left ≤ 12`).
GO requires `DA_trt − DA_base < 0` with a 95% **seed-level paired bootstrap** CI
excluding 0 (B = 2,000, rng 20260810) **AND** McNemar exact two-sided p < 0.05 on the
discordant DA pairs.

**CO-PRIMARY, GATING: clear-rate non-inferiority.**
GO requires the **upper** bound of the 95% CI on `(clear_base − clear_trt)` to be
**< +1.0 percentage point**. If clear rate falls by more, it is **NO-GO regardless of
dies-ahead**.

**SECONDARY (reported, no verdict authority):** topout rate, stall rate, mean pills,
net bad-ends (topout+stall), pills among both-clear pairs (tempo tax), and the flip rate
actually realised in rollout.

**NO-GO conditions** — N1 clear-rate loss upper CI bound ≥ +1.0 pp; N2 dies-ahead CI
includes 0; N3 dies-ahead falls but net bad-ends do not; N4 identity or liveness gate
fails ⇒ void.
**STOP/NO-GO is reported with the same prominence as a GO.**

---

## 5. BREAKAGE ACCOUNTING (the structural law, made a number — fixed now)

Uniform population sampling prices breakage automatically; the accounting is still stated
explicitly so it cannot be softened later.

On the paired set, classify every seed:
- **BREAKAGE** `b10` = base CLEARED and trt did NOT clear.
- **RESCUE**  `b01` = trt CLEARED and base did NOT clear.
- **DA RESCUE** = base dies-ahead and trt does not; **DA BREAKAGE** = trt dies-ahead and
  base does not.

Reported: raw counts, exact-binomial two-sided p on the discordant split, and the **net
population effect** = `(b01 − b10)` clears per N games and `(DA_base − DA_trt)`
dies-aheads per N games, side by side. At the census ratio 9,576 clears : 1,501
dies-ahead = **6.4 : 1**, one lost clear is 6.4× the cost of one avoided dies-ahead;
the report states the net in both units and does not let a dies-ahead win stand alone.
**A dies-ahead win with meaningful breakage is a LOSS and is reported as one.**

---

## 6. DEVIATION LOG

- 2026-08-10: at time of commit — one, declared above in §1: the term is applied at the
  ROOT re-rank, not at every leaf, because the root re-rank is the form every offline
  gate scored and the form whose dose is calibrated.

- 2026-08-10, **AFTER the lulu primary read out. Two entries. The verdict rule and the
  primary verdict are UNCHANGED and are not re-opened.**

  1. **SECONDARY (drip) MECHANISM SPLIT NOT CAPTURED.** `PREREG_STAGE2` §6.3 lists
     "dies-ahead split by mechanism" as a SECONDARY with no verdict authority. The
     rollout row records `res` and `viruses_left` but not which of the two `res =
     "topout"` sites fired (`env.step` terminal = T_PLACE vs post-injection
     `spawn_blocked()` = T_GARB), so the split is **not reported**. Recorded as a
     shortfall rather than reconstructed post hoc from a proxy.

  2. **ADDED: a SCALE-MATCHED NULL CONTROL ARM, declared here before it was run.**
     The primary read NO_GO with a favourable-but-not-significant dies-ahead point
     estimate and enormous outcome churn (1.78% of plies flipped → 611 of 3,000 paired
     seeds ended with a DIFFERENT clear/not-clear outcome; only 760 pairs identical).
     That leaves exactly the question memory law `dr-mario-av-reach-refuted` names —
     *is this the TERM or is it the PERTURBATION?* — and that memory says a
     scale-matched control IS the test.
     **ARM**: the identical LUT with each feature's table row-permuted (rng 20260810).
     Same 288 entries, same value multiset per feature, same |Delta| scale, same
     silicon cost; no fitted board→penalty mapping. Gate 0 already measured it at
     holdout AUC **0.4746** (fitted model 0.7220), so it is certified label-blind.
     **PAIRING**: against the base rows already computed for seeds 20000..22999; the
     base arm is deterministic in the seed, and 25 seeds are re-derived and asserted
     byte-equal as a drift check.
     **READ-OUT RULE, fixed now**: report `DA_shuf − DA_base` and the churn
     statistics next to the fitted arm's, plus the difference-in-differences
     (fitted − shuffled) on dies-ahead with a 95% paired seed bootstrap on the common
     seed set. *If the shuffled arm produces a comparable dies-ahead movement and
     comparable churn, the fitted term's rollout effect is NOT distinguishable from a
     scale-matched random perturbation and the offline AUC edge did not transfer.*
     **NO VERDICT AUTHORITY** — the primary verdict is already fixed at NO_GO and this
     control can only explain it, never overturn it.

  3. **THE FIRST NULL WAS NOT DOSE-MATCHED, AND A DOSE-MATCHED ONE WAS ADDED.**
     Reported as a defect in my own control, not buried. The row-permuted LUT preserves
     the |Delta| value multiset but flips **7.28%** of rollout plies against the fitted
     arm's **1.78%** — a 4.1× more aggressive intervention. A bigger perturbation does
     more damage, so that control's difference-in-differences is **biased IN FAVOUR of
     the fitted arm** and is an UPPER bound on its advantage.
     **ADDED ARM**: the same row-permuted tables scaled by `k`, with `k` chosen on the
     SEALED HOLDOUT's 32-sibling layer so that the target-class argmax-flip matches the
     fitted arm's 2.12% — the identical instrument and statistic that set the fitted
     model's own ship dose. `k = 0.2` → 2.01% (fitted 2.12%). The calibration used **no
     rollout outcome whatsoever**, only the offline flip statistic, so it cannot have
     been tuned to a result. The chosen `k` is very slightly UNDER-dosed, which flatters
     the null and is therefore the conservative direction for the fitted arm.
     Same pairing against the same stored base rows; same 25-seed base re-derivation
     drift check. Still **NO VERDICT AUTHORITY**.
