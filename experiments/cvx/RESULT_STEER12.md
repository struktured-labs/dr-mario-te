# RESULT (2026-10-06): STEER12, tempo levers for FAIR on the couch11 clock at opponent-measured pace

- **Pre-registration:** `PREREG_STEER12.md` (6b68ccc7, 0 main rows) + addendum A (d6a32b6d, committed before any main
  row was read).
- **Farm:** 19,200 games, audit OK, every job rc 0. FAIR's rows reused (steer11 pilot / steer8), identity-gated 20/20.
- **Outputs:**
  - `analyze_steer12.py` → `steer12/analysis.txt`;
  - `steer12_stallcal.py` → `steer12/stallcal.txt`;
  - `steer12_pace.py` → `steer12/pace.txt`.

## Short answer
1. **Opponent-measured pace (couch data only):**
   - dr. lulu M = 167.5 s [140.9, 223.5];
   - the owner M = 239.5 s [148, 387]. He never cleared, so this is very uncertain.
2. **FAIR on couch11 at those paces:**
   - **dr. lulu:** loses **23.5%** of races [21.1, 26.0]: 16.75 slow + 6.75 kill. The couch result was 3/9 (33%), a CI
     that contains it.
   - **The owner:** loses **11.5%**.
   - **Gate-b tap-out:** 6.0%.
3. **Answer speed is the lever.** Each frame of realised answer latency is worth **2.0 pp** of the LULU race
   [1.55, 2.41]. All four latency arms are ESTABLISHED (Bonferroni K = 8):

   | arm | LULU loss | gate-b tap-out |
   |---|---|---|
   | FAIR | 23.5% | 6.0% |
   | −2 f | **18.3%** | 4.0% |
   | −4 f | **15.1%** | 4.2% |
   | −6 f | **11.9%** | 2.8% |
   | zero-latency ceiling | **5.2%** | 1.0% |

   Tempo was charged 1:1 on the realised answer shift, which is an upper-side model of the race gain (see S6).
4. **Execution fidelity:**
   - **Perfect execution** buys **+3.1 pp** (LULU loss 23.5 → 20.4%), almost all of it kills (6.75 → 3.50). FAIR's sim
     steering already wastes only **+0.5 pills** vs perfect.
   - **Silicon's overhead is the big lever.** Random-root misses that cost +9 / +18 pills (silicon's couch overhead is
     ~+18–22) raise the LULU loss to **31.8% / 43.1%** (interpolated).
   - So execution fidelity, the gap between silicon-like and perfect execution, is worth **up to ~23 pp** of losses
     under this (harsh) miss model.
5. **MIN_THINK −2 f is not expressible honestly** beyond its latency channel (+5.2 pp = lat_m2).
   - Its cost is non-final commits at the earlier gate (+1–7 pp of decisions), which the sim cannot model.
   - **Break-even:** with 7 pp more non-final commits, each must cost ≤ 0.74 pp of losses per pp. That is ≤ 14% of a
     random-root miss (5.24 pp per pp).
6. **STALL CALIBRATION (addendum A): the sim does NOT demonstrably under-produce stalls.**
   - Pooled couch (19 games): 24.0 stall-pills from ≤ 16 viruses [9.4, 43.1], vs sim FAIR 20.1 (LULU) / 23.4 (owner).
   - **Against dr. lulu alone:** the couch's point estimate is 1.8× the sim's (35.7 [10, 69] vs 20.1; stall ≥ 30 s in
     44% [11, 78] vs 32.5%).
   - **Against the owner:** the couch is below the sim (13.5 vs 23.4).
   - **The most likely source of any shortfall is EXECUTION:** sim FAIR executes almost perfectly. Silicon-like misses
     (q 2–3%, which also reproduce silicon's pill overhead) raise sim stalls to 26–28 pills and ≥ 30 s stalls to 40–43%,
     i.e. to the couch's dr. lulu-day level.
   - Garbage rates match the couch (5.9 vs 5.9 cells/min) and are NOT the gap.
   - ⚠ STEER10's pace-gap stall comparison mixed definitions: couch "no progress at one virus count" (125/155/73/…)
     vs sim "no clearing move". It overstated the couch's stalls.

## 1. Opponent-measured pace (`steer12/pace.txt`)
**Method:** the vs_race human model T_L = T_L0 + δ·D, with δ 2.65 s per AI tile landed on the human.
- Effective time τ = t − δ·D(t).
- A cleared game gives T0 = τ(T).
- A censored game is extrapolated with a pooled power shape f = (τ/T0)^a.
- M = the median of T0.
- Games with < 12 viruses cleared are excluded.

| opponent | games | T0 per game (s) | M |
|---|---|---|---|
| dr. lulu | 9 (10/05; she cleared 2) | 167.5, 206.5 (cleared), 140.9, 171.4, 265.8, 223.5, 140.9, 152.8 (cleared), 142.5 | **167.5 s**; shape a 0.725, σ_log 0.229 |
| owner | 6 (10/04; 4 openings < 12 cleared excluded; he never cleared) | 402.7, 301.7, 371.4, 190.2, 154.5, 142.5 | **239.5 s**; σ 0.454 |

- **Her 9/27 two games** have no human-seat track and were not used.
- **δ is the dominant uncertainty of M:** lulu M = 248.0 s at δ 1.5 and 113.4 s at δ 4.0.
- **But δ cancels in the race:** FAIR's LULU win is 79.3% / 76.5% / 81.1% at δ 1.5 / 2.65 / 4.0, each with its own
  fitted M. The premise holds: sim FAIR sends 10.9 tiles/min; the couch AI landed 9.9 on her.

## 2. PRIMARY: LULU race at M 167.5 s (δ 2.65, σ 0.15; n = 1,200 paired; Bonferroni K = 8)

| arm | win % [95%] | loss slow / kill | Δ vs FAIR [95%] | Bonferroni | verdict | churn fixed / new | t_clear med | s/pill | realised tempo f/pill |
|---|---|---|---|---|---|---|---|---|---|
| **FAIR** | **76.50** [74.00, 78.92] | 16.75 / 6.75 | — | — | — | — | 208.4 s | 1.81 | 0 |
| lat −2 f | 81.67 | 14.00 / 4.33 | **+5.17** [+2.75, +7.67] | [+1.50, +8.67] | HELPS | 144 / 82 | 204.4 | 1.77 | −1.92 |
| lat −4 f | 84.92 | 11.50 / 3.58 | **+8.42** [+6.00, +11.00] | [+5.04, +11.88] | HELPS | 176 / 75 | 200.2 | 1.73 | −3.84 |
| lat −6 f | 88.08 | 8.83 / 3.08 | **+11.58** [+9.00, +14.17] | [+7.87, +15.17] | HELPS | 200 / 61 | 196.6 | 1.70 | −5.74 |
| lat ceiling | **94.83** | 4.25 / 0.92 | **+18.33** [+15.92, +20.83] | [+14.87, +21.75] | HELPS | 245 / 25 | 187.3 | 1.60 | −10.39 |
| ex_perfect | 79.58 | 16.92 / 3.50 | **+3.08** [+1.83, +4.42] | [+1.37, +4.88] | HELPS | 50 / 13 | 210.4 | 1.81 | 0 |
| ex_q02 (+9.9 pills) | 67.33 | 21.17 / 11.50 | −9.17 [−11.75, −6.50] | [−12.67, −5.46] | HURTS | 85 / 195 | 223.2 | 1.79 | 0 |
| ex_q03 (+13.8) | 62.33 | 22.25 / 15.42 | −14.17 [−17.08, −11.25] | [−18.17, −10.04] | HURTS | 86 / 256 | 226.6 | 1.79 | 0 |
| ex_q05 (+23.1) | 50.25 | 25.42 / 24.33 | −26.25 [−29.42, −23.08] | [−30.50, −21.87] | HURTS | 73 / 388 | 237.9 | 1.77 | 0 |

**Activity:**
- the clamp binds on 3.9–6.7% of pills;
- PROPH-armed pills are 0.2–1.4%;
- the realised miss rate is 2.0 / 2.9 / 4.9%;
- 0 perfect-execution fallbacks.

## 3. Secondaries

| | FAIR | lat −2 | lat −4 | lat −6 | ceiling | perfect | q02 | q03 | q05 |
|---|---|---|---|---|---|---|---|---|---|
| S1 owner race, M 239.5 (n = 600) | 88.50 | +3.50 | +4.33 | +5.50 | +10.33 | +4.50 | −7.50 | −11.33 | −23.67 |
| S2 gate-b tap-out (n = 600) | 6.00 | −2.00 | −1.83 | −3.17 | −5.00 | −3.00 | +8.17 | +10.67 | +20.00 |
| S2 tap≤100 | 0.83 | −0.50 | −0.33 | −0.67 | −0.50 | 0.00 | +1.67 | +2.50 | +6.17 |
| S3 LULU stress M 100 | 32.42 | +4.50 | +10.58 | +16.92 | +29.58 | +0.08 | −7.42 | −11.25 | −18.00 |
| S3 LULU stress M 120 | 51.08 | +7.33 | +9.92 | +15.33 | +27.17 | +1.42 | −10.58 | −15.33 | −25.33 |
| S4 δ 1.5 / M 248.0 | 79.33 | +5.42 | +7.17 | +9.92 | +15.33 | +3.83 | −9.08 | −14.83 | −26.00 |
| S4 δ 4.0 / M 113.4 | 81.08 | +5.42 | +7.75 | +10.75 | +15.75 | +4.33 | −8.08 | −13.08 | −25.25 |
| S5 σ 0.229 | 74.67 | +6.08 | +7.75 | +11.83 | +18.25 | +3.17 | −9.33 | −14.67 | −26.08 |

Full 95% CIs are in `steer12/analysis.txt`. Every latency, perfect and q cell excludes 0 at 95% except tap≤100 for some
latency arms and perfect, and stress M 100 for perfect.

**S7 latency slope:** **−1.99 pp of LULU win per +1 f** of realised answer latency [−2.41, −1.55] (OLS over FAIR / −2 /
−4 / −6). STEER7 measured −2.42 pp per f (race) under the legacy clock.

**S8 execution curve:**

| | overhead vs perfect | loss |
|---|---|---|
| ex_perfect | 0 | 20.4% |
| FAIR | **+0.46** pills | 23.5% |
| q02 | +9.9 | 32.7% |
| q03 | +13.8 | 37.7% |
| q05 | +23.1 | 49.8% |

- Interpolated loss at +0 / +9 / +18 pills: **20.4 / 31.8 / 43.1%**.
- **Per-miss cost:** +5.24 pp of losses per +1 pp of random-root miss rate.
- ⚠ The miss model is "a uniformly random other root", which is harsher per miss than silicon's. Silicon's 18% off-brain
  placements cost ~+18–22 pills, while q 3% random misses cost +14. Read the +9 / +18 losses as UPPER bounds for
  silicon-like overhead of that size.

**S9 MIN_THINK −2 f:**
- **Gain:** the latency channel = lat_m2's +5.17 pp.
- **Cost:** the extra non-final commits at the 4 f gate (+1–7 pp of decisions, RESULT_SETTLE sec. 8), which the sim
  cannot model.
- **Priced as random-root misses**, the net is [−31.5, −0.1] pp. That only says that random-quality non-final answers
  would erase it.
- **Break-even:** at +7 pp non-final commits, each may cost ≤ 0.74 pp of losses per pp (≤ 14% of a random-root miss).
  At +1 pp, ≤ 5.2 pp per pp.
- **Settling it needs the anytime-commit model** (STEER7 follow-up (a)) on the ROOTORD root order.

## 4. STALL CALIBRATION (addendum A; `steer12/stallcal.txt`)
**Definition**, identical on both sides: an act-stall is ≥ 10 consecutive AI decisions on which no legal placement of
the actual pill clears any virus. Sim runs are truncated at the human's finish T_L (couch games end when she wins).

| per game (v0 ≤ 16) | stall-pills | longest stall | stall ≥ 30 s |
|---|---|---|---|
| couch 10/05 vs dr. lulu (n = 9) | **35.7** [10.2, 69.0] | 31.3 s [12.2, 53.9] | **44%** [11, 78] |
| couch 10/04 vs owner (n = 10) | 13.5 [2.6, 28.8] | 15.0 s | 20% [0, 50] |
| couch, both days (n = 19) | **24.0** [9.4, 43.1] | 22.7 s [11.4, 36.0] | 32% [11, 53] |
| sim FAIR, LULU @ M 167.5, truncated (n = 1,200) | **20.1** [18.5, 21.7] | 25.6 s | **32.5%** |
| sim FAIR, owner @ M 239.5, truncated (n = 600) | 23.4 | 28.7 s | 27.5% |
| sim ex_perfect, LULU | 19.5 | 24.7 s | 30.7% |
| sim ex_q02, LULU | 25.9 | 31.4 s | 39.8% |
| sim ex_q03, LULU | 27.6 | 32.2 s | 42.5% |
| sim ex_q05, LULU | 30.3 | 33.6 s | 47.2% |

The ≤ 12 and ≤ 8 thresholds show the same ordering.

**Answer to the question "does the sim under-produce stalls?"**
- **Not demonstrably.** Pooled over 19 couch games the sim is within the couch CI on every metric.
- **The only gap with a direction is dr. lulu's 10/05 day:** point estimates 1.8× in stall-pills, 44% vs 32% in
  ≥ 30-s stalls, on 9 games whose CIs include the sim. Against the owner the couch stalls LESS than the sim.
- **(1) Execution misses: the best candidate.**
  - Sim FAIR executes nearly perfectly: +0.46 pills vs perfect, and perfect stalls the same (19.5).
  - Silicon wastes ~+18–22 pills.
  - Injecting misses at the dose that reproduces silicon's pill overhead (q 2–3%) lifts sim stalls to 26–28 pills and
    40–43% ≥ 30 s: dr. lulu's couch level.
- **(2) Garbage: NOT the gap.** Garbage received per minute matches (couch 5.9 / 5.1 vs sim 5.9 / 5.4). In the sim the
  top garbage tercile has 2× the stalls of the bottom (24 vs 12 pills), so garbage drives stalls, but the sim already
  has the couch's garbage.
- **(3) Unexplained remainder:** not identifiable from 9 games. On the couch boards, own placements built 3 of 4 walls
  (STEER10 mechanism check, quoted).
- **Implication for the tempo-vs-stall trade-offs** (A16, edge-reach): they were measured on sim FAIR's near-perfect
  execution. If silicon's misses create the extra stall-prone boards, a stall fix's value on silicon is plausibly
  LARGER than the sim showed. Check this by re-scoring stall fixes on a miss-injected FAIR (q ≈ 2–3%), not by
  shelving them.
- **⚠ Definition trap found:** the banked couch stall files (`stall_*_lulu_20261005.json`) count "≥ 10 placements at
  one virus count". That is no-progress, not no-clearing-move: 125/155/73/60/51 pills vs act-stall 100/136/35/27/37.
  STEER10's pace gap compared that couch figure with the sim's act-stall, overstating the couch side.

## 5. Caveats
- **R102: the 1:1 tempo channel and the zero-latency ceiling are bounds, not builds.** Gravity-bound pills would lock no
  sooner on silicon.
- **The owner's M** has a 2.6× wide CI. S1 is descriptive.
- **The random-root miss model is harsh per miss.** The execution curve's +9 / +18 levels are upper bounds on what
  silicon-like overhead of that size costs.
- **Every figure is sim-on-couch11:** the human is modelled, the AI clock is calibrated, and the brain is FAIR's
  final-answer brain.
- **Re-use of FAIR rows:** identity-gated 20/20. The blocks are declared reuse (STEER10 blocks).

## Files (`experiments/cvx/`)
- **Pre-registration:** `PREREG_STEER12.md`.
- **Code:**
  - runs: `steer12_run.py` (Knob), `steer12_jobs.py`, `steer12_farm.sh`;
  - gates: `steer12_gate.sh`, `steer12_identity.py`;
  - q calibration: `steer12_qcal.sh`, `steer12_qcal_read.py`;
  - pace and stalls: `steer12_pace.py`, `steer12_stallcal.py`;
  - analysis: `analyze_steer12.py`.
- **Rows / outputs:**
  - `steer12/main/` (19,200);
  - `steer12/gate/`, `steer12/qcal/`, `steer12/stallcal/` (couch per-decision flags, 19 games);
  - `steer12/analysis.txt`, `steer12/stallcal.txt`, `steer12/stallcal_fair.txt`, `steer12/pace.txt`, `steer12/pace.json`.
