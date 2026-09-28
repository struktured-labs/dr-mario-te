# STEER6 phase 2: stuck-virus measurement spec (written before the measurement run)

This is a characterisation, not an A/B, so there is no gate. The definitions are fixed here before any
measurement game.

## Build and conditions
- **Build:** ANTIBODY in sim, `steer_run.make("s5b_hsv512")`. That is CHAIN540 + reach-masked root + unified
  DRTAPP=2 + HSV512, under the couch steering model.
- **Conditions:** four, 600 seeds each (37934–39132 even; declared reuse, the OPP1 block).

| cond | instrument | opponent |
|---|---|---|
| gb-0804 | gate (b), L11, cap 600 | OWNER-0804 bursty (linked to AI clears) |
| gb-09 | gate (b) | OWNER-2026-09 renewal refit |
| gb-lulu | gate (b) | **dr. lulu 2026-09 renewal fit** (`opp_lulu202609.py`, `lulu_fit_202609.json`, n = 2 games, PROVISIONAL) |
| race-4.7 | vs_race, lam **4.7**/min (her measured volley rate), Hartford sizes | race scored at M 140 δ 2.65 (the OPP1b primary); 160 / 177 reported |

## Instrument (`stuck_probe.py`)
- **Trajectories are unchanged.** The probe only clones boards. Identity is 9/9 vs banked rows (gb-0804, gb-09,
  race lam 2), and 4/4 local == Hetzner md5.
- **At every decision, for every remaining virus:** does a legal straight-drop placement clear it (place + faithful
  resolve, cascades included)? This is checked for three kinds of "clearing move":
  - **str:** with ANY colour pair.
  - **act:** with the actual pill.
  - **mask:** the actual pill inside the shipping reach mask.
- **VIRUS episode:** a virus's consecutive decisions without a clearing move, kept if ≥ 10.
  - Early in a game almost every virus qualifies: a lone virus needs 3 more cells, and one pill adds 2.
  - So these are stratified by viruses left at the start (≤ 4 / 5–12 / > 12). The endgame strata are the couch
    "lingering virus".
- **BOARD stall:** consecutive decisions where NO remaining virus has a clearing move. This is the couch G1 stall:
  2 of 102 pills had one. **N = 10 and N = 20.**
- **Ends:**
  - cleared_own / cleared_garbage;
  - unlocked_own: the board right after the AI's placement, before garbage, was already structurally clearable;
  - unlocked_garbage;
  - unlocked_pill: it was structurally clearable before, and only the pill colour was wrong (act/mask only);
  - end: censored by the game's end.

## Questions answered (all descriptive)
1. **Frequency:** games with ≥ 1 board stall ≥ N (str / act / mask); stalls per game; the fraction of decisions spent
   in a stall.
2. **Duration and end:**
   - stall length distribution;
   - end-type shares (own / garbage / pill / censored);
   - viruses left at stall start.
3. **Outcomes:**
   - What fraction of tap-outs (gate b) and race losses (race-4.7 at M 140 δ 2.65) contain a stall ≥ N?
   - What fraction are IN a stall at the end (censored stall)?
   - The same fractions for clears and race wins, as the base rate.
   - The pills and seconds lost to stalls in won games (the tempo cost).
4. **Endgame lingering viruses (virus episodes, vleft0 ≤ 4):** frequency and ends.

Rows: `steer6/measure/{local,remote}/`. Analysis: `analyze_steer6_measure.py`.
