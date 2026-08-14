# H12 calibration prep notes (2026-08-14, pre-verdict, descriptive only)

Measured on 199 seeds (30000-30199 ex 30001), champion const play, using the
rig's own `gate_fires()` (oracle_arm.py:153). 31,828 plies.

## 1. The draft's cost premise is wrong ~10x
Gate `d_spawn_h >= 12 OR viruses <= 8` fires on **56.1% of plies** (17,869/31,828),
not "a few %". An H12 top-4 rollout at every gated ply costs ~half an oracle run.
Calibration MUST either tighten the predicate or re-price the arm before endpoint.

## 2. Top-4 margin distribution at gated plies (champion value units)
| quantile | rank2 | rank3 | rank4 |
|---|---|---|---|
| 0.10 | 0 | 8 | 10 |
| 0.25 | 0 | 20 | 26 |
| 0.50 | 10 | 49 | 62 |
| 0.75 | 43 | 133 | 159 |
| 0.90 | 141 | 278 | 321 |

**>=25% of gated plies have an EXACT top-2 tie.** The near-tie world the certified
gaps live in (all 7 sat at champion ranks #2-#4) is frequent, not exotic.

## 3. Candidate tightened predicates for calibration to price
- gate AND rank2_margin == 0            (est. ~15-25% of all plies)
- gate AND rank4_margin <= 26 (q25)     (top-4 genuinely contested)
- gate AND near-tie AND viruses <= 8    (endgame-only variant)
Pick by fair-prize projection per the draft's mandatory sizing gate; the 7
holdout-certified fixtures (pending owner sign-off) are the acceptance test.

## 4. Context from the overnight arc
Certified core = CASCADE + ROUTE/DIG families; one-step static features CANNOT
express either (proto_cvd 1/7) — the rollout is the only known instrument.
