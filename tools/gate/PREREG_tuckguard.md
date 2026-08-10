# Pre-registration — DRTUCKGUARD gate (task #102)

**Written and committed BEFORE any gate number exists.** The point is that "too tight" and "too
loose" are defined here rather than after we can see which way the result went.

Carts, one flag apart, both on the v6e-corrected emitter:
`tuck-noguard` `d33dfa2b98e19b840f8b67ffca9d6ca0` · `tuck-guard` `4d9ab049f4d6df41afa506d01f8d43da`

⚠ Run on **probe5/6/7 only**. The stock probe3/fieldplay brains never serve the tuck mailbox at
`$5087/$5088`; a DRTUCK cart reads open bus there, which decodes as "always take the final
column", so the executor is silently inert and any tuck gate on the old rig is **vacuous**.

## The property being protected

**A veto is `TUCK_C2 <- $FF`, which the executor already reads as "no tuck" — it steers straight
to the final column, i.e. exactly the pre-tuck behaviour.** So the guard's worst case is *"we did
not tuck"*, never *"we tucked wrong"*.

That is the whole reason this is worth shipping even though tucks are not: a safety mechanism
whose failure mode is the status quo ante is a fundamentally different object from one that can
misfire. It makes an **arbitrary** descriptor stream safe — v1, v3, or a future firmware whose
selection logic we do not control — rather than only the streams we generate.

## Decision rule — fixed in advance

| # | Condition | Verdict |
|---|---|---|
| 1 | **Any** of the 23 known-completable descriptors is vetoed | **HARD FAIL — too tight.** Those are ground truth; a veto there is a false veto, and the `+2` margin or the final-column choice must loosen. |
| 2 | **Any** v1 descriptor that stranded in the measured 4/4 still strands with the guard on | **HARD FAIL — too loose.** The guard does not do its job. |
| 3 | Veto rate on the synthetic stream | **SOFT SIGNAL — report, do not auto-fail.** If it materially exceeds the observed strand rate, the guard is buying safety with value; that trade goes in the report rather than being buried. |

Report **veto count alongside completion count** in every arm, so over-tightness is visible
rather than inferred from a silence.

## Value re-price — required, not optional

A veto is a **silent** behaviour change: the cart simply does not tuck, and nothing in the
pass/fail gate above would notice value quietly draining away. So the paired A/B is re-run
**with the guard on**:

- baseline measured tuck value: **−4.16 pills, 95% CI [−7.61, −0.67]**
- same rig, **stride-2 seeds** (2k and 2k+1 share a capsule stream, so `range(N)` would be N/2
  correlated pairs), paired.

Interpretation fixed in advance: if the guard preserves most of −4.16 it is **free safety**; if it
eats the interval it is **priced, not assumed free**, and that number goes in the report either
way. "The guard is safe" and "the guard is worth having" are different claims and this is the one
that settles the second.

## Known judgement calls being tested

Both were fitted to a 23-completion sample and are exactly what rule 1 and rule 3 exist to catch:
1. the **`+2` row margin**;
2. measuring free fall in the **final** column (rather than the traversal span or the approach
   column).

If rule 1 fires, the first thing to try is the span rather than shrinking the margin — a strand is
caused by the *highest stack along the path*, and the final column is a proxy for that, not the
thing itself.
