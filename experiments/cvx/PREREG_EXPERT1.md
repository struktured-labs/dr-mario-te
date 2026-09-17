# PRE-REG run 18 (2026-09-15, AT LAUNCH): expert-tape candidates vs winholes80, L11 OWNER-BURST, n=600
Source of the hypotheses: the Nutmeg tourney tape, SAME-LEVEL comparison (prelims are L11-class:
start-VIR mass at 44-48). Experts vs our winholes80, phase-binned (see expert insights memo):
(1) they CARVE THE SPAWN LANE only in the danger band (lane median 11->6 across 9-19 vir, edge-lane
crossing positive); (2) they leave cols 0/7 LOADED where ours are empty; (3) they run 2-6x our holes
mid-game and win on TEMPO -- holes80 may over-pay for cleanliness early.
All candidates are WEIGHT-MUXES on the existing vcount compare (silicon-cheap; no new adder term;
controls verified: gate-exact vs baseline, 0 diffs outside the band).
Arms (baseline = winholes80, the standing candidate it would replace):
  winh80_lane19w2 / winh80_lane19w4  -- phase-gated lane carve
  winh80_edge19w2                    -- phase-gated edge preference
  winh80_early40                     -- refund half the holes price while vcount>19 (tempo-for-mess)
n=600 CRN pairs (declared reuse: streams 36734..37932, consumed at other regimes), cap 600.
PRIMARY = paired tap-out vs winholes80, McNemar; SECONDARY = clear rate, median pills (tempo).
Screen-at-n>=400 rule respected (SE(tapout) ~ 1.3pp at n=600, discordance ~0.10).
Decision: any arm with tap-out DOWN p<0.05 -> pre-registered confirmation at n>=1500 before any claim;
clear-rate up alone does NOT promote (tap-out is the owner metric). Max-of-4 inflation on the SCREEN
applies (~+2SE); the screen number is never the estimate.

## ADDENDUM 18b (registered 2026-09-15 BEFORE run 18 results were viewed): TRAVEL-TIME / late-height arms
Owner observation, verbatim shape: "garbage takes FOREVER to fall in the endgame because of how long
it takes to reach the bottom... good players account for that." Mechanism: every capsule and every
received garbage half pays gravity-time ∝ fall distance; a LOW board in the endgame is a TEMPO TAX
(matches the tape: experts hold maxh 13-15 late; our slowest phase is the emptied endgame board).
The eval has no notion of time — this is the cheapest place to give it one.
Arms (same baseline winholes80, same seeds, same primary): `winh80_tall8_12` (ENDK=8, ENDH=-12 =
REWARD height when vcount<=8) and `winh80_tall8_24` (ENDH=-24). Weight-mux on existing infra; run 9's
flat result for negative ENDH was L20-DRIP with clear-rate primary and does not transfer.
Runs after EXP1 finishes (18b). Same decision rule; 18 and 18b findings pool into ONE max-of-6 caveat.
