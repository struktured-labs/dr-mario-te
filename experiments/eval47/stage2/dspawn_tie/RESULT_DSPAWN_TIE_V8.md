# Result — exact-v8 `d_spawn_h` tie-resolution arm

**Final 2026-08-11: NO_GO. Do not ship or sweep this intervention.**

The arm completed all 9,000 registered paired seeds (61000..69999) under
`exo_lulu`. The treatment changed only raw exact-v8 value ties and every one
of its 7,975 logged flips strictly lowered the linked spawn-lane sensor. It did
not improve bad ends and it significantly increased dies-ahead versus the
champion.

## Endpoint result

| endpoint | base | treatment | treatment - base (95% paired bootstrap CI) | exact McNemar |
|---|---:|---:|---:|---:|
| bad end (topout or 300-pill stall) | 567 | 570 | +0.033pp [-0.389, +0.445] | p=0.9171 |
| dies ahead | 151 | 169 | **+0.200pp [+0.022, +0.378]** | **p=0.03846** |

The bad-end comparison had 369 discordant pairs and a 0.418pp 95% analytic
half-width, so the registered 1pp adequacy requirement was reachable. The
nearly unchanged total masks churn between bad-end types: treatment changed
base's 245 topouts / 322 stalls into 265 topouts / 305 stalls. Stalls were
scored at parity with topouts throughout.

Among 8,247 common clears, treatment used 0.072 fewer pills on average, with
a 95% CI of [-0.562, +0.427]; there is no measured tempo benefit. Treatment
changed the categorical result in 379 games and the result or pill count in
3,004 games.

The registered action-flip dose gate passed: treatment changed 7,975 of
1,228,025 plies (0.6494%) and the null changed 7,413 of 1,230,297 (0.6025%), a
7.22% relative mismatch. All integrity checks and killed mutants passed.

## Post-registered semantic audit of the null

The separately preregistered replay audit found that action-ID flip count was
the wrong dose measure:

| first flip | n | exact successor-board aliases | distinct successor boards | alias fraction |
|---|---:|---:|---:|---:|
| treatment | 3,939 | 0 | 3,939 | 0.00% |
| label-blind null | 4,831 | 4,467 | 364 | 92.47% |

Treatment therefore caused **10.82x** as many distinct first-state changes as
the null. Exact equality covered all 128 color, virus, and link bytes plus
expansion metadata; the audit replay gate and all four declared mutants
passed. Of the 4,467 null aliases, all had zero sensor delta and 4,465 used a
same-color pill. This explains the null's weak churn despite an apparently
matched action dose.

Consequently, the registered treatment-versus-null directionality contrast is
not mechanistically dose-matched and must not be used to estimate direction
versus random state churn. It does **not** alter the treatment-versus-champion
finding: the candidate independently fails GO and significantly worsens
dies-ahead.

## Decision and durable law

- Close the exact-value-tie `d_spawn_h` resolution lane. Do not reverse the
  sensor, sweep tie sizes, or tune a nearby threshold on these endpoint seeds.
- For future policy arms, an intervention dose is a change to the canonical
  exact linked successor state, not merely a different action ID. Nulls must
  match distinct-state dose and must calibrate first-flip timing, base value
  gap, successor-state distance, and gate duty before endpoint seeds open.
- The separately recorded K4/wq60 post-landed-garbage arm remains a different
  mechanism, not a continuation of this failed tie resolver. Its corrected
  null is a prerequisite; its current document is design-only permission to
  build and calibrate, not permission to run endpoints.

Machine-readable authority:

- `out/result.json` — endpoint counts, paired estimates, provenance, and gates
- `out/null_semantic_audit.json` — exact first-flip successor-state audit
- `out/evaluation/META.json` and 36 segment files — immutable raw evaluation
  rows and runtime identity

