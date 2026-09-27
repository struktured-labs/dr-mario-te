# Instrument audit — why the A/B could not be measured

## 1. The adjudicator IS arm-dependent, and geometry does not explain it

Mantel-Haenszel, disagreement rate, control minus treated:
* stratified by round DURATION (<30 / 30-45 / >=45 s): **+0.275, 95% CI [+0.070, +0.479]**
* stratified by P2 VIRUSES LEFT (<=80 / >80): **+0.246, CI [+0.043, +0.449]**

Both exclude zero. Duration is **not** shifted by treatment (median 26.6 s control vs
26.5 s treated), so it cannot be the mechanism. **R96 controls both pass**: randomised
disagreement -> CI contains zero (does not see an effect that is not there); disagreement
forced to track arm -> +1.000, excludes zero (can see one that is).

## 2. Both instruments are wrong in BOTH directions, at arm-dependent rates

| | poll says death / video says not | poll says NOT / video says death |
|---|---|---|
| noproph | 18/40 = **45%** | 8/15 = **53%** |
| proph | 7/35 = **20%** | 13/15 = **87%** |

The poll MISSES far more than it over-flags, and the miss rate differs hugely by arm.

## 3. ⚠ THE PULSE HYPOTHESIS IS NOT SUPPORTED — the comfortable story fails

The hypothesis: DRPROPH pulses the capsule 1 frame on / 1 frame off, so on the treated arm
a ~30 Hz oscillation confuses a HOLD (persistence) detector, and the whole asymmetry is my
own instrument being fooled rather than anything about deaths. If true, the banked footage
could be re-scored and the A/B recovered with no new silicon.

**Measured directly, at 60 fps, as period-2 alternation of P2's top-rows centroid through
the settle window (n=23, 12 control / 11 treated):**

| arm | median alt_rate | mean |
|---|---|---|
| noproph (control) | **0.0100** | 0.0192 |
| proph (treated) | **0.0030** | 0.0035 |

**Alternation is LOWER on the treated arm — the opposite of what the pulse hypothesis
predicts.** The motion-matched stratification is too small to be decisive (cells of 3-8),
but the marginal comparison is unambiguous in direction.

**A mechanistic account of why the pulse may be invisible, consistent with earlier
measurement:** the fatal capsule was measured to have **ZERO travel frames** — it spawns
already at rest and locks. A capsule that is already at rest against a blocked side cannot
be displaced by a press, so DRPROPH's pulse may produce **no visual signature at all**, and
therefore cannot be fooling a pixel hold-detector via motion.

⇒ **The instrument asymmetry remains UNEXPLAINED.** It is not geometry and, on this
evidence, not the pulse.

## 4. DRPROBE IS NOT THE ARBITER — checked before proposing anything

`DRPROBE=1` logs **`($0046, $0727, $04)` on change** — game mode, 1P/2P, and the VS-CPU
flag — into a 64x3B ring at `$6200`. That captures **mode transitions**, i.e. *that* a round
ended. **It does not record WHICH SEAT topped out**, which is the entire arbitration
question.

Two further blockers:
* it is read **via SAVE-STATE** ("$6200 is captured"), not live;
* the freeze dossier from this very run records **`savestate trigger did not produce a new
  file`** — savestates may not be functional on this rig at all.

⇒ **DRPROBE as shipped cannot arbitrate.** A state-level arbiter would need a build change
(the cart already reads both boards and both virus counters every hook, so the information
is present — it simply is not logged). **Not proposed; reported for ruling.**

## Standing status

**No trustworthy estimate in either direction, and now with the leading candidate cause
REFUTED rather than confirmed.** Two pixel instruments, no arbiter, no ground truth
([[dr-mario-cvc-video-instrument]]). The video's 8/8 validation was performed on
non-pulsing footage and does not extend to DRPROPH=1 arms.
