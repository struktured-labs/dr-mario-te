# PREREG (2026-10-03): STEER8b — fair settle (gravity pin), eh on the true b1, R4 vs flat hang (blocks 3–5)

Written and committed BEFORE any STEER8 game, with STEER8a's prereg. Same brain (`Leaf6FwDecider`, every switch on),
fits, runner and seeds as STEER8a. It runs after STEER8a.

## Block 3: what is a FAIR settle worth? (the couch carts pin P2 gravity 5 f per pill)
**Source:** the settle lane, Mesen frame-level on the couch carts, CONFIRMED; relayed by the coordinator. See memory
`dr-mario-settle-gravity-pin-violation`.
- Unmodified game: G0 = 1 (274/274).
- Today's cart: G0 = 6 (72/73), so 5 gravity frames are lost per pill.
- DRSETTLE=3 plus a readiness guard:
  - G0 6 → 1 (392/392);
  - GO hook 2 vs 14 (314/314), i.e. ~6 f earlier.
- The steer model's fitted G0 = 7|8 is today's pinned cart, so fair = 2|3.

**Arms** (shifts in frames vs today; all on faithful DIST60):

| arm | steer G0 | round-start pill G0 | answer frame | mask T_LAT | mask G0 | tempo (BASE_F, gate-b clock) |
|---|---|---|---|---|---|---|
| **(a) today** = fD (STEER8a rows) | 0 | 0 | 0 | 19 | 8 | 0 |
| **(b-dep) fair DRSETTLE, DEPLOYED fw mask** `fD_sB_dep` | −5 (2\|3) | −4 | −6 | 19 | 8 | −6 |
| **(b-ref) fair DRSETTLE, REFIT mask** `fD_sB_ref` | −5 | −4 | −6 | **13** | **3** | −6 |
| **(c) fair, no settle cut** (settle 15, no pin) `fD_sC` | −5 | −4 | 0 | 19 | 3 | 0 |

**How the arms are modelled:**
- **Tempo:** the settle lane said "let the fall physics produce it; with BASE_F only use −6 for (b) and 0 for (c)".
  The race and gate-b clocks are BASE_F-style constants, so −6 / 0 is what is used here.
- **PROPH:** steer_model pulses on [F0, t_act) with gravity from G0. So (a) has ~4 presses mostly under frozen
  gravity, (b) ≤ 1 press under live gravity, and (c) ~4 presses under LIVE gravity. This is the settle lane's
  description; no extra modelling.
- **steer_model change:** a gravity start before F0 (fair G0 = 2 < F0 = 3) now pre-counts the missed frame:
  `spd = max(0, F0 − g0)`. That is 0 for G0 ≥ 3, so every pre-STEER8 use is unchanged; the identity re-check is in
  the gates below.
- **(b-dep) vs (b-ref)** decides the firmware DRREACH mask constants. The deployed mask (T 19 / G0 8, baked into
  `reach_6502.py`) credits PROPH pre-gravity moves that (b) no longer has.

**Cells:** gb10 **1,500**, rc10 600, lulu10 600. LULU is kept because dr. lulu is the bar.

**Note: gb10's opponent is PLACEMENT-clocked.** Owner202609 runs a renewal in AI placements at 2.08 s per
placement, so the tempo / clock shift cannot move gate-(b) outcomes; it moves only `elapsed_s`.
- gb10 prices G0 + answer + mask.
- The races (time-clocked volleys) add tempo.

**Reported** (descriptive; no ship bar here, because fairness is mandatory and this prices it):
- Each arm vs (a), per cell: Δ with 95% CIs and churn.
- **(c) − (a)** = minus what the pin was worth.
- **(b-ref) − (c)** = the settle cut under fair gravity.
- **(b-ref) − (b-dep)** = the mask refit.

**Mask decision rule:** if (b-ref) − (b-dep) gb10 tap-out excludes 0 at 95%, recommend the better constants.
Otherwise keep the deployed constants (status quo).

## Block 4: eh on the TRUE b1, a firmware-fix candidate
- **Arm:** `fD_ehb0` (switch `ehb1=0`: eh scored on the link-aware fixpoint child) vs fD.
- **Cells:** gb10 600 (39134–40332) and rc10 600. LULU dropped.
- **Rule:**
  - **RECOMMEND the fw fix** iff gb10 tap-out Δ upper CI < 0 AND rc10 Δ upper CI ≥ 0.
  - **HARMFUL** iff the gb10 lower CI > 0.
  - Otherwise "no detectable difference → no fw change needed".

## Block 5: R4 hang vs flat hang (R4 has never been A/B'd)
- **Arm:** `fD_hang0` (flat 40, any column) vs fD.
- **Cells:** gb10 600 and rc10 600.
- **Rule:**
  - **Drop R4** iff hang0 − fD gb10 tap-out upper CI < 0 AND rc10 upper CI ≥ 0.
  - **R4 earns its keep** iff the lower CI > 0.
  - Otherwise no detectable difference.

## Multiplicity
There are 6 gb10 tap-out comparisons across blocks 3–5: three arms vs (a), the mask comparison, block 4 and block 5.
Each gets 95% and a Bonferroni 99.17% CI. Any "significant" statement uses the Bonferroni CI.

## Totals
Block 3: 3 × 2,700. Blocks 4–5: 2 × 1,200. That is **10,500 games**, at 8 workers, after STEER8a.

## Gates (run before this commit; results recorded in the commit message)
1. **Identity after the steer_model edit:** `fA_off` gb under OWNER-0804 is still byte-identical to the banked rows.
2. **Mask at fair G0** (`steer8_mask_validate.py`): reach_fw_tap with G0 = 3 vs the frame sim at G0_CHOICES 2|3
   (phase 1), at T_LAT 7 / 13 / 19. The required agreement is 100%.
3. **Smoke:** every block-3/4 arm runs (2 games each).

---

## AMENDMENT (2026-10-03, before ANY 8b game): the driver's PROPH window, ledge fixes A/B/C; block 3 re-specified
**Status when this was written:** no 8b game had run. The 8b phase of `steer8_farm.sh` was stopped before it launched
(`steer8a-farm` runs 8a only). The block-3 arms in the table above (`fD_sB_*`, `fD_sC`) are **SUPERSEDED and NOT
RUN**.

**Why.** The settle lane traced the real driver frame by frame (Mesen, 17 PROPH-armed G2 pills, real carts).
- **PROPH stops at the FIRST VALID PUBLICATION** (GO + ~1.3 f), not at the commit.
- From then until the commit (GO + MIN_THINK 6 f) the driver only rotates.
- At the commit, DISTGATE's budget is the free rows below. It ignores the frames left in the current row, so on a
  throat ledge it clamps the lateral move to 0. (`steer_model._eff` already models this: `dist_table[0] = 0`.)
- **Frame conversion:** our frame = their frame + 1.

**Model changes** (guarded attributes; defaults = the pre-STEER8b behaviour; identity re-checked below):
- **steer_model.Steer:**
  - `proph_end_f`: PROPH pulses only on [F0, p_end).
  - `dg_extra(thr, spd)`: fix B.
  - `ledge_commit`: fix C.
- **reach_fw_tap:**
  - `PROPH_END`: the mask's PROPH window end.
  - `DISTROW`: fix B.
  - `LEDGE_T`: fix C. For a PROPH-armed board, every `T_LAT` use inside `reachable()` becomes `TL = LEDGE_T`.
- **Amended driver rule:** [F0, p_end) PROPH → [p_end, t_act) idle under gravity → rotate and steer at t_act.
- **Model limitation, declared:** rotation still starts at t_act. Silicon rotates from the first publication, but
  the pooled t_act is silicon's first LATERAL move, so moving rotation earlier would shift every rotation placement in
  every arm.

**Fixes** (settle lane, confirmed):

| fix | name | what it does | how it is modelled here |
|---|---|---|---|
| **A** | DRPROPHHOLD | PROPH continues until the COMMIT with its own direction; rotation takes the shared tap slot | `p_end = None` (to t_act). The mask's PROPH window runs to T_LAT. |
| **B** | DRDISTROW | at 0 free rows, the lateral budget = min(7, floor(max(0, thr − counter) / 2)), where counter is the gravity counter before this frame's tick; ≥ 1 free row = 7 | It REPLACES the 0. Rotation is never clamped. |
| **C** | DRLEDGECOMMIT | a PROPH-armed pill skips MIN_THINK and commits at the first valid publication once its orientation is reached | steer: armed t_ans = min(t_ans, p_end). Mask: TL = p_end for armed boards. |

**Block 3 arms** (faithful DIST60; **600 per cell**: gb10, rc10, lulu10 on 39134–40332):

| arm | G0 (round start) | answer | tempo | steer p_end | fixes | mask (T_LAT / G0 / PROPH end / B / C) |
|---|---|---|---|---|---|---|
| **fD_a2** (a) today | 0 | 0 | 0 | **10** | — | DEPLOYED 19 / 8 / T_LAT / – / – |
| **fD_bdep2** (b) fair, deployed mask | −5 (−4) | −6 | −6 | **4** | — | DEPLOYED 19 / 8 / T_LAT / – / – |
| **fD_bref2** (b) fair, refit mask | −5 (−4) | −6 | −6 | 4 | — | 13 / 3 / **4** / – / – |
| **fD_c2** (c) fair, no cut | −5 (−4) | 0 | 0 | **10** | — | 19 / 3 / T_LAT / – / – |
| **fD_brefA** b-ref + A | −5 (−4) | −6 | −6 | until commit | A | 13 / 3 / T_LAT / – / – |
| **fD_brefAB** b-ref + A + B | −5 (−4) | −6 | −6 | until commit | A, B | 13 / 3 / T_LAT / **B** / – |
| **fD_brefABC** b-ref + A + B + C | −5 (−4) | −6 | −6 | 4 (armed commit at 4) | A, B, C | 13 / 3 / – / B / **C at 4** |

- In fD_brefABC, A is moot for armed pills because C commits them at p_end.
- **Known fw/model mismatch, recorded:** the DEPLOYED fw mask credits PROPH until T_LAT 19, while silicon stops at
  ~f10. Even today's cart (a) is over-credited. The b-dep/b-ref pair measures exactly this.

**Analysis** (`analyze_steer8b2.py`; descriptive, 95% CIs and churn beside every Δ):
- **Every arm vs fD_a2.** These 6 comparisons plus block 4 make 7 gb10 tap-out comparisons. Any "significant"
  statement uses Bonferroni **99.29%**.
- **Decomposition:**

| comparison | what it shows |
|---|---|
| c2 − a2 | minus the pin's worth |
| bref2 − c2 | the settle cut under fair gravity |
| bref2 − bdep2 | the mask refit |
| brefA − bref2 | fix A |
| brefAB − brefA | fix B |
| brefABC − brefAB | fix C |

- **Mask decision:** recommend the refit iff the bref2 − bdep2 gb10 tap-out 95% CI excludes 0 in its favour.
  Otherwise status quo.
- The shippable combination is decided by the settle lane's Mesen replay bar plus the gravity-fidelity gate. These
  arms price the candidates.
- **a2 vs 8a's fD (today):** report the number of differing rows per cell (any key, and outcome), i.e. how much the
  PROPH-window correction moves today's arm.

**Block 4** is unchanged: `fD_ehb0` vs 8a's `fD`, gb10 600 + rc10 600. **Block 5 (hang=0) is DROPPED** (the
coordinator's allowance).

**Totals:** 7 × 1,800 + 1,200 = **13,800 games**, 8 workers, queued after 8a (`steer8b_farm.sh`).

**Gates (before this amendment's commit):**
- **Mask vs frame sim** under every amended config (`steer8b_mask_validate.py`; 840 boards incl. 11 PROPH-armed,
  352 armed candidates). Every CONSISTENT config (a2-today, b-ref, c, b-ref+A, +A+B, +A+B+C) agrees **100.000%**.
- **Measured mask/driver mismatch:**
  - deployed mask vs the (b) driver: 24 mismatches, all on armed boards (armed agreement 93.2%);
  - deployed mask vs (a2): 0 on these boards.
- **Identity:** the 8a arms `fA_off` / `fD_off` under the amended runner reproduce the banked python rows (2 + 2).
  STEER7's `steer7_dlat` S=0 still reproduces STEER6d (2/2) after the guarded edits.
- **Smoke:** every amended arm runs.

---

## SECOND AMENDMENT (2026-10-03, before ANY 8b game): fix D (DRPROPHFIRST) replaces A/B/C
**Status:** no 8b game had run. `steer8b-farm` was stopped while still waiting for 8a. The A, A+B and A+B+C arms from
the first amendment are **DROPPED, NOT RUN**: the settle lane's Mesen replays ruled them out (hybrids 3–5, or regret 22
for ABC).

**Fix D (DRPROPHFIRST)** is the settle lane's pick. It meets the G2 bar vs 464a4b75: landing == final 100 vs 99,
hybrids 1 vs 1, regret 17.2 vs 17.1.
- **What it does:** a PROPH-armed pill that is still on its spawn row, not committed, not DONE, and has
  WDOG2 < MIN_THINK pulses PROPH INSTEAD of running the rotation pre-phase and the MIN_THINK hold.
- **Window:** [F0, min(GO + 6 f, leaving the spawn row, DONE)), in PROPH's own direction, at the TAP rate.
- **After the window:** rotation, then the answer's lateral steering.
- **Measured:** 4 presses, commit at their f10 median = our **f11**.

**Modelled as:**
- **steer:** `proph_first_end = 11`. An armed pill gets t_ans = 11, and PROPH pulses while f < t_ans. If the capsule's
  row > 0 at a decision frame, t_ans = that frame. Rotation and lateral start at t_ans (the declared limitation).
  p_end = None for D arms, so the window is not cut at 4.
- **mask (refit):** `LEDGE_T = 11` and `PROPHFIRST`. An armed board's commit is TL = min(11, G0 + thr + 1), the
  closed-form spawn-row exit, and PROPH is credited on [F0, TL).
- **DONE** before GO + 6 is not modelled. The search rarely DONEs that early (anytime replay: 1% by GO + 6 f).

**Block 3 arms** (600 per cell; gb10, rc10, lulu10):
- `fD_a2`, `fD_bdep2`, `fD_bref2`, `fD_c2` (unchanged from the first amendment);
- **`fD_brefD`** (fair, refit mask T13 / G0 3, D driver);
- **`fD_bdepD`** (fair, DEPLOYED fw mask T19 / G0 8, D driver). The next couch build may pair D with the current fw.

Block 4 is unchanged. **Total: 6 × 1,800 + 1,200 = 12,000 games.**

**Analysis** (`analyze_steer8b2.py`):
- Each arm vs a2. These 5 comparisons plus block 4 make 6 gb10 comparisons, so Bonferroni is **99.17%**.
- **Decomposition:**

| comparison | what it shows |
|---|---|
| c2 − a2 | minus the pin's worth |
| bref2 − c2 | the settle cut under fair gravity |
| bref2 − bdep2 | the mask refit |
| brefD − bref2 | fix D under the refit mask |
| bdepD − bdep2 | fix D under the deployed mask |
| **brefD − bdepD** | the mask under D: can D ship on the current fw? Status quo unless the CI excludes 0 |

- The a2-vs-fD discordance count is reported.

**Gates (before this commit):**
- **Mask vs frame sim:** `b-ref+D` is a consistent config and agrees **100.000%** (840 boards, 11 armed, 352 armed
  candidates).
- **Deployed mask vs the D driver:** 8 mismatches, all armed (97.7% armed agreement). Without D it is 24, i.e. 93.2%.
- **Identity after the D edits:** fA_off gb and fD_off rc47 still match the banked python rows (2 + 2). STEER7's
  `steer7_dlat` S=0 still matches STEER6d (2/2).
- **The D arms run, and D is active:** `fD_bdepD` LULU seed 39134 fires PROPH 34× vs 1× under the first-amendment arm
  on the same seed.
