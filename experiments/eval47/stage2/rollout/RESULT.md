# STAGE 2 ROLLOUT — THE PRIMARY ENDPOINT. VERDICT: **NO-GO**

Pre-registration: `PREREG_ROLLOUT.md` (committed at f5f58f0, before any A/B game) →
`PREREG_STAGE2.md` §6.3/§6.4 @ b9725fc. The verdict rule was not renegotiated.

MANDATORY CAVEAT: Corpus `s2lulu`: generating policy = shipped champion (bit-exact),
environment = dr. lulu fitted bursty pressure, clear rate 79.80% — BELOW the 96.9%
label-quality screen. Labels are game outcomes broadcast onto decisions; no
counterfactual attribution.
SECOND CAVEAT: the arm under test is ROUND-2 / CONTAMINATION-FLAGGED
(`PREREG_SHIPPABLE.md` deviation 7).

---

## THE HEADLINE, SAID FIRST

**The shippable evaluator does NOT reduce dies-ahead in rollout, and — this is the
finding that matters — a LABEL-BLIND TERM OF THE SAME SIZE DOES EXACTLY AS WELL.**

At a dose-matched null (row-permuted tables, holdout AUC 0.4746, flipping 1.96% of plies
against the fitted arm's 1.78%):

| arm | dies-ahead vs base | clear vs base |
|---|---|---|
| fitted S1br2_lut8_q64 (AUC 0.7220) | **−0.80 pp** [−2.20, +0.60] | +0.30 pp |
| dose-matched label-blind null (AUC 0.4746) | **−0.53 pp** [−1.93, +0.87] | +0.17 pp |
| difference-in-differences | **−0.27 pp [−1.73, +1.13]** | — |

The offline AUC edge (+0.0575 over the champion, 100% of 2,000 bootstrap reps positive)
**did not transfer to the rollout endpoint.** *Signal ~ sqrt(R)/SE; proxies rule OUT
only* — this is that law being paid.

---

## ARM DEFINITIONS

**BASE** — the shipped champion, unchanged: ws=20, wt=0, `variant("winner")`, depth-3,
`pressure_rig._choose_base` enumeration (`o4 = 0..3`, `var = [2,3,0,1][o4]`, `cc = 0..7`,
strict `>`, so ties keep the first in that order).

**TRT** — identical plus one subtracted term, `sco_i = cand_val_i − Delta(post-placement
features of candidate i)`, `Delta` = `S1br2_lut8_q64`: additive per-feature LUT over
`{e_escape_routes, BURIED, RDYEXT, d_spawn_h, POLL, VRDY, a_topout_dist, x_hvar}`,
288 int12 entries = 3,456 bits, 8 BRAM reads + 8 int adds, 0 multiplies, 0 DSP, 0 new
board passes, ship dose `Delta_sd = 10`. **The ten champion weights are bit-identical;
nothing is re-weighted.** `Delta ≡ 0` is therefore an exact-identity control.

**DEVIATION, declared in the prereg before the run**: the term is applied at the ROOT
re-rank, not at every leaf. That is the form every offline gate scored
(`shippable/round2.py:149`) and the form whose dose is calibrated. A NO-GO here is a
NO-GO for the validated rule at the validated dose, not a proof that a leaf-level
application must also fail.

---

## IDENTITY GATES — BOTH DIRECTIONS, ALL MUTANTS FIRE

| gate | lulu | drip |
|---|---|---|
| **G0** deployed integer pipeline reproduces the artifact's own reported holdout numbers: AUC **0.7220** (reported 0.7220), A_champ **0.6645** (0.6645), flip **2.12%** target / **1.65%** cleared (2.12/1.65), \|Delta\|max 52, sd 9.59 | PASS | — |
| G0 mutants: sign-flip AUC **0.2780**, shuffled tables **0.4746**, feature-permute **0.4160**, wrong enum order → base argmax disagrees on **36.95%** | all fire | all fire |
| **G1a OFF-identity** — `Delta` zeroed reproduces `pressure_rig.play()` and `p0_ab.play_one(forced=False)` on res/pills/garbage/dies_ahead **and the identical per-ply action sequence** | **12/12** (action-seq 12/12) | **12/12** (12/12) |
| **G1b** killed mutant: same zero `Delta`, enumeration order REVERSED (tie resolution only, ≈36% of decisions) must BREAK G1a | breaks 12/12 | breaks 11/12 |
| **G1c** killed mutants: sign-flipped / row-shuffled tables must break G1a | 12/12 · 12/12 | 10/12 · 12/12 |
| **G1d liveness** — the real term differs from base and flips plies | 12/12, 63/2438 = 2.58% | 11/12, 34/1727 = 1.97% |
| **G1e** exact-bound pruning gives byte-identical action sequences to scoring all 32 | 12/12 | 12/12 |

Two further checks that could have failed and did not:
* **Harness vs the census.** The BASE arm on seeds 20000..22999 (disjoint from the corpus)
  reproduces the 12,000-seed lulu census composition: clear 80.67% vs 79.80%, topout
  13.80% vs 14.05%, stall 5.53% vs 6.15%, dies-ahead 12.13% vs 12.51% — **every census
  value inside the base arm's 95% CI.**
* **Untouched games are bit-identical.** On the 527/3,000 games where the term never
  flipped a ply, base and treatment agree on every field (asserted).
* **Base re-derivation.** 25 base games re-derived inside the control runs: **0 mismatches.**
* **The verdict function itself is mutant-tested** (`test_verdict.py`): it returns GO on a
  synthetic true win, NO_GO on a win with a 4pp clear-rate collapse, NO_GO on a null,
  NO_GO on a regression, INCONCLUSIVE at N=800; McNemar and bootstrap hand-checked.

---

## THE FULL TABLE

### PRIMARY — dr. lulu bursty pressure, N = 3,000 paired seeds 20000..22999 (6,000 games)

| metric | BASE [95% CI] | TRT [95% CI] | paired diff (trt−base) [95% CI] |
|---|---|---|---|
| **dies-ahead** | **12.13%** [11.00, 13.30] (364) | **11.33%** [10.23, 12.47] (340) | **−0.800 pp [−2.200, +0.600]** |
| **clear** | **80.67%** [79.23, 82.03] (2420) | **80.97%** [79.57, 82.37] (2429) | **+0.300 pp [−1.301, +1.867]** |
| topout | 13.80% [12.57, 15.03] (414) | 12.87% [11.70, 14.10] (386) | −0.933 pp [−2.334, +0.467] |
| stall | 5.53% [4.70, 6.40] (166) | 6.17% [5.33, 7.10] (185) | +0.633 pp [−0.433, +1.701] |
| bad-ends (topout+stall) | 19.33% (580) | 19.03% (571) | −0.300 pp [−1.867, +1.301] |
| mean pills | 155.41 [153.21, 157.73] | 154.91 [152.63, 157.27] | −0.500 [−2.651, +1.663] |
| pills, both-clear pairs (n=2119) | 136.71 | 136.31 | −0.403 [−2.217, +1.476] |

McNemar exact two-sided: dies-ahead **p = 0.2793** (238 rescued vs 214 broken);
clear p = 0.7462; topout p = 0.2110; stall p = 0.2759.

### SECONDARY — generic drip pressure, N = 1,500 paired seeds 20000..21499 (3,000 games). NO VERDICT AUTHORITY.

| metric | BASE | TRT | diff [95% CI] |
|---|---|---|---|
| dies-ahead | 2.53% (38) | 1.80% (27) | −0.733 pp [−1.667, +0.200] |
| clear | 94.93% (1424) | 95.73% (1436) | +0.800 pp [−0.535, +2.133] |
| topout | 2.53% (38) | 1.80% (27) | −0.733 pp [−1.667, +0.200] |
| stall | 2.53% (38) | 2.47% (37) | −0.067 pp [−1.133, +1.000] |
| bad-ends | 5.07% (76) | 4.27% (64) | −0.800 pp [−2.133, +0.535] |
| mean pills | 129.82 | 128.81 | −1.009 [−3.453, +1.440] |

McNemar dies-ahead p = 0.1524 (30 rescued, 19 broken); clear p = 0.2807.
Same sign as lulu, same non-significance. The term is not lulu-specific and it is not
reading the volley schedule — it is simply not doing much.

---

## BREAKAGE — MEASURED EXPLICITLY, AND IT IS ENORMOUS

The structural law says an always-on change loses at population scale unless breakage is
essentially zero. **Breakage here is not zero; it is 301 games.**

| | lulu (N=3,000) | drip (N=1,500) |
|---|---|---|
| games the champion CLEARED that the new arm does NOT (**BREAKAGE**) | **301** (12.4% of the base's 2,420 clears) | **46** |
| games the new arm CLEARED that the champion does NOT (RESCUE) | 310 | 58 |
| **net clears** | **+9** (p = 0.7462) | +12 (p = 0.2807) |
| dies-ahead rescued / newly caused | 238 / 214 → **net +24** (p = 0.2793) | 30 / 19 → net +11 |
| **net in clear-equivalents at the census 6.4 : 1 ratio** | **+12.75 per 3,000 games** | +13.72 per 1,500 |

Uniform population sampling prices breakage at the true ratio automatically. The net is
**+12.75 clear-equivalents in 3,000 games = +0.43% of a game each** — statistically and
practically indistinguishable from zero, obtained by churning 611 of 3,000 game outcomes.

**Churn is the real story.** A **1.78% per-ply argmax-flip rate** produced:
* 2,473 / 3,000 games with at least one changed ply; only **760 pairs identical**;
* **611 discordant clear outcomes** and **452 discordant dies-ahead outcomes**;
* of the 364 base dies-ahead games, only 126 stayed dies-ahead — 238 were rescued and
  **214 entirely new ones were created**.

This rig is chaotic in the action sequence: perturbing 1.8% of plies reshuffles ~20% of
game outcomes. That is why the pre-registered ±1.0 pp clear-rate non-inferiority margin
was **unreachable at N = 3,000 by construction** — the paired CI half-width is ±1.58 pp.

---

## THE SCALE-MATCHED NULL — WHY THIS IS A REFUTATION AND NOT JUST AN UNDERPOWERED RUN

Declared in the prereg deviation log before it was run; **no verdict authority.**
The null arm is the identical LUT with each feature's table row-permuted (rng 20260810):
same 288 entries, same value multiset, same silicon cost, holdout AUC **0.4746**.

| null | ply-flip | dies-ahead vs base | clear vs base | discordant clears | DiD (fitted − null) |
|---|---|---|---|---|---|
| value-matched, k=1 | 7.28% (**4.09×** the fitted dose) | **+1.13 pp** [−0.40, +2.77] | **−2.00 pp** [−3.87, −0.10] | 854 | −1.93 pp [−3.53, −0.33] |
| **dose-matched, k=0.2** | **1.96%** (1.10× — fair) | **−0.53 pp** [−1.93, +0.87] | +0.17 pp [−1.43, +1.83] | 657 | **−0.27 pp [−1.73, +1.13]** |

`k` was chosen on the SEALED HOLDOUT's 32-sibling layer so the target-class argmax-flip
matched the fitted arm's 2.12% (k=0.2 → 2.01%) — the identical instrument and statistic
that set the fitted model's own ship dose, using **no rollout outcome whatsoever**, and
very slightly UNDER-dosed, which flatters the null.

I reported my own first control as defective: the k=1 null is **4.1× more aggressive**, so
its favourable DiD is an UPPER bound biased toward the fitted arm and must not be quoted.
**The fair, dose-matched comparison separates nothing: DiD −0.27 pp with a CI spanning
zero and only 60.5% of bootstrap reps negative.**

What the two nulls together do establish: **churn is not free but it is not directed
either.** A 4× dose of random perturbation costs 2.00 pp of clear rate (CI excludes 0) and
*raises* dies-ahead; a 1× dose of random perturbation is neutral. The fitted term sits at
the neutral point. Its 0.7220-vs-0.6645 AUC advantage buys nothing a coin flip of the same
size does not.

---

## VERDICT — PRE-REGISTERED RULE, APPLIED VERBATIM

### **NO-GO** (lulu, primary, N = 3,000 = the full pre-registered N)

Three of the pre-registered NO-GO conditions fire:
* **N1** — clear-rate non-inferiority FAILS: upper 95% bound on (clear_base − clear_trt) is
  **+1.30 pp ≥ +1.00 pp**. (The point estimate favours the treatment by 0.30 pp; the gate
  fails on WIDTH, because 611 discordant clears make the CI ±1.58 pp.)
* **N2** — dies-ahead 95% CI on the paired difference is **[−2.200, +0.600] pp**, includes 0.
* **N2** — McNemar exact two-sided **p = 0.2793 ≥ 0.05**.
* N3 does NOT fire (bad-ends fell by 0.30 pp), and N4 does not fire (all gates pass).

**Reported with the same prominence a GO would have been.**

A trend worth flagging under N3 even though the condition did not fire: of the 28 topouts
avoided, **19 reappeared as stalls** — 68% of the topout reduction converted to 300-pill
stalls rather than to clears. That is exactly the mechanism N3 exists to catch, showing up
as a trend at this dose.

### Power, for the record — NOT a re-opening of the verdict

At the observed point estimates the pre-registered gates would have needed
**N ≈ 9,044** for the dies-ahead McNemar and **N ≈ 4,453** for clear-rate
non-inferiority. But the dose-matched null says the effect at the observed size is not
attributable to the term, so more N would most likely buy a precisely-measured null.

---

## WHAT THIS COSTS THE PROGRAMME, AND WHAT IT BUYS

1. **The shippable arm is refused.** `S1br2_lut8_q64` at `Delta_sd = 10` on the root
   re-rank does not reduce dies-ahead and cannot clear the clear-rate gate. Do not spend
   silicon on it.
2. **The AUC→rollout bridge is broken for this class of term, and now that is measured.**
   +0.0575 holdout AUC, 2.12% argmax-flip, and a fully live wiring produced a rollout
   effect indistinguishable from a label-blind term of the same size. Every future
   candidate in this lane must be read against a **dose-matched, label-blind null**, not
   against the champion alone.
3. **A new hard constraint on the endpoint itself.** The rig's outcome churn under a 1.8%
   ply perturbation is ~20% of games. Any future arm at this flip rate needs
   **N ≳ 4,500 paired seeds just to be able to pass the ±1.0 pp clear-rate gate**, and
   more to resolve a sub-1 pp dies-ahead effect. The pre-registered N = 3,000 was too
   small for the perturbation size, and that is now a measured number rather than a guess.
4. **The lever, if there is one, is a LOWER flip rate with a SHARPER target.** The
   shippable lane's own dose curve already showed the flip landing disproportionately on
   ties (3.80% of tied decisions vs 1.13% of decided ones). A term that fires only where
   the champion is genuinely indifferent would churn far less and would be testable at a
   feasible N; a term that flips 1.8% of all plies is a policy rewrite priced at 611
   coin-flipped clears.

---

## ARTIFACTS

`experiments/eval47/stage2/rollout/`
* `PREREG_ROLLOUT.md` — pre-registration + 3 deviation-log entries
* `arm_lut.py` — the arm (integer LUT pipeline, exact-bound pruning, rig-replica rollout)
* `gate0_provenance.json`, `gate1_identity.json` (12 seeds), `gate1_identity_4seed.json`
* `run_ab.py`, `run_ctrl.py`, `calib_null.py`, `analyse.py`, `addendum.py`, `test_verdict.py`
* `out/ab_lulu.jsonl` (3,000 pairs), `out/ab_drip.jsonl` (1,500), `out/ctrl_lulu_shuf.jsonl`
  (3,000), `out/ctrl_lulu_shuf_k02.jsonl` (3,000)
* `out/rollout_result.json` (the verdict), `out/addendum_lulu.json` (nulls, churn, power),
  `out/calib_null.json`

Total 15,000 games, all local, ≤6 workers, `systemd-run --user --scope`, waited in-turn.
