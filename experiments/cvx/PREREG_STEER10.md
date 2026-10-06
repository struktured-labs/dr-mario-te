# PREREG (2026-10-06): STEER10 — the AI's ENDGAME STALLS vs dr. lulu: edge-column reach, earlier targeting, digging

Written and committed BEFORE any STEER10 farm game. At commit time `steer10/` holds no `lulu10b_* / gb10_* / rc10_*`
row files: only `steer10/mech/` (the mechanism check on banked couch boards) and `steer10/gate/` (identity gate rows).
The commit message records the count.

## 1. Why
Couch forensics 10/05 (`couch_forensics/RESULT_LULU_20261005.md`), dr. lulu vs ANTIBODY_DIST_FAIR, the AI won 6–3:
- the AI wins on opening pace (25.6 vs 13.3 viruses/min while > 30 remain);
- **all 3 of her wins were AI ENDGAME STALLS** on viruses in the EDGE columns 0 / 7 (201 s at 7, 59 s at 16, 36 s at
  13); she is the faster player at ≤ 12 viruses (4.9 vs 4.1/min);
- brain-only perfect-execution replays beat her from only 16 of 187 starts in her wins ⇒ BRAIN / structure, not
  execution. The 10/04 M5 G2 loss to the owner (cols 6–7) is the same shape.
**Already tried and failed (not repeated):** STEER9 "don't seal a live column" (harmful at every dose), STEER6e
"combos off near the end", the stall breaker; STEER6's dist_stall (early tap-outs, churn).

## 2. Candidate rules (`rules_steer10.py`; all on the silicon-faithful brain; empty rule == DIST60 exactly)
- **(a) earlier targeting** — DIST60's dist_target (W 60, one target = the min-D virus, kdig 0) switched on at
  root vcount ≤ vk with vk raised from 4. Firmware-side target pick; the RTL DIST FSM is unchanged.
- **(b) edge hygiene ("eseal")** — root penalty P × (edge-column viruses LIVE on the root and SEALED on the soft b1),
  only while root vcount > 12 (the opening). STEER9's SEALV restricted to columns 0 / 7.
- **(c) edge dig ("edig")** — at root vcount ≤ vk_dig, for each edge column whose top virus is SEALED on the root,
  root penalty P × the column's vertical DIG COST on the soft b1 (cap cells above the virus parsed into same-colour
  runs: Σ(4 − min(L,3)) over runs + (3 − Lm) for the run sitting on the virus when it matches it).
- **(d) edge reach ("ereach")** — NEW, from the mechanism check (§3): for each side (col 0 + col 1; col 7 + col 6)
  whose EDGE column holds a virus on the root, root penalty P × max(0, max height of the side's two columns on the
  soft b1 − h0). Always on.
All root penalties go through `seal_steer9._choose_fw_seal` (STEER9's gated mechanical copy of braingap `_choose_fw`,
value-identical at pen = 0), subtracted after DRVETO with its 16-bit saturation, computed on the firmware's own SOFT
b1 (the board the 6502 already builds for the eh terms).

## 3. Mechanism check (before any game; `steer10_mech.py`, `steer10_mech_report.py` → `steer10/mech_check.txt`)
**Boards.** The banked per-AI-pill cases of all 9 lulu 10/05 games (`couch_forensics/cases_ai_<g>_lulu_20261005.jsonl`)
plus 10/04 M5 G2 (`steer10/mech/cases_ai_m5g2_fair_20261004.jsonl`, generated with the same `m4g2_fair_20261004.cases`
code path; `cases_stall_m5g2` has no boards). Base = the silicon-faithful brain (`Leaf6FwDecider`, all fw switches,
DIST60, deployed mask at the pill index).

**Instrument checks.** `S10Decider` with the empty rule reproduces every banked brain-only replay
(`replay_*_lulu_20261005.jsonl`) byte-identically: 345/345 starts over the 9 games; and equals the banked faithful-brain
choice on 1,446/1,446 observed boards.

### 3.1 The mechanism: the couch edge stalls are REACH losses
Measured on `reach_fw_tap.reach_mask_fw` (the shipping driver mask): a vertical placement in column 0 (7) leaves the
mask once column 0 (7) or its neighbour 1 (6) reaches **height 15 at pill 0, 14 at pills 50–100, 13 at pill 150,
12–13 at 200+**. On every stall board checked the stuck edge column was OUT of the mask (M1 G4 p97/p110/p130, M2 G3
p96/p105/p117, M1 G2 p61–p150).

| game | edge column lost (with viruses) | at pill | viruses left | how |
|---|---|---|---|---|
| M1 G2 (her win, stall 7) | col 0 (9 viruses) | p57 | 15 | col 1 → 14 by HER garbage (all 7 height-raising events at ≥ 10 were garbage) |
| M1 G4 (her win, stall 16) | col 0; col 7 | p74; p93 | 23; 17 | own + garbage |
| M2 G3 (her win, stall 13) | col 7; col 0 | p35; p71 | 38; 16 | own (27 of 34 raising placements were brain choices, silicon == brain) |
| M5 G2 (owner win) | col 7 | p15 | 41 | col 6 → 14 (3 brain, 4 execution) |

- Own placements that raised an edge side to ≥ 11 while its edge column held viruses were mostly BRAIN choices:
  M2 G3 27/34, M1 G4 12/13, M1 G1 15/18 (silicon == faithful brain).
- Consequence for (c): the dig moves are outside the mask. On sealed-edge stall boards a root with a lower dig cost
  than base's choice existed on 5/49 boards (M1 G4), 1/5 (M2 G3), 0/51 (M5 G2), 0 (M1 G2: col 0 live but unreachable).
- Consequence for (a): DIST switches on (≤ 8–16 viruses) after the reach loss in most of these games.
- In the sim (banked FAIR lulu10 rows), edge columns 0/7 hold **52%** of the structurally stuck virus-decisions in
  episodes starting at ≤ 16 viruses (uniform would be 25%), so a sim screen can see the mechanism.

### 3.2 Grid (anecdote-tuned on these boards: DECLARED). `steer10/mech_check.txt`
Brain-only replays (observed capsules + observed garbage, perfect execution) from the banked start grid (345 lulu starts
+ 38 M5 G2 starts), classified as `replaysum_lulu_20261005` (AI-WIN / AI-LOSS / OPEN). Decisions: every observed board.

| variant | her-win games (M1 G2, M1 G4, M2 G3, M5 G2): AI wins from /225 | AI-win games (6): AI LOSES from /158 | starts fixed / new (all) | M1 G4 starts ahead of her 3 at p145 | decisions changed /1,446 | reach-loss raises (base 16): avoided | edge dig cost Δ (sum) |
|---|---|---|---|---|---|---|---|
| base (DIST60) | 19 | 22 | – | 5 | – | – | – |
| A_vk8 | 20 | 17 | 15 / 5 | 18 | 68 | 0 | +0 |
| A_vk12 | 22 | 13 | 23 / 5 | 12 | 87 | 0 | −5 |
| **A_vk16** | 23 | 12 | **27 / 5** | **22** | 106 | 2 | −5 |
| A_vk12_W120 | 23 | 16 | 27 / 12 | 4 | 120 | 1 | +9 |
| AE_vk16 (edge-first target) | 13 | 15 | 22 / 17 | 17 | 47 | 2 | +0 |
| AE_vk48 | 16 | 16 | 32 / 24 | 25 | 100 | 5 | −11 |
| AK_vk12_kdig3 | 17 | 16 | 14 / 13 | 10 | 38 | 0 | −4 |
| B_eseal150 (opening, edge seals) | 11 | 24 | 9 / 12 | 28 | 23 | 1 | +0 |
| B_eseal400 | 10 | 21 | 10 / 18 | 21 | 32 | 1 | +0 |
| C_edig60_vk12 | 18 | 19 | 4 / 9 | 2 | 12 | 1 | −32 |
| C_edig60_vk16 | 18 | 14 | 12 / 8 | 9 | 20 | 2 | −48 |
| C_edig120_vk16 | 10 | 10 | 20 / 17 | 9 | 28 | 2 | −63 |
| C_edig60_vk16_all | 11 | 12 | 16 / 23 | 8 | 62 | 2 | −39 |
| **D_reach60_h11** | 16 | 10 | **18 / 7** | 5 | 34 | **11** | **−16** |
| **D_reach120_h11** | 16 | 9 | **25 / 8** | 7 | 49 | **14** | **−10** |
| D_reach120_h10 | 7 | 8 | 25 / 19 | 14 | 77 | 14 | −9 |
| D_reach60_h12 | 21 | 10 | 15 / 2 | 5 | 17 | 7 | −8 |
| D_reach250_h11 | 16 | 3 | 27 / 11 | 0 | 70 | 14 | −3 |
| **AD_vk16_reach120_h11** | 19 | **2** | **34 / 9** | 14 | 151 | 14 | −14 |
| AD_vk16_reach60_h11 | 21 | 5 | 33 / 10 | 16 | 135 | 11 | −20 |

(eseal: base's choice newly seals an edge virus on 49 boards; B keeps 23 / 32 of them open, A_vk16 5, D 3–5.)

**Reading (declared before any sim game):**
1. **No rule rescues her two structural wins in replay.** M1 G2 (col 0 walled by her garbage on col 1) stays at
   1–8 / 44 and M2 G3 at 0–6 / 27 for every variant. A brain rule cannot undo a garbage wall, and M2 G3's edges were
   already out of reach by p35 / p71. The anecdotes that motivated STEER10 are, like STEER9's, mostly not fixable
   per-game; the screen tests the GENERAL hypothesis that keeping edges reachable / targeting earlier wins races.
2. **What the rules do move:** the precarious AI wins (M1 G1: base loses from 17/43 perfect-execution starts; A_vk16
   7, D_reach120 6, AD 1) and M1 G4 (A_vk16 leaves the replays at a median 6 viruses at p145 vs 12; 22 starts ahead
   of her 3 vs 5).
3. **(b) eseal acts but hurts** (keeps 23–32 seals open; replays fixed 9–10 / new 12–18; fewer wins in her games):
   the STEER9 pattern again. **Not screened.**
4. **(c) edig acts on decisions** (digs more: dig cost −32 to −63) **but the outcomes churn** (fixed ≈ new; vk16 /
   P120 / all-columns break M1 G4's 9 winning starts): the digs are mostly outside the mask (§3.1). **Not screened.**
5. **(d) ereach avoids 11–14 of the base brain's 16 reach-loss raises.** At P 60–120 (h0 11) the edge dig cost still
   FALLS vs base (−16 / −10: the excavation credit offsets the setup penalty); at P 250 the dig gain erodes to −3 and
   new losses rise (11); h0 10 breaks M1 G4 / M2 G3 (new 19); h0 12 barely acts (7 avoided, 17 changes).
6. **(a):** vk 16 dominates vk 8 / 12 (27 / 5 fixed / new); W 120, edge-first targets and kdig 3 add churn.
7. **(a)+(d) combined** has the best harm profile (AI-win-game losses 22 → 2; fixed 34 / new 9).

## 4. Arms (all = FAIR + one rule; chosen from §3 by fixed / new counts in her wins vs harm in the AI's wins)
| arm | rule (`steer10_run.RULE_ARMS`) | why (from §3.2) |
|---|---|---|
| **`s10_A16`** | (a) dist_target gate vk 4 → **16** (W 60, min-D target, kdig 0) | the requested family; vk 16 dominates 8 / 12 (fixed / new 27 / 5; M1 G4 ahead-of-her 22 vs 5); W 120 / edge-first / kdig add churn |
| **`s10_R60`** | (d) ereach **P 60**, h0 11 | the dig-preserving dose: edge dig cost falls most vs base (−16), avoids 11/16 reach-loss raises, fixed / new 18 / 7 |
| **`s10_R120`** | (d) ereach **P 120**, h0 11 | avoids 14/16 raises and still digs more than base (−10); fixed / new 25 / 8. P 250 (dig gain eroded to −3, new 11) and h0 10 (new 19) are excluded per the "do not block digs" criterion |
| **`s10_A16R120`** | (a) + (d): vk 16 AND ereach P 120 h0 11 | best harm profile (AI-win-game losses 22 → 2; fixed / new 34 / 9); a ship candidate would be the combination, and combined flags need their own certificate (memory `dr-mario-combo-pairing-hazard`) |

- **Not screened:** (b) eseal and (c) edig: they change decisions but their replay outcomes are net harmful (b) or churn
  (c) (§3.2 items 3–4). Edge-first targets (AE), kdig 3 (AK) and W 120 likewise.
- **K = 4 ⇒ Bonferroni 99.375% two-sided** on every bar CI.
- **Activity counters** in every row (rule 26): `dec`, `fired` (some root penalised with unequal pens), `changed` (the
  chosen root ≠ the target-only argmax on the same board), `tgt_on` (DIST term active), `tgt_diff` (target ≠ DIST60's).
  Note: for `s10_A16` the root rule is off, so its `changed` is 0 by construction; its activity is `tgt_on` / `tgt_diff`.

## 5. Design (declared REUSE everywhere)
- **Baseline = FAIR** = STEER8b arm `fD_bdepD`:
  - the silicon-faithful brain: `Leaf6FwDecider`, every fw switch on (hang = 1, ehb1 = 1, ehnp = 1, veto, wrap,
    order), dist_target W60 vk4 (DIST60);
  - fair DRSETTLE: G0 −5 / round-start −4, answer −6, tempo −6;
  - PROPH-first fix D at f11;
  - the DEPLOYED fw mask T19 / G0 8.
- **Harness REUSED:** `steer10_run.py` is `steer9_run.make` (= `steer8_run.make("fD_bdepD")` verbatim) except the
  decider class: `rules_steer10.S10Decider` (= `Leaf6FwDecider` + one STEER10 rule). The root penalties go through
  `seal_steer9._choose_fw_seal` (STEER9's gated mechanical copy of braingap `_choose_fw`, value-identical at pen = 0).
  Game loops: `stuck_probe.play_gb` / `play_race`; opponents: `refit_opp`.

### Cells and fits

| cell | instrument | fit | n per arm (paired) | FAIR rows |
|---|---|---|---|---|
| **lulu10b** (PRIMARY) | vs_race LULU race, lam **2.84**, volley sizes **83 / 7 / 10 %** (2 / 3 / 4 cells) | `couch_forensics/lulu_fit_202610b.json` (11 games; rate and size_hist, renormalised over 2–4: 112 / 9 / 14 of 135) | **1,200** | NEW `s10_base` rows (the old lulu10 rows are lam 2.56 + Hartford sizes) |
| **gb10** (guard) | gate (b) vs `owner202610` | `owner_fit_202610.json` (Owner202609 class) | **1,200** | banked `steer8/gb10_fD_bdepD_*` (39134–40332) + `steer9/gb10_s9_base_*` (the other 600; identity-gated byte-identical to fD_bdepD in STEER9) |
| **rc10** (guard) | vs_race owner race, lam **2.36**, Hartford sizes, **M 177, δ 2.65** | owner_fit_202610 rate | **600** | banked `steer8/rc10_fD_bdepD_*` |

- **Sizes plumbing:** `vs_race._volleys` maps one uniform draw per volley to a size through `vs_race.SIZES`. The run
  script sets `SIZES` per cell. Volley times and colours (the CRN stream, keyed by seed and lam) are unchanged.
  `hartford` == vs_race's own constant, so the rc10 instrument is STEER6r–9's exactly (identity gate below).
- **The LULU pace (M) and the pace prior — why the primary averages over M.** On the banked FAIR lulu10 rows
  (lam 2.56) the sim AI clears in a median **149 s** (p25 128, p75 177) and sends **41.5 tiles/game**; on the couch
  (10/05) FAIR needed a median **209 s** in the 4 games it cleared (and ≈ 265 s at its whole-game virus pace of
  10.9/min). The sim AI is 1.4–1.8× faster than silicon (decomposed in `steer10_pacegap.py` → `steer10/pacegap.txt`,
  reported as its own section of the result). At the standing LULU pace **M 140** the sim race is close to a
  survival test:

  | M (s), δ 2.65 | FAIR win | slow loss | kill (tap-out) loss |
  |---|---|---|---|
  | 60 | 56.3% | 42.0% | 1.7% |
  | 80 | 80.8% | 16.3% | 2.8% |
  | 100 | 89.8% | 5.8% | 4.3% |
  | 120 | 91.5% | 3.5% | 5.0% |
  | 140 | 92.2% | 2.5% | 5.3% |
  | 177 | 92.8% | 1.3% | 5.8% |

  On the couch her wins were 2 slow (endgame stalls) + 1 kill, and the AI won 6/9 (67%). Near M 80–100 the sim
  race has the couch's shape (close races, slow losses ≥ kills); at M 140 a stall can only cost a game by killing
  the AI. Her true sim-equivalent pace is not identifiable from 11 games (the sim-vs-silicon tempo gap is the
  confound), so the PRIMARY averages over a declared **pace prior M ∈ {80, 100, 120, 140} s** (equal weights),
  spanning the couch-shaped races (80) to the standing convention (140). Each M is reported separately.
  This choice was made on the banked lulu10 FAIR rows (lam 2.56), before any STEER10 game.

### Seeds (REUSE declared; the registry is exhausted, `--check` FAILS every block)

| cell | seeds | jobs |
|---|---|---|
| lulu10b | 39134–40332 + 40334–40932 + 33000–33598 (step 2; = STEER9's gb10 block) | 24 × 50 |
| gb10 | the same 1,200 | 24 × 50 |
| rc10 | 39134–40332 | 12 × 50 |

- These blocks were used by STEER5d / OPP1 / STEER6b / 6r / 7 / 8 / 9. No STEER10 design choice used these sim seeds:
  the rules and doses were shaped on the couch boards only (§3), and the M prior on banked FAIR rows (levels only).
- Registry note appended to the 36734–40932 and 33000 entries' REUSE text at commit time.

## 6. Endpoints and the BAR (per arm vs FAIR, paired, seed bootstrap 4,000; Bonferroni over the K arms of §4). `analyze_steer10.py`; churn (fixed / new) printed beside every Δ.

**PRIMARY: LULU race WIN, pace-prior averaged** (lulu10b): per seed, the mean over M ∈ {80, 100, 120, 140} of the
`vs_race.evaluate` win indicator at δ 2.65 (σ 0.15; the same per-seed pace quantile at every M). Reported as win
and as the LOSS rate (100 − win).

**GUARDS (no demonstrated harm):**
- gb10 **tap-out** Δ: HARM iff its Bonferroni **lower** CI > 0.
- rc10 **owner race win** (M 177, δ 2.65) Δ: HARM iff its Bonferroni **upper** CI < 0.

**PASS iff** primary Δ Bonferroni **lower CI > 0** AND no tap-out harm AND no owner-race harm.

**Declared secondaries (reported, never the bar):**
- **Garbage-time-charged LULU race** (from the pace-gap analysis, `steer10_pacegap.py`, before any STEER10 game: on
  the couch a pill followed by her garbage takes 4.4 s median vs 1.0 s for a plain pill, ≈ +3.2 s per received volley
  that the vs_race clock does not charge the AI): the pace-prior win with the AI's finish time shifted by +3.2 s per
  received release (≈ tiles_recv / 2.27, the 202610b mean release size). Approximate (the volley timeline is not
  re-simulated); reported per arm beside the primary.
- LULU race win at each M (with churn); M 100 / 140 at δ 2.0; lulu10b tap-out (how == topout).
- gb10 tap≤100 (opening harm).
- **Stalls, per cell:** act-stall pills (board-level, ≥ 10) that START at ≤ 16 viruses (the couch stalls started at
  7–16) and at ≤ 4 (STEER6e); the **longest stall** per game in pills and in sim seconds; the share of games with a
  stall ≥ 36 s (every one of her wins had one); edge-column (0/7) STRUCTURAL stuck-virus decisions.
- Activity counters (rule 26).

**NULL AUDIT** (memory `pass-condition-vs-null-outcomes`, done before the data):
- A neutral arm fails the primary (as it should) and passes each guard with probability ≈ 1 − 0.00625/2 per guard:
  the guards never reject on an outcome the null predicts.
- The guards are "no demonstrated harm", not non-inferiority. At n = 1,200 gb10 the tap-out guard catches a true
  harm of ≈ +2 pp about half the time (discordance ~9%, SE ≈ 0.85 pp, Bonferroni half-width ≈ 2.3 pp). A passing arm's
  point estimates and CIs are printed and a pass is a SCREEN pass (confirmation on fresh blocks is not possible: the
  seed space is exhausted; the couch A/B is the confirmation).
- Power (primary), from banked FAIR-vs-arm pairs scored on the pace prior (lam 2.56 rows; STEER8b/9 arms): per-seed
  Δ sd 0.11 (a near-identical arm) to 0.43 (a heavily changed one) ⇒ SE 0.32–1.23 pp at n = 1,200 ⇒ Bonferroni
  half-width ≈ 0.9–3.4 pp. Base average loss ≈ 11% over the prior, so the screen detects a cut of roughly a tenth to
  a third of the LULU losses depending on churn; smaller true effects FAIL as underpowered (rule 13: report as such,
  not as negative).

**Interpretation rules:** rule 26 (an arm with 0 changed decisions is UNRUN), rule 13 (a FAIL with CIs spanning 0
is underpowered), and the stall-breaker lesson (fixed / new beside every net Δ).

## 7. Gates done before this commit
1. **Identity:** `s10_base` (`steer10_run.py`, empty rule) == the banked FAIR `fD_bdepD` rows, **9/9** (gb10 / rc10 /
   lulu10 × 3 seeds 39134–39138), every non-stamp key byte-identical (`steer10_identity.py`, rows in `steer10/gate/`).
2. **Mechanism instrument:** `S10Decider` (empty rule) reproduces the banked brain-only replays 345/345 and the banked
   faithful-brain choice on 1,446/1,446 couch boards (§3).
3. **SIZES override:** with `SIZES = lulu202610b` the volley TIMES and COLOURS are identical to the hartford stream
   (seed 39134, lam 2.84), and the size frequencies over 600 seeds are 2: 0.830 / 3: 0.067 / 4: 0.103 (hartford
   0.730 / 0.170 / 0.099).
4. **Smoke + activity** (seed 36734/36736, outside the analysis blocks, NOT analysed): every arm runs in lulu10b and
   gb10; `s10_A16` DIST term on at 35–150 decisions per game (target differs from DIST60's on 20–56); the ereach
   arms penalise unequal roots on 31–132 decisions per game and change the root on 1–3; the combination does both.
5. **Analyzer selftest:** `analyze_steer10.py --selftest` PASS (8 cases incl. "no demonstrated harm" with a CI
   spanning 0 must PASS; 5 mutants killed: LULU on the mean, LULU on the upper CI, tap guard dropped, tap guard as
   non-inferiority at 0, race guard dropped).
6. **Farm dry run:** 264 jobs × 50 = **13,200 games** (lulu10b s10_base 1,200; per arm lulu10b 1,200 + gb10 1,200 +
   rc10 600).
7. The pace prior (§5) was chosen on banked FAIR lulu10 rows (lam 2.56, levels only) before any STEER10 game.

## 8. Implementation cost (for any arm that passes; NOT built here)
**Context** (as STEER9 §8): the te firmware 6502 runs at the copro clock (85.909 MHz MiSTer / 54.669 Pocket); a
search is ~26k leaves × ~1,849 clocks (≈ 26 f); DIST60's root target pick is ≈ 11k cycles median at ≤ 4 viruses
(≤ 0.19 ms). Latency prices (memory `dr-mario-answer-latency-is-worth-tapouts`): +1 f on every decision ≈ +2.7 pp
tap-out (STEER6c); the faster-side slope is ≈ 1.1 pp/f (STEER7).

| arm | firmware work | answer latency | RTL |
|---|---|---|---|
| **A: dist_target gate vk 4 → 16** | one constant in the DRDIST root gate (`dist_6502.py`); the target pick (`_vdist` over every virus, argmin) runs over ≤ 16 viruses instead of ≤ 4: ≈ 4 × 11k ≈ 45k cycles median, SERIAL before the search (the leaf FSM needs TGT latched) | ≈ 0.5 ms ≈ **+0.03 f** MiSTer / +0.05 f Pocket, only at ≤ 16 viruses ⇒ ≈ +0.03–0.08 pp tap-out (STEER6c slope), inside noise | **none** (the 0-cycle DIST FSM is target-agnostic; kdig stays 0) |
| **D: ereach (P, h0 11)** | per allowed root, on the soft b1 the 6502 already builds for the eh terms: 2 sides × 2 column-top scans (≤ 64 cell reads) ≈ 0.5–1k cycles/root ≈ 15–30k cycles/decision; a 16-bit saturating subtract like DRVETO | done in the root loop while the copro runs that root's ply 2–3 (as the eh terms): **≈ 0 f**; serial worst case ≈ 0.35 ms ≈ 0.02 f | **none** |
| combination A + D | both of the above | ≈ +0.03 f (A's serial pick) | none |

- **ROM / RAM:** each routine ≈ 0.2–0.5 KB next to `dist_6502.py` / `reach_6502.py`; a few bytes of RAM (h0, P).
- **Build:** a firmware change means a full Quartus fit (update_mif is a no-op), so it carries the usual
  placement-seed timing lottery (memory `dr-mario-leaf-has-no-timing-budget`); the logic itself is unchanged.
- **Gates before a build** (if anything passes): a bit-exact golden of the 6502 routine vs `rules_steer10` on ≥ 5k
  boards (target index for A; per-root pen for D), py65 per-root V1 == `S10Decider` on the couch boards, the measured
  co-sim DONE latency (A's serial pick), and the couch A/B.

## 9. Shared-box protocol
- **Throttle:** systemd user unit `steer10-throttle` (`dr_mario_rl/tmp/steer10/throttle.sh`): SIGSTOPs every python
  process in `steer10-*.service` cgroups while `dr_mario_rl/tmp/steer10/PAUSE` OR `dr_mario_rl/tmp/PAUSE_ALL` exists;
  otherwise caps them at 8 runnable. Self-tested (cap 8 S + 2 T; PAUSE 10/10 T in 2 s; PAUSE_ALL logic 10/10 T on a
  scratch path; resume 8). Desk analyses also run in `steer10-desk-*` units (`dr_mario_rl/tmp/steer10/desk.sh`).
- **Load:** 8 workers, nice 19, MemoryMax 24G. No wall-clock timeouts in the harness.
