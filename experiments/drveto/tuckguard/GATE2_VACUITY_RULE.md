# Gate 2 vacuity rule — FIXED BEFORE THE RESULTS LAND

All four arms run on **one CRN seed (114)**. A mutant kill on a single seed can pass
**VACUOUSLY**: if `mut_approach` or `mut_nomargin` never encounters the condition it is built
to break on that seed's board sequence, the arm looks clean and the gate reports PASS **for the
wrong reason**. R96 in its purest form — *a mutant never given the chance to fail has not been
shown able to fail.*

## Every verdict must be reported WITH its exercise counts

* **engaged descriptors** per arm (`TUCK_C2 != $FF`, legal values — col 0-7, row 0-15)
* **vetoes fired** on the tg1 arm
* **placements** total, cross-checked `pills ≈ playFrames/100`
  ⚠ with the `$03A7` correction folded in: that counter is **per-round and non-monotone**, so a
  naive value-change count over-reports by ~2-3x.

## Decision rule (fixed now, before the numbers)

> **< ~10 vetoes, or < ~20 engaged descriptors ⇒ the verdict is VACUOUS, not PASS**, and the
> gate must be re-run across more seeds.

**"No failures observed" must never stand in for "the mutant could not fail" when the honest
reading is "the mutant was never asked."**

Expectation for calibration, not a target: 18,000 frames at ~100 frames/placement ≈ **180
placements**, so the counts may well be ample — **but they are reported, not assumed.**

## Same treatment for the safety-property gate

*"On every vetoed descriptor the placement was identical to no-tuck"* is meaningful only if
**there were vetoed descriptors**. The count goes in the same sentence as the verdict.

## Modes reported SEPARATELY, never pooled

`find_tuck` (geometric) and `synth_tuck` (`MINROW=5`, manufactures the very condition under
test). Pooling would let a manufactured rate pass as a natural one.
