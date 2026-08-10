# PRE-REGISTRATION — STAGE 2: a shippable learned survival term for DIES-AHEAD

Written and committed **before** the corpus was extracted and before any model saw any
data. Author: stage-2 corpus lane. Date 2026-08-10.

Anything in this file may be *reported as deviated from*, but not silently changed.
Every number produced downstream must cite this file's commit hash.

---

## 0. WHAT STAGE 2 IS, AND THE TWO WAYS IT CAN FAIL

Stage 1 measured a CEILING: a 500-tree GBM read AUC 0.956 vs the champion evaluator's
0.926 on 5,824 held-out decisions. That is permission to test and nothing else.

This lane fails if either of these happens and we do not say so:

1. **We stop at AUC.** Project law: *signal ~ sqrt(R)/SE; proxies rule OUT only.* The
   deliverable is a **measured reduction in dies-ahead in actual rollouts with no loss of
   clear rate**. An AUC number is an intermediate gate, never a result.
2. **We fit something that cannot ship.** The evaluator runs at a leaf of a depth-3
   search on an FPGA coprocessor. The silicon budget is fixed BEFORE fitting in §5, and
   any model outside it is reported as *ceiling*, explicitly not as a candidate.

---

## 1. TARGET CLASS (fixed by recon C, not chosen post hoc)

Regime: **dr. lulu's fitted bursty pressure model**
(`experiments/eval47/results/dr_lulu_20260808_fit.json`), the regime the mandate names.

Census of record: `experiments/eval47/jointdig/results_hetzner/lulu_census.jsonl`,
12,000 games, champion base arm (ws=20, variant "winner"), seeds 2..12001.
Composition: clear 9,576 (79.80%) / topout 1,686 (14.05%) / stall 738 (6.15%);
dies-ahead 1,501 (12.51%).

Recon C partitioned failures by the rig's own control flow (a structural partition — it
cannot be tuned after the fact) and found the classes are NOT variants of one thing:

| mechanism | what happened | share of failures | BROAD-addressable |
|---|---|---|---|
| `T_GARB`  | spawn blocked immediately after a garbage volley | 50.5% | 42.9% |
| `T_PLACE` | `env.step` returned terminal — self-inflicted    | 17.5% | **0.0%** |
| `T_TRUNC` | 300-pill budget expired, still alive (= "stall") | 32.0% | n/a (nothing dies) |

**PRIMARY TARGET CLASS = `dies_ahead AND end_kind == garbage_topout` (DA x T_GARB).**
1,065 games per 12,000 (8.87%). It carries 100% of the BROAD-addressable prize
(456 games per 12,000 = 3.80% of all rows).

**EXPLICITLY NOT THE TARGET, and NEVER POOLED INTO IT** (recon C's do-not-pool cells):
- DA x T_PLACE (436/12,000): BROAD-addressable 0.0% [0.0, 0.0]. Budget spent here is wasted.
- stalls / T_TRUNC (738/12,000): nothing tops out. A survival ruler is *provably vacuous*
  on these; they need the virus-tempo lane. Stored, sliced, never pooled.
- not-ahead topouts: early deaths on wrecked boards, 1.5% of the census.

---

## 2. THE CORPUS (`s2lulu`) — fixed before extraction

### 2.1 Generating policy
`p0_ab.play_one(seed, forced=False)` under `model="lulu"` — the SHIPPED CHAMPION
(`pressure_rig._choose_base`, ws=20, wt=0, `fast_rtl_x.variant("winner")`), which the
p0_ab OFF-identity gate already certifies equals `pressure_rig.play()`. Not a surrogate.

### 2.2 What is kept (this is the fix for recon A's ★★★ coverage collapse)
Stage 1 kept only the last K=10 decisions of failure games and matched controls on
EXACT max_height, which collapsed the entire corpus to `max_height >= 13` — it never saw
an ordinary-play board, i.e. it never saw the population where the STRUCTURAL LAW says
breakage is decided.

Stage 2 keeps **EVERY decision of every extracted game**:
- ALL 1,686 topout games — all decisions.
- ALL 738 stall games — all decisions (separate file; never pooled).
- A seed-sampled set of CLEARED games — all decisions (the control side, and the only
  place breakage can be measured).

There is **NO exact-height stratification and no matched-pair dropping.** Height is
reported as a *slice* (bands h<=9 / 10-12 / 13-14 / 15-16), never as a filter. If the
model only works at h>=13 that is a finding, not something the corpus should hide.

### 2.3 Per-decision schema (identical to stage 1's, plus mechanism fields)
`seed, pill_idx, t_to_end, board_col[128], board_vir[128], cur, nxt, cand_vals[32]
(NaN = illegal), action, n_legal, max_height, viruses, occ, garbage_cum,
garbage_this_ply, clear_size_this_ply, since_last_garbage, outcome, dies_ahead,
end_kind, viruses_left_at_end`.
Boards are stored; **per-candidate features are DERIVED**, so all 32 siblings of every
decision are recoverable without a re-run.

### 2.4 Sizes (declared before the run; actuals to be reported against these)
- LOCAL, <=6 workers: 1,686 topout + 738 stall + 1,700 sampled clear games
  (sample rng 20260810), expected ~700k-800k decisions.
- HETZNER, queued strictly BEHIND `060-pressured-census-4.sh`: the full 12,000-seed
  extraction (all 9,576 clears included) — the population-scale control side.
This is ~40x stage 1's 19,075-decision contrast on the local half alone.

---

## 3. LABELS

### 3.1 Primary label
`y = 1` iff the decision comes from a game in the target class (`dies_ahead == 1` AND
`end_kind == garbage_topout`); `y = 0` iff the decision comes from a **cleared** game.
Decisions from T_PLACE topouts, not-ahead topouts and stalls are **excluded from the
primary contrast** and reported as named slices.

### 3.2 The label defect, stated up front
The label is a GAME outcome broadcast onto that game's decisions. There is no
counterfactual: a decision 40 plies before the end carries the same label as the last
one. `t_to_end` is stored so this can be sliced, and the primary analysis is **reported
at every t_to_end band**, because stage 1 measured the signal decaying exactly as
attribution loosens (d_spawn_h: AUC 0.9290 all fatal rows, 0.9480 at t_to_end<=2,
0.5449 on stalls). Nothing here is allowed to be reported pooled over t_to_end only.

### 3.3 Shuffled-label control (built INTO the pipeline, not bolted on later)
Every corpus file ships a column `y_shuf`: the primary label permuted **across GAMES**
(seed-level, rng 20260810), preserving the positive-game count and the cluster
structure. Stage 1's permutation was decision-level and therefore anti-conservative;
this one is not.

**Every AUC reported by this lane must be reported next to the same statistic computed
on `y_shuf`.** An AUC without its floor is not a result.

*This control demonstrably can fail*: the pipeline also emits `f_leak = y + N(0,0.1)`,
which must read AUC > 0.95 against `y` and 0.48-0.52 against `y_shuf`. If `f_leak` does
not separate on `y`, the pipeline is broken and the corpus is discarded. If a real
feature reads high against `y_shuf`, the split or the permutation is broken and the
corpus is discarded.

---

## 4. SPLIT — by GAME, never by decision

`hold = (seed % 10) in {7,8,9}`; `train` = the rest. Deterministic and
feature-independent. Asserted at build time: `set(train_seeds) & set(hold_seeds) == {}`.

Three further guards, all **measured and reported**, not assumed:
1. **Twin-seed aliasing.** 2k and 2k+1 share a pill stream. `seed % 10` puts ...6/...7
   twins on opposite sides. The count of twin pairs straddling the split and the number
   of decisions they carry is reported. (Under this engine the virus board is drawn from
   `default_rng(seed)`, so twins play different boards — recon C measured res agreement
   3,991/6,000 vs 3,962 under independence — but the number is reported anyway.)
2. **A game is positive XOR control by construction**; overlap must be 0.
3. **ROLLOUT SEEDS ARE DISJOINT FROM THE ENTIRE CORPUS.** The §6 rollout uses seeds
   20000..29999, which appear in no corpus file. A model may be tuned on train, checked
   once on hold, and is then tested on seeds it has never touched in any form.

---

## 5. THE SHIPPABLE CLASS — fixed BEFORE fitting (measured silicon budget)

Measured, this session, on the real RTL (`fpga/copro/LeafEval.sv`, Verilator + Quartus
23.1std on the Pocket part 5CEBA4F23C8 with the Pocket production policy):

- 29,730 leaf evaluations per depth-3 decision.
- ~1,600 clocks/leaf all-in; Pocket deadline gives **+250 clocks/leaf** of design margin
  (worst observed board floor is +310).
- Pocket ALM pool: **218 free** of 18,480, with 194 ALMs of fitter-seed noise.
- Pocket M10K: **258 free** (2.64 Mbit). DSP: **51 free**.
- => ALMs are exhausted; BRAM and DSP are not. The shippable model must SPEND BRAM AND
  DSP, NOT ALMs, and must be evaluated SEQUENTIALLY (one comparator, one adder, one
  cursor, parameters in an M10K).

**A model is IN CLASS iff all four hold:**
| budget | bound |
|---|---|
| added clocks per leaf | <= 250 |
| added ALMs | <= 150 |
| parameter store | <= 2 M10K (<= 20,480 bits), host-uploadable |
| new whole-board passes | **0** (every feature must be accumulable inside the existing S_COLWALK) |

Concretely in class: the 10 champion terms **bit-identical**, minus a sequential additive
correction `Delta(x)` over a narrow 8-feature x 8-bit vector — e.g. ~32 depth-4 quantised
trees (160 cycles, 12.4 kbit, ~91-150 ALMs) or ~200 stumps. `d_spawn_h` is free: the
existing column walk already computes per-column heights; capturing `max(H[3],H[4])`
measured **-420 ALMs / +1 DSP / +0 cycles** with a 948/948 correctness gate.

Out of class, and to be reported as CEILING ONLY: the stage-1 500-tree GBM (~4 orders of
magnitude over the cycle budget, needs a second board pass); any feature requiring a new
traversal (`c_das_reach`, `e_escape_reach` — these ARE in the corpus, flagged
`OFF_BUDGET`, precisely so the price of using them is visible).

**Keeping the 10 champion terms bit-identical is deliberate**: it makes `Delta == 0` an
EXACT-IDENTITY control, which is the killed-mutant/liveness pair this project requires,
and it makes the change doseable against the structural law.

---

## 6. THE VERDICT RULE

### 6.1 Gate A — corpus admissible (must pass, else no stage 2)
- **A1 fidelity**: the instrumented replayer reproduces the lulu census row
  (`res, pills, garbage, dies_ahead`) on >=24 gate seeds spanning topout/stall/clear,
  and on 100% of games in the bulk run.
- **A2 killed mutants**: `ws=0` and a garbage-rng offset must BREAK A1. A gate that
  passes mutants is vacuous and the corpus is discarded.
- **A3 shuffled-label floor + leak positive control** as specified in §3.3.
- **A4 cross-checks** over every decision: recomputed MAXH(pre) == stored `max_height`;
  recomputed virus count == stored `viruses`; `nlegal_probe(pre)` == stored `n_legal`;
  stored `action` == `nanargmax(cand_vals)`; chosen action legal.

### 6.2 Gate B — offline, on the holdout (proxy; can only RULE OUT)
Let `A_champ` = AUC of `CHAMP_EVAL` (the champion's own depth-3 root value for the chosen
placement) and `A_shuf` = the same statistic on `y_shuf`.
An in-class model advances to rollout only if ALL hold:
- **B1** holdout AUC(model) − AUC(`y_shuf` refit) >= 0.10 (i.e. it is not the floor).
- **B2** holdout AUC(model) > `A_champ`, with a 95% **seed-clustered** bootstrap CI on
  the paired difference excluding 0. (Stage 1's +0.031 [+0.0016, +0.0638] cleared 0 by
  0.0016 on ~390 clusters after a max-over-4-arms selection. This lane treats any margin
  under +0.01 as NOT CLEARED, and corrects for arm selection by declaring the arm before
  the holdout is opened.)
- **B3 within-decision endpoint** — the gap stage 1 never tested. At a leaf the model
  ranks 32 siblings of the SAME parent, a job the game-outcome label never trained.
  Required: on target-class decisions, the model's ranking of the champion's chosen move
  versus its legal siblings must be measurably different from the champion's own ranking
  — pre-registered as **argmax-flip rate >= 2%** on target-class decisions (memory law
  `dr-mario-spawn-lane-gate-probe`: below ~2% the arm is untestable, and spending
  rollouts on it is a known way to burn a night for nothing).
- **B4 eval-hacking holdout**: AUC must survive on the slice `end_kind == step_topout`
  (T_PLACE) *and* on `since_last_garbage` deciles, i.e. the model must not be reading the
  volley schedule instead of the board. Reported, not thresholded — a large slice-to-slice
  swing is a written caveat on everything downstream.

Failing B1, B2 or B3 = **STOP HERE**. Report the ceiling and the reachable fraction. Do
not spend rollout compute.

### 6.3 THE PRIMARY ENDPOINT (this is the actual deliverable)

Paired rollout, base arm vs treatment arm, **N = 3,000 seeds drawn uniformly from
20000..29999** (disjoint from every corpus seed), lulu regime, same rig, same injection
schedule, 2 arms = 6,000 games (~2.9 h on Hetzner at 0.583 g/s).

Uniform sampling from the population is deliberate: it prices breakage at the true
population ratio automatically, instead of sampling failures and clears separately and
re-weighting, which is how the always-on penalty family got its net-harm number.

**PRIMARY: dies-ahead count.**
GO requires `DA_trt − DA_base < 0` with a 95% seed-bootstrap CI excluding 0, and
McNemar exact two-sided p < 0.05 on the discordant DA pairs.

**CO-PRIMARY, GATING: clear-rate non-inferiority.**
GO requires the **upper** bound of the 95% CI on `(clear_base − clear_trt)` to be
**< +1.0 percentage point**. If clear rate falls by more than that, the result is
**NO-GO regardless of the dies-ahead number.** This is the structural law expressed as a
number: at this population ratio (9,576 clears : 1,501 dies-ahead = 6.4:1) breakage is
6.4x as expensive as rescue, and the always-on penalty family already died at exactly
this hurdle at four doses (net bad-ends per 40k: +464.7 / +201.8 / +967.6 / +2380.8 —
harmful at every dose, breakage floor ~6/240).

**SECONDARY (reported, no verdict):** net bad-ends (topout+stall), stall count, pills
among both-clear pairs (tempo tax), dies-ahead split by mechanism, per-mechanism rescue
and breakage seed lists.

**ROLLOUT GATES** (must pass or the rollout is void): base arm must reproduce the
census/base row on every seed (identity); treatment must differ from base on >=1 seed
(liveness). Both are killed-mutant-shaped: identity fails if the harness drifted,
liveness fails if the term is inert.

### 6.4 STOP / NO-GO — stated now, in advance

**STOP (do not proceed, report what was learned):**
- S1 Gate A fails on fidelity or a mutant survives -> the corpus is not evidence.
- S2 No in-class model clears B1/B2 -> "the ceiling is X and none of it is reachable in
  the shippable class"; report the ceiling, stop.
- S3 Argmax-flip < 2% on target-class decisions (B3) -> the arm is untestable; STOP
  before spending rollouts.
- S4 The only model that clears B2 is out of class (§5) -> report as CEILING ONLY,
  explicitly not a candidate, and stop. This is a genuinely useful result and must not be
  dressed up as a win.

**NO-GO (the model was tested and refused):**
- N1 Clear-rate loss upper CI bound >= +1.0 pp -> NO-GO even if dies-ahead improved.
- N2 Dies-ahead CI includes 0 -> NO-GO (no measured reduction).
- N3 Dies-ahead falls but net bad-ends do not (rescues converting topouts into 300-pill
  stalls) -> NO-GO; recon C already showed naive survival rescue (0.972) collapses to
  0.556 once progress is required, so a "rescue" that stops clearing is not a rescue.
- N4 The rollout identity or liveness gate fails -> void, re-run, never report.

**A result that is STOP or NO-GO is reported with the same prominence as a GO.**

---

## 7. LABEL-QUALITY LAW — the corpus FAILS the literal screen. Stated here, up front.

`dr-mario-label-quality-law` says: screen rollouts on CLEAR RATE > 96.9%.

**This corpus does not meet that bar.** The lulu census clear rate is **79.80%**
(9,576/12,000). The drip census stage 1 used was 95.46%, also below the bar.
Every downstream number from this lane carries that caveat, in writing, always.

Why the corpus is nonetheless informative — three separate reasons, each checkable:

1. **The mechanism the threshold prices is not the mechanism operating.** The 96.9% bar
   was derived to choose between ROLLOUT POLICIES labelling positions with a
   pills-to-clear REGRESSION target, where a bimodal clear/fail outcome inflates
   per-label SE. Here the label IS the binary game outcome and the failures ARE the
   signal.
2. **The generating policy is not degraded — the ENVIRONMENT is adversarial.** The
   policy is the shipped champion, bit-for-bit (p0_ab's OFF-identity gate; the local
   replay reproduces census seeds 2/3/4/5/6 exactly on res/pills/garbage/dies_ahead).
   A low clear rate under dr. lulu's fitted pressure is the phenomenon under study, not
   an artifact of a weak labeller. Under this same policy with NO pressure, clean solo
   failure is <0.20%.
3. **The same memory records the threshold as REFUTED as a decider** — "use it to RULE
   OUT, never to RULE IN". Nothing is being ruled IN by it here.

**And the bigger defect, which the law does not cover:** the label is a game outcome
pasted onto a whole game's decisions with no counterfactual (§3.2). Fixing ATTRIBUTION
(per-candidate forced-rollout labels) buys more than fixing the clear rate would. The
corpus stores boards + all 32 candidate values precisely so that an attribution layer can
be added on the same seeds without re-running the census.

**Mandatory caveat string**, to be attached to every number this lane produces:
> Corpus `s2lulu`: generating policy = shipped champion (bit-exact), environment = dr.
> lulu fitted bursty pressure, clear rate 79.80% — BELOW the 96.9% label-quality screen.
> Labels are game outcomes broadcast onto decisions; no counterfactual attribution.

---

## 8. FEATURES (frozen before fitting)

Computed on the POST-placement board, via `vocab2/feature_battery.py` **reused
unchanged**, so every number lands on the same instrument that produced stage 1's
0.9002 / 0.9290.

**BASELINE 11** (`feature_battery.NAMES11`, from `fast_rtl_x._base_scan`):
`MAXH HOLES TOPRISK SPAWN SETUP MATCHED BURIED RDYEXT VRDY CROSS POLL`.

**CANDIDATES 15** (`feature_battery.CAND_NAMES`):
`a_topout_dist a_d_maxh b_spawn_prox b_spawn_prox_strict c_das_reach c_d_das_reach
c_nlegal_probe c_d_nlegal d_gvuln_mass d_crit_cols d_spawn_h e_escape_routes
e_escape_reach x_hvar x_jagged`.

**`d_spawn_h = max(H_post[3], H_post[4])` is the lane's single strongest known input**
(AUC 0.9290 vs the champion SPAWN term's 0.9002; paired +0.0288 [+0.0195, +0.0348],
200/200 bootstrap reps positive; 0.9480 at t_to_end<=2). It is in the corpus as a
FEATURE by pre-registered routing. It is also free in silicon.

**COMPARATOR, never a model input:** `CHAMP_EVAL = cand_vals[i, action[i]]`.

**Silicon tagging, declared now so it cannot be rationalised later:**
- `FREE_IN_COLWALK` (0 new passes): `MAXH, a_topout_dist, d_spawn_h, d_crit_cols,
  d_gvuln_mass, x_jagged, x_hvar, e_escape_routes, HOLES, TOPRISK, SPAWN`.
- `OFF_BUDGET` (needs a new traversal — usable only as CEILING evidence):
  `c_das_reach, c_d_das_reach, e_escape_reach`.

**Known correction to the mandate's framing, carried forward:** SPAWN is not mainly
*saturating* — only 0.11% of fatal rows read its ceiling of 8. It is a **dead-zone**
sensor: it reads 0 for any spawn-column height <= 12, which is 98.13% of cleared-game
decisions. `d_spawn_h` is the same sensor with the dead zone removed — which is exactly
why it wins AUC and exactly why an always-on version has broad clear-game contact.

**And a warning from recon C that this lane must not ignore:** at the terminal window
`d_spawn_h` is already EXHAUSTED — the champion already takes a minimum-spawn-lane action
on 91.3% of plies in the last 12 before a T_GARB death, and 49.8% of those games have no
ply where any action would have lowered the lane. Whatever the learned term is, it has to
bite EARLIER than 6-12 plies from the end, or on the **tie set** (36.0% of all champion
decisions have the top value TIED among >=2 legal actions — a third of moves are
currently decided by enumeration order, not by the evaluator). That is why the corpus
keeps ALL decisions of a game rather than the last ten.

---

## 9. COMPUTE DISCIPLINE (binding)

- Hetzner (`root@178.104.197.190`): jobs queued **strictly behind** the running
  `060-pressured-census-4.sh`; pending queue verified EMPTY before adding. The runner
  claims `ls -1 pending/*.sh | sort | head -1` under `flock`, so the name prefix is the
  order; ours is `070-`. Nothing is displaced.
- Remote-node discipline: the synced code is **hashed** and the hash recorded in the job
  and in the corpus meta; the fidelity gate is **re-run on the remote after the sync**;
  `ps` not `pgrep -c`; the results file is appended under `flock`.
- Local: **<= 6 workers, hard cap** (unbounded jobs have OOM-killed this box five times).
  Long jobs run under `systemd-run --user --scope` and are waited on IN-TURN.
- No Mesen, no hardware. Pure simulation.

---

## 10. DEVIATION LOG

(Every departure from the above is appended here with its reason, and the affected
numbers are marked. An empty log is the expected case.)

- 2026-08-10: none at time of commit.
