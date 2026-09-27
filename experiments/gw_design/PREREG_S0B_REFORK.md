# PREREG — S0-B: capsule-fair refork of the S0-A deepening flips

**Registered 2026-08-18, BEFORE any refork row exists.** Task #125. Approved by the team
lead as the replacement for the endpoint A/B, which §7.2 showed cannot decide this arm.

## 1. Why this instrument and not the endpoint

S0-A passed its gate (33.8% flip rate) but the **dose binds**: 0.240% of plies at the
ceiling, 0.144% shippable, against H12's measured 1.98%. At H12-equal per-flip quality that
projects 0.62pp against an MDE of ~0.84pp — under-powered **before** any quality discount.
An endpoint A/B would buy a guaranteed-ambiguous null.

The refork prices **per-flip quality directly**, which is the actual question; the endpoint
was only ever a proxy for it. It needs no endpoint power. Same instrument the h13-gate lane
used to close gate-v2 on 2026-08-18.

## 2. Population and instrument

**Population:** the **381 deepening flips** banked in `out/s0a_50100.jsonl` (`kind=deepen`,
`flip=1`), seeds 50100-51099. Fixed and countable before this document was written.

**Instrument:** capsule-fair refork. At each flip, fork **both** the champion's pick (`keep`)
and the deepened pick (`flip`) under **K = 17 unseen capsule streams**, matching the h13-gate
configuration exactly. Within a stream both lines face the identical future (common random
numbers); averaging over K removes single-draw luck. **Unit: mean viruses progress per flip,
`flip − keep`.**

**RAND control: MANDATORY.** A uniformly-drawn alternative legal candidate at the same dose,
forked identically. h13-gate measured **−0.559** for it against a **+0.012** null — that
separation is what proves the instrument discriminates rather than returning zero for
everything.

## 3. Decision rule — FIXED BEFORE DATA, and the bar is DERIVED not chosen

Let `d` = mean(flip − keep) in viruses/flip, with a 95% CI over flips.

**Where the bar comes from.** H12: 1.98% dose over ~159 plies/game = 3.15 flips/game →
+8.5pp clear ⇒ **2.70pp clear per flip**. This arm: 0.240% × 159 = **0.38 flips/game**. To
clear an MDE of 0.84pp it needs **2.21pp per flip = 82% of H12's per-flip value.** So the
question is not "is `d` > 0" but "is `d` within striking distance of H12's per-flip value".

⚠ **The ideal calibration is unavailable and I am not pretending otherwise.** H12's own
accepted flips have never been run through this refork, so its per-flip value in *these
units* is unknown — `flip_log` stores no env state, so it cannot be reforked without a
re-run. The bar below is therefore expressed in the instrument's demonstrated dynamic range
(RAND −0.559 → null +0.012, a span of ~0.57 viruses/flip), and **the H12 calibration is
registered as the thing that would make this precise** (§6).

| verdict | condition |
|---|---|
| **VOID** | RAND control not clearly negative (CI upper < −0.2 required), or < 300 flips scored |
| **NEGATIVE — close the lane** | CI upper < 0 |
| **NULL — close the lane** | CI includes 0 **and** CI upper < **+0.15** (≈ 26% of the instrument's range; cannot reach the derived bar even optimistically) |
| **INDETERMINATE** | CI includes 0 **and** CI upper ≥ +0.15 — report the n that would resolve it; do **not** proceed |
| **POSITIVE — license endpoint pricing** | CI lower > 0 **and** point estimate ≥ **+0.15** |

⚠ A POSITIVE does **not** license an endpoint at the current dose. §7.2's arithmetic still
binds, so a positive returns with the **dose-increase question attached** (wider h band, or
top-3 candidates) and the endpoint must be re-sized against the measured `d`.

⚠ **The null shape to beat is h13-gate's, not zero:** +0.012 with wins almost exactly equal
to losses. Report the **win/loss split**, not only the mean — symmetric trades at a positive
mean is the churn signature.

## 4. VOID conditions

1. RAND control not clearly negative ⇒ the instrument is not discriminating; no verdict.
2. Fewer than 300 flips scored (of 381 available) ⇒ attrition unexplained.
3. Any fork sharing a capsule stream with the play seed ⇒ seed-peeking; the alias trap
   (`2k ≡ 2k+1`) must be checked on the **canonical even member**.
4. Determinism: re-running one flip must reproduce its `d` exactly.

## 5. Killed mutants

| id | mutation | must be caught by |
|---|---|---|
| **M-F1** | fork `keep` twice (flip arm ignored) | `d` must be **exactly 0**; any non-zero means the arms are not paired |
| **M-F2** | unpaired streams (different draws per arm) | variance must inflate materially; proves CRN pairing is load-bearing |
| **M-F3** | RAND substituted for the flip arm | must reproduce ≈ h13-gate's −0.559 order; if it does not, the instrument is not comparable to theirs and the bar is not transferable |
| **M-F4** | verdict router: ignore the +0.15 bar, use `CI lower > 0` alone | must return POSITIVE on a synthetic small-but-significant fixture where the true rule returns NULL |

M-F3 doubles as the cross-lane comparability check: it is the same control h13-gate ran, so
agreement licenses using their null shape as my reference.

## 6. Registered follow-on, whatever the verdict

**The missing calibration is the highest-value cheap experiment this lane can hand forward:**
run H12's own accepted flips through this identical refork to express its per-flip value in
these units. That converts every future "is this arm worth an endpoint" question from an
argument into a comparison, and it is the calibration point the distill lane identified as
absent ("no calibration point exists for AUC → dies-ahead"). Requires re-running H12 with
env capture; not in scope here, registered as the successor.
