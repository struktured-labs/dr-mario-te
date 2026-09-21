# Morning 2026-09-21 — clock-in-search

**Candidate: winner + k_clock=40.** Python-only. Do not Quartus.

Pricing fall time at the root (`val -= k_clock * (0.6 + 0.35*fall_rows)`) beat
always-on winner at n=400 on both jobs. This is the first VS term that
cleared the promote bar.

## n=400 confirm (seeds 43134+, 5600 VS + 3200 Hartford, verified)

VS vs winner (800 games each) and Hartford TRATE=0.025 solo (n=400):

| k_clock | VS vs winner | Hartford topout | dies-ahead | elapsed |
|---|---|---|---|---|
| **40 (gen0)** | **60.0% (480/800)** | **42.8%** | 41.0% | 578s |
| 10 | 58.2% (466/800) | 47.0% | 45.0% | 621s |
| 20 | 56.4% (451/800) | 47.0% | 43.8% | 622s |
| 0 incumbent | — | 50.2% | 48.0% | 641s |
| 30 (gen1 interp) | 60.5% (484/800) | **40.5%** | 39.5% | 591s |
| 50 (gen1) | 64.5% (516/800) | 53.2% **worse** | 50.0% | 567s |
| 60 | 59.5% | 59.2% worse | 55.2% | 574s |
| 80 | 45.8% fail | 70.2% suicide | 66.0% | 522s |

Gen0 screen held: kc10/20/40 all still >55% VS. kc40 is the declared
candidate (best gen0 dual). kc30 is a 20–40 interpolation and slightly
better on Hartford; treat as the same family, not a new idea. kc50 is a
trap: more VS wins, more Hartford deaths. kc80 is the old slam.

## What this is

Hartford tempo as a **search cost**, not a leaf shape. Mild doses (10–40)
prefer shorter drops without ki80 suicide. Games got faster (641s → 578s)
and tap-out under the Hartford clock stream fell 50.2% → 42.8%. Dies-ahead
went down, not up.

## What it is not

- Not on the FPGA. Root term is Python. MEGADOSE / RTL freeze is a later
  conversation, after vs-holes80.
- Not a P2 brain. Still a self-board clock. dr. lulu’s timed drip is unsolved.
- Not kc50. Chasing VS% past ~40 overdoses Hartford.

## Next (human)

1. n=400 VS **kc40 vs holes80** (owed ship gate; winner already beats holes80
   63.8% — clock must not give that back).
2. If that holds, MEGADOSE k_clock=40 on Mesen, then one RTL constant if it
   still fits ALMs. Still no Quartus until that A/B.
3. Do not run vsloop2 gen1. Do not k_hold unless kc40 vs holes80 dies.

Overnight stop condition met. Scheduler should cancel.
