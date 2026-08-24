# FIT_CONFIG (DRAFT — becomes registered on commit AFTER team-lead approval;
# nothing computes until then. Inventory numbers filled from the C-deep
# analyze; all rules below are fixed independently of any label content.)

## Registered feature candidates (A3.5 + A4), exact definitions

All three are board-scalar functions over (color, is_virus) planes in the
g_stranded mold, computed on the candidate's RESULTING board.

(i) **g_center** (center-column clearability, gate-center-blind + both lulu
    kills were center spawn blockage):
    g_center = Σ_{c ∈ {3,4}} [ H_c + B_c ]
    where H_c = column height (16 − topmost occupied row, 0 if empty) and
    B_c = burial of the DEEPEST virus in column c = count of occupied
    non-virus cells above it in c (0 if no virus in c).

(ii) **g_attack** (attack-capital — the G2 combo-liquidation: same-color
     mass staged against viruses):
     g_attack = Σ_{viruses v} min(3, |largest 4-connected component of
     same-color non-virus cells orthogonally adjacent to v|).

(iii) **g_construct** (construction-capital — partial MULTI-STEP progress
      toward each clear; the stall's missing gradient, SHARPENED by the
      epic32 bookend: the winning move there was a single-step capture on a
      sorted column — already priced by the current evaluator's clear search
      — while the stall's missing move was a multi-step build; the feature
      must therefore value exactly the staged-but-unfinished regime):
      For each virus v of color k and each axis (row/col), consider the ≤4
      4-cell windows through v along that axis that fit the board. A window
      is LIVE iff every cell is color-k or EMPTY (any other-color cell, pill
      or virus, kills it — a mixed plug is dead). Live-window score s =
      count of color-k cells in it (v included, so s ≥ 1).
      g_construct = Σ_v [ best live-window score over both axes == 2 ]
      = the COUNT of viruses with staged multi-step construction: a clean
      window holding exactly v + one built matching cell, ≥2 placements from
      clearing. s=3 (single-step capture) is INTENTIONALLY EXCLUDED as
      already-priced; s=1 (no progress) scores 0.

## Fit model

Ridge regression predicting per-candidate label surv/8 from
[champ_value (the banked/recomputed value), g_center, g_attack, g_construct],
z-scored per stratum, α by 5-fold CV WITHIN the training split only.
Fitted separately per population: {C ∪ Cdeep} (primary, replay-gated lab
states) and {A ∪ B} (silicon imports, reported alongside, never pooled with
the primary).

## Held-out split (registered BEFORE the fit; deterministic, no peeking)

Unit = SEED for C/Cdeep (all states+candidates of a seed stay together);
unit = SOURCE ROW for A/B. Held out ⇔ (seed or crc32(row)) % 4 == 3.
Nothing from a held-out unit touches fitting, z-scoring, or α selection.

## Baselines and pass criteria (A2 verbatim + operationalization)

A2: "fitted contamination features ... must beat BOTH controls on HELD-OUT
states: better held-out label prediction than the shuffle-control fit AND a
non-zero improvement over the mimic/champion-value baseline, split registered
before the fit runs."

- **Champion-value baseline**: ridge on [champ_value] alone, same split/CV.
- **Shuffle-fit control**: the identical 4-feature pipeline trained on
  per-state permuted labels (rng seed 20260823, recorded), scored on the
  TRUE held-out labels.
- **Primary metric**: mean within-state Spearman rho between predicted and
  true surv over held-out states with label spread; secondary: held-out MSE.
- **PASS** ⇔ on {C ∪ Cdeep} held-out: (a) rho_full − rho_champval > 0 with a
  state-level bootstrap 95% CI excluding 0 (10,000 resamples, seed 146), AND
  (b) rho_full > rho_shufflefit. Anything else = NO PASS; per-feature
  coefficients and ablations are then diagnostic only.

## Inventory it fits on (C-deep analyze, 2026-08-24)

| stratum | states | candidate rows | claims | calib rho | champ_surv mean |
|---|---|---|---|---|---|
| C (mid, k=30-50) | 75 | 1,746 | 4 | 0.634 | 7.05 |
| **Cdeep (k=8-20)** | **1,200** | **25,254** | **269 (22.4%/state)** | 0.515 | 5.40 |
| A (silicon pop-A) | 34 | 835 | 1 | 0.735 | 7.24 |
| B (silicon corpus) | 35 | 912 | 0 | 0.689 | 7.77 |

Total 229,976 forks banked. Primary fit population {C ∪ Cdeep}: 1,275
states / 27,000 candidate rows / 273 claims. Side population {A ∪ B}: 69
states / 1,747 rows / 1 claim. MIMIC FAIL_NO_CLAIMS at full n; shuffle dose
384 claims (count is not quality — validation discriminates).
VOIDS (travel with every total, deduped by id): A tile 5 + settle 6;
B tile 4 + settle 7 + mode 5; C/Cdeep 0 of 300 games (replay aborts 0);
D unreadable 6 (v1 round). The ≥150-claim SECONDARY bar is met on claims
COUNT (269 fresh k≥8); its Fisher/rescue/calibration halves await the
forced-move validation run (not yet scheduled — team-lead's call).
