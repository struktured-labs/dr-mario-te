# RESULT (2026-10-05/06, Claude): dr. lulu vs ANTIBODY_DIST_FAIR. The AI won both matches, 3-2 and 3-1

**The first match wins any bot has taken off dr. lulu, with a fair bot.**

- **Build:** couch cart **dbbb5007** + rbf **318607aa** (fw 1488e158). The cart is fair settle (DRSETTLE=3, DRSETTLEPIN=0)
  + DRPROPHFIRST + DRLATEGUARD + DRSTUDYEND on DIST60. FAIRPLUS (cart 5b3d8183 = + DRLGPRESTART + DRDISTROW=2) was NOT
  loaded.
- **Recording:** `/mnt/data/Videos/2026-10-05 20-09-41.mkv`, 1080p60 clean HDMI.
  - 0–11 s is the owner's previous match-final screen (excluded).
  - 2208–2313 s is the DRSTUDYEND hold after the last game.
- **Players:** dr. lulu = P1 (left), AI = P2 (right). L11 MED.
- **n = 9 games: every figure here is PROVISIONAL.** The owner reported that she was frustrated by the end.

## Short answer

1. **Results:** the AI won 6, dr. lulu 3. Two rows of the quick read were wrong:
   - M2 G1 and M2 G2 were **AI clears** (14/00 and 06/00), not her top-outs.
   - M2 G4 ended at 2208 s, not 2310 s.
   - **The AI won 4 games by clearing first and 2 by her top-out. She won 2 by clearing first and 1 by AI tap-out.**
2. **Why the AI won: opening tempo.**
   - Over the time each spent with more than 30 viruses left, the AI cleared 25.6 viruses/min to her 13.3.
   - It placed 35 pills/min to her 26.
   - In the endgame (12 or fewer left) she was the faster one: 4.9 vs 4.1 viruses/min.
   - **She won only when the AI's endgame stalled:** 201 s at 7 (M1 G2), 59 s at 16 ending in a tap-out (M1 G4), and 36 s at 13
     (M2 G3). In her 6 losses the longest AI stall averaged 33 s.
3. **The AI's endgame stalls are mostly BRAIN/STRUCTURE, not execution.**
   - M1 G2: the 7 last viruses were a 6-virus column-0 stack, plus one virus capped by 4 of her garbage cells.
     - No single placement could clear any of them on 110/110 stall pills.
     - The faithful brain with perfect execution, replayed from any start pill after p26 (43 s in), ALSO stalls at exactly 7.
     - This is the "no build-toward-clear term" class first seen on 9/27 G1.
4. **The M1 G4 tap-out was EXECUTION** (details in section 5).
   - The brain-only replays never top out: 0 of 116 start pills.
   - The decisive pill was p61: a LATEGUARD×PRESTART previous-target execution after her garbage, which FAIRPLUS fixes.
   - The race itself was hers: the AI was stuck at 16 for 59 s while she went 14→3.
5. **Her deaths:**
   - M1 G1: her own pills (lane cells: 24 own, 2 garbage; her own last pill locked in the spawn cells).
   - M1 G3: AI garbage. A garbage single landed at (0,4), on top of a column-4 tower of 5 garbage + 4 own cells.
6. **Her sends:** 2.95 volleys/min and 6.66 cells/min across the 10/05 games; 83/84 checkable volleys obey the ROM column rule.
   - **lulu_fit_202610b** (11 games pooled): 2.84 [2.63, 3.13] volleys/min (was 2.56 on n=2), size mix 2/3/4 = 83/7/10%.
   - The AI sent her about 1.5× more: 4.21 volleys/min, 10.05 cells/min.
7. **FAIRPLUS:** see sections 4 and 7.
   - Per pill, it lands the copro's final answer more often and removes every replayed hybrid.
   - **However,** about half of silicon's misses are NOT reproduced by Mesen of the same cart (the "silicon-only" misses). FAIRPLUS
     cannot target those.
   - Brain-only replays say perfect execution would have flipped only 16 of 187 start points across her 3 wins.
   - **⇒ FAIRPLUS would most likely not have changed her wins, except plausibly M1 G4.**

## 1. Verified results (D1)

Method:
- Game windows come from both bottles' 60 fps reads. Game over is when both previews blank, or both boards freeze for 1.5 s; the
  freeze rule is needed for M1 G5 and M2 G4.
- Final counts come from the HUD, read with per-seat digit templates fitted on this capture. The P1 digit boxes sit about 1 NES px off,
  so one shared template set fails.
- Every ending was also checked by eye on frame tiles.

| game | play window (s) | length (s) | result | final lulu/AI (HUD) | winner | quick read |
|---|---|---|---|---|---|---|
| M1 G1 | 18.2–364.8 | 346.5 | lulu topped out | 06/04 | AI | lulu topped out 06/04 |
| M1 G2 | 369.9–759.3 | 389.4 | lulu cleared | 00/07 | lulu | lulu cleared 00/07 |
| M1 G3 | 771.6–878.0 | 106.4 | lulu topped out | 25/07 | AI | lulu topped out 25/07 |
| M1 G4 | 883.2–1104.8 | 221.6 | AI topped out | 03/16 | lulu | AI tapped out 03/16 |
| M1 G5 | 1112.9–1296.8 | 184.0 | AI cleared | 26/00 | AI | AI cleared 26/00 |
| M2 G1 | 1304.6–1563.2 | 258.6 | AI cleared | 14/00 | AI | lulu topped out 14/01 |
| M2 G2 | 1568.3–1800.7 | 232.3 | AI cleared | 06/00 | AI | lulu topped out 06/01 |
| M2 G3 | 1805.2–2013.6 | 208.4 | lulu cleared | 00/11 | lulu | lulu cleared 00/11 |
| M2 G4 | 2022.0–2208.1 | 186.1 | AI cleared | 14/00 | AI | AI cleared 14/00 |

## 2. Both seats tracked per pill (D2)

- **Reader:** `scan2_fair_20261004.py` at 60 fps, geometry `geom_lulu_20261005.json`.
  - P2 is the 10/03–10/04 fit.
  - P1 x0 was refit to 424.1.
  - Board virus counts match the HUD (checked at t=1000: 20/25).
- **Tracker:** the fixed hidden-spawn tracker (`track_hidden_dist60_20261003.py`), plus the 10/04 clear-pop repair.
  - 31% of the AI's spawns on M1 G4 were hidden same-colour spawns.

| game | lulu pills (hidden) | lulu gate exact/garbage/unexpl. | AI pills (hidden) | AI gate | repairs lulu | repairs AI |
|---|---|---|---|---|---|---|
| M1 G1 | 151 (17) | 120/29/1 of 150 | 212 (22) | 197/14/0 of 211 | unexplained_kept 1 | float_removed 10, landing_rederived:exact 8, landing_rederived:garbage 1, unexplained_kept 2 |
| M1 G2 | 160 (20) | 130/29/0 of 159 | 217 (26) | 198/16/2 of 216 | – | float_removed 1, unexplained_kept 4, landing_rederived:exact 1 |
| M1 G3 | 43 (4) | 34/8/0 of 42 | 62 (9) | 55/5/1 of 61 | float_removed 1, landing_rederived:exact 2 | float_removed 3, unexplained_kept 1, landing_rederived:exact 3 |
| M1 G4 | 100 (32) | 87/12/0 of 99 | 146 (46) | 132/13/0 of 145 | – | float_removed 6, landing_rederived:exact 5 |
| M1 G5 | 87 (16) | 73/12/1 of 86 | 107 (24) | 97/9/0 of 106 | float_removed 2, landing_rederived:exact 3, unexplained_kept 1 | float_removed 6, landing_rederived:exact 6 |
| M2 G1 | 113 (21) | 87/18/7 of 112 | 148 (27) | 135/12/0 of 147 | float_removed 2, landing_rederived:exact 2, unexplained_kept 8, landing_rederived:garbage 1 | float_removed 4, landing_rederived:exact 4 |
| M2 G2 | 91 (9) | 73/17/0 of 90 | 133 (15) | 119/13/0 of 132 | float_removed 1, landing_rederived:exact 1 | float_removed 14, landing_rederived:exact 12 |
| M2 G3 | 91 (23) | 81/7/2 of 90 | 134 (25) | 122/10/1 of 133 | unexplained_kept 2 | float_removed 34, landing_rederived:exact 31, landing_rederived:garbage 2, unexplained_kept 1 |
| M2 G4 | 85 (10) | 71/12/1 of 84 | 97 (11) | 85/11/0 of 96 | unexplained_kept 1 | float_removed 3, landing_rederived:exact 2 |

- **The mechanics gate explains 900/912 of her steps and 1243/1247 of the AI's.**
- Her M2 G1 track has 7 unexplained steps (1491–1542 s). All are 1–3-cell misreads around her rows 0–1 and 12–14. They are reader
  errors, not mechanics.

## 3. dr. lulu's profile (D3)

### Pace (viruses/min / pills/min)

| game | lulu 0–60 s | 60–120 s | ≥120 s | >30 left | 13–30 left | ≤12 left | whole game | AI 0–60 s | AI whole game |
|---|---|---|---|---|---|---|---|---|---|
| M1 G1 | 15.0 / 32.0 | 8.0 / 21.0 | 5.03 / 26.0 | 15.72 / 29.8 | 6.85 / 22.6 | 2.88 / 28.3 | 7.27 / 26.1 | 24.0 / 38.0 | 7.62 / 36.7 |
| M1 G2 | 14.0 / 34.0 | 13.0 / 27.0 | 4.68 / 22.1 | 12.39 / 31.7 | 8.61 / 22.0 | 4.07 / 23.1 | 7.4 / 24.7 | 24.0 / 35.0 | 6.32 / 33.4 |
| M1 G3 | 13.0 / 26.0 | 12.93 / 22.0 | – | 12.84 / 25.7 | 13.46 / 18.8 | – | 12.97 / 24.2 | 30.0 / 37.0 | 23.12 / 35.0 |
| M1 G4 | 18.0 / 33.0 | 12.0 / 28.0 | 8.86 / 23.0 | 18.21 / 32.4 | 10.16 / 25.7 | 9.59 / 24.0 | 12.18 / 27.1 | 18.0 / 38.0 | 8.66 / 39.5 |
| M1 G5 | 10.0 / 30.0 | 8.0 / 24.0 | 3.75 / 31.0 | 10.02 / 26.7 | 3.15 / 30.7 | – | 7.18 / 28.4 | 25.0 / 46.0 | 15.66 / 34.9 |
| M2 G1 | 11.0 / 29.0 | 5.0 / 27.0 | 7.79 / 24.7 | 7.23 / 27.3 | 8.78 / 24.7 | – | 7.89 / 26.2 | 24.0 / 41.0 | 11.14 / 34.3 |
| M2 G2 | 21.0 / 31.0 | 11.0 / 27.0 | 5.34 / 17.6 | 19.43 / 30.7 | 11.7 / 22.2 | 3.15 / 19.7 | 10.85 / 23.5 | 19.0 / 39.0 | 12.4 / 34.3 |
| M2 G3 | 17.0 / 36.0 | 19.0 / 29.0 | 8.14 / 17.6 | 17.18 / 35.3 | 19.06 / 28.6 | 8.1 / 18.2 | 13.82 / 26.2 | 20.0 / 47.0 | 10.65 / 38.6 |
| M2 G4 | 18.0 / 32.0 | 11.0 / 26.0 | 4.54 / 24.5 | 17.74 / 31.5 | 7.67 / 25.4 | – | 10.96 / 27.4 | 26.0 / 37.0 | 15.48 / 31.3 |

| pooled, 9 games | 0–60 s | 60–120 s | ≥120 s | >30 left | 13–30 left | ≤12 left | whole game |
|---|---|---|---|---|---|---|---|
| dr. lulu | 15.22 / 31.4 (9.0 min) | 11.06 / 25.8 (8.8 min) | 5.85 / 23.2 (17.8 min) | 13.25 / 29.5 (12.4 min) | 9.06 / 24.5 (14.6 min) | 4.87 / 23.1 (8.6 min) | 9.51 / 25.9 (35.6 min) |
| AI | 23.33 / 39.8 (9.0 min) | 12.08 / 33.5 (8.8 min) | 3.99 / 34.0 (17.8 min) | 25.61 / 39.4 (6.6 min) | 11.78 / 36.3 (12.9 min) | 4.11 / 32.9 (16.1 min) | 10.88 / 35.3 (35.6 min) |

- **She is a steady ~26 pills/min player.** She is fast in the opening: 15.2 viruses/min over the first 60 s, and 13.3 while she has
  more than 30 left.
- **She is not slower than the AI in the endgame:** 4.9 vs 4.1 viruses/min with 12 or fewer left.
- **The AI wins the opening:** 23.3 vs 15.2 viruses/min over the first 60 s. Its tempo is 40 vs 31 pills/min there, and 35 vs 26 over
  whole games.

### Sends (as received by the other board; fixed tracker; ROM column rule)

| game | lulu volleys/min | lulu cells/min | lulu sizes | lulu ROM ok/checkable | lulu first send (s) | AI volleys/min | AI cells/min | AI sizes | AI ROM ok/checkable | AI first send (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 G1 | 2.43 | 5.73 | 2:11 3:1 4:2 | 12/13 | 7.8 | 5.2 | 12.65 | 2:23 3:3 4:3 6:1 | 25/25 | 12.2 |
| M1 G2 | 2.48 | 5.11 | 2:15 3:1 | 13/13 | 14.7 | 4.5 | 10.7 | 2:21 3:5 4:3 | 21/21 | 3.8 |
| M1 G3 | 2.83 | 5.66 | 2:5 | 4/4 | 24.4 | 4.72 | 13.57 | 2:4 3:1 4:3 | 6/6 | 7.6 |
| M1 G4 | 3.53 | 7.6 | 2:12 4:1 | 12/12 | 4.7 | 3.28 | 6.83 | 2:11 3:1 | 12/12 | 7.9 |
| M1 G5 | 2.95 | 5.91 | 2:9 | 7/7 | 31.9 | 4.31 | 10.27 | 2:11 3:1 6:1 | 12/12 | 4.3 |
| M2 G1 | 2.81 | 5.61 | 2:12 | 11/11 | 12.3 | 4.19 | 8.86 | 2:17 4:1 | 16/16 | 17.5 |
| M2 G2 | 3.42 | 8.67 | 2:9 3:1 4:3 | 10/10 | 11.6 | 4.43 | 10.69 | 2:13 3:1 4:3 | 14/14 | 20.5 |
| M2 G3 | 3.22 | 8.5 | 2:7 3:1 4:3 | 6/6 | 5.7 | 2.41 | 6.32 | 2:6 4:1 5:1 | 4/4 | 32.3 |
| M2 G4 | 3.59 | 8.82 | 2:8 3:1 4:2 | 8/8 | 18.0 | 4.2 | 10.35 | 2:9 3:3 5:1 | 10/10 | 24.6 |

- **ROM column rule (rom_attack_rule):**
  - Her volleys: 83/84 checkable conform. The one violator (M1 G1, 269.5 s, columns 1/2/3/5) has no sender-side attack, so it is a
    tracker artefact.
  - The AI's volleys: 120/120.
- **Sender side vs receiver side:** 87 of her 99 combo placements (ROM comboCounter) are matched to a volley the AI received.
  - The other 12 were in flight when the game ended.
  - 19 of the 104 received volleys have no matched attack.
  - For the AI's sends to her: 146 of 172 matched, 26 in flight.
- **Timing:**
  - She sends flat across a game: 2.9 volleys/min in the first 30 s, 3.2 at 30–90 s, 2.9 after 90 s.
  - By her remaining viruses: 3.2/3.4/3.1 with more than 8 left, and 1.35 with 8 or fewer. She stops sending at the end.
  - Gap median 12.9 s (p10 5.7, p90 40.2).

### Refit: `lulu_fit_202610b.json`

Same key layout as lulu_fit_202610, plus `sessions`, `per_session_rate` and `rate_ci95_game_bootstrap`. The old files are untouched.

| | games | volleys/min | 95% CI (game bootstrap) | cells/min | sizes 2 / 3 / 4 | gap p50 (s) | merged doubles |
|---|---|---|---|---|---|---|---|
| lulu_fit_202610 (9/27, soft 720p) | 2 | 2.56 | – | 6.12 | 77 / 13 / 10% | 16.3 | 3% |
| 10/05 alone (clean 1080p) | 9 | 2.95 | [2.67, 3.27] | 6.66 | 85 / 5 / 11% | 12.3 | 0 |
| **lulu_fit_202610b (pooled)** | **11** | **2.84** | **[2.63, 3.13]** | **6.52** | **83 / 7 / 10%** | **12.9** | 0.7% |

- The 10/05 rate (2.95) is about 15% above 9/27 (2.56). The 9/27 CI is degenerate (n=2).
- **The sims' LULU opponent should use 202610b.** It sends about 2.8/min, mostly 2-cell volleys, not the 4.7 of the 202609 fit.
- Clear pace per game (48 → final, whole game) runs 7.2–13.8 viruses/min. The 9/27 games were 5.6 and 10.1.

### Her deaths (spawn-lane provenance at the top-out, tag tracker)

| game | who topped out | final | spawn cells plugged | what arrived after the last tracked pill | already occupied (own pill) | col 3 above top virus (P own, G garbage) | col 4 above top virus |
|---|---|---|---|---|---|---|---|
| M1 G1 | dr. lulu | 06/04 | [[0, 3], [0, 4]] | – | [[0, 3, 'linked'], [0, 4, 'linked']] | {'P': 12, 'G': 2} | {'P': 12} |
| M1 G3 | dr. lulu | 25/07 | [[0, 4]] | garbage [[0, 4]] (volley cells [[0, 4, 3], [11, 0, 2]]) | – | {'G': 1} | {'G': 5, 'P': 4} |
| M1 G4 | AI | 03/16 | [[0, 3]] | own next capsule locked at row 0: [[0, 2, 2], [0, 3, 1]] | – | {'G': 1, 'P': 15} | {'P': 9} |

- M1 G4's col 3 "G:1" is the AI's own p146 capsule half at (0,3), not garbage. The tag tracker labels every cell that appears after
  the last tracked pill as G.
- **M1 G1 (06/04) was her own error.**
  - Columns 3 and 4 were both 16 tall.
  - Above the top virus: col 3 had 12 own + 2 garbage cells, col 4 had 12 own.
  - Her last pill locked in the spawn cells.
  - The AI had been stuck at 4–7 for 196 s and she had closed a 25/11 gap. She needed about 90 more seconds at her own last-minute pace.
- **M1 G3 (25/07) was garbage.**
  - A blue garbage single landed at (0,4) after her last pill.
  - Column 4 above its top virus held 5 AI garbage cells + 4 own.
  - She was slow in this game (35 left at 60 s) against the AI's fastest opening (30 viruses/min). The AI sent 13.6 cells/min.

## 4. The AI per game (D4)

| game | AI pills | silicon == faithful brain | misses by label | co-sim category of silicon's landing | previous-target / pills after a garbage window | silicon-only misses | copro final == python brain |
|---|---|---|---|---|---|---|---|
| M1 G1 | 212 | 170 (80.2%) | PREV-TARGET:9 EARLIER-PUB:7 TUCK:4 HYBRID:11 SHORT-LANDING:5 LATE-FLIP:6 | FINAL:157 HYBRID:21 AT-GATE:17 TUCK:4 OTHER-PUB:13 | 9 of 12 | 20 of 42 | 184/212 |
| M1 G2 | 217 | 178 (82.0%) | PREV-TARGET:8 HYBRID:10 SHORT-LANDING:3 EARLIER-PUB:16 LATE-FLIP:1 TUCK:1 | FINAL:174 HYBRID:21 OTHER-PUB:8 AT-GATE:13 TUCK:1 | 8 of 15 | 32 of 39 | 212/217 |
| M1 G3 | – | (co-sim / Mesen not run) |  |  |  |  |  |
| M1 G4 | 146 | 118 (80.8%) | PREV-TARGET:6 HYBRID:6 TUCK:1 EARLIER-PUB:12 LATE-FLIP:3 | FINAL:104 HYBRID:15 OTHER-PUB:11 TUCK:1 AT-GATE:15 | 6 of 12 | 20 of 28 | 128/146 |
| M1 G5 | – | (co-sim / Mesen not run) |  |  |  |  |  |
| M2 G1 | – | (co-sim / Mesen not run) |  |  |  |  |  |
| M2 G2 | – | (co-sim / Mesen not run) |  |  |  |  |  |
| M2 G3 | – | (co-sim / Mesen not run) |  |  |  |  |  |
| M2 G4 | – | (co-sim / Mesen not run) |  |  |  |  |  |

- **Labels** come from `ai_lulu_20261005.py`; the first match wins:
  1. TUCK
  2. PREV-TARGET: after a garbage window, silicon replayed the previous pill's target.
  3. CLAMP-SLAM
  4. LATE-FLIP
  5. SHORT-LANDING
  6. HYBRID: on none of the copro's publishes.
  7. COPRO!=BRAIN
  8. EARLIER-PUB: an earlier publish was executed and the copro final was never adopted.
  9. OTHER
- **Same-colour aliasing:** a YY/RR/BB capsule has two action indices per pose (a and a+8). The verbatim execfid census and
  `report.landings` compare raw indices, so they miss, for example, M1 G4 p61. Every comparison here is canonical.
- **"Silicon-only"** means the FAIR Mesen replay of the SAME cart does not land where silicon did. Each such miss is banked with its
  board, capsules, silicon trajectory, co-sim publish timeline and Mesen landings (`cases_ai_misses_lulu_20261005.jsonl`) for a
  dedicated lane.
- **Two checks that do NOT explain them:**
  - **The copro's seeded tie-break.** The silicon seed is (NAV_T|1)^$A4, while every replay uses seed 0. Only 27 of 218 misses (all
    9 games) fall within the 3-point jitter, and the best seed gains at most 3 pills per game (`seed_lulu_20261005.py`).
  - **A uniform answer delay on the FAIR cart:** +2 / +5 / +10 f reproduces 7 / 9 / 11 of M1 G4's 28 misses, and +10 breaks others.
- **Fidelity is the same in her wins and her losses:** silicon == faithful brain on 81.4% vs 81.8% of pills.
- **The AI's sends:** 2.4–5.2 volleys/min and 6.3–13.6 cells/min per game; pooled 4.21 volleys/min and 10.05 cells/min, against her
  2.95 and 6.66.
  - Its sends fall in her wins: 8.0 vs 11.1 cells/min, because it clears less.
- **AI stalls (10 or more pills at one count):**

  | game | stalls |
  |---|---|
  | M1 G1 | 7/6/5/4 viruses, 43/51/71/41 s |
  | M1 G2 | 10 viruses 71 s, then 7 for 199 s / 110 pills |
  | M1 G4 | 30/23/16, the last 59 s |
  | M2 G1 | 1 virus for 50 s |
  | M2 G2 | 29/21/11 |
  | M2 G3 | 38/16/13 (36 s) |
  | M1 G3, M1 G5, M2 G4 | none |

## 5. M1 G4: the AI's tap-out (D5)

M1 G4 ended lulu 03 / AI 16 at 221.6 s, after 146 AI pills. AI gate 145/145, 5 clear-pop repairs; 46 of 146 AI spawns were hidden
same-colour spawns.

**Timeline:**
- **The race:** level at 60 s (30/30). She led from 90 s (23 vs 28).
- **The stall:**
  - The AI's last virus clear was p96 at 159.5 s. It then played 49 pills / 59 s at 16 while she went 14→5, and →3 with her last pill.
  - A virus-clearing move existed on only 4 of the 49 stall pills, and the faithful brain would have taken none of them.
- **What was sealed:**
  - 5 viruses in col 0, capped by the AI's own p0 half + 4 of her garbage singles (G5/G13/G56/G73, rows 2–5).
  - 4 in col 6, under its own p9/p12/p91/p92 halves + 1 garbage cell.
  - 7 buried in rows 13–15.
- **The death was its own pill.** p146 locked at row 0, cols 2–3, on the col-3 stack that p144 had raised to 15. p143–p145 match
  the brain. Her last volley had landed 20 pills earlier.

**Fidelity:**
- Silicon == faithful brain on 118/146 (81%).
- The 28 misses:

  | miss type | count | pills |
  |---|---|---|
  | EARLIER-PUB | 12 | |
  | PREV-TARGET | 6 | p6, p19, p61, p92, p98, p125 |
  | HYBRID | 6 | |
  | LATE-FLIP | 3 | |
  | TUCK | 1 | |

- 20 of the 28 are silicon-only.

**Brain-only replays** (faithful brain, perfect execution, observed capsules + her observed garbage), from every pill p60–p145 and from
every 2nd pill p0–p58, 116 start points in all:
- **Top-outs: 0/116.** Silicon topped out ⇒ **the tap-out is execution.**
- **The race:**
  - 9 starts (p20–p36) CLEAR at p132 (208.7 s), while she still had 8. **That is an AI win.**
  - The other 107 are alive at p145 with 1–16 viruses (median about 13) against her 5.
  - From p100 onward, 11–16 every time: the stall had become structural.
- **Decisive pill p61:**
  - A YY capsule, right after her 2-cell volley landed at p60.
  - Silicon landed H col 2, which is p60's target (the LATEGUARD×PRESTART previous-target defect). The brain and the copro final
    say V col 5.
  - Brain-only from p60/p61 reaches 2 viruses at p145 (max height 3). With silicon's p61, it reaches 12.
  - The replays are chaotic (p68 → 8, p89 → 4), so treat this as provisional.

**FAIR vs FAIRPLUS, Mesen chained + her garbage via $0318/$0329:**

| cart | landing == copro final | hybrids |
|---|---|---|
| FAIRPLUS (5b3d8183) | 124/146 | 0 |
| FAIR (dbbb5007) | 116/146 | 5 |

- The FAIR replay reproduces p61's previous-target landing exactly (H col 2, rot 2).
- FAIRPLUS lands the final on p61 (V col 5) and on 5 of the 6 previous-target pills.
- In the stall, though, silicon's misses at p99, p100, p107, p113, p121, p123, p124, p127, p129, p130, p133 and p134 are
  silicon-only. FAIR and FAIRPLUS both land the final there, so FAIRPLUS does not touch them.

**Verdict:**
- The tap-out was EXECUTION: the p61 previous-target defect, then silicon-only misses in the stall stacking it to the top.
- The race was lost to STRUCTURE + GARBAGE: col 0 was sealed partly by her garbage, and the brain alone is stuck from about p100.
- **Would FAIRPLUS have changed it?** It fixes the decisive pill p61 and the other previous-target pills. With perfect execution after
  that, the AI would have been at about 2 viruses against her 5. But the silicon-only misses remain, so whether the AI wins stays open.

## 6. Why the AI won (D6)

| game | winner | 30 s | 60 s | 90 s | 120 s | 150 s | 180 s | 210 s | 240 s | AI longest stall | AI→her cells/min | her→AI cells/min | loser's finishing deficit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M1 G1 | AI | 41/35 | 33/24 | 29/17 | 25/11 | 24/7 | 20/7 | 13/6 | 11/5 | 70.9 s at 5 (43 pills) | 12.65 | 5.73 | her 6 left, ~90 s more at own last-60-s pace |
| M1 G2 | dr. lulu | 41/37 | 35/24 | 30/17 | 21/10 | 18/10 | 17/10 | 14/7 | 10/7 | 200.9 s at 7 (110 pills) | 10.7 | 5.11 | AI 7 left, no clear in its last 60 s |
| M1 G3 | AI | 42/30 | 35/18 | 29/12 |  |  |  |  |  | 11.4 s at 30 (6 pills) | 13.57 | 5.66 | her 25 left, ~107 s more at own last-60-s pace |
| M1 G4 | dr. lulu | 37/37 | 30/30 | 23/28 | 20/23 | 15/19 | 9/16 | 6/16 |  | 59.2 s at 16 (49 pills) | 6.83 | 7.6 | AI 16 left, ~960 s more at own last-60-s pace |
| M1 G5 | AI | 42/34 | 38/23 | 33/17 | 30/10 | 30/3 | 27/1 |  |  | 14.7 s at 1 (6 pills) | 10.27 | 5.91 | her 26 left, ~390 s more at own last-60-s pace |
| M2 G1 | AI | 39/37 | 37/25 | 33/16 | 32/10 | 30/5 | 21/3 | 16/1 | 14/1 | 52.5 s at 1 (28 pills) | 8.86 | 5.61 | her 14 left, ~210 s more at own last-60-s pace |
| M2 G2 | AI | 38/35 | 29/29 | 23/23 | 16/21 | 13/14 | 9/10 | 6/4 |  | 28.9 s at 21 (15 pills) | 10.69 | 8.67 | her 6 left, ~120 s more at own last-60-s pace |
| M2 G3 | dr. lulu | 39/39 | 31/29 | 25/22 | 12/16 | 5/13 | 4/13 |  |  | 36.4 s at 13 (22 pills) | 6.32 | 8.5 | AI 11 left, ~330 s more at own last-60-s pace |
| M2 G4 | AI | 36/34 | 32/23 | 24/17 | 19/9 | 16/5 | 14/2 |  |  | 19.7 s at 9 (8 pills) | 10.35 | 8.82 | her 14 left, ~210 s more at own last-60-s pace |

| factor | her wins (M1 G2, M1 G4, M2 G3) | mean | her losses (M1 G1, M1 G3, M1 G5, M2 G1, M2 G2, M2 G4) | mean |
|---|---|---|---|---|
| AI longest stall (s) | [200.9, 59.2, 36.4] | 98.83 | [70.9, 11.4, 14.7, 52.5, 28.9, 19.7] | 33.02 |
| AI lead at 60 s (viruses) | [11, 0, 2] | 4.33 | [9, 17, 15, 12, 0, 9] | 10.33 |
| AI lead at 120 s | [11, -3, -4] | 1.33 | [14, 20, 22, -5, 10] | 12.2 |
| her viruses/min, 0–60 s | [14.0, 18.0, 17.0] | 16.33 | [15.0, 13.0, 10.0, 11.0, 21.0, 18.0] | 14.67 |
| AI viruses/min, 0–60 s | [24.0, 18.0, 20.0] | 20.67 | [24.0, 30.0, 25.0, 24.0, 19.0, 26.0] | 24.67 |
| her viruses/min, whole game | [7.4, 12.18, 13.82] | 11.13 | [7.27, 12.97, 7.18, 7.89, 10.85, 10.96] | 9.52 |
| AI viruses/min, whole game | [6.32, 8.66, 10.65] | 8.54 | [7.62, 23.12, 15.66, 11.14, 12.4, 15.48] | 14.24 |
| AI garbage to her (cells/min) | [10.7, 6.83, 6.32] | 7.95 | [12.65, 13.57, 10.27, 8.86, 10.69, 10.35] | 11.06 |
| her garbage to AI | [5.11, 7.6, 8.5] | 7.07 | [5.73, 5.66, 5.91, 5.61, 8.67, 8.82] | 6.73 |
| AI silicon == brain (%) | [82.0, 80.8, 81.3] | 81.37 | [80.2, 80.6, 82.2, 83.1, 82.0, 82.5] | 81.77 |

**What separates her 3 wins from her 6 losses (n = 3 vs 6, PROVISIONAL):**
1. **The AI's endgame stall:** longest stall 99 s on average in her wins vs 33 s in her losses. All 3 wins contain an AI stall of
   36 s or more at 7–16 viruses.
2. **The AI's opening lead:** the AI was 4.3 viruses ahead at 60 s in her wins vs 10.3 in her losses, and 1.3 vs 12.2 at 120 s.
   - In her wins the AI's whole-game pace was 8.5/min, vs 14.2/min in her losses.
   - Her own pace barely moves: 11.1 vs 9.5/min whole game, 16.3 vs 14.7/min over the first 60 s.
3. **Garbage follows tempo:** the AI sent her 8.0 cells/min in her wins vs 11.1 in her losses. Her sends were the same (7.1 vs 6.7).
4. **Not execution:** silicon == brain was 81% in both.

**Anatomy of the AI's longest stall** (`stall_<game>_lulu_20261005.json`; unique cells above the remaining viruses at the stall start,
by provenance: P = the AI's own pill halves, G = her garbage):

| game | stall | viruses in edge cols 0/7 | sealing cells | pills with a single-move virus clear |
|---|---|---|---|---|
| M1 G1 | 5 viruses, 71 s / 43 pills | 3 of 5 | G 4, P 2 | 1 |
| M1 G2 | 7 viruses, 201 s / 110 pills | 6 of 7 (a col-0 virus stack) | G 4 (all on the col-1 virus) | 0 |
| M1 G4 | 16 viruses, 59 s / 49 pills | 7 of 16 | G 7, P 19 | 4 |
| M2 G1 | 1 virus, 53 s / 28 pills | 1 of 1 | G 2, P 1 | 1 |
| M2 G3 | 13 viruses, 36 s / 22 pills | 9 of 13 | G 4, P 21 | 6 |

- **The stuck viruses sit in the EDGE columns,** and her garbage is a real part of the seal: at the low counts it is most of what lies
  above them.
- A 2-cell ROM volley lands in columns {s, s+4} with s = 0–3, so 1 in 4 of them hits column 0 and 1 in 4 hits column 7.
- This is the same pattern as 10/04 M5 G2 (col 7 sealed by garbage).

**Per game:**
- **M1 G1 (06/04):**
  - The AI led 25/11 at 120 s, then stalled at 7→4 for 196 s.
  - She closed to 6 and topped out on her own pills.
  - This was a precarious board for the AI: the brain-only replay topped out from 17 of 43 start points. Silicon survived.
- **M1 G2 (her win):**
  - The AI led 21/10 at 120 s, then stalled at 7 for 201 s (110 pills, never a single-move clear).
  - BRAIN-level: brain-only replays from p26 onward stall at exactly 7.
- **M1 G3 (25/07):** the AI's fastest opening (30/min). She was slow, and it ended in a garbage plug at 106 s.
- **M1 G4 (her win):** section 5.
- **M1 G5 (26/00):** pure AI tempo, 10 at 120 s vs her 30.
- **M2 G1 (14/00):**
  - The AI was at 10 by 120 s, then stalled at 1 virus for 50 s.
  - She was too far behind, at 14.
- **M2 G2 (06/00), the closest race:**
  - She led at 120 s (16/21) and was level at 150–180 s (13/14, 9/10).
  - The AI then cleared its last 10 in about 52 s while she went 9→6 (3/min over her last minute).
  - Perfect brain execution would NOT have done better: brain-only replays topped out from 3 of 27 starts and were mostly left at 1
    virus when silicon cleared.
- **M2 G3 (her win):**
  - She raced 12→0 between 120 and 208 s while the AI stalled at 13 for 36 s.
  - Brain-only replays did not beat her from 25 of 27 starts: they topped out or were still stuck when she cleared.
- **M2 G4 (14/00):** AI tempo, 9 at 120 s vs her 19.

**Perfect-execution counterfactual (brain-only replays, all games, `replaysum_lulu_20261005.json`):**

| game | actual | start points | AI wins under perfect execution | AI loses | undecided (capsules run out) | AI viruses left when undecided |
|---|---|---|---|---|---|---|
| M1 G1 | AI (lulu topped out) | 43 | 26 | 17 | 0 | – |
| M1 G2 | lulu (cleared) | 44 | 5 | 39 | 0 | – |
| M1 G3 | AI (lulu topped out) | 16 | 16 | 0 | 0 | – |
| M1 G4 | lulu (AI topped out) | 116 | 9 | 0 | 107 | median 13, range 1–16 |
| M1 G5 | AI (cleared) | 22 | 17 | 0 | 5 | median 3, range 3–4 |
| M2 G1 | AI (cleared) | 30 | 13 | 2 | 15 | median 3, range 1–3 |
| M2 G2 | AI (cleared) | 27 | 5 | 3 | 19 | median 1, range 1–5 |
| M2 G3 | lulu (cleared) | 27 | 2 | 25 | 0 | – |
| M2 G4 | AI (cleared) | 20 | 3 | 0 | 17 | median 2, range 1–10 |

- **Her wins:** the brain with perfect execution would have beaten her from only 16 of 187 start points (M1 G2 5/44, M1 G4 9/116,
  M2 G3 2/27). From the rest it stalls (7 or 13 sealed viruses) or tops out.
- **The AI's wins:** perfect execution LOSES from 22 of 158 start points (M1 G1 17/43, M2 G1 2/30, M2 G2 3/27). Silicon held on there.
- **⇒ The outcome is far more sensitive to the brain's endgame structure (sealed virus columns, no build-toward-clear) than to
  execution.** M1 G4's tap-out is the exception.

## 7. FAIRPLUS counterfactual (D7)

| game | AI pills replayed | FAIR dbbb5007: landing == copro final | FAIR hybrids | FAIRPLUS 5b3d8183: == copro final | FAIRPLUS hybrids | silicon previous-target pills |
|---|---|---|---|---|---|---|
| M1 G1 | 212 | 173 (82%) | 8 | 182 (86%) | 0 | 9 → FAIR reproduces 8, FAIRPLUS lands final 8 |
| M1 G2 | 217 | 201 (93%) | 9 | 210 (97%) | 0 | 8 → FAIR reproduces 4, FAIRPLUS lands final 8 |
| M1 G3 | not run (trimmed) |  |  |  |  |  |
| M1 G4 | 146 | 116 (79%) | 5 | 124 (85%) | 0 | 6 → FAIR reproduces 4, FAIRPLUS lands final 5 |
| M1 G5 | not run (trimmed) |  |  |  |  |  |
| M2 G1 | not run (trimmed) |  |  |  |  |  |
| M2 G2 | not run (trimmed) |  |  |  |  |  |
| M2 G3 | not run (trimmed) |  |  |  |  |  |
| M2 G4 | not run (trimmed) |  |  |  |  |  |
| **total** | 575 | **490** (85%) | **22** | **516** (90%) | **0** | 23 → 16 / 21 |

## 8. Highlights (D8)

PRIVATE to the owner: never published or committed. In `~/projects/dr_mario_rl/tmp/lulu_20261005/clips/`, h264 crf 18 + AAC,
cropped to the NES picture (x 255–1666):

| clip | recording s | what |
|---|---|---|
| `m1g5_ai_clinches_match1_3-2_26-00.mp4` | 1282–1299 | **the first match win any bot has taken off dr. lulu**: the AI clears its last virus with her at 26 |
| `m2g4_ai_clinches_match2_3-1_14-00.mp4` | 2194–2211 | the AI clears out to take match 2, 3-1 |
| `m2g2_closest_race_ai_clears_06-00.mp4` | 1785–1803 | the closest race: level at 9/10 30 s earlier, the AI finishes with her at 6 |
| `m1g4_ai_tapout_03-16.mp4` | 1090–1107 | the AI's tap-out: stuck at 16, its own pill locks at row 0 while she clears to 3 |
| `m1g2_lulu_stage_clear_00-07.mp4` | 744–762 | her stage clear, 00/07, after the AI's 201-s stall at 7 |
| `m2g3_lulu_stage_clear_00-11.mp4` | 1998–2016 | her fastest game (13.8 viruses/min): clears with the AI stuck at 11 |

## Open / hand-offs

1. **SILICON-ONLY MISSES (new top question; coordinator: bank, don't investigate here).**
   - About half of silicon's misses are not reproduced by Mesen of the same cart fed the co-sim timeline (M1 G4: 20 of 28).
   - Not the tie-break seed, not a uniform answer delay.
   - All are banked in `cases_ai_misses_lulu_20261005.jsonl`. Next candidates: the board the cart actually uploads, upload timing vs
     the settle, and the stale-search state.
2. **The census aliasing fix** (same-colour capsules: a ≡ a+8) belongs in execfid `prevtarget.py` / `report.landings`. The 10/04 figures
   probably undercount.
3. **Brain:** the M1 G2 (7) and M2 G3 (13) stalls are sealed-column / build-toward-clear cases again (9/27 G1, 10/04 M5 G2). STEER9's
   "don't seal" arms failed, so a build-toward-clear term is the open idea.

## Files (`experiments/couch_forensics/`)

- **Code:**
  - `lulu_20261005.py` (track | hudtpl | results | analyze [game] | merge | fit)
  - `cases_lulu_20261005.py` (per-AI-pill cases with the faithful brain)
  - `ai_lulu_20261005.py` (fidelity labels, co-sim categories, previous-target census with same-colour aliasing, Mesen FAIR/FAIRPLUS)
  - `m1g4_lulu_20261005.py` (stall | replay | replay_early | report)
  - `replay_lulu_20261005.py` + `replaysum_lulu_20261005.py` (brain-only replays)
  - `stall_lulu_20261005.py`
  - `seed_lulu_20261005.py`
  - `why_lulu_20261005.py`
  - `tables_lulu_20261005.py`
  - `geom_lulu_20261005.json`, `hud_templates_lulu_20261005.json`
- **Banked cases:**
  - `cases_lulu_20261005_lulu_pills.jsonl`, `cases_lulu_20261005_ai_pills.jsonl` (both seats per pill: runs / sent / cascade)
  - `cases_lulu_20261005_volleys.jsonl` (every send with its matched received volley and ROM-column check, both directions)
  - `cases_ai_<game>_lulu_20261005.jsonl` (per AI pill: board, capsules, silicon vs faithful brain, category, trajectory, garbage)
  - `cases_ai_fidelity_lulu_20261005.jsonl` (labels + Mesen FAIR/FAIRPLUS per pill)
  - `cases_ai_misses_lulu_20261005.jsonl` (**every AI miss** with board, trajectory, publish timeline, Mesen FAIR/FAIRPLUS/delayed
    landings and the `silicon_only` flag)
  - `pubtrace_<game>_lulu_20261005.jsonl` (co-sim publish timelines, fw 1488e158, seed 0)
  - `replay_*_lulu_20261005.jsonl`, `cases_stall_*_lulu_20261005.jsonl`, `cases_seed_lulu_20261005.jsonl`
- **Summaries:**
  - `summary_lulu_20261005.json`, `ai_lulu_20261005.json`, `why_lulu_20261005.json`, `replaysum_lulu_20261005.json`
  - `stall_*_lulu_20261005.json`, `seed_lulu_20261005.json`
  - **`lulu_fit_202610b.json`**
- **Not committed:**
  - Per-frame reads, raw tracks, Mesen logs and frames: `~/projects/dr_mario_rl/tmp/lulu_20261005/fx/`.
  - Clips (private): `~/projects/dr_mario_rl/tmp/lulu_20261005/clips/`.
