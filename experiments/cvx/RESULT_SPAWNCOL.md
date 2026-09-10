# RESULT — spawn-lane candidate vs CHAMPION (run of PREREG_SPAWNCOL.md)
2026-09-10. Pre-registration was filed before the run; nothing below is a post-hoc slice.

## PRIMARY — NULL. `winsc2` is NOT a champion.
n = 800 CRN-paired fresh seeds (38534..40132 step 2, registry PASS, 0 overlap), L20 drip, cap 600.

| arm | clear | d | 95% CI | W | L | McNemar p | topout | stall | med pills |
|---|---|---|---|---|---|---|---|---|---|
| champion | 89.25% | — | — | — | — | — | 8.75% | 2.00% | 197 |
| **winsc2** (primary) | 90.38% | +1.12pp | [-1.6,+3.8] | 66 | 57 | **0.4709** | 7.25% | 2.38% | 200 |
| winsc5 (dose check) | 91.00% | +1.75pp | [-1.1,+4.6] | 75 | 61 | 0.2649 | 6.25% | 2.75% | 211 |

Decision rule said: `p >= 0.05` => NOT a champion, report the null with its CI, no re-slicing, and do
not quote the screen's +9.0pp as the result. Applied as written.

## SECONDARY (pre-specified, reported for completeness, NOT a rescue)
Topout endpoint, McNemar: champion tops out & winsc2 does not = 58, reverse = 46, p = 0.2807.
For winsc5: 61 vs 41, p = 0.0594. Topout falls monotonically across the three arms,
**8.75% -> 7.25% -> 6.25%**, in the direction the mechanism predicts.

## ★★★ THE DURABLE FINDING — the curse is the story
| candidate | screen (n=100) | validation | curse |
|---|---|---|---|
| convex height `wincvx16_11` | +5.0pp | -2.5pp | **-7.5pp** |
| spawn lane `winsc2` | +9.0pp | +1.12pp | **-7.9pp** |

SE of a paired difference at n=100 with ~25% discordance is 5.0pp; expected max-of-4 inflation is
+5.3pp BEFORE any real effect exists. **A n=100 screen cannot produce a usable lead.**
=> standing rule: **screen at n >= 400**. See [[dr-mario-screen-n100-is-useless]].

## The honest residual, and why it is PARKED not chased
Both doses positive, topout monotone across three independent 800-seed arms: the null does not
exclude a true effect around +1.5pp, it cannot resolve one. Resolving 1.5pp needs ~4,270 seeds
(~12,800 games, ~3.5 h). Affordable, but it buys a 1.5pp SOLITAIRE clear-rate gain while the north
star is a RACE against a person ([[dr-mario-it-is-a-race-not-survival]]). Parked.

## int16-wrap hazard — DISCHARGED (pre-committed in the prereg)
1,936,228 REAL depth-2 leaf boards: champion [-266,+7234], `winsc2` [-510,+7186], **zero wraps**,
headroom >= 25,533. A purely-negative term makes the wrap SAFER (the binding side is the positive max).
⚠ Adversarial hill-climb reaches +141,006 for the SHIPPED champion, so the wrap is not dead code by
construction. Full detail: [[dr-mario-int16-wrap-headroom]].
