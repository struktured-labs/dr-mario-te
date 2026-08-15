# H12 calibration prep notes (2026-08-14, pre-verdict, descriptive only)

Measured on 199 seeds (30000-30199 ex 30001), champion const play, using the
rig's own `gate_fires()` (oracle_arm.py:153). 31,828 plies.

## 1. The draft's cost premise is wrong ~10x
Gate `d_spawn_h >= 12 OR viruses <= 8` fires on **56.1% of plies** (17,869/31,828),
not "a few %". An H12 top-4 rollout at every gated ply costs ~half an oracle run.
Calibration MUST either tighten the predicate or re-price the arm before endpoint.

## 2. Top-4 margin distribution at gated plies (champion value units)
| quantile | rank2 | rank3 | rank4 |
|---|---|---|---|
| 0.10 | 0 | 8 | 10 |
| 0.25 | 0 | 20 | 26 |
| 0.50 | 10 | 49 | 62 |
| 0.75 | 43 | 133 | 159 |
| 0.90 | 141 | 278 | 321 |

**>=25% of gated plies have an EXACT top-2 tie.** The near-tie world the certified
gaps live in (all 7 sat at champion ranks #2-#4) is frequent, not exotic.

## 3. Candidate tightened predicates for calibration to price
- gate AND rank2_margin == 0            (est. ~15-25% of all plies)
- gate AND rank4_margin <= 26 (q25)     (top-4 genuinely contested)
- gate AND near-tie AND viruses <= 8    (endgame-only variant)
Pick by fair-prize projection per the draft's mandatory sizing gate; the 7
holdout-certified fixtures (pending owner sign-off) are the acceptance test.

## 4. Context from the overnight arc
Certified core = CASCADE + ROUTE/DIG families; one-step static features CANNOT
express either (proto_cvd 1/7) — the rollout is the only known instrument.

## 5. PROVISIONAL pre-freeze staging results (2026-08-14 evening, blackmage)

- **Mechanism acceptance: 7/7.** Top-4 fork, H=15, K=5 sampled streams (true cur+next only)
  re-ranks ALL seven holdout-certified fixtures correctly (3 outright, 4 tied-first).
  `h12_proto.py`, provisional pending design freeze.
- **Fair-prize sizing, 510 fresh gated-tie plies (seeds 30300+):** trigger rate 16.5% of
  plies; rollout overrides champion at 96% of triggers **but median fair gain = 0.00** —
  the naive intervene-at-every-tie arm is stage-2 churn at 9x the dose. DO NOT RUN undosed.
- **The dose curve (the design consequence — H12 gains a margin knob θ_margin):**
  | θ_margin | % of triggers | % of ALL plies | mean fair gain |
  |---|---|---|---|
  | ≥0.5 | 12.2% | 2.01% | +1.07 |
  | **≥1.0** | **5.5%** | **0.91%** | **+1.56** |
  | ≥1.5 | 2.5% | 0.42% | +2.00 |
  | ≥2.0 | 1.6% | 0.26% | +2.20 |
  Anchor θ_margin=1.0: half stage-2's ply dose with DIRECTED signal where stage-2's null
  proved its signal was random. Conversion to projected dies-ahead awaits the Tier-A factor.

## 6. CALIBRATION RESULT (2026-08-15, post-GO, 1500 fresh gated-tie plies, seeds 32000+)

Tier-A conversion factor now exists: oracle = 3.65% ply dose of oracle-quality flips
→ −11.57pp dies-ahead. H12 projection = dose% × mean_dfair × 11.57/(3.65 × G), where G =
oracle per-flip realized gain (unknown; bracketed 2.5–4.5 virus-equivalents from the CLAIR
mine's gap≥3 distribution).

| θ_margin | % of ALL plies | mean dfair | projection @G=2.5/3.5/4.5 | vs ≥1pp bar |
|---|---|---|---|---|
| ≥0.5 | 2.28% | +0.88 | **2.55 / 1.82 / 1.42 pp** | CLEARS at all G |
| ≥1.0 | 0.69% | +1.39 | 1.22 / 0.87 / 0.68 pp | borderline |
| ≥1.5 | 0.24% | +1.84 | 0.57 / 0.40 / 0.31 pp | fails |
| ≥2.0 | 0.05% | +2.55 | 0.16 / 0.11 / 0.09 pp | fails |

Trigger rate replicated at 18.2% of plies (vs 16.5% first measurement). Median dfair at the
raw tie is still 0.00 — the undosed arm remains DO-NOT-RUN.

**FREEZE RECOMMENDATION: θ_margin = 0.5.** It is the only rung that clears the prereg bar
under every plausible conversion. Churn context: 2.28% ply dose ≈ stage-2's 1.8% — but
stage-2's perturbation was PROVABLY undirected (its null matched it), while every θ0.5 flip
carries measured fair gain ≥ +0.5 (mean +0.88). Direction is the thing stage-2 lacked.
θ=1.0 is the documented sensitivity arm if the endpoint wants a lower-churn second dose.

**Next step (owner authorization required — decisive spend):** endpoint A/B, N=9,000 paired
seeds per the power floor, H12(θ0.5) vs champion, with per-ply flip provenance and a
dose-matched null. Estimated cost: one cpx62 burst, ~15–20h, ~$5. Acceptance pre-check
already passed (fixtures v2: 7/7).
