# RESULT (2026-10-03, Claude): the owner and dr. lulu send about HALF as many volleys as the 202609 fits said

**Why a refit:** `track.py` misses a spawn whenever the next capsule has the same colours.
- `owner_sends.py` / `lulu_profile.py` then read the merged second pill (2 cells) as a 2-cell garbage VOLLEY, and two
  merged pills as a "4".
- On this cart, runs of identical capsules are common: 10–24% of spawns per game, including a run of ≥ 7 YY verified
  on video.

**Method** (`refit_sends_202610.py`):
1. Re-track every source from its BANKED per-frame reads with `track_hidden_dist60_20261003.py`. No video decode.
2. Re-run `owner_sends`' volley extraction verbatim on the new tracks.

**Gates:**
1. **Tracker identity:** `track.py` today on the banked frames reproduces every banked raw file, 18/18
   (colours + landings).
2. **Old numbers reproduced:** the old extraction on the old tracks reproduces the published fits exactly (owner L11
   4.87/min and 11.25 cells/min; lulu 4.73 and 11.39).
3. **ROM column rule** (`rom_attack_rule.py`): size 2 lands in columns {s, s+4}, size 3 in {s, s+2, s+4}, size 4 in
   {s, s+2, s+4, s+6}. Checkable volleys only (fully visible, one cell per column):

   | volleys | conform / checkable, new tracker | conform / checkable, old tracker | violations, old tracker |
   |---|---|---|---|
   | owner | **114/114** | 74/107 | 33 |
   | dr. lulu | **24/24** | 18/24 | 6 |

   The removed "volleys" are exactly the shapes garbage cannot have: same-column pairs (vertical pills) and adjacent
   pairs (horizontal pills).

## Old vs new
**The owner** (sends as received by the AI):

| | volleys/min | 95% CI (game bootstrap) | cells/min | mean size | sizes 2 / 3 / 4 | doubles | gap p50 (s) |
|---|---|---|---|---|---|---|---|
| **owner_fit_202609**, L11 9/24–26, 11 games | **4.87** | [4.17, 5.56] | **11.25** | 2.31 | 85% / 2% / 12% | 1.6% | 8.3 |
| same 11 games, new tracker | 2.57 | [2.10, 3.16] | 5.44 | 2.12 | 89% / 9% / 1.5% | 0 | 15.8 |
| 10/03 match 1, 4 games (owner groggy, cat on lap) | 1.91 | [1.62, 2.35] | 4.26 | 2.23 | 86% / 5% / 9% | 0 | 26.1 |
| **owner_fit_202610**, L11 9/24–26 + 10/03, 15 games, 37.2 min | **2.36** | **[1.99, 2.85]** | **5.08** | 2.15 | **89% / 8% / 3%** | 0 | 20.0 |
| sensitivity: + 9/27 HSV days, 21 games | 2.36 | [2.11, 2.64] | 5.34 | 2.26 | 85% / 9% / 7% | 1.4% | 18.8 |
| L10 (9/26 PM), old → new | 3.59 → 2.08 | | 9.77 → 5.14 | | | | |

**Per session, old → new (L11):** 9/24 5.02 → 1.95 · 9/25 4.70 → 2.80 · 9/26 AM 4.91 → 2.82 · 9/27 4.32 → 2.35 ·
10/03 → 1.91.

**dr. lulu** (2 games, PROVISIONAL):

| | volleys/min | cells/min | sizes 2 / 3 / 4 | gap p50 (s) | upper bound |
|---|---|---|---|---|---|
| **lulu_fit_202609** | **4.73** | **11.39** | 78% / 3% / 17% | 8.7 | ≤ 7.13 |
| **lulu_fit_202610** | **2.56** | **6.12** | 77% / 13% / 10% | 16.3 | ROM-plausible ≤ 2.71; all unexplained ≤ 4.96 |

- Her soft 720p capture still leaves 31 unexplained steps with new cells. Almost all add ONE cell in one column, which
  is a reader error, not a volley shape.
- Clear pace (5.6 / 10.1 viruses/min) comes from the HUD and is unchanged.

## What changes
- **The sims' opponents send about 2× (owner) to 1.8× (lulu) too much.**
  - OWNER-2026-09 (gate b, `opp_owner202609.py` on `owner_fit_202609.json`) draws 4.87 volleys/min. The data say 2.36.
  - The LULU race uses lam 4.7 ("her measured rate"). The data say 2.56.
  - The VS-race instrument (lam 6) is 2.5× the owner, not "+23%".
- **The size mix flips.**
  - 4-cell sends are rare (3%), not 12–17%.
  - 3-cell sends are 8–13%, not 2–3%.
  - 2-cell sends always land in two columns 4 apart, never the same column.
  - The 202609 "column" and "4-send" findings were hidden pills.
- **Not re-derived:** the phase table, and any sim result that used the 202609 fits. These snapshots are for the
  steersim lane to re-run.
- **The new snapshots load in the existing opponent classes** via `fit_path` (checked: `Owner202609(fit_path=...)` and
  `Lulu202609(fit_path=...)`). No sims were run.
- The 202609 files are untouched.

## Files
- `owner_fit_202610.json`, `lulu_fit_202610.json`. Same key layout as 202609, plus `supersedes`, `compare`,
  `columns.rom_column_rule_checkable_volleys`, per-session rates, and a sensitivity block. Gap samples are in board
  time (STUDY pauses capped).
- `refit_sends_202610.py` (retrack | fit | write) → `refit_sends_202610_cases.jsonl` (every game, old and new tracker,
  every volley with time, board time, size, columns, linked-pair flag) and `refit_sends_202610_table.json`.
- The re-tracked raws (`rawh_*`) are in `~/projects/dr_mario_rl/tmp/dist60_20261003/refit/` (regenerable from the
  banked frames in ~25 s).
