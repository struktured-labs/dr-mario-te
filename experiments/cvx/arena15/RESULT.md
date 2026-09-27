# #15 RESULT (2026-09-23) — send/gcol/halves cannot make the arena kill

winner vs holes80, n=80 seeds × 2 seats = 160/cell, seeds **50134+**.
Pinned `VsPolicy`, ws=0.

| config | winner win | topout+crush | mean sent | how |
|---|---|---|---|---|
| cells g6 h4 (default) | 89/160=55.6% | **0.6%** | 32.3 | 159 clear, 1 crush |
| lines g6 h4 | 113/160=70.6% | **0.0%** | **3.5** | 160 clear |
| cells g8 h4 (cols 0/4 on) | 92/160=57.5% | **4.4%** | 32.8 | 153 clear, 5 topout, 2 crush |
| cells g6 h8 | 89/160=55.6% | 0.6% | 32.4 | same as default |
| lines g8 h8 | 98/160=61.2% | 1.2% | 3.5 | 158 clear, 2 topout |

**Reading.** `lines` *reduces* garbage (2 simultaneous lines are rare) so the arena
gets *more* race, not less. Opening spawn-adjacent cols 0/4 is the only knob that
moves how-mix, and only to 4.4% — not Hartford's ~70%. Halves cap 8 is a no-op
(cells//3 already ≤4). The cells//3 proxy is **not** why nobody dies; both
players clear viruses faster than this injector can plug them.

Do not re-score kc40 vs holes80 under a "calibrated" arena: none of these configs
is in the tape neighborhood. Next physics levers (not this sweep): fire on 1
line, delayed/stacked garbage, or a slower opponent. Arena win rate stays a
**race** metric. Survival stays gate (b) / Hartford TRATE, which is Claude's #16/#17.
