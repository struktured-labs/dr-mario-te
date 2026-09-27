# labels-146 PILOT RESULTS (2026-08-21, PREREG_LABELS applied mechanically)

Chain: drm-labels-pilot-w4 -> -w8 (resumed per-seed after the settled core-split
scale-up), PILOT_CHAIN_OK. All artifacts in out/ (PILOT_REPORT.json is the
machine-readable version). n=80 states / 128 label rows / 21,384 forks.

## Gates (pre-harvest, all kills real)

G1 replay bit-exact vs bank end-to-end on topout/stall/clear seeds
(30000/86ply, 30034/400, 30002/283). G2 M-stale KILLED (vals mismatch, ply 44).
G3 population mutant KILLED per-double: double-capsule state ratio exactly
2.000, non-doubles 1.000 (prereg carries the pre-data amendment from the
mis-derived pooled bar). G4 determinism byte-exact.

## Validation (report-only sign test per §5)

| labeler | claims | rescued | broken | p(sign) | pred dsurv | realized r-b |
|---|---|---|---|---|---|---|
| **true** | 15 | **2** | **0** | 0.25 | 0.575 | 0.133 |
| M-shuffle | 18 | 1 | 0 | 0.50 | 0.681 | 0.056 |
| M-mimic | **0** | — | — | — | — | **FAIL_NO_CLAIMS** |

Direction correct (true > shuffle, no breaks), underpowered at n=15 as
expected — the campaign promotion gate is set at team-lead review from this
discordance. Voids: NONE (claims exist, shuffle does not outperform, cost
under bar).

## dsurv-vs-k profile (S-death, H=25) — WINDOW RULE inputs

| k | n | mean dsurv | max | claim yield | in window |
|---|---|---|---|---|---|
| 1 | 12 | 1.667 | 6 | 0.250 | YES |
| 3 | 12 | 1.000 | 5 | 0.083 | YES (contiguity) |
| 6 | 12 | 1.750 | 8 | 0.250 | YES |
| 10 | 12 | 1.500 | 5 | 0.333 | YES |
| 15 | 12 | 1.250 | 5 | 0.167 | YES |
| 20 | 12 | 1.167 | 5 | 0.167 | YES |

**WINDOW RULE -> end-25 .. end-1** (every k hot except k=3 at 0.083, which is
inside the contiguous range; +5 deep-end extension).

## HORIZON RULE -> campaign H = 25

24 dual-labeled states: H25 mean tau vs H40 = 0.873 (>=0.85), claim Jaccard
0.833 (>=0.75) — PASS. H15: tau 0.744, Jaccard 0.667 — fails both. Mechanical
verdict H=25.

## Cost (measured, ratios not wall-clock)

0.718 cpu-s/fork (2.5x CHEAPER than the 1.78 prior scaled from the endpoint
unit's H15 figure), 120.3 cpu-s/label row. At 20 workers: ~600 label rows/h,
~4,800 overnight.

## Findings beyond the registered numbers (hypotheses, not conclusions)

1. **Both rescues sit at k=10; every k<=6 claim failed to rescue.** The
   lock-in boundary is ~6-10 plies before death — quantitative confirmation of
   the kill-classification picture, now with per-ply counterfactual labels.
2. **Labels can be right AT HORIZON while game-rescue fails**: claim
   30000/85 (k=1, dsurv 6): forced arm survived 28 further plies (> H=25),
   then died — the label's direct claim (survive 25) was TRUE; the game-level
   endpoint asks more. Campaign validation should record BOTH endpoints:
   survived-past-ply+H (the label's own claim — primary calibration) and game
   failure (the decision-relevant secondary). Flagging for the promotion-gate
   amendment.
3. One claim (30014/242) died 1 ply after the forced move under the true
   future while 8/8 sampled futures survived — the sampled->true transfer
   noise the validation exists to price.
4. M-shuffle makes MORE claims than true (18 vs 15): randomizing the champion's
   label inflates apparent dsurv — expected, and why claim COUNT is not a
   quality metric; only outcome validation is.
