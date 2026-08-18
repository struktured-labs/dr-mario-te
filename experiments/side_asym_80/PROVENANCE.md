# What the #80 claim actually was — recovered 2026-08-18, before the re-test finished

Written while the re-test arms were still running, and committed separately from the
results so it can be dated independently of them. Nothing here depends on the
re-test's outcome.

## The claim is exactly reconstructible, and it is 10 events

The stored headline is *"6.0% vs 0.67% death rate by side, p=0.02"*. It is **not**
recoverable from `fourway_result.json` (which averages the side away), but it IS
reconstructible arithmetically, and the reconstruction is exact:

```
across the two adversary arms: 80 held-out seeds + 70 transfer seeds  = 150 seeds
                               5 champion deaths  + 5 champion deaths = 10 deaths
split by the champion's seat:  9 on one side, 1 on the other

  9/150 = 6.00%      1/150 = 0.667%      two-sided exact binomial p = 0.0215
```

All three published figures fall out of a **9-vs-1 split on ten death events**. The
`0.67%` is `1/150`, and `p=0.02` is `P(|X-5| >= 4)` for `X ~ Binom(10, 0.5)` =
`22/1024 = 0.0215`. There is no other combination in this lane's numbers that
produces all three.

**So the claim is a real computation, not a transcription error — and its entire
evidence base is ten Bernoulli trials.**

## Direct confirmation of one half of it

`dr-mario-qa-wt/experiments/adversary_t3/cosim_handoff_5seeds.json` retains the
per-game side label for the five held-out-arm deaths (recovered by deterministic
replay, and the file states the replay matches `fourway_result.json` exactly):

| seed | dying_champ_side |
|---|---|
| 6045 | 1 |
| 6049 | 1 |
| 6059 | **0** |
| 6065 | 1 |
| 6077 | 1 |

4-vs-1, champion dying more often when seated at **side 1** — the seat that moves
**second** in `vs_harness.play_match`. Direction noted as a fact; per
measurement-rules #19 it is not a direction this n can support, and the re-test was
registered direction-free.

## ⚠ The project had already written the caution, and the claim was filed anyway

That same file carries an explicit warning, in the QA lane's own words:

> *"dying_swap is 1 for 4 of 5 seeds (6045,6049,6065,6077) and 0 for one (6059).
> Binomial test against even odds: p=0.375 — statistically indistinguishable from 5
> coin flips. **Do NOT read this as a P1/P2 side asymmetry or any kind of finding**;
> it is kept per-seed only because it is needed to reproduce/replay each game, not
> because the split itself means anything."*

The two statements are about the same phenomenon and reach opposite conclusions:
p=0.375 "not a finding" on the 5-death subset, versus p=0.02 "a finding" once the
transfer arm's 5 deaths are pooled in. Pooling the transfer arm is defensible on its
own terms — disjoint seeds (6xxx vs 7xxx) and a genuinely different champion lineage
(`pre20`) — so this is not a case of one lane being careless. **It is
[[dr-mario-measurement-rules]] #20, the retrieval failure, in its cleanest form: the
warning was recorded, correctly, in an artifact nobody read before filing the task.**

⇒ The operational lesson is independent of how the re-test comes out: **a caution
written into a data file is not a caution attached to the number.** It travelled
with the replay fixture, not with the statistic, and the statistic is what got
filed.

## What this does to the re-test

Nothing — the design and decision rule were committed (056934a) before this
reconstruction was done, and neither is amended. But it sharpens what a null would
mean. A 9-vs-1 on ten events is precisely the regime measurement-rules #13 names:
*a p=0.02 side asymmetry found by looking, which failed to replicate on fresh
seeds.* The re-test is powered at 3.0x the claimed effect, so it can now distinguish
"underpowered" from "absent" — which the original design, at a CI half-width
(±5.39 pp) wider than its own claimed effect (5.33 pp), could not.
