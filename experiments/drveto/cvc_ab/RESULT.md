# DRPROPH CvC L20 A/B — RESULT

**T_stop 2026-09-01T03:03:06Z** (floor arm binding). Truncated blind before unblinding.
Regime: **L20, CvC, start-of-round pile-up population (82-83 viruses left of 84), distinct
from the banked L20 farm's median 41.**

## Pre-registered PRIMARY: ADDRESSABLE champion deaths per completed round

| arm | rounds | ADDRESSABLE | rate | exclusions | reloads |
|---|---|---|---|---|---|
| noproph (control) | 128 | 22 | **0.1719** | 0 | 0 |
| proph (treated) | 120 | 15 | **0.1250** | 0 | 0 |

**Difference (proph − noproph) = −0.0469, 95% CI [−0.1350, +0.0413].**
Relative rate 0.73 (gated prediction 0.333).
**The CI contains zero AND contains the gated effect (−0.1146).**

n bought: 128 / 120. **120 floor MET. 186 conservative target NOT MET.**

⇒ Direction favours DRPROPH; the interval excludes neither no-effect nor the full gated
effect. **This is not a GO and it is not a refutation.**

## ⚠⚠ TWO VALIDITY PROBLEMS THAT COME BEFORE THE NUMBER

### 1. The arms have wildly different measurement failure rates

| arm | video-confirmed | poll/video DISAGREEMENTS | disagreement rate |
|---|---|---|---|
| noproph | 22 | 18 | **45%** |
| proph | 28 | 7 | **20%** |

The adjudicator fails **more than twice as often on the control arm**. A differential
measurement artifact between arms makes the confirmed sets **not comparable**, and it is
the numerator of the primary that is built from them. This alone is enough to withhold a
verdict.

### 2. noproph has ZERO UNADDRESSABLE deaths; proph has 13

DRPROPH **cannot make a board's gates blocked** — the gates are a property of the board.
Two candidate explanations, unresolved:
* **Real mechanism:** DRPROPH's own lateral escape pushes the capsule INTO the gate
  column, filling it — i.e. the fix converts addressable deaths into unaddressable ones.
  That would be a genuine and important finding, and it would mean the primary's
  stratification is endogenous to the treatment.
* **Artifact:** the parent-board timing or the stratifier behaves differently under the
  treatment.

**A stratifier whose strata are caused by the treatment cannot define the primary
population.** Until this is explained the stratified contrast is not trustworthy.

## The unstratified secondary points the OTHER WAY

All video-confirmed champion deaths per round: noproph 0.1719 vs proph **0.2333**,
d = +0.0615, 95% CI [−0.0385, +0.1615]. **Treated arm HIGHER**, CI contains zero.

Reported because a reader who sees only the favourable pre-registered endpoint would be
misled. The two are not contradictory — the primary conditions on a stratum whose
membership may itself be treatment-dependent (problem 2) — but that is an explanation, not
a defence.

## VERDICT

**NO GO, and no refutation. The floor was met, so this is not simply "underpowered" — but
the differential disagreement rate and the endogenous strata mean the comparison is
COMPROMISED, not merely imprecise.** Recommended status: **INDETERMINATE pending
explanation of the two artifacts**, not a null.

Exposure over the run: 37/50 = 74% ADDRESSABLE pooled (supersedes 56% (5/9); both were
provisional under n~10, and this one is at n=50).

## Protocol deviations and disclosures

* **Overrun:** the run continued ~7h19m past its stop; truncated blind at T_stop from
  round counts alone. 705 out-of-protocol rounds discarded, not pooled, not used as a
  robustness check.
* **Blinding:** three leaks. **The material one exposed the full per-arm contrast at ~40%
  of target N to both analysts and is disclosed at that strength**; a third was negligible
  (one round, zero deaths). Fixes 1 and 2 were themselves the sources of leaks 2 and 3. A
  fourth, blinding-adjacent event: the floor gate auto-printed a poll-based contrast before
  truncation was computed — T_stop has zero degrees of freedom so it cannot have been
  influenced.
* **Bounded damage, stated at full strength:** the stopping rule is data-independent and
  the analysis pre-registered, so no decision either analyst could take was biasable.
* The poll endpoint is **not** quoted anywhere: it over-flags champion deaths.
