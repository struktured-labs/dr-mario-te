# RESULT (2026-10-03): STEER6e — gating CHAIN / EXCAV in the endgame of ANTIBODY_DIST. Both arms FAIL.

- **Pre-registration:** `PREREG_STEER6e.md` (`1625e41e`), committed before any screen game.
- **Rows:** `steer6e/screen/`. **Analyzer:** `analyze_steer6e.py`, output in `steer6e/analysis.txt`.
- **Sample:** 600 paired seeds (37934–39132 even, declared reuse), gate (b) OWNER-0804 + race lam 6, unified tap
  steering. 3,600 games, local, nice 19.
- **Exactness:** the identity arm `s6_dist_target60` reproduces the banked STEER6 screen rows **1200/1200**
  byte-identical (outcome and stuck-probe fields).
- **Wiring guard:** each variant differs from DIST60 on banked couch endgame boards (chain0 13/51, fin 18/51); the
  identity arm differs on 0/51.

## Result (each arm vs identity, paired, 95% seed bootstrap)
**Baseline:** tap-out 18.83%, race win 74.33%. Brain finishing-move take rate at ≤ 4 viruses: 56.1%.

| measure | **s6e_chain0** (w_chain → 0 at ≤ 4) | **s6e_fin** (+ w_excav, w_hang → 0) |
|---|---|---|
| **E1** endgame pills, k4 → clear, both won | **−4.12 [−7.25, −1.06]** ✓ (n = 444; base 41.1) | −0.59 [−4.65, +3.64] ✗ |
| — the same in sim seconds | −23.7 [−37.2, −10.0] | −1.8 [−19.3, +16.6] |
| last-virus pills (k1 → clear) | −3.78 [−6.58, −0.94] | +1.19 [−1.93, +4.40] |
| endgame stall-pills / game (act ≥ 10, from ≤ 4 viruses) | **−6.3 [−9.9, −2.9]** (30.2 → 23.9) | +1.5 [−2.6, +5.4] |
| **E2** race win, M 177 δ 2.65 | **−3.00 [−5.50, −0.50]** ✗ | −2.50 [−4.67, −0.17] ✗ |
| race endgame seconds (t4 → clear) | −5.7 [−8.9, −2.1] | −5.1 [−8.9, −1.5] |
| tiles sent / race | **−7.53 [−8.76, −6.34]** | −7.71 [−8.88, −6.59] |
| **E3** gate-(b) tap-out | **+3.00 [+0.33, +5.67]** ✗ (churn 25 fixed / 43 new) | +0.67 [−1.83, +3.17] ✓ (28 / 32) |
| tap≤100 | +0.00 (identical, as required) | +0.00 |
| brain finishing take rate | 40.4% | **86.8%** |
| **verdict** | **FAIL** (E1 only) | **FAIL** |

**Post-hoc race sensitivity: damage per sent tile δ.**
- vs_race's docstring calls δ "assumed", but δ 2.65 s/tile **is fitted**: tape, n = 181 hits, 95% CI [0.95, 4.13]
  (memory `dr-mario-vs-race-endpoint`).
- δ = 0 lies outside that CI. It is shown only to isolate the tempo effect.

| δ | s6e_chain0 | s6e_fin |
|---|---|---|
| 0 | +3.00 [+0.67, +5.50] | +3.00 [+0.50, +5.50] |
| 1.0 (≈ fitted CI low end, 0.95) | −1.83 [−4.50, +0.83] | −1.33 [−4.00, +1.33] |
| 2.0 | −3.83 [−6.17, −1.50] | −4.50 [−6.83, −2.33] |
| 2.65 (fitted point) | −3.00 | −2.50 |

## Reading
**1. The owner's tempo complaint is real in the sim, and CHAIN540 is its endgame cause.**
- Turning the chain reward off at ≤ 4 viruses makes won endgames 4.1 pills (≈ 24 sim-s) shorter, the last virus 3.8
  pills shorter, and cuts endgame stall-pills by 6.3 per game.
- In a pure race with no garbage damage, that is **+3 pp** of race wins.

**2. The combos pay for themselves.**
- The endgame cascades send about **7.5 tiles per game**. At the instrument's δ 2.65 that damage is worth more than
  the tempo: race −3.0 pp.
- **Without the chain term, tap-out rises 3 pp** (43 new vs 25 fixed). The pill-only cascades are also what keeps a
  colour-starved board from filling.
- **Race over the fitted δ range:** at the CI's low end (≈ 1) chain0 is about break-even, −1.8 [−4.5, +0.8], i.e.
  null. At the fitted point it is −3.0.
- So **no δ in the fitted range turns the race positive.**
- The **E3 tap-out failure (+3.0 [+0.3, +5.7]) does not depend on δ at all.** The verdict cannot flip on δ.

**3. Forcing the finish (s6e_fin) is not the lever.**
- It finishes 87% of available finishes (vs 56%), yet endgames are not shorter and races are worse.
- The deferrals the couch decomposition found are mostly cheap: the deferred finish usually lands a pill or two later
  while the readiness and cascade structure pays out.
- **Per the pre-declared reading:** chain gating moves E1, the excav gate adds nothing to it, and the owner's chain
  hypothesis is the part that matters for tempo. It does not survive the non-inferiority bars.

**4. Nothing to ship from this screen.**
- Leave ANTIBODY_DIST's endgame as built.
- A chain re-weight is not worth a holdout on this evidence. Removing the chain costs tap-out regardless of δ.

## Caveats
- **Declared seed reuse** (STEER5d / OPP1 / STEER6 block). Two arms; a pass would have needed a holdout anyway.
- **Sim only.** The gate-(b) and race opponents are models.
- **The race point estimate depends on δ** (table above), but every δ inside the fitted CI gives a null or negative
  race result. The tap-out bar fails independently of δ.
