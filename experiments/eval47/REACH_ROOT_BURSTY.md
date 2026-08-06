# BURSTY-PRESSURE gate: reach_root A/B (base32 / reach32 / reachfull)

**Date:** 2026-08-05 · **Rig:** `eval47/reach_root_ab.py --pressure bursty` (this session added
`viruses_left_at_end` / `dies_ahead` tracking + exact McNemar to the script; `pressure_rig.py`
itself untouched, read-only per file-ownership rule)
**Model:** `bursty_model.py` `BurstyPressureModel` v1 (same fit as `BURSTY_V1_RESULTS.md`:
n_matches=4, n_volleys=61, n_clears=188)
**L11, n=120 paired seeds (0-119), workers=6, base32 is the control for every arm.**

This is the decisive test for task #17-unified's central hypothesis: *does the shipped decider's
blindness to reachability (`ab47.py::_choose_base` enumerates all 32 straight-drop (col,orient)
slots and never asks whether a pill can physically get there) explain a material share of the
"dies-ahead" pressure deaths?* `reach32` isolates the pure legality fix (same 32 candidates,
illegal ones removed, nothing added). `reachfull` adds the full BFS-reachable set (straight +
tuck-class, theta=250-gated). Reading `reach32` first isolates the fix; `reachfull` second prices
the ceiling that includes genuine new tuck capability.

## 1. Control sanity check

`base32` reproduces the shipped strand20 decider (`ab47.py::_choose_base(wt=0, ws=20)`)
bit-for-bit per `reach_root.py`'s own selftest. Its bursty-pressure numbers here should match
`BURSTY_V1_RESULTS.md`'s shipped-baseline row exactly, since it's the same env, same seeds, same
model fit, same injection convention:

| | bad-ends (topout+stall) | topout / stall | dies-ahead (v≤12) |
|---|---|---|---|
| **`BURSTY_V1_RESULTS.md` shipped ws=20** | 32/120 (26.7%) | 21 / 11 | 16/120 (13.3%) |
| **this run's `base32` control** | 32/120 (26.7%) | 21 / 11 | 16/120 (13.3%) |

Exact match on every field. The rig and the disease-defining baseline are measuring the same
thing.

## 2. Results

| arm | pills Δ (both-won, n) | clear rate | bad-ends | **dies-ahead (v≤12)** | dies-ahead rate | viruses@death | McNemar (rescued/harmed, p) | tuck_fires/g |
|---|---|---|---|---|---|---|---|---|
| **base32 (control)** | — | 73.3% (88/120) | 32/120 | 16/120 | **13.3%** | 5.41 | — | 0.00 |
| **reach32** | −1.36 [−3.69, +0.00] **WASH** (n=85) | 71.7% (86/120) | 34/120 | 20/120 | **16.7%** | 5.65 | 1 / 3, p=0.625 (moved 4/120=3.3%) | 0.00 |
| **reachfull** | −29.87 [−44.84, −14.42] **REAL** (n=79) | 85.0% (102/120) | 18/120 | 11/120 | **9.2%** | 5.39 | 23 / 9, p=0.0201 (moved 32/120=26.7%) | 4.17 |

garbage/g (halves injected): base32 63.62 → reach32 61.42 → reachfull 46.94 (reachfull's lower
figure is a consequence of finishing in ~30 fewer pills on average, not a change in the injection
rule — fewer placements played before the game ends means fewer bursty-firing opportunities).

## 3. Why reach32 is null: the legality gap is nearly nonexistent on boards the AI actually visits

`reach_root.py`'s docstring quotes a global figure of 2.70% of the 32 straight-drop candidates
being physically unreachable (walled off by a column filled to row 0). Instrumented directly on
this run's `reach32` arm (`n_reach / n_base_legal` per decision, averaged per game):

- mean `reach_frac` (reachable / 32) across all 120 games = **0.9971** — i.e. the AI loses on
  average **0.29%** of its candidate set to illegality, an order of magnitude below the
  docstring's 2.70% corpus-wide figure.
- only **31/120 games** ever hit a decision where even one candidate was illegal.
- worst case observed: `reach_frac` = 0.9678 (≈1 of 32 candidates removed at that game's worst
  decision).

Under bursty pressure, at L11, playing the shipped strand20 weights, the boards the decider
actually reaches essentially never have the severe overhangs that would wall off a straight-drop
column. The legality bug is real (confirmed by the earlier `tuck_enum.py` corpus study) but it
almost never fires on the game states this rig's pressure regime produces, so removing those rare
illegal candidates from the argmax has nothing to bite on.

## 4. Verdict on the hypothesis

**REFUTED for reach32.** Unreachable-argmax placements are NOT a material contributor to
bursty-pressure dies-ahead deaths. reach32's paired-pills delta is a WASH (CI includes 0, and its
upper bound sits at exactly 0.00). Its bad-end McNemar is not significant (p=0.625, only 4/120
seeds moved at all). Its dies-ahead count moved in the **wrong** direction, 16/120 (13.3%) →
20/120 (16.7%) — nominal, not statistically distinguishable from noise given only 4 discordant
seeds, but there is no signal here supporting the hypothesis in either magnitude or direction.

**reachfull is REAL, but for a different reason.** Bad-ends fall 32→18 (McNemar p=0.020, 32/120
seeds moved), clear rate rises 73.3%→85.0%, and dies-ahead falls 13.3%→9.2%. The mechanism behind
this delta is not the legality subtraction (`tuck_fires/g=0.00` in reach32, meaning zero tuck-class
candidates exist in that mode by construction) — it's reachfull's **addition** of genuinely new
tuck-class root candidates: mean 6.39 legal tuck candidates per decision beyond the 32 straight
drops, and the AI actually fires a tuck placement on average **4.17 times per game** (118/120
games fired at least one). reachfull's win is a capability expansion, not a bug fix.

**Per the task's own conditional: reach32 does NOT move dies-ahead, so say so plainly.** This
means the "unreachable placements kill the AI at decision time" story is refuted for the
decision-time (spawn-time) tier that `reach32`/`reachfull` both operate on (both are exact
spawn-time BFS reachability per `TUCK_BFS_PORT_REPORT.md`'s proof — `reachfull`'s edge is *breadth
of the candidate set*, not a *different point in time*). This experiment does not itself test the
late-arrival/mid-fall tier (explicitly out of scope here, owned by DRDISTGATE) — but by
elimination, since decision-time legality-only filtering is null and decision-time capability
expansion (reachfull) only partially closes the gap (13.3%→9.2%, still 11 dies-ahead games left),
whatever residual dies-ahead mechanism reach32/reachfull cannot touch is a candidate for the
late-arrival tier or another mechanism entirely — this run does not distinguish between those
two remaining explanations, only that decision-time legality-pruning isn't it.

**Net structural-fix framing:** the #17-unified structural fix's *value* here is mostly the tuck
unification (reachfull's genuine new tuck-class reach), not the reach32 legality prune. reach32 in
isolation should not be shipped as a pressure-death mitigation — it does nothing and trends
slightly negative.

## Provenance

- Rig (edited this session, owned by this task): `/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/reach_root_ab.py`
  — added `viruses_left_at_end` / `dies_ahead` (threshold v≤12, same convention as
  `pressure_rig.py`) tracking to `play()`, and exact-binomial McNemar (`scipy.stats.binomtest`,
  same convention as `analyze_reactive.py::mcnemar`) plus dies-ahead/viruses-at-death reporting to
  `compare()`.
- Decider/modes: `/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/reach_root.py`
  (`MODES = (base32, reach32, reachfull)`, unmodified).
- Bursty model: `/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/bursty_model.py`
  (`fit_struktured_20260804()`, read-only import, unmodified).
- `pressure_rig.py`: NOT imported, NOT modified — own runner replicates its injection convention
  (rng from `(seed, pills_placed)`, `board._apply_gravity()` before `resolve()` after injection)
  exactly, per file-ownership rule.
- Run command: `reach_root_ab.py --seeds 120 --workers 6 --level 11 --arms reach32 reachfull
  --pressure bursty --out results/reach_root_bursty_n120`
- Raw results: `results/reach_root_bursty_n120_reach32.json`,
  `results/reach_root_bursty_n120_reachfull.json` (each has its own freshly-computed `ctrl` +
  `arm` full per-seed rows).
- Driver log: `tmp_logs/reach_root_bursty_n120.log`.
- Smoke tests before the full run: n=8 (`tmp_logs/smoke_reach_bursty_*.json`) and n=12
  (`tmp_logs/smoke2_reach32.json`) — ran clean, no exceptions, plausible numbers.
- Comparison baseline: `BURSTY_V1_RESULTS.md` (shipped ws=20 under bursty: 32/120 bad-ends,
  16/120 dies-ahead 13.3% — reproduced exactly by this run's `base32` control, §1).
