# RESULT gate (b) — see PREREG_GATEB.md
**Gate (b) RESULT — 2026-09-23 (Claude).** Pinned path (`import_pin`, `VsPolicy.decide`, ws=0), OWNER burst model (`fit_struktured_20260804`), L11, cap 600, n=600 CRN (seeds 36734.. step 2, declared reuse). Files: `experiments/cvx/gateb/`, prereg `PREREG_GATEB.md`.

| arm | tap-out | dies-ahead (vleft≤12) | clear | med pills | med elapsed |
|---|---|---|---|---|---|
| **holes80** | **24.33%** | 22.00% | 75.50% | 160 | 613 s |
| winner (kc0) | 40.50% | 39.17% | 59.50% | 159 | 575 s |
| **kc40** | **41.00%** | 39.67% | 59.00% | 151 | 523 s |

Paired (McNemar): kc40 vs holes80 **78/178, p<0.0001** (holes80 fewer tap-outs); kc40 vs winner 123/126, **p=0.90** (identical survival); winner vs holes80 76/173, p<0.0001.

**Reading.** The clock term buys exactly what it claims — speed (elapsed 613→523 s, pills 160→151) — and **zero survival**: kc40 dies as often as winner, ~1.7x holes80, under the pressure model fit to the owner's own play. So kc40 is a **VS-only gain on a race-only arena** (#15); on the owner's #1 metric the couch/booth build stays holes80. Not a knock on the term: it is the right *kind* of term (search-side tempo, as TIME1 predicted) — it just needs to live on the holes80 trunk, and that needs the trunk's solitaire number to survive it. Suggest the next MEGADOSE/loop arm be `holes80 + k_clock∈{10,20,40}` scored on THIS gate, not on arena win rate.

Absolute levels here (24/40%) are higher than run 16's (13/19%) — same ranking, different player (ws=0 pinned vs ws=20 worker3) — which is #16's point; the calibration table is running now (37/2700).
