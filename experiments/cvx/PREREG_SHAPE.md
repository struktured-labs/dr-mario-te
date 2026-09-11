# PRE-REGISTRATION — re-optimising the NEVER-TUNED shape constants
Registered 2026-09-10 AT LAUNCH. The step rule below is fixed BEFORE any data exists.

## The premise, verified not assumed
1. **Five shape constants have NEVER been optimized.** Dumping `variant("r47")` against
   `variant("winner")` shows coef-opt2 moved exactly five slots — `R_SETUP 60->32`,
   `R_MATCHED 60->48`, `R_BURIED 30->48`, `R_RDYEXT 12->8`, `R_VRDY 24->8`. Every shape constant
   is still at its r47 value: **`R_MAXH=12`, `R_HOLES=20`, `R_TOPRISK=90`, `R_SPAWN=150`,
   `R_POLL=6`.** These are the top-out-facing terms, and **top-out is ~76% of the champion's
   remaining failure**.
2. **What tuning did happen used a censored objective.** All ten rigs in
   `dr-mario-qa-wt/experiments/eval47/` are hardcoded `max_pills=300` — `pressure_rig.py`,
   `ab47.py`, `mirror47.py`, `firmware_tier3_ab.py`, `reach_root*.py`, `reach_divergence*.py`,
   `blunder_ai_rows.py`, `firmware_tier3_spotcheck.py`. **None uses 400 or 600.** Cap 300 censors
   **5.5pp** of the clear label and does so ASYMMETRICALLY, against slower-but-safer policies
   ([[dr-mario-flip-hazard-and-cap-mismatch]]).
3. **This is the only candidate class silicon can afford.** The shipped copro closes timing at
   **0.165 ns against a +0.10 ns bar**, with **placement-seed noise spanning 0.076-0.380 ns**; a NEW
   leaf term costs a third pipeline stage ([[dr-mario-leaf-has-no-timing-budget]]). A constant change
   costs nothing. Perturbations are **x2 / /2 on purpose: doubling or halving preserves POPCOUNT**
   (12/6/24 -> 2 bits; 90/45/180 -> 4; 150/75/300 -> 4; 20/10/40 -> 2; 6/3/12 -> 2), so every arm
   here has an RTL multiplier cost **identical to the shipped one**. Verified, not assumed.

## Design — a GRADIENT estimate, not a max-of-N screen
Ten arms, one per (axis, direction), each changing exactly ONE slot (verified):
`winw_maxh_{6,24}` · `winw_holes_{10,40}` · `winw_toprisk_{45,180}` · `winw_spawn_{75,300}` ·
`winw_poll_{3,12}`, plus the champion. n = 400 CRN-paired seeds, L20 drip, **cap 600**.
Seeds: fresh block **21180..21978 step 2** (`--check` PASS), registered AT LAUNCH.

**This deliberately does NOT pick the best arm.** Picking a max of ten at n=400 would carry ~+3.9pp
of inflation ([[dr-mario-screen-n100-is-useless]]). Instead the ten arms estimate five local
gradients and are combined into ONE point, so noise-driven axes contribute ~0 in expectation
rather than being selected FOR their noise.

## STEP RULE — fixed now, applied mechanically
For each axis independently:
- compute the paired clear-rate difference vs champion for its two arms, and the per-arm SE from
  that arm's OWN observed discordance, `SE = 100*sqrt((W+L))/n`;
- if the better direction's `d > 1.0 * SE`, move that axis to that tested value; otherwise **leave
  it at the champion value**;
- take the tested point (x2 or /2) exactly — no interpolation, because no intermediate was measured;
- if both directions pass, take the larger `d`.

Threshold rationale, stated before the data: a 1.0-SE bar is deliberately lenient because this is an
INCLUSION decision, not a selection. Wrongly including a truly-zero axis costs ~0 in expectation;
wrongly excluding a real one costs the whole gain. With a 1.0-SE bar a truly-zero axis is included
~16% of the time and contributes ~0. The asymmetry is the point.

**If NO axis passes, there is no combined point.** Report the shape constants as already near-optimal
and stop — that is a real answer.

## Then, and only then
The combined point `winshape` gets its OWN pre-registered validation, n = 2000, fresh block,
McNemar exact, powered for +2.2pp. **The screen's numbers will not be quoted as the result.**

## Pre-committed hazards
- int16 wrap: these are RE-WEIGHTS of existing terms, and doubling `R_TOPRISK`/`R_SPAWN` raises the
  NEGATIVE side, which moves the binding POSITIVE maximum DOWN — safer, not riskier
  ([[dr-mario-int16-wrap-headroom]]). Re-measure on real leaves before any ship claim anyway.
- Score against the CHAMPION, never a target.
- L20 drip solitaire lane on CPU. No live silicon exists; nothing here is a silicon or couch claim.
