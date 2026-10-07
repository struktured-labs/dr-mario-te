# RESULT (2026-10-07): STEER13, stall fixes under silicon-like execution and an honest price for MIN_THINK cuts

- **Pre-registration:** `PREREG_STEER13.md` (f81794cc), committed with 0 main rows.
- **Farm:** 25,200 games, audit OK, every job rc 0, on the never-analysed STEER11 block 41100–44298 (declared reuse).
- **Analysis:** `analyze_steer13.py` → `steer13/analysis.txt`; `steer13/extra.txt` holds the declared decomposition and
  pill counts.
- **Opponents:** at measured pace (dr. lulu M 167.5, the owner M 239.5).
- **Sample sizes:** LULU n = 1,600 paired, guards n = 600.

## Short answer
1. **A16 HELPS once execution is silicon-like** (4% random misses ≈ silicon's pill overhead).
   - LULU race +2.94 pp [+0.88, +5.06], Bonferroni [+0.62, +5.31], with no guard harm. **Verdict: RECOMMEND a couch
     test.**
   - The gain grows with execution noise: −1.2 at q 0 (STEER11 pilot), +0.75 at q 2% (n.s., n = 800), +2.94 at q 4%.
   - Mechanism: stall-pills from ≤ 16 viruses −3.7/game, games with a ≥ 30 s stall −5.1 pp, slow losses 399 → 356.
2. **R60 does not help:** +1.69 [Bonferroni −1.12, +4.50], n.s. It trades slow losses for kills again (kills 297 → 235,
   slow 399 → 434) and adds stalls. **NOT RECOMMENDED.**
3. **The anytime-commit model** reproduces the firmware's publish sequences exactly: 326/326 (1488), 331/331 (V11).
   **In it, today's cart (fw 1488, MIN_THINK 6 f) commits to a non-final answer on 33.6% of pills.**
   - DRLATEGUARD refuses 6.6% of pills, and 10.4% land off the final.
   - That alone reproduces silicon-scale execution overhead (+27.6 pills vs perfect execution), so part B needed no
     injected misses (q_B = 0).
4. **V11 firmware at the same 6 f gate is the big lever:** LULU loss **40.1% → 22.7%**, +17.4 pp
   [Bonferroni +14.2, +20.6]; owner race +5.2. ⚠ It is an UPPER BOUND, because the model's 1488 is slower than the couch
   (section 4).
5. **MIN_THINK cuts with V11:**
   - **−2 f (DRMINTHINK = 8): +1.88 [Bonferroni −0.81, +4.67], NOT WORTH IT by the pre-registered rule.**
     - The non-final commits cost it nothing: (v114 − v116) − (oracle4 − oracle6) = +0.06 pp [−2.6, +2.6], so 100% of
       the −2 f gain survives.
     - **The −2 f lever is just small** once tempo is charged as lock frames (+1.8 even with an instant final, vs
       STEER12's 1:1 upper-side +5.2).
     - It does cut gate-b tap-out −2.33 [Bonferroni −4.83, −0.11].
   - **−4 f (MIN_THINK 2 f): +4.75 [Bonferroni +1.88, +7.44], WORTH A COUCH TEST.** ⚠ This is optimistic by ≤ 0.5 f per
     pill: V11's first publish lands at GO + 2.6–2.9 f, the model says 2.3, and the gate waits for it.

## 1. Part A: A16 / R60 at silicon-like execution (q 4% random-root misses; FAIR at the same dose)

| arm | LULU loss (slow / kill) | Δ win vs FAIR [95%] {Bonferroni K = 2} | churn fixed / new | owner loss | gate-b tap-out | verdict |
|---|---|---|---|---|---|---|
| FAIR | **43.50%** (24.94 / 18.56) | — | — | 26.83% | 19.33% | — |
| **A16** | **40.56%** (22.25 / 18.31) | **+2.94 [+0.88, +5.06] {+0.62, +5.31}** | 176 / 129 | 26.00% (Δ +0.83) | 17.00% (Δ −2.33 {−5.83, +1.17}) | **HELPS, RECOMMEND** |
| R60 | 41.81% (27.12 / 14.69) | +1.69 [−0.75, +4.19] {−1.12, +4.50} | 222 / 195 | 26.17% | 17.67% | n.s., NOT RECOMMENDED |

**More, A16 / R60 − FAIR:**

| measure | A16 | R60 |
|---|---|---|
| LULU-race tap-out | −3.12 [−5.00, −1.12] | −2.62 |
| tap≤100 | 0.00 (4.17%) | 0.00 (4.17%) |
| q 2% sensitivity (n = 800) | +0.75 [−2.25, +3.62] | +0.50 |

**STALLS.** Definition: an act-stall is ≥ 10 consecutive decisions on which NO legal placement of the ACTUAL pill clears
any virus. LULU race, per game, truncated at her finish | untruncated:

| arm | stall-pills, v0 ≤ 16 | v0 ≤ 12 | v0 ≤ 8 | longest stall, v0 ≤ 16 | games with a stall ≥ 30 s |
|---|---|---|---|---|---|
| FAIR | 27.5 \| 43.0 | 24.9 | 19.9 | 32.1 s \| 49.1 s | 42.5% \| 45.8% |
| A16 | **23.9** \| 35.3 | 22.2 | 19.0 | **27.8 s** \| 41.7 s | **37.4%** \| 41.2% |
| R60 | 29.4 \| 48.7 | 26.8 | 21.2 | 33.6 s \| 56.5 s | 47.8% \| 51.6% |

- **A16 − FAIR:** stall-pills ≤ 16 **−3.66 [−5.16, −2.18]**; stall ≥ 30 s **−5.06 pp [−7.75, −2.38]**.
- **R60 − FAIR:** +1.88 [−0.04, +3.72]; stall ≥ 30 s **+5.25 pp [+2.38, +8.19]**.

**Reading:**
- **A16's gain is the STEER10 mechanism (fewer and shorter endgame stalls, fewer slow losses: 399 → 356), now large
  enough to see.** Its gain rises with execution noise: STEER11 pilot q 0 −1.23 → q 2% +0.75 → q 4% +2.94. This is the
  direction the coordinator's question anticipated, and it confirms STEER12's warning: stall fixes valued on
  near-perfect execution were under-valued.
- **Caveats:**
  - the cross-dose comparison mixes seeds and n, so treat it as suggestive;
  - the random-root miss model is harsh on kills (FAIR kill 18.6% at q 4%, while couch AI tap-outs are rare). Part A's
    ABSOLUTE levels are pessimistic. Its deltas are the result.

## 2. Part B: anytime commit + DRLATEGUARD (q_B = 0), MIN_THINK pricing
**The model** (`anytime13.py`, validated in `steer13/anytime_cal.txt`):
- The firmware publish rules are replayed on the faithful brain: 1488 in Pass-0 order; V11 with the DRROOTORD depth-2
  pre-pass, then descending d2.
- Timing is 1,645 clocks/leaf, fitted on 1488. **Out-of-sample on V11**, at-gate-final at GO + 2 / 4 / 6 / 8:
  5.7 / 86.4 / 91.5 / 93.1% (co-sim 4.5 / 85.2 / 90.9 / 92.4%).
- **The driver:** commits at GO + MT to the mailbox; later publishes are adopted under the cart's DRLATEGUARD rule.
- **Tempo:** lock-frame difference vs today's 1488 execution of the same pill.

| arm | LULU loss (slow / kill) | owner loss | gate-b tap-out | pills to clear (median) | time to clear | non-final commits | refused | landed on final | tempo vs today |
|---|---|---|---|---|---|---|---|---|---|
| **today: 1488, MT 6** | **40.12%** (36.06 / 4.06) | 16.50% | 5.83% | 140 | 252.1 s | 33.6% | 6.6% | 89.6% | 0 |
| V11, MT 6 | **22.69%** (16.69 / 6.00) | 11.33% | 5.67% | 120 | 215.2 s | 8.8% | 0.7% | 98.6% | −0.96 f/pill |
| V11, MT 4 (DRMINTHINK = 8) | 20.81% (16.00 / 4.81) | 10.50% | **3.33%** | 118 | 209.7 s | 15.9% | 1.1% | 98.2% | −2.35 |
| V11, MT 2 | **17.94%** (13.81 / 4.12) | 8.17% | 4.17% | 117 | 207.0 s | 22.9% | 1.5% | 97.8% | −3.11 |
| oracle, MT 6 | 20.75% | — | — | 118 | 212.0 s | 0 | 0 | 100% | |
| oracle, MT 4 | 18.94% | — | — | 117 | 206.1 s | 0 | 0 | 100% | |

**PRIMARY contrasts** (LULU M 167.5, Bonferroni K = 3; guards Bonferroni 6):

| contrast | Δ win [95%] {Bonferroni} | churn | gate-b tap-out Δ {Bonf} | owner race Δ {Bonf} | verdict |
|---|---|---|---|---|---|
| **V11 MT 6 − today** | **+17.44 [+14.69, +20.12] {+14.19, +20.62}** | 407 / 128 | −0.17 | **+5.17 {+0.50, +9.83}** | HELPS |
| V11 MT 4 − MT 6 (DRMINTHINK = 8) | +1.88 [−0.38, +4.19] {−0.81, +4.67} | 185 / 155 | **−2.33 {−4.83, −0.11}** | +0.83 | n.s., **NOT WORTH IT** |
| V11 MT 2 − MT 6 | **+4.75 [+2.50, +6.94] {+1.88, +7.44}** | 210 / 134 | −1.50 | +3.17 {−0.56, +7.00} | HELPS, **WORTH A COUCH TEST** |

**References and decomposition (LULU, 95%):**

| quantity | value |
|---|---|
| oracle4 − oracle6 (the −2 f lever with an instant final) | +1.81 [−0.38, +4.12] |
| oracle6 − today (today's non-final commits vs an instant final) | **+19.38 [+16.62, +22.00]** |
| non-final-commit penalty of MT 6 → MT 4 under V11 = (v114 − v116) − (orc4 − orc6) | **+0.06 [−2.56, +2.56]** |
| survival ratio (v114 − v116) / (orc4 − orc6) | 1.03 [−3.2, +6.2] (uninformative: small denominator) |
| V11 MT 6 − oracle MT 6 (V11's residual non-final-commit cost) | −1.94 [−3.75, −0.19] |

**Reading:**
- **V11 removes most of today's non-final commits** (33.6% → 8.8% of pills, refusals 6.6% → 0.7%) and with them most of
  the model's execution overhead (140 → 120 pills).
- **Under V11, cutting MIN_THINK adds non-final commits** (8.8 → 15.9 → 22.9%), but DRLATEGUARD adopts nearly all their
  late finals. The −2 f cut loses nothing to them (penalty +0.06).
- **What limits the −2 f cut is the lever itself.** Earlier commits lock only ~1.4 f/pill earlier (gravity-bound pills),
  worth +1.8 pp, below this n's resolution.
- **−4 f** (realised −2.15 f/pill, after waiting ~1 f for V11's first publish on most pills) is resolved at +4.75.

## 3. Verdicts
| question | verdict |
|---|---|
| A16 under silicon-like execution | **RECOMMEND a couch test** (HELPS, no guard harm; stalls and slow losses down) |
| R60 under silicon-like execution | **NOT RECOMMENDED** (n.s.; more stalls; it trades slow losses for kills) |
| DRMINTHINK = 8 (MIN_THINK −2 f) with V11 | **NOT WORTH IT on the primary** (+1.9, n.s.; zero commit penalty; the lever is small). It does lower gate-b tap-out −2.3 (Bonferroni). |
| MIN_THINK −4 f with V11 | **WORTH A COUCH TEST** (+4.75, Bonferroni-positive; ≤ 0.5 f/pill optimistic model bias) |
| V11 vs 1488 at 6 f | **HELPS, large** (+17.4 sim; an upper bound, see 4). V11 is the step before any MIN_THINK cut. |

## 4. Caveats, signed
- **Today's cart in the model is slower than the couch: an upper bound on V11's gain.** B_14886 needs 140 pills /
  252 s to clear (median).
  - The couch FAIR (1488) needed 120 pills / 209 s in its 4 clear games. Those were easier boards: brain-only 102 vs
    the sim's 111, i.e. couch-equivalent ≈ 129 pills.
  - So the model's 1488 non-final commits likely cost ~10 more pills than silicon's.
  - V11's +17.4 is an upper bound. Scaled by the overhead it removes (140 → 120 vs a likely ~129 → 120), something like
    half of it is the plausible size.
  - The model's 1488 landed on the final 89.6% vs the couch's 81.6% (faithful-brain MATCH). Silicon has additional,
    unmodelled miss sources and cheaper near-misses.
- **V11 MT 2 is optimistic by ≤ 0.5 f per pill.** The model's V11 first publish is ~0.5 f early (out-of-sample bias),
  and MT 2's commit waits for it.
- **The tempo model is lock-frame based** (more physical than STEER12's 1:1 commit shift). STEER12's lat_m2 +5.17 is the
  upper-side figure; oracle4 − oracle6 = +1.81 is this model's.
- **Not modelled:** tucks (none in the sim) and V11's TUCKREACH / TUCKLIVE effects.
- **Part A's miss model** (random root) is harsh on kills.
- **Sim-on-couch11 throughout;** the opponents are models at measured pace.

## Files (`experiments/cvx/`)
- **Anytime model:** `anytime13.py`, `steer13_anytime_cal.py` (→ `steer13/anytime_cal*.{txt,jsonl}`,
  `steer13/anytime_coef.json`).
- **Steering:** `steer_model.py` (`execute(sched=...)` + `_lateguard_ok`).
- **Runs:** `steer13_run.py`, `steer13_jobs.py`, `steer13_farm.sh`.
- **Gates:** `steer13_gate.sh`, `steer13_identity.py`.
- **Calibration:** `steer13_cal_read.py` → `steer13/cal/qb.txt`.
- **Analysis:** `analyze_steer13.py`.
- **Rows:** `steer13/main/` (25,200), `steer13/cal/`, `steer13/gate/`.
- **Outputs:** `steer13/analysis.txt`, `steer13/extra.txt`.
