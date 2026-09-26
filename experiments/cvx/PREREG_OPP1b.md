# PREREG (2026-09-26): OPP1b — confirm or refute the hsv flip against the LULU racer

Written and committed BEFORE any OPP1b game.

## Why
OPP1 (`PREREG_OPP1.md`, RESULT_OPP1.md) fired a pre-declared flag: **hsv FLIPS vs LULU**.
- **Race win (vs_race, lam 2, M 140, δ 2.65):** hsv − base **−3.83 [−7.50, −0.50]**, n = 600 paired, seeds
  37934–39132. Upper CI < 0 at 3 of 6 bracket points.
- **Race-row tap-out:** +3.50 [+0.33, +6.83].
- **Mechanism, descriptive only:**
  - The deficit is mostly **loss_race** (54 → 73), i.e. the bot is slower. **loss_kill** moves only 14 → 18.
  - The hsv-only kills are LATE: median t_end 662 s, median 3 viruses left.
  - This reverses the STEER5d direction at lam 6 on the same seeds, where hsv was +1.2 pp at M 177.

**Why this is not yet a verdict:**
- OPP1 made ≈ 11 comparison families, so ≈ 0.5 false flags are expected at α = .05.
- The "any bracket point" rule is lenient: the 6 points reuse the same rows.
- A confirmatory test on independent seeds is cheap, so it is run instead of arguing.

## Design
- **Builds:** as in OPP1 (`s4_base`, `s5b_hsv512`), unified DRTAPP=2 steering.
- **Instrument:** `steer_race.py ARM 2.0 LO CNT 2 OUT 11 2 unified`, identical to OPP1 LULU. Exactness is
  inherited: OPP1's race rows matched local vs remote md5-for-md5, and the code hashes are unchanged.
- **Seeds (declared reuse, disjoint from OPP1 and from the hsv selection block 36734–37932):** the STEER5d race
  blocks minus OPP1's 600. Even seeds, step 2:
  - 39134–40932: 900
  - 33000–34198: 600
  - 26280–26958: 340
  - 60348–60998: 326
  - **Total: 2,166 paired.** The lam-6 rows for these seeds are already banked (STEER5d), so lam 2 vs lam 6 on the
    same seeds is available descriptively.

## Primary endpoint and decision rule
- **Primary:** hsv − base race win at **M 140, δ 2.65**, paired seed bootstrap (4,000).
  - **Flip CONFIRMED** iff the upper 95% CI < 0.
  - Otherwise **NOT CONFIRMED**: the OPP1 flag is treated as a likely false positive, and the pooled OPP1 + OPP1b
    estimate is reported beside it.
- **Secondary (reported, no gate):**
  - race-row tap-out hsv − base;
  - all 6 bracket points (M 140/160/177 × δ 2.65/2.0);
  - loss-type decomposition (race / kill);
  - the lam-2 vs lam-6 contrast on the same seeds.
- **Power:** the SE scales from OPP1 (≈ 1.8 pp at n = 600) to ≈ 0.95 pp at n = 2,166.
  - If the OPP1 point of −3.8 is true, detection is near-certain.
  - At a true −2 pp, power is ≈ 55%.
  - At a true 0, the false-confirm rate is 2.5%.

## Execution
- Hetzner (4 workers, systemd-run) plus local (nice 19, 4 workers). 4,332 games, estimated ~40 min.
- Rows go in `opp1b/{local,remote}/`; the analysis is appended to `analyze_opp1.py` as `--b`; the result is appended
  to `RESULT_OPP1.md`.
