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

# RESULT holes80+k_clock (amendment)
**[CLAUDE] gate (b) — holes80 + k_clock RESULT (2026-09-23).** Same rig/seeds as the kc40 row (owner burst model, pinned, L11, cap 600, n=600 CRN). Files `experiments/cvx/gateb/h80kc*`.

| arm | tap-out | dies-ahead | clear | med elapsed | vs holes80 (W/L, McNemar) |
|---|---|---|---|---|---|
| **holes80** | **24.33%** | 22.00% | 75.50% | 613 s | — |
| h80 + kc10 | 35.17% | 33.17% | 64.83% | 589 s | 81/146, p<1e-4 |
| h80 + kc20 | 42.33% | 40.17% | 57.67% | 587 s | 64/172, p<1e-4 |
| h80 + kc40 | 50.17% | 46.00% | 49.83% | 567 s | 52/207, p<1e-4 |
| winner | 40.50% | 39.17% | 59.50% | 575 s | 76/173 |
| kc40 (winner) | 41.00% | 39.67% | 59.00% | 523 s | 78/178 |

**Verdict: the root clock term costs survival monotonically on the safe trunk too** (+11 / +18 / +26 pp tap-out for 10/20/40) while buying almost no tempo there (613→589→567 s). At kc40 the holes80 trunk is *worse* than plain winner. Per the pre-registered bar, the k_clock family is **closed at the root as well as the leaf** for the couch objective. What it wins in the arena is speed paid for with deaths that the arena cannot see (#15).

Standing picture for the ship decision: holes80 (24.3%) remains the only trunk that clears the owner metric; nothing tested this week — leaf muxes (runs 18/19), constant gradient (run 20), interaction terms (vsloop v1/v2), root clock (this) — beats it there. Suggest #17 close with this table, and the MEGADOSE/FPGA CLOCK40 lane be marked *not couch-eligible* (soak can continue as a silicon-stability datapoint).
