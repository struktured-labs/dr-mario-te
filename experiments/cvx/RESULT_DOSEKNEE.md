# RESULT (2026-09-24, Claude solo) — PREREG_DOSEKNEE.md: DRCHAIN=540 passes screen AND holdout
Firmware-faithful brain (winner leaf + strand20, StrandedChainD3Decider; tucks/veto not modelled).
VS-RACE vs a 177-s human, 6 volleys/min:
| block | n | fw180 | fw540 | diff (delta 2.65 fitted) | diff (delta 2.0) |
| screen 36734+ | 300 | 88.0% | 95.3% | +7.3pp [+3.3,+11.3] | 77.7 -> 84.0 |
| holdout 40134+ (Hetzner) | 200 | 85.5% | 94.0% | +8.5pp [+3.5,+14.0] | +6.5 [-0.5,+14.0] |
Gate (b) tap-out, owner burst model:
| screen | 600 | 2.83% | 2.33% | -0.50pp [-2.17,+1.00] |
| holdout | 400 | 4.50% | 3.00% | -1.50pp [-4.25,+1.00] |
Tiles sent/game: ~49-52 -> ~63-66. fw270 +3.3 (ns), fw360 +2.7 (ns) in the screen (non-monotone = noise).
Per the pre-registered rule fw540 is a FIRMWARE CANDIDATE: DRCHAIN=540 (a_chw = 135, fits the 8-bit reg).
Silicon path: Childproof recipe (theta400dblcanon veto2fixa, seed 13) with DRCHAIN=540, pinned-seed rebuild
(ROM-only diff reproduced placement exactly for Stomper), then soak + couch check. Owner go-ahead needed.
