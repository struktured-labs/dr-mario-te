# RESULT (2026-09-24) — PREREG_ADAPTIVE1.md: opponent-aware chain dose is NULL; "more chain" is the only hint
vs a modelled human (live race), 6 volleys/min, 2.65 s/tile, base = fw180 (winner leaf + chain180 + strand20):
| policy | primary M177 (n=300) | primary M220 | holdout M177 (n=200) | kills (prim/hold) |
| fw180 | 88.3% | 92.3% | 86.0% | 1 / 3 |
| fw360 | +3.0 [-1.3,+7.0] | +2.3 [-1.3,+6.0] | +5.5 [+0.5,+11.0] | 1 / 5 |
| press | +0.7 [-2.0,+3.3] | +1.7 [-0.3,+3.7] | +1.0 [-2.0,+4.0] | 1 / 3 |
| cruise | -0.7 [-5.0,+3.7] | -0.3 | -1.5 [-6.5,+4.0] | 3 / 3 |
| press_cruise | -0.7 | +0.3 | +1.5 [-4.0,+7.0] | 3 / 3 |
Per the pre-registered rule NO policy passes (needs CI>0 in BOTH blocks AND kills not higher).
Reading: at 88% the residual losses are almost all RACED (34/35); the lever against fast humans is more
attack, and it pays UNCONDITIONALLY (fw360 sends 56.6 vs 42.3 tiles) — gating it on race state only
removes attack from the moments it would have helped. Next: chain-dose knee (180/270/360/540) on VS-race
+ gate (b) survival before any firmware change. Silicon note: w_chain is a baked firmware constant
($70E6 copro MMIO), so a dose change = one pinned-seed rebuild (placement reproduces; ROM-only diff).
