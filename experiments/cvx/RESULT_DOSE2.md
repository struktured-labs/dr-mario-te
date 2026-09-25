# RESULT (2026-09-25, Claude solo): DOSE2 — past the knee? DRCHAIN 720/900 + tournament level L15
Pre-reg: `PREREG_DOSE2.md` (written at launch). Rev `vsrace-r1 / vsharness-r1 / rom-attack-2026-08-01`.

## Verdict: 540 STAYS. Neither 720 nor 900 clears the bar; the knee is at or below 540.
The L11 ranking survives at L15 only partly: 540 = 720 = winner at the scaled 236 s pace. At 177 s,
540 beats winner (−8.0 pp for winner).

## (A) L11, vs a 177 s human, lam 6/min, n=300 paired seeds 36734.. step 2 (`vsrace2` + `vsrace3`)
| arm | WIN% δ=2.65 (fitted) | paired vs fw540 | WIN% δ=2.0 (registered) | paired vs fw540 | med t_end | sent |
|---|---|---|---|---|---|---|
| fw_winner (180) | 88.0 | −7.3 [−11.3, −3.3] | 77.7 | −6.3 [−11.7, −1.0] | 201 s | 48.8 |
| fw360 | 90.7 | −4.7 [−8.3, −1.0] | 77.0 | −7.0 [−12.7, −1.3] | 211 s | 60.6 |
| **fw540** | **95.3** | — | **84.0** | — | 215 s | 63.0 |
| fw720 | 94.7 | −0.7 [−3.7, +2.0] | 79.7 | −4.3 [−9.3, +1.0] | 235 s | 75.9 |
| fw900 | 96.0 | +0.7 [−2.3, +3.7] | 83.0 | −1.0 [−5.7, +3.7] | 233 s | 80.3 |

Gate (b), owner burst model, n=600 paired, L11:
| arm | win% | tap-out% | paired tap-out vs fw540 | stall% | med pills |
|---|---|---|---|---|---|
| fw_winner | 96.2 | 2.83 | +0.50 [−1.17, +2.17] | 1.00 | 133 |
| fw360 | 95.7 | 2.83 | +0.50 [−1.17, +2.17] | 1.50 | 135 |
| **fw540** | 96.7 | **2.33** | — | 1.00 | 145 |
| fw720 | 95.5 | 2.67 | +0.33 [−1.33, +2.00] | 1.83 | 151 |
| fw900 | 95.2 | 3.50 | +1.17 [−0.67, +3.00] | 1.33 | 160 |

Bar (to advance past 540): VS paired CI excludes 0 **and** gate-b tap-out upper CI ≤ +1 pp.
- fw720: VS CI contains 0 (both δ); tap-out upper +2.00. **FAIL.**
- fw900: VS CI contains 0 (both δ); tap-out upper +3.00. **FAIL.**

Mechanism (descriptive): past 540 the bot sends more (76–80 vs 63 tiles) but plays slower (median
235 s vs 215 s). The extra damage only pays when δ is large: 720/900 lose at δ ≤ 1 and tie at δ = 3.
They also use more pills (151/160 vs 145), and 900's tap-out point estimate is the worst in the table.

## (B) L15 (64 viruses), Hetzner, lam 6/min, n=200 paired seeds 40134.. step 2 (`vsrace_l15/`)
The human anchor at L13+ is thin (tape n=2), so there are two views:
- **Anchor-free** break-even (the slowest human median we still beat at ≥50%; lower is better):
  fw540 100 s, fw720 94 s, winner 128 s at δ=2.65; 144 / 147 / 158 s at δ=2.0.
- **Scaled point** M = 177·64/48 = 236 s (declared assumption):

| arm | WIN% δ=2.65 | paired vs fw540 | WIN% δ=2.0 | paired vs fw540 | clear% | med t_end | l_cap (δ=2.65) |
|---|---|---|---|---|---|---|---|
| **fw540** | 90.5 | — | 81.5 | — | 91.5 | 280 s | 7 |
| fw720 | 91.0 | +0.5 [−5.0, +6.0] | 85.5 | +4.0 [−2.0, +10.5] | 91.0 | 305 s | 11 |
| fw_winner | 90.0 | −0.5 [−5.5, +5.0] | 81.5 | +0.0 [−7.0, +7.5] | 94.0 | 247 s | 0 |

At the unscaled 177 s: fw720 +5.0 [−1.0, +10.5], winner **−8.0 [−15.0, −1.0]** vs fw540.

Reading: at L15 the three doses are statistically indistinguishable at the scaled pace. 540 keeps its
edge over the old dose only against a faster human. **Flag:** `loss_cap` games rise with dose at L15
(winner 0 · 540 7 · 720 11 of 200). These are games where the bot used the 600-pill cap without
clearing or topping out, so the high-chain policy stalls on the bigger board. `l_cap` is CENSORED:
at δ=2.0 the same games count as `loss_race`, so this is an outcome-label artifact of one game
population, not two. It is also the same failure the stall-breaker lane (#2) targets.

## Pending
- L15 gate (b) tap-out (the owner's metric at tournament level): fw_winner / fw540 / fw720, n=600 paired
  seeds 40134.. step 2, Hetzner unit `drm-l15gb` (launched 16:18:50Z; local↔remote game md5 `a4fef43f` match).
  If 540's L15 tap-out is worse than winner's by >1 pp (upper CI), the couch default should depend on level.

## Provenance
- L11 rows: `vsrace2/fw_{winner,360,540}_l6.0_*`, `vsrace3/fw{720,900}_l6.0_*`, `gateb/fw*_*.jsonl`.
- L15 rows: `vsrace_l15/*_L15_*.jsonl` (rsync from `/root/drm/l15/`). Current `vs_race.py` (8ff227b6)
  reproduces banked row fw540 L15 seed 40134 byte-for-byte.
- `gate_b.py` gained an optional 8th CLI arg `level` (default 11); L11 rows are byte-identical
  (re-ran fw540 seed 36734 = banked row).
