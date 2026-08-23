# PREREG — E4, a margin endpoint for DRP1SLICE (AMENDMENT 2)

**STATUS: REGISTERED 2026-08-23, BEFORE COMPUTATION.** No E4 statistic has been
computed on population A or anywhere else. The only quantity used to size this
document is a planning SD taken from the **independent old-box 5 s probe**
(3 cycles, ship arm, 12 complete matches — not population A). The registering
commit contains no E4 number, and that is the timing proof.

## Why a new measurand (the honest framing)

**I am selecting this endpoint after discovering the registered primary is
degenerate, using data I already hold.** That is a legitimate move and also the
classic route to a finding that does not replicate. The controls are:

1. This document is committed before any E4 computation.
2. **Population A (126 pairs / 993 matches) is EXPLORATORY for E4.
   Population B is the CONFIRMATORY out-of-sample test.** They are reported
   separately and are never pooled into one number.
3. Direction, estimator, resampling unit, and decision threshold are fixed here.

Why E1-binary cannot carry the claim: of 128 captured match endings, P2 won 111
and P1 won 0 (the single apparent P1 win reads 48/48 viruses — a fresh match,
i.e. a transition artifact). With a ~99% constant winner, paired ship/slice
discordance cannot exceed ~2%, against a power table sized for ~4%. No scorer
fixes that.

## The measurand

**Unit of observation: one COMPLETE match** — a segment bounded by a detected
match boundary on BOTH sides (a boundary = either side's virus counter
increasing, i.e. a new match began). Partial segments are excluded by
construction: the first segment of a cycle begins mid-match (the F1 restore
lands in live play) and the last is truncated by the end of the cycle.

**E4a (PRIMARY): P1's virus count at the last sample of the match.**
How much of its board P1 had cleared when the match ended. Readable on ~100% of
complete matches and **requires no end-of-match frame to be captured** — which
is the entire point, given the ~2.5 s ending window.

**E4b (SECONDARY): P1's minimum virus count within the match** — deepest
progress reached.

**Hypothesised direction: SLICE LOWER than SHIP on both** (P1 clears more before
dying). Registered as a two-sided test regardless.

## Why this is NOT a tempo endpoint (the prereg's hard exclusion)

The original prereg excludes any tempo/duration/latency endpoint, because
DRP1SLICE has two documented phase dials that move tempo without being the
mechanism. E4 is a **board-progress** measure, not a duration: it asks how far
P1 got, not how long it took. Match duration / time-to-death is **deliberately
NOT used** for exactly this reason.

Two residual pathways by which tempo could still leak in. Per measurement rule 2
both are signed here, in advance:

1. **Sampling staleness (E4a).** The last sample precedes the actual death by up
   to one cadence. Slice completes slightly MORE matches per cycle (3.94 vs
   3.84 — descriptive E3), i.e. slightly shorter matches, so its last sample
   sits a slightly larger fraction of the way from the end ⇒ slice reads
   slightly HIGHER (less progress).
2. **Observation count (E4b).** Shorter matches ⇒ fewer samples ⇒ fewer chances
   to observe a low minimum ⇒ slice reads slightly HIGHER.

**Both residual biases run AGAINST the hypothesised direction.** A positive
result is therefore conservative; a null is not explained away by them.

## Estimator, pairing, uncertainty

- **Pairing:** by (seed, match ordinal within the cycle), using ordinals present
  in BOTH arms for that seed.
- **Estimator:** difference of means, `mean(slice) - mean(ship)`, over paired
  matches; negative = favours slice = the hypothesised direction.
- **Uncertainty: bootstrap resampling SEEDS, not matches** — matches within a
  cycle share a board, a cart boot and a session and are not independent.
  10,000 resamples, 95% percentile CI.
- **Decision threshold:** CI excludes 0 in the predicted direction ⇒ POSITIVE.
  CI spans 0 ⇒ NULL. CI excludes 0 in the wrong direction ⇒ NEGATIVE. No other
  reading, and no subgroup hunting.

## MDE at the n we actually have

Planning SD from the independent old-box probe: per-match P1 end count
mean 42.7, **SD ≈ 5.1** (n=12 — crude, and stated as crude). With ~4 complete
matches per seed, the per-seed mean has SD ≈ 5.1/√4 ≈ 2.6, and the paired
difference SD ≈ 2.6·√2 ≈ 3.6. At 80% power, two-sided α=0.05,
`MDE ≈ 2.8 · 3.6 / √n_seeds`:

| population | n seeds | MDE (viruses) | as % of the ~42.7 mean |
|---|---|---|---|
| A (exploratory) | 124 | **≈ 0.9** | ~2.1% |
| B (confirmatory, if full) | 240 | **≈ 0.65** | ~1.5% |

The realised SD will be recomputed and reported at analysis; if it differs
materially from 5.1 the MDE is restated, and the restatement is disclosed.

## Scope and carry-over

- The two frozen ship rows (48757, 45431) contribute **zero complete matches**
  and are excluded by construction, not by hand.
- **E1-binary is RETAINED as a declared secondary with its degeneracy stated.**
  A 111:1 P2 dominance is itself a finding about the CvC harness and belongs
  beside REPORT.md's "P2 copro dominant" note. It is not deleted.
- E1b, E2, E3 carry over unchanged.
- Arms, carts, core, seeds and seed order, cycle and cadence, and all seven VOID
  conditions are unchanged from the original prereg and AMENDMENT 1.

---

# ERRATA (2026-08-23, after computation) — E4b was never a distinct statistic

**E4b (P1 minimum virus count within the match) is identical to E4a (P1 count at
the last sample) BY CONSTRUCTION, and I should have seen that before
registering it.**

P1's virus count is monotonically non-increasing within a match — viruses are
only ever cleared, and VS garbage adds pills, never viruses. Verified on the
corpus: **0 of 2,244 within-match steps show an increase, across 740 complete
matches.** So LAST == MIN in every match, and E4a and E4b return the same number
to the last decimal.

Recorded rather than quietly dropped. The consequence is small — the two were
registered as primary and secondary, not as independent confirmations, so no
result is double-counted — but "two endpoints agreed" would have been a
meaningless sentence and is not one I get to write.

The registered residual-tempo argument for E4b (observation count) is moot for
the same reason: a minimum over more samples cannot go lower than a monotone
sequence's endpoint.

**E4a stands exactly as registered.** A genuinely distinct secondary would have
to measure something the monotone count cannot — e.g. P1's peak `occ_top3`
(how close to death it came), which is NOT registered here and is therefore not
reported as an endpoint.
