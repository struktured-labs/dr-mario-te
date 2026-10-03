# RESULT (2026-10-03): STEER7 — what is a FASTER answer worth? (PREREG_STEER7.md `3b39e296`)

**Setup:**
- **Brain:** `s6_dist_target60` (ANTIBODY + dist_target60, the couch build) under the STEER6d measured endgame
  latency, shifted by S frames on every decision.
- **What a shift moves:** the steer answer frame, the mask T_LAT, race tempo, and the gate-(b) clock (`steer7_dlat.py`).
- **Cells:** gate (b) OWNER-0804; race lam 6, M 177, δ 2.65; LULU race lam 4.7, M 140.
- **Seeds:** declared-reuse. Block A = the STEER6 screen block. Block B is used for the primary only.
- **Scale:** 13,200 games, local, 12 workers.
- **Analysis:** `analyze_steer7.py` → `steer7/analysis.txt`.

**Integrity:**
- **Identity:** S = 0 reproduces the banked STEER6d rows on every key — gb 600/600, rc6 600/600, rc47 600/600.
- **Completion audit:** 13,200/13,200 rows.
- **Activity counters (rule 26):** the realised answer frame moves by +0.98 / −1.01 / −2.01 / −3.95 / −16.22 f per
  decision for +1 / −1 / −2 / −4 / ceil.
  - The mask T_LAT moves with it.
  - The steer clamp binds on 0.1–0.4% of decisions at −1/−2 f and 3.6% at −4 f. The tempo over-credit is
    0.076 f/decision at −4 f.
  - The ceiling clamps every decision by construction.

## PRIMARY (pre-registered): FAIL
S = −1 f vs S = 0, n = 1,200 paired:

| endpoint | S = 0 → S = −1 | Δ [95% CI] | churn (fixed / new) |
|---|---|---|---|
| gate-(b) tap-out | 19.58 → 19.33% | **−0.25 [−1.84, +1.42]** | 53 / 50 |
| race | 75.50 → 77.42% | +1.92 [−0.92, +4.83] | 168 / 145 |
| tap≤100 | | −0.08 [−0.83, +0.67] | |

- The tap-out CI does not exclude 0, so the bar fails.
- **The −1 f effect is not the mirror of STEER6c's +1 f cost.** The CI excludes −2.67.
- Block A and block B agree: +0.00 and −0.50.

## WORTH-PER-FRAME CURVE (block A, n = 600 paired vs S = 0)

| arm | realised Δframes | gate-(b) tap-out Δ [95%] | fix/new | race M177 Δ [95%] | fix/new | LULU M140 Δ [95%] | fix/new | race-row tap-out Δ |
|---|---|---|---|---|---|---|---|---|
| +1 | +1.00 | **+2.83 [+0.33, +5.33]** | 22/39 | −2.00 [−6.33, +2.50] | 83/95 | −2.50 [−6.00, +1.00] | 50/65 | +1.00 |
| 0 | 0 | 18.67% (base) | — | 74.00% (base) | — | 81.00% (base) | — | 0 |
| −1 | −0.99 | +0.00 [−2.17, +2.17] | 22/22 | +3.50 [−0.50, +7.33] | 87/66 | +0.67 [−3.00, +4.33] | 64/60 | −3.50 |
| −2 | −1.99 | −1.67 [−4.33, +1.00] | 38/28 | **+5.17 [+1.00, +9.50]** | 100/69 | +0.33 [−3.33, +4.00] | 65/63 | −5.17 |
| −4 | −3.94 | **−4.17 [−7.17, −1.17]** (Bonferroni [−8.00, −0.33]) | 55/30 | **+10.00 [+6.00, +14.00]** | 110/50 | +4.33 [+0.33, +8.50] | 88/62 | −10.17 |
| **ceiling** | −16.22 | **−14.33 [−17.50, −11.33]**: 18.7 → **4.3%** | 94/8 | **+22.83 [+19.17, +26.50]**: 74 → 96.8% | 148/11 | **+17.00 [+13.83, +20.33]** | 108/6 | −24.50 |

**Slope** (OLS over arm means, joint seed bootstrap; pp per +1 frame of latency):

| endpoint | all arms +1..−4 | faster side 0..−4 |
|---|---|---|
| gate-(b) tap-out | +1.30 [+0.66, +1.94] | **+1.12 [+0.36, +1.89]** |
| race | −2.42 [−3.14, −1.64] | **−2.42 [−3.38, −1.43]** |
| LULU | −1.20 | −1.07 |

**Symmetry:** Δ(+1) + Δ(−1) = +2.83 [−0.83, +6.50] tap-out. That is suggestive of a steeper slowing cost, but the CI
spans 0, so the asymmetry is not established at n = 600.

**Reading:**
- **Faster IS worth tap-outs, about 1.1 pp per frame on the faster side, and about 2.4 pp of race per frame.**
- **One frame is below the resolution of the pre-registered test.**
  - The prereg was powered (89%) for the symmetric −2.67, but the faster side runs at about −1.1 per frame.
  - At n = 1,200 the −1 f arm had ~25% power at that size.
  - So the FAIL means "−1 f alone is not detectable", NOT "speed does not matter".
- **The lever is real at larger sizes:**
  - −4 f gives −4.2 pp tap-out (Bonferroni-significant) and +10 race.
  - The ceiling (answer at spawn) takes gate-(b) tap-out from 18.7% to **4.3%** and race win to 96.8%.
- **Caveat on mechanism:** each arm moves all four latency channels together (answer frame, mask, race tempo,
  gate-b clock), as STEER6c did. The curve does NOT separate "act sooner" from "play faster".

## SECONDARY (added after the prereg: the couch tracker bug): see the addendum
Gate (b) on owner_fit_202610, and the LULU race at lam 2.56, for S = 0/−1/−2. Results are in
`steer7/analysis_refit.txt` (pending; queued in `steer7b_farm.sh`).

## PART 2 (desk): where could frames come from? → `RESULT_STEER7_DESK.md`
- **The silicon answer frame is set by DRIVER constants:** ~1.5 f edge + **7.5 f settle** (`DELAY2` = 15 hooks; it
  was designed as ~3 f) + **6 f MIN_THINK** (12 hooks) = the f15 no-rotation mode.
- **The search DONE lands ~26 f after the commit gate.**
- **At the gate the running best is the final answer only 66% of the time** (60% in the endgame).

**Pricing the candidate levers with this curve** (the faster-side slope ≈ 1.1 pp tap-out and 2.4 pp race per frame;
−4 f measured −4.2 pp; ceiling −14.3 pp):

| lever | frames | sim-priced worth | risk |
|---|---|---|---|
| 1. settle cut, `DELAY2` 15 → ~3 hooks | −6 f on every searched decision (GO and DONE move too) | **≈ −6 pp tap-out, ≈ +14 race.** Interpolated between the −4 f and ceiling arms. | low–medium; RAM-trace the spawn edge first |
| 2. clear-window prestart (GO at the lock of a clearing placement) | ≈ ceiling on the ~35–40% of placements that clear (54 f idle window > ~32 f search) | **≈ −5 to −7 pp** by linear weighting. Not tested per placement class. | medium–high |
| 3. 6502 / engine overlap | −6 f on DONE (−20% clocks) | not separable here: it moves endgame slams (tempo) and the final-at-gate rate, not the first action | medium (RTL) |
| 4. two-pass root ordering (depth-2 key) | 0 f; final-at-gate 66 → 89% (endgame 60 → 84%) | **unpriced:** the sim acts on FINAL answers only | low (firmware) |
| 5. ply-3 pruning, topk2 8 → 4 | −14 f on DONE | needs a brain A/B (quality) | high |

**Follow-ups this points to (none built):**
- **(a) Model the driver's anytime commit in the sim.** Commit to the running best at the gate, using
  `steer7_anytime.py`'s trajectory. That would price lever 4 and the 34% non-final commits.
- **(b) Separate the channels.** Shift only the steer answer frame + mask, vs only the tempo + clock, to see whether
  the ceiling's −14 pp is "act sooner" or "play faster".
- **(c) A Mesen RAM trace of the spawn edge.** This is the one check that gates lever 1.
