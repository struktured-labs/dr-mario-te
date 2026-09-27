# RESULT (2026-09-26, Claude): the owner's garbage sends as the AI receives them. Are they bigger or more frequent than the sims assume?

**Data:** every recorded couch game.
- 9/24 G1–G3, 9/25 G1–G4, 9/26 AM G1–G4 (incl. the partial G4): L11, 11 games, 25.7 min.
- 9/26 PM G1–G3: **LEVEL 10**, 8.1 min.

**Volley extraction:** from the banked placement pairs (`owner_sends.py`):
- extras = garbage singles present after the AI's pill resolves;
- the garbage-aware mechanics fit supplies the size when a volley completed a clear;
- arrival time = the AI's next spawn, so resolution is one placement (~0.6–2 s).

**Phase axes:** time into the game, and both HUD virus counters, read by digit templates harvested from P2's
counter (`hud_digits.py`). P2 template read == validated board reader on 1,151/1,166 anchors. P1 matches 5/5
eyeballed HUD values.

## Verdict: NO, this week's sends are not larger or more frequent than the sims assume. They are slightly *smaller*.
| | volleys/min | mean cells/volley | cells/min | size mix 2 / 3 / 4 |
|---|---|---|---|---|
| **owner, L11 (this week)** | **4.87** [95% 4.16–5.54] | 2.31 | **11.25** | **85% / 2% / 12%** (+2 merged doubles) |
| owner, L10 (9/26 PM) | 3.58 | 2.72 | 9.75 | 23 / 0 / 4 (+2 merged) |
| VS-race model (lam 6, Hartford sizes) | 6.0 (+23%) | 2.37 | 14.2 (+26%) | 73% / 17% / 10% |
| gate-(b) Aug bursty fit, linked to the AI's clears, on the SAME AI clears | 5.25 (+8%) | 2.36 effective (2.54 nominal) | ≈12.4 (+10%) | 69% / 15% / 11% (+5, 6) |

Per session (volleys/min): 9/24 5.02 · 9/25 4.70 · 9/26 AM 4.91 · 9/26 PM (L10) 3.58. Cells/min: 11.6 · 10.7 · 11.5
· 9.8.

## Where the model and the owner differ (the refit is about SHAPE, not volume)
1. **Size mix:** the owner's sends are almost all 2s and 4s.
   - 3-cell sends are rare: 2% vs 15–17% in both sim models.
   - 4-cell sends are 12%, and 2 more "doubles" landed in one placement interval.
   - Mean size is about the same. The owner's chain stacking shows up as 4-sends, not 3-sends.
2. **Columns:** 77% of the owner's 2-cell sends land in two different columns, 23% in one.
   - The Aug `bursty_model.sample` always stacks a 2-cell send in ONE column (`n_cols = round(n/2)`).
   - It places only 2 cells for a 3-send (`rows_per_col = n // n_cols`).
   - Real 4-sends spread over 3 columns in 5 of 8 cases.
3. **Timing:**
   - Inter-volley gaps: median 8.3 s (p10 4.2, p25 5.7, p75 13.9, p90 23.9), CV 0.81. That is a little *more
     regular* than Poisson, with **no burst clustering**: only 2 of 114 gaps are ≤ 3 s and 20 are ≤ 5 s.
   - The Aug fit's gap median was 15 s, but gate (b) does not use gaps. It fires on AI clears, which gives the right
     rate here (5.25 vs 4.87/min) for the wrong reason.
4. **Linkage:** gate (b) sends only after AI clears. The owner says his sends are organic and not targeted, and the
   data agree: the rate is flat across the AI's progress (below). A refit should be an independent renewal process,
   not a clear-triggered one.

## Phase dependence (`phase_sends.py`, `owner_sends_phase.json`)
L11, volleys/min (mean size):

| by | bin | rate (mean size) |
|---|---|---|
| time into game | open < 30 s | 5.09 (2.21) |
| | mid 30–90 s | 4.82 (2.33) |
| | late ≥ 90 s | 4.80 (2.35) |
| owner's viruses | > 30 | 4.72 (2.25) |
| | 21–30 | 4.83 (2.33) |
| | 9–20 | 6.32 (2.56), 1.4 min, 9 volleys |
| | ≤ 8 | 0.1 min, not measurable |
| AI's viruses | > 30 | 4.84 |
| | 21–30 | 5.34 |
| | 9–20 | 4.32 |
| | ≤ 8 | 5.05 |

All levels by owner viruses: > 30: 4.47 (2.28) · 21–30: 4.88 (2.26) · 9–20: 4.15 (2.70), 20 volleys.

- **Rate is not clearly phase-dependent.** It is flat by time and by the AI's board. By the owner's board it moves
  in opposite directions between L11 and all levels.
- **Size rises weakly when the owner is at 9–20 viruses:** 2.56–2.70 vs ~2.25, on 9–20 volleys. That is consistent
  with "he combos more at some parts of the game", but the evidence is thin.
- He almost never reaches ≤ 8 (0.1–0.3 min in total), because the games end first.
- ⇒ `owner_fit_202609.json`: flat rate/size by default, with the phase table included for sensitivity runs.

## Files
- `owner_sends.py` → `owner_sends_cases.jsonl`: every volley, with time, size, columns and how it was measured, plus
  the model-implied fires per game.
- `hud_digits.py`: HUD digit reader.
- `phase_sends.py` → `owner_sends_phase.json`.
- **`owner_fit_202609.json`**: refit parameters (rate, size pmf, gap quantiles + samples, column spread, phase table,
  comparison block). Decoding ran at nice 19 / single thread.

**Caveats:**
- These are sends *received*, at one-placement resolution.
- Unexplained mechanics steps: 17 volleys have unknown size (11 in L11).
