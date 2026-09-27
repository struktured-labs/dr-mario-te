# PRE-REG (2026-09-26, before any STEER4 arm runs): board-shape levers under the REAL regime (shipping REACH+TAP build)

**Why.** Couch forensics on REACH+TAP (`experiments/couch_forensics/RESULT_COUCH_TAP.md`) put both tap-outs on the
BRAIN's board shape: high viruses in spawn columns 3–4 (and 5) get buried into towers. Every earlier board-shape screen
(stall breaker, maxh24, burial ×2, toprisk) ran with perfect execution, where tap-out was ~2%, so there was no signal.

## Baseline = the shipping couch build in sim
- **Brain:** fw540 + reach mask `reach_fw_tap.reach_mask_fw(tap=2)` (the shipping rule), root pre-filter.
  Decider `cascade_shape_x.ShapeReachDecider` at zero doses. The zero-dose selfcheck is identical to the masked
  decider on 311/311 boards.
- **Execution:** `steer_model.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True)`. This is NEW: the
  shipping DRTAPP=2 cart runs every press (PROPH, rotation, lateral) through one scheduler, ≥ P frames apart;
  soft-drop is held.
  - Differs from STEER3's P=2 cell (rotation 1/frame, lateral 1 frame after it) by 1–2 frames on rotated moves.
- **G1' consistency check:** the unified frame simulator (answer at T_LAT = 19) vs `reach_fw_tap(tap=2)`, strict
  landing, on 738 boards from baseline games: **100% of candidates for pill < 300**. The only mismatches (0.4%
  overall) are at pill ≥ 400, the near-instant-gravity tail couch games never reach.
- Execution samples the silicon answer latency (p10 f15, median f19, p90 f26) while the mask assumes f19. So in
  sim, as on silicon, a late answer can miss a target the mask allowed (the k61 mechanism).
- **G0:** `tap_unified=False` and every earlier arm unchanged. Checked before launch: fingerprints, couch
  `ec5501cf`, STEER1 pulse/reach rows.

## Arms
gate (b), OWNER model, L11 MED, cap 600, n=600 paired seeds 36734.. step 2 (declared reuse). Paired vs the baseline.

| arm | lever | doses | firmware-only? |
|---|---|---|---|
| (1a)/(1b) `s4_sv180` / `s4_sv540` | spawn-column virus priority: `val += w_sv·nv` iff the placement's span meets cols 3–5 and its upper cell lands at row ≤ 9 (parent tops) | w_sv 180 (×2 a virus's root value) / 540 (×4 = one chain step) | **YES**: nv = LEV_RVV (existing register); landing row and span come from the parent LIVE board the firmware already holds |
| (2a)/(2b) `s4_sp100` / `s4_sp300` | spawn-lane height, UNGATED: `val −= w_sp·max(0, spawn_h(parent+placed) − 10)` iff the placement clears nothing (LEV_RVC = 0 ⇒ the child IS parent+placed, the DRVETO argument); else 0 | w_sp 100 / 300 per row (300 = the failed gated sb_spawn dose) | **YES**: LEV_RVC + LIVE + candidate |
| (3) `s4_rot2` | mask rotation conservatism: the first rotation slot is 2 frames later for candidates that rotate (the k61 fix) | +2 f | **YES**: a mask constant |
| (4) `s4_combo` | the best of (1a/1b/2a/2b) + (3) | — | YES |

Not tested, because they need RTL: exact region virus counts and the child's spawn height after clears. The
engine does not expose the resolved child board to the firmware.

**Arm (4) selection rule (fixed now).** Among (1a, 1b, 2a, 2b), take the most negative paired tap≤100 point
estimate (tie → whole-game tap-out). Combine it with (3). Run it after (1)–(3) finish.

## Endpoints and bar
- **PRIMARY:** tap≤100 (tap-out within the first 100 pills) and whole-game tap-out, paired vs baseline,
  seed-bootstrap 95% CI.
- **PASS** = one primary CI entirely below 0 AND the other primary's upper CI ≤ +1 pp.
- **SECONDARY, passing arms only:** VS race lam 6, n=300, vs the 177-s human at δ 2.65 / 2.0. Recommend only if
  the win-diff lower bound is ≥ −2 pp (the STEER2 rule).
- This is a SCREEN on reused seeds with 5+1 arms: a pass recommends a holdout (fresh seed block) before any build.

## Compute
- Hetzner rbm-train-2 (IRON RULE: service control only; local↔remote game md5 exactness gate) for 4 arms.
- Local at `nice 19`, ≤ 4 workers: the owner records OBS on this box.
