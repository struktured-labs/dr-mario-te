# RESULT (2026-09-27): STEER6 "BUILD TOWARD A CLEAR"

- Phase 1 prior art: `PRIOR_STEER6.md` (`7205268e`).
- Phase 2 measurement spec: `MEASURE_STEER6.md`.

## Phase 2: how big is the stuck-virus prize? (ANTIBODY in sim, 600 seeds × 4 conditions)
**Setup:**
- Instrument: `stuck_probe.py`. The probe only clones boards: 9/9 rows are identical to banked rows, and local ==
  Hetzner 4/4.
- Rows: `steer6/measure/`. Analysis: `analyze_steer6_measure.py` → `steer6/measure/analysis.txt`.
- **Stall** = consecutive decisions in which NO remaining virus has a clearing move with the actual pill ("act").
  This is the couch lulu-G1 definition.
- "str" = no clearing move with ANY colour pair: the board is structurally sealed.

| | gb OWNER-0804 | gb OWNER-2026-09 | gb **lulu fit** | race lam 4.7 (M140 δ2.65) |
|---|---|---|---|---|
| outcome | tap-out 23.0% | tap-out 21.8% | tap-out 18.5% | tap-out 26.7%; race win 68.5% |
| games with a stall ≥ 10 / ≥ 20 (act) | 85% / 59% | 78% / 56% | 77% / 50% | 80% / 54% |
| games with a SEALED stall ≥ 20 (str) | 53% | 48% | 44% | 46% |
| decisions spent inside a stall ≥ 10 | 32% | 33% | 30% | 34% |
| stall length p50 / p90 (≥ 10) | 18 / 66 | 19 / 82 | 17 / 66 | 18 / 90 |
| viruses left at stall start (p50) | 4 | 4 | 4 | 5 |
| **losses dying INSIDE a stall** (act ≥ 10) | **75%** of tap-outs | **76%** | **83%** | kill 64% · **slow 70%** |
| **losses = a terminal stall ≥ 20 that started at ≤ 4 viruses** | **41%** of tap-outs | **45%** | **47%** | slow losses **52%**; kills 13% |
| wins: pills spent in stalls ≥ 10 | 37% of pills | 32% | 31% | 25% (**≈ 50 s per won race**) |

**How stalls end** (str stalls ≥ 10, all conditions):
- **~90% are unlocked by the AI's OWN placements.** Garbage unlocks 3–5% (26–40 per 600 games).
- act stalls end mostly because the right pill COLOUR finally arrives: unlocked_pill ≈ 55–60%. The board was
  already structurally clearable; the bot was waiting on colour.

**Is the death-in-a-stall a consequence of the full bottle?** No:
- The terminal stalls in tap-outs are long: median **44–87 pills**, and 46–64% last ≥ 50 pills.
- They start at a median of **3 viruses left**.
- These are endgames where the bot is stuck for dozens of pills while the bottle fills, not the last few pills of a
  full board.
- Race kills are different: they are short (p50 29 pills) and early (10 viruses left). Those are not this problem.

**Reading:**
- **The prize is large and concentrated in the endgame.**
  - About **45% of all gate-(b) tap-outs** (≈ 10 pp of absolute tap-out at the 22% base rate) are "stuck endgame"
    deaths: a stall of ≥ 20 pills that began with ≤ 4 viruses left.
  - About **half of the slow race losses** are the same thing.
  - **Even the wins bleed tempo:** a quarter to a third of all pills are spent with no clearing move, about 50 s per
    won race. That is the "lulu outraced it by ~1 virus/min" gap.
- **The couch G1 stall is typical, not a fluke.** Its shape matches: 4 viruses left, own-pill unlocks, ~100 pills.
- **Garbage almost never unlocks a stall in sim.** So a term that makes the AI build the support itself is aimed at
  the right actor.
- **Caveat:** these are the sim's straight-drop semantics. On silicon, tucks add moves the probe cannot see, so the
  true stall rate may be somewhat lower.

## Phase 3: candidates (`cascade_leaf6_x.py`) and couch regression (`steer6_regress.py`)
**The distance D(v).** A per-virus clearing distance: the minimum over 4-windows through v of the cell cost.
- Horizontal: each empty cell costs `1 + support gap`.
- Vertical: each empty cell above v costs 1.
- A wrong-colour cell or a cavity makes that route infeasible.
- It is graded and gravity-aware, and it takes the min over routes, so it is not a cover price.

**Five modes**, all switched on by a root (firmware-side) gate: (a) dist_end, (b) rowsup_end, (c) dist_stall,
(d) dist_target, (e) dist_hsv. Details are in `PREREG_STEER6.md` (`030e459f`).

**Couch regression**, from lulu G1 mid-stall (k120), counting pills until the sealed yellow clears:

| decider | with garbage | without garbage |
|---|---|---|
| ANTIBODY | 54 | 117+ (never) |
| D-candidates | 4–10 | 4–10 |

**Match-1 G3** (walled-in yellow): ANTIBODY 54 pills; dist_hsv 12–15.

## Phase 4: SCREEN (PREREG_STEER6.md; 600 paired seeds 37934–39132; gate b OWNER-0804; race lam 6, M 177, δ 2.65)
Rows: `steer6/screen/`. Local 3,000 + Hetzner 3,000; exactness 10/10. Analysis: `analyze_steer6.py` →
`steer6/screen/analysis.txt`.

**Baseline (ANTIBODY):** tap≤100 3.33%, tap-out **23.00%**, race win **68.17%**.

| arm | tap≤100 Δ | **tap-out Δ** | **race win Δ** | churn (fixed/new) | stall pills/game | endgame-stall deaths | verdict |
|---|---|---|---|---|---|---|---|
| **(a) dist_end60** | +0.00 | **−6.00 [−8.50, −3.50]** (17.0%) | **+6.17 [+3.33, +9.00]** | **48 / 12** | 77 → 48 | 9.3 → 4.7% | **PASS** |
| (b) rowsup_end180 | +0.00 | +0.83 [−2.17, +3.83] | +1.67 [−1.17, +4.33] | 39 / 44 | 77 → 55 | 9.3 → 9.0% | fail |
| **(c) dist_stall60** | −0.83 [−2.50, +0.67] | **−4.50 [−8.50, −0.50]** | **+9.67 [+5.50, +14.00]** | 91 / 64 | 77 → 45 | 9.3 → 5.7% | **PASS** |
| **(d) dist_target60** | +0.00 | **−4.17 [−6.67, −1.67]** | **+6.17 [+3.50, +8.83]** | 43 / 18 | 77 → 53 | 9.3 → 6.3% | **PASS** |
| (e) dist_hsv60 | −0.67 [−2.50, +1.17] | +2.00 [−2.17, +6.17] | −2.00 [−6.50, +2.67] | 75 / 87 | 77 → 85 | 9.3 → 9.8% | fail |

Other reported measures:
- **Race at δ 2.0:** (a) +8.0, (c) +13.3, (d) +8.0.
- **Pills to clear in games both builds won:** (a) −21.8, (c) −18.9, (d) −16.1.

**Reading:**
- **Three distance arms PASS the screen**, with the mechanism visible.
  - Stall pills per game fall 24–33.
  - "Endgame-stall" deaths roughly halve: 9.3 → 4.7–6.3% of games.
  - Wins get faster (−16 to −22 pills), and the race improves by +6 to +10 pp.
- **Not churn** (the stall-breaker test):
  - (a) fixes 48 base tap-outs and adds 12.
  - (d) fixes 43 and adds 18.
  - (c) churns more (91 / 64), because it also fires in mid-game stalls.
- **(a) and (d) are identical to ANTIBODY until the root has ≤ 4 viruses.**
  - tap≤100 Δ is exactly 0.
  - A replay check on 3 seeds: the first differing decision happens at root vcount = 4, or the games never
    diverge.
- **The two failures are instructive:**
  - **Row support (b)** is "finish-line"-shaped: it only credits support that has already reached the row, the same
    trap as setup and ACC35.
  - **HSV-region distance (e)**, always on, adds stall pills (+8) and nets zero. The walled-in M1-G3 anecdote does
    not generalise. Always-on shaping of mid-game viruses is the burial-price family again.
- **Caveat:** 5 arms were screened on one declared-reuse block, and all of this is sim-only. **Next, as
  pre-registered:** a powered confirmatory holdout on disjoint seeds, then the opponent suite and an RTL estimate.
