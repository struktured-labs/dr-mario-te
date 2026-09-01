# DRPROPH CvC L20 A/B — RESULT

**STATUS: INDETERMINATE (COMPROMISED). Not a GO. Not a null. Nothing to act on.**

**T_stop 2026-09-01T03:03:06Z**, floor arm binding, truncated blind before unblinding.
Regime: **L20, CvC, start-of-round pile-up population (82-83 viruses left of 84), distinct
from the banked L20 farm's median 41 left.**

---

## ⚠⚠ THE LEADING CANDIDATE EXPLANATION: DRPROPH MAY BE CAUSING DEATHS

Stripped of strata, **the treated arm had MORE champion deaths per round than the control:**

| arm | rounds | ALL video-confirmed champion deaths | rate |
|---|---|---|---|
| noproph (control) | 128 | 22 | **0.1719** |
| proph (treated) | 120 | 28 | **0.2333** |

d = **+0.0615**, 95% CI [−0.0385, +0.1615] (contains zero).

And the entire divergence between that and the favourable stratified primary below is the
**13 UNADDRESSABLE deaths that exist ONLY in the treated arm** (control has zero).

**One hypothesis fits every number here, and it is not the comfortable one: DRPROPH's
lateral push may be shoving capsules INTO the gate column** — converting deaths it could
have helped into deaths it cannot, and adding some that would not have happened at all.
That single mechanism explains, simultaneously:
* the 0-vs-13 UNADDRESSABLE asymmetry (the treatment creates blocked gates),
* the higher total champion-death rate in the treated arm,
* and the favourable-looking stratified primary (the deaths it "removes" from ADDRESSABLE
  reappear as UNADDRESSABLE).

**It is not established. It is also not less likely than the benign reading.** The
alternative is a stratifier/adjudicator defect (see the two artifacts below). Both are live.

---

## The pre-registered primary — and why it CANNOT carry the verdict

ADDRESSABLE champion deaths per completed round, video-confirmed:

| arm | rounds | ADDRESSABLE | rate | exclusions | reloads |
|---|---|---|---|---|---|
| noproph | 128 | 22 | 0.1719 | 0 | 0 |
| proph | 120 | 15 | 0.1250 | 0 | 0 |

d = −0.0469, 95% CI [−0.1350, +0.0413]. Relative rate 0.73 (gated prediction 0.333).
**CI contains zero AND contains the gated effect.** n bought 128/120 — **120 floor MET,
186 conservative target NOT met.**

### ⚠ THIS ESTIMAND IS INVALID BY CONSTRUCTION — a pre-registration defect

Conditioning on ADDRESSABLE is **conditioning on a POST-TREATMENT VARIABLE** if the
treatment can move stratum membership. **The 0-vs-13 split is direct evidence that it can.**
A stratum the treatment can alter is a **collider**, not a refinement, and conditioning on
it induces exactly the spurious favourable association seen above.

This is a **design defect in the pre-registration**, not a surprise in the data. The
stratification was approved on the assumption that eligibility is a property of the BOARD
and therefore pre-treatment. **That assumption was never verified and is false whenever the
mechanism's own action can alter the gates.**

⇒ **STANDING RULE: before a stratum may define a primary endpoint, DEMONSTRATE IT IS
UNAFFECTED BY TREATMENT — compare stratum proportions across arms. If they differ
materially, the stratified estimand is a collider.**
Here they differ maximally: 100% ADDRESSABLE in control, 54% in treated.

---

## Second artifact: the arms have different MEASUREMENT failure rates

| arm | video-confirmed | poll/video disagreements | rate |
|---|---|---|---|
| noproph | 22 | 18 | **45%** |
| proph | 28 | 7 | **20%** |

The adjudicator fails **more than twice as often on the control arm**, and the confirmed
sets are the numerators of every figure above. **Arm-dependent measurement invalidates the
comparison independently of the collider problem** — if the instrument is arm-dependent,
nothing downstream survives it. This is the first thing to investigate.

---

## Exposure

**74% (37/50)** ADDRESSABLE, pooled. Third movement of this figure from an UNCHANGED
scorer: **80% (4/5) → 56% (5/9) → 74% (37/50)**. Quote it with the count, always.

## Order of work (not started; the write-up comes first)

1. **Adjudicator asymmetry** (45% vs 20%) — arm-dependent measurement; if real, nothing
   downstream survives.
2. **Stratum endogeneity** (0 vs 13) — is DRPROPH filling the gate column, or is the
   stratifier treatment-dependent?

Both use banked footage. No new silicon time.

## Protocol deviations and disclosures

* **Overrun:** ran ~7h19m past its stop; truncated blind at T_stop from round counts alone.
  705 out-of-protocol rounds discarded — not pooled, not used as a robustness check.
* **Blinding: three leaks. The material one exposed the full per-arm contrast at ~40% of
  target N to both analysts and is disclosed at that strength**; a third was negligible
  (one round, zero deaths). **Fixes 1 and 2 were themselves the sources of leaks 2 and 3.**
  A fourth, blinding-adjacent: the floor gate auto-printed a poll-based contrast before
  truncation was computed — T_stop has zero degrees of freedom, so it cannot have been
  influenced. Design note: **a floor gate should evaluate against the in-protocol dataset,
  not the live file.**
* **Bounded damage, at full strength:** the stopping rule is data-independent and the
  analysis pre-registered, so no decision either analyst could take was biasable.
* The **poll endpoint is quoted nowhere** — it over-flags champion deaths.
