# RESULT (2026-10-06): STEER10: the AI's endgame stalls vs dr. lulu. All 4 arms FAIL; DIST at ≤ 16 viruses is a near-miss

- **Pre-registration:** `PREREG_STEER10.md`, commit `b6194e29`, written before any farm game (the commit records 0
  row files).
- **Rows:** `steer10/`. The farm (`steer10_farm.sh`) ran 13,200 games; audit OK (264 × 50); every job rc 0. It ran
  under the steer10-throttle PAUSE switch, through 6 shared PAUSE_ALL windows.
- **Analyzer:** `analyze_steer10.py` → `steer10/analysis.txt`.
- **Baseline FAIR** = STEER8b `fD_bdepD`. Its faithful-brain rows:
  - NEW `s10_base` on lulu10b;
  - banked gb10 rows (steer8 + steer9 `s9_base`) and banked rc10 rows.
  - Identity gate: 9/9 byte-identical.

## Short answer
1. **The couch edge stalls are REACH losses.**
   - An edge column holding viruses, or its neighbour, grows to height 13–15. The shipping reach mask then never
     offers that edge column again.
   - In 3 of the 4 games examined (M1 G4, M2 G3, M5 G2), own placements did most of the raising. In M1 G4 and M2 G3
     those were mostly brain choices; in M5 G2 they were mixed brain and execution.
   - In M1 G2 it was HER garbage on column 1.
2. **No arm passes** the pre-registered bar, which needs the LULU race lower CI > 0 at Bonferroni 99.375%.
3. **`s10_A16` is a near-miss: DIST60's dist_target term switched on at ≤ 16 viruses instead of ≤ 4.**
   - LULU race (pace prior): **+1.35 pp**, 95% CI [+0.02, +2.71], Bonferroni [−0.38, +3.06].
   - Neither guard shows harm.
   - The mechanism is visible:

     | measure (LULU race, per game) | change |
     |---|---|
     | stall-pills from ≤ 16 viruses | **−7.0** [−10.1, −4.1] |
     | longest stall | −6.3 s |
     | edge-column stuck-virus decisions | −42 |
     | LULU race tap-out | **−1.83 pp** [−3.08, −0.58] |
     | slow race losses at M 100–140 | −13 to −15 games |

   - Rule 13: this FAIL is **underpowered, not negative**.
4. **The edge-reach rule (new family d) fails, and the sim reverses what the replays predicted.**
   - It cuts tap-out (kill) losses but SLOWS the AI: slow race losses rise, stall-pills rise and edge stuck-virus
     decisions rise.
   - At P 120 that costs −4.75 pp at M 80, and stall-pills from ≤ 16 viruses go up by **+6.75**.
5. **Sim vs couch pace:** the sim clears in a median 147 s, the couch AI in 209 s (its clear games).
   - **78% of that gap is seconds per pill, not pills.**
   - The biggest single piece is the time around her garbage, which the race clock never charges: +40 s per game.
   - Charging it drops FAIR's simulated LULU win from 87.0% to **75.1%**.

## 1. Mechanism check (before any game; PREREG §3, `steer10/mech_check.txt`)
**Inputs and instrument check:**
- Boards: the banked per-AI-pill cases of all 9 lulu 10/05 games plus 10/04 M5 G2, the latter regenerated through the same
  `m4g2_fair_20261004.cases` path.
- `S10Decider` with the empty rule reproduces the banked brain-only replays **345/345**.
- It matches the faithful brain's choice on **1,446/1,446** boards.

**Reach losses.** A vertical col 0 / col 7 placement leaves the `reach_fw_tap` mask once the edge column or its
neighbour reaches the threshold height:

| pill | height that blocks it |
|---|---|
| 0 | 15 |
| 50–100 | 14 |
| 150 | 13 |
| 200+ | 12–13 |

On every stall board checked, the stuck edge column was out of the mask.

| game | edge column lost (holding viruses) | at pill | viruses left | how |
|---|---|---|---|---|
| M1 G2 (her win, stall at 7) | col 0 (9 viruses) | p57 | 15 | col 1 → 14 by HER garbage |
| M1 G4 (her win, stall at 16) | col 0 / col 7 | p74 / p93 | 23 / 17 | own + garbage |
| M2 G3 (her win, stall at 13) | col 7 / col 0 | p35 / p71 | 38 / 16 | own: 27 of 34 raising placements were brain choices |
| M5 G2 (owner win) | col 7 | p15 | 41 | col 6 → 14 (3 brain, 4 execution) |

**Grid:** 21 variants. Brain-only replays (observed capsules + garbage, perfect execution) from 383 starts, plus a decision
pass over 1,446 boards. Column guide:
- **her-win games:** M1 G2, M1 G4, M2 G3 and M5 G2 (225 starts);
- **AI-win games:** the AI's 6 wins (158 starts);
- **fixed / new:** starts that flip to an AI win / from an AI win, over all games;
- **raises avoided:** of the base brain's 16 moves that lift an edge side into the reach-loss band;
- **dig cost Δ:** negative means the variant digs more than base.

| variant | her-win games: AI wins / 225 | AI-win games: AI loses / 158 | fixed / new | raises avoided /16 | dig cost Δ |
|---|---|---|---|---|---|
| base DIST60 | 19 | 22 | – | – | – |
| A vk 8 / 12 / **16** | 20 / 22 / **23** | 17 / 13 / **12** | 15/5, 23/5, **27/5** | 0 / 0 / 2 | 0 / −5 / −5 |
| A vk 12, W 120; edge-first target vk 16 / 48; kdig 3 | 23; 13 / 16; 17 | 16; 15 / 16; 16 | 27/12; 22/17, 32/24; 14/13 | 0–5 | −11 to +9 |
| (b) eseal P 150 / 400 | 11 / 10 | 24 / 21 | 9/12, 10/18 | 1 | 0 |
| (c) edig P 60 at vk 12 / 16; P 120 at vk 16; all columns | 18 / 18 / 10 / 11 | 19 / 14 / 10 / 12 | 4/9, 12/8, 20/17, 16/23 | 1–2 | −32 to −63 |
| **(d) ereach P 60 / 120, h0 11** | 16 / 16 | 10 / 9 | **18/7, 25/8** | **11 / 14** | **−16 / −10** |
| (d) ereach P 120 h0 10; P 60 h0 12; P 250 h0 11 | 7; 21; 16 | 8; 10; 3 | 25/19; 15/2; 27/11 | 14; 7; 14 | −9; −8; −3 |
| **A16 + ereach P 120** / A16 + ereach P 60 | 19 / 21 | **2** / 5 | **34/9** / 33/10 | 14 / 11 | −14 / −20 |

**Reading, declared in the prereg:**
- No rule rescues her two structural wins in replay.
  - M1 G2 is walled by her garbage, and a brain rule cannot undo that.
  - M2 G3's edges were out of reach by p35 / p71.
- The rules move the precarious AI wins (M1 G1) and M1 G4.
- **(b) eseal** acts but hurts (the STEER9 pattern).
- **(c) edig** acts on decisions but its outcomes churn, because the digs are outside the mask.
- Neither (b) nor (c) was screened.

## 2. Arms (PREREG §4; K = 4, Bonferroni 99.375%)

| arm | rule | why |
|---|---|---|
| `s10_A16` | (a) dist_target gate vk 4 → 16 (W 60, min-D target) | vk 16 dominates 8 / 12 |
| `s10_R60` | (d) ereach P 60, h0 11 | the dose that best keeps digs (dig cost −16) |
| `s10_R120` | (d) ereach P 120, h0 11 | avoids 14 of 16 raises and still digs more than base |
| `s10_A16R120` | (a) + (d) | best replay harm profile; a combined build needs its own certificate |

## 3. Results (paired vs FAIR; seed bootstrap 4,000)
**What the cells are:**
- **Primary:** lulu10b LULU race win averaged over the pace prior M ∈ {80, 100, 120, 140} s. Fit lulu_fit_202610b: lam
  2.84, sizes 83/7/10. δ 2.65, n = 1,200.
- **Guards:** gb10 tap-out (n = 1,200) and rc10 owner race at M 177 (n = 600). Harm means the Bonferroni CI excludes 0 on
  the bad side.
- FAIR levels: LULU win **87.00%** (loss 13.00%), gb10 tap-out **6.17%**, owner race **93.50%**.

| arm | **PRIMARY LULU win Δ** [95%] {Bonf} | gb10 tap-out Δ {Bonf} (churn fixed/new) | rc10 owner race Δ {Bonf} (churn fixed/new) | verdict |
|---|---|---|---|---|
| **s10_A16** | **+1.35 [+0.02, +2.71] {−0.38, +3.06}** | +0.42 {−1.58, +2.17} (37/42) | −1.33 {−3.50, +0.67} (9/17) | **FAIL**: underpowered near-miss; no harm |
| s10_R60 | +0.29 [−1.50, +2.08] {−1.90, +2.62} | −0.92 {−2.92, +1.17} (53/42) | −0.50 {−3.67, +2.50} (26/29) | FAIL (null) |
| s10_R120 | −1.46 [−3.48, +0.56] {−4.12, +1.23} | −0.50 {−2.58, +1.67} (55/49) | −0.50 {−3.67, +2.67} (26/29) | FAIL (worse races) |
| s10_A16R120 | +0.19 [−1.77, +2.17] {−2.31, +2.79} | −1.25 {−3.42, +0.92} (62/47) | +2.17 [+0.17, +4.33] {−0.50, +4.83} (27/14) | FAIL |

**LULU win at each M** (Δ [95%], churn fixed/new):

| arm | M 80 | M 100 | M 120 | M 140 |
|---|---|---|---|---|
| FAIR level | 78.00% | 87.83% | 90.58% | 91.58% |
| s10_A16 | +0.58 [−1.67, +2.67] 87/80 | +1.58 [−0.08, +3.25] 60/41 | +1.50 [+0.00, +2.92] 48/30 | **+1.75 [+0.42, +3.08]** 44/23 |
| s10_R60 | −1.08 109/122 | −0.08 86/87 | +1.08 76/63 | +1.25 69/54 |
| s10_R120 | **−4.75 [−7.50, −2.00]** 117/174 | −1.33 98/114 | −0.17 85/87 | +0.42 79/74 |
| s10_A16R120 | **−3.67 [−6.42, −0.92]** 129/173 | +0.25 101/98 | +2.08 [+0.08, +4.17] 90/65 | +2.08 [+0.17, +4.08] 84/59 |

**Declared secondaries:**

| arm | garbage-time-charged LULU win (FAIR 75.06%) | M 100 δ 2.0 | M 140 δ 2.0 | LULU race tap-out (FAIR 8.00%) | gb10 tap≤100 |
|---|---|---|---|---|---|
| s10_A16 | +0.42 [−1.00, +1.83] | +1.08 | **+2.42 [+0.83, +4.00]** | **−1.83 [−3.08, −0.58]** (40/18) | **+0.50 [+0.17, +0.92]** |
| s10_R60 | −0.56 | −1.58 | −0.17 | −1.08 (66/53) | +0.00 |
| s10_R120 | **−4.40 [−6.42, −2.33]** | **−6.75** | −1.17 | −0.92 (76/65) | −0.17 |
| s10_A16R120 | **−2.92 [−4.92, −0.90]** | **−4.83** | +1.50 | **−2.08 [−4.00, −0.17]** (80/55) | −0.08 |

**Stalls (LULU race, per game; FAIR level → arm, Δ [95%]):**

| arm | stall-pills, act ≥ 10, from ≤ 16 viruses (FAIR 24.9) | longest stall, s (23.9) | edge-virus structural-stuck decisions (689) | games with a stall ≥ 36 s (13.2%) |
|---|---|---|---|---|
| s10_A16 | **−7.00 [−10.08, −4.13]** | **−6.29 [−9.66, −3.04]** | **−42 [−56, −30]** | 10.2% |
| s10_R60 | +2.07 [−1.74, +5.84] | +0.74 | +16 [−6, +37] | 15.8% |
| s10_R120 | **+6.75 [+2.23, +11.13]** | +3.92 | **+55 [+29, +81]** | 18.2% |
| s10_A16R120 | −3.39 [−7.37, +0.37] | −3.73 | −4 | 12.9% |

- Stalls starting at ≤ 4 viruses are unchanged by every arm (DIST60 already owns that range).
- gb10 and rc10 show the same direction, smaller: A16's gb10 stall-pills from ≤ 16 are −3.55 and edge-stuck −24; R120's
  are +4.06 and +36.

**Activity (rule 26):**
- **s10_A16:** the DIST term is on at 55–58% of decisions (FAIR 20–22%); its target differs from DIST60's on 33%. Its
  root rule is off by design, so `changed` = 0.
- **ereach arms:** they penalise roots unequally on 54–61% of decisions and change the chosen root on 1.6–1.8% (P 60) and
  2.9–3.1% (P 120). That clears the interpretability floor; these arms RAN.

**Post-hoc (declared, not the bar; `steer10_posthoc.py` → `steer10/posthoc_losstype.txt`): LULU losses by type** (FAIR →
arm, fixed / new). "Slow" means the AI was alive but slower; "kill" means it topped out first.

| arm | M 80 slow | M 80 kill | M 140 slow | M 140 kill |
|---|---|---|---|---|
| s10_A16 | 220 → 212 (80/76) | 44 → 45 | **31 → 18** (19/9) | **70 → 62** (25/14) |
| s10_R60 | 220 → 247 | 44 → 30 | 31 → 31 | 70 → 55 |
| s10_R120 | **220 → 292** (94/160) | **44 → 29** | 31 → 48 | **70 → 48** |
| s10_A16R120 | 220 → 274 | 44 → 34 | 31 → 17 | 70 → 59 |

**Reading:**
1. **A16 shortens the stalls the couch showed.**
   - Stall-pills from ≤ 16 viruses −28%, longest stall −6 s, edge stuck −6%.
   - Slow losses fall at M 100–140, and LULU-race tap-outs fall.
   - The gain shrinks to zero at M 80. A very fast racer is not stopped by fewer stalls: the AI's whole-game tempo is the
     binding constraint there.
   - It FAILS on power. The pre-registered half-width (≈ 1.7 pp at its realised churn) is about the size of the effect.
   - Watch items:
     - gb10 tap≤100 +0.50 pp (6 more early tap-outs in 1,200). The term turns on in early games that reach 16 viruses
       fast.
     - Owner race −1.33 (n.s.).
2. **ereach trades tempo for survival, and the trade is negative against her.**
   - It removes kill losses: −15 to −22 at M 140.
   - It adds slow losses, much more at fast M: +27 to +72 at M 80.
   - It raises the stall measures it was meant to cut.
   - The replays on the couch boards did not show this. They use fixed capsules and garbage and no steering, and on 1–3%
     of decisions the cost appears later in the game.
   - The *mechanism* (why keeping the sides low makes edge viruses stay stuck longer) is **not tested here**. A plausible
     reading is that the penalty taxes the vertical builds that clear an edge virus as well as the walls. It is an
     untested aside; don't act on it.
3. **The combination inherits both effects and nets to zero.** It looks better against slow opponents: owner race
   +2.17 [+0.17, +4.33] at 95% (not at Bonferroni), and tap-out −1.25 (n.s.).

## 4. Sim vs couch pace gap (coordinator's question; `steer10_pacegap.py` → `steer10/pacegap.txt`, `pacegap_lulu10b_base.txt`)
**Inputs:**
- Banked rows only, no new games.
- Couch: the 10/05 AI seat. Silicon, ANTIBODY_DIST_FAIR, hidden-spawn tracker per pill. Its 4 clear games are M1 G5,
  M2 G1, M2 G2 and M2 G4.
- Sim: FAIR in the LULU race, the new `s10_base` lulu10b rows (lam 2.84). The banked lam 2.56 rows give the same picture
  within 2 s.

| | couch (4 AI clears) | sim FAIR (1,104 clears) |
|---|---|---|
| time to clear p25/50/75 (s) | 186 / **209** / 239 | 129 / **147** / 175 |
| pills to clear | 105 / **120** / 137 | 96 / **111** / 133 |
| seconds per pill | **1.74** | **1.33** (80 f/pill) |
| stall-pills (act ≥ 10) | 0 / 0 / 15 (M2 G1: 60) | 0 / 10 / 22 |
| garbage cells received | 22.5 / 25.5 / 27 per game (5.6–8.7/min) | 10 / 14.5 / 20 per game (6.1/min) |

**Decomposition: 209 / 147 = 1.42 = pills 1.08 × seconds per pill 1.31.** By log share, **pills 22%, seconds per pill
78%.**

**Pills (+9 median).**
- Silicon needed 107 / 148 / 133 / 97 pills.
- The brain-only perfect-execution replay of the SAME capsules and garbage needed 103 / 101 / 110 / 76 (median 102).
- So **execution costs ≈ 22 pills per game** (median per-game difference).
- The sim's 111 already includes the steering model's own execution losses. The couch clear games were also easier
  boards than the sim median: brain-only 102 vs the sim's 111.
- Endgame stalls are absent from 3 of the 4 couch CLEAR games. They decide the games she wins (201 / 59 / 36 s), which
  are not in this sample.

**Seconds.** The same couch pills were re-timed with the sim's race clock (39 + 2 × max(0, 15 − hmax) + 40 × runs
frames; garbage costs 0).

| couch pill kind | couch (s/game) | sim clock (s/game) | excess (s/game) | share of excess |
|---|---|---|---|---|
| no clear, no garbage after | 70.8 | 54.2 | +16.6 | 23% |
| clearing pill | 86.1 | 70.4 | +15.7 | 22% |
| **garbage landed after it** | **55.9** | **15.5** | **+40.5** | **56%** |
| total | 212.8 | 140.0 | **+72.8** | |

- Per-pill medians on the couch: plain 1.0 s, 1-step clear 1.8 s, 2+-step clear 2.6 s, **garbage-followed 4.4 s**.
- The vs_race clock gives garbage drops no time at all. That is the largest single miss.
- Couch boards under perfect execution AND the sim clock would clear in ≈ 119 s.

**What this means for "zero losses" claims:**
- Sim race levels against her are optimistic.
  - FAIR's LULU win is 87.0% on the pace prior. Charging +3.2 s per received volley (the couch median) drops it to
    **75.1%**.
  - The couch result was 6/9 (67%).
- The race endpoint should charge garbage-handling time, and probably the measured plain-pill and clear-animation time,
  before any absolute claim.
- Relative comparisons between brains survive only if the arms receive similar garbage. Watch arms that change sends or
  the game length: every arm's garbage-charged Δ is below its raw Δ, by 0.9 pp (A16, R60) up to 2.9–3.1 pp (R120,
  A16R120).

## 5. PASS / FAIL and implementation cost
- **PASS: none.** All four arms FAIL the pre-registered bar.
  - `s10_A16`: underpowered near-miss, no demonstrated harm.
  - `s10_R60`: null.
  - `s10_R120`: worse races (M 80 and garbage-charged significant).
  - `s10_A16R120`: null on the primary.
- **Costs** (PREREG §8; moot for a ship decision, priced for the near-miss).
  - **`s10_A16`:**
    - one constant in the firmware DIST gate (vk 4 → 16);
    - the 6502 target pick runs over ≤ 16 viruses: ≈ 45k cycles, serial before the search;
    - latency ≈ **+0.03 f** MiSTer / +0.05 f Pocket, only at ≤ 16 viruses, ≈ +0.03–0.08 pp tap-out by the STEER6c slope;
    - **no RTL change** (the 0-cycle DIST FSM is target-agnostic; kdig stays 0);
    - risk: a full Quartus fit and its timing lottery.
  - **ereach:** about 0.5–1k cycles per root, overlapped with the copro ≈ 0 f; firmware only. Moot.
- **If the near-miss is pursued** (coordinator / owner decision; named here before any follow-up):
  - There are no fresh seeds; the registry is exhausted.
  - Options:
    - a larger declared-reuse block for a Bonferroni-free single-arm test of +1.35 pp: SE 0.69 pp at n = 1,200 means
      n ≈ 2,400 for 80% power or ≈ 3,300 for 90%;
    - or a couch A/B of A16 on the FAIR cart with the firmware gate constant changed.
  - Its cheap firmware form makes the couch A/B practical.
  - The gb10 tap≤100 +0.5 pp and the M 80 null should be watched.

## Files (`experiments/cvx/`)
- **Code:**
  - rules and mechanism check: `rules_steer10.py`, `steer10_mech.py`, `steer10_mech.sh`, `steer10_mech_report.py`;
  - harness and farm: `steer10_run.py`, `steer10_farm.sh`, `steer10_gate.sh`, `steer10_smoke.sh`;
  - analysis: `steer10_identity.py`, `analyze_steer10.py`, `steer10_pacegap.py`, `steer10_posthoc.py`.
- **Rows:** `steer10/{lulu10b,gb10,rc10}_*.jsonl`, `steer10/gate/`, `steer10/mech/`. The latter holds the replays and
  decisions of 23 variants and `cases_ai_m5g2_fair_20261004.jsonl`.
- **Reports:** `steer10/mech_check.txt`, `steer10/analysis.txt`, `steer10/pacegap.txt` (lam 2.56 FAIR rows),
  `steer10/pacegap_lulu10b_base.txt`, `steer10/posthoc_losstype.txt`.
- **Shared box:** throttle `dr_mario_rl/tmp/steer10/throttle.sh` (PAUSE / PAUSE_ALL, cap 8, desk-analysis priority),
  desk runner `dr_mario_rl/tmp/steer10/desk.sh`. Seed-registry REUSE notes were added to the 36734–40932 and 33000
  entries.
