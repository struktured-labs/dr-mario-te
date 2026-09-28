# RESULT (2026-09-27): STEER6 "BUILD TOWARD A CLEAR"

- Phase 1 prior art: `PRIOR_STEER6.md` (`7205268e`).
- Phase 2 measurement spec: `MEASURE_STEER6.md`.

## Phase 2: how big is the stuck-virus prize? (ANTIBODY in sim, 600 seeds × 4 conditions)
**Setup:**
- Instrument: `stuck_probe.py`. The probe only clones boards: 9/9 rows are identical to banked rows, and local ==
  Hetzner 4/4.
- Rows: `steer6/measure/`. Analysis: `analyze_steer6_measure.py` → `steer6/measure/analysis.txt`.
- **Stall** = consecutive decisions in which NO remaining virus has a clearing move with the actual pill ("act").
  This is the couch lulu-G1 definition.
- "str" = no clearing move with ANY colour pair: the board is structurally sealed.

| | gb OWNER-0804 | gb OWNER-2026-09 | gb **lulu fit** | race lam 4.7 (M140 δ2.65) |
|---|---|---|---|---|
| outcome | tap-out 23.0% | tap-out 21.8% | tap-out 18.5% | tap-out 26.7%; race win 68.5% |
| games with a stall ≥ 10 / ≥ 20 (act) | 85% / 59% | 78% / 56% | 77% / 50% | 80% / 54% |
| games with a SEALED stall ≥ 20 (str) | 53% | 48% | 44% | 46% |
| decisions spent inside a stall ≥ 10 | 32% | 33% | 30% | 34% |
| stall length p50 / p90 (≥ 10) | 18 / 66 | 19 / 82 | 17 / 66 | 18 / 90 |
| viruses left at stall start (p50) | 4 | 4 | 4 | 5 |
| **losses dying INSIDE a stall** (act ≥ 10) | **75%** of tap-outs | **76%** | **83%** | kill 64% · **slow 70%** |
| **losses = a terminal stall ≥ 20 that started at ≤ 4 viruses** | **41%** of tap-outs | **45%** | **47%** | slow losses **52%**; kills 13% |
| wins: pills spent in stalls ≥ 10 | 37% of pills | 32% | 31% | 25% (**≈ 50 s per won race**) |

**How stalls end** (str stalls ≥ 10, all conditions):
- **~90% are unlocked by the AI's OWN placements.** Garbage unlocks 3–5% (26–40 per 600 games).
- act stalls end mostly because the right pill COLOUR finally arrives: unlocked_pill ≈ 55–60%. The board was
  already structurally clearable; the bot was waiting on colour.

**Is the death-in-a-stall a consequence of the full bottle?** No:
- The terminal stalls in tap-outs are long: median **44–87 pills**, and 46–64% last ≥ 50 pills.
- They start at a median of **3 viruses left**.
- These are endgames where the bot is stuck for dozens of pills while the bottle fills, not the last few pills of a
  full board.
- Race kills are different: they are short (p50 29 pills) and early (10 viruses left). Those are not this problem.

**Reading:**
- **The prize is large and concentrated in the endgame.**
  - About **45% of all gate-(b) tap-outs** (≈ 10 pp of absolute tap-out at the 22% base rate) are "stuck endgame"
    deaths: a stall of ≥ 20 pills that began with ≤ 4 viruses left.
  - About **half of the slow race losses** are the same thing.
  - **Even the wins bleed tempo:** a quarter to a third of all pills are spent with no clearing move, about 50 s per
    won race. That is the "lulu outraced it by ~1 virus/min" gap.
- **The couch G1 stall is typical, not a fluke.** Its shape matches: 4 viruses left, own-pill unlocks, ~100 pills.
- **Garbage almost never unlocks a stall in sim.** So a term that makes the AI build the support itself is aimed at
  the right actor.
- **Caveat:** these are the sim's straight-drop semantics. On silicon, tucks add moves the probe cannot see, so the
  true stall rate may be somewhat lower.
