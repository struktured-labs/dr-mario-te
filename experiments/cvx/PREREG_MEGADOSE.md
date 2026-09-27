# PRE-REG (2026-09-22): MEGADOSE A/B k_clock=40 vs k=0 on live NES

FPGA CLOCK40 is soaking. This is the teacher-on-real-ROM gate, not another Quartus.

**ROM:** base `drmario.nes` (1P). VS-CPU ROM is banned (AI hook eats input).
**Driver:** Mesen2 file bridge + `VsPolicy` d3 winner trunk (same as vs_choose).
**A:** k_clock=0 (= `_choose_base(winner)`). **B:** k_clock=40.
**Level:** 11 MED. **Seeds:** 40..47 (8-bit RNG write at level-select). Paired.
**n=8 per arm** (16 games). Screen, not a ship claim.

**Metrics:** clear (won), pills, end_v. Diverge vs sim is diagnostic only.

**Hold:** B clear rate not >10pp worse than A. Faster (fewer pills) is supporting,
not required. Collapse = MEGADOSE fail; FPGA soak can stay but we do not promote
the term as NES-sane.

**Not this run:** 2P VS on Mesen, Hartford poke, Quartus, kc34.

## RESULT (2026-09-22) — FAIL the 10pp bar, not a slam collapse

16 live games, L11 MED, seeds 40–47 paired. `play_one_game` auto-advances after
a clear, so `pills=200` is the cap on the *next* level. Real L11 metric is
`level_wins>=1` / `pills_to_first_win`.

| seed | k=0 L11 | pills | k=40 L11 | pills |
|---|---|---|---|---|
| 40 | clear | 90 | clear | 83 |
| 41 | clear | 73 | **miss** (7 left) | — |
| 42 | clear | 82 | clear | 98 |
| 43 | **miss** (2 left) | — | **miss** (12 left) | — |
| 44 | clear | 108 | clear | 98 |
| 45 | clear | 61 | clear | 73 |
| 46 | clear | 147 | clear | 96 |
| 47 | clear | 98 | clear | 97 |
| **rate** | **7/8** | mean 94 | **6/8** | mean 91 |

delta_clear = −12.5pp → prereg FAIL (bar was −10pp). Extra miss is seed 41.
Clears are not slower. n=8 is one game. FPGA CLOCK40 soak stays. Do not
Quartus a revert. Next MEGADOSE if anyone cares: stop at first level-clear
(don’t farm L12) and n≥24.
