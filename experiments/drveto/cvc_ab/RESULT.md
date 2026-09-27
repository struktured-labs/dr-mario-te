# DRPROPH CvC L20 A/B — THE RUN PRODUCED NO USABLE ESTIMATE. AN AUDIT OF WHY.

**This document is an INSTRUMENT AUDIT, not a result with caveats. There is no usable estimate
of DRPROPH's effect in this run, in either direction, and no number in it should be quoted as
one. The experimental question is OPEN and will be answered by a RE-RUN once the instrument is
trustworthy.**

Read the three sentences under "How much to trust this" before anything else.

---

## What the run actually produced — the durable output

The instrument findings, not the effect estimate:

1. **The poll and the video are BOTH pixel-based and neither can arbitrate the other.** They
   disagree in both directions at arm-dependent rates: the poll over-flags champion deaths 45%
   (control) / 20% (treated), and MISSES 53% / 87%. There was no ground truth in the
   measurement system.
2. **The video adjudicator's "validated 8/8" does NOT cover DRPROPH=1 arms** — that validation
   ran on non-pulsing footage, and the detector's test is a persistence HOLD.
3. **The observer contaminated the observed.** The A/B poller wrote screenshots into the very
   directory `freeze_watch` hashes to detect a frozen screen, manufacturing **nine hourly
   "freezes"** (intervals alternating 60.57/61.57 min), with **zero in the 11.7 h after the
   poller stopped**. Only the interval structure betrayed it.
4. **A stale cache hid two in-window reloads from the primary.** `refresh=False` fetched only
   when the cache was absent; it was written once at 21:17Z with 5 events and never updated.
   **The code was correct and the data was old**, so nothing failed and nothing looked wrong.
5. **DRSEATLOG now exists and is gated** — a cart-side latch recording the ROM's own loss
   condition every hook, independent of pixels, with its transition-sampling mutant killed
   10/10. It is what makes a trustworthy re-run possible.

**That list is worth more than the number would have been.**

## How much to trust this document

* **One blinding leak exposed the full per-arm contrast at ~40% of target N to both analysts.**
* **The run overran its stop by 7.5 h and was truncated blind** at T_stop 03:03:06Z (705
  out-of-protocol rounds discarded).
* **A stale cache hid two in-window reloads from the primary**, so the first report's "zero
  reloads, zero exclusions" was false; corrected denominators are noproph 128 → **124**, proph
  120.

Smaller items, enumerated rather than counted: two further blinding leaks (a cosmetic gate that
printed its inputs; a pooled tally reconstructable by repetition), and one blinding-adjacent
floor-gate event. **Damage bounded and the argument is strong: the stopping rule was
data-independent and the analysis pre-registered, so no decision either analyst took was
biasable.**

## Why no estimate survives

* **The pre-registered primary is INVALID BY CONSTRUCTION.** ADDRESSABLE is a
  **post-treatment** stratum — the treatment's own lateral push can alter gate occupancy — so
  conditioning on it is a **collider**. Stratum proportions differ maximally between arms
  (100% vs 54%), and conditioning induced an association in the favourable direction.
* **The unstratified secondary rests on an arm-dependent instrument.** Disagreement is
  predicted by ARM even after matching on geometry (Mantel-Haenszel +0.275, CI [+0.070,
  +0.479] by duration; +0.246, [+0.043, +0.449] by viruses-left; both R96 controls pass). The
  asymmetry is **unexplained** — geometry does not account for it, and the pulse hypothesis was
  tested and **not supported** (period-2 alternation is *lower* on the treated arm, 0.0030 vs
  0.0100 median).

### The numbers, recorded for completeness only

⚠ **Neither row is an estimate. Neither leaves this document.**

| quantity | value | status |
|---|---|---|
| stratified primary (ADDRESSABLE/round) | recomputed against corrected denominators | **INVALID as an estimand — post-treatment stratum. NOT TO BE QUOTED.** |
| unstratified (all champion deaths/round) | treated higher than control | **A BOUND AT BEST — inherits an arm-dependent instrument. NOT TO BE QUOTED.** |

## Regime label, which rides on any future comparison

L20, CvC, start-of-round pile-up population (82-83 viruses left of 84) — **distinct from the
banked L20 farm's median 41 left**. On silicon P2 is the copro champion; any emulator
substitute must reproduce that or say it does not.

## What the re-run needs

A **game-state arbiter** that does not share the pixel failure mode. DRSEATLOG supplies the seat;
its **latch extension** (specced, gated behind a 38 h / k ≤ 3 soak bar) would supply the death
geometry. Until then the video detector's arm-dependent error is uncharacterised, and any A/B
built on it inherits that error.
