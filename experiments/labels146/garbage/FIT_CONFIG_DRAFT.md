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

(iii) **g_construct** (construction-capital — partial progress toward each
      clear; the stall's missing gradient):
      For each virus v of color k and each axis (row/col), consider the ≤4
      4-cell windows through v along that axis that fit the board; a window
      containing a virus of another color is DEAD (scores nothing); live
      window score = count of color-k cells in it (v included).
      g_construct = Σ_v [ max live-window score over both axes − 1 ] ∈ [0,3n].

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

## Inventory it fits on (filled at C-deep analyze)

- states / candidate-rows / claims per stratum: <FILL>
- tile/settle/mode void counts (travel with all totals): <FILL>
