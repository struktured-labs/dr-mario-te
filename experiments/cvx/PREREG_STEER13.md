# PREREG STEER13 (2026-10-06): stall fixes under silicon-like execution, and an honest price for MIN_THINK cuts

- **Lane:** steersim. **Ruling:** the coordinator, 2026-10-06, after STEER12.
- **Tree:** h16-wt `experiments/cvx`, branch h16-rollout-gated.
- **Committed before any STEER13 main-farm game:** `steer13/main/` does not exist at this commit.
- **What was run first** (on other seeds; no race outcome was read):
  - the identity gate and smokes;
  - the anytime-model validation (co-sim boards, no games);
  - the q_B calibration (PILLS / EXECUTION ONLY, sec. 3).

## 1. Questions
- **A.** STEER12 found FAIR's sim executes almost perfectly (+0.5 pills vs perfect) while silicon wastes ~+18–22. Does
  A16 (DIST gate vk 4 → 16) or R60 (edge-reach P 60) help once execution is silicon-like?
- **B.** STEER12 priced −2 f of answer latency at +5.2 pp of the LULU race, assuming the final answer is always known at
  the gate. A MIN_THINK cut commits earlier to the copro's RUNNING BEST, which is the final only 66% (fw 1488) /
  ~90% (V11 ROOTORD) of the time at GO + 6 f. How much of the −2 f gain survives? Is DRMINTHINK = 8 with V11 firmware
  worth a couch test?

## 2. Common instruments (inherited, identity-gated)
- **Race clock:** couch11.
- **FAIR** = `steer10_run.make(...)` (STEER8b fD_bdepD brain + fair driver).
- **Opponents at measured pace (STEER12):**
  - LULU race: M 167.5 s, δ 2.65, σ 0.15, lam 2.84, lulu_fit_202610b sizes;
  - owner race: M 239.5 s, lam 2.36, Hartford sizes;
  - gate b vs owner202610 (pill-keyed, no clock).
- **Miss model** (STEER12 `ex_qNN`): with probability q per pill, the steering target is a uniformly random OTHER root,
  allowed by the shipping reach mask and legal. The RNG is keyed by (seed, pill), so every arm draws the same misses.
- **Identity** (`steer13_identity.py` + `steer13_gate.sh`):
  - `A_fair_q00` and `B_orc6_q00_fairref` reproduce FAIR's banked rows on every non-stamp key (lulu 4/4, gb 3/3 each;
    part A including the stuck probe).
  - The positive control differs.
  - `B_14886` charges tempo 0 on every pill: it IS the tempo reference.
  - Every arm's smoke is active.

## 3. Arms
### Part A (`steer13_run.py`, kind "miss")
| arm | brain | miss dose |
|---|---|---|
| `A_fair_q04` | FAIR (`s10_base`) | **q 4%** |
| `A_a16_q04` | `s10_A16` | 4% |
| `A_r60_q04` | `s10_R60` | 4% |
| `A_*_q02` (sensitivity) | same three | 2% |

**Why q 4%:** STEER12's paired overhead vs perfect execution (n = 1,200) was +9.9 / +13.8 / +23.1 pills at q 2 / 3 / 5%.
+18 pills interpolates to q ≈ 3.9%, so the PRIMARY dose is **4%**. The **sensitivity dose is 2%** (≈ +10 pills).

### Part B: anytime commit (`anytime13.py`, `steer13_run.py` kind "anytime")
**The publish model:** the faithful brain's per-root values equal the firmware's (braingap 0 / 6,570 roots mismatch).
`anytime13._choose_fw_meta` replays the firmware publish rules:
- **fw 1488:** Pass-0 order, strictly-greater replacement.
- **V11** (= V1 a1ef31c8, publish-identical to V11 without preemption, LEFLUSH sec. 0):
  - a DRROOTORD depth-2 pre-pass;
  - then the deep pass in descending d2;
  - equal values from an earlier today-rank win.

**Timing:** a flat 1,645 clocks per engine leaf, fitted on the 1488 co-sim publish times (`steer13_anytime_cal.py` →
`steer13/anytime_cal.txt`).

**Validation on the 10/03 co-sim boards:**

| check | result |
|---|---|
| identity | **335/335** (final + all 32 root values) |
| publish SEQUENCES exactly equal | **326/326 (1488), 331/331 (V11)** (non-tuck boards) |
| 1488 publish times, in-sample | residual sd 0.95 f |
| V11 publish times, out-of-sample | bias +0.51 f (the co-sim publishes later), sd 0.61 f |

**P(mailbox == final at GO + g)**, co-sim vs model:

| g | 1488 co-sim | 1488 model | V11 co-sim | V11 model |
|---|---|---|---|---|
| 2 | 45.1 | 45.1 | 4.5 | 5.7 |
| 4 | 57.4 | 59.5 | **85.2** | **86.4** |
| 6 | 65.6 | 67.8 | **90.9** | **91.5** |
| 8 | 72.7 | 71.2 | 92.4 | 93.1 |

At GO + 2, V11 has usually published nothing yet: the pre-pass ends at ~2.3 f in the model vs 2.6–2.9 f measured, so
MT 2 waits for the first publish. **Known bias:** the model's V11 first publish is ~0.5 f EARLY, which is optimistic for
V11 MT 2 by ≤ 0.5 f per pill. It is reported, not corrected (no V11 data was used to fit).

**The driver** (`steer_model.execute(sched=...)`):
- **GO** = FAIR's sampled answer frame − 6, since FAIR's gate is GO + 6 (MIN_THINK = 12 hooks).
- **Gate** = GO + MT. At the gate the driver commits to the mailbox, waiting if it is empty.
- **Later differing publishes** (frame = ceil(GO + t)) are adopted under the cart's **DRLATEGUARD** rule:
  - need = (|Δcol| + rotations) · 2;
  - avail = (thr − speedCounter) + (thr + 1) · (K − [Δcol ≠ 0]);
  - plus a clear own row;
  - the first refusal FREEZES the pill.
- **MT 4 / 2** move the gate by −2 / −4 f, with the steer lat, the PROPH-first end and the reach-mask T_LAT shifted as
  STEER12's lat arms.
- **Oracle arms:** the final is published at GO (no non-final commit).
- **Tucks are not modelled** (as everywhere in the sim).

**RACE TEMPO:**
- Each pill is charged (its lock frame − the lock frame of the same pill under TODAY's cart), i.e. the fw-1488 anytime
  schedule at MT 6 under DRLATEGUARD with the same miss draw.
- That reference runs as a state-preserving counterfactual.
- **Why this reference:** couch11 was fitted on that silicon, so B_14886 is tempo-neutral by construction, and every
  other arm pays or gains only its difference from today's cart, including the extra steering of late adoptions.

**Arms**, all at the residual miss dose q_B:

| arm | firmware | MIN_THINK |
|---|---|---|
| `B_14886_qb` | 1488 | 6 f (TODAY) |
| `B_v116_qb` | V11 | 6 f |
| `B_v114_qb` | V11 | **4 f (DRMINTHINK = 8)** |
| `B_v112_qb` | V11 | 2 f |
| `B_orc6_qb` / `B_orc4_qb` | oracle: the final at the gate | 6 / 4 f (the −2 f lever without non-final commits) |

**Residual miss dose q_B** (`steer13_jobs.py cal` → `steer13_cal_read.py` → `steer13/cal/qb.txt`; PILLS / EXECUTION
ONLY):
- **Setup:** 400 seeds of the STEER10/12 LULU block (39134–39932); arms `A_fair_q04` and `B_14886` at q 0 / 2 / 3 / 4%.
- **Rule** (written in `steer13_cal_read.py` before it ran): q_B = the q at which the anytime-1488 arm's overhead vs
  perfect execution equals A_fair_q04's (linear interpolation), rounded to 0.5%.
- **Why a residual:** silicon's +18–22 pill overhead already CONTAINS 1488's non-final commits, so the anytime model
  plus the full q 4% would double-count them.
- **Result** (`steer13/cal/qb.txt`, pills / execution only; overhead vs perfect execution, both-clear seeds):

  | arm | overhead (pills) | landed on the brain's final | other |
  |---|---|---|---|
  | `A_fair_q04` (part A's silicon dose) | **+16.65** [+9.6, +23.6] | 95.4% | — |
  | `B_14886` at q 0 | **+27.56** [+19.6, +35.2] | 90.2% | non-final commits 33.1%; late publishes 0.40/pill, adopted 0.33, refused 0.062 |
  | `B_14886` at q 2 / 3 / 4% | +36.8 / +39.0 / +45.3 | — | — |

  - **The anytime model ALONE already exceeds part A's lumped target, so the rule outputs q_B = 0** (the
    interpolation clamps at its lowest grid point).
  - **Part B therefore runs with NO injected misses:** today's 1488 non-final commits under DRLATEGUARD by themselves
    reproduce (and exceed) silicon-scale pill overhead.
  - **Disclosed:** the couch's 10/05 AI landed on the faithful brain's choice on 81.6% of pills, vs 90.2% here. Matching
    THAT rate would need ~+8 pp of misses. It is not used, because the pre-declared anchor is pill overhead.

## 4. Seeds and n (declared REUSE; the registry is exhausted)
- **Block:** even seeds from **41100**: the STEER11 confirmation block, ABANDONED BEFORE ANALYSIS. Its 663 partial
  STEER11 rows were never analysed and are not used.
  - It is disjoint from the STEER10/12 seeds that generated A16/R60 and the STEER12 levels.

| cell | n | seeds |
|---|---|---|
| LULU race | **1,600** per arm | 41100–44298 |
| owner race + gate b | **600** per arm (oracle arms: LULU only) | 41100–42298 |
| part A q 2% sensitivity (LULU only) | 800 | 41100–42698 |

- **Sizing:** from the measured throughput: the calibration farm ran ~2,250 games/h at the cap of 8.
- **Games:** part A 3 × 2,800 + 3 × 800 = 10,800; part B 4 × 2,800 + 2 × 1,600 = 14,400; **total 25,200**
  (`steer13_jobs.py main`), ≈ 11 h plus PAUSE_ALL windows.
- **Stopping:** data-independent. All jobs run. `analyze_steer13.py` withholds every contrast until all rows exist.
- **Shared box:** `steer13-throttle` (PAUSE `dr_mario_rl/tmp/steer13/PAUSE` + `tmp/PAUSE_ALL`, cap 8), nice 19.

## 5. Endpoints and decision rules (`analyze_steer13.py`; selftest PASS: 5 cases, 4 mutants killed)
### Part A
**PRIMARY:** LULU race win at M 167.5, A16 − FAIR and R60 − FAIR at q 4%, paired, seed bootstrap. Bonferroni over
K = 2 arms; HELPS / HURTS / n.s.

**GUARDS:** owner race M 239.5 and gate-b tap-out. Harm iff the Bonferroni CI over the 4 tests (2 arms × 2 guards)
excludes 0 on the bad side.

**RECOMMEND for a couch test** iff primary Bonferroni lower > 0 AND no guard harm.

**ALSO:**
- absolute loss (slow / kill) per arm vs dr. lulu and the owner;
- churn;
- gate-b tap≤100;
- LULU-race tap-out;
- the q 2% deltas;
- **STALLS**, stated definition: an act-stall is ≥ 10 consecutive AI decisions on which NO legal placement of the
  ACTUAL current pill clears any virus (stuck_probe "act"). Per game:
  - stall-pills with v0 ≤ 16 / 12 / 8;
  - the longest stall;
  - games with a stall ≥ 30 s;
  - each both truncated at her finish T_L and untruncated.

### Part B
**PRIMARY contrasts** (LULU race M 167.5, Bonferroni K = 3):
- v114 − v116 (DRMINTHINK = 8 with V11);
- v112 − v116;
- v116 − 14886 (V11 vs today at 6 f).

**WORTH A COUCH TEST** (per MIN_THINK cut) iff its contrast's Bonferroni lower > 0 AND no harm on gate-b tap-out / the
owner race (Bonferroni over 2 guards × 3 contrasts).

**ALSO:**
- **SURVIVAL** of the −2 f gain = (v114 − v116) / (orc4 − orc6), seed bootstrap;
- orc6 − 14886 (what today's non-final commits cost);
- absolute loss rates per arm vs dr. lulu and the owner;
- activity: non-final commits, late publishes, adoptions, refusals, landed on the final, tempo f/pill.
  - The landed-on-final rate of B_14886 is also an external check against the couch's 81.6% (10/05 AI MATCH 1025/1256).

## 6. Interpretation and null audit
- **Rule 13:** a non-established contrast is underpowered, not negative. The paired SE at n = 1,600 is ~1.1 pp.
- **Rule 26:** smokes confirm every arm is active.
- **Measurement scope:** the miss model is random-root (harsh per miss) and the anytime model omits tucks. The 1:1
  lock-frame tempo and the model's V11 first-publish bias are bounds. Absolute levels are sim-on-couch11.
- **Under the null**, each HELPS / HURTS / harm call fires at ≤ 5% / K. A CI straddling 0 is n.s., never "no effect".
