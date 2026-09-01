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

---

## AMENDMENT 2, 2026-09-01T00:55Z — RE-SIZE. Still zero noproph deaths in existence.

### Why changing a stopping rule here is legitimate, recorded so it is auditable

Changing a stopping rule after seeing data is normally forbidden. Three properties make
this the exception, and all three are checkable after the fact:

1. **Exposure is a NUISANCE PARAMETER, not the treatment contrast.** What was
   re-estimated is the event RATE (how often an ADDRESSABLE champion death occurs at
   all), never the difference between arms.
2. **Zero noproph data exists.** The contrast is entirely unobserved, so no stopping
   decision can possibly have been informed by it.
3. **The re-size runs AGAINST my own interest** — it makes the experiment longer and
   harder. That is the direction that cannot be gamed.

The correction that forced it (same code path, more deaths):

| | n=5 | n=9 |
|---|---|---|
| ADDRESSABLE | 4 | 5 |
| UNADDRESSABLE | 1 | 4 |
| **exposure** | **80%** | **56%** |

### The sizing, verified independently

Measured on the proph (TREATED) arm: 5 ADDRESSABLE deaths / 43 rounds =
**0.116 per round**.

* **Conservative (the plan is sized against this):** treat the observed rate as if it
  were the control rate — i.e. assume the mechanism is weak — and require power to detect
  a 66.7% drop from it, 0.116 -> 0.039. **n = 186 rounds per arm.**
* For contrast only, the arithmetically exact reading of a rate measured on the treated
  arm: if the gated 66.7% rescue is real, the control rate is 0.348 and detecting
  0.348 vs 0.116 needs only **n = 51 per arm**. Not used for sizing — it assumes the
  answer.

The original **60-round floor gives ~7 events per arm and is ~3x too small.** At that N
the design would most likely return a null that means nothing, and Amendment A would then
misread it as "not enough time" when it actually meant "not enough rounds".

### FEASIBILITY — answered NOW, not at the stop

**Yes, comfortably.** Rounds run at 103/h (measured). With alternating blocks each arm
gets half the clock, so **6 h yields ~309 rounds per arm** — clear of the 120 floor and
clear of the 186 conservative target.

⚠ **My earlier cost estimate was wrong in the safe direction: a video pass takes 10.9 s
measured, not the 1-2 minutes this document first claimed.** At 12 poll-flagged deaths
per 43 rounds, 6 h implies ~86 candidates per arm, ~172 total, ~32 minutes of processing.
**Video confirmation is not the bottleneck.**

The real constraint is that the soak runs unattended but the ANALYSIS requires an
operator. If the session ends before the stop, the banked CSV and footage still support
scoring later — nothing is lost, it is only deferred.

### Amended stopping rule

1. **The 6-hour clock is the binding constraint**, not a round floor. Blocks keep
   alternating as now.
2. **Floor for a PRIMARY verdict: 120 completed rounds per arm.** Below that the contrast
   is reported as **UNDERPOWERED-DESCRIPTIVE** and a GO/NO-GO is refused — an explicit
   third outcome, registered now rather than invented at the stop.
3. **The effect estimate is reported with a confidence interval regardless of n.** A wide
   CI containing both zero and the gated 66.7% is an honest, useful result; "null" is not.
4. **Analyse RATE PER ROUND, never raw counts.** Alternating blocks make unequal round
   totals near-certain.
5. **State what n the clock actually bought next to the n it needed** (against both 120
   and 186), in the headline of any result.

---

## AMENDMENT 3, 2026-09-01T01:20Z — reload accounting. Decided blind to the contrast.

A freeze fired at 01:13:12Z and freeze_watch auto-reloaded at **01:13:37Z, 23 minutes
into the noproph block**. Same legitimacy basis as Amendment 2: this is an **accounting
rule about a nuisance EVENT**, the treatment contrast is not used to decide it, and it is
recorded before the stop.

### The hazard

The round boundary rule is "any INCREASE in virus count". **A core reload produces exactly
that**, so a freeze+reload is indistinguishable from a round end. Left alone it fabricates
a boundary, inflating the denominator of whichever arm froze and biasing that arm's
per-round death rate **DOWNWARD**. The arm that froze is **noproph — the control** — so
this error direction makes DRPROPH look *worse*, not better. It is still a corrupted
denominator and is excluded either way.

### RULE (in force)

1. **Rounds whose `[start,end]` interval spans a `RELOADED` timestamp are EXCLUDED**,
   identified structurally from `freeze_watch.log` (a real event boundary per R95, never
   a heuristic on the virus series). `reloads.py` parses those timestamps.
2. **The round immediately following a reload is also excluded** (partial, corrupt
   duration).
3. **Exclusions are reported per arm** with every result.
4. **Freeze/reload counts are reported PER ARM as a secondary.** Unequal freeze rates
   make the denominators non-comparable, and that asymmetry is itself a finding about the
   builds; it does not get to stay invisible.

### What actually happened to the data, measured

The freeze did **not** fabricate a boundary in the banked series, for a reason worth
recording: during the frozen interval the poller's samples came back with **unreadable
counters** (`p1`/`p2` empty, 01:12:18Z-01:13:11Z), and unreadable samples are skipped as
gaps by construction — so no spurious INCREASE was ever seen. The reload timestamp lies
**after the last banked sample**, so zero rounds required exclusion from segment 1.
The rule stands for the rest of the run regardless.

### ⚠ THE CONTROLLER DIED ON THE FREEZE — the more serious defect

`sample()` let a `subprocess.TimeoutExpired` escape when ssh blocked against the frozen,
mid-reload box. The exception killed the loop and **the noproph arm silently stopped
accumulating for ~5 minutes**. A soak controller that cannot survive the exact event it
exists to observe is a worse bug than the accounting one. Fixed: every remote call now
degrades to a gap and never raises, the arm-switch assert became a retry-then-warn, and
the sample loop has an outer guard. Restarted on the **noproph** arm so the interrupted
arm continues; the pre-outage series is banked separately as `ab_samples_L20_seg1.csv`
and the segments are not silently concatenated.

### ⚠ AND AN R49 LEAK OF MY OWN, disclosed

`analyze_ab.py` printed both arms' rates side by side as soon as both existed — a partial
comparison the pre-registration forbids, and **I saw it** (33 vs 51 rounds, both far below
the 120 floor; the script's own verdict line read UNDERPOWERED). It is not used, not
reported, and carries no weight in anything downstream. The fix is structural rather than
a resolution to be careful: **the script now WITHHOLDS the contrast until every arm clears
the floor**, printing per-arm descriptive counts only. Discipline that lives only in the
analyst's head is not discipline.

---

## AMENDMENT 4, 2026-09-01T01:25Z — obligations created BY the leak

Recorded because the leak in Amendment 3 changes what I am allowed to do for the rest of
the run, not merely what happened.

### Why the leak's damage is bounded — the reasoning, so it is not mistaken for luck

**A peek can only bias a study through a decision it is able to influence.** The stopping
rule here is **data-independent** (>=120 rounds/arm, or a 6 h clock) and the analysis is
pre-registered. No interim value can move either. The glance therefore had nothing to act
on. That is the pre-registration doing its job, and it is the reason for having written it
before running anything.

### THE RESIDUAL RISK IS REAL: I now know the direction

Every remaining judgment call — exclusions, scoring edge cases, which frames adjudicate,
how a malformed sample is treated — **must be made by a WRITTEN RULE, not by discretion.**

**If a situation arises that this pre-registration does not cover: write the rule down,
state explicitly that it was written after the leak, and then apply it.** Do not resolve
it on judgment in the moment. A rule written after a peek and labelled as such is
auditable; a judgment call made after a peek is not.

### MANDATORY IN THE FINAL WRITE-UP

The leak is disclosed **in the write-up itself**, not only in a commit log. A reader
assessing the result is entitled to know that the analyst saw a partial contrast, when,
what it showed, and why the design bounds the damage. Specifically to be stated:

* `analyze_ab.py` printed both arms' rates side by side as soon as both existed, and I
  saw it, at 33 vs 51 rounds — both far below the 120-round floor;
* it was not used and carries no weight downstream;
* the stopping rule is data-independent, so the peek had no decision to influence;
* the fix was structural (the contrast is now withheld until every arm clears the floor),
  not a resolution to be more careful;
* every rule written after 01:20Z is labelled as post-leak.

### Rule written 2026-09-01T01:30Z — POST-LEAK, per Amendment 4: SEGMENT POOLING

Situation not covered by the pre-registration: the controller's death at the 01:13Z
freeze split the L20 series into two files. Rule, written down rather than resolved on
judgment, and labelled post-leak because it was written after the R49 glance:

* **Segments are POOLED PER ARM.** Same cart, same core, same level — the outage is an
  interruption in *observation*, not a change in *condition*.
* **A segment boundary is treated as a BLOCK boundary**, so no round is ever inferred
  across it. This is structural rather than a promise: the restart begins a fresh
  `(arm, block)` key and the transition detector only joins samples within one key.
* **The outage-spanning round is excluded** by Amendment 3's reload rule, unchanged.

It is an accounting rule about an interruption; it does not touch the contrast, and it
was applied identically to both arms.

---

## AMENDMENT 5, 2026-09-01T01:35Z — SECOND R49 LEAK, through a COSMETIC gate

### What happened

The floor gate added in Amendment 3 **suppressed the comparison LINE while printing both
arms' endpoint rates on adjacent lines**, under a heading that said the contrast was
WITHHELD. Two per-arm rates side by side **is** the contrast; subtraction is not a barrier.
The team lead ran the script to find a stop signal and saw them. Reported at 15/51 and
15/47 — both far below the floor.

**A gate that withholds a LABEL while printing its INPUTS is a label, not a gate.**

This is the second leak through the same defect, and the first one I fixed "structurally"
was the one that created it. The audit test that should have been applied to the fix, and
is now applied to every script touching this data:

> **Could a reader who cannot see the withheld quantity still COMPUTE it from what IS
> printed?** If yes, it is not withheld.

### Same defect found in two more places by that test

* `analyze_ab.py`'s **per-block detail lines** printed a per-arm outcome tally
  (`{'TOPOUT_P2': 8, ...}`) and every round's outcome with its arm — the endpoint
  numerator, handed over directly.
* `stratify.py` printed **`arm=` on every death** and its strata, which is the ADDRESSABLE
  numerator per arm.

### The fix (structural, and audited this time)

Below the floor, output is limited to quantities from which the endpoint **cannot** be
reconstructed:
* **allowed** — rounds per arm, hours per arm, reloads per arm, exclusions per arm,
  progress-to-floor, and the outcome tally **POOLED ACROSS ARMS**;
* **withheld** — every per-arm death count, every per-arm rate, the arm column on
  individual deaths, and per-arm strata.

Rounds per arm stay visible because stopping requires them and, on their own, they yield
nothing; the moment a per-arm death count joins them the endpoint is one division away,
so per-arm counts are pooled instead. `--unblind` exists for the stop and **stamps its use
into `UNBLIND_LOG.txt`** with a timestamp and the round counts at the time.

### Disposition

Damage bounded by the same argument as before, and it still holds: **the stopping rule is
data-independent** (>=120 rounds/arm or the 6 h clock), so neither of us can act on what we
saw. Both arms were far below the floor. Nothing is invalidated.

### MANDATORY IN THE WRITE-UP — now TWO leaks, disclosed as two

A reader is entitled to both, because two independent leaks through one defect is a
materially different disclosure from one:
1. **~01:20Z, to the analyst** — the script printed the contrast outright; 33 vs 51 rounds.
2. **~01:35Z, to the team lead** — the "fixed" gate printed both arms' rates adjacently;
   15/51 and 15/47. Disclosed by the team lead at the moment it happened.

Both are stated with the bounded-damage reasoning **and** with the fact that the first fix
was cosmetic, since that is the part a reader needs in order to judge whether the second
fix is real.

---

## AMENDMENT 6, 2026-09-01T01:40Z — THIRD R49 LEAK: a pooled tally read TWICE

### The defect

The Amendment 5 fix admitted "the outcome tally **pooled across arms**" as safe. Pooled at
a **single instant** it genuinely is. But **the arms alternate in 30-minute blocks and only
one arm is live at a time**, so

```
tally(end of a block) − tally(start of that block)  =  that ARM's deaths, exactly
```

**Blinding was defeated by REPETITION, not by a missing suppression** — and a status
command is precisely the thing that gets run repeatedly. This is the same failure a level
deeper: version 1 leaked because a *quantity* was printed; version 2 leaked because a
*time series* of a "safe" quantity is not safe when the design partitions time by arm.

### IT ACTUALLY HAPPENED — disclosed with the readings

I emitted the pooled tally **twice**, both inside the noproph block:

| reading | AMBIGUOUS | TOPOUT_P1 | TOPOUT_P2 |
|---|---|---|---|
| first run (~01:31Z) | 58 | 12 | 31 |
| second run (~01:33Z) | 59 | 12 | 31 |

Differenced, that discloses: **over ~2 minutes of the noproph block, noproph accrued
+1 AMBIGUOUS round and ZERO champion deaths.** One round's worth of single-arm
information. Small, but it is exactly the forbidden quantity and it is disclosed on the
same footing as the other two. The second reading was also quoted in a message to the team
lead.

### ADMISSION CRITERION (the general rule, now stated explicitly)

> **A quantity may be printed below the floor only if ITS TIME-DERIVATIVE is also
> uninformative about the endpoint** — not merely if it looks aggregated.

* **passes** — rounds per arm, hours per arm, reloads per arm, exclusions per arm,
  progress-to-floor, controller liveness / last-sample time. Their deltas are denominators
  and nuisance counts, carrying no death information.
* **fails** — any outcome count, pooled or per-arm. Its delta is a single-arm numerator.

### STRENGTHENED AUDIT TEST

Not *"can a reader compute the withheld quantity from this output?"* but:

> **"Can a reader compute it from this output TOGETHER WITH ANY OTHER OUTPUT THIS TOOL HAS
> EVER PRODUCED, INCLUDING EARLIER RUNS OF ITSELF?"**

**Blinding is a property of the whole output history, not of a single invocation.**

### Fixes applied

* `analyze_ab.py` — the pooled outcome tally is **withheld**; the blinded report now emits
  only the passing set above.
* `stratify.py` — **gated whole** below the floor rather than field-by-field. Suppressing
  its `arm=` column was never enough: run it twice across a block and the *new* deaths that
  appear all belong to whichever arm was live, and which arm that was is knowable from the
  clock.

### Disposition

Bounded as before — the stopping rule is data-independent (>=120 rounds/arm or the 6 h
clock), so no one can act on it; both arms remain far below the floor; nothing is
invalidated. **The write-up now discloses THREE leaks as three**, each with its cause, and
including that fixes 1 and 2 were themselves the sources of leaks 2 and 3. A reader needs
that chain to judge whether this fix is real.
