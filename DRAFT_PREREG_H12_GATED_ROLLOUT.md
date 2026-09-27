# DRAFT prereg — gated narrow rollout (H12, top-2) as a shippable re-ranker

**STATUS: DRAFT, CONDITIONAL, NOT SEALED, NOT AUTHORIZED TO RUN.**
This lane exists **only if** the Tier-A `ORACLE-DIST` verdict (in flight) returns GO. Per the
sealed decision rule, a DIST NO_GO closes root re-ranking for the historical policy and this
draft is archived unrun. Written 2026-08-13 while the endpoint is blinded, so the design cannot
be shaped by the answer.

## Why this shape, given everything banked

- **Horizon audit:** H≤8 reproduces the oracle's choice *worse than random*; H12 recovers ~49%
  (`ORACLE_HORIZON_SENSITIVITY.md`). The signal lives 12+ pills out. One-ply terms are dead
  seven different ways (stage-2, d_spawn tie arm, distilled teacher, DA knobs, regime gates,
  trajectory-feature screen).
- **Mechanism:** 478/489 oracle flips are virus-progress choices, and the trajectory screen
  shows the signature is **deferred clearing** — structure only a rollout sees natively.
- **Cost shape:** the gate fires on a few % of plies; two candidates; H12. That is ~100× cheaper
  than the oracle and the only rollout dose with any evidence behind it.

## Design (to be frozen only after DIST-GO)

- **Gate** (unchanged from the oracle prereg): `d_spawn_h >= 12 OR viruses <= 8`, evaluated on
  the current board.
- **Trigger thinning**: additionally require the champion's top-4 value spread ≤ G (G chosen on
  CALIBRATION seeds only, targeting a 1–3% ply-flip rate; frozen before endpoint).
- **Action**: roll the champion's top-4 candidates forward **H=12** pills with the real policy
  and **candidate-independent pressure (`exo_lulu_v1`)** — never the legacy coupled model, and
  never the realized schedule.
  ⚠ **CAPSULE OBSERVATION SET (corrected 2026-08-13 after the fairness screen):** the fork sees
  TRUE capsules only through the preview window (cur + next — what the copro actually has);
  beyond that, capsules are SAMPLED from the stream distribution, candidate-common per depth.
  The earlier "capsules-true" wording repeated the CEILING arm's convention, which is wrong for
  a SHIPPABLE re-ranker: the capsule-refork screen showed 7/10 single-flip advantages were
  selection-level seed-peeking ([[dr-mario-flip-fairness-screen]]); a policy rolled on true
  capsules selects on information the cart cannot have.
- **Selection**: survivor-with-virus-progress, exactly the oracle's rule, K=1 sample (bias
  direction stated in every quote: understates).
- **Comparator set**: base champion; treatment; **dose-matched label-blind null** (same gate,
  same thinning, uniform draw among the same top-4 — the natural null for a k-candidate re-ranker); shuffled-label mutant must fail the verdict gate.
- **Endpoints**: dies-ahead primary; bad-ends co-primary with stalls counted at parity with
  topouts; clear-rate non-inferiority sized honestly: **N = 9,000 paired seeds registered**
  (floor 7,826 at the stage-2 discordance; recompute from pilot discordance before sealing).
- **Provenance**: full per-flip schema (the arbitrated shared columns), runtime manifest
  fail-closed, ordered banking, blinded monitoring until 100% rows.
- **Policy semantics**: decide at sealing whether the arm runs `historical` (comparable to the
  DIST calibration) or `firmware_v8 + p2_surrogate` (speaks for the cart). Default intent:
  **run BOTH at half-N is forbidden** — pick one, full N; the cart-faithful form is the one
  that can ship, so it is the default choice if the mirror's gates all pass on this rig.

## Silicon feasibility note (do not skip)

H12×2 at gated plies must fit the copro's real-time budget. The BoardEngine executes a full
place+resolve in RTL; 24 rollout placements ≈ 24 sequential engine passes + eval. Before any
rollout arm is sealed, a **cycle-budget memo** must show the worst-case gated ply fits inside
the pill fall time at the fastest gravity the gate can fire under, or define the degrade rule
(skip rollout, play champion) and count degrades in the endpoint.

## Kill conditions (pre-commit)

- DIST NO_GO ⇒ archive unrun.
- Calibration flip-rate outside [1%, 5%] after G sweep on calibration seeds ⇒ not testable, stop.
- Cycle-budget memo shows >30% degrade rate at any gravity ⇒ not shippable as specified, stop.

## Amendments from the fairness-screen results (2026-08-14, pre-seal)

- **TOP-4, not top-2** (changed above): all five screened-structural gaps sat at champion rank
  #2–#4; one was #4. A top-2 rollout misses it. K=2 vs K=4 cost is priced in calibration.
- **FAIR-PRIZE SIZING GATE (new, mandatory before endpoint):** only 5/114 (4%) of big CLAIR
  flip advantages survive the capsule-fair screen — the CLAIR ceiling badly overstates the
  reachable per-ply prize. Calibration must therefore re-estimate the prize in FAIR mode
  (sampled capsules beyond preview, exo_lulu pressure) on ≥500 gated plies. **If the fair
  per-gated-ply expected gain × realistic trigger rate projects <1pp dies-ahead at endpoint
  power, the arm is NOT RUN** — the same not-testable discipline as the seal-penalty lane.
- **Regression fixtures:** the five screened survivors (tools/fairness/survivor_fixtures.json)
  are mandatory checks for any candidate: the rollout must flip all five states to the
  screened-better move; a candidate that misses ≥2 is rejected before any endpoint spend.
