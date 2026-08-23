# E4a on population A — EXPLORATORY. Result: an informative NULL

**Population A is EXPLORATORY for E4 (AMENDMENT 2). Population B is the
confirmatory out-of-sample test. These are never pooled.**
Registration commit `5c2870e` precedes this computation.

## Result

| | |
|---|---|
| seeds paired | 123 |
| complete matches per arm (shared ordinals) | 322 |
| ship mean P1 virus count at match end | **42.429** |
| slice mean | **42.484** |
| **difference (slice − ship)** | **+0.056 viruses** |
| seed-clustered bootstrap 95% CI (10,000 resamples of SEEDS) | **[−0.742, +0.866]** |
| bootstrap mass favouring slice | 45.8% |
| realised per-match SD | 6.07 (planning SD was 5.1) |

**Verdict by the registered threshold: NULL — the CI spans 0.**
The hypothesised direction was slice LOWER; the point estimate is very slightly
higher, and the interval is centred on nothing.

## What this null does and does not bound

It is **informative, not merely inconclusive**: it excludes any effect larger
than about **0.87 viruses in either direction** on a mean of 42.4. The realised
precision matches the registered MDE (~0.9 at n≈124 seeds), so the study did
what it was sized to do.

⚠ **The limit worth stating next to the number, not under it:** P1 clears only
**~5.6 of its 48 viruses before dying** on average. The endpoint's dynamic range
is therefore narrow — P1 is being comprehensively beaten in this CvC matchup
(see the 111:1 P2 dominance), so there is little room for *any* P1-side
mechanism to express itself in progress-at-death. A tight null in absolute virus
terms is not the same as a tight null on the mechanism.

Both registered residual-tempo biases ran AGAINST the hypothesis, so this null
is not explained away by them — but neither is it strong evidence that the NMI
tail is harmless, for the dynamic-range reason above (rule 8).

## Standing

Exploratory. It does not settle the claim, and by AMENDMENT 2 it cannot: the
confirmatory read is population B. What it does establish is that E4a is
**computable, precise, and well-behaved** at this n — which is what makes B
worth running.
