# RESULT (2026-10-06): STEER11, a couch-calibrated race clock. The A16 near-miss reverses on it; the confirmation was abandoned before analysis

- **Commits:**
  - clock + identity cb842760;
  - prereg stage A 5afb7816, committed before the pilot was analysed;
  - stage B 0b79f3d8, with 0 confirmation rows.
- **Rows:**
  - `steer11/clockcal_pills.jsonl`: the couch table;
  - `steer11/pilot/`: 3,600 rows, audit OK;
  - `steer11/confirm/`: 663 PARTIAL rows, banked untouched, NOT analysed. See section 4.

## Short answer
1. **The vs_race clock was 23% fast against the couch, and the error was structural.**
   - It charged 0 for received garbage and undercharged cascades.
   - The couch-calibrated clock `couch11` reproduces the held-out AI clear times: median 210.8 vs 209.2 s observed.
   - Sim FAIR now clears in a median **208.4 s** (couch 209) at **1.81 s/pill** (couch 1.74).
2. **FAIR's absolute levels on couch11** (STEER10 blocks):
   - **LULU race:** 87.0% → **40.5%** win over the STEER10 pace prior (M 80/100/120/140: 13.3 / 32.4 / 51.1 /
     **65.0%**). Losses are almost all SLOW: 55.6 slow vs 4.0 kill.
   - **Owner race:** 93.5% → **83.8%**.
   - **Gate-b tap-out** stays 6.17%: its garbage is pill-keyed, so the clock does not touch it.
   - **Caution:** the STEER10 pace prior was built for the too-fast legacy clock. On couch11 only M ≈ 140 matches the
     couch's 6/9 (67%).
3. **s10_A16 on couch11, on the SAME 1,200 STEER10 seeds:** **−1.23 pp [−2.58, +0.19]**, against +1.35 on the legacy
   clock.
   - It still cuts stalls (stall-pills from ≤ 16 viruses −5.7, longest stall −6.4 s) and LULU tap-outs (−2.75 pp).
   - It loses tempo: −3.0 at M 80, +0.8 at M 140. **Tempo is what binds on the corrected clock.**
4. **The confirmation was ABANDONED BEFORE ANALYSIS.** It was stopped at 663 / 24,000 rows on the coordinator's
   priority call: the pilot was negative and the power at the design effect was 0.42. **No PASS/FAIL verdict exists.**
   **A16 is parked.**

## 1. The clock (`steer11_clockcal.py` → `steer11/clockcal.txt`, `steer11/clock_couch11.json`)
**Data:** every AI inter-spawn interval of 19 couch games, from real-time HDMI captures with the hidden-spawn tracker.
- 10/04: the owner vs FAIR / FAIR2, 10 games.
- 10/05: dr. lulu vs FAIR, 9 games.
- Totals: 2,147 pills, 2,128 intervals, 0 pauses > 15 s.
- The table was rebuilt with the forensics' own loaders. It matches the banked `cases_*_ai_pills` on 2,147 / 2,147
  pills.

**Features** are exactly what the sim knows per placement:
- the drop rows `15 − hmax` of the landing's target columns;
- the clear steps;
- the gravity fall rows of each cascade step;
- whether a volley landed, and the rows its tiles fell;
- whether the garbage set off a clear.

**Interval means (s):**

| interval | couch | legacy clock |
|---|---|---|
| plain | 1.01 | 0.95 |
| 1-step clear | 1.85 | 1.56 |
| 2-step clear | 2.62 | 2.23 |
| 3+-step clear | 3.97 | 2.99 |
| garbage after, no own clear | 3.88 | 0.94 |
| garbage after, own clear | 5.60 | 1.85 |

**Models** (OLS on the interval, game-cluster bootstrap; LOGO = leave one game out, error on the game total):

| model | terms | per-pill RMSE | LOGO game-total mean / mean \|err\| / max |
|---|---|---|---|
| legacy | 39 + 2 drop + 40 steps f, garbage 0 | 1.14 s | +23.0% / 23.0% / 31.7% |
| M1 | + flat per-volley charge (190 f) | 0.57 s | −1.7% / 5.5% / 18.8% |
| M3 | + cascade fall rows, + garbage fall rows | 0.33 s | −0.1% / 3.0% / 8.3% |
| **M4 (chosen)** | M3 + garbage set off a clear | **0.32 s** | **−0.1% / 3.1% / 8.4%** |
| M5 | M4 + per garbage cell | 0.31 s | `vol` goes negative: over-fit |

**M4 coefficients** (all 19 games; NES frames, game-cluster 95% CI):

| term | frames (95% CI) |
|---|---|
| per pill | 33.3 [30.7, 36.0] |
| per drop row | + 3.1 [2.8, 3.3] |
| per clear step | + 20.2 [18.3, 22.7] |
| per cascade fall row | + 15.9 [15.2, 16.5] |
| per released volley | 17.4 [−17, +52] |
| per garbage fall row | + 16.9 [13.5, 20.6] |
| garbage set off a clear | + 44.1 [14, 89] |

- The cascade and garbage gravity rates were fitted independently and agree (15.9 vs 16.9 f/row), as one ROM falling
  routine would predict.
- **Diagnostic:** a 10/05-vs-10/04 day shift is −4.3 f per pill (≈ 4%). It is small, so the pooled model was kept.

**VALIDATION** (hold-out: fitted on the other 15 games, predicting the 4 10/05 AI clear games):

| game | observed | couch11 on its silicon pills | legacy |
|---|---|---|---|
| M1 G5 | 184.0 | 187.9 (−3.9) | 142.1 |
| M2 G1 | 258.6 | 258.0 (+0.6) | 190.7 |
| M2 G2 | 232.3 | 233.8 (−1.5) | 171.8 |
| M2 G4 | 186.1 | 185.3 (+0.8) | 127.6 |
| **median** | **209.2** | **210.8 (residual −1.6 s; per-game mean \|residual\| 1.7 s)** | 157.0 |

- **Brain-only pills + the median execution overhead (22) × the game's predicted s/pill:** median 217.0 s (residual
  −7.8 s).
  - Per game the residual is −35 / +44 / +0 / −1 s.
  - That spread is the pill-count error: M2 G1 needed 47 extra execution pills, not 22.
- **In the sim** (pilot, FAIR, 1,048 clears): median **208.4 s**, 115 pills, 1.81 s/pill.

**Implementation:**
- `vs_race.CLOCK` (None = legacy) feeds `vs_race.pill_frames` / `garbage_drop_timed`. These are used by `vs_race.play`
  and `stuck_probe.play_race`.
- Under a calibrated clock, rows add `clock`, `nrel` and `garb_s`.
- **Identity** (`steer11_identity.py`, legacy clock, patched code): 17/17 rows byte-identical to the banked
  STEER10 / STEER8 FAIR and A16 rows (lulu10b, rc10, gb10). The positive control differs.
- **Clock tests** (`steer11_clocktest.py`):
  - sim feature code == calibration code: 190/190 cascades, 1,138/1,138 in an all-action sweep, 30/30 garbage drops;
  - t_end == Σ traced charges, with 0 formula mismatches;
  - a legacy replay == banked, and couch11 changes t_end.
- **Validity:** fitted on FAIR-timing silicon (tempo −6); `steer11_run.py` asserts it.

## 2. FAIR on the corrected clock (`steer11/pilot.txt`; STEER10 blocks, declared reuse)

| | legacy clock | **couch11** |
|---|---|---|
| LULU race win, pace prior M 80–140 (lam 2.84, lulu_fit_202610b) | 87.00% | **40.46%** |
| ↳ M 80 / 100 / 120 / 140 | 78.0 / 87.8 / 90.6 / 91.6% | **13.3 / 32.4 / 51.1 / 65.0%** |
| ↳ losses: slow / kill | 8.2 / 4.8 | **55.6 / 4.0** |
| LULU race tap-out (how == topout) | 8.00% | 12.67% |
| time to clear p25 / 50 / 75 | 128.5 / 147.4 / 174.7 s | **176.3 / 208.4 / 258.0 s** |
| pills to clear / s per pill / tiles received | 111 / 1.33 / 14.5 | 115 / 1.81 / 20.0 |
| garbage handling time | 0 | 31.6 s per clear game |
| owner race M 177 (lam 2.36), n = 600 | 93.50% | **83.83%** (tap-out 10.50%) |
| gate-b tap-out (clock-independent) | 6.17% | 6.17% |

- **Reading the LULU numbers.** STEER10 set the pace prior to make races "couch-shaped" on the too-fast clock
  (PREREG_STEER10 sec. 5). On couch11:
  - FAIR's 40% average is dominated by M 80–100, i.e. a dr. lulu far faster than the couch one.
  - M 140 gives 65.0%; the couch result was 6/9 (67%).
  - The coordinator ruled (2026-10-06) that decisions from now on use **opponent-MEASURED pace**: M fitted from her
    and the owner's couch clears on the couch11 clock, in a new prereg (STEER12).
- **Losses are SLOW losses (55.6 of 59.5 pp).** On the corrected clock the AI mostly loses by being later, not by
  topping out. The garbage it receives (+38% tiles; 31.6 s of handling per clear game) is part of that.

## 3. s10_A16 on couch11 (pilot, the STEER10 hypothesis block: NOT confirmatory)

| A16 − FAIR, same 1,200 seeds | legacy clock | **couch11** |
|---|---|---|
| LULU pace-prior win | +1.35 [+0.02, +2.71] | **−1.23 [−2.58, +0.19]** |
| M 80 (churn fixed / new) | +0.58 (87/80) | **−3.00 [−4.67, −1.42]** (32/68) |
| M 100 | +1.58 (60/41) | −1.83 (77/99) |
| M 120 | +1.50 (48/30) | −0.92 (102/113) |
| M 140 | +1.75 (44/23) | +0.83 (114/104) |
| stall-pills from ≤ 16 viruses | −7.0 | **−5.66 [−9.01, −2.56]** |
| longest stall | −6.3 s | **−6.39 s [−11.45, −1.71]** |
| LULU race tap-out | −1.83 | **−2.75 [−4.42, −1.08]** (67/34) |
| slow losses at M 80 / 100 / 120 / 140 (games) | | 1011 → 1046, 770 → 791, 532 → 540, 354 → 339 |
| owner race M 177 | −1.33 | +1.50 [−1.00, +4.17] (35/26) |

**Mechanism, as measured:** A16 keeps doing what STEER10 saw. It stalls less and tops out less. But on a clock that
charges what the couch charges, it is slower overall: median time to clear 208.4 → 209.6 s, pills 115 → 117. Slow
losses rise wherever the opponent is fast.

**Discordance:** seeds whose pace-prior result differs between arms rise from 19% to 45% on couch11. The clock couples
pill timing to garbage arrival, so small decision changes reshuffle which pill receives a volley.

## 4. The confirmation: ABANDONED BEFORE ANALYSIS
- **Pre-registration:** PREREG_STEER11 stage A (5afb7816) and stage B (0b79f3d8).
  - n = 4,000 per instrument per arm by the committed rule; seeds 41100–49098, disjoint from STEER10.
  - UNDERPOWERED BY DESIGN: power 0.42 at the floored design effect of 0.675 pp, 0.23 at 0.7 × that.
- **Launched** 16:04Z. **Stopped** 16:14:54Z on the coordinator's priority call: the same-seed pilot was negative on
  the corrected clock, and the power was 0.42.
- **Banked untouched** in `steer11/confirm/`:

  | cell | FAIR rows | A16 rows |
  |---|---|---|
  | lulu11 | 132 | 113 |
  | gb11 | 132 | 85 |
  | rc11 | 116 | 85 |

  That is 663 rows in 16 files; the last job of each cell is truncated mid-file.
  - Only these row counts, a blind quantity, were read.
  - No contrast, level or outcome was computed.
  - `analyze_steer11.py confirm` now REFUSES (R97).
- **There is no verdict.** Neither PASS nor FAIL is claimed for A16. **A16 is parked:** it buys stalls and survival
  but costs tempo, and tempo binds on couch11.

## Files (`experiments/cvx/`)
- **Clock:**
  - `steer11_clockcal.py`;
  - `steer11/clockcal_pills.jsonl` (+ `steer11/clockcal/` per game);
  - `steer11/clockcal.txt`;
  - `steer11/clock_couch11.json`;
  - `vs_race.py` (CLOCK / pill_frames / garbage_drop_timed);
  - `stuck_probe.py`.
- **Gates:** `steer11_identity.py` + `steer11_gate.sh` + `steer11/gate/`; `steer11_clocktest.py`.
- **Runs:** `steer11_run.py`, `steer11_jobs.py`, `steer11_farm.sh`, `steer11_sizing.py` (`steer11/sizing.txt`).
- **Analysis:** `analyze_steer11.py` (pilot → `steer11/pilot.txt`; confirm refuses).
- **Shared box:** throttle `dr_mario_rl/tmp/steer11/throttle.sh`, PAUSE `dr_mario_rl/tmp/steer11/PAUSE` +
  `tmp/PAUSE_ALL`, desk runner `dr_mario_rl/tmp/steer11/desk.sh`.
- **Seed registry:** REUSE notes on "champ145 reserve" / "gwprice". The block is spent only up to the partial rows.
