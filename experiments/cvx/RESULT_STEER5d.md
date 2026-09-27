# RESULT (2026-09-26): STEER5d — HSV512 PASSES the powered non-inferiority check (and helps the race)

Pre-reg: `PREREG_STEER5d.md` (committed `7d8d8a5` before any 5d game).
- **Arms:** hsv512 (`cascade_leaf5b_x`, the HSV leaf term at W = 512) vs the shipping REACH+TAP baseline. Both run
  with unified DRTAPP=2 steering.
- **Seeds:** DECLARED REUSE of older blocks not used to select hsv (37934–40932, 33000–34198, 26280–26958,
  60348–60998), plus the banked fresh-464 pairs. The selection block 36734–37932 is excluded.
- **Exactness:** local and Hetzner code hashes match for all 11 modules, and per-instrument game md5s match (gate b
  `d3a96a67`, race `bb080382`).

| endpoint (paired, seed bootstrap) | n | base | hsv512 | Δ [95% CI] | bar | met |
|---|---|---|---|---|---|---|
| whole-game tap-out (gate b, OWNER, L11) | 2,564 | 26.44% | 24.80% | **−1.64 [−3.86, +0.70]** | upper ≤ +1.5 | ✅ |
| race win δ 2.65 (vs_race lam 6, 177-s human) | 3,066 | 66.60% | 68.95% | **+2.35 [+0.23, +4.44]** | lower ≥ −2 | ✅ |
| tap≤100 (reported) | 2,564 | 5.30% | 3.04% | **−2.26 [−3.35, −1.21]** | expected < 0 | ✓ |
| race win δ 2.0 (reported) | 3,066 | | | +1.63 [−0.52, +3.72] | | |

**Verdict: PASS.**
- **Early tap-outs fall about 43%** (5.3 → 3.0%) at every stage of testing. This replicates the STEER5b discovery,
  the 5c fresh holdout and this powered check.
- **Whole-game tap-out** is non-inferior, with the point estimate favourable.
- **The race improves**, with a CI entirely above 0: clear rate 67.2 → 70.2%.
- The race bar was the hard one (≈ 50% power at a true 0). It passed with margin.

**Evidence trail for hsv:**
- STEER5b: post-hoc discovery, n = 600, reuse.
- STEER5c: fresh 464 confirmatory; tap≤100 replicated, non-inferiority underpowered.
- STEER5d: this powered check, n = 2,564 / 3,066, on blocks independent of the selection.
All three are sim-only, under the steering model and the OWNER garbage model.

## Build note
The parallel RTL fork recorded `893aeb8`: "CHAIN540+REACH+TAP+HSV: FAILED timing at seed 13 (copro −0.494 vs
+0.10 bar)".
- The fold noted in RESULT_STEER5c avoids adding a combine input. It puts −512 per high spawn-column virus into
  LeafEval's existing pre-scaled `matched60` accumulator in S_COLWALK (signed, about +2 bits) and leaves S_DONE2's
  adder tree unchanged.
- If the failed fit added a new term to S_DONE2, the fold is the first thing to try.
- Remember the seed noise (0.076–0.380 ns): one fit is n=1, so sweep seeds before concluding.

Files: `analyze_steer5d.py`; rows in `steer5d/{local,remote}/` (gate b `gb_*`, race `rc_*`).
