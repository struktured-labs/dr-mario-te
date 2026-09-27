# PRE-REGISTRATION — run 14: holes dose ladder, TAP-OUT as PRIMARY. AT LAUNCH 2026-09-11.

## ★ THE PRIMARY ENDPOINT CHANGES, AND WHY THAT IS LEGITIMATE
Owner ruling, this session, verbatim: *"its the tap out stuff that matters its game play as a whole
is great otherwise"* — consistent with the standing #1 priority banked long before today
([[dr-mario-childproof-champion-and-tapout-lead]]).
⇒ **PRIMARY = paired TOP-OUT rate vs champion, McNemar exact.** Clear rate drops to secondary.
⚠ This is NOT a post-hoc switch to the endpoint that looks best: top-out has been a PRE-SPECIFIED
secondary in every prereg in this lane, and the justification is an owner priority that predates
this session's data. Stating it explicitly so nobody has to take that on trust later.

## Arms
champion / **`winholes80`** (PRIMARY, R_HOLES 20->80) / `winholes160` (dose probe, 20->160).
All three holes values are **popcount 2** (20=10100b, 80=1010000b, 160=10100000b), so every arm is
exactly cost-neutral in the RTL shift-add: no new term, no carry level, no third pipeline stage.

## Why `winholes80` is the candidate
Ranked on the owner's metric across every validation run so far:
| candidate | run | n | champ TO% | arm TO% | relative | p | silicon cost |
|---|---|---|---|---|---|---|---|
| **winholes80** | 13 | 1518 | 8.70 | **5.14** | **-40.9%** | 0.00011 | FREE |
| winw_holes_40 | 12 | 2000 | 8.95 | 5.55 | -38.0% | 0.000027 | FREE |
| wincombo | 10 | 2000 | 9.00 | 5.65 | -37.2% | 0.000056 | **pipeline stage** |
| winend8_48 | 10 | 2000 | 9.00 | 7.25 | -19.4% | 0.016 | **pipeline stage** |
`winholes80` leads AND is free. But it has only ONE run, and it was a pre-specified DOSE PROBE in
`PREREG_HOLES.md` explicitly barred from becoming champion on that run. This is its own test.

## ⚠⚠ SEED EXHAUSTION — this is the LAST fully-fresh run this lane can do
The distinct-pill-stream space is 32,767 and **only 515 streams remain free (1.6%)**. This run uses
all 515, across 9 registered fragments (block structure is irrelevant to a within-seed paired test).
**After this, fresh-seed validation is over**: future work must either reuse streams and say so, or
change the REGIME (level / pressure model), which produces genuinely different games from the same
seed. That is a program-level constraint, not a detail.

## Power, honestly
n=515. Top-out discordance ran ~12.5% at n=1518, so SE ~1.56pp against an effect of ~-3.6pp
=> adequately powered for the PRIMARY. **Underpowered for clear rate** (~4.3pp MDE vs a ~+3.8pp
effect), which is a further reason the primary is top-out and not clear rate.

## Decision rule, fixed now
- PRIMARY p < 0.05 and top-out DOWN => `winholes80` is the tap-out champion candidate, free in
  silicon. It then owes only a passing fit.
- p >= 0.05 => not confirmed; `winw_holes_40` (confirmed TWICE, runs 12 and 13) remains the
  standing candidate and run 13's +3.82pp/5.14% is withdrawn as a single-run dose probe.
- `winholes160` cannot become champion off this run; it only says whether the ladder is still rising.
