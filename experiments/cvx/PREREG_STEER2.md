# PRE-REG (2026-09-25, written BEFORE any STEER2 arm runs): re-check what ships, under real steering

Every earlier shipping decision assumed perfect execution or looked only at tap-out: CHAIN540 over 180, rejecting
the holes80 leaf, and STEER1's arm-5 fix. STEER2 re-checks dose × reach-root with the couch steering model
(`steer_model.Steer(proph="throat")`, gated in STEER1) on BOTH instruments.

Instrument changes since STEER1:
- `vs_race.play(..., steer=)` hook: the executed placement goes through `probe_placement` (sends) and `env.step`;
  a non-straight landing is forced for both calls.
- `vs_race` arms `fw_winner_reach` / `fw540_reach` = `cascade_reach_x.ReachAwareDecider` at chain 180 / 540.
- **G0 PASS:**
  - steer=None is unchanged: 4/4 vendored fingerprints.
  - The regenerated vsrace2 fw540 rows equal the banked ones field for field; only the CLI's added `"level"` key
    differs.
  - The vsrace_l15 fw540 row is byte-identical.
  - The STEER1 couch arm is byte-identical (md5 `ec5501cf`).
- Race time keeps the silicon-calibrated cart clock (45 + 2·fall_rows + 40·cascade f/ply) computed on the EXECUTED
  placement. Steering changes where pills go (hence sends, clears and fall rows), not the per-ply clock model.

## Cells (all steering ON)
**A. SURVIVAL:** gate (b), OWNER burst model, L11 MED, cap 600, n=600 paired seeds 36734.. step 2.
- S1 fw540: banked as STEER1 `couch`.
- S2 fw540 + reach: banked as STEER1 `reach`.
- S3 fw_winner (chain 180): new.
- S4 fw_winner + reach: new.

**B. RACE:** vs_race lam 6, n=300 paired seeds 36734.. step 2, all four cells (R1 fw540, R2 fw540_reach,
R3 fw_winner, R4 fw_winner_reach). Scored vs a 177-s human (σ 0.15) at δ 2.65 (PRIMARY, fitted) and δ 2.0, plus
break-even pace. Context: the banked perfect-execution rows (vsrace2 fw540 / fw_winner, same seeds).

**C. L15** (level robustness): gate (b) L15, n=300 paired seeds 40134.. step 2, fw540 vs fw540 + reach.

## Endpoints
PRIMARY: paired diffs, seed bootstrap 95% CI.
- Survival: tap≤100 (couch-like) and whole-game tap-out.
- Race: VS win rate at δ 2.65.

Contrasts:
- reach effect per dose: S2−S1, S4−S3, R2−R1, R4−R3;
- dose under steering: S1−S3, S2−S4, R1−R3, R2−R4 (does 540 still beat 180 once execution is real?);
- L15: reach − no-reach.

## Bar to RECOMMEND building the reach-root firmware
For the dose it would ship with, BOTH:
1. survival: tap≤100 paired diff (reach − no-reach) has its 95% CI entirely below 0;
2. race: the VS-race paired win diff (reach − no-reach) at δ 2.65 has its LOWER 95% bound ≥ −2 pp. That is the
   DOSE2 non-inferiority rule ("upper CI ≤ +1 pp" on tap-out), mirrored for a higher-is-better endpoint with a
   2 pp margin.
δ 2.0 and the L15 cell are reported as robustness. A failure there is flagged but doesn't veto.

**Dose pairing rule.** Default is 540 (the incumbent couch build). Switch to 180 only if, both with reach:
- 180's tap≤100 is lower than 540's with the CI entirely below 0; AND
- 180's race win is not worse than 540's by more than 2 pp (lower bound of 180−540 ≥ −2 pp).
If 540's own reach cell fails the bar and 180's passes, recommend 180 + reach.

## Declared limits
- Same as STEER1: no anytime running-best or slam-to-intermediate in the model; the owner's garbage model;
  1 couch death anchors the calibration.
- Race pace comes from the calibrated clock, not from the steer model's frame counts.
