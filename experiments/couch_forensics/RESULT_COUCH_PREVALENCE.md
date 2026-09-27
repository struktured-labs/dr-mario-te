# RESULT (2026-09-25, Claude): prevalence of driver overrides across all 7 recorded CHAIN540 couch games

Question: the 9/25 G2 death (RESULT_COUCH_G2.md) ended in driver overrides (DISTGATE clamp + DRPROPH escapes).
Is that a rate or a one-off? Same pipeline and gates, applied to every AI placement in both recordings (AI = P2):
- 9/24 night: G1, G2, G3, all won.
- 9/25 morning: G1, G3, G4 won; G2 lost (tap-out).

## Headline
- **DRPROPH fired only in the lost game.** It fired 24 times in 9/25 G2 and **0 times in the six won games**
  (363 verified placements). A won game never reached the throat-ledge regime (first occupied row of col 3/4 ≤ 2).
- Driver overrides (clamp + PROPH-against-brain + late flip), by population:

  | population | overrides |
  |---|---|
  | won games | **4.4%** (16/363) |
  | G2, whole game | 22.1% (15/68) |
  | G2, last 12 placements | **8/12** |

  The densest 12-placement window in any won game holds **3**, and **0 of 329** such windows reach 8.
- **So the death sequence is unusual in override density.** The overrides are concentrated in the ledge regime
  that only the lost game entered. Caveat: the stall that led there was the brain's own play (RESULT_COUCH_G2), so
  overrides are partly a consequence of the tall spawn lane, not only its cause.
- **What follows an override:** +0.4 to +0.5 rows of extra spawn-lane height over the next 3–5 pills vs matched
  MATCH placements. The CI includes 0 (n=27).
  - Clamp short-landings alone: **+1.0 row** excess (n=10–11). Late flips: ~0.
  - P(ledge within 5 pills): 0.19 after an override vs 0.09 matched.
- **No routine DAS carry.**
  - Normal first lateral move: median **f18** (n=370; f14–f28 holds 97%).
  - 14 moved before f10. 11 of them one column at f5, followed by a 16-f fresh-press gap: a pre-computed answer
    (DRPRESPIPE), not carry. Only **2/370** show a carry-like f8 first move then a 6-f cadence.

## 1. Per-game rates (VERIFIED placements; all placements in brackets)
| game | result | n | MATCH | clamp short | PROPH esc. (against brain) | late flip | **override %** | PROPH fired | PROPH → MATCH | tuck | other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 9/24 G1 | won | 54 | 43 | 2 | 0 | 1 | **5.6%** [5.0% of 60] | 0 | – | 0 | 8 |
| 9/24 G2 | won | 103 | 84 | 3 | 0 | 3 | **5.8%** [5.4% of 111] | 0 | – | 1 | 11 |
| 9/24 G3 | won | 24 | 22 | 0 | 0 | 0 | **0.0%** [0/24] | 0 | – | 1 | 1 |
| 9/25 G1 | won | 82 | 59 | 2 | 0 | 1 | **3.7%** [5.4% of 92] | 0 | – | 2 | 14 |
| **9/25 G2** | **lost (tap-out)** | 68 | 45 | 3 | **5** | 7 | **22.1%** [20.8% of 72] | **24** | 14 | 2 | 6 |
| 9/25 G3 | won | 43 | 35 | 1 | 0 | 2 | **7.0%** [8.5% of 47] | 0 | – | 1 | 4 |
| 9/25 G4 | won | 57 | 52 | 0 | 0 | 1 | **1.8%** [1.6% of 61] | 0 | – | 0 | 4 |
| **pooled** | | **431** | 340 (78.9%) | 11 | 5 | 15 | **7.2%** [7.3% of 467] | 24 | 14 | 7 | 48 |

- **PROPH, when it fired (24):** 5 escapes went AGAINST the brain's side, 14 ended where the brain wanted anyway
  (its target was already on the pulse side), and 5 fell into other categories.
- **Short landings without the clamp signature:** 5 more, not counted as overrides.
- **OTHER (48, 11%):** silicon landed on a different target than the sim with no intermediate pose match.
  Candidates are anytime-search truncation, sim/silicon brain differences and residual misreads. It is not
  counted as a driver override and needs its own look.

## 2. What follows an override
Spawn-lane height = max(height c3, c4). The same quantity is measured 3 and 5 placements later, against MATCH
placements from any game with the same spawn-lane height (±1). Verified steps only.

| horizon | n overrides | Δ lane, override | Δ lane, matched MATCH | excess [95% CI] | P(ledge fo≤2), override vs matched |
|---|---|---|---|---|---|
| +3 pills | 27 | +0.15 | −0.26 | **+0.41** [−0.15, +1.02] | 0.22 vs 0.17 |
| +5 pills | 27 | +0.11 | −0.36 | **+0.47** [−0.32, +1.29] | 0.19 vs 0.09 |

By type (excess Δ lane at +3 / +5):
- **Clamp short-landing:** +0.99 / +1.06 (n=10 / 11).
- **PROPH escape:** +0.21 / +0.50 (n=3 / 1, too few).
- **Late flip:** −0.02 / +0.05 (n=14 / 15).

Reading: clamps look harmful, roughly a row of extra spawn-lane height; late flips look neutral. Neither passes a
CI at this n.

## 3. Steering timing (frames from the preview change; no-PROPH placements with a lateral move, n=370)
`5:11 6:1 8:2 13:1 14:10 15:102 16:23 17:21 18:17 19:18 20:16 21:25 22:23 23:17 24:16 25:25 26:26 27:10 28:1 38:1 39:2 65:1 91:1`
- Median f18. That is answer latency, not the 6-f think gate.
- Of the 14 moves before f10:
  - 11 are a single column at f5 followed, where observable, by a 16-f gap: a fresh press, so an early (pipelined)
    answer.
  - 2 (9/25 G1 k10, G2 k19) move at f8 and then keep a 6-f cadence, consistent with carry.
  - 1 at f6.
- Direction vs the previous pill's last move: 8/12 same, against a 57% base rate. That is not diagnostic, since the
  ROM allows redirecting carry between pills.
- **Carry is not the driver's path (≤ 2/370).**
- PROPH pulses: first move at f3–5 in 21/23.

## 4. G2 in context
| | override density |
|---|---|
| won games, all placements | 4.4% |
| won games, mean 12-window | 0.61 / 12 |
| won games, max 12-window | **3 / 12** (9/25 G3, from idx 20) |
| G2, whole game | 22.1% |
| **G2, last 12** | **8 / 12** (clamp 2, PROPH-against 4, late flip 2) |

PROPH-against-brain escapes in any won-game 12-window: max 0.

## Gates
- **Geometry, per video:** `fit_geometry.py` reproduces the 9/25 origin (1131.50, 340.25). 9/24 = (1131.75, 340.50),
  within 0.3 px, so the same reader applies.
- **GATE 1a, virus counter:**
  - 9/24: 14/15 frames agree.
  - 9/25 G1/G3/G4: 6/10.
  - Every mismatch was a clear-animation frame: hollow "pop" tiles read as viruses (+4 = a 4-clear of pill halves).
    Re-checked 0.5 s later, 4/5 agree; the 5th was caught mid-clear again.
  - Placements are unaffected: the settled board is taken after pops vanish.
- **GATE 1b, colours:** 3/3 frames on 9/24 by eye (and 3/3 on 9/25 earlier).
- **GATE 2, decider plumbing:** 428/428 (unchanged code).
- **Mechanics gate with garbage (`mech_check.py`):**
  - S_k + landing + resolve, then any 0–4-single garbage volley (repeated columns allowed), must equal S_{k+1}.
  - **435/453 steps (96%)** reproduce exactly (370) or via a garbage volley (65).
  - The 18 unexplained steps mark their two adjacent placements UNVERIFIED (36 of 467). Rates are over verified
    placements, with the all-placements rate beside them; conclusions don't change.
- **Consistency:** the full-G2 run reproduces the death-window run on all 51 overlapping placements (category and
  sim action identical).

## Caveats
- One lost game and six won. "Overrides are rare except in the ledge regime" is well supported. "Overrides cause
  deaths" is n=1 plus the suggestive +1-row clamp effect.
- The ledge regime is reached through the brain's stall play first. A driver fix (PROPH direction from the ply-2
  plan, pre-hold) addresses the exit from that regime, not the entry.

## Files
- `fit_geometry.py`: per-video origin fit.
- `run_games.sh`: slice, track, analyze, classify per game.
- `mech_check.py`: garbage-aware mechanics gate. Outputs are in `mech/`.
- `prevalence.py`: this report. Its output is in `prevalence_out.txt`.
- `cases_<video>_<game>.jsonl` (7 files) and `cases_all_games.jsonl`: all 467 cases, with game, result and
  verified flag.

No footage or frames are committed; they are in gitignored `tmp/couch_forensics/`.
