# PREREG (2026-09-28): STEER6d — dist_target60 under its MEASURED whole-decision latency distribution

Written and committed BEFORE any STEER6d game. Requested by the coordinator before shipping the built DRDIST.

## Why
reachbuild built dist_target60 (h16 `190cb12b` ANTIBODY_DIST_BUILD.md; dr-mario-te `dist-target` `1f430974`).
- **Engine cycles per command are identical (0 added).**
- **Whole-decision endgame latency still shifts**, because the term changes what the search does (tuck extension,
  top-k work).
- Measured over **437 real endgame boards** (real copro6502 co-sim, DRDIST fw vs ANTIBODY fw, both on the DIST RTL):
  mean −0.07 f, median +0.005, p95 +2.73, **max +12.8**, min −7.4.
- STEER6c priced latency at ≈ 2.7 pp tap-out per frame on every decision, so the tails could matter.
- The per-board deltas are banked in `steer6/endgame_latency_deltas.json`, extracted from reachbuild's
  `tmp/fwcosim_end` via their `analyze_endgame_latency.py` loader.

## Design (`steer6_dlat_dist.py`)
**How the latency is applied.**
- On every ACTIVE decision (root viruses ≤ 4), one delta is drawn from the 437 per-board values (deterministic per
  board) and converted to whole frames by stochastic rounding.
- It moves:
  - the steer answer frame (clamped ≥ F0 = 3);
  - the reach-mask T_LAT;
  - vs_race BASE_F;
  - the gate-(b) clock.
- Inactive decisions run at nominal latency.
- Identity: with delta ≡ 0 it reproduces the screen rows (2/2 after a JSON round-trip).

**Variants.**
- **full**: the measured distribution.
- **clip**: draws above the p95 (+2.73) are replaced by the p95. **full − clip = the tail's contribution.**

**Cells** (seeds 37934–39132, 600 paired, vs banked ANTIBODY rows):
1. gate (b), OWNER-0804;
2. race lam 6, M 177, δ 2.65 (the STEER5d/6 instrument);
3. the **LULU race**: lam 4.7, M 140, δ 2.65.

2 variants × 3 cells × 600 = **3,600 games**.

## Bar (on the FULL variant; 95% seed-bootstrap CIs, paired vs ANTIBODY)
**PASS** iff all three hold:
1. gate-(b) tap-out Δ upper CI **< 0**;
2. race (lam 6) Δ lower CI **≥ −2 pp**;
3. LULU race Δ lower CI **≥ −2 pp**.

tap≤100 is reported. It cannot move, because the term and its latency are off above 4 viruses.

**Also reported:**
- **Tail contribution:** full − clip, paired, for tap-out and both races.
- **Latency cost:** full − dist_target60@nominal (the screen / opponent-suite rows).

**Reading declared now.**
- If full passes, the measured latency distribution does not undo the gain, and ship proceeds on this axis.
- If full fails but clip passes, the TAILS bite. The build then needs a tail cap before shipping: an effort bound
  on the tuck extension / top-k in the endgame.
- If both fail, the latency does not survive even without its tail, and ship does not proceed.
