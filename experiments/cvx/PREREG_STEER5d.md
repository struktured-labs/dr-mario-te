# PRE-REG STEER5d (2026-09-26, written BEFORE any 5d game runs): POWERED non-inferiority check of HSV512

**Arms.**
- `s5b_hsv512`: the HSV leaf term at W = 512 (`cascade_leaf5b_x`).
- vs `s4_base`: the shipping REACH+TAP brain (fw540 + `reach_fw_tap(tap=2)` mask) with unified DRTAPP=2 steering.
- Identical code otherwise. Local and Hetzner code hashes match for all 11 modules; per-instrument game md5
  gates run at launch.

## Seed policy: DECLARED REUSE of older blocks NOT used to select hsv
The STEER4/5 selection block 36734–37932 is EXCLUDED. `seed_registry.py --check` confirms each block as consumed by
the owners below: reuse, declared. The blocks are 2,766 distinct streams, with no alias seed (35208 excluded) and no
overlap with 36734–37932.

| block (even seeds, step 2) | streams | prior owner (registry) |
|---|---|---|
| 37934–40132 | 1,100 | cvx champion-search lane: convex-height valid tail + scval (spawn-lane validation) |
| 40134–40932 | 400 | cvx end_screen (L11) and STEER2/DOSE2 L15 cells (a different level) |
| 33000–34198 | 600 | H12 substitution arm (Aug) |
| 26280–26958 | 340 | cvx run 13 holes-alone confirmation blk A |
| 60348–60998 | 326 | cvx run 13 blk B |
| **fresh 464** (4002–4462, 40934–41098, 17000–17098, 17300–17398, 20900–20998) | 464 | the STEER5 control / STEER5c confirmatory block (banked pairs INCLUDED) |

**Samples.**
- **GATE (b):** OWNER model, L11 MED, cap 600, paired baseline vs hsv512.
  - Seeds 37934–40132 + 40134–40932 + 33000–34198 = **2,100 new pairs**.
  - Plus the banked fresh 464 pairs = **2,564 paired**.
- **RACE:** vs_race lam 6, unified tap steering, scored vs the 177-s human at δ 2.65 (δ 2.0 reported).
  - Seeds 37934–40932 + 33000–34198 + 26280–26958 + 60348–60998 = **2,766 new pairs**.
  - Plus the banked fresh 300 pairs (STEER5c) = **3,066 paired**.

## BARS (on the full 5d sample above)
1. **Whole-game tap-out** paired Δ (hsv − base): **upper 95% CI ≤ +1.5 pp**.
2. **Race win (δ 2.65)** paired Δ: **lower 95% CI ≥ −2 pp**.
3. **tap≤100** paired Δ is reported alongside (expected < 0; not a gate).

**PASS iff 1 AND 2.** Seed-bootstrap CIs (4,000 resamples), paired by seed.

## Honest power (from the STEER5c SEs scaled to n)
- **Tap-out:** SE ≈ 1.15 pp at n = 2,564, so the bar needs an estimate ≤ ≈ −0.75. That is ≈ 90% power if the true
  effect is the pooled −2.3 pp, and ≈ 26% if it is 0.
- **Race:** SE ≈ 1.03 pp at n = 3,066, so the bar needs an estimate ≥ ≈ 0.
  - ≈ 50% power if the true race effect is exactly 0, ≈ 5% if it is the 5c point estimate of −1.7.
  - 80% power at a true 0 would need ≈ 6,400 paired race games.
  - ⇒ **A race FAIL is weak evidence; a race PASS is meaningful.**

**Compute and wall time (posted up front).**
- ≈ 9,700 new games: 4,200 gate b + 5,532 race.
- Hetzner (4 procs, ≈ 50 games/min) takes ~40%; local (`nice 19`, ≤ 4 workers, ≈ 75 games/min) takes ~60%.
- **Estimated wall time ≈ 80–110 min.** Race games are shorter, so nearer the low end.
