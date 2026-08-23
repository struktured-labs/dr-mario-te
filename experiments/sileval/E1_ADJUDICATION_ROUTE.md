# (c) RESULT — an adjudication route EXISTS, and it corrects my earlier verdict

**2026-08-23, swap lane. Pure offline pass over population A's banked rows.
Zero box time. No population-B row exists.**

## ⚠ FIRST: I was wrong, and here is exactly why

I reported "E1 is not adjudicable" and "a faster cadence does not fix it".
**Both were wrong**, from one root cause with two heads:

1. **I keyed on the wrong signature.** I asked "is a side at 0 viruses?" — but
   a match that ends by TOP-OUT never satisfies that, and top-outs are how
   almost every match here ends. The right key is the MODE.
2. **My decoder was silently discarding the evidence.** `find_base()` requires
   the virus counters to AGREE with the board contents, and refuses otherwise —
   which is exactly what happens during the end-of-match animation. It dropped
   ~15% of samples, and **mode `$07` was inside every one of them.** The
   "15.3% undecodable" figure I reported was an artifact of that check, not a
   property of the data: with a signature-verified fixed base, **0.0% of 4,589
   samples are undecodable.**

The check shared the fault's assumption. That is measurement rule 1's shape,
and it cost a day.

## The route

| mode | meaning | winner rule |
|---|---|---|
| `$03` | a side CLEARED its board | the side at 0 viruses won |
| `$07` | a side TOPPED OUT | the side with occupied cells in playfield rows 0-2 lost |
| `$08` | level-start screen (new match) | boundary marker, no result |
| `$04` | play | — |

`occ_top3` is a sound top-out discriminator here: across 108 top-out samples
the losing side reads 6-19 occupied cells in rows 0-2 while the winning side
reads **0**, i.e. viruses are never placed in the top three rows at this level,
so a nonzero reading means stacked pills.

## Coverage, and the cadence law

Full-corpus census (255 OK rows, 4,589 samples, 0 dropped):

`$04` 4312 · `$08` 145 · **`$07` 124** · **`$03` 4** · `$02` 2 · `$01` 2

- 993 match boundaries; **128 end-states captured = 12.9% of matches.**
- Implied end-of-match window **W ≈ 2.5 s**.

Capture rate should then be `min(1, W/T)` for cadence `T`. Tested against the
5 s probe, which is an independent cadence:

| cadence T | predicted W/T | **observed** |
|---|---|---|
| 20 s (population A) | 12% | **12.9%** |
| 6.86 s (probe) | 36% | **33.3%** |

The model holds across a 3x change in cadence. ⇒ **cadence DOES fix capture,
and the requirement is quantified: T ≤ ~2.8 s for ≥90% of match endings.**
Our save-state+1.3 MB-scp sampler floors out at 6.9 s, so reaching ~2.8 s means
a cheaper detector — poll the ~7 KB SCREENSHOT for the end-of-match frame and
take a save-state only on detection — not merely a smaller `SAMPLE_SECS`.

## ⚠ THE BIGGER PROBLEM: E1 is near-degenerate

Of the 128 captured end-states, adjudication gives:

| outcome | n |
|---|---|
| **P2 wins** (108 by P1 top-out, 3 by clear) | **111** |
| P1 wins | 1 — and it reads 48/48 viruses, a fresh match, so it is a transition artifact, not a win |
| ambiguous | 16 (12.5% of captured endings) |

Per arm: ship 59 P2 / 0 P1, slice 52 P2 / 1 doubtful P1.

**P2 wins ~99% of matches.** This is not a capture bias toward one ending type:
both ending types ($07 top-outs AND $03 clears) show P2 winning. It matches
`REPORT.md`'s own note that P2 (the copro side) is dominant in this CvC setup.

Consequence, and it is independent of readability: **if the winner is ~99%
constant, paired discordance between ship and slice cannot exceed ~2%** — below
the ~4% the prereg's power table was sized to detect. So even with a perfect
scorer and 100% capture, **E1 as specified is underpowered by construction at
n=240, let alone n=126.**

DRP1SLICE is a P1-side change and P1 essentially never wins, so the endpoint has
almost no room to move in the direction the hypothesis predicts.

## What would make E1 viable

1. **Adjudicate ALL matches, not just match 1.** There are 993 matches in
   population A versus 126 usable pairs — roughly 8x the n, pairing on
   (seed, match index). The prereg already allows matches 2..k as secondary;
   this promotes them.
2. **Fix the detector before the cadence** (screenshot-triggered save-state).
3. **Reconsider the measurand.** With a 99:1 outcome, a *margin* endpoint —
   time-to-top-out for P1, or virus count at P1's death — carries far more
   information per match than a binary winner, and is readable from the
   existing sampled timeline without catching the ending at all.

(3) is the one I would actually push: it makes the primary readable from data
we ALREADY have, at n≈993 matches, and it is the same underlying claim — the
removed NMI overrun tail should help P1 survive longer near death.

## Status of the other endpoints
**E1b is readable now** — `occ_top3` near-death is computable on every sample,
0 dropped. E2 (wedge monitor) and E3 (tallies) likewise.
