# RESULT (2026-09-26): STEER5 — no leaf term passes; spawn-column BURIAL pricing harms hard (burial96 again); post-hoc HSV (clear high spawn-col viruses) is a near-miss

Pre-reg: `PREREG_STEER5.md` (committed `4b0b08c` before any arm ran). Baseline = the shipping REACH+TAP build in sim
(the STEER4 base; `s5_base` reproduces the banked rows exactly). gate (b), OWNER model, L11 MED, n=600 paired seeds
36734.. step 2, seed-bootstrap 95% CIs vs the baseline. Pass bar: one primary CI entirely below 0 AND the other's
upper CI ≤ +1 pp.

| arm | leaf term | tap≤100 | Δ tap≤100 | tap-out | Δ tap-out | win | verdict |
|---|---|---|---|---|---|---|---|
| base | shipping REACH+TAP | 6.17% | — | 26.33% | — | 73.7% | — |
| s5_bur32 | BUR35 (non-matching cells over spawn-col viruses) ×32 | 8.00% | +1.83 [−0.83, +4.67] | 32.17% | **+5.83 [+1.00, +10.67]** | 67.8% | fail (harms) |
| s5_bur96 | BUR35 ×96 | 15.33% | **+9.17 [+5.83, +12.50]** | 52.00% | **+25.67 [+20.33, +30.83]** | 48.0% | fail (harms) |
| s5_acc60 | ACC35 (accessible spawn-col viruses) +60 | 6.17% | +0.00 [−2.50, +2.50] | 29.17% | +2.83 [−2.00, +7.67] | 70.8% | fail |
| s5_acc180 | ACC35 +180 | 8.67% | +2.50 [−0.33, +5.50] | 33.33% | **+7.00 [+2.00, +12.00]** | 66.7% | fail (harms) |
| s5_rb48 | R_BURIED +48 in cols 3–5 only (→ 96) | 7.17% | +1.00 [−1.67, +3.83] | 30.83% | +4.50 [−0.33, +9.33] | 69.2% | fail |
| s5_rb144 | R_BURIED +144 in cols 3–5 (→ 192) | 10.83% | **+4.67 [+1.67, +7.67]** | 47.50% | **+21.17 [+16.00, +26.33]** | 52.5% | fail (harms) |

No arm passes, so there is no race secondary and no RTL work.

**CONTROL (seed-reuse bias).** The baseline on 464 FRESH streams (registered at launch):
- tap≤100 4.96%: fresh − reused −1.21 [−3.95, +1.58];
- tap-out 27.37%: +1.04 [−4.28, +6.46];
- win 72.6%.

⇒ No detectable reuse bias at this resolution (±4–5 pp). The reused-block results stand, with that CI as the caveat.

**Reading.**
- **Every burial-pricing shape harms, and dose-dependently.** Restricting it to the spawn columns doesn't escape
  the burial96 lesson: pricing "covering viruses" makes the brain contort under garbage and pay in tap-outs.
- **Rewarding accessibility doesn't help either.** At the dose of a virus clear it harms.
- The leaf's existing burial calibration (R_BURIED 48, coef-opt) looks locally optimal under the real regime too.

## (a) Pre-treatment stratification (coordinator request): initial HIGH spawn-column viruses (cols 3–5, row < 9)
The stratum comes from the reset layout (`hsv_census.py`), so it is pre-treatment and legitimate. Distribution on the
reused block: 2–9, mostly 4–7.

| initial count | reused block (n) | tap≤100 | tap-out | fresh control (n) | tap-out | POOLED (n) | tap-out |
|---|---|---|---|---|---|---|---|
| ≤4 | 134 | 4.5% | 29.9% | 112 | 19.6% | 246 | 25.2% |
| 5 | 183 | 5.5% | 24.0% | 136 | 24.3% | 319 | 24.1% |
| 6 | 171 | 8.2% | 24.6% | 125 | 32.8% | 296 | 28.0% |
| ≥7 | 112 | 6.2% | 28.6% | 91 | 34.1% | 203 | **31.0%** |

- **A weak, noisy dose-response in sim.**
  - The reused block is flat. The fresh block rises (19.6 → 34.1%).
  - Pooled (n = 1064), ≥7 vs ≤5 is **+6.4 pp [−1.0, +14.0]**.
  - Mean initial count is 5.46 in tapped-out games vs 5.36 in survivors.
- The couch contrast (7 high viruses in both deaths vs 2–5 in the healthy games) is directionally consistent, but the
  simulated layout effect is small against a 25% base rate. So the layout is a modest risk factor, not a dominant
  one. The couch's sharper split may be n = 6 noise, or a mechanism the owner model lacks (the human timing garbage
  onto an unfinished spawn column).
- **No arm's effect concentrates in the high-count stratum.** Within-stratum paired effects are listed by
  `strata_steer5.py`. The harming arms harm in every stratum.

## (b) STEER5b (post-hoc, PREREG_STEER5b.md): see RESULT_STEER5b section below

**Post-hoc** (pre-registered `e76eb7f` after STEER5 failed, before running). HSV leaf term = −W·#(viruses in cols 3–5 at
row < 9) remaining in each leaf board: "clear the high spawn-column viruses first", active only while they exist.

| arm | tap≤100 | Δ tap≤100 | tap-out | Δ tap-out | win | verdict |
|---|---|---|---|---|---|---|
| base | 6.17% | — | 26.33% | — | 73.7% | — |
| s5b_hsv180 | 5.00% | −1.17 [−3.67, +1.50] | 23.83% | −2.50 [−6.67, +1.83] | 76.2% | fail |
| **s5b_hsv540** | **3.17%** | **−3.00 [−5.33, −0.67]** | 23.67% | −2.67 [−7.50, +2.33] | 76.3% | **fail (near-miss)**: tap≤100 CI < 0, but the tap-out upper CI is +2.33 > +1 |

- **The first leaf/root term in STEER4–5 with both point estimates negative** and one CI excluding 0. It is also
  directionally consistent with the couch contrast: prompt clearing of high spawn-column viruses.
- It did not pass the pre-registered bar, and it is post-hoc on the reused block, so no build recommendation.
- Within-stratum effects are negative in all four hsv9 strata (e.g. hsv540 tap≤100 −3.7 / −2.2 / −3.5 / −2.7).
  The benefit is NOT concentrated in the high-count stratum. It acts as a general "clear spawn-column viruses
  early" prior.
- **Next step if pursued:** a paired holdout on the fresh 464-stream block, where the baseline control is already
  banked, so only the hsv arm needs running (~15 min). It is underpowered for tap≤100 (base ≈ 5%, CI ≈ ±3 pp), so
  pooling it with this block is the honest read.

**RTL sketch for HSV (the only near-candidate; no RTL owed since nothing passed).**
- **Per leaf:** a region-gated count of virus cells in cols 3–5 × rows 0–8 (27 fixed cells). The column walk
  already sees each cell's virus bit, so this is one region mask plus a ≤5-bit counter.
- **Delta path (CMD 6/7):** a non-clearing placement never changes virus cells, so a child's HSV equals the
  parent's. Latch it in BASE for zero delta cost. Clearing children take the full NODE eval, which includes the
  counter.
- **Combine:** one more subtract. 540 = 1000011100b (popcount 4); **512 (popcount 1)** is the RTL-cheap dose to
  test instead.
- Per [[dr-mario-leaf-has-no-timing-budget]] (slack 0.165 ns), a new combine input likely needs a pipeline
  stage, unless it is folded into an existing accumulator (it is a constant-weight virus count, so it could ride
  the matched/virus-count path).
- **Estimate:** tens of ALMs of logic; the cost is timing, not area.

## Finding while wiring (flag for the coordinator)
- The extra `_eval_rtl` terms (R_SPAWNCOL, R_ENDH, R_LANEW, R_EDGEW, R_HOLESREL, R_CVX) are **absent from
  `_combine_terms`**, the non-clearing delta leaf path. In the chain search they would apply only at clearing
  leaves.
- No banked chain-brain arm used them: all `vs_race` chain arms are `winner` / `winholes80` trunks, so this is
  latent.
- Any future chain-brain use of those terms must add them to the delta path, as STEER5 did for its own terms
  (`cascade_leaf5_x`).

**Files:**
- Deciders: `cascade_leaf5_x.py` (STEER5 code of record), `cascade_leaf5b_x.py` (5b).
- Stratum: `hsv_census.py`, `steer5/hsv_census.json`.
- Analysis: `analyze_steer5.py`, `strata_steer5.py`.
- Rows: `steer5/{local,remote,control,b_local,b_remote}/`.
