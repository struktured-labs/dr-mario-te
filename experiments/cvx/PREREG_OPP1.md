# PREREG (2026-09-26): OPP1 — does anything we'd ship collapse against a deliberate opponent?

Written and committed BEFORE any OPP1 game on the analysis block (smoke/identity runs only, listed below).

## Builds (steering ON: couch P2 driver model, unified DRTAPP=2 taps, `steer_model.py`)
| label | what | code |
|---|---|---|
| **base** | the shipping REACH+TAP build (CHAIN540 + reach-masked root, tap P=2) | `steer_run.make("s4_base")` |
| **hsv** | base + the HSV leaf term at W=512 (STEER5d PASS) | `steer_run.make("s5b_hsv512")` |

## Opponent profiles
| profile | model | code | status |
|---|---|---|---|
| **OWNER-0804** | `fit_struktured_20260804` bursty: fire LINKED to the AI's clears | `opp_models.OwnerBursty` = gate_b's injection | **banked** (STEER5d rows); the **COMMON BLIND BASELINE** |
| **OWNER-2026-09** | refit `owner_fit_202609.json` (`a46b8ba`): INDEPENDENT renewal process (not linked to AI clears, phase-flat), empirical L11 gaps ÷ 2.08 s per AI placement, size pmf {2:.854, 3:.024, 4:.122}, p_double .016, fitted column split | `opp_owner202609.py` | new |
| **STRIKER H5 / H6 / H8** | lulu147 striker PORTED (`striker_model.py` @1049308, AST-identical helpers): earns volleys with the bursty-v1 fire/size draws on the AI's clears, BANKS them, releases ALL when the AI's scaffold height ≥ H or the oldest has waited 9 placements | `opp_models.Striker` | new |
| **LULU (the RACER)** | vs_race modelled human: pace median M ∈ {140, 160, 177} s (σ .15), volleys Poisson **lam 2/min** (Hartford sizes), damage δ 2.65 s/tile (δ 2.0 reported) | `steer_race.py … 2.0 … 11 2 unified` | new |
| PRO | — | — | **SKIPPED**: the pro tape's send data is unusable (garbage-VS format unconfirmed, 1 fps); a fit is not cheap |

- LULU is bracketed, not fitted. The 0808 fit JSON pools both players and its raw events were stripped, so there
  is no cheap per-player pace/send fit.
- The dossier's claim that she "releases when scaffold tall" is unconfirmed. The striker profiles cover that
  behaviour as a stress test, not as a model of her.

### Pre-launch checks (already done, not on the analysis endpoints)
- **Striker port gate:** at H=5/6/8, no release fires below H unless the timeout triggers (0 violations). A mutant
  that releases at any height is KILLED (13 violations).
- **OWNER-0804 identity:** `opp_run.py` with OwnerBursty(0804) reproduces the banked gate_b rows field-for-field:
  4/4 on 36734 (STEER4/5 rows) and 6/6 on 37934–37938 (STEER5d rows, both builds).
- **OWNER-2026-09 smoke** (s4_base, 12 seeds on the selection block 36734):
  - 0.180 volleys per eligible placement, against 0.184 volleys per AI placement on the couch.
  - 1.78 cells land per volley against 2.27 drawn. The shortfall is volleys whose column top is full; they are
    skipped, which is the same drop rule every profile uses.

## Seeds — DECLARED REUSE, independent of hsv's selection
- **Gate (b):** 37934–39132, even, step 2 → **600 paired seeds**. The OWNER-0804 cells for both builds are the
  banked STEER5d rows.
- **Race:** the same 600 seeds.
- Registry: consumed by the cvx champion-search lane and by STEER5d. The OPP1 reuse is noted on that entry
  (2026-09-26).
- The STEER4/5 selection block 36734–37932 is excluded.
- Gate (b) conditions are unchanged: L11 MED, cap 600, garbage from placement 25.

## Endpoints (per build × opponent cell)
- **Whole-game tap-out** (topout).
- **tap≤100** (topout at ≤ 100 pills).
- **Clear rate.**
- **LULU:** race win (`vs_race.evaluate`), at every M × δ. Secondary: tap-out (`how == topout`) in the lam-2 race
  rows.

## Comparisons (all paired by seed, 4,000-resample seed bootstrap, 95% CIs; NO gates — this is a characterisation)
- **A. Opponent effect per build:** each opponent minus the COMMON BLIND BASELINE OWNER-0804, same build, same
  seeds.
  - Reconciliation rule: never against an arm-specific volume-matched control.
  - The striker's earned volume is identical to the blind baseline's by construction (the same draws). Only the
    TIMING differs, minus whatever is still banked at game end, which is reported.
- **B. hsv − base per opponent.** Does the STEER5d win hold, flip or vanish against each opponent?
- **C. LULU:** base and hsv win rates at M 140/160/177 × δ 2.65/2.0, and hsv − base at each point.

## Pre-declared reading
**COLLAPSE (a build × opponent cell) =** either of the following, against the common blind baseline:
- whole-game tap-out rises by **≥ +10 pp** with CI lower > 0; or
- tap≤100 rises by **≥ +3 pp**, with CI lower > 0, AND at least doubles.

**hsv FLIPS against an opponent =** hsv − base whole-game tap-out CI lower > 0 (hsv significantly worse). The same
test applies to tap≤100. Otherwise, **hsv holds**.

**LULU:**
- Report where each build's win rate crosses 50% on the M bracket.
- "hsv flips vs the racer" = hsv − base race win CI upper < 0 at any bracket point.

**Power:** n = 600 paired. For whole-game tap-out, the SE of a within-build opponent contrast is ≈ 2 pp, so the
≥ +10 pp collapse bar is detectable with near-certainty. hsv − base per opponent has SE ≈ 2.3 pp, so it detects a
flip only if the flip is ≳ 5 pp. A null there is "no large flip", not "no flip".

## Execution
- **Split:** Hetzner (4 workers, systemd-run) and local (nice 19, ≤ 4 workers; the owner records OBS on this box).
- **Exactness gate before trusting remote rows:** module md5s must match. Per new opponent × build, 2 seeds must
  produce md5-identical rows locally and remotely.
- **Estimated wall time:** 4,800 gate-b games + 1,200 race games. That is ≈ 1–1.5 h at the STEER5d rate.
- **Files:**
  - code: `opp_models.py`, `opp_owner202609.py`, `opp_run.py`;
  - rows: `opp1/{local,remote}/`;
  - analyzer: `analyze_opp1.py`;
  - result: `RESULT_OPP1.md`.
