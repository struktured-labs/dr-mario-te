# RESULT (2026-09-27, Claude): first clean-HDMI recording of dr. lulu vs ANTIBODY (HSV build), series 1-1

- Build: rbf 6b73907c / fw 77ec742c / couch cart 198a95e3.
- Video: `20260927_111114_struktured_v6c_part2.mkv`. lulu = P1, ANTIBODY = P2.
- Everything ran at nice 19 / single thread (OBS was recording).
- **G1** (0.0–494.1 s): **ANTIBODY won.** lulu topped out at 2 viruses with the AI at 1 (HUD).
- **G2** (504.8–793.4 s): **lulu won by CLEARING FIRST** (48 → 0 at 793 s). The AI was at 5 and did NOT tap out.

## Capture, re-fit and gates (new capture path: rivalmage → Samsung, 720p)
- **Geometry changed.** The gap-fold fit over both bottles gives pitch **44.6 × 38.5** (was 43.8 × 38.57) and P2
  origin (1125.25, 341.0), in `geom_lulu_20260927.json`. The reader now takes a per-capture geometry (`CF_GEOM`).
  The HUD digit boxes did not move.
- **L11 verified** by the HUD (LEVEL 11/11 MED/MED, 48 viruses) in both games.
- **Two reader fixes the softer capture forced.** Both are regression-checked on the 9/25 capture: 50/50 pre-death
  boards identical.
  1. **Virus animation.** One animation phase has only 1–2 dark interior pixels, so one frame under-counted by 3–5.
     `track.py` now marks a settled cell as a virus if it read as a virus in any frame of the next ~0.33 s. Viruses
     never move, and static pills never cross the threshold.
  2. **Wall bleed.** The light-blue bottle wall makes a BLUE tile in column 0/7 read square wall-side corners, so a
     left half looked unlinked and fell in the sim. Links for the wall columns are now decided from the inner corners.
- **GATE 1:** P2 HUD == board reader at spawns **458/460**. The 2 misses are game-boundary frames.
- **Mechanics gate:** 206/233 (G1) and 120/139 (G2) steps reproduce exactly or via a garbage volley, so **~12% are
  unexplained** (vs ~4% on the 1080p captures). Those placements are flagged UNVERIFIED. The verified numbers below
  use 187/235 and 106/141 placements.
- **Placement match vs the HSV brain (verified):** G1 **67%**, G2 **68%**. The owner matches were 71–85%. The
  difference is mostly OTHER (20%), some of which may be capture-related. Treat it as provisional.

## 1. G1: the column-2 stall
**The stall:** the AI sat at **4 viruses from 177.7 s to 377.9 s** (200 s, ~99 pills). The last virus it needed was
a **YELLOW at row 8 of column 2**. That is outside HSV's cols 3–5, and it was there from the start.
- **Why it could not be cleared:** column 2 above it was a tall **mixed-colour stack**, top→down `r b y b r b r y`
  (plus garbage on top). A vertical clear was impossible; the only way was a horizontal yellow line through row 8.
- **Clearing moves existed on only 2 of 102 pills** (`linger_cell.py` → `linger_lulu_g1_c2.jsonl`), both at the very
  end:
  1. **k180:** silicon placed H3 YY at row 8 (yellows at (8,3),(8,4)).
  2. **k181:** a clearing move existed (H5 YR at row 8). **The HSV brain chose it; silicon landed one column off
     (H6).** That is an execution miss.
  3. **k184:** silicon cleared it with V5 YB (the next clearing chance). The HSV brain's own choice here was V3 YB,
     not the clear.
- **Did her garbage unlock it?** Partly. During the stall, cols 3–4 (which had to reach row 9 to carry a row-8 line)
  received **82 cells from the AI's own pills and 16 from lulu's garbage**. The support was mostly the AI's own
  building; her garbage helped only at the margin.
  - The owner's read ("her dumps eventually gave the search a board it could fix") is directionally right: the fix
    only became reachable when those columns happened to fill to row 9.
  - The dominant cause is structural: a single virus sealed under a mixed stack, needing a multi-pill horizontal
    build that a depth-3 search does not plan from far away.
- **Widened HSV region (cols 2–6, `leaf5b_wide.py` = a mechanical copy with `range(2, 7)`, W=512):** it changes
  **only 3 of 102** choices. It picks the clear at k184 (silicon did it anyway) but **would not have shortened the
  stall**: for ~99 pills no clearing line existed within the search horizon. What would help is a term that values
  *building toward* the clear (support under the target row), not one that rewards clearing it.

## 2. G2: execution, and why the AI lost
**lulu simply outraced it.** She cleared 48 in 284 s (**10.1 viruses/min**); the AI managed 43 (9.1/min). The AI
finished 5 short.

**Execution cost** (`exec_cost.py`: viruses the HSV brain's choice would clear vs what silicon's landing cleared):
**3 missed clears, 3 viruses**, in 141 placements:
- **k23 (556.7 s)** SHORT-LANDING: the brain's V1 BB would clear 1; silicon landed V2 at row 5 and cleared 0.
- **k52 (606.5 s)** LATE-FLIP: the brain's H4 BR would clear 1; silicon ended H1 RB and cleared 0.
- **k88 (683.0 s)** OTHER: the brain's H6 YY would clear 1; silicon went V4 YY and cleared 0.

Those three are real execution mistakes and cost about 3 of the 5-virus deficit.
- The rate is **not unusual**: 0–2 missed clears per game in the owner's HSV matches, 5 in lulu G1.
- Classes (verified): MATCH 72, OTHER 17, late flip 7, short 5, tuck 5. PROPH fired once.
- **DRSPAWNEDGE class:** 1 top-row lock (k127, 772.9 s). The next pill landed exactly where the brain wanted, so
  there is no missed-edge harm on record.

## 3. dr. lulu profile (`lulu_profile.py` → `lulu_fit_202609.json`, `lulu_cases.jsonl`). PROVISIONAL, n = 2 games.
**Clear pace:** G1 **5.6 viruses/min** (48 → 2 in 490 s, then topped out under the AI's pressure). G2
**10.1 viruses/min** (48 → 0 in 284 s).

**Her sends as received by the AI:**

| measure | value |
|---|---|
| volleys/min | **4.7** (explained volleys only; ≤ **7.1** if every unexplained step with new cells was a volley) |
| cells/min | ≥ **11.4** |
| size mix | 2: 78% · 3: 3% · **4: 17%** (the owner: 85 / 2 / 12) · merged doubles 1.6% |
| gaps (s) | median 8.7 (p10 3.6, p90 25.6), CV 0.73, 5% ≤ 3 s |

**Phase:** an **aggressive opening**.
- First 30 s: 6 volleys/min, mean size 3.3, 20 cells/min. After that ~3.5–4.8 volleys/min, mean ~2.3.
- By her remaining viruses: mean size 3.0 while she has > 30, 2.1–2.5 later.
- n is small (6–8 volleys in the opening).

**vs the owner (`owner_fit_202609.json`):** a similar volley rate (4.7 vs 4.9, both lower bounds) with **more 4-cell
sends** and a front-loaded opening. The clearer difference is **clear speed**: 10.1/min in the game she won. That is
the "racer" profile.

## Files
- **Cases:** `cases_lulu_20260927.jsonl` (376 classified placements with both brains, the wide-HSV choice, the mask,
  timing, missed-clear flags), `linger_lulu_g1_c2.jsonl`, `lulu_cases.jsonl`.
- **Fit:** `lulu_fit_202609.json`.
- **Geometry:** `geom_lulu_20260927.json`.
- **Scripts:** `linger_cell.py`, `exec_cost.py`, `lulu_profile.py`, `leaf5b_wide.py`, and the reader.py / track.py /
  analyze_tap.py changes.
