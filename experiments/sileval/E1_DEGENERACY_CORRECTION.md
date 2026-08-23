# CORRECTION — E1-binary is LESS degenerate than I reported

**2026-08-23. This corrects a number I gave team-lead, and it partially
undercuts the reasoning they accepted when approving the measurand change.
Sending it rather than letting it stand.**

## What changed

Another lane located the real per-match winner: the per-set win counters at
**`$031E` (P1) / `$039E` (P2)**. These give **100% capture** — no end-frame
needed. Counting increments across all 255 rows:

| | my end-frame method (12.9% capture) | **win counters (100% capture)** |
|---|---|---|
| P1 wins | 0 (+1 artifact) | **29** |
| P2 wins | 111 | **771** |
| P2 share | ~100% | **96.38%** |

**My 12.9% sample was BIASED, and biased in a direction I had flagged as a risk
and then failed to apply.** P2 wins mostly by P1 topping out — mode `$07`, a
~2.5 s window that samples readily. P1 wins by clearing — mode `$03`, of which
the entire corpus contains **4 samples**. So P1's wins were systematically
under-captured, and I read ~99-100% P2 where the truth is 96.4%.

## Consequence for the measurand argument

I told team-lead: *"if the winner is ~99% constant, paired discordance cannot
exceed ~2%, below the ~4% the power table was sized for."*

With P1 winning **3.62%**, the independence upper bound on paired discordance is
**2p(1−p) ≈ 7.0%**, which is **above** the ~4% the design was sized for, not
below it. **E1-binary is therefore not underpowered by construction in the way I
claimed.**

Two things keep it from being a clean reversal, and both must be said:
- 7.0% is an **upper bound under independence**. The arms are strongly
  correlated (same seed, same generated board, argmax-identical carts), so real
  discordance will be far below it — plausibly still under 4%. Unknown until
  measured, and now measurable at 100% capture.
- The endpoint is still low-variance, and the direction of interest (P1 winning
  more under slice) has only a 3.6% base rate to move.

## Status

**E1-binary should be re-examined, not written off.** It is now fully readable
via `$031E`/`$039E`, so the discordance rate can simply be MEASURED rather than
bounded — which settles the power question with data instead of my arithmetic.

E4a remains registered and read (an informative null), and the AMENDMENT 2
exploratory/confirmatory structure stands regardless. But the *justification* I
offered for prioritising it was partly wrong, and the decision deserves to be
revisited on the corrected number.

## The error shape, again

My "exhaustive" RAM scan MISSED `$031E`/`$039E` because I required a win counter
to be **non-decreasing** — and these **reset to 0 between sets**. That single
negative step disqualified the true answer on the first test.

**That is the same failure shape as `find_base` deleting the end-of-match
samples: my search criterion encoded an assumption the phenomenon violates.**
Twice in one investigation. The scan was exhaustive over OFFSETS and narrow over
BEHAVIOURS, which is not exhaustive at all.
