# PRE-REG (2026-09-20 AT LAUNCH): clock-in-search loop

TIME1: travel-time value must live in the SEARCH, not a leaf height mux.
ki80 (v2 VS loop): always-slam via `k_time*(-fall_rows)*urgency` at dose 80
suicided (17.5% vs k=0, 352 top-outs). This loop is the unpaid TIME1 bill
at milder second-scale doses, scored on Hartford pressure AND VS.

**Trunk:** `variant("winner")`, ws=0, wt=0. k_clock=0 is `_choose_base(winner)`.

**Term (root, every candidate):**
`val -= k_clock * (T_LAT + FPR * fall_rows)` with T_LAT=0.6, FPR=0.35
(lockstep vs_sim / pressure_rig_time). T_LAT is per-pill constant and cannot
change argmax. Only `FPR * fall_rows` reranks: prefers already-tall landing
columns. Spire/dies-ahead risk is a SAFETY gate, not a surprise.

**Not in this loop:** k_race/k_tempo/k_atk/k_safe/k_time (v1/v2 negatives).
No leaf lane/tall/early muxes. No Quartus. No vsloop2 gen1.

**Gen0 members:** k_clock ∈ {0, 10, 20, 40} after scale. kc80 moved 36.1% and
kc160 54.9% (ki80-class, barred). kc20=14.5% kc40=23.0%. Tall boards move
more than empty-flat (physics: fall_rows nearly constant on a flat well).
Seeds **42134+** DECLARED REUSE, disjoint from v1 36734, racer 40134, v2 41134.
Outdir `clockloop/`. C(4,2)=6 VS pairings.

**Scoring (both, or we fool ourselves):**
1. VS fictitious-play, both seats, n=80 seeds/pairing (C(5,2)=10 pairings).
   Primary vs incumbent: win vs k_clock=0.
2. Hartford v2 clock stream: pressure_rig_time + NutmegModel bursty +
   TRATE=0.025, cap 600, n=80 same seeds, each member solo. Report tap-out,
   dies-ahead (topout with vleft≤12), elapsed_s.

**Promote bar (screen, not ship):** VS vs k=0 >55% OR Hartford tap-out down
vs kc=0 with VS vs k=0 ≥45% AND dies-ahead not up. Then owes n≥400 VS vs
winner AND n≥400 Hartford vs winner and vs holes80.

## RESULT gen0 (2026-09-20) — SCREEN HIT, confirm launched

960 VS + 320 Hartford verified. VS how: clear 938, opp_topout 12, crushed 10.

| member | VS vs kc0 | Hartford topout | dies-ahead | elapsed |
|---|---|---|---|---|
| kc10 | **61.2% (98/160)** | 48.8% | 48.8% | 639s |
| kc20 | **57.5% (92/160)** | 48.8% | 47.5% | 612s |
| kc40 | **57.5% (92/160)** | **43.8%** | 43.8% | 604s |
| kc0 incumbent | — | 51.2% | 51.2% | 652s |

All three nonzero clear >55% VS. kc40 also drops Hartford tap-out 51.2→43.8
and is faster. n=400 confirm seeds 43134+ launched. No Quartus. No gen1.

## RESULT confirm n=400 (2026-09-21) — HOLD. Candidate kc40.

5600 VS + 3200 Hartford verified. Gen0 kc10/20/40 all still >55% vs winner.
kc40: **60.0% (480/800) VS**, Hartford topout **42.8%** vs kc0 50.2%,
dies-ahead 41.0% vs 48.0%, elapsed 578s vs 641s.

kc30 (gen1 interp) 60.5% VS / 40.5% Hartford — same family. kc50 64.5% VS
but Hartford 53.2% worse (trap). kc80 45.8% VS / 70.2% topout (slam).

Python-only. Do not Quartus. Next owed gate: kc40 vs holes80 n=400.
See clockloop/MORNING.md.

**Identity:** k_clock=0 vs `_choose_base(winner)` bit-identical, including
forced-behind ctx.

**Scale (must pass before games count):** some nonzero dose moves >0 pills.
Empty-flat wells may not move (fall_rows nearly constant) — that is physics,
not a dead term. A dose that moves ≥30% of all pills is ki80-class; do not
put it in gen0.
