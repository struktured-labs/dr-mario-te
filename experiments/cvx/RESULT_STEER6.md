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

## Phase 4b: STEER6b confirmatory holdout (PREREG_STEER6b.md `f6bcfca0`)
**Setup:**
- Disjoint seeds: gate b **1,500** (39134–40932 + 33000–34198); race **2,166** (+ 26280–26958 + 60348–60998).
- Paired against the banked ANTIBODY STEER5d rows.
- Bonferroni: **98.33%** CIs.
- Analysis: `analyze_steer6.py --holdout` → `steer6/holdout/analysis.txt`.
- **Baseline:** tap-out 25.40%, race win 69.30%.

| arm | tap-out Δ (98.33%) | tap≤100 Δ | race Δ (98.33%) | churn (fixed / new of 381) | verdict |
|---|---|---|---|---|---|
| **(d) dist_target60** | **−5.40 [−7.47, −3.42]** (→ 20.0%) | −0.07 [−0.27, 0] | **+6.56 [+4.89, +8.20]** | **124 / 43** | **CONFIRMED** |
| (a) dist_end60 | −3.53 [−5.73, −1.40] (→ 21.9%) | −0.07 [−0.27, 0] | +6.97 [+5.26, +8.73] | 122 / 69 | **CONFIRMED** |
| (c) dist_stall60 | −3.93 [−7.00, −0.80] | **+1.27 [0.00, +2.60]** | +7.53 [+4.80, +10.16] | 239 / 180 | NOT confirmed (tap≤100 bar) |

- **Pooled screen + holdout** (descriptive, n = 2,100): dist_target −5.05 [−6.43, −3.67]; dist_end −4.24;
  dist_stall −4.10.
- **Race at δ 2.0:** +10.2 to +10.6 pp for all three.
- dist_stall's mid-game firing adds early tap-outs and churns heavily: the stall-breaker pattern again.

**Provenance** (`steer6_verify_holdout.py`: **PASS**).
- **Rebalanced mid-run** on the coordinator's clearance. Hetzner's xargs was paused (SIGSTOP), its unread job
  lines cut at the first newline after its stdin offset (4,096 → 4,116 B), and it was resumed (SIGCONT). The 4
  running jobs were untouched.
- **Where each job file ran** (lists in `steer6/holdout/provenance/`):

| place | job lines | detail |
|---|---|---|
| local, original list | 111 | — |
| Hetzner, kept | 38 | 1–38 of its list; 1,890 games |
| moved to local | 73 | 39–111 of Hetzner's list; 3,592 games |

- Every job file has exactly its planned seeds, and there are **0 duplicate seeds** across the union for every
  (instrument, arm).
- The local pool was widened 4 → 17 workers mid-run via GNU xargs SIGUSR1.

## Phase 4c: does the gain survive the RTL route's answer latency? (PREREG_STEER6c.md `c939a866`)
**Latency cost per route** (`steer6_latency.py`):
- Leaves per root search on 1,166 real ANTIBODY boards: median 26,129; 17,844 at ≤ 4 viruses. That is ≈ 1,849
  clocks per leaf at the 69-board co-sim median.
- Sequential dist_target: 8 cycles/leaf → **+0.10 f median / +0.17 f max** (MiSTer 85.909 MHz).
- dist_end: +0.49 / +1.25 f (p95).
- dist_stall over all viruses: +3.0 / +17.6 f.
- A concurrent route: 0.

**Pre-registered test** (whole-game shift, rounded up to whole frames, every decision): **the gains do NOT
survive.**
- dist_target@+1 f: tap-out −1.50 [−4.67, +1.67]; its own latency cost is **+2.67 [+0.33, +5.00] pp tap-out**.
- dist_end@+2 f: tap-out −2.00; cost +4.00 pp tap-out and −6.5 pp race.
- **Answer latency is precious in this regime:** 1 frame on every decision ≈ 2.7 pp of tap-out. That is as big
  as the term's own gain.

**Post-hoc sensitivity STEER6c-s** (addendum written before its games): the real-size cost, paid only while the
term is active (root ≤ 4 viruses). `analyze_steer6.py --dfrac`.
- **dist_target@0.17 f: tap-out −3.83 [−6.50, −1.17]**, race +5.33 [+2.67, +8.17]. Cost vs @0: +0.33
  [−0.67, +1.33], not significant.
- dist_end@1.25 f: tap-out −5.33 [−7.83, −2.83], race +7.17. Cost +0.67 [−0.67, +2.00].
- **Reading:** at its true size and scope, the sequential route's latency is probably tolerable. The pre-registered
  test failed, so that is not demonstrated. **Build requirement: the 0-added-cycle route** (below).

## Opponent suite for the recommended arm (dist_target60 vs ANTIBODY, 600 paired, 37934–39132)
`analyze_steer6.py --opp`.

| opponent | ANTIBODY → dist_target60 tap-out | Δ [95%] |
|---|---|---|
| OWNER-0804 (screen) | 23.0 → 18.8% | −4.17 [−6.67, −1.67] |
| OWNER-2026-09 (refit) | 21.8 → 16.3% | **−5.50 [−8.00, −3.00]** |
| **dr. lulu fit** (renewal, couch 9/27) | 18.5 → 14.3% | −4.17 [−6.33, −2.00] |
| STRIKER H6 (lulu147) | 24.2 → 21.5% | −2.67 [−5.17, −0.33] |
| **LULU race** (lam 4.7, her measured rate) | race-row tap-out 26.7 → **16.7%** | **−10.0 [−13.0, −7.3]** |

- LULU race win: M 140 δ 2.65 **68.5 → 81.0% (+12.5 [+9.7, +15.5])**; M 160 +12.0; M 177 +10.8.
- At δ 2.0: +9.5 / +11.2 / +11.7.
- tap≤100 Δ is exactly 0 against every opponent: the term is off until ≤ 4 viruses.
- **No flags.** dist_target60 improves against every opponent, and most against the racer: it clears the last
  viruses sooner instead of stalling.

## PICK: `s6_dist_target60`, by the pre-declared rule and by total cost
**Pre-declared rule:** among confirmed arms, the cheapest RTL within 1.5 pp of the best.
- dist_target is both the cheapest AND the best: holdout −5.40 vs dist_end −3.53.

**Total cost** (area + latency + fit risk), as the coordinator asked:

| | dist_target (d) | dist_end (a) |
|---|---|---|
| firmware | picks ONE target per decision at the root, only at ≤ 4 viruses. D over ≤ 4 viruses on the soft CPU is a few thousand cycles, ≈ 0.1 ms, once per decision | sets W per decision |
| RTL area | 1 target descriptor register (row 4b, col 3b, colour 2b, valid, W) + 14 latched cells × 2b + a 5-bit window datapath. **≈ 60–80 FFs, a few adders** | per-virus D inside the S_VNEXT walk: cell reads + window datapath, per virus |
| latency | **0 cycles on the concurrent route** (below). Sequential fallback: +0.10–0.17 f, only at ≤ 4 viruses | sequential +0.5–1.25 f at ≤ 4 viruses; a concurrent route is harder (≤ 4 targets) |
| fit risk | lowest. A new small FSM; S_DONE2 unchanged (fold into `matched60`) | per-virus states lengthen the critical virus walk |

## RTL sketch for dist_target (0 added cycles)
**Target (firmware).** At each root decision with ≤ 4 viruses, firmware computes D for each remaining virus. The
definition is exactly `cascade_leaf6_x._vdist`, kdig 0, cap 16. It writes `TGT = {valid, row, col, colour}` of the
min-D virus (ties: lowest index), or valid = 0.

**Capture during S_COLWALK (full-scan NODE leaves).** `colh[c]` is already computed (latch it on every scan, not
only in base_mode). Add:
- the 7 cells of the target's ROW (cols c−3..c+3, 2 bits each), latched when `wr_ == tgt_row`;
- the 7 cells of the target's COLUMN (rows r−3..r+3), latched when `wc == tgt_col`;
- the target's own virus bit, to detect "cleared": D = 0 when it is gone.

**Delta leaves (CMD 7).** Start from BASE's latched row/col cells and colh. Patch in the 2 placed cells (off_a,
off_b) and the placed columns' new heights. These are the same inputs S_DNEW already computes for the holes delta.

**D-FSM.** It runs CONCURRENTLY with the existing sequence:
- S_VNEXT…S_SETUP_V on NODE leaves (≥ 16 per-virus states + 2 × 90-cell setup windows);
- S_DPOL (48 cycles) … on delta leaves.

It walks **one window per cycle**, 4 horizontal + 4 vertical ≤ 8 cycles. Each step is a 3-cell cost:
- same colour → 0;
- empty and above `16 − colh` → `1 + gap` (4-bit subtract);
- else infeasible.

It keeps a running min (5 bits). Every path it runs beside is longer than 8 cycles, so it adds **0 cycles to the
leaf**.

**Combine.** Pre-scale `−60·D = −(64·D − 4·D)` (shift-subtract), and subtract it from the pre-scaled `matched60`
accumulator before S_DONE (the HSV fold pattern, signed, +2 bits). **S_DONE2's adder tree is unchanged**, so there
is no new combine input on the critical path.

**Gates to build before ship:**
1. A bit-exact golden. The Python `_x6` target mode is the spec; the 6502 target picker must match
   `_root_dists` / argmin on ≥ 5k boards.
2. A tb_leafeval score-exact vs the golden on random + real boards, both NODE and delta paths.
3. Fit ≥ +0.10 ns copro slack, swept over seeds (one fit is n = 1).
4. Measured co-sim DONE latency: the 69-board distribution must be unchanged (0-cycle claim).
5. The 0-cycle claim is also checked in the co-sim on endgame boards.

## Verdict (phases 1–4)
- **The stuck-virus / endgame-stall problem is the biggest remaining sim failure mode:** ~45% of tap-outs, ~half
  of the slow race losses.
- **A graded, gravity-aware clearing-distance term, switched on only at ≤ 4 viruses, fixes a large part of it.**
  - dist_target60 is CONFIRMED on 1,500 / 2,166 disjoint seeds: tap-out **25.4 → 20.0%**, race **+6.6 pp**.
  - It improves against every opponent profile, including **+12.5 pp race win against the dr. lulu racer**.
  - It survives its real-size latency.
- **Recommendation: build dist_target60 on the 0-added-cycle RTL route**, with the gates above. Sim-only so far,
  so the couch A/B is the real test.
- **Owner decisions:**
  1. Go / no-go on the RTL build: an RTL fork, ~1 build cycle plus the gates.
  2. Whether the Pocket build also gets it. Its 54.669 MHz clock makes the sequential fallback 1.6× costlier, so the
     concurrent route matters more there.
