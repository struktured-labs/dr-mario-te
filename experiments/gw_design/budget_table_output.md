## Champion decision cost, MEASURED (copro cycles)

| population | n | p10 | median | p90 | p99 | max |
|---|---|---|---|---|---|---|
| all decisions | 1500 | 37.7 M | **45.1 M** | 58.1 M | 72.1 M | 80.3 M |
| post-garbage only | 208 | 35.9 M | **41.8 M** | 50.5 M | 57.7 M | 62.5 M |

## Window budget at the POCKET copro tap (54.669358 MHz, 909658 cycles/frame)

| h | W (f) | W (cycles) | releases | budget @ median cost | budget @ p90 cost | EXTRA searches after the mandatory post-garbage one |
|---|---|---|---|---|---|---|
| 0 | 264 | 240.1 M | 1.0% | 5.32 | 4.14 | **4.32** |
| 1 | 248 | 225.6 M | 0.5% | 5.00 | 3.88 | **4.00** |
| 2 | 232 | 211.0 M | 1.9% | 4.68 | 3.63 | **3.68** |
| 3 | 216 | 196.5 M | 3.8% | 4.35 | 3.38 | **3.35** |
| 4 | 200 | 181.9 M | 7.2% | 4.03 | 3.13 | **3.03** |
| 5 | 184 | 167.4 M | 13.9% | 3.71 | 2.88 | **2.71** |
| 6 | 168 | 152.8 M | 13.0% | 3.39 | 2.63 | **2.39** |
| 7 | 152 | 138.3 M | 11.1% | 3.06 | 2.38 | **2.06** |
| 8 | 136 | 123.7 M | 11.1% | 2.74 | 2.13 | **1.74** |
| 9 | 120 | 109.2 M | 10.1% | 2.42 | 1.88 | **1.42** |
| 10 | 104 | 94.6 M | 4.3% | 2.10 | 1.63 | **1.10** |
| 11 | 88 | 80.0 M | 7.7% | 1.77 | 1.38 | **0.77** |
| 12 | 72 | 65.5 M | 3.8% | 1.45 | 1.13 | **0.45** |
| 13 | 56 | 50.9 M | 3.8% | 1.13 | 0.88 | **0.13** |
| 14 | 40 | 36.4 M | 2.4% | 0.81 | 0.63 | **0.00** |
| 15 | 24 | 21.8 M | 2.4% | 0.48 | 0.38 | **0.00** |
| 16 | 8 | 7.3 M | 1.9% | 0.16 | 0.13 | **0.00** |

## Window budget at the MISTER copro tap (85.909088 MHz, 1429464 cycles/frame)

| h | W (f) | W (cycles) | releases | budget @ median cost | budget @ p90 cost | EXTRA searches after the mandatory post-garbage one |
|---|---|---|---|---|---|---|
| 0 | 264 | 377.4 M | 1.0% | 8.36 | 6.50 | **7.36** |
| 1 | 248 | 354.5 M | 0.5% | 7.85 | 6.10 | **6.85** |
| 2 | 232 | 331.6 M | 1.9% | 7.35 | 5.71 | **6.35** |
| 3 | 216 | 308.8 M | 3.8% | 6.84 | 5.32 | **5.84** |
| 4 | 200 | 285.9 M | 7.2% | 6.33 | 4.92 | **5.33** |
| 5 | 184 | 263.0 M | 13.9% | 5.83 | 4.53 | **4.83** |
| 6 | 168 | 240.1 M | 13.0% | 5.32 | 4.14 | **4.32** |
| 7 | 152 | 217.3 M | 11.1% | 4.81 | 3.74 | **3.81** |
| 8 | 136 | 194.4 M | 11.1% | 4.31 | 3.35 | **3.31** |
| 9 | 120 | 171.5 M | 10.1% | 3.80 | 2.95 | **2.80** |
| 10 | 104 | 148.7 M | 4.3% | 3.29 | 2.56 | **2.29** |
| 11 | 88 | 125.8 M | 7.7% | 2.79 | 2.17 | **1.79** |
| 12 | 72 | 102.9 M | 3.8% | 2.28 | 1.77 | **1.28** |
| 13 | 56 | 80.0 M | 3.8% | 1.77 | 1.38 | **0.77** |
| 14 | 40 | 57.2 M | 2.4% | 1.27 | 0.98 | **0.27** |
| 15 | 24 | 34.3 M | 2.4% | 0.76 | 0.59 | **0.00** |
| 16 | 8 | 11.4 M | 1.9% | 0.25 | 0.20 | **0.00** |

(`releases` = share of the 208 MEASURED post-garbage decisions whose h_hit was that value; small-n, see caveats.)

## Cost of candidate computations, in the same currency

| computation | cycles | Pocket frames | largest h that still fits | label |
|---|---|---|---|---|
| (a) linear tail term, per-feature LUT in 6502 firmware (19 table reads + 19 adds x 32 candidates, ~12 cyc each) | 7.3e+03 | 0.0 | h <= 16 | DERIVED |
| (a') same term in RTL beside LeafEval (Stage-2 precedent: 8 reads + 8 adds = 18 of 250 cycles) | 1.28e+03 | 0.0 | h <= 16 | DERIVED |
| base post-garbage re-search (1 champion decision) -- MANDATORY | 4.51e+07 | 49.6 | h <= 13 | MEASURED |
| (b) 2-candidate x 1 extra ply (known next capsule, no sampling) | 9.03e+07 | 99.2 | h <= 10 | DERIVED |
| (b+) the above PLUS the mandatory base search | 1.35e+08 | 148.8 | h <= 7 | DERIVED |
| (c) top-4 x 1 extra ply + base | 2.26e+08 | 248.1 | h <= 0 | DERIVED |
| (c') H12 as certified: topk 4 x fork_samples 5 x horizon 15 | 1.35e+10 | 14884.1 | **never** (exceeds even h=0) | DERIVED |

C_median = 45.1 M cycles = 49.6 Pocket frames = 31.6 MiSTer frames
C_p90    = 58.1 M cycles = 63.8 Pocket frames
