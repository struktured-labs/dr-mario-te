# PREREG (2026-09-27): STEER6b — powered confirmatory holdout for the three screen passers

Written and committed BEFORE any STEER6b game.

## Why
The STEER6 screen (`RESULT_STEER6.md`, `fcb00c97`; 600 seeds, 5 arms) passed three clearing-distance arms against
ANTIBODY:

| arm | tap-out Δ | race Δ | churn (fixed / new) |
|---|---|---|---|
| (a) `s6_dist_end60` | −6.00 [−8.50, −3.50] | +6.17 | 48 / 12 |
| (c) `s6_dist_stall60` | −4.50 [−8.50, −0.50] | +9.67 | 91 / 64 |
| (d) `s6_dist_target60` | −4.17 [−6.67, −1.67] | +6.17 | 43 / 18 |

Five arms were screened on one declared-reuse block, so the passes must be confirmed on disjoint seeds.

## Design
- **Arms:** `s6_dist_end60`, `s6_dist_stall60`, `s6_dist_target60`. The code is unchanged since the screen:
  `cascade_leaf6_x.py` md5 `6dd0bf63`, `steer_run.py` `cf255327`, `stuck_probe.py` `8c2fa96e`.
- **Baseline:** ANTIBODY STEER5d banked rows. The stuck_probe path is identity-tested against them.
- **Gate (b):** OWNER-0804, L11, cap 600, unified tap-2 steering. Seeds **39134–40932 + 33000–34198** (even,
  step 2) = **1,500 paired**.
- **Race:** vs_race lam 6, M 177, δ 2.65. The same 1,500 seeds **+ 26280–26958 + 60348–60998** = **2,166 paired**.
- These are declared reuse, disjoint from the screen block 37934–39132 and from the hsv selection block
  36734–37932.

## Confirmation rule (per arm; 3 arms → Bonferroni: two-sided **98.33%** seed-bootstrap CIs, 4,000 resamples)
**CONFIRMED** iff all three hold:
1. whole-game tap-out Δ has its upper 98.33% CI **< 0** (superiority);
2. race win Δ has its lower 98.33% CI **≥ −2 pp** (non-inferiority);
3. tap≤100 Δ has its upper 98.33% CI **≤ +1 pp**.

Also reported (no gate): 95% CIs, churn (fixed / new), stall pills per game, endgame-stall deaths, and the
pooled screen + holdout estimate (descriptive).

**Power** (screen SEs scaled to n = 1,500):
- The tap-out SE is ≈ **0.8 pp** for (a) and (d). They differ from ANTIBODY only at ≤ 4 viruses, so the pairs
  are highly concordant. For (c) it is ≈ **1.3 pp**.
- At the screen's point estimates, the Bonferroni superiority test (z ≥ 2.39) has ≈ 100% power for (a) and (d),
  and ≈ 80% for (c).
- If the screen overestimated by half (winner's curse), power is ≈ 90% for (a), ≈ 55% for (d) and ≈ 25% for (c).

## Recommendation rule (declared now)
- Among CONFIRMED arms, recommend the **cheapest-RTL** arm whose holdout tap-out point estimate is within
  **1.5 pp of the best** confirmed arm.
- RTL cost order, cheapest first:
  1. (d) dist_target: one firmware-chosen virus; the leaf computes ONE D.
  2. (a) dist_end: ≤ 4 viruses per leaf.
  3. (c) dist_stall: up to every virus when active.
- The recommended arm then goes through the opponent suite:
  - gate b vs OWNER-2026-09, the lulu fit, and STRIKER H6;
  - the LULU race (lam 4.7, M 140);
  - each at n = 600 on 37934–39132, where the ANTIBODY rows are already banked or cheap.
- It also gets an RTL cost sketch.

## Execution
- Hetzner (4 workers, exactness already gated on this code: 10/10) plus local (nice 19, ≤ 4 workers).
- 3 × (1,500 + 2,166) = **10,998 games**, estimated ≈ 3 h.
- Rows: `steer6/holdout/{local,remote}/`. Analysis: `analyze_steer6.py --holdout`. Result: appended to
  `RESULT_STEER6.md`.
