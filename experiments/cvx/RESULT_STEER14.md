# RESULT (2026-10-11): STEER14, A16 x a slam-gate cut on V11 under the cart-faithful descent model

- **Pre-registration:** `PREREG_STEER14.md` (ae0e0853, committed with no `steer14/main/`), Addendum A (ddc19420) for the
  interrupted farm.
- **Farm:** 42,800 games, 856 jobs, audit OK (`STATUS: DONE`, 2026-10-11T00:44:57Z), no `GUARD_FAIL`, every row's jit
  guard == `064752972d064a89`.
- **Analysis:** `analyze_steer14.py` → `steer14/analysis.txt` (run once, by the `steer14-desk-autoreport` unit, after
  DONE; rc 0). Part R: `steer14/analysis_R.txt` (2026-10-09, before the interruption; the full run reproduces it).
- **Opponents at measured pace:** dr. lulu M 167.5 s, the owner M 239.5 s. All arms V11 firmware, MIN_THINK 6 f, q 0
  unless stated.
- **Everything here is a simulator result.** Seeds are a declared reuse (prereg sec. 4).

## Short answer
1. **STEER13's "V11 +17.44 pp vs dr. lulu" does not survive the corrected model: +0.06 pp [−2.31, +2.44]** on the same
   1,600 seeds. Once the descent waits for the cart's slam gate, the model no longer prices V11 as a race win over
   today's 1488 cart.
2. **(iii) The combined candidate (A16 + gate cut u8) vs today's FAIR2PLUS-equivalent: +11.82 pp
   [Bonferroni +10.20, +13.33], no guard harm. Verdict: CERTIFIED** (in the model). LULU loss 24.4 % → 12.6 %.
3. **(i), (ii) A16 ADDS VALUE at both gates:** +2.53 [Bonferroni +1.12, +3.92] at today's gate, +3.33
   [Bonferroni +2.16, +4.51] at u8. No guard harm.
4. **(iv) No interaction established:** +0.80 [Bonferroni −0.96, +2.57]; MDE 2.32 pp, so a smaller interaction is not
   excluded.
5. **Most of (iii) is the gate cut, not A16:** the gate cut alone is +8.49 [+7.25, +9.71] (reference, not a
   pre-registered contrast). It comes from the endgame: GO → lock on pills below 10 viruses 49.5 f → 31.6 f.
6. **The gain is all in slow losses; kills do not fall.** (iii): slow losses 939 → 287, kill losses 307 → 356
   (of 5,100).

## 1. Part R: STEER13's V11 vs 1488, re-derived (STEER13's own seeds; 95 %, no decision rule)

| endpoint | 1488 (`C13_14886`) | V11 (`C13_v116`) | Δ [95 %] | churn fixed / new |
|---|---|---|---|---|
| LULU race win (n 1,600) | 74.69 % | 74.75 % | **+0.06 [−2.31, +2.44]** | 193 / 192 |
| owner race win (n 600) | 88.00 % | 86.67 % | −1.33 [−4.67, +2.00] | 48 / 56 |
| gate-b tap-out (n 600) | 3.83 % | 5.83 % | +2.00 [−0.33, +4.33] | 19 / 31 |

- **STEER13's model, same seeds:** 59.88 % → 77.31 %, +17.44 [+14.69, +20.12].
- **Survival:** 0.00 of it [−0.14, +0.14]; corrected − STEER13 = −17.38 pp [−20.56, −14.00].
- **Why:** tempo vs today's cart was −0.96 f/pill for V11 in STEER13's model and is **+0.37 f/pill** in the corrected
  one. V11's DONE is later, and it is disarmed more often (9.0 % of pills vs 5.7 %).
- **What V11 still does in the model:** non-final commits 30.3 % → 8.9 %; landed on the final 95.9 % → 99.1 %
  (endgame 95.0 % → 98.4 %). Loss mix moves from slow to kill (slow 22.44 → 18.81 %, kill 2.88 → 6.44 %).
- **The model's 1488 vs the couch** (prereg sec. 6): median 122 pills, 220.6 s to clear, against the couch FAIR's 120
  pills / 209 s. STEER13's model had 140 pills.
- The owner-race and gate-b contrasts are not established in either direction (n 600).

## 2. Part M: the 2x2 (n 5,100 LULU; guards n 1,000)

**Absolute:**

| arm | LULU loss (slow / kill) | owner loss | gate-b tap-out | pills (median) | t_clear |
|---|---|---|---|---|---|
| `S14_d4_k32` (today's FAIR2PLUS-equivalent) | 24.43 % [23.27, 25.57] (18.41 / 6.02) | 11.00 % | 5.00 % | 119 | 216.3 s |
| `S14_d16_k32` (A16) | 21.90 % [20.76, 23.04] (15.63 / 6.27) | 8.60 % | 4.60 % | 118 | 215.5 s |
| `S14_d4_u8` (gate cut) | 15.94 % [14.96, 16.94] (9.61 / 6.33) | 8.90 % | 5.40 % | 116 | 187.9 s |
| `S14_d16_u8` (**combined**) | **12.61 %** [11.73, 13.55] (5.63 / 6.98) | 7.90 % | 4.40 % | 116 | 186.4 s |

**Primary contrasts** (LULU race win, paired by seed; Bonferroni K = 4) **and guards** (Bonferroni K = 6):

| | contrast | Δ win [95 %] | Bonferroni | churn fixed / new | gate-b tap-out Δ {Bonf} | owner race Δ {Bonf} | verdict |
|---|---|---|---|---|---|---|---|
| (i) | A16 at today's gate | +2.53 [+1.43, +3.63] | [+1.12, +3.92] | 469 / 340 | −0.40 {−2.23, +1.43} | +2.40 {+0.00, +4.90} | **A16 ADDS VALUE** |
| (ii) | A16 at u8 | +3.33 [+2.43, +4.25] | [+2.16, +4.51] | 363 / 193 | −1.00 {−2.80, +0.80} | +1.00 {−1.10, +3.13} | **A16 ADDS VALUE** |
| (iii) | combined vs today | **+11.82 [+10.53, +12.98]** | **[+10.20, +13.33]** | 856 / 253 | −0.60 {−2.50, +1.30} | +3.10 {+0.10, +6.10} | **CERTIFIED** |
| (iv) | (ii) − (i) | +0.80 [−0.59, +2.18] | [−0.96, +2.57] | — | — | — | none established (MDE 2.32 pp) |

- **Guards:** no harm on any contrast. Guard churn (fixed / new): gate-b tap-out 25 / 21, 29 / 19, 28 / 22; owner race
  56 / 32, 40 / 30, 78 / 47.
- **(iv) per-seed values:** {−2: 30, −1: 494, 0: 4,003, +1: 551, +2: 22}.
- **Reference, not pre-registered:** the gate cut alone (`S14_d4_u8` − `S14_d4_k32`) +8.49 [+7.25, +9.71], churn
  730 / 297.

**Loss types and tap-outs (descriptive):**

| contrast | slow losses (fixed / new) | kill losses (fixed / new) | LULU-race tap-out Δ [95 %] | gate-b tap ≤ 100 Δ [95 %] |
|---|---|---|---|---|
| (i) | 939 → 797 (456 / 314) | 307 → 320 (104 / 117) | −1.88 [−2.69, −1.10] | −0.20 [−0.60, +0.20] |
| (ii) | 490 → 287 (328 / 125) | 323 → 356 (123 / 156) | −1.98 [−2.78, −1.16] | −0.40 [−0.90, +0.10] |
| (iii) | 939 → 287 (784 / 132) | 307 → 356 (220 / 269) | −1.94 [−2.92, −0.90] | −0.30 [−0.80, +0.20] |

- Kill losses rise by 13 / 33 / 49 games of 5,100 while tap-outs fall: the arms are killed in games they would
  otherwise have lost slowly or won. No CI was pre-registered for the kill count; it is reported, not tested.

## 3. Stalls (LULU, per game; truncated at her finish | untruncated)

| arm | stall-pills v0 ≤ 16 | ≤ 12 | ≤ 8 | longest stall | games with a stall ≥ 30 s |
|---|---|---|---|---|---|
| `S14_d4_k32` | 21.1 \| 33.5 | 19.9 | 16.8 | 26.2 s \| 41.8 s | 33.4 % \| 36.2 % |
| `S14_d16_k32` | 18.2 \| 24.9 | 17.3 | 15.2 | 23.1 s \| 31.9 s | 30.3 % \| 33.4 % |
| `S14_d4_u8` | 24.0 \| 33.4 | 22.7 | 19.2 | 24.8 s \| 36.5 s | 25.2 % \| 26.0 % |
| `S14_d16_u8` | 19.1 \| 23.1 | 18.3 | 16.2 | 19.4 s \| 24.8 s | 20.9 % \| 21.8 % |

| contrast | stall-pills ≤ 16 (truncated) | longest stall | games with a stall ≥ 30 s |
|---|---|---|---|
| (i) | −2.92 [−3.69, −2.15] | −3.03 s [−4.04, −2.00] | −3.04 pp [−4.57, −1.55] |
| (ii) | −4.90 [−5.82, −4.00] | −5.41 s [−6.48, −4.35] | −4.22 pp [−5.55, −2.88] |
| (iii) | −1.93 [−2.91, −0.97] | −6.76 s [−7.91, −5.59] | −12.41 pp [−14.08, −10.80] |

- A16 removes stall-pills at both gates. The gate cut does not (truncated count 21.1 → 24.0 with DIST4, untruncated
  33.5 → 33.4), but stalls ≥ 30 s fall under it (33.4 % → 25.2 %).

## 4. Where the tempo goes: GO → lock, disarm, DOWN source

| arm | tempo vs today's cart (f/pill) | GO → lock, all pills (today's cart, same pills) | GO → lock, ENDGAME pills (today's cart) | endgame share of pills | disarmed (today's-cart ref) | DOWN via DONE / stability / none |
|---|---|---|---|---|---|---|
| `C13_14886` (1488) | +0.00 | 43.2 f (43.2) | 49.4 f (49.4) | 45.3 % | 5.7 % (5.7) | 48.4 / 49.9 / 1.7 % |
| `C13_v116` | +0.37 | 42.9 f (42.5) | 49.5 f (48.7) | 43.4 % | 9.0 % (5.9) | 49.9 / 48.2 / 1.9 % |
| `S14_d4_k32` | +0.37 | 43.0 f (42.6) | 49.5 f (48.7) | 43.9 % | 9.0 % (5.8) | 50.2 / 48.0 / 1.8 % |
| `S14_d16_k32` | +0.46 | 43.6 f (43.1) | 51.6 f (50.8) | 41.7 % | 9.5 % (6.3) | 49.1 / 49.3 / 1.6 % |
| `S14_d4_u8` | −9.39 | 33.1 f (42.5) | **31.6 f** (48.5) | 43.9 % | **17.1 %** (5.9) | 18.2 / 80.9 / 1.0 % |
| `S14_d16_u8` | −9.62 | 33.4 f (43.0) | **32.1 f** (50.8) | 40.7 % | **18.6 %** (6.4) | 19.2 / 79.9 / 0.9 % |

**Execution quality:**

| arm | non-final commits | late / pill | adopted | refused | landed on the final (endgame) | DIST target on |
|---|---|---|---|---|---|---|
| `S14_d4_k32` | 8.9 % | 0.098 | 0.093 | 0.005 | 99.0 % (98.3 %) | 21.1 % |
| `S14_d16_k32` | 8.1 % | 0.089 | 0.085 | 0.003 | 99.3 % (98.8 %) | 57.4 % |
| `S14_d4_u8` | 9.0 % | 0.097 | 0.091 | 0.007 | 98.7 % (97.8 %) | 20.1 % |
| `S14_d16_u8` | 8.0 % | 0.086 | 0.081 | 0.005 | 99.0 % (98.2 %) | 56.9 % |

- The gate cut roughly doubles the SLAM_ARM disarm rate (9 % → 17–19 %) and costs 0.3–0.6 pp of landed-on-final
  (endgame 0.5–0.6 pp). The tempo figures are net of both.
- Under u8, 80 % of pills start DOWN on the stability rule; under today's gate half wait for DONE.

## 5. Sensitivity: (iii) with q 2 % random-root misses (LULU, n 2,000, 95 %)

| | today (`S14_d4_k32_q02`) | combined (`S14_d16_u8_q02`) | Δ [95 %] | churn fixed / new |
|---|---|---|---|---|
| q 2 % | 64.55 % | 78.25 % | **+13.70 [+11.45, +15.90]** | 410 / 136 |
| q 0, same seeds | 75.05 % | 87.55 % | +12.50 [+10.55, +14.45] | 343 / 93 |

- Same sign as the primary; HELPS at 95 %. Realised miss rate 1.98 % in both arms; landed on the final 96.8 % in both.
- With misses, kill losses are 12.40 % vs 12.45 %: the whole gain is again in slow losses (23.05 → 9.30 %).

## 6. Part D: slam-gate dose-response (DIST4, LULU, first 600 seeds; descriptive, 95 %)

| config (KOPEN, KEND, VCEND) | LULU loss (slow / kill) | Δ win vs k32 [95 %] | churn | tempo f/pill | GO → lock all / endgame | landed on final (endgame) | disarmed |
|---|---|---|---|---|---|---|---|
| **k32** (32, 255, 10) today | 25.00 % (19.50 / 5.50) | — | — | +0.38 | 43.0 / 49.4 f | 99.0 % (98.4 %) | 8.8 % |
| k24 | 23.50 % (18.50 / 5.00) | +1.50 [−2.00, +5.00] | 61 / 52 | −0.56 | 42.0 / 49.2 | 99.0 (98.3) | 11.0 % |
| k16 | 21.50 % (16.50 / 5.00) | +3.50 [−0.33, +7.17] | 77 / 56 | −1.31 | 41.8 / 51.0 | 99.1 (98.6) | 13.4 % |
| k8 | 22.33 % (15.83 / 6.50) | +2.67 [−1.00, +6.17] | 71 / 55 | −1.59 | 40.9 / 49.2 | 98.9 (98.3) | 13.8 % |
| k4 | 22.33 % (15.83 / 6.50) | +2.67 [−1.00, +6.50] | 74 / 58 | −1.61 | 41.2 / 49.8 | 98.9 (98.3) | 14.1 % |
| e32 (32, 32, 10) | 19.83 % (14.00 / 5.83) | +5.17 [+2.83, +7.67] | 45 / 14 | −5.16 | 37.5 / 37.0 | 99.0 (98.2) | 10.4 % |
| e16 (32, 16, 10) | 17.00 % (10.33 / 6.67) | +8.00 [+5.50, +10.67] | 56 / 8 | −7.02 | 35.8 / 32.8 | 98.9 (98.0) | 12.1 % |
| v4 (32, 255, 4) | 20.83 % (15.00 / 5.83) | +4.17 [+1.67, +6.67] | 43 / 18 | −2.97 | 39.8 / 42.2 | 99.0 (98.3) | 9.7 % |
| u16 (16, 16, 10) | 15.33 % (9.67 / 5.67) | +9.67 [+6.00, +13.17] | 93 / 35 | −8.83 | 33.9 / 32.7 | 98.7 (97.8) | 16.2 % |
| **u8** (8, 8, 10) | 17.33 % (10.67 / 6.67) | +7.67 [+4.33, +11.17] | 84 / 38 | −9.36 | 33.2 / 31.6 | 98.7 (97.8) | 17.2 % |

- The endgame cuts carry the effect: e16 alone is +8.00 with only 8 newly lost games. The KOPEN-only cuts
  (k24 … k4) are not established at this n (±~4.5 pp).
- On these 600 seeds u16 scores above u8 (+9.67 vs +7.67); the intervals overlap heavily and part D is not a test.
  G\* = u8 was fixed by the execution-only stage-1 rule before any race outcome existed, and is not revisited here.

## 7. The interrupted farm (Addendum A, and the check it owed)
- **Timeline:** paused by `PAUSE_ALL` 2026-10-09 04:31:31 EDT; the workstation went down hard at 05:22:37 EDT with
  the pause still held; relaunched 2026-10-10 12:14 EDT (16:14:06Z); a stale `PAUSE_ALL` from 10/9 held the workers
  for the first ~50 s and was removed by the coordinator; DONE 2026-10-11T00:44:57Z.
- **Banked before:** 412 / 856 jobs, all structurally valid. **Discarded unread and re-run:** 10 in-flight jobs
  (326 partial rows). **Run after:** those 10 + 434 never-started jobs.
- **Re-run check: PASS.** All 326 discarded partial rows equal the re-run rows on every key outside the `rig` stamp
  (`tmp/steer14/restart/redo_equal.py`). Inside the stamp only `git` and `numba_cache` differ.
- **Final audit** (`tmp/steer14/restart/audit_files.py`): 856 / 856 files with 50 valid rows, right arm and seed, no NUL
  byte. Two stamp sets, differing only in the numba root (`nb14_20261008T234430Z` / `nb14_20261010T161406Z`) and the
  git stamp (a834a9db / ddc19420; ddc19420 is the addendum commit, a document-only change). The `steer14_run.py` and
  `steer_model.py` shas are identical across all 42,800 rows.
- No main-farm outcome was read before DONE; between launch and DONE only `--status` and the structure audits ran.
- **Process failure, disclosed:** the lane's completion poll did not resume it at DONE; the analysis had already been
  written by the unit at 00:50Z, and this result was written about 14 h later. Nothing was read or decided in between.

## 8. Caveats (signed)
- **Simulator only, and the model has just been shown to move a headline by 17 pp.** Part R is the reminder: the same
  contrast was +17.44 under one descent model and +0.06 under the corrected one. (iii) depends on the slam-gate, DONE
  and SLAM_ARM models being right about a cart that does not exist yet.
- **The u8 cut is untested on a cart.** The model validation (prereg sec. 2.2) is on today's flags (KOPEN 32,
  KEND 255). Under u8, 80 % of pills descend on the stability rule and non-final slams become routine; the model
  prices that at 0.3–0.6 pp of landed-on-final. The cart's real cost of an early endgame slam (tucks, PRESTART and
  pre-commit rotation are not modelled) is unknown. A cart build and chained replays come before any couch claim.
- **Silicon vs model on V11:** part R says the model sees no race gain from V11 over 1488. That does not contradict
  the silicon capture (tall-endgame landing ≠ final 24 % → 3.3 %): the model's 1488 lands on the final 95.9 % of the
  time, so it has little of that defect to remove. The model may under-state 1488's execution misses.
- **Kills do not improve.** Every gain is in slow losses. Against a faster or harder-hitting opponent the kill floor
  (~6–7 % vs dr. lulu at q 0, ~12 % at q 2 %) is untouched by A16 and by the gate cut.
- **(iv)** is under-powered below ~2.3 pp; "none established" is not "no interaction" (Rule 13).
- **Part D** is n 600 per configuration, descriptive; its KOPEN-only rows are not established (Rule 19: no direction
  stated).
- **Seeds are a declared reuse** (prereg sec. 4): not independent confirmation of anything measured on those streams.
  Part R deliberately uses STEER13's own seeds.
- **The commit timing** is STEER13's latency sampler (GO median 7 model frames vs the replay cart's f2), common to all
  arms.
- **Owner-race guard for (i) and (iii)** has a Bonferroni lower bound at +0.00 / +0.10: no harm, and not a certified
  gain either (it is a guard, tested one-sided for harm).

## 9. Files
- `steer14/analysis.txt`, `steer14/analysis_R.txt`; rows `steer14/main/` (856 files, 42,800 rows).
- Restart tooling and the discarded partial rows: `tmp/steer14/restart/` (untracked).
