# failure-objective: is the shipped eval speed-optimal or survival-optimal?

**Thread:** failure-objective · **Date:** 2026-08-06 · **Simulator:** python offline
(`fast_rtl_x` numba kernel + `root_search` + `FaithfulDrMarioEnv`, the same simulator
`eval47/ab47.py` / `eval47/pressure_rig.py` use for all coefficient tuning to date --
**not** Verilator/RTL. Per house rule this is adequate for a claim about a *scalar rate*
produced by an unmodified search algorithm under different coefficients; it would **not**
be adequate for a move-identity claim (py65/python agrees with RTL on move choice only
~13% of the time, CANDIDATE_TIER3.md sec 10). No claim below is a move-identity claim --
every arm here is the SAME `_choose_base` decider, only the 6 numeric weights change.)

## Hypothesis (falsifiable)

The champion's coefficients -- `fast_rtl_x.variant("winner")`'s 5 constants
(`R_VRDY=8 R_BURIED=48 R_RDYEXT=8 R_SETUP=32 R_MATCHED=48`) plus the root-only
`g_stranded` cost weight `ws=20` -- were selected to **maximize clear speed**
(pills-to-clear / clear rate, per `eval47/ab47.py`'s dose-sweep verdict metric, and per
`sweep_n120.log`'s original ws dose search which picked ws=20 over ws=60 specifically
because ws=20 gave a REAL pills-delta and ws=60 didn't, despite both hitting the same
bad-ends floor under drip pressure). They were never re-optimized against a **survival**
objective (bad-end rate under pressure). If survival-optimal coefficients differ
materially from the shipped point, that is the "dies-while-ahead" gap: the AI is tuned to
win fast when nothing goes wrong, not to survive when the human is hitting it.

**Falsifiable claim under test:** a coordinate scan around the champion point, scored by
bad-end rate (topout+stall) under `eval47/bursty_model.py`'s v1.1 human-only-cadence
pressure fit (paired seeds, same seed range used in `BURSTY_V1_RESULTS.md` sec 5), finds a
point that beats the champion's bad-end rate by more than sampling noise. If nothing beats
it -- DEAD (the two objectives already coincide at the shipped point, which is itself the
finding). If something beats it -- ALIVE, report the coefficient delta and the
speed-lost-per-survival-gained tradeoff.

## Method

- **Champion anchors reused, not recomputed.** `eval47/results/bursty_v1_1_n120_wt0_ws20.json`
  already has n=120 paired-seed bursty-v1.1 runs at `ws=0` (no-defense control) and `ws=20`
  (shipped): bad-ends **47/120 (39.2%)** vs **20/120 (16.7%)**. Restricted to the seeds
  0..39 subset that the new arms below reuse for pairing: ws=0 -> 10/40 (25.0%), ws=20 (the
  champion) -> **9/40 (22.5%)**.
- **New arms** (`coef_sweep.py`, this dir): reuses `pressure_rig.py`'s `play()`/`compare()`
  machinery unmodified, with a custom initializer overriding individual `R_*` weight-vector
  entries after `fast_rtl_x.variant("winner")` is built -- same call path, same bursty-v1.1
  model object (rebuilt in-process via `bursty_model.fit_struktured_20260804()` +
  `fit_ensemble_source.fit_per_player()`, matching `run_bursty_v1_1_validity.py`'s
  "single source of truth" contract), same L11, same 300-pill cap, seeds 0..39, workers=4.
  - **ws axis** (the term-47 `g_stranded` cost, the knob most directly aimed at the
    abandoned-material / burial pattern that plausibly drives dies-ahead): `ws in {10, 40}`,
    bracketing the shipped 20 (0 and 20 covered by the anchor).
  - **R_* axis**: `R_BURIED` (burial-penalty term, same defensive spirit as `ws`) and
    `R_SETUP` (readiness/tempo term, most plausibly in tension with survival -- building
    "setup" structure can raise burial risk for a later speed payoff), each perturbed to
    0.5x and 2x its champion value, holding ws=20 and the other 4 R_* constants at champion.
- **Timing pilot** (`timing_pilot.py`/`timing_pilot2.py`): 4.33s/game at n=40, workers=4,
  bursty v1.1, L11 -- sized the whole 6-arm sweep at ~18 min total, safely inside the
  portfolio's 4-worker/8GB self-cap (peak system-wide python RSS observed ~9.7GB across ALL
  agents on the box, not just this thread; box has 123GB total / 82GB free).
- **Prior art folded in** (no recompute needed): `eval47/REACTIVE_MODE_RESULTS.md` already
  tested *temporarily* boosting `ws` to 40/60 (reactive `ws+boost` for K placements after
  garbage lands) under bursty **v1** (not v1.1) pressure and found **no config beat static
  ws=20** (K=4/boost=20 -> 35/120 vs ws=20's 32/120; K=8/boost=20 -> 32/120 tie; K=4/boost=40
  -> 39/120, worse) -- McNemar non-significant on all three, two of three trending harmful.
  A temporary elevation under the older, pool-contaminated v1 model isn't decisive on its
  own, but it independently pointed the same direction this thread's static-ws sweep found.

## Results

Paired bootstrap CI (10k reps) on bad-end-rate(arm) minus bad-end-rate(champion ws=20),
same 40 seeds both sides. "WASH" = CI straddles 0.

| axis | value | n | bad-ends | rate | dies-ahead | delta vs champion (22.5%) | verdict |
|---|---|---|---|---|---|---|---|
| ws (anchor) | 0 | 120 | 47 | 39.2% | 33 (27.5%) | -- | (no-defense control) |
| **ws (champion)** | **20** | **40** | **9** | **22.5%** | **5 (12.5%)** | **--** | **--** |
| ws | 10 | 40 | 8 | 20.0% | 5 (12.5%) | [-20.0%, +12.5%] | WASH |
| ws | 40 | 40 | 10 | 25.0% | 5 (12.5%) | [-12.5%, +17.5%] | WASH |
| R_BURIED | 24 (0.5x) | 40 | 15 | 37.5% | 10 (25.0%) | [-5.0%, +35.0%] | WASH |
| R_BURIED | 96 (2x) | 40 | 10 | 25.0% | 2 (5.0%) | [-12.5%, +20.0%] | WASH |
| R_SETUP | 16 (0.5x) | 40 | 11 | 27.5% | 4 (10.0%) | [-10.0%, +20.0%] | WASH |
| R_SETUP | 64 (2x) | 40 | 8 | 20.0% | 1 (2.5%) | [-17.5%, +12.5%] | WASH |

**Every one of the 6 perturbations -- both directions, on 3 different axes -- is a WASH
against the shipped champion point.** None beats it with a resolved CI; the two arms with
a nominally better point estimate (ws=10 and R_SETUP=64, both 20.0% vs champion's 22.5%)
still have CIs that comfortably straddle 0. Directionally, halving either burial-penalty
term (`ws`->10 partially, `R_BURIED`->24, `R_SETUP`->16) trends toward MORE bad-ends
(point estimates 20.0-37.5% vs champion's 22.5%), consistent with those terms doing real
defensive work; doubling them does not clearly buy anything further beyond noise. The
`R_BURIED`/`R_SETUP` 2x arms both show a lower dies-ahead COUNT (2/40 and 1/40 vs
champion's 5/40) alongside a similar or slightly worse total bad-end rate -- a hint that
stronger anti-burial pressure trades stalls/other death modes for fewer "died on the
doorstep" losses specifically, but n is far too small (single-digit event counts) to
report that as anything beyond a pattern worth a note for whoever runs the next dose.

## Verdict

**DEAD**, for the resolution this cheap test can see. A 6-point local coordinate scan
around the champion's 6-dimensional coefficient vector -- covering the ws axis
symmetrically (0.5x, 2x the champion dose) and two plausible survival/speed-tension
R_* terms (R_BURIED, R_SETUP) at the same doses -- found **no point that materially beats
the champion's bad-end rate under honest human-cadence bursty pressure**. Combined with
the independent prior result in `REACTIVE_MODE_RESULTS.md` (temporarily elevating ws to
40-60 also failed to beat static ws=20, under the older v1 pressure model), the picture is
consistent: **the speed-optimized champion point already sits at or very near a local
survival optimum on every axis tested here.** That is the notable finding the hypothesis
predicted as its negative outcome -- the two objectives (minimize pills-to-clear,
minimize bad-end rate) do not visibly diverge in this neighborhood of coefficient space.

**Caveat, stated plainly (n=40 is a signal, not a finding):** every CI above is wide
(15-55 points), because bad-end rate is a Bernoulli proportion over only 40 paired seeds
and single-digit event counts drive several of the dies-ahead columns. This test could
NOT have detected an effect smaller than roughly +/-15-20 percentage points reliably. It
was designed as the CHEAPEST kill, not a definitive one: it answers "is there an easy,
large win nearby that six single-axis nudges would have found" -- no -- not "is the
champion provably optimal." A real CMA-ES / full coordinate-descent run (the task's
original ask) over the full 6D space at n>=120/arm would cost on the order of 6-10x this
run's ~18 minutes per comparable-resolution arm and was NOT run, because this cheap probe
already came back flat in the most promising directions (the two terms structurally
closest to a burial/survival mechanism, ws and R_BURIED, plus R_SETUP as the speed-leaning
counterweight) -- per the portfolio rule, a clean negative here is the stopping point,
not a mandate to spend the 10x.

## Next step

If someone wants to push past this negative: (1) widen to n=120/arm on just the two arms
with the best point estimates (ws=10, R_SETUP=64) to see if the trend firms up or
regresses to the champion, since those are the only two that didn't point strictly worse;
(2) the dies-ahead-specific pattern on the R_BURIED/R_SETUP 2x arms (fewer near-doorstep
deaths, similar total bad-ends) is a distinct, second falsifiable hypothesis -- "stronger
anti-burial coefficients shift the death MODE, not the death RATE" -- worth its own cheap
paired test at n>=120 before it's spent on real coefficient-search compute. Otherwise:
STOP, this thread is closed on the evidence collected.

## Provenance

- `coef_sweep.py` -- the sweep harness (this dir)
- `analyze.py` -- assembles arms + anchor into the table above with paired bootstrap CIs
- `timing_pilot.py`, `timing_pilot2.py` -- throughput pilots (4.33s/game at n=40,
  workers=4, bursty v1.1, L11)
- `results/sweep_*_n40.json` -- raw per-seed rows for every new arm
- `results/analysis_summary.json` -- machine-readable version of the results table
- `sweep_run1.log` -- full driver stdout/stderr for the 6-arm run
- Anchors: `/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/results/bursty_v1_1_n120_wt0_ws20.json`
- Prior art: `/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/BURSTY_V1_RESULTS.md`,
  `/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/REACTIVE_MODE_RESULTS.md`,
  `/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/ab47.py` (original ws dose
  search under drip, `sweep_n120.log`),
  `/home/struktured/projects/dr_mario_rl/tmp/combo_term/fast_rtl_x.py` (`variant("winner")`)
