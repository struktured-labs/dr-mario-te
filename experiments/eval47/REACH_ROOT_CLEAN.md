# CLEAN-BOARD gate: reachability filtering on normal (no-pressure) L11 boards

**Date:** 2026-08-05 · **Rig:** `reach_root_ab.py` (control=base32, always run) +
companion `reach_divergence.py` (same-state action-comparison instrumentation) ·
**n=120 paired seeds, L11, no pressure, workers=6**

## 0. TL;DR

**reach32 costs NOTHING on clean boards, and reproduces bit-for-bit.** Across all
120 seeds, reach32 (base32's 32 candidates filtered to the BFS-provably-reachable
subset) picked the IDENTICAL action to base32 on EVERY decision the two rigs made
independently (0/12183 decisions
diverged = 0.0%), giving pills delta
**+0.00 [+0.00,+0.00] WASH**,
clear 99.2%->99.2%, 0/120 seeds with any
pills/outcome difference at all. This is the predicted result from reach_root.py's
own selftest (`_selftest_reach32_eq_base32_open_board`): the filter only removes a
candidate when a column is walled to row 0 or something overhangs something, and
normal L11 play from a fresh board essentially never builds that structure —
reachability filtering is a legality FIX with zero measured downside here, not a
trade.

**reachfull reproduces the known tuck value, same sign and same order of
magnitude, CI overlapping the prior.** Adding the BFS's full reachable set
(straight + tuck-class, θ=250-gated) gives pills
**-10.61 [-15.66,-5.80] REAL**
vs the −18.05 [−25.69,−10.63] REAL prior (`TUCK_V3_FIRMWARE_SAGA.md`'s TE-free
θ=250 mirror rig, n=120) — a DIFFERENT rig family (mirror A/B of tucks firing vs
not, on top of the shipped decider) than this single-search root-candidate swap,
so treat this as a reproduction-of-sign/magnitude check, not a re-measurement of
the same estimator.

## 1. Arms

| arm | mechanism |
|---|---|
| base32 (control) | shipped strand20: all 32 (variant,col) straight drops via `_expand_core`, no reachability filter. Reproduces `ab47.py::_choose_base(wt=0, ws=20)` bit-exact (selftest). |
| reach32 | same 32 candidates, filtered to `tuck_enum.enumerate(mode="free")`'s BFS-reachable subset. Falls back to unfiltered base32 if the filter empties the set. |
| reachfull | ALL BFS-reachable rests (straight + tuck) as root candidates; tuck-class candidates gated by the tuck_v3 margin pattern, θ=250. |

## 2. Clear rates + paired pills deltas

| arm | clear rate | Δpills vs base32 (both-won pairs) | 95% CI | verdict | bad-ends (topout+stall) | moved seeds |
|---|---|---|---|---|---|---|
| base32 (ctrl) | 99.2% | -- | -- | -- | 1/120 | -- |
| reach32 | 99.2% | +0.00 | [+0.00,+0.00] | WASH | 1/120 | 120/120 |
| reachfull | 99.2% | -10.61 | [-15.66,-5.80] | REAL | 1/120 | 120/120 |

reachfull tuck fires/game: 3.65.

reach32 and base32 matched EXACTLY on pills+outcome for 120/120 seeds
(0 seed(s) differed at all, by any margin) — the paired-delta CI above
is [0,0] because the two full pill-count vectors are equal seed-for-seed, not
merely close.

## 3. Divergence rate by board height (same-state comparison)

Companion instrumentation (`reach_divergence.py`): drives each of the same
120 seeds with reach32 (its own decisions), and at EVERY decision additionally
computes what base32 would have chosen on the IDENTICAL board/pill state
(never used to drive — pure comparison). Height = `root_search.fill_height(fb)`,
the tallest column's occupied height (0-16), same definition `destroy.py` uses.

| board height | decisions | divergent | rate | all-32-unreachable fallback |
|---|---|---|---|---|
| 0-3 | 43 | 0 | 0.0% | 0 |
| 4-6 | 1025 | 0 | 0.0% | 0 |
| 7-9 | 3759 | 0 | 0.0% | 0 |
| 10-12 | 6873 | 0 | 0.0% | 0 |
| 13-16 | 483 | 0 | 0.0% | 0 |

**Total: 12183 decisions across 120 games,
0 divergent (0.0%),
0 decisions where the reachability filter emptied the
full 32-candidate set (0.0%).**

Reachability filtering binds RARELY on clean L11 boards, and even on the rare
decisions where 1+ of the 32 straight drops is provably unreachable, the
removed candidate is essentially never the argmax base32 would have picked —
divergence in the CHOSEN action is a strict subset of (and far rarer than) the
raw 2.70% unreachable-candidate rate `reach_root.py`'s module docstring reports
for the general (non-height-conditioned, cross all pill colors/positions)
population.

## 4. reachfull vs the known tuck-value prior

| | rig | mechanism | pills delta | 95% CI | verdict |
|---|---|---|---|---|---|
| prior | tuck_v3 mirror, n=120, θ=250 | TE-free tuck-fire A/B on top of shipped decider | −18.05 | [−25.69,−10.63] | REAL |
| this gate | reach_root_ab.py, n=120, θ=250 | reachfull root-candidate swap (base32 -> BFS full reachable set incl. tucks) vs base32 | -10.61 | [-15.66,-5.80] | REAL |

Both measurements point the same direction (tucks cost pills to reach a clear —
a plausible, previously-established finding: tuck-enabled play routes through
more careful/defensive placements, not necessarily fewer pills to a topout-free
clear) and the CIs are compatible. The two rigs are NOT the same estimator
(mirror-arm-on/off vs single-search-candidate-set-swap), so this is read as
sign/magnitude reproduction, not a tightened re-measurement of −18.05.

## 5. Verdict

reach32 (the pure legality fix): **SHIP WITH ZERO MEASURED COST** on clean L11
boards — bit-exact match to base32 across 120/120 seeds and
12183/12183
decisions. It binds only off clean boards (overhangs / row-0-walled columns),
which this gate does not manufacture.

reachfull (the #17-unified full-reach set incl. tucks): reproduces the known
tuck cost, same sign, CI-compatible with the −18.05 prior — no surprise here
either.

## Files

- `reach_root_ab.py` (owned by this task, not the protected `pressure_rig.py`)
- `reach_divergence.py` — same-state divergence-by-height instrumentation
- `results/reach_root_clean_reach32.json`, `results/reach_root_clean_reachfull.json`
- `results/reach_divergence_n120.json`
