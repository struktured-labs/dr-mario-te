# PREREG (2026-10-04): STEER9 — "don't seal a live column" on the silicon-faithful brain, vs FAIR

Written and committed BEFORE any STEER9 screen game. At commit time `steer9/` holds no `gb10_* / rc10_* / lulu10_*`
row files (only `steer9/gate/` gate rows and the mechanism-check outputs); the commit message records the count.

## 1. Why
Couch forensics 10/04 (`couch_forensics/RESULT_FAIR_20261004.md`, `stall_fair_20261004.py`,
`stall_m5g2_fair_20261004.json`): three couch stalls share one cause. Viruses became unreachable as a line, and the
brain has **no term that values keeping access to a virus open**.
- dr. lulu 9/27 G1: one yellow (8,2) under a mixed own-pill stack, ~99 pills stalled.
- 10/04 M4 G2 (FAIR2's tap-out): a tall board; the reach mask shrank 30 → 1.
- 10/04 M5 G2 (FAIR lost the race): col 6 walled to row 0 by p65 (rows 3–5 own halves p4/p13/p14, rows 0–2 garbage);
  col 7's 6 viruses unreachable for 119 pills.

## 2. The route predicate and the rules (`seal_steer9.py`)
**LIVE / SEALED** (one kernel, many call sites): a virus is LIVE iff `cascade_leaf6_x._vdist(kdig=0, cap=99) < 99`,
i.e. some 4-window through it (horizontal or vertical) can be completed by straight drops without first clearing
another cell (every other cell is its colour, or empty and fillable from above; nothing empty below it in a vertical
window). Otherwise SEALED. (Feasible `_vdist` costs are ≤ 48, so `< 99` is exactly "a route exists".)

**Root-side rules** (firmware-implementable; computed per allowed root on the firmware's own SOFT b1, the board the
6502 already builds for the eh terms):

| rule | n_new(a) counts | dose |
|---|---|---|
| **SEALV** | viruses LIVE on the root board and SEALED on b1(a) (a cleared virus does not count) | penalty `P × n_new`, or veto |
| **SEALC** | virus COLUMNS whose top virus is LIVE on the root and whose top virus on b1(a) is SEALED | veto |

- **Penalty mode:** root value −= P × n_new, with DRVETO's 16-bit saturation.
- **Veto mode:** root value −= 20000 iff n_new > 0 AND some allowed legal root has n_new == 0 (DRVETO strength).
  Every root sealing ⇒ no penalty, so the failure mode is the status quo.
- `_choose_fw_seal` is a mechanical copy of braingap `_choose_fw` (diff: the pen line after DRVETO, plus tracking the
  no-penalty argmax for the activity counter). **Gate: P = 0 is action- AND root-value-identical to
  Leaf6FwDecider on 235/235 couch boards.**

**Leaf rule (mechanism comparison only, NOT screened):** −W × (#SEALED viruses) at every leaf, all virus counts.

## 3. Mechanism check on the banked couch cases (`steer9_mech.py`, `steer9_mech_report.py` → `steer9/mech_check.txt`)
Silicon-faithful brain (`Leaf6FwDecider`, every fw switch on, DIST60, deployed mask at the pill index) = **base**.
Each rule is applied to the SAME observed board. A **seal event** is a virus that is LIVE on board k and SEALED on
board k+1. It is **own** when the silicon move's soft b1 already seals it; otherwise it is garbage / a board change.

| game | own-seal decisions (silicon == base) | base brain would seal the same virus | kept open: **V150** | **VVETO** | **CVETO** | leaf W60 |
|---|---|---|---|---|---|---|
| M5 G2 | 20 (13) | 13 | 8/13 | **13/13** | 7/13 | 3/13 |
| M4 G2 | 26 (21) | 21 | 14/21 | **21/21** | 15/21 | 5/21 |
| lulu G1 | 17 (12) | 14 | 9/14 | **14/14** | 13/14 | 3/14 |

**The critical moves themselves:**
- **M5 G2 col-6 wall (p4 / p13 / p14): NO rule changes it.**
  - All three were silicon ≠ brain: OTHER, LATE-FLIP and OTHER (execution).
  - On those boards the brain's own choices put **0** cells in col 6.
  - p4's silicon move sealed (6,6) with a hanging half. The brain's own p4 choice sealed a different virus; V150,
    VVETO and CVETO move it to a=14 (one cell in col 6, seals nothing).
  - p13 and p14 sealed nothing NEW: (6,6) was already sealed, so a route rule cannot see them. The leaf `buried`
    term already prices deepening.
  - Col-6 cells p0..p65: silicon 3, brain 1, rules 1–2.
  - **Col 7's six viruses were sealed by GARBAGE** (p138: not the AI's move).
  - In-stall re-seals of col 6 by the brain itself (p127 (10,6), p137 (8,6)): every V rule keeps them open.
- **M4 G2 tall-board sequence:** own seals at p78, p82 and p85 are brain choices (silicon == base). V150, VVETO and
  CVETO all keep them open. p84 was silicon ≠ base.
- **lulu G1 (8,2):** sealed at p7 by a silicon move that the faithful DIST60 brain would NOT make (lulu G1 was
  ANTIBODY). No rule is needed there. The later col-2 stack sits on an already-sealed virus.

**Reading:**
- The route rules DO change the brain's own sealing decisions: VETO 100%, V150 ~65%, CVETO 54–93%.
- The leaf form is weak (21–24%, because the other leaf terms dominate) and is the expensive one in RTL. **Dropped.**
- The specific couch walls were execution deviations, an older brain, or garbage. So this screen tests the GENERAL
  hypothesis: whether stopping the brain's own seals lowers tap-out. The anecdotes cannot be fixed by a brain rule.
- Base brain seal rate: 9–22% of decisions newly seal ≥ 1 virus, and a 0-seal allowed alternative existed on
  100% of boards.

## 4. Arms (all = FAIR + one rule; faithful DIST60)
| arm | rule | firmware cost (estimate, §8) |
|---|---|---|
| `s9_V150` | SEALV penalty, P = 150 per newly sealed virus | per-root, can overlap the copro: ~0 answer cycles |
| `s9_VVETO` | SEALV veto (−20000) | needs every root's flag before selection: pre-pass ≈ 0.08–0.13 f, unless overlapped with Pass 0 |
| `s9_CVETO` | SEALC veto (column top only) | ~8 virus checks per root; pre-pass ≈ 0.02 f |

**Dose choice (declared):**
- The doses were chosen on the couch boards above, which is anecdote tuning, declared here. P400 behaves like the
  veto on these boards (keeps 11/13, 20/21, 13/14 open), so the two V doses bracket soft vs hard.
- The C rule is screened at its strongest dose (cheapest firmware).

**Activity counters in every row** (rule 26): `seal.dec`, `seal.fired` (some allowed root penalised) and
`seal.changed` (the chosen root ≠ the no-penalty argmax on the same board = what FAIR's brain picks).

## 5. Design (declared REUSE everywhere)
- **Baseline = FAIR** = STEER8b arm `fD_bdepD`:
  - faithful DIST60 (`Leaf6FwDecider`, sw all on);
  - fair DRSETTLE: G0 −5 / round-start −4, answer −6, tempo −6;
  - PROPH-first fix D at f11;
  - the DEPLOYED fw mask T19 / G0 8.
- **Harness REUSED:** `steer9_run.py` is `steer8_run.make("fD_bdepD")` verbatim except the decider class. It uses
  `stuck_probe.play_gb` / `play_race`, `refit_opp`, and the steer_model hooks.
- **Fits:** gate (b) `owner202610` (gb10). Race lam 2.36, M 177, δ 2.65 (rc10). LULU lam 2.56, M 140 (lulu10).
- **Seeds (REUSE declared; the registry is exhausted, and `--check` FAILS every block):**

| cell | n per arm (paired) | seeds | FAIR rows |
|---|---|---|---|
| gb10 | **1,200** | 39134–40332 (STEER8b) + 40334–40932 + 33000–33598 (STEER6b / 8a) | banked `steer8/gb10_fD_bdepD_*` + new `s9_base` |
| rc10 | 600 | 39134–40332 | banked `steer8/rc10_fD_bdepD_*` |
| lulu10 | 600 | 39134–40332 | banked `steer8/lulu10_fD_bdepD_*` |

  - gb10 is doubled for power: at n = 600 the Bonferroni tap-out CI clears 0 only ~26–55% of the time for a true
    −2 pp; at n = 1,200, ~52–87%.
- **Identity gate (done):** `s9_base` reproduces the banked fD_bdepD rows **9/9** (3 per cell), every non-stamp key
  byte-identical. The new-seed FAIR rows are therefore valid FAIR rows.
- **Totals:** 3 arms × (1,200 + 600 + 600) + 600 `s9_base` = **7,800 games** (`steer9_farm.sh`, 156 jobs × 50).

## 6. Endpoints and the BAR
**Per arm vs FAIR, paired, seed bootstrap** (`analyze_steer9.py`). Churn (fixed / new) is printed beside every net Δ.
- gb10 **tap-out** Δ;
- rc10 **race win** Δ (M177, δ 2.65);
- lulu10 **LULU race win** Δ (M140);
- **endgame stall-pills / game:** board-level act-stalls ≥ 10 that start at ≤ 4 viruses (STEER6e definition). Also
  all act-stall pills (STEER6) and SEALED ("str") stall pills ≥ 10, because the couch stalls started at 7–17 viruses.
  All three are reported per cell with 95% CIs.
- the activity counters.

**PRIMARY BAR (as specified by the coordinator), per arm, all CIs at Bonferroni across 3 arms (99.17%):**
**PASS iff gb10 tap-out Δ upper CI < 0 AND rc10 race Δ lower CI > −1 AND lulu10 race Δ lower CI > −1.**
`analyze_steer9.verdict`; the killed-mutant selftest passes, with 6 mutants killed.

**NULL AUDIT of this bar** (memory `pass-condition-vs-null-outcomes`, done BEFORE the data).
- The race guard is a non-inferiority margin of 1 pp at n = 600.
- Assume a race-NEUTRAL rule (true Δ = 0) with STEER8b-level race churn (20–80 discordant pairs of 600). Then
  P(lower 99.17% CI > −1) = **0.15 / 0.08 / 0.05 / 0.05** for 20 / 40 / 60 / 80 discordant pairs, per race cell.
- Both cells together: ≤ 2%.
- **So this bar FAILS a race-neutral rule ~98% of the time.** It can pass only an arm that demonstrably GAINS about
  +2 to +3 pp of race in BOTH race cells, or one with very low churn.
- **This is recorded, not changed.** A FAIL whose race CI spans 0 means "no demonstrated race non-inferiority at
  1 pp". It does not mean "race loss".
- **Declared secondary (NOT the bar):** STEER6r's "no demonstrated loss" form (race upper CI ≥ 0), printed beside
  the verdict.

**Interpretation rules:**
- **Rule 26:** an arm whose `changed` count is 0 is UNRUN, not neutral.
- **Rule 13:** a FAIL with a tap-out CI spanning 0 is underpowered, not negative.
- **Re-weighting caution:** the rules fire in the opening too (9–22% of couch decisions). Prior art: always-on
  shaping of mid-game viruses (STEER6 dist_hsv; the burial-price family) has netted zero or worse. An improvement
  concentrated in stall-pills without a tap-out gain is reported as such.

## 7. Gates done before this commit
1. **Copy:** `_choose_fw_seal` (P = 0, wleaf = 0) == braingap `_choose_fw` on 235/235 couch boards, for the action
   and every root value. The source diff is the penalty line, the act0 tracking and the renamed leaf kernels only.
2. **Identity:** `s9_base` == banked `fD_bdepD`, 9/9 rows (gb10 / rc10 / lulu10 × 3), in `steer9/gate/`.
3. **Smoke + activity:** every arm runs, and the rule is active:
   - V150: changed 11–14 per game;
   - VVETO: changed 6–25 per game;
   - CVETO: changed 22–43 per game.
4. **Verdict selftest:** PASS, with 6 mutants killed.
5. **Farm dry run:** 156 jobs.

## 8. Implementation cost estimates (for any arm that passes; NOT built here)
**Context:** the te firmware 6502 runs at the copro clock (85.9 MHz MiSTer / 54.7 Pocket). DIST's root pick is 11k
cycles median, ≤ 0.19 ms. A search is ~26k leaves × ~1,849 clocks, so the copro is busy for ~26 f and the 6502
mostly waits on it.

**Seal check per board:** for each virus, ≤ 4 horizontal + ≤ 4 vertical windows × 3 cells, early exit on the first
live route. That is ≈ 150–300 cycles per virus, so **≈ 4–8k cycles per board** at 20–40 viruses.

| rule | firmware work | answer latency | RTL |
|---|---|---|---|
| **SEALV penalty (V150)** | root board once + soft b1 per allowed root: ~30 × 6k ≈ 0.2M cycles ≈ 2.3 ms. Done in the root loop while the copro runs ply 2–3 for that root (the eh terms are already computed there), so it overlaps. | **≈ 0 f**. Serial worst case ≈ 0.14 f ≈ +0.15–0.4 pp tap-out (STEER7 slope 1.1–2.7 pp/f). | none |
| **SEALV veto (VVETO)** | the "some root keeps everything open" test needs every root's flag before selection. Either a pre-pass at Pass 0 (as DRREACH's mask, ≈ 0.08–0.13 f unless interleaved with Pass 0's CMD 4 nodes), or folded into the DRREACH mask as a skip. | 0.08–0.13 f if not overlapped | none |
| **SEALC veto (CVETO)** | ≤ 8 column-top checks per root ≈ 1.5k cycles | ≈ 0.02 f even serial | none |

- **ROM:** each routine is ~0.4–0.7 KB, next to `dist_6502.py` / `reach_6502.py`. **RAM:** 32 flag bytes.
- **Build:** a firmware change means a full Quartus fit (update_mif is a no-op), so it carries the usual
  placement-seed timing lottery (memory `dr-mario-leaf-has-no-timing-budget`). The logic itself is unchanged.
- **Leaf rule:** a new LeafEval term over ALL viruses at every leaf, i.e. a per-virus route FSM. That is not
  0-cycle like DIST's single-target FSM, and it needs a new adder level (a pipeline stage). **Not screened**
  (mechanism check §3).

## 9. Shared-box protocol
- **Throttle:** systemd user unit `steer9-throttle` (`dr_mario_rl/tmp/steer9/throttle.sh`).
  - It SIGSTOPs every python process in `steer9-*.service` cgroups while `dr_mario_rl/tmp/steer9/PAUSE` OR
    `dr_mario_rl/tmp/PAUSE_ALL` exists.
  - Otherwise it caps them at 8 runnable.
  - Self-tested: cap 8 S + 2 T; each PAUSE file 10/10 T in 2 s; resume 8.
- **Load:** 8 workers, nice 19, MemoryMax 24G.
- **Timeouts:** no wall-clock timeouts exist in the harness. The only `timeout=` is the git stamp call, which is
  caught and falls back to "?".
