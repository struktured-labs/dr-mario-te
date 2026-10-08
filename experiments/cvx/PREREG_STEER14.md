# PREREG STEER14 (2026-10-07): A16 x a slam-gate cut on V11, under a cart-faithful descent model, and STEER13's V11-vs-1488 re-derived

- **Lane:** steersim (STEER14). **Ruling:** the coordinator, 2026-10-07, after STEER13 (7fee23d5), REDIRECTED the same
  day before any main-farm game.
- **Tree:** h16-wt `experiments/cvx`, branch h16-rollout-gated.
- **Committed before any STEER14 main-farm game:** `steer14/main/` does not exist at this commit (the commit message
  records the check).
- **Superseded draft, disclosed:** a first STEER14 design crossed A16 with MIN_THINK 6 / 2 f.
  - It was never committed and no game of it ran on any main seed.
  - Only its gate and smoke rows ran (STEER13 block and the smoke seed); they were deleted unread except for the
    identity / activity checks.
  - The coordinator dropped MIN_THINK as a factor: the a16-mt-build lane's chained Mesen replays of the FAIR2PLUS cart
    show MIN_THINK −4 f moves the commit 1.7 f earlier and the lock **+0.00 f**. The descent starts at the cart's slam
    gate, not at the commit.
- **Lane stall, disclosed:** the stage-1 screen and gate finished on 2026-10-07 (21:04Z / 13:01 EDT). The lane's
  completion monitors expired before then, so nothing resumed it until the coordinator did on 2026-10-08 19:42 EDT.
  Those rows were not read in between (no file was opened), and no decision was taken on them before the rule ran.
- **Run before this commit** (no STEER14 main seed played):
  - the slam-gate validation on the cart replays (`steer14_slamcal.py`, e859887a);
  - the DONE model (`steer14_donecal.py`);
  - the STAGE-1 SCREEN of the slam-gate cut, execution metrics only, rule committed first in c4a14d71
    (`steer14_cal_read.py`). A first, KOPEN-only calibration (rule in e859887a) was stopped at 113 rows, unread (counts
    only), when the coordinator added the endgame cut; it is superseded and not used;
  - the identity gate and smokes (`steer14_gate.sh` → `steer14_identity.py`);
  - the analyzer's selftest and known-answer test (`steer14_kat.py`);
  - the worker guard and its killed mutants.

## 1. Questions
- **Q-R (the number the owner relies on).** STEER13 put V11 at MIN_THINK 6 f +17.4 pp vs today's 1488 cart (LULU race).
  Its model began the soft drop as soon as the capsule was aligned after the commit. How much of the +17.4 survives once
  the descent waits for the cart's slam gate?
- **The gate cut G\*:** a two-stage design.
  - **Stage 1 (screen):** the cut G\* is chosen from KOPEN cuts and ENDGAME cuts on execution metrics, by a rule committed
    first.
    - KOPEN cuts: a shorter stability wait above 10 viruses.
    - ENDGAME cuts: release DOWN under the K rule below 10 viruses, where today's cart is DONE-only (KEND 255), a
      35–57 f wait per endgame pill in the DONE model.
    - Uniform cuts: both.
  - **Stage 2:** G\* is crossed with A16. A 2x2x2 (KOPEN × KEND × A16) at the required n would need 8 × 5,100 LULU
    games and does not fit.
- **Q1 (iii):** under the corrected model, does the combined candidate (A16 + G\*, V11) beat today's FAIR2PLUS-equivalent
  (V11, DIST4, today's gate k32) vs dr. lulu?
- **Q2 (i), (ii):** does A16 add value on V11 at today's gate, and at G\*?
- **Q3 (iv):** does A16's value depend on the gate (interaction)?
- **Sensitivity:** does (iii) hold with q 2 % random-root misses on top?
- **Dose-response:** the LULU race for every screened gate configuration (DIST4).
- **Where the tempo goes:** GO → lock per pill and per ENDGAME pill (< 10 viruses), beside today's cart on the same
  pills, and the SLAM_ARM disarm rate, for every arm.

## 2. Instruments
### 2.1 Inherited (STEER13 part B, identity-gated)
- **Race clock:** couch11.
- **FAIR driver and brain:** `steer10_run.make(RULE)`.
- **Opponents at measured pace:**
  - dr. lulu: M 167.5 s, δ 2.65, σ 0.15, lam 2.84, lulu_fit_202610b sizes;
  - the owner: M 239.5, lam 2.36, Hartford sizes;
  - gate b vs owner202610.
- **anytime13 publish schedules:** V11 (DRROOTORD) / 1488.
- **The commit:** at GO + 6 f to the mailbox. GO = FAIR's sampled answer frame − 6, from STEER13's silicon latency
  sampler.
- **Late publishes:** adopted under DRLATEGUARD.
- **Race tempo:** lock frame − the lock frame of the same pill under TODAY's cart. q_B = 0.

### 2.2 The correction: the cart's DRSLAM gate
**The rule** (`patch_cartridge_copro.py` dn_p2; FAIR and FAIR2PLUS flags DRSLAM 1, KOPEN 32, KEND 255, KCROSS 8, LOWY 8,
VCEND 10, MATURE 2, ABORTSTALE 1, from the carts' build logs):
- Once aligned and orient-locked, DOWN is held only while either:
  - the search is DONE, or
  - SLAM_ARM is set and the driver's target has been stable for ≥ K hooks (2 per frame). K = KCROSS if ROM Y < 8, else
    KEND (255 = DONE only) below 10 viruses, else KOPEN.
- Otherwise there is no button and the capsule falls at natural gravity.
- `steer_model.execute(slam=...)` implements it. `slam=None` is byte-identical to before.

**Validated on the a16-mt-build lane's chained + garbage Mesen replays** (6 games × {FAIR2PLUS, MT2 cart}; input md5s in
`steer14/slamcal/inputs.md5`):
- **The rule vs the traced DOWN input:** 98.8 % of 50,570 frames agree; the first DOWN frame is exact on 93.6 % of
  pills. The misses are a 1-frame hook-order lag when DONE arrives mid-frame.
- **The corrected model vs the cart**, fed the same co-sim schedules and DONE (1,181 pill-runs, prestart pills excluded):

  | measure | corrected model | STEER13 model |
  |---|---|---|
  | DOWN start exact | **98.2 %** | 0.2 % |
  | lock frame exact (±1) | **94 % (98 %)** | 1 % |
  | mean lock error | −0.55 f | −14.1 f |
  | landing == cart | 99.3 % | — |

- **MIN_THINK 6 → 2 f, lock change on the same pills:** cart +0.00 f, corrected model **+0.00 f**, STEER13 model −2.06 f.
- **Example m2g2 p60:** cart commit f8, DOWN f21, lock f37; corrected model f8 / f21 / f37.

### 2.3 Two mechanisms the gate brings in, both modelled (`steer14_run.Knob14`)
1. **SLAM_ARM disarm (DRSLAM_MATURE + DRABORTSTALE).** A pill is disarmed (it waits for DONE) if it is a match's first
   pill, or if the previous pill locked while its search was still running at this pill's edge, i.e.
   GO + done_f > lock + gap.
   - **The gap** = max(12, 24 − ROM Y of the landing) + 20.2 f per clear step + 15.9 f per cascade fall row (couch11's
     coefficients), plus the garbage-drop frames before this pill (race only).
   - On the replays: the gap matches ±1 f on 96 % of no-clear pills; the disarm is predicted **585 / 585**.
2. **DONE time** (`steer14_donecal.py`). STEER13's leaf-count timing fits publishes (sd 0.95 f), but its implied search
   end is ~10 f early and nearly constant.
   - Model: done_f = 0.0015162 f/leaf × leaves(fw) + a residual drawn from the 1488 co-sim residuals of the pill's
     vcount band. The draw is keyed by (seed, pill), so the arm and its reference share it. Never before the final
     publish.
   - V11 out-of-sample: p10/50/90 35.1/45.4/57.3 f vs co-sim 34.6/45.0/55.4.

**The reference (today's cart)** = fw 1488, MIN_THINK 6 f, KOPEN 32, with its own SLAM_ARM chain. The gap's clear part
comes from the arm's landing.

**Other inherited mechanics:**
- **A missed pill** (q > 0) steers to its random root on the gate's terms (published at the arm's first publish
  frame).
- **A16:** the anytime META decider is `rules_steer10.make(vk=16)`, which must reproduce the brain's choice on every
  decision.
- **The stall probe** runs on every LULU row.

### 2.4 Guards and gates
- **Module patches** (Knob13 / `steer10_run.make`, plus Knob14's wrap of `vs_race.garbage_drop_timed`) are module
  attributes read at call time.
  - `stuck_probe.play_race` calls `V.garbage_drop_timed`, so the wrap hits the importer's binding; its activity counter
    `garb_events` > 0 in the smokes.
  - No `from X import` of a patched name exists in cvx or braingap.
- **Worker guard:**
  - fresh numba cache root per launch;
  - `jit_guard()` (150 fixed boards, sha `064752972d064a89` on two fresh caches) before any game;
  - exit 5 on failure;
  - killed mutants (`steer14_guard_mutants.py`): wrong sha, dead vk 16 gate and a corrupted META are each KILLED; the
    control passes.
- **Identity gate** (`steer14/gate/identity.txt`):

- **Result: PASS** (`steer14/gate/identity.txt`, rows in `steer14/gate/`).
  - **IDENTITY:** `S14_id_v116` (gate OFF) == STEER13's `B_v116_qb` on every key but the stamps: LULU 50/50, owner race
    25/25, gate b 25/25.
  - **CONSISTENCY:** `C13_14886` charges tempo 0 on every pill (it IS today's-cart reference).
  - **DETERMINISM:** `S14_d4_k32` run twice on 10 seeds is identical.
  - **POSITIVE CONTROL:** `S14_d16_k32` differs from `S14_d4_k32` on 10/10 rows (target-on decisions 1,256 vs 379).
  - **SMOKES:** every gate family is active. That covers the KOPEN cut, the endgame cuts e32 / e16 / v4, uniform u16 at
    q 2 %, gate b, the owner race and `C13_v116`:
    - DOWN via DONE and via stability, anytime activity;
    - misses at q 2 %;
    - A16 target-on;
    - endgame stability slams under every endgame cut;
    - the garbage-drop wrap firing on race rows.
  - Every row carries the probe where expected (ndec ∈ {dec, dec + 1}) and the guard sha.
- **Known-answer test of the analyzer** (`steer14_kat.py`): **PASS**.
  - 25 known answers are reproduced exactly: parts R / M / D deltas and churn, both guards, the interaction histogram,
    the sensitivity, the reference and the survival ratio.
  - A missing file withholds parts M / D; swapping the G\* arms is detected (10 mismatches).
  - **It failed first, and both causes are fixed:**
    1. `steer14_jobs.seeds()` / `blocks()` bound `LO` as a default argument at import, so the KAT's patched block was
       ignored. Production never patches `LO`, so the main job list is unchanged; LO is now read at call time.
    2. The KAT's own templates were real rows whose outcome depends on the seed (`vs_race.evaluate` draws the human's
       finish time from it). They are now seed-proof, asserted on four seeds.

## 3. Arms (`steer14_run.ARMS`; V11, MIN_THINK 6 f, slam gate ON unless stated)
**Slam-gate configurations** `steer14_run.GATES` = (KOPEN, KEND, VCEND). Pills at ROM Y < 8 always use KCROSS 8.

| family | configurations |
|---|---|
| **today** | **k32** = (32, 255, 10) |
| KOPEN cuts | k24, k16, k8, k4 = (K, 255, 10) |
| ENDGAME cuts | e32 = (32, 32, 10), e16 = (32, 16, 10), v4 = (32, 255, 4) |
| uniform | u16 = (16, 16, 10), u8 = (8, 8, 10) |

**Arms:**

| part | arm | DIST gate | slam gate | fw | misses | role |
|---|---|---|---|---|---|---|
| R | `C13_14886` | vk 4 | k32 | **1488** | 0 | today's cart (== its own tempo reference) |
| R | `C13_v116` | vk 4 | k32 | V11 | 0 | STEER13's "V11, 6 f", corrected |
| M | `S14_d4_k32` | vk 4 | k32 | V11 | 0 | today's FAIR2PLUS-equivalent |
| M | `S14_d16_k32` | **16 (A16)** | k32 | V11 | 0 | A16 at today's gate |
| M | `S14_d4_u8` | vk 4 | **G\*** | V11 | 0 | the gate cut alone |
| M | `S14_d16_u8` | **16** | **G\*** | V11 | 0 | **the combined candidate** |
| M | `S14_d4_k32_q02` / `S14_d16_u8_q02` | 4 / 16 | k32 / G\* | V11 | **q 2 %** | sensitivity pair (LULU only) |
| D | `S14_d4_{every other configuration}` | vk 4 | each | V11 | 0 | dose-response (LULU only) |

**G\* (stage-1 screen):**

- **Stage-1 screen** (`steer14/cal/gate_cut.txt`; rule c4a14d71; 400 seeds; tempo vs k32 summed per game; DIST4,
  V11). Every candidate is ELIGIBLE: landed-on-final within 1 pp on all pills and on endgame pills, refusals within
  0.5 pp.

  | config | tempo vs k32 (f/game) | f/pill | landed on final (endgame) | disarmed | endgame GO→lock (today's cart, same pills) |
  |---|---|---|---|---|---|
  | **k32** (today) | 0 | 0 | 99.07 % (98.39 %) | 8.8 % | 49.6 f (48.9) |
  | k24 | −142.5 [−153, −132] | −1.02 | 99.00 (98.29) | 11.0 | 49.6 |
  | k16 | −224.0 | −1.59 | 98.85 (98.04) | 12.7 | 49.3 |
  | k8 | −274.9 | −1.99 | 99.01 (98.50) | 14.1 | 51.0 |
  | k4 | −282.1 | −2.09 | 99.11 (98.70) | 14.5 | 51.9 |
  | e32 | −752.1 | −5.43 | 98.97 (98.14) | 10.4 | 36.9 |
  | e16 | −1,028.0 | −7.33 | 98.84 (97.87) | 12.0 | 32.6 |
  | v4 | −454.0 | −3.28 | 98.98 (98.15) | 9.9 | 42.0 |
  | u16 | −1,256.1 | −9.27 | 98.95 (98.22) | 16.1 | 32.9 |
  | **u8** | **−1,342.7 [−1,405, −1,282]** | **−9.95** | 98.86 (98.11) | 17.9 | 32.3 |

- **Model check:** MIN_THINK 2 f − 6 f = −0.02 f/pill, consistent with the cart's +0.00.
- **G\* = u8** (KOPEN = KEND = 8, VCEND 10): the most negative tempo per game among the eligible cuts.
- **Reading, execution only:**
  - The endgame rule is the dominant lever in the model: e16 alone saves ~4× k8's frames.
  - Every cut raises the SLAM_ARM disarm rate (8.8 → 17.9 % for u8). The tempo figures above are net of that.
  - V11 at today's gate is slower than today's 1488 cart on endgame pills (49.6 vs 48.9 f): its DONE is later.
  - **No race outcome was read.**

## 4. Seeds and n (declared REUSE; the registry is exhausted)
- **Part R:** STEER13's own seeds, **deliberately**, so the corrected contrast is paired with STEER13's banked one.
  - LULU 41100–44298 (1,600); owner race + gate b 41100–42298 (600).
  - This is a re-derivation of a published number on the same games under a corrected model; it is not new evidence
    about V11 from fresh games.
- **Part M:** even seeds **44300–54498** (5,100 streams), arms interleaved per 50-seed block.
  - Owner race + gate b: the first 1,000; sensitivity: the first 2,000. **Part D:** the first 1,000.
  - Every one of these streams was consumed before (`seed_registry.py --check 44300 5100 2`: 5,100 collisions):
    - 2,900: champ145 reserve / the H12 endpoint at L20, and gwprice;
    - 700: the H16 trial block. L20 e1/e2 played 53100–53700. REGISTRATION_H16's L11 clean guard, if it ran, starts
      near 54300, so ≤ 100 of these streams may have been played at L11, without dr. lulu's race, by H12/H16 brains;
    - 584: cvx run 12 winshape blk B (L20 drip);
    - 500: h12-distill;
    - 316: cvx run 13 blk C (L20 drip);
    - 100: the Hedge-2 dose probe (vs-rules).
  - **None was ever used by an L11-race study, nor to select or estimate A16, MIN_THINK, the slam gate, V11 or any
    STEER-lineage arm.**
    - STEER11's abandoned confirmation played only 41100–41398.
    - STEER13 played LULU 41100–44298. The registry's "41100–45098" note was its planned n.
    - At L11 with dr. lulu's volleys these are different games from the L20 / vs-rules uses. **A reuse, declared;
      nothing here is independent confirmation of anything measured on those streams before.**
- **Stage-1 screen:** 400 seeds 39134–39932 (STEER10/12/13 calibration block), execution metrics only; 11 arms
  (4,400 games).
- **Sizing** (`steer14/sizing.txt`; Rule 47):
  - Neither piece of (iii) has been measured under the gate model, so σ(iii) uses STEER13's per-seed proxies on its
    1,600 seeds: A16 − FAIR at q 4 % and MIN_THINK 2 − 6 f (the nearest measured tempo lever).
  - σ = sd(sum) = 0.6393 (correlation between the pieces +0.015).
  - n = ((2.4977 + 0.8416) × 0.6393 / 0.03)² = 5,064 → **5,100**: Bonferroni K = 4, two-sided α 0.05, power 0.80 at
    +3 pp.
  - **MDEs at this n:**
    - (iii) 2.99 pp; (i) / (ii) ~1.8–2.0 pp;
    - (iv) ~2.5–2.9 pp. **The interaction is under-powered below ~2.5 pp; a null there is not "no interaction".**
    - Guards (n 1,000, Bonferroni 6): gate-b tap-out 2.6 pp, owner race 3.9 pp.
    - Sensitivity (n 2,000, 95 %): ~4.0 pp.
    - Part R (n 1,600, 95 %): ±~2.7 pp half-width.
    - Part D (n 600 per configuration, 95 %): ±~4.5 pp (a description, not a test).
- **Games:** part R 5,600 + part M 32,400 + part D 8 × 600 = 4,800, total **42,800** (856 jobs of 50,
  `steer14_jobs.py main`, in that order).
  - The shared box also carries a Quartus fit, a co-sim farm and other lanes; expect ~15–20 h at 10 workers plus PAUSE
    windows.
- **Stopping:** data-independent. All jobs run.
  - `analyze_steer14.py` withholds part R until all its rows exist, and parts M / D until all of theirs do.
  - Part R is analysed and reported as soon as it is complete (it is independent of M / D).
  - While the farm runs, only `analyze_steer14.py --status` (row counts) is run.
- **Shared box:** unit `steer14-farm-main` (MemoryMax 24G, MemorySwapMax 0, Nice 19), 10 workers.
  - `steer14-throttle` caps runnable workers at 10 and SIGSTOPs them while `dr_mario_rl/tmp/PAUSE_STEER14` or
    `dr_mario_rl/tmp/PAUSE_ALL` exists (self-tested both ways).
  - No wall-clock timeouts anywhere.
- **Registry:** the block is registered in `dr-mario-rl/tools/seed_registry.py` at launch.

## 5. Endpoints and decision rules (`analyze_steer14.py`; selftest PASS, KAT PASS)
**PART R** (95 %, seed bootstrap; no decision rule, a measurement):
- C13_v116 − C13_14886 on the LULU race at M 167.5 (churn), the owner race and gate-b tap-out;
- beside it, STEER13's own contrast on the same seeds (+17.44);
- **SURVIVAL** = corrected / STEER13, with a seed-bootstrap CI, and corrected − STEER13 per seed.

**PART M, PRIMARY:** LULU race win at M 167.5, paired by seed, seed bootstrap (4,000). **Bonferroni over K = 4:**

| | contrast | answers |
|---|---|---|
| (i) | `S14_d16_k32` − `S14_d4_k32` | A16 at today's gate |
| (ii) | `S14_d16_u8` − `S14_d4_u8` | A16 at the gate cut |
| (iii) | `S14_d16_u8` − `S14_d4_k32` | **the combined candidate vs today's FAIR2PLUS-equivalent** |
| (iv) | (ii) − (i), per seed | the interaction |

HELPS / HURTS iff the Bonferroni CI excludes 0; otherwise n.s.

**GUARDS** for (i)–(iii):
- gate-b tap-out (harm = up) and the owner race at M 239.5 (harm = down), n = 1,000 each;
- harm iff the Bonferroni CI over 2 guards × 3 contrasts = 6 excludes 0 on the bad side.

**VERDICTS:**
- **(iii) CERTIFIED** iff its Bonferroni lower > 0 AND no guard harm on (iii).
- **(i), (ii):**
  - **A16 ADDS VALUE** iff the Bonferroni lower > 0 AND no guard harm;
  - **A16 HURTS** iff the Bonferroni upper < 0 OR guard harm;
  - otherwise **A16 NOT ESTABLISHED**.
- **(iv):** POSITIVE / NEGATIVE interaction iff its Bonferroni CI excludes 0; otherwise "none established", with its
  MDE.

**ALSO** (declared, descriptive):
- churn (fixed / new) beside every net delta;
- absolute loss (slow / kill) per arm vs dr. lulu and the owner; gate-b tap-out;
- activity per arm: non-final commits, late publishes, adoptions, refusals, landed on the final, tempo f/pill, disarmed
  pills (arm and reference), DOWN via DONE / stability / none, DIST target-on share;
- LULU-race tap-out and gate-b tap≤100 deltas; loss-type churn;
- **STALLS**, as STEER13 part A: an act-stall is ≥ 10 decisions on which no legal placement of the ACTUAL pill clears
  any virus. Per game, truncated at her finish T_L | untruncated:
  - stall-pills v0 ≤ 16 / 12 / 8;
  - the longest stall;
  - games with a stall ≥ 30 s;
  - deltas with CIs for (i), (ii), (iii);
- reference (not a contrast): `S14_d4_u8` − `S14_d4_k32` (the gate cut alone);
- **where the tempo goes, every arm:** GO → lock per pill and per ENDGAME pill (< 10 viruses), beside today's cart on
  the same pills; endgame landed-on-final; SLAM_ARM disarm rate (arm and today's cart); DOWN via DONE / stability /
  none;
- **SENSITIVITY:** (iii) at q 2 % (n 2,000, 95 %, churn), with the q 0 (iii) on the same seeds beside it.

**PART D** (descriptive, 95 %): per gate configuration, LULU Δ vs k32 on the first 600 seeds, plus tempo, GO → lock
(all and endgame pills), landed on the final and disarmed.

## 6. Interpretation and scope (signed)
- **Rule 13:** a non-established contrast is under-powered, not negative. **Rule 19:** no direction is stated for an
  n.s. contrast.
- **The commit timing is STEER13's silicon latency sampler** (GO median 7 model frames). The replay cart's GO is f2
  (same gravity origin).
  - The model therefore starts its stability clock and DONE ~5 f later relative to gravity than the replay cart does.
  - This is common to every arm and to the reference: it moves absolute tempo, not the arm-vs-reference timing.
  - In the validation the model was given the cart's own GO; in the farm it is not.
- **Not modelled:**
  - tucks;
  - PRESTART answers (precomputed during garbage windows; 67 of 1,248 replayed pills);
  - the cart's pre-commit rotation (laterals start at the commit, as today);
  - garbage frames in gate b's gap (gate b is pill-keyed; the gap only feeds SLAM_ARM there).
- **The DONE model** is fitted on co-sim boards from couch games; its residuals are drawn by vcount band only. DONE
  gates every pill below 10 viruses and decides SLAM_ARM, so its distribution, not just its mean, matters. It is
  validated out-of-sample on V11 at the quantiles above.
- **The model's 1488 vs the couch** (STEER13 sec. 4: 140 vs ~129 couch-equivalent pills) is re-checked under the
  corrected model: `C13_14886`'s pills and time to clear are reported beside the couch FAIR's 120 pills / 209 s.
- **The gate's own numbers** (KOPEN 32 / KEND 255 / VCEND 10 / KCROSS 8) are today's flags.
  - A KOPEN cut changes only pills at ≥ 10 viruses above ROM Y 8.
  - An ENDGAME cut changes pills below 10 viruses (below 4 for v4), where today's cart is DONE-only.
  - KCROSS 8 at ROM Y < 8 is unchanged everywhere.
  - Non-final slams are modelled as the cart does them: the pill keeps dropping; a later publish is adopted only under
    DRLATEGUARD (and resets the stability count); a refusal freezes the pill, which lands where it is.
- Under the null each HELPS / HURTS / harm call fires at ≤ 5 % / K.

## 7. Files (`experiments/cvx/`)
- **Model:** `steer_model.py` (`execute(slam=...)`).
- **Validation:** `steer14_slamcal.py` → `steer14/slamcal/`; `steer14_donecal.py` → `steer14/done_model.*`.
- **Runs:** `steer14_run.py` (Knob14, arms, worker guard), `steer14_jobs.py`, `steer14_farm.sh`, `steer14_throttle.sh`
  (unit `steer14-throttle`).
- **Stage-1 screen:** `steer14_cal_read.py` → `steer14/cal/gate_cut.txt`.
- **Gates:** `steer14_gate.sh`, `steer14_identity.py` → `steer14/gate/`; `steer14_guard_mutants.py`.
- **Sizing:** `steer14_sizing.py` → `steer14/sizing.txt`.
- **Analysis:** `analyze_steer14.py` (`--status`, `--rederive`, `--selftest`); `steer14_kat.py` (known-answer test).
