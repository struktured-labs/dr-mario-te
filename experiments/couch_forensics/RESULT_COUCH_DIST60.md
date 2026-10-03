# RESULT (2026-10-03, Claude): couch ANTIBODY_DIST (DIST60) endgames. Was the AI "comboing instead of clearing"?

- **Match:** the owner vs ANTIBODY_DIST (rbf 318607aa + cart c960dd49), L11 MED, AI = P2. The AI won G3 and G4 by full
  clear.
- **Video:** `/mnt/data/Videos/2026-10-03 08-26-24.mkv` (rivalmage, OBS 1080p60, NES box x 254–1665).
- **Owner, after G4:** *"the bot wasted lots of cycles on the last virus (not even because it was hard to reach, it was
  comboing more than deliberately clearing)"*.
- **Resources:** everything ran at nice 19 with single-thread ffmpeg, decoding only the game windows.

## Capture, tracker fix, gates
- **Geometry** (`geom_dist60_20261003.json`):
  - Seeded from single pill-half bounding boxes, then grid-searched to minimise link violations: CW 44.4, CH 38.6,
    origin (1129.5, 341.2), preview y 219.2.
  - 8 violations over 461 cells on 14 frames, nearly all on the falling capsule.
- **Windows:** G3 609–786 s (pills 0–85). G4 842–947 s + 1937–2090 s (pills 0–132).
  - G4 sat on the STUDY pause from 947 s to 1937 s.
  - The two halves join exactly. The board diff across the pause is the owner's 4-cell volley (Y/R/B/B into cols
    0/2/4/6), as logged.
- **NEW, hidden spawns (`track_hidden_dist60_20261003.py`).**
  - **The bug:** `track.py` finds spawns only where the preview changes, so it MISSES every spawn whose following
    capsule has the same colours.
  - **The fix:** a capsule that appears at row 0 cols 3–4 in the preview's colours, inside one preview run, is a
    spawn.
  - **Mechanics gate, old → new tracker:**

    | game | explained (old) | explained (new) |
    |---|---|---|
    | G3 | 73/75 | **84/84** |
    | G4 | 89/97 | **128/129** |

  - **Hidden spawns found:** G3 9 of 86 placements; G4 32 of 133.
- **⚠ Side finding (affects prior work).** `mech_check` "explains" a merged hidden pill as a garbage volley.
  - **How often:** on the re-scanned prior endgames, 8 of 23 "garbage-explained" steps were hidden pills (dr. lulu
    G1: 8 of 22). Here, 12 of 23.
  - **What it touches:**
    - `owner_sends.py` / `lulu_profile.py` count those as volleys, so the OWNER-2026-09 and lulu send fits (volleys/min,
      the 2-cell share) are probably INFLATED.
    - All old pill counts are low by about 10–25%.
  - **Not re-derived here.** The owner and lulu send fits were not recomputed.

## 1. What the AI did from 4 viruses to 0
`cases_dist60_20261003.jsonl` (219 placements, both games). Per-virus phases:

| game | viruses left | s | pills | clears: virus / pill-only | cascades → garbage sent | garbage recv | target D before each pill |
|---|---|---|---|---|---|---|---|
| G3 | 4 | 14.9 | 7 | 1 / 2 | 1 → 2 cells | 0 | 1 1 1 1 1 1 1 |
| G3 | 3 | 6.0 | 3 | 1 / 0 | 1 → 2 | 0 | 1 1 1 |
| G3 | 2 | 12.5 | 7 | 1 / 1 | 2 → 4 | 0 | 3 3 3 3 2 2 1 |
| G3 | **1** | **2.4** | **1** | 1 / 0 | 0 | 0 | 3 |
| **G3 total** | | **35.7** | **18** | 4 / 3 | 4 → 8 | 0 | |
| G4 | 4 | 5.0 | 2 | 1 / 0 | 1 → 2 | 0 | 1 1 |
| G4 | 3 | 20.5 | 8 | 1 / 3 | 1 → 2 | 1 vol (2) | 16 3 3 2 2 1 1 1 |
| G4 | 2 | 3.6 | 2 | 1 / 0 | 0 | 0 | 2 1 |
| G4 | **1** | **44.0** | **21** | 1 / **7** (49 cells) | **5 → 10** | 1 vol (2) | 3×11, then 16×8, then 1 1 |
| **G4 total** | | **73.1** | **33** | 4 / 10 | 7 → 14 | 2 vol (4) | |

**Owner's claim, G4's last virus: confirmed in what he saw, refuted as a choice.**

*What he saw is accurate:* 21 pills and 44 s on one virus, with 7 pill-only clears and 5 cascades sending 10 garbage
cells.

*But on 19 of those 21 pills, no root move could bring the target closer to clearing:*
- **The target:** a yellow virus at (14,0). The cell below it was empty and (14,1) held a blue, so the only route was
  vertical: 3 yellow halves stacked in column 0.
- **p112–122, 11 pills, colour wait.** At every decision the only capsule colour that could reduce D was **YY**
  (`twoply_dist60_20261003.py`).
  - No (cur, nxt) pair offered even a 2-pill plan.
  - The 12 capsules seen were RY BB BB RB BB RB BY BY RB RY BB BB: no YY. With uniform capsules that is about
    (8/9)^11 = 27% likely.
- **p122, the seal.** The owner's 2-cell volley put a RED on top of the virus at (13,0), so D = ∞.
  - p123–124: no capsule colour could help.
  - p125–128: only a red-carrying capsule could, and four YB arrived (≈ 4%).
- **p129–130, the dig.** The search found the 2-pill dig and silicon executed it.
  - p129: YY on top of the red.
  - p130: BR completes a red row 13, so the yellows drop onto the virus (D = 1).
- **p131–132, the finish.** p131 had no yellow; p132 finished.
- **Did it ever pass up a D-reducing move on the last virus?** 0 times. It took both of the 2 that existed.
- **Silicon == the DIST60 sim** on 19/21 of these pills.
- **Reading:** the cascades were what it did with capsules that could not help, and they were free: 10 cells sent.

**Where the hypothesis DOES hold: the 4 → 2-virus phases (finishing deferred).**

*G3, the red virus at (11,2):*
- A FINISHING move existed on 6 pills (p68, 69, 70, 73, 75, 77). It was cleared on the 6th: 9 pills / 18 s after
  the first chance.
- p73 was a silicon landing miss: the sim chose the finish.
- p70 cashed a cascade instead (sent 2).

*G4, p107:* a finish was declined for a cascade (sent 2) and taken 2 pills / 8 s later.

**In the sim brain, over the 10/03 positions:**
- At ≤ 4 viruses, a finishing root move existed on 14 decisions. DIST60 took it on 9 and **declined it on 5**.
- A D-reducing root move existed on 23 decisions. DIST60 took it on 15.

## 2. Why: replay through the sim brain, with term decomposition
**Agreement.** Silicon landing == the DIST60 sim (`Leaf6Decider` dist_target60, reach mask at the true pill index):

| scope | silicon == DIST60 | silicon == ANTIBODY (mode off) |
|---|---|---|
| all placements | **194/218 (89%)** | 188/218 (86%) |
| ≤ 4 viruses | **44/51 (86%)** | 38/51 (75%) |

- **The crossover confirms the DIST build on silicon.** Where DIST60 ≠ ANTIBODY (8/51 endgame decisions), silicon
  followed DIST **6 : 0**.
- **On the prior ANTIBODY couch games it goes the other way:** 4 : 71 (115 decisions).

**Does DIST change anything here?** Yes, 8/51 decisions:
- 4 finish or reduce D where ANTIBODY would not;
- 3 keep column 0 clean on G4's last virus (p112, p113, p118), where **ANTIBODY would have buried it** (D → ∞);
- 1 is neutral.

**Decomposition** (`decomp_dist60_20261003.py`):
- **Method.** A mechanical copy of the d3 search returns every root action's exact value, split into PV components.
  - Selfcheck: argmax 199/199 == `Leaf6Decider.choose` (DIST60 and off); max |Σ − val| = 0.75.
  - **Root value = imm1 + leaf1/2 + best2/2.** Ply-2 and ply-3 terms enter at half weight.
- **The 8 decisions where a D-reducing move existed and DIST60 chose otherwise** (chosen − best D-reducing, mean):
  - for the chosen move: **CHAIN +219**, LEAF +63, EXHANG +51, STRAND +15, CELLS +8;
  - for the D-reducing move: VIR −98, **DIST −54**.
- **The declined FINISHING moves** (`procrast_dist60_20261003.py`):

  | set | n | for the chosen move | for the finish | largest term |
  |---|---|---|---|---|
  | 10/03 | 5 | **CHAIN +256, EXHANG +96**, LEAF +77 | VIR −153, DIST −42 | CHAIN 3, EXHANG 2 |
  | prior ANTIBODY / TAP couch | 27 | CHAIN +120, EXHANG +93, LEAF +28 (median LEAF +102) | VIR −102, DIST −50 | LEAF 10, CHAIN 7, EXHANG 7, WIN 3 |

  The 3 WIN cases are legitimate: the PV clears the board.
- **The mechanism, measured:**
  - **Finishing now versus finishing next pill differs by only ~120.** That is VIR 180 vs 90 at half weight, plus
    DIST's 1 → 0 at half weight (≈ 30).
  - **Two terms beat that routinely:**
    1. a planned cascade: CHAIN540, +270 per step at half weight;
    2. the root EXCAV term: 24·min(run,3)². That is **+96 for leaving a same-colour 2-stack on the virus**, which is
       exactly the D = 1 vertical finish. EXCAV pays for NOT finishing.
  - **−60·D is too small to matter there:** |ΔDIST| ≈ 42–54.
  - **The LEAF part is readiness credit that a finish destroys** (`leafterms_dist60_20261003.py`).
    - Root-child base-leaf terms, chosen − finishing, all 32 declined finishes (mean): READINESS SETUP +33,
      MATCHED +42, RDY +73, VRDY +64. Each favours not finishing in 84–94% of cases.
    - Shape terms partly offset them: HOLES −31, POLL −17.
    - **Reading:** the leaf pays for a virus being lined up. Clearing that virus deletes the credit. A move that
      keeps the line-up and finishes at ply 2 collects both: the credit at leaf1 and VIR at half weight.
    - EXCAV is the same idea at the root.
    - **So "comboing instead of clearing" has three parts:** readiness credit (LEAF + EXCAV) plus CHAIN540, against a
      VIR + DIST finishing reward that the half-weight lookahead discounts.
- **Offline fix check on the same banked positions** (`variants_dist60_20261003.py`), finishing-move take rate:

  | variant | 10/03 | prior |
  |---|---|---|
  | DIST60 | 9/14 | 22/49 |
  | chain0 @ ≤ 4 | 9/14 | 22/49 |
  | exh0 + chain0 @ ≤ 4 | 13/14 | 34/49 |
  | W180 + exh0 + chain0 | 13/14 | 40/49 |

  - Gating the chain alone does not move finishing. It does raise the D-reducing rate (171 vs 148 of 209).
- **What the hypothesis gets right and wrong:** chain/combo rewards outbid −60·D on **finishing deferrals in the
  4 → 2 phases** (together with EXCAV and LEAF). They did **not** cause the G4 last-virus time.

## 3. Context: ANTIBODY's couch endgames (re-scanned with the hidden-spawn tracker)
`cases_prior_endgame_dist60_20261003.jsonl`. Every game is n = 1, so the whole table is PROVISIONAL.

| game | build | 4 → 0 s / pills | last virus s / pills | last 2 s / pills | no D-reducing move (sealed / colour) | finish available, not taken | cascades | volleys sent (cells) | garbage recv |
|---|---|---|---|---|---|---|---|---|---|
| **10/03 G3** | DIST | **35.7 / 18** | 2.4 / 1 | 14.8 / 8 | 5 (0/5) | 5 of 9 | 4 | 4 (8) | 0 |
| **10/03 G4** | DIST | **73.1 / 33** | **44.0 / 21** | 47.6 / 23 | 23 (7/16) | 1 of 5 | 7 | 7 (14) | 2 (4) |
| 9/27 M1G1 | ANTIBODY | 73.9 / 33 | 2.4 / 1 | 43.6 / 18 | 13 (8/5) | 3 of 5 | 6 | 6 (13) | 2 (4) |
| 9/27 M1G3 | ANTIBODY | 78.1 / 40 | — (2 → 0 in one) | 7.1 / 3 | 28 (20/8) | 8 of 11 | 7 | 9 (20) | 2 (5) |
| 9/27 M2G1 | ANTIBODY | 61.1 / 29 | 9.6 / 6 | 59.2 / 28 | 18 (2/16) | 4 of 6 | 4 | 4 (8) | 3 (8) |
| 9/27 M2G3 | ANTIBODY | 28.8 / 11 | 4.5 / 1 | 7.4 / 2 | 4 (0/4) | 6 of 7 | 1 | 1 (2) | 1 (2) |
| 9/27 dr. lulu G1 | ANTIBODY | 317.8 / 182 (never finished) | 48.9 / 31+ | 97.5 / 56+ | 64 (63/1) | 1 of 4 | 22 | 22 (45) | 14 (28) |
| 9/26 TAP t26b G1 | pre-HSV | 61.8 / 28 | — | 25.9 / 12 | 8 (1/7) | 1 of 3 | 3 | 3 (6) | 3 (6) |
| 9/26 TAP m2 G1 | pre-HSV | 44.9 / 17 | 2.2 / 1 | 33.4 / 11 | 8 (0/8) | 3 of 6 | 1 | 1 (2) | 1 (2) |
| 9/26 TAP m2 G3 | pre-HSV | 51.8 / 29 | 9.3 / 5 | 14.9 / 9 | 17 (1/16) | 4 of 7 | 3 | 3 (6) | 2 (5) |

- **DIST's two endgames are not slower than ANTIBODY's.**
  - 4 → 0: DIST mean 54 s / 26 pills vs ANTIBODY's owner games 60 s / 28 pills (n = 2 vs 4).
  - G4's last virus is the longest single-virus finish here, but ANTIBODY had equally long 2-virus phases
    (M2G1 59 s / 28; M1G1 44 s / 18).
- **The endgame "comboing" is ANTIBODY-family behaviour, not new with DIST.** Cascades and sends during the endgame
  run at the same rate (M1G3: 7 cascades / 9 volleys in 40 pills; G4: 7 / 7 in 33).
- **Silicon declined available finishes:** DIST 6 of 14 (43%) vs ANTIBODY 21 of 29 (72%). PROVISIONAL, n < 10 games.
- **dr. lulu G1's col-2 stall, re-counted:** 201.6 s / **117 pills** at 4 viruses (was ~99–102 with the old
  tracker), sealed (D = ∞) on 56. It is the sealed-target archetype. DIST's G4 seal lasted 8 pills.

## 4. Fix screen (STEER6e): both arms FAIL; the combos pay for themselves in the sim
- **Setup:** `../cvx/PREREG_STEER6e.md` (`1625e41e`), `../cvx/RESULT_STEER6e.md`.
  - 600 paired seeds, gate (b) + race lam 6.
  - The identity arm reproduces the banked STEER6 rows 1200/1200.
- **s6e_chain0** (CHAIN off at ≤ 4 viruses):
  - endgames faster: E1 −4.12 [−7.25, −1.06] pills, ≈ −24 sim-s;
  - endgame stall-pills −6.3 / game;
  - but race −3.00 [−5.50, −0.50] (7.5 fewer tiles sent per game) and tap-out +3.00 [+0.33, +5.67] (churn 25 / 43).
- **s6e_fin** (CHAIN + EXCAV/HANG off): finishes 87% of available finishes (vs 56%), but E1 is −0.59 (null) and race
  is −2.50.
- **Post-hoc:** with no damage per sent tile (δ = 0), both arms win +3.0 pp of races. ⇒ The trade is **tempo vs
  garbage damage**.
  - δ 2.65 is fitted (tape n = 181, CI [0.95, 4.13]). At the CI's low end chain0's race result is null
    (−1.8 [−4.5, +0.8]).
  - The tap-out failure (+3.0) does not depend on δ, so **no δ flips the verdict**.

## Files
**Cases (banked):**
- `cases_dist60_20261003.jsonl`: 219 placements with the board, pill index, silicon landing, mechanics (cells,
  viruses, cascade steps, runs, garbage sent), garbage received, DIST target / D before and after, D-reducing and
  finishing counts, DIST60 and ANTIBODY choices, and the PV term split of the chosen vs the best D-reducing move.
- `cases_prior_endgame_dist60_20261003.jsonl`: 400 prior endgame placements, same schema.
- `rawh_dist60_20261003_{G3,G4a,G4b}.jsonl`, `rawh_prior_dist60_20261003_*.jsonl`: tracked per-pill boards.
- `prior_spec_dist60_20261003.json`, `geom_dist60_20261003.json`.

**Scripts:** `track_hidden_` (tracker fix), `endgame_` (cases), `decomp_` (search decomposition + selfcheck),
`summary_`, `compare_`, `procrast_`, `leafterms_`, `twoply_`, `variants_` — all suffixed `dist60_20261003.py`.

**Reproduce:** `python endgame_dist60_20261003.py . OUT.jsonl` is byte-identical to the banked cases, and so is
`--prior prior_spec_dist60_20261003.json OUT`.
