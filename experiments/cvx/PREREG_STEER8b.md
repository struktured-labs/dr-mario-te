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
