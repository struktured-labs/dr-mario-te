# PREREG STEER12 (2026-10-06): tempo levers for FAIR on the couch11 race clock, at opponent-MEASURED pace

- **Lane:** steersim. **Ruling:** the coordinator, 2026-10-06, after STEER11.
- **Tree:** h16-wt `experiments/cvx`, branch h16-rollout-gated.
- **Committed before any STEER12 main-farm game.** `steer12/main/` does not exist at this commit.

## 1. Question
On a clock that charges what the couch charges (STEER11 `couch11`), FAIR loses mostly SLOW races. The question is how
far each **tempo lever** gets FAIR toward zero losses:
- **(a)** a faster answer (a latency curve);
- **(b)** MIN_THINK −2 f;
- **(c)** execution fidelity (fewer wasted pills).

They are measured against dr. lulu and the owner at their **measured** paces.

This is a **measurement study**, not a ship gate. Every arm reports absolute loss rates with CIs and churn. A lever is
called **established** only when its Bonferroni CI excludes 0.

## 2. Instruments (all inherited, all identity-gated)
**Race clock:** `couch11` (STEER11, cb842760; `steer11/clock_couch11.json`).
- Fitted on 19 couch games / 2,128 AI intervals.
- Hold-out: median 210.8 s predicted vs 209.2 s observed on the 4 AI clear games.

**FAIR** = `steer10_run.make("s10_base")` = STEER8b `fD_bdepD`: silicon-faithful brain, DIST60, fair driver.

**OPPONENT-MEASURED PACE** (`steer12_pace.py` → `steer12/pace.txt`, `pace.json`; couch data only, NO sim win rate
read):
- **Method:**
  - effective time τ = t − δ·D(t), with δ 2.65 s per AI tile landed on the human (the vs_race damage model);
  - f = fraction of her 48 viruses cleared;
  - a cleared game gives T_L0 = τ(T);
  - a censored game is extrapolated with a pooled shape f = (τ/T0)^a;
  - M = the median of the per-game T0;
  - games with fewer than 12 viruses cleared are excluded (declared in the script before it ran).

| opponent | M | game bootstrap 95% | games | shape a | linear-extrapolation M |
|---|---|---|---|---|---|
| **dr. lulu** | **167.5 s** | [140.9, 223.5] | 9 (10/05; 2 cleared, 7 censored) | 0.725 | 165.7 |
| **owner** | **239.5 s** | [148.4, 386.7] | 6 (10/04; he never cleared) | 0.625 | 187.9 |

- **dr. lulu:** her 9/27 two games have no human-seat track and are not used. Measured per-game spread σ = 0.229.
- **Owner:** 4 openings were excluded (< 12 cleared: 27–72 s games). σ = 0.454. **Highly uncertain.**
- **Sensitivity to δ:**

  | δ | lulu M | owner M |
  |---|---|---|
  | 1.5 | 248.0 | 369.3 |
  | 4.0 | 113.4 | 116.4 |

  δ enters both the fit and `vs_race.evaluate`, so it largely CANCELS whenever the sim AI's sends match the couch
  AI's. That cancellation is checked by secondary S4.

**Human model otherwise as STEER10 / 11:**

| race | lam | sizes | σ (primary) |
|---|---|---|---|
| dr. lulu | 2.84 | lulu_fit_202610b | 0.15 (standing) |
| owner | 2.36 | Hartford | 0.15 (standing) |

## 3. Arms (`steer12_run.py`; each wraps FAIR's Steer object in `Knob` and touches nothing else)
### (a) Latency curve: STEER7 semantics on FAIR, G0 FIXED at FAIR's

| arm | answer frame | PROPH-first end | reach mask T_LAT |
|---|---|---|---|
| `lat_m2` / `lat_m4` / `lat_m6` | max(F0, x − 6 + D), D = −2 / −4 / −6 | max(F0, 11 + D) | max(F0 + 1, 19 + D) |
| `lat_ceil` (zero-latency ceiling) | F0 on every pill | F0 | F0 |

- **Race tempo:** 1:1 on this pill's REALISED answer shift (after the F0 clamp) vs FAIR's realised answer on the same
  pill. It is added to couch11's per-pill base.
- **Smokes:** realised −1.9 / −3.8 / −5.7 / −9.6 f per pill; the clamp binds on ~5% of pills.
- **Caveat, signed:** gravity-bound pills would lock no sooner on silicon, so 1:1 tempo is an UPPER-side model of the
  race gain. Gate b carries no tempo channel (its opponent is pill-keyed): there the lever is "act sooner" only.

### (b) MIN_THINK −2 f: not run as its own arm
**Why:** the steer model executes the brain's FINAL answer on every pill. MIN_THINK 12 → 8 hooks has two effects:
- −2 f of answer latency. This is lat_m2's channel, so lat_m2 IS its gain.
- More non-final commits at the earlier gate: final-at-gate 91/86/91% → 85/84/84% with ROOTORD fw (RESULT_SETTLE
  sec. 8), i.e. 1–7 pp of decisions.

The sim cannot express the second effect without an anytime-commit model (STEER7 desk follow-up (a), never built; the
FAIR sim brain is fw 1488 without ROOTORD). We therefore report a **BRACKET**:
- **net ∈ [lat_m2 Δ − 7 × c, lat_m2 Δ − 1 × c]**, where c = the per-miss cost from the (c) arms.
- A non-final commit is priced as a random miss. That is an upper bound on its cost: a running best is usually a
  near-best root.

### (c) Execution-overhead knob

| arm | what |
|---|---|
| `ex_perfect` | the brain's choice placed straight: no steering model, overhead 0 by definition |
| `ex_qNN` | FAIR's steering model + injected misses: with probability q per pill the steering target is a uniformly random OTHER action, allowed by the shipping reach mask and legal on the board |

- **The miss model is grounded on the couch:** 10/05 had 18% non-MATCH AI pills, and only 29/231 were an adjacent
  column. Most were a different root.
- **Dose:** calibrated on PILLS ONLY on 60 seeds outside the evaluation blocks (`steer12_qcal.sh` →
  `steer12/qcal/overhead.txt`; no race outcome was computed). The q grid brackets +9 / +18 pills of overhead vs
  `ex_perfect`.
- **Calibration result** (pills only; paired overhead vs ex_perfect, seeds where both cleared, n ≈ 26–53):

  | arm | overhead (pills) |
  |---|---|
  | FAIR (q 0) | +4.5 [−0.1, +13.2] |
  | q 1% | +4.3 |
  | **q 2%** | **+9.3** [+2.4, +17.5] |
  | **q 3%** | **+19.3** [+8.7, +31.1] |
  | q 4% | +16.9 |
  | q 6% | +33.8 |
  | q 8% | +24.7 |

  The high-q arms clear less often, so their both-clear overhead is biased low.
- **PRE-REGISTERED q grid: `ex_q02`, `ex_q03`, `ex_q05`.** q 2% ≈ +9 and q 3% ≈ +18 bracket the ruling's targets;
  q 5% sits beyond them for the slope.
- Random-root misses cost far more pills each than silicon's near-misses, so the "equivalent miss rate" is much lower
  than 18%. The knob is anchored in PILLS, as the ruling asked.
- **Read:**
  - loss at 0 / +9 / +18 pills of overhead, by linear interpolation over (overhead, loss) of ex_perfect / FAIR / q-arms;
  - overhead = the paired mean (pills − ex_perfect pills) over seeds where both cleared;
  - "how much loss execution fidelity alone could buy back" = loss(+18) − loss(0).

## 4. Seeds and n (declared REUSE; FAIR's rows are reused, not re-run)

| cell | seeds | FAIR rows (reused) |
|---|---|---|
| LULU race | STEER10 LULU block, 1,200: 39134–40332, 40334–40932, 33000–33598 | the steer11 pilot couch11 rows `steer11/pilot/lulu10b_c11_s10_base_*` |
| owner race | 600: 39134–40332 | the steer11 pilot `rc10_c11_s10_base_*` |
| gate b vs owner202610 | the same 600 | the banked `steer8/gb10_fD_bdepD_*` |

- **Identity** (`steer12_identity.py` + `steer12_gate.sh`): the no-op arms `lat0` / `q00` reproduce those FAIR rows on
  every non-stamp key (lulu 4/4, rc 3/3, gb 3/3 each). The positive control (vs banked A16) differs. Every arm's smoke
  is active.
- **Main farm:** 8 arms × (1,200 + 600 + 600) = **19,200 games** (`steer12_jobs.py main`, `steer12_farm.sh main`).
- **Shared box:** `steer12-throttle` (PAUSE `dr_mario_rl/tmp/steer12/PAUSE` + `tmp/PAUSE_ALL`, cap 8), nice 19.
- **Stopping rule:** data-independent. All 384 jobs run.
- **Withholding:** `analyze_steer12.py` withholds every contrast until all rows exist (R97).

## 5. Endpoints (`analyze_steer12.py`; selftest PASS, classifier mutant killed)
**PRIMARY:** the LULU race at M 167.5 s (δ 2.65, σ 0.15). Per arm:
- the ABSOLUTE win and loss % (seed bootstrap 95%), loss split slow / kill;
- paired Δ vs FAIR: 95% CI, Bonferroni over K = 8 (99.6875%), churn fixed / new;
- classification HELPS / HURTS / n.s. by the Bonferroni CI.

**SECONDARY:**

| | endpoint |
|---|---|
| S1 | owner race at M 239.5 s |
| S2 | gate-b tap-out and tap≤100 |
| S3 | LULU stress bracket M 100 / M 120 (reported separately) |
| S4 | δ-paired sensitivity: δ 1.5 with M 248.0; δ 4.0 with M 113.4 |
| S5 | σ 0.229 (her measured spread) |
| S6 | time to clear / pills / s per pill; activity (realised tempo shift per pill, clamp %, armed %, miss %, perfect fallback) |
| S7 | the latency SLOPE: pp of LULU win per frame of realised answer shift, OLS over FAIR / m2 / m4 / m6, seed bootstrap |
| S8 | the EXECUTION curve and loss at 0 / +9 / +18 pills of overhead |
| S9 | the MIN_THINK bracket |

## 6. Interpretation rules
- **Rule 13:** a non-established lever is underpowered, not absent. n = 1,200 gives a paired SE of ~0.7–1.5 pp.
- **Rule 26:** an arm with zero activity is UNRUN. Smokes confirm activity.
- **R98:** no stratum defines an endpoint.
- **R102:** the ceiling and the 1:1 tempo channel are bounds, not buildable levers.
- **The owner's M** has a 2.6× wide CI. S1 is descriptive.

## 7. Null-outcome audit
There is no PASS/FAIL. Under the null (an arm ≡ FAIR), "HELPS" or "HURTS" fires with probability ≤ 5% / 8 per arm. A
null-predicted outcome (a CI straddling 0) is reported as n.s., never as evidence of absence.
