# Hunt B: Adversarial Garbage Scheduler vs. the strand20 champion

**Date:** 2026-08-06 · **Target:** `fast_rtl_x.variant("winner")` + `eval47/terms47.g_stranded` at ws=20,
root-only (`ab47.py::_choose_base(wt=0, ws=20)`, bit-exact via `reach_root.choose_base32` — see
`adversary_harness.py`'s own header for the provenance chain). L11, real NES pill stream
(`NesPillSource`).

**Verdict up front: the exploit is real, large (13x the honest dies-ahead rate), holds at n=120,
and is earned within the same garbage budget the honest human model spends — and it is driven
almost entirely by column TARGETING, not by firing more often or sending more material.**

---

## 1. Method

### 1.1 Earnability budget (not invented here — cited)

Per task instruction, the adversary's total garbage per game is capped at what a human sender
produces on average, cited from this project's own honest fit:
`BURSTY_V1_RESULTS.md` §5, `results/bursty_v1_1_n120_wt0_ws20.json` — the champion (ws=20) arm's
measured average garbage/game under the struktured-only (pool-decontaminated) bursty v1.1 model,
n=120, is **52.925 halves**. `BUDGET_HALVES = round(52.925) = 53` is a **hard per-game cap** — every
schedule below, honest or adversarial, is truncated the instant it would exceed 53 halves in one
game. This is a strictly conservative reading of "no more than a human sends on average" (a hard
per-game ceiling is tighter than an average-only constraint).

### 1.2 Clear-triggered only

A volley may fire **only** immediately after the champion's own placement clears cells (the same
"opponent clear stands in for the AI's own clear" convention `pressure_rig.py`'s bursty branch and
`bursty_model.inject_bursty_garbage()` already use — reused verbatim here, not reinvented). No clear
this placement ⇒ zero chance of a volley, structurally: `bin_of(0)` matches none of the three
clear-size bins `(4,6)`, `(7,10)`, `(11,999)`. An attack never appears from nowhere.

### 1.3 Schedule encoding (the search space)

A schedule ("genome") is:
- **fire probability per clear-size bin** — `{4-6: p, 7-10: p, 11+: p}`, free in `[0,1]`. This is the
  *timing* axis: which of the champion's own clears earn a follow-up, subject to the same total
  budget everyone shares.
- **volley-size weights** over `{2,3,4,5,6}` — the empirical histogram's own support
  (`bursty_model.py`'s fitted volley-size histogram from footage; no schedule can invent a bigger
  volley than any human sender in the footage ever produced).
- **target-column policy** — `random` (honest baseline's own policy) / `spawn` (columns 3,4 first,
  the NES's actual spawn lane) / `near_spawn` (columns ranked by distance to 3,4) / `tallest` /
  `thin`.

Board-mutation mechanics (first-empty-row-from-top, unlinked single half, random color 1..3,
gravity+resolve after) are copied verbatim from `pressure_rig._inject_garbage` /
`bursty_model.inject_bursty_garbage` — only the **decision** (fire? how big? which columns?)
differs between the honest model and an adversarial schedule.

### 1.4 Search

(mu+lambda) evolutionary search (no external deps), fitness = `1000×dies_ahead_rate +
topout_rate` (dies-ahead dominates, topout is the tie-break — matching the task's stated priority
order), evaluated on a small disjoint training seed pool (seeds 4,000,000+, pill cap 100 during
search only, to bound worst-case per-game cost under heavy pressure — final validation always uses
the house-standard 300-pill cap). Run **three independent times** this session at different
population/generation scales; all three converged on the same qualitative shape: `near_spawn`
targeting, fire probability ~35–51% on the two common clear-size bins, near-zero on the rare 11+
bin. That convergence, not any single run's numeric genome, is the search-phase finding.

### 1.5 Holdout (the number that matters)

Best/representative genomes from the search, plus two hand-built controls, were re-evaluated on
**n=120 holdout seeds (5,000,000–5,000,119), disjoint from every training seed**, at the full
300-pill house-standard cap, against a **matched-volume honest baseline**: the real, struktured-only
bursty v1.1 model (`fit_ensemble_source.fit_per_player`, not a stub), driven by the *same* play loop,
same budget cap, same seeds. This is the paired comparison the task asks for.

---

## 2. Results (n=120 every row, holdout seeds, 300-pill cap, budget=53 halves)

| schedule | dies-ahead | topout | clear | avg garbage/game |
|---|---|---|---|---|
| **honest v1.1 random** (control) | 2.5% [0.0, 5.3] | 3.3% | 92.5% | 42.4 |
| **ga_near_spawn_a** | **32.5% [24.1, 40.9]** | 65.8% | 34.2% | 35.1 |
| ga_near_spawn_b | 28.3% [20.3, 36.4] | **80.8%** | 19.2% | 32.2 |
| honest_shape_spawn_target | 24.2% [16.5, 31.8] | 46.7% | 52.5% | **27.2** |
| always_spawn_max | 0.8% [0.0, 2.5] | **95.8%** | 4.2% | 33.9 |

95% CIs are normal-approximation binomial, n=120 per row.

**Every adversarial schedule spent LESS average garbage than the honest baseline's own natural
average (42.4 halves)** — the exploit is not "send more," it is "send the same or less, better
aimed."

### 2.1 The headline number

`ga_near_spawn_a` (GA-discovered, `near_spawn` targeting): **dies-ahead 32.5% vs. the honest
baseline's 2.5% — a 13.0x multiple, +30.0 percentage points, non-overlapping 95% CIs, at 83% of the
honest baseline's own average garbage volume.** This is the primary metric the task asks the
adversary to maximize, confirmed at n=120, not a small-n candidate.

### 2.2 Targeting is the lever — isolated cleanly

`honest_shape_spawn_target` keeps the honest v1.1 model's **own** fire probabilities and volley-size
mix (the real human-observed cadence, not GA-tuned) and changes **only** the column choice from
random to spawn-first. Result: dies-ahead **24.2%** (9.7x the honest baseline) at **27.2 halves
average** — the *lowest* garbage spend of any candidate, well under both the 53-halve budget and the
honest baseline's own 42.4-halve natural average. A skilled human sender who simply *aims* at the
opponent's spawn lane, without changing anything else about when or how much they send, gets most of
the exploit for free. This isolates targeting as the dominant variable, cleanly, with everything else
held at the honest human shape.

### 2.3 Dies-ahead and raw topout are DIFFERENT levers — a documented negative

`always_spawn_max` (fire=1.0 every bin, always the max observed volley size, spawn targeting) is the
single best schedule for raw **topout** (95.8%, 29x the honest baseline) — but it is *worse than the
honest baseline* on **dies-ahead specifically** (0.8% vs. 2.5%). Maximal, unconditional pressure
buries the champion outright, early, while it still holds many viruses; it does not reproduce the
"dies on the doorstep of clearing" signature the task's failure taxonomy singles out and asks to be
maximized *first*. The GA-tuned schedules (which throttle fire probability rather than always firing)
land closer to the doorstep and score far higher on dies-ahead precisely because they don't
overwhelm the board outright. **Honest negative, not manufactured:** "just send everything, aimed at
spawn" is a worse dies-ahead exploit than a calibrated schedule, despite being the crudest and most
brute-force candidate tried. Naive maximal aggression is not the answer to this specific failure
mode — timing/throttling matters too, just less than targeting.

---

## 3. Honesty-rule bookkeeping

- **n reported for every rate above** (all n=120, holdout, disjoint from training).
- **Transfer filter applied**: every number in §2 is from the *holdout* run, not the GA training run
  the genomes were found on. The GA search itself (trained at n≤24 per generation, pill-capped for
  speed) surfaced *candidates*; only the n=120 holdout numbers in §2 are reported as findings.
- **Matched-volume comparison, not "infinite garbage kills it"**: every adversarial schedule's
  average garbage spend (27.2–35.1 halves) is *at or below* the honest baseline's own natural
  average (42.4 halves) under the identical hard 53-halve cap. The exploit's size is not an artifact
  of handing the adversary more material — if anything the adversarial arms are spending less.
- **A negative is reported, not hidden**: `always_spawn_max` failing to beat the honest baseline on
  dies-ahead (§2.3) is exactly the kind of result the honesty rules ask to be surfaced rather than
  quietly dropped in favor of the flashier topout number.
- **Search-phase directional evidence**: three independent in-session GA runs (population/generation
  scales varied for wall-clock reasons — see §4) all converged on `near_spawn`/`spawn` targeting as
  the dominant lever before the n=120 holdout confirmed it; that convergence is corroborating, not
  load-bearing — the load-bearing numbers are §2's holdout table.

---

## 4. What this is NOT (scope honesty)

- **Not a full 3-hour GA sweep.** Wall-clock constraints in this session meant the GA search phase
  ran at reduced population/generation/train-seed scale across three attempts (documented in
  `tmp_logs/`) rather than one long continuous search. The search converged on the same targeting
  lever every time it was run, which is itself informative (a shallow, robust optimum, not a fragile
  one requiring exhaustive search to find) — but a longer search was not exhausted to look for a
  larger optimum than `near_spawn`/`spawn`. Anytime deliverable, as scoped by the task.
- **Not tested against every wt/ws configuration** — only the shipped strand20 champion
  (wt=0, ws=20) per the task's stated target.
- **`tallest` and `thin` target modes were implemented in the search space but did not surface as
  GA winners** in any of the three search runs; not separately holdout-validated here since they
  were dominated in training.

---

## 5. Files

- `adversary_search.py` — full GA + holdout harness (schedule encoding, board mechanics, GA driver).
- `validate_only.py` — the script that produced §2's numbers: skips re-running the GA (already
  converged 3x) and holds out the representative genomes directly at n=120/300-pill/budget=53.
- `validate_result.json` — raw output backing §2's table (per-arm dicts with n/clear/topout/
  stall/dies_ahead counts, not just the rates).
- `best_schedules.json` — the 4 adversarial schedules + honest baseline, machine-readable, with
  provenance header.
- `smoke_result3.json` (in scratchpad, referenced for the search-convergence claim in §1.4/§3) —
  earliest independent replication of the near_spawn/spawn finding at small n, used only as
  corroborating evidence per §3, not as a holdout number.

## 6. Reuse audit (nothing re-derived that already existed)

- Champion decide path: `adversary_harness.py::_lazy()` / `reach_root.choose_base32`, untouched.
- Board mutation mechanics: copied from `pressure_rig._inject_garbage` /
  `bursty_model.inject_bursty_garbage`.
- Honest model: `bursty_model.fit_struktured_20260804()` + `fit_ensemble_source.fit_per_player()`,
  the same call `run_bursty_v1_1_validity.py` uses — not a stub, not a saved-JSON copy (rebuilt
  in-process from live footage each run, per that script's own documented convention).
- Budget: cited from `BURSTY_V1_RESULTS.md` §5's own measured number, not assumed.
