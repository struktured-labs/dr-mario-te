# PRE-REGISTRATION — spawn-lane eval candidate vs CHAMPION
Registered 2026-09-10, BEFORE the validation run. Screen data is closed; no seed is reused.

## Hypothesis
Every top-out on this ROM is a SPAWN PLUG ([[dr-mario-spawnplug-verdict]]): the cart cannot place
the new capsule at the spawn cells, so the ONLY software lever is to keep columns 3-4 clear.
The shipped leaf's spawn term is `if r < 4 and (c == 3 or c == 4): spawn += 1` — it is BLIND until
junk has already reached row 3, by which point the plug is usually unavoidable. The planner has a
`spawn_col_height` feature the leaf does not. Candidate adds it to the leaf:

    leaf -= W * SUM over non-virus occupied cells in columns 3,4 of (ROWS - r)

i.e. a height-weighted count of the spawn lane, biting from the FIRST cell placed there.
Viruses are excluded: they are the target, not clutter, and cannot be steered around.

## Arms
- champion = `variant("winner")` (r47 + coef-opt2 5-constant reweight) — the STANDING champion.
- candidate = `winsc2` (winner + W=2). **PRIMARY.**
- dose check = `winsc5` (winner + W=5). Pre-specified consistency arm, NOT a separate champion claim.

## Why this candidate, and why the screen is not the estimate
A 5-arm dose screen (W in {2,5,10,20}, 100 paired seeds, L20 drip, cap 600) gave a MONOTONE
dose-response: +9.0 / +7.0 / +0.0 / -20.0 pp vs the champion's 81.0%. The harm arm is significant
(W=20: p=0.0012) in the direction the mechanism predicts — over-steering the spawn lane raises
topout 16.0% -> 37.0%. The leader halves topout, 16.0% -> 8.0%.
⚠ +9.0pp is a MAX-OF-4 and is NOT the estimate. The last candidate screened at +5.0pp and validated
at -2.5pp: measured winner's curse on this exact rig = **-7.5pp**. This run exists to replace it.

## Design
CRN-paired: identical seed => identical virus layout, pill stream AND garbage, so the pair differs
ONLY by the eval. Regime: level 20, drip pressure, wt=0 ws=20, **max_pills=600**.
The cap is 600, not the historical 300, because 300 truncates games in progress: on 200 champion
seeds, cap 300 scored 82.0% clear / 11.0% stall and cap 600 scored 87.5% / 3.5% — **11 of 22
"stalls" were wins in progress**, and the truncation biases AGAINST any slower-but-safer policy.

## Seeds
FRESH block, DISJOINT from every seed consumed in experiments/cvx (900 seeds, 36734..38532):
**EVEN 38534..40132 step 2 (800 streams)**. Registry `--check 38534 800 2` = PASS, 800 distinct
streams, keys 19267..20066, overlap with prior use = 0. Screen seeds are NOT reused, NOT pooled.

## PRIMARY endpoint
Paired clear-rate difference, winsc2 vs champion, **McNemar exact two-sided** on discordant pairs.
## SECONDARY
topout% split (the mechanism's own endpoint), stall%, median pills-to-terminal, and the winsc5
dose-consistency direction.

## Decision rule, fixed now
- p < 0.05 AND direction positive => genuine champion candidate. Report effect + CI. It STILL owes
  an RTL/firmware feasibility check (int16 wrap + ALM cost) before any ship claim.
- p >= 0.05 => NOT a champion. Report the null with its CI. Do not re-slice, do not re-screen on
  this data, do not quote +9.0pp as if it were the result.
- direction negative => report as harm.
- winsc5 cannot rescue a winsc2 null: if PRIMARY fails, the candidate fails.

## Pre-committed hazards
- **int16 wrap**: the leaf combine wraps (`s & 0xFFFF`). Worst case here is 2 * 32 cells * 16 rows
  = 1024, well inside range, but the check is owed on the REAL observed leaf range, not this bound.
- **Score against the baseline you replace** ([[dr-mario-score-against-the-baseline-you-replace]]):
  the comparator is the champion, never a target.
- This is the L20 drip SOFTWARE lane on Mesen/CPU. No live silicon exists right now (rivalmage fan
  dead, bluemage awaiting a 2.5Gb switch), so NOTHING here is a silicon or couch-test claim.
