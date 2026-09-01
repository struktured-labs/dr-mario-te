# PRE-REGISTRATION: Mesen calibration of the video death-detector

**CLAIM BOUNDARY, stated first because a limitation in a limitations section does not
survive paraphrase: this calibrates the detector's DECISION LOGIC ONLY — not the capture
pipeline (no capture-card compression, noise, or colour) — and it CAN CONFIRM a detector
defect but CANNOT EXONERATE the detector.**

Registered 2026-09-01, before any Mesen run. Nothing built at registration time beyond the
two header-remapped ROMs.

## Why

The DRPROPH A/B could not be measured: the framebuffer poll and the OBS video are **both
pixel-based**, share a failure mode, and disagree in both directions at arm-dependent rates
(poll over-flags 45% control / 20% treated; poll MISSES 53% / 87%). Video was designated
ground truth **by fiat**, on an 8/8 validation performed on **non-pulsing footage**. Mesen
reads RAM, so it knows which seat topped out and on which frame **without inferring anything
from pixels** — it can supply the truth column the silicon corpus lacks.

## Design

1. Run each arm in Mesen (`proph1_L20_mmc1.nes` md5 `6f6af81e…`, `proph0_L20_mmc1.nes` md5
   `9d485a05…`; mapper 100→1, **PRG+CHR byte-identical**). DRPROPH is cart-side 6502 and
   executes natively.
2. Label every champion death **from RAM** — ground truth, no adjudication.
3. Render those frames, push them through the **same 5.5156x / 4.8889y transform** the
   capture path applies, and feed them to the **unmodified** video adjudicator.
4. Compute the confusion matrix **with a real denominator**, separately for DRPROPH=1 and 0.

## Pre-registered analysis

### A. Corpus matched to the SILICON death geometry

The Lua brain is *"emptiest column, vertical"*, not the shipped search, so Mesen's natural
death population is not ours. **We hold the silicon death boards, so the corpus is filtered/
weighted to match them** on: `fo3`, `fo4`, top-three-row stack height, which gates are
blocked, and viruses-left band.

**Distribution overlap on those five features is REPORTED**, so a reader can judge transfer.

⚠ **If Mesen's weaker brain cannot produce our death shapes at all, THAT IS THE ANSWER —
report it and stop.** It is not a setback to be worked around.

### B. Latency sweep — a CONDITION, not a refinement

DRPROPH's pulse fires only in the driver's **no-answer window**, and in the harness that
window is set by `latency`, a tunable (README: silicon is ~15-50 f). **The rate at which the
treatment engages would otherwise be a parameter I select.** So the sweep spans **beyond
15-50 f at both ends** — planned points **8, 15, 24, 35, 50, 70, 100 frames** — and detector
error is reported **as a function of engagement rate**, making the knob the independent
variable rather than a confound.

**READING OF A FLAT RESULT, FIXED IN ADVANCE:** if detector error is **flat across the sweep,
that is evidence engagement is NOT the cause** — weak but real. **It must NOT be written up
as "inconclusive."** This is registered now precisely so a flat result cannot be downgraded
later.

### C. R96 controls, REBUILT for this setup (not assumed to transfer)

* **negative control** — labels randomised, independent of arm: the analysis must NOT detect
  an arm effect.
* **positive control** — detector errors forced to track arm: the analysis MUST detect it.
Both are rebuilt against this pipeline's own data; the silicon controls do not carry over.

## What each outcome means (fixed before running)

* **Detector shows the same arm-dependent error against RAM truth** → the defect is in the
  **decision logic**, is characterisable, and the banked silicon footage can be **re-scored
  without new silicon time**. Strong and actionable.
* **Detector error flat across the sweep** → evidence engagement is not the cause (per B).
* **No arm-dependent error at all** → **weak. Does NOT clear the detector**, because both the
  death population and the engagement rate differ from silicon. Consistent with the defect
  living in the capture path, which would be a different and narrower hunt.

## Constraints

Banked data and Mesen only. **No silicon, nothing on rivalmage, nothing rebuilt.** Mesen is
**single-instance** — only one driver at a time; confirm nothing else is attached before
launching. The seat-log spec remains a decision document pending the owner's ruling.
