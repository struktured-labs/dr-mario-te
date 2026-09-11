# PRE-REGISTRATION — `winshape` vs CHAMPION.  Registered AT LAUNCH 2026-09-11, before any game.

## The candidate, and how it was built
`winshape` = champion + **`R_HOLES 20 -> 40`** + **`R_POLL 6 -> 12`**.
Produced by the step rule fixed in `PREREG_SHAPE.md` BEFORE run 11's data existed, applied
mechanically to run 11 (n=400, fresh block 21180..21978):

| axis | /2 | champion | x2 | SE | verdict |
|---|---|---|---|---|---|
| `R_HOLES` | -4.00 | 0 | **+4.25** | 2.08 | **MOVE -> 40** (d/SE 2.05) |
| `R_POLL` | +0.75 | 0 | **+4.00** | 2.21 | **MOVE -> 12** (d/SE 1.81) |
| `R_MAXH` | -0.75 | 0 | +1.50 | 2.00 | hold |
| `R_TOPRISK` | -3.25 | 0 | -2.25 | 2.08 | hold |
| `R_SPAWN` | +0.00 | 0 | -0.75 | 1.94 | hold |

Both survivors are MONOTONE across the tested span and both cut top-out hard
(11.00% -> 6.00% and -> 7.50%). That is the censored-cap prediction coming true: the never-tuned
SAFETY constants were set too low, which is exactly what tuning under a 300-pill cap rewards.

## ★ WHY THIS CANDIDATE MATTERS MORE THAN `wincombo`
**It is FREE in silicon.** Both moves are exact DOUBLINGS, so the shift-add multiplier popcount is
unchanged (`20=10100b` / `40=101000b`, `6=110b` / `12=1100b` -- verified, not assumed) and the adder
tree is untouched: **no new term, no extra carry level, no third pipeline stage.**
`wincombo` (+2.20pp, validated) adds TWO terms to a combine with ~0.065 ns of headroom and therefore
owes a pipeline stage = a leaf cycle = tempo ([[dr-mario-leaf-has-no-timing-budget]]).
**If `winshape` lands at a comparable size, it strictly dominates `wincombo`.**

## Design
CRN-paired, L20 drip, wt=0 ws=20, **max_pills=600**. n = **2000** fresh streams across three
registered blocks: `21980..24462` (1242) + `50100..51266` (584) + `60000..60346` (174), all
`--check` PASS, all disjoint from the 5,300 streams consumed by runs 01-11. Block structure is
irrelevant to a within-seed paired test.
Arms: champion / **`winshape`** (PRIMARY) / `winw_holes_40` (pre-specified decomposition — says how
much of any effect is the holes half alone; NOT a champion claim on its own).

## PRIMARY / SECONDARY
PRIMARY: paired clear-rate difference `winshape` vs champion, **McNemar exact two-sided**.
Powered for +2.2pp. SECONDARY: top-out% split (the mechanism's endpoint), stall%, and the
`winw_holes_40` decomposition.

## Decision rule, fixed now
- `p < 0.05` and positive => genuine champion candidate, and a **zero-silicon-cost** one. Report
  effect + CI, re-measure the int16 range on real leaves, then it is a ship conversation.
- `p >= 0.05` => not a champion. Report the null with its CI; the shape constants stay as shipped.
  No re-slicing, and run 11's +4.25 / +4.00 will NOT be quoted as the result.
- negative => report as harm.

## Pre-committed hazards
- ⚠ **Selection-induced inflation is NOT zero here.** The two axes were included BECAUSE their
  estimates exceeded 1 SE, so `E[true | included] < observed`. Run 11's numbers are therefore
  upper-biased and are not the estimate — this run is.
- int16: both changes RAISE negative terms, moving the binding POSITIVE maximum DOWN => safer
  ([[dr-mario-int16-wrap-headroom]]). Re-measure on real leaves anyway before any ship claim.
- Score against the CHAMPION, never a target.
- L20 drip SOLITAIRE lane on CPU. bluemage is back up, but nothing here is a silicon or couch claim.
