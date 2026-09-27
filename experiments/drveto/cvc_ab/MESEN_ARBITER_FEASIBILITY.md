# Mesen as a ground-truth arbiter — FEASIBILITY (no build, no silicon)

**Verdict: BUILDABLE, but it answers a NARROWER question than the one we need, and its
value is ASYMMETRIC — a positive result is informative, a negative one is not conclusive.**

## Step 1 — does the cart run in Mesen? ✅ YES, verified

`remap_mapper.py` rewrites iNES mapper 100 -> 1 (**PRG+CHR byte-identical**, header only).
Both A/B arms remapped cleanly:
* `proph1_L20_mmc1.nes` md5 `6f6af81e9160e68796a58a6b78567879`
* `proph0_L20_mmc1.nes` md5 `9d485a057a44826d54f64048b3a9225f`

Mesen binary present (`~/mesen2-vsrules/Mesen`), harness present
(`/mnt/data/drmario/pocket-copro/mesen_copro_qa/`), and **nothing is currently driving
Mesen**, so the single-instance trap is clear.

★ **DRPROPH is CART-SIDE 6502 code, so it executes natively in Mesen** — it does not depend
on the copro. That is the one thing that has to be true for this idea to work, and it is.

## Step 2 — ⚠ THE COPRO IS EMULATED, SO THE DEATH POPULATION IS NOT THE SILICON ONE

The harness serves the `$5200` mailbox from **Lua**, not the shipped FPGA firmware. The
default brain is *"emptiest column, vertical"* — a trivial heuristic, not the champion
search. A `planner_bridge.py` can route to a py65 d3 planner, but that is still not the
shipped firmware.

⇒ **P2's move quality, and therefore how and how often it dies, differs from silicon.** A
detector calibrated on that population does not automatically transfer to the silicon
corpus.

## Step 3 — ⚠⚠ THE SHARPEST PROBLEM: THE KEY PARAMETER IS A KNOB I WOULD BE CHOOSING

DRPROPH's pulse fires **only in the driver's no-answer window**. In the harness that window
is set by `latency` — an explicit tunable, README: *"Silicon is ~15-50 f; set it to
reproduce the..."*.

**So the rate at which DRPROPH engages — the very thing suspected of confusing the
detector — would be set by a parameter I select.** Calibrating a detector against a
treatment whose intensity is a knob is a weak test at a single value.

⇒ **If this is built, it must run a LATENCY SWEEP, not one setting**, and report detector
error as a function of engagement rate. That converts the knob from a confound into the
independent variable, which is the only honest way to use it.

## Step 4 — rendering: which claim is being made

Mesen renders clean **256x240**. The silicon endpoint came through a capture card at
**1920x1080** with a non-integer rescale (5.5156x / 4.8889y) — the transform that already
broke exact bitmap matching (R94).

Two options, and they claim different things:
* **feed Mesen frames through the same rescale** -> calibrates the **DECISION LOGIC** under
  the same geometry. Does **NOT** reproduce capture-card compression, noise, or colour.
* **re-calibrate the decoder for 256x240** -> then it is **not the same adjudicator**, and
  the result says nothing about the one that produced the corpus.

**The claim I would make is the first, stated explicitly: decision logic only, not the
capture pipeline.**

## What it would and would not establish

* **If the detector shows the same arm-dependent error against RAM truth** -> the defect is
  in the **decision logic**, confirmed and characterisable, and the banked silicon footage
  can be re-scored. **Strong, actionable.**
* **If it does NOT** -> weak. It could mean the defect is in the capture path, OR that the
  Mesen death population / DRPROPH engagement rate simply differs. **Does not clear the
  detector.**

## Recommendation

Worth building **only with the latency sweep and the decision-logic-only claim stated up
front**. The alternative — a cart-side "which seat topped out" log — remains the durable
fix: the driver already reads both boards and both virus counters every hook, so the
information exists and is simply not recorded. That is a build change and needs the owner's
ruling.

Both R96 controls to be rebuilt for this setup, not assumed to transfer.
