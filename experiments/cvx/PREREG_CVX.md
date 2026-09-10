# PRE-REGISTRATION — convex-height eval candidate vs CHAMPION (registered BEFORE the validation run)

**Hypothesis.** The shipped leaf charges a CONSTANT w[R_MAXH]=12 per row of stack height, so
height 4->5 costs exactly what 13->14 costs. Top-out is a CLIFF, so the true cost of height is
CONVEX. Candidate adds ONE nonlinear term over an EXISTING feature (the banked open lead
"nonlinear in the same 11 terms is UNTESTED"):  leaf -= CVX * max(0, maxh - KNEE)^2 .

**Arms.** champion = `variant("winner")` (r47 + the coef-opt2 5-constant reweight, the STANDING
champion). candidate = `wincvx16_11` (winner + CVX=16, KNEE=11).

**Why this candidate.** Chosen by a 6-arm screen (CVX in {8,16,32} x KNEE in {8,11}) on 100 paired
seeds. It led at BOTH L11 (+4.0pp) and L20 (+5.0pp). ⚠ The screen selects the max of 6, so those
figures carry winner's-curse inflation and are NOT the estimate. This run exists to replace them.

**Design.** CRN-paired: identical seed => identical virus layout, pill stream AND garbage
(garbage is a pure function of (seed, pills_placed)), so the pair differs ONLY by the eval.
Regime: level 20, drip pressure, wt=0 ws=20, max_pills=300 (the L20 rate-amplifier regime;
L11 baseline sits at 95% and is CEILING-LIMITED, hence unusable for power).

**PRIMARY.** Paired clear-rate difference, McNemar exact two-sided on discordant pairs.
**SECONDARY.** median pills-to-terminal; stall% and topout% split.

**Seeds.** A FRESH block, DISJOINT from the 100 screening seeds (36734..36932), drawn from the registry: EVEN seeds 36934..38532 step 2 (800 streams).
seed registry --suggest. Screening seeds are NOT reused and NOT pooled.

**Decision rule, fixed now.**
- p < 0.05 AND direction positive  => genuine champion candidate; report effect + CI, then it still
  owes an RTL/firmware feasibility check (int16 wrap + ALM cost) before any ship claim.
- p >= 0.05                        => NOT a champion. Report the null honestly with its CI; do not
                                      re-slice, do not re-screen on the same data, do not quote the
                                      screen's +5.0pp as if it were the result.
- direction negative               => report as harm.

**Pre-committed hazards.**
- int16 wrap: the leaf wraps (`s & 0xFFFF`). A large convex penalty could wrap to POSITIVE and
  invert the ranking. Check the observed leaf range; CVX=16/KNEE=11 caps the term at 16*25=400.
- The candidate must be scored against the CHAMPION it replaces, never against a target
  (dr-mario-score-against-the-baseline-you-replace).
