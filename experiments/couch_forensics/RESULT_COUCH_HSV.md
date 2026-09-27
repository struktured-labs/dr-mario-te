# RESULT (2026-09-27, Claude): first couch match on CHAIN540+REACH+TAP+HSV (rbf 6b73907c + cart 198a95e3), AI 3-0

- Video: `20260927_081955_struktured_v6c_part2.mkv`. AI = P2.
- Windows: G1 50.1–280.0 s, G2 320.9–502.3 s, G3 531.2–708.8 s + 913–1107.2 s. G3 was paused on the STUDY
  screen 708.8–913 s; that time is excluded.
- **L11 verified:** the HUD reads LEVEL 11/11 MED/MED with 48 viruses at each game's first spawn, and reader ==
  HUD 3/3.
- Everything ran at nice 19 / single thread (OBS was recording).
- 369 placements.

## 1. Hardware validation of HSV: the silicon brain follows the HSV decider
Two masked brains were compared on every placement:
- **(a) HSV:** `cascade_leaf5b_x.Leaf5ReachDecider(tap=2, w5=(0,0,0,512))`
- **(b) no-HSV:** the same with w5 = 0, which is identical to the existing masked TAP decider, 369/369.

The two disagree on only **14/369 placements (3.8%)**. HSV binds only while high spawn-column viruses remain.

| silicon | placements | match (b) no-HSV | match (a) HSV | **disagreement subset: silicon == HSV / == no-HSV / neither** |
|---|---|---|---|---|
| **9/27 HSV build** | 369 | 276 (75%) | 282 (76%) | **9 / 3 / 2** (n=14) |
| 9/27 G1 / G2 / G3 | 96 / 88 / 185 | 77% / 80% / 71% | 80% / 84% / 71% | 3/0/1 · 5/1/0 · 1/2/1 |
| **9/26 TAP build, no HSV (control)** | 489 | 400 (82%) | 392 (80%) | **4 / 12 / 2** (n=18) |

**A clean crossover:**
- On HSV silicon, 9 of the 12 decided disagreements follow HSV.
- On yesterday's non-HSV TAP silicon, 12 of 16 follow no-HSV.
- Fisher exact **p = 0.02** two-sided (0.012 one-sided).
- **HSV is live on silicon.** The residual 3/12 is the usual ~20–25% silicon ≠ sim noise.

## 2. Placement classes (brain = the HSV decider)
| game | MATCH | late flip | short landing | tuck | other |
|---|---|---|---|---|---|
| G1 | 77 | 6 | 4 | 0 | 9 |
| G2 | 74 | 3 | 2 | 0 | 9 |
| G3 | 131 | 8 | 9 | 11 | 26 |

PROPH fired only in G3 (33 pills).

**G3 dig-out (685–709 s).**
- Cols 3/4 stood at height 15 (first occupied row 1 in both) from k79 to k89, about 12 s. PROPH fired on every
  pill (LEFT pulses at f4/6).
- HSV and no-HSV chose identically throughout. One high virus remained, and the brain aimed at cols 0–2.
- **Silicon dug out with TUCKS:** k79, 80, 82, 83, 84 slid under the spawn-lane overhang into the cavity below,
  landing in cols 2 and 4 at rows 10–14. That is outside the sim's straight-drop action space (the cart's DRTUCK).
- The other pills: 2 MATCH (k87, k89), 3 same-cell 180° colour flips (k81, 86, 88), and 1 different column (k85).
- By k90 the lane had collapsed from 15/15 to 10/7, and the game was won.
- No placement in the window was a clamp short-landing.

**New observation: 180° colour flips sit on PROPH pills.** Right cells, halves reversed:
- 9/27: 3/33 PROPH pills vs 2/336 non-PROPH.
- 9/26: 1/8 PROPH vs 0/481.
- Pooled: **4/41 (~10%) vs 2/817 (0.2%).**
- Consistent with the shared tap scheduler dropping one rotation when PROPH pulses precede the answer. Small n;
  worth a driver-side check (interface-compliance sim on ledge spawns).

## 3. Contrast metrics vs yesterday (`cases_tap_contrast.jsonl`)
"Hi-virus c3-5" = viruses in cols 3–5 at rows ≤ 8. "Match" here is vs the no-HSV masked brain.

| game | outcome | hi-virus c3-5 start → clear | hi-virus·s | lane > 10 (frac) | garbage /min | PROPH |
|---|---|---|---|---|---|---|
| AM-G1 (9/26) | AI tap-out | 7 → 2 by 21 s, 2 left to death | 245 | 0.91 | 12.5 | 8 |
| AM-G2 (9/26) | AI tap-out | 7 → 1 by 52 s, 1 left 75 s | 286 | 0.23 | 12.2 | 0 |
| AM-G3 / PM-G1..3 (9/26) | healthy | 2–5 → 0 in 13–27 s | 25–58 | 0–0.05 | 6.5–10.1 | 0 |
| **HSV-G1** | AI clear | 5 → 1 by 12 s, **last one for the whole game (224 s)** | 250 | 0.17 | **13.6** | 0 |
| **HSV-G2** | AI clear | **8 (most of any game) → 0 by 33 s** | 101 | 0.05 | 10.9 | 0 |
| **HSV-G3** | AI clear | 4 → 1 by 12 s, **last one for the whole game (387 s)** | 213 | **0.53** | 11.1 | 33 |

Reading:
- **HSV clears the first high spawn-column viruses fast** (all but one within 12–18 s in every game, including an
  8-virus start).
- **In 2 of 3 games, the LAST high virus stayed for the whole game.**
- G3 still reached a 12-s spawn-lane crisis that only the tucks solved.
- Garbage was at the high end (10.9–13.6/min, like yesterday's deaths), and the build won all three.
- n = 3 games: the HSV effect on OUTCOMES is not measurable yet. On DECISIONS it is confirmed (section 1).

## Files
- `cases_hsv_20260927.jsonl`: 369 classified placements with both brains, the mask and timing.
- `cases_hsv_control_20260926.jsonl`: yesterday's 489 TAP placements with the HSV decider added.
- `classify_tap.py`.
- `analyze_tap.py`: `HSV=W` computes the leaf5b HSV choice alongside the masked one.
- `contrast_tap.py`: extended with the HSV games, and caps inter-spawn intervals at 15 s so pauses don't count.

## Addendum: match 2 on the HSV build (same recording, after 1107 s), AI 3-0, last game 19-0
**Windows:**
- G1: 1264.7–1491.7 s.
- G2: 1545.0–3227.6 s. It paused 1660.9–1721 s (61 s), then 1736.0–3212 s (the clip). Pause time is excluded:
  inter-spawn intervals are capped at 15 s.
- G3: 3229.6–3421.9 s.

**L11 verified** by the HUD (48 viruses, LEVEL 11/11 MED/MED) on all three.

**HSV again follows the silicon.** Disagreement subset: silicon == HSV **11**, == no-HSV **3** (n = 16). Pooled
over both matches: **20 : 6**, against the non-HSV control's 4 : 12. Fisher p = 0.0014 (two-sided).

| game | n | MATCH | late flip | short | tuck | other | PROPH | hi-virus c3-5 start → clear | hi-virus·s | lane > 10 | garbage /min |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M2-G1 | 99 | 82 | 0 | 3 | 0 | 14 | 0 | 5 → 1 by 15 s → 0 at 24 s | 56 | 0.01 | 8.4 |
| M2-G2 | 70 | 60 | 0 | 2 | 2 | 6 | 0 | 5 → 1 by 17 s → 0 at ~118 s of play | 170 | 0.26 | 9.3 |
| M2-G3 (19-0) | 85 | 76 | 1 | 0 | 0 | 8 | 0 | 5 → 1 by 9 s → 0 at 48 s | 71 | 0.07 | 10.1 |
| *M1-G3 (near tap-out)* | 185 | 131 | 8 | 9 | 11 | 26 | 33 | 4 → 1 by 12 s → 0 at ~181 s of play | 213 | 0.53 | 11.1 |

### Why match-1 G3 nearly tapped out and match 2 did not (`linger_g3.py` → `linger_hsv_g3.jsonl`, `linger_hsv2_g2.jsonl`)
The last high virus in M1-G3 was a **yellow at row 8 of column 3** (a spawn column). It was sealed in by a
sequence, not missed by the brain.
1. **k9 (547 s), silicon SHORT-LANDING.** The brain aimed H YR at cols 1–2 / row 5. The pill landed one column
   short, at cols 2–3, colours reversed. Its yellow half bridged column 3 at row 5, leaving an empty gap above the
   virus (rows 6–7) under an overhang.
2. **Owner garbage** stacked on it: a yellow at row 4 (k41), then a **red cap at row 2** plus a yellow at row 3 (k56).
3. **k63 (653 s), silicon TUCK.** The sim brain chose a vertical BB drop into column 4. Silicon slid a horizontal BB
   under the overhang, which put a **blue into the row-6 gap**. After that, column 3 read (top→virus)
   `r y y y b y Y`.
4. **On all 88 pills while it lingered, no candidate at all could clear it** (0/88 immediate clears, mask or no
   mask). The column grew into the 15-tall spawn-lane tower (the 685–698 s crisis). Tucks dug the top out, the blue
   cleared after the STUDY pause, and the virus cleared at about 918 s raw.

Match 2 started with the same load (5 high spawn-col viruses every game), and none got sealed.
- In M2-G2 the last one (a **blue at row 7 of column 3**) sat under a red for about 85 s. The red was then cleared
  and the brain stacked two blues on it.
- The brain passed on the first clearing move (k59: 6 were available, it chose V2 BB) and cleared it on the next
  chance (k64).

**Answer to the owner:**
- Match-1 G3 wasn't the brain ignoring that last virus. The virus got walled in early by two execution slips on
  the cart plus his garbage:
  - a pill landed one column short and left a hole over it;
  - his garbage capped the column with red;
  - a tuck later slid a wrong-colour (blue) half into the hole.
- After that no move could clear it for 88 pills (every candidate was checked), so that column grew into the tower
  that nearly topped it out, until the tucks dug it out.
- Match 2 started with exactly the same number of high centre viruses but never got one sealed. They were gone in
  24–48 s, and the one stubborn blue was cleared as soon as a clearing move existed.
- Garbage was similar (about 8–10 vs 11 cells/min), and his pace wasn't the difference.
- So it was mostly sequence luck plus two execution slips.
- The fix it points to is on the execution side: don't let a short landing or a tuck bridge or fill a hole
  directly above a high spawn-column virus with a non-matching colour. The sim brain has no tuck moves, so it can't
  see that risk yet.

- **Cases:** `cases_hsv2_20260927.jsonl` (254 classified placements).
- **Lingering-virus traces:** `linger_hsv_g3.jsonl` and `linger_hsv2_g2.jsonl`.
- **Contrast:** `cases_tap_contrast.jsonl`, extended with M2-G1..3.
