# SEED CENSUS -- Hunt A (solo play, no pressure, strand20 champion) -- INTERIM

**STATUS: INTERIM / TRUNCATED.** The background census job (`census_run.py`, nohup+disowned, PID group still alive) was designed to run for a 10200s (2h50m) wall-clock budget chunked in waves of 300 seeds, matching the harness's own throughput calibration (1.421 games/sec isolated -- see `throughput_run.log`). This report was forced to finalize after only **732s (12.2 min)** of that budget had elapsed, because the interactive session ended before the full budget did -- NOT because calibration or the time budget said this was enough. The background process was left running (detached) and may have produced more checkpointed data in `census/census_results.jsonl` after this report was written; re-run `build_report.py` against `census/CENSUS_DONE` once the job finishes for the full-budget report.

Champion: fast_rtl_x.variant("winner") leaf + eval47/terms47.g_stranded, ws=20, root-only -- ab47.py::_choose_base(wt=0, ws=20) bit-exact, via eval47/reach_root.py::choose_base32. Level 11. No pressure (clean solo play). Failure taxonomy: house definitions.

## Run parameters

- Seed order: `range(65536)` shuffled once under fixed RNG seed `20260806` -- the n consumed IS a genuine uniform sample of the FULL 16-bit seed space, just a small one at this truncation point.
- Workers: 6, wave size: 300, warmup (untimed): 12 seeds
- Budget requested: 2.83h; **actual elapsed at truncation: 0.203h**
- **n = 674** seeds played (1.028% of the 65536-seed space)
- Measured throughput this run: 0.820 games/sec (box concurrently running several other agents' 6-worker jobs -- load average observed up to 66 on 24 cores; this is BELOW the harness's isolated calibration of 1.421 games/sec)

## Outcome distribution

| result | n | rate |
|---|---|---|
| clear | 674 | 100.0000% |
| topout | 0 | 0.0000% |
| stall | 0 | 0.0000% |
| **DIES_AHEAD** (topout, viruses_left<=12) | 0 | 0.0000% |
| **SLOW** (worst decile of pills-to-clear) | 70 | 10.39% of clears |

Pills-to-clear over 674 clears: min=57, median=93.0, p90=124, max=269.

## The tail

- **0** seeds ended TOPOUT or STALL at this n. Honest reporting: 0/674 is NOT evidence the champion never fails -- the REACH_ROOT_CLEAN reference measured 1/120 bad-ends (~0.83%) for this exact decide path, so ~5.6 bad-ends would be the naive expectation at this n; seeing 0 is within sampling noise at n=674 (binomial P(0 successes | p=0.0083, n=674) ≈ 0.4%), not a contradiction, but also not a replication.
- **70** seeds are in the worst decile of pills-to-clear. Full opening-board + pill-prefix material for these is in `census/TAIL_SEEDS.json`.
- No TOPOUT/STALL fatal boards to report -- none occurred in this truncated sample.

## Structure check: SLOW-decile vs matched control

Comparing the 70 slow-decile seeds' OPENING virus layout + first-20-pill-half color stream against 140 matched random controls (ordinary clear, non-slow seeds from this same run).

| feature | slow mean±sd | control mean±sd | |Δ|/pooled_sd | flag |
|---|---|---|---|---|
| n_virus | 48.000±0.000 | 48.000±0.000 | 0.00 |  |
| min_row_near_spawn | 6.129±0.375 | 6.179±0.482 | 0.12 |  |
| n_virus_top4 | 0.000±0.000 | 0.000±0.000 | 0.00 |  |
| pill_color_entropy_first20 | 1.512±0.078 | 1.520±0.057 | 0.12 |  |
| n_mono_pills_first20 | 6.343±1.866 | 6.764±2.140 | 0.21 |  |
| longest_color_run_first20 | 3.914±1.228 | 4.314±1.737 | 0.27 |  |
| n_distinct_colors_first10pills | 2.957±0.203 | 2.993±0.084 | 0.23 |  |
| virus_color_red | 16.429±2.544 | 15.471±2.842 | 0.35 |  |
| virus_color_yellow | 15.686±2.806 | 16.564±2.713 | 0.32 |  |
| virus_color_blue | 15.886±3.138 | 15.964±2.719 | 0.03 |  |

**NO SIGNATURE**: no feature differs from the matched control by >1.5 pooled-sd. Honest negative at n_slow=70, n_control=140.

## Honesty notes

- This is a TRUNCATED run: n reflects an interactive-session time limit, not the calibrated 3h budget or an exhausted seed space. Treat all rates here as a small-n snapshot, not the final census.
- The 0/674 bad-end count is a small-n absence, not a demonstrated 0% rate -- see the binomial sanity-check above.
- The background job (`census_run.py`, nohup+disowned) was left RUNNING at session end and will keep checkpointing to `census/census_results.jsonl` and `census/failures_seen.jsonl` toward its original 10200s budget unless something on the box kills it; a follow-up session can extend this report with `replay_failures.py` + `build_report.py` once `census/CENSUS_DONE` exists.
- Candidate flags (if any) above are exploratory, single-batch, and NOT validated against a transfer filter -- per house rule, not a finding.
