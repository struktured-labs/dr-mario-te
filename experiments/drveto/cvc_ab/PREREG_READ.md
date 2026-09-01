# PRE-REGISTRATION: how the DRPROPH L20 A/B will be read

Registered 2026-09-01T00:34Z. At registration the noproph L20 arm had **not started**
(block 0 = proph, switching ~00:49Z) and **zero noproph deaths existed**. Strata
definitions are fixed separately in `PREREG_STRATA.md` and are not restated here.

Regime label, attached to every number: **L20, CvC, start-of-round pile-up population
(82-83 viruses left of 84), distinct from the banked L20 farm's median 41 left.**

## Primary endpoint

**ADDRESSABLE champion-seat deaths per completed round**, by arm.

* numerator: champion (P2) deaths that are **VIDEO-CONFIRMED** and fall in the
  ADDRESSABLE stratum;
* denominator: completed rounds observed in that arm.

DRPROPH can only act on ADDRESSABLE deaths, so this is the only contrast that is about
the mechanism. UNADDRESSABLE and OTHER counts are published alongside but never pooled
into it.

## The endpoint is VIDEO-CONFIRMED, and that is a cost not a formality

The poll disagreed with the video on 1 of 6 champion deaths already scored, so the poll
is disqualified as the count. It remains the INDEX: it says where to look. Every
candidate death gets a video pass — segment cut, ~280 frames decoded, reset-bounded
hold search, then the parent board scored. **Budget: roughly 1-2 minutes per candidate
death, and the proph arm is producing ~8 candidates per 24 rounds.** At the target N
below that is on the order of 40 video passes and ~1 hour of processing. If that makes
the block slower, it is slower.

## Scoring both arms with ONE code path

The noproph arm is scored with the **identical** transcribed `proph_trigger` condition
(`eligibility.py`, validated on 15 hand-computed boards). On that arm the trigger cannot
fire, so what is being computed is **counterfactual eligibility** -- "would DRPROPH have
had a move here" -- which is exactly the denominator that makes the arms comparable.
The scorer is not re-implemented or re-tuned between arms. **If it needs a fix, it is
fixed once and BOTH arms are re-scored from the banked frames.**

## Target N

From the standing power table (two-proportion, 80% power, alpha 0.05) with DRPROPH's
measured in-regime rescue of 66.7%, so that a rate `p0` falls to `p0 x 0.333`:

| p0 = ADDRESSABLE champion deaths per round, noproph | rounds needed per arm |
|---|---|
| 0.15 | ~150 |
| 0.20 | ~101 |
| 0.30 | ~62 |
| 0.40 | ~44 |

The proph arm currently sits at 4 ADDRESSABLE deaths in 24 rounds = **0.167/round**. If
DRPROPH works, noproph should be higher, so `p0` in the 0.25-0.40 band is the planning
assumption and **the target is ~60-90 completed rounds per arm**. Rounds run ~100/hour,
so that is roughly one hour of block time per arm -- about 4 hours of alternating
wall-clock. This is a far friendlier requirement than the pessimistic rows of the
original table precisely because exposure measured 80% rather than the 10-20% feared.

## Stopping rule

Run until **each arm has >= 60 completed rounds with all candidate deaths
video-confirmed**, or **6 hours of wall clock**, whichever comes first. Analyse **once**,
at the stop. No interim comparison decides whether to continue -- the stop is on N and
clock only, never on the result.

## R49: no partial comparisons

**The proph arm's numbers will not be quoted against a partial noproph arm at any point,
in any form**, including "so far it looks like". Until both arms reach the stop, reports
state per-arm descriptive counts with their arms labelled and explicitly decline the
contrast. The proph arm's existing 8/24 poll figure is superseded by video-confirmed
counts and is not a baseline for anything.

## Secondary, pre-specified: did the mechanism FIRE, or merely qualify?

A mechanism that fires and fails is a different finding from one that never engages, and
they have different fixes. Trigger ARMING is determined by the parent board and is
already computed (all 5 scored deaths had `fo3 = 1`, so the trigger armed on every one).
But `proph_pulse` presses only inside the driver's **no-answer window** -- if the search
publishes in time, the adopt path runs and DRPROPH never presses. So arming does not
imply pressing.

The observable consequence of a press is **lateral motion of the fatal capsule in the
throat before it locks**. For each ADDRESSABLE proph-arm death, 60 fps frames spanning
spawn-to-lock will be decoded and the active capsule's column tracked:

* **FIRED_AND_FAILED** -- capsule moves laterally, still locks fatally;
* **NEVER_ENGAGED** -- capsule shows no lateral motion before locking;
* **INDETERMINATE** -- lock window too short or the capsule not resolvable.

Reported as a split with its own denominator. ⚠ Stated in advance: at L20 the lock
window is ~8-10 frames (~0.15 s), so INDETERMINATE may dominate; if it does, that is
reported as an instrument limit, **not** converted into evidence for either branch.

---

## AMENDMENT, 2026-09-01T00:45Z — still before the noproph arm started

Two additions on the team lead's ruling. Both are registered **before any noproph death
exists**, and both constrain how a result will be READ rather than how it is collected.

### A. What a NULL would mean — fixed now so the reading cannot drift

The video shows the fatal capsule is visible in the throat for **ZERO frames before it
locks** at 60 fps (2/2 deaths), with `fo3 == 1` on every scored death. The capsule
spawns already at rest and locks with no observable travel. **DRPROPH's entire working
headroom is therefore the lock window itself — roughly 8-10 frames at L20.**

⇒ **A null in this A/B would mean "there is not enough TIME", NOT "the veto logic is
wrong."** Those imply completely different repairs: an earlier trigger edge (act on the
PREVIOUS pill, before the ledge that causes the at-rest spawn is built) versus a better
direction choice. The direction logic is not what a null here would indict, and it will
not be described as such.

### B. L20 is a CONSERVATIVE regime for DRPROPH — the evidence is asymmetric

If the mechanism's headroom is the lock window, and higher levels shorten that window
(faster gravity), then L20 gives DRPROPH **less** time to act than L11 does. Therefore:

* **a POSITIVE result at L20 is STRONG evidence** — the mechanism worked despite the
  least favourable timing, and L11 play would give it more room, not less;
* **a NULL at L20 is WEAK evidence about L11 play** — it is consistent with "insufficient
  time at L20 specifically", and does not establish that the mechanism fails where the
  window is longer.

This asymmetry is stated in advance so that a null cannot be reported as a general
refutation, and rides alongside the standing regime label.

### C. The PROPH_DIR / press-stream instrument is a PRE-COMMITTED FOLLOW-UP, not a rescue

The FIRED_AND_FAILED vs NEVER_ENGAGED split came back INDETERMINATE and cannot be
resolved from footage; it needs the emitted `PROPH_DIR` byte or the `$F5`/`$F8` press
stream. **It is deliberately NOT being built now.** The A/B answers the program's actual
question without it, and if the A/B is positive the split is spend on a question nobody
needs answered.

**It is hereby pre-committed as the FIRST FOLLOW-UP, conditional on a NULL result.**
Recorded here so that building it after a null is visibly the registered plan rather than
a post-hoc rescue of a disappointing outcome. Tonight's evidence budget goes to completed
rounds instead.
