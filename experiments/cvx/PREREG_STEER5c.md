# PRE-REG STEER5c (2026-09-26, written BEFORE any 5c game runs): CONFIRMATORY holdout of the HSV leaf term

**Arm.** `s5b_hsv512`: the HSV leaf term of `cascade_leaf5b_x` (−W · #viruses in cols 3–5 at row < 9, at every leaf)
at the RTL-buildable dose **W = 512** (popcount 1). The shipping REACH+TAP baseline brain and steering are otherwise
unchanged. hsv540 reproduces its banked md5 after this session's edits (`4f19c4da`), so the code is unchanged.

**Why a holdout.** hsv was chosen AFTER STEER5 failed (post-hoc, STEER5b), on the reused 36734.. block, so that
block cannot confirm it.

## PRIMARY (confirmatory)
- **Data:** the FRESH 464-stream block, registered 2026-09-26 as the STEER5 control: even seeds 4002–4462,
  40934–41098, 17000–17098, 17300–17398, 20900–20998.
- **Comparison:** gate (b), OWNER model, L11 MED, paired vs the BANKED baseline control on the same seeds
  (`steer5/control/ctl_*`, `s5_base` = the shipping baseline).
- **PASS iff BOTH:**
  1. tap≤100 paired Δ **point estimate < 0**;
  2. whole-game tap-out paired Δ **upper 95% CI ≤ +2 pp** (the DOSE2/STEER2 non-inferiority margin).
- **AND the race secondary:** vs_race lam 6, **n = 300 FRESH seeds** (the first 300 of the block: 4002–4462 and
  40934–41070), paired vs the baseline race on the same seeds, both run fresh. Unified tap steering, scored vs a
  177-s human at δ 2.65. Its **lower 95% CI of the win diff must be ≥ −2 pp**. δ 2.0 is reported too.

## Honest power
From the STEER5b hsv540 paired SEs scaled to n = 464:
- **tap≤100:** SE ≈ 1.35 pp. The point-estimate-below-0 criterion is near-certain if the true effect is ≈ −3 pp.
- **tap-out:** SE ≈ 2.85 pp. The upper-CI-≤-+2 criterion needs an estimate ≤ ≈ −3.6 pp:
  - ≈ 38% power if the true effect is −2.7 pp (the 5b estimate);
  - ≈ 10% chance of passing if the true effect is 0.
⇒ A FAIL here is weak evidence against the term. A PASS is meaningful.

## Reported, NOT counted toward the pass
- hsv512 on the original 600-seed block (paired vs `s4_base`), to check that dose 512 ≈ 540.
- **POOLED** 600 + 464 estimates, descriptive only (the 600 block is not independent of the hsv selection).
- The hsv9 layout strata.

## If it passes
Include the full RTL spec:
- the 27-cell region count (cols 3–5 × rows 0–8, the virus bit);
- the combine (−512·HSV);
- the delta-path argument (a non-clearing child's HSV equals its parent's);
- the expected pipeline impact at 0.165 ns slack.

**Compute.** Hetzner (IRON RULE, local↔remote md5 exactness gate) for the fresh gate (b) and the races; local
`nice 19` ≤ 4 workers for the 600-block descriptive cell.
