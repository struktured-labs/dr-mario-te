# RESULT (2026-09-26, Claude, fast pass): CHAIN540+REACH+TAP couch build (rbf 77b521b2 + cart 198a95e3), two tap-outs

The owner played two couch games this morning. The AI tapped out in both while far ahead: G1 AI 16 vs owner 32,
G2 AI 7 vs owner 29.
- Video: `20260926_074256_struktured_v6c_part2.mkv` (still recording). G1 runs 8.9–103.2 s, G2 143.5–276.5 s.
  AI = P2.
- The decode ran at `nice 19` with single-threaded ffmpeg and numba, over 0–280 s only.
- 105 placements were analysed (G1 46, G2 59).

## Verdict: neither (a) steering nor (b) mask. The towers are the brain's own play plus garbage on high
## viruses (the stall-with-tower archetype again); one fatal pill in G2 is a rotation/gravity race (c).
- **(a) Steering works as designed.**
  - Lateral taps land at exactly 1 column / 2 frames: **77 of 94 lateral gaps = 2 f**.
  - The first answer move is at median **f18**, the designed T_LAT = 19 with the ~1 f preview offset.
  - PROPH pulses at f3–4 (8/8).
  - Silicon lands exactly where the masked brain chose on **87/105** placements (G1 37/46, G2 50/59). Before
    the fatal pill, no landing fell outside the mask.
- **(b) The mask is NOT over-restricting.**
  - Through the build-up it allowed 30 of 32 candidates, and masked == unmasked.
  - It removed the unmasked brain's choice only **6 times, all in each game's final pills**: G1 k41–45, where the
    col-4 needle plus the pill resting across its top physically block the path right; and G2 k60–61.
  - Once it SAVED the game: at G1 k42 the unmasked brain wanted H3 at row 0 (the spawn cells, suicide). The mask
    sent it to V1, and silicon followed.
- **Who built the towers:**
  - **G1:** col 4 = three VIRUSES hanging at rows 7–9 (never cleared, empty cells under them) + an early brain
    pill (k0/k2/k4 are the only pills ever placed in col 4, all MATCH) + garbage (col 4 took the most garbage of
    any column: 5 of 19 cells) + one pill resting on top. The rest of the bottle was low (cols 5–7 at 1–2 rows).
  - **G2:** the col 5–6 tower was built by brain placements (k8, 13–16, 23, 40, all MATCH the masked brain). Col 6
    ended as five unlinked singles on a row-7 virus.
- **(c) The one silicon ≠ brain miss that killed:** G2 k61, thr 13. The masked brain chose V4@7: rotate, one step
  right, drop into the only open column. The pill instead shifted right while still horizontal and locked at row 0
  on the col-5 ledge (first occupied row 1), covering the spawn cell (0,4). Rotation and lateral move register on
  the same frame, f20, and the gravity tick comes at f21 (G0 8 + thr 13). The mask called V4 reachable, silicon
  missed by about a frame: a 1–2-frame margin in the mask's timing model (T_LAT / G0 or the rotation slot) is
  worth checking. One case.
- **PROPH (tap mode) fired 8 times, all in G1's final phase** (col-4 needle, first occupied row = 2). It pulsed
  LEFT, consistent with the right side being blocked anyway.

## Gates
- **Geometry:** fit_geometry (1131.25, 340.50), within 0.3 px of the prior captures.
- **GATE 1:** HUD virus counter **13/13** frames across both games.
- **Masked-decider identity:** all-ones mask == unmasked **105/105**.
- **GATE 2 (decider plumbing):** 428/428 (unchanged).
- Colours are not separately eyeballed on this capture. The 87/105 exact pose+colour matches with the sim imply
  the reads are right.

## For the build decision
- The deaths come from **board shape the brain builds** (tall columns on high, uncleared viruses, garbage on top),
  the same archetype as the CHAIN540 9/25 G2 death. They do **not** come from the new tap steering or the reach
  mask. The mask helped once.
- Nothing here says REACH+TAP is worse than CHAIN540 by mechanism. Counts are too small to compare builds: this
  build 2/2 tap-outs vs CHAIN540 1/7 recorded, Fisher p ≈ 0.08.
- The one new-build-specific risk seen is the rotation/gravity race at G2 k61 (n=1).

## Files
- `analyze_tap.py`: masked vs unmasked brain vs silicon, timing. Needs `GAMES="t0:t1,..."`.
- `cases_tap_20260926.jsonl`: the 105 banked cases (board, pills, both brains, silicon, mask, timing).
- `scan_frames.py` / `fit_geometry.py`: now `ffmpeg -threads 1`.

## Addendum: G3 (AI won) + an abandoned G4, same recording (fast pass, nice 19 / single-thread)
- **Windows:**
  - G3: 307.2–564.0 s. Ends **AI 00 vs owner 20**; STAGE CLEAR appears on P2 at 564.3 s.
  - G4: 599.8–707.3 s, **abandoned mid-game** at owner 24 / AI 21.
  - **Dr. Mario content ends at ≈707.3 s.** The frame is black from 708 s, then a static non-Dr. Mario screen
    through ≥820 s (the rivalmage core switch). Nothing after 707 s is analysed.
- **Build = TAP (AA_DRMARIO_TAP.mgl behaviour), not the DAS fallback.** Lateral-gap histograms:
  - G3: `1:10  2:88  3:1  4:3  5:5  6:4  7:2  8:1  11:2  12:2  13:1  17:1  18:1  20:1  22:1  26:1  44:1`, so 88 of
    125 gaps are 2 frames.
  - G4: `1:1  2:14  4:2  6:3`.
  - The DAS signature (first press, then 16 f, then 6 f) is absent: there is no 16-f cluster. The 9/25 DAS
    CHAIN540 games showed 6 f ×10 and 16 f ×7.
  - First answer move: median ≈ f18 (T_LAT 19).
- **Placements vs the masked brain (tap mask, P=2):**
  - G3: **100/120** match (83%).
  - G4: **40/49** (82%).
  - The mask never removed the brain's choice.
  - No landing fell outside the mask; 3 tucks.
  - **PROPH never fired.** Spawn-lane height maxed at 12: neither game entered the ledge regime.
  - The mismatches (G3 20, G4 9) are scattered different targets / orientations. There is no clamp, PROPH or
    ledge pattern. Not examined further (fast pass).
- **Gates:** masked-decider identity 169/169. Mechanics with garbage: 161/167 steps exact or explained (6
  unexplained).
- **Cases:** `cases_tap_20260926_g3g4.jsonl` (169).
