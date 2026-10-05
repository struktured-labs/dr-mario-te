# RESULT (2026-10-04, Claude): FAIR vs FAIR2 on the couch. Was FAIR "more aggressive in the opening"?

**Owner, after match 3:** *"it seemed more aggressive in the opening than fair2? any chance of that?"*

**Short answer:**
- **Yes, the openings differed.** In every FAIR game the AI's first send came before every FAIR2 first send, and it
  sent more in the first 30 s.
- **No, the build didn't cause it.** The same brain, on the same virus layouts and capsule sequences, predicts the same
  pattern.
  - In 3 of the 5 FAIR games, a 2-pill combo was available at the start.
  - Execution fidelity in the opening was identical: 84% on both builds.
- **Over whole games the send rates were the same:** about 5–6 volleys/min, nearly all 2-cell.
- **The owner's M3 G1 claim is confirmed.** The top four cells of column 4 were AI garbage, and the last of them
  plugged (0,4).
- Every figure here is **PROVISIONAL**: 5 games per build.

## Setup
**Builds:**
- **FAIR** = cart dbbb5007 + rbf 318607aa (fw 1488e158). Matches 1 and 3.
- **FAIR2** = cart b1b57638 (fair D + DRABORTSTALE) + rbf V11 43aa62d5 (fw c51d2e21). Matches 2 and 4.
  - V11 is 1488 + TUCKREACH + TUCKLIVE + ROOTORD + LEFLUSH. Its main search is the same as FAIR's; only tucks and
    root order differ.

**Recordings** (L11 MED, AI = P2):

| recording | contents | game windows (s) |
|---|---|---|
| `2026-10-04 08-59-07.mkv` | M1 | G1 0–330, G2 348–592 |
| `2026-10-04 19-15-50.mkv` | M2 | 42–122, 148–356, 372–546 |
| | M3 | 615–662, 692–726, 734–770 |
| | M4 | 855–1107, 1126–1302 |
| `2026-10-04 20-05-50.mkv` | M5 G2 | 15–349 |

- M1 G3, the 5-s fluke, is excluded.
- **Log correction:** M2 G2 was NOT an AI full clear. The recording and the HUD show 32 / 01: the owner topped out
  with 1 AI virus left.

**Method:**
- **Reader** (`scan2_fair_20261004.py`): one decode reads BOTH bottles.
  - The geometry is `geom_fair_20261004.json`, refit with `geomfit_fair_20261004.py`.
    - P2 = the 10/03 fit.
    - P1 x0 = 424.6. Scored by linked halves − 2×violations: 12 violations / 815 cells.
    - The old "violations only" score is degenerate: a half-cell shift reads everything as singles.
  - Board virus counts equal the HUD on the frames checked.
- **Tracker:** the hidden-spawn tracker on each bottle, plus a new repair, `fair_20261004.repair`, for the
  **clear-pop artefact**.
  - The next capsule can appear while the previous clear's pop tiles are still drawn. Then the settled board keeps a
    capsule half, and the "landing" is a row-0 hover or is missing.
  - Repair: drop floating cells, then re-derive the landing from S_{k+1}. Exact matches are preferred, and a
    spawn-cell landing is only replaced by an exact one.
  - The repair also recovered a lost AI combo in M3 G1: a 5-s cascade plus garbage step.
- **Mechanics gates** (S_k + landing + faithful resolve explains S_{k+1}):

  | seat | explained | exact | via garbage |
  |---|---|---|---|
  | AI | **878/881** | 821 | 57 |
  | owner | **623/633** | 511 | 112 |

- **AI sends, two instruments:**
  - **Sender side:** each AI placement's ROM comboCounter (matched runs summed over the cascade), giving an attack of
    size min(runs, 4).
  - **Receiver side:** garbage appearing on the owner's board (`refit_sends_202610.volleys`, verbatim).
    - **ROM column rule: 93/93 checkable volleys conform, 0 violations.**
  - Reconciled under the ROM **accumulation** rule: attacks sent before the receiver's next checkAttack add up, capped
    at 4.
  - 117 of 134 attacks were assigned to a landed volley. 17 were in flight when the game ended: the target topped
    out first, or (9 of them) a volley went unseen in M1 G1's noisier owner track.
  - Two merged 2-sends land as one **4**: M3 G1, M3 G3 and M4 G2.

## Per game
- Opening windows count from the first AI spawn.
- `*` = the game ended before 60 s.
- "brain-only" = the silicon-faithful brain (braingap `Leaf6FwDecider`, all switches on), placing the observed
  capsules with perfect execution and no garbage.
- Lane cells = the cells of the owner's columns 3 / 4 above the top virus at death, by provenance (owner's own pills
  vs AI garbage), from `lane_fair_20261004.py`.

| game | build | len s | AI 1st send s (brain-only) | AI sends 0–30 s (brain-only) | 0–60 s volleys | whole game volleys/min, cells/min | AI pills/min, viruses/min 0–60 s | owner pills/min, viruses/min 0–60 s | silicon == brain | owner's death (spawn plug) |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 G1 | FAIR | 322 | **3.7** (3.7) | 4 (4) | 5 | 5.4, 12.1 | 37, 24 | 30, 11 | 81.5% | none: AI full clear, owner at 17 |
| M1 G2 | FAIR | 236 | **2.8** (2.8) | 2 (3) | 4 | 5.6, 11.9 | 39, 25 | 29, 15 | 83.3% | own pill at (0,3)/(0,4). Lane cells: own 15 / AI garbage 6 |
| M3 G1 | FAIR | 37 | 13.6 (14.7) | 4 (3) | 5* | **8.2, 16.3** | 42, 34 | 24, 13 | 88.5% | **GARBAGE**: a yellow at (0,4) from a {0,4} pair. Col 4 rows 0–3 all garbage |
| M3 G2 | FAIR | 27 | 15.2 (16.1) | 2 (2) | 2* | 4.4, 8.8 | 48, 33 | 37, 11 | 68.2% | own pill locked at the spawn cells. Lane cells: own 4 / garbage 0 |
| M3 G3 | FAIR | 30 | **3.4** (3.4) | 4 (4) | 4* | 7.9, 15.9 | 38, 34 | 32, 12 | 89.5% | own pill at (0,3). Lane cells: own 6 / garbage 3 |
| M2 G1 | FAIR2 | 72 | 15.3 (10.7) | 3 (2) | 6 | 5.9, 11.7 | 41, 18 | 30, 7 | 89.4% | own pills. Lane cells: own 13 / garbage 1 |
| M2 G2 | FAIR2 | 200 | 17.7 (17.7) | 2 (3) | 5 | 5.1, 10.5 | 41, 28 | 31, 11 | 78.2% | own pills. Lane cells: own 12 / garbage 1 |
| M2 G3 | FAIR2 | 168 | 18.2 (15.4) | 3 (3) | 3 | 5.7, 11.8 | 41, 18 | 33, 17 | 88.9% | own pill: the last capsule locked at row 0, cols 4–5. Lane cells: own 13 / garbage 3 |
| M4 G1 | FAIR2 | 241 | 30.0 (30.0) | 1 (1) | 3 | 5.0, 10.9 | 33, 22 | 31, 23 | 82.1% | none: AI full clear, owner at 5 |
| M4 G2 | FAIR2 | 164 | 36.8 (15.7) | 0 (2) | 2 | 4.4, 8.8 | 34, 16 | 32, 27 | 85.3% | none: the **AI** topped out (`m4g2_fair_20261004.py`) |

- **Volley sizes landed on the owner:** 2-cell for 93 of 115 explained volleys; 3-cell 9; 4-cell 8 (mostly merged
  2-sends); and five 1/5/6-cell readings, all on the noisier owner tracks of M1 G1, M1 G2 and M4 G1.
- **Whole-game AI send rate, pooled:** FAIR 5.7 volleys/min, FAIR2 5.1. That is about 2.4× the owner's fitted rate
  (owner_fit_202610: 2.36/min).

## FAIR vs FAIR2 (game = unit, exact two-sided permutation p; n = 5 vs 5, PROVISIONAL)

| metric | FAIR | FAIR2 | p |
|---|---|---|---|
| AI first send (s) | 3.7, 2.8, 13.6, 15.2, 3.4 | 15.3, 17.7, 18.2, 30.0, 36.8 | **0.008** (the floor for 5 vs 5) |
| AI volleys in 0–30 s (pooled per min) | 16 (6.5/min) | 9 (3.6/min) | 0.095 per game |
| AI viruses/min, 0–60 s | 30.0 | 20.4 | 0.032 |
| AI volleys/min, whole game (per-game mean) | 6.3 | 5.2 | 0.25 |
| AI pills/min, 0–60 s | 40.9 | 38.0 | 0.33 |
| owner pills/min, 0–60 s | 30.5 | 31.4 | 0.65 |
| owner viruses/min, 0–60 s | 12.4 | 17.0 | 0.30 |

- **The comparison the owner made, M3 (FAIR) vs M2 (FAIR2), 3 vs 3:**
  - First send: 3.4 / 13.6 / 15.2 s vs 15.3 / 17.7 / 18.2 s.
  - AI clear pace over the opening: 33–34 viruses/min vs 18–28.
  - p = 0.1 on both, which is the floor for 3 vs 3.
- **What the owner noticed was real:** earlier first sends, more sends in the first 30 s, and a faster clear pace in M3.

**Why it is not the build:**
1. **Same layout, same brain, same prediction.**
   - The brain-only first send falls on the same pill as silicon's in 6/10 games.
   - It falls at **pill 2** in M1 G1, M1 G2 and M3 G3, exactly the three ultra-early FAIR sends.
   - 0–30 s sends, brain-only vs silicon: FAIR 16 vs 16, FAIR2 11 vs 9. Most of the 16-vs-9 gap is in the layouts and
     capsule sequences, not the silicon.
2. **Execution in the opening was identical.**
   - Silicon == brain over the first 60 s: FAIR 120/143 (83.9%), FAIR2 159/190 (83.7%).
   - Whole games: FAIR 82%, FAIR2 84%.
3. **FAIR2's layouts had more high viruses:** 13 / 16 / 18 / 10 / 17 in rows 0–8, vs FAIR 11 / 11 / 13 / 12 / 16. This
   fits FAIR2's slower AI clear pace in the opening.
4. **The two builds share the main search.** A brain-level opening difference is not expected, and none is seen.

**What is left over (n tiny, not evidence of a mechanism):**
- FAIR2 sent about 2 fewer volleys in 0–30 s than its brain-only expectation.
- Mostly M4 G2: first send at 36.8 s vs 15.7 s brain-only. That game had the day's highest-virus layout, and the
  owner's best opening (27 viruses/min).

## The owner's M3 claims
- **M3 G1, "garbage … outright killed the spawn cells": CONFIRMED.**
  - The AI sent 5 attacks in 37 s (8.2/min, the day's highest). 3 volleys landed, one of them two 2-sends merged into a
    4.
  - The owner was the slowest of the day here: 15 pills in 37 s. A slow receiver collects merged volleys (ROM
    accumulation).
  - At death, column 4 rows 0–3 were all AI garbage. The killing cell was a yellow from a {0,4} pair, which stayed at
    row 0 because column 4 was full to row 1. The owner's column 3 was at 12.
  - Frame trace: the garbage lands at 657.13 s; the next throw at 659.15 s overlaps it.
- **M3 G2 and G3 were not garbage deaths.**
  - G2: the owner's own pill locked at the spawn cells.
  - G3: the owner's own pill at (0,3).
  - Garbage was 0 of 4 and 3 of 9 of the lane cells. These two match the owner's own "I messed up".
- **Across the day:** of 7 owner deaths, 1 was made by garbage (M3 G1). The other 6 were the owner's own pills in the
  spawn lane: own 4–15 cells vs garbage 0–6.

## Bonus: late flips and hybrids by build
Whole games, brain classifier:

| | silicon == brain | LATE-FLIP | hybrid proxy |
|---|---|---|---|
| FAIR | 315/383 (82%) | 7 | 41 |
| FAIR2 | 426/508 (84%) | 9 | 54 |

- The hybrid proxy is a straight-drop miss with the brain's orientation at another column, or the brain's column at
  another orientation.
- Per 100 pills these rates are about equal across the builds.
- Exact hybrid counts need the co-sim timelines. Those exist only for M4 G2 (10 HYBRID of 109); see
  `cosim_m4g2_fair_20261004.jsonl`.

## Also in this lane (reported separately, files here)
- **M4 G2, FAIR2's tap-out** (`m4g2_fair_20261004.py`):
  - A 45-pill sealed-virus stall at 16–17 viruses on the day's highest layout. No virus-clearing move existed on 41 of
    those 45 pills.
  - It ended with HYBRIDs at p84, p105 and p107 that the Mesen replay of the real cart does not reproduce.
  - PROPH-FIRST explains p106 and p107, but not p13 or p84, which were not armed.
  - Stale answers, and answers delayed by +3 to +25 f, do not reproduce the misses.
  - DAS carry is untested: the probe injects after filler pills and resets the pad.
  - Silicon locks a median 18 f later than the replay.
- **M5 G2, FAIR, owner full clear** (`stall_fair_20261004.py`):
  - Column 6 was walled to row 0 by p65: the AI's own early halves p4, p13 and p14, plus 3 garbage cells.
  - Column 7's six viruses, capped only by garbage, were then unreachable on 119/119 stall pills.
  - Only 3 viruses were cleared in the last 120 pills.

## Files (`experiments/couch_forensics/`)
**Code:**
- `scan2_fair_20261004.py`, `geomfit_fair_20261004.py` and `geom_fair_20261004.json`
- `fair_20261004.py` (track | analyze): windows, repair, sends, reconciliation, pace, death, compare
- `brain_fair_20261004.py`: the silicon-faithful brain per pill, plus the opening counterfactual
- `lane_fair_20261004.py`: spawn-lane provenance

**Banked cases:**
- `cases_fair_20261004_ai_pills.jsonl`: per AI pill, with runs, sent and cascade steps
- `cases_fair_20261004_owner_pills.jsonl`
- `cases_fair_20261004_volleys.jsonl`: every AI attack with its landed volley, every owner-board volley with its sends
  and ROM-column check, and the owner's sends as received by the AI
- `cases_fair_20261004_brain.jsonl`

**Summaries:**
- `summary_fair_20261004.json`: per game, the windows, the compare block and the permutation tests
- `brain_fair_20261004.json`, `brain_first_send_fair_20261004.json`, `lane_fair_20261004.json`

**M4 G2:**
- `m4g2_fair_20261004.py`, `cases_m4g2_fair_20261004.jsonl`, `pubtrace_m4g2_fair_20261004.jsonl`
- `cosim_m4g2_fair_20261004.jsonl`, `m4g2_replay_fair_20261004.txt`
- `mesen_m4g2_delay_fair_20261004.txt`, `mesen_m4g2_stalevalid_fair_20261004.txt`

**M5 G2:** `stall_fair_20261004.py`, `stall_m5g2_fair_20261004.json`, `cases_stall_m5g2_fair_20261004.jsonl`

**Not committed:** per-frame reads, raw tracks and sample frames are in `~/projects/dr_mario_rl/tmp/fair_20261004/`.
The Mesen logs are in `dr-mario-lateflip-wt/tmp/lateflip/M4G2_fair2_*`.
