# TRANSFER FILTER -- Hunt A / Hunt B candidate exploits -- INTERIM / TRUNCATED

**STATUS: INTERIM. The perturbation battery is CODE-COMPLETE, SMOKE-TESTED, and RUNNING
(nohup+disowned, PID 1942955, `adversary/transfer_filter.py`), but this report was forced to
finalize before the run finished.** Only the honest-baseline reference batches had completed at
truncation (model fit + 2x n=40 honest-baseline runs, ~150s of an estimated ~45min/~1500-game
total). **No candidate has been perturbed yet.** The structural/fluke counts below are **0 and 0
because nothing has been classified yet -- this is NOT a negative result**, unlike Hunt A's
genuine documented negative (see §1). This is the same failure mode `SEED_CENSUS.md` hit
(interactive session ended before its background budget did) -- same house handling: leave the job
running, document exactly how far it got, and give the re-run recipe.

The background process is untouched by this report and will keep writing to
`adversary/tmp_logs/transfer_filter_run.log` and checkpoint to
`adversary/transfer_filter_result.json` (written once, atomically, at the very end of the run --
if that file exists, the run finished; there are no incremental checkpoints in this version of the
script). A follow-up session should: (1) check `pgrep -af transfer_filter.py` / whether
`transfer_filter_result.json` exists, (2) if it exists, re-derive this report's §2/§3 tables from
it, (3) if the process died without producing that file, re-launch with
`python transfer_filter.py --workers 6 --out transfer_filter_result.json` (~45min at this box's
current load; safe to shrink `N_*` constants at the top of the file for a faster, smaller-n pass
if the box is under load from other agents' jobs).

---

## 1. Hunt A (SEED_CENSUS.md) -- ZERO candidates, confirmed, nothing to transfer-filter

Checked `census/TAIL_SEEDS.json` directly (all 70 SLOW-decile tail seeds, the only seeds
`SEED_CENSUS.md` flagged at all): **every one of the 70 has `result == "clear"` and
`fatal_board == None`.** Combined with `SEED_CENSUS.md`'s own headline (0/674 topout or stall at
that truncation), Hunt A produced **no fatal board, no topout, no stall -- zero candidate exploits
of any kind** to run through this filter. The "SLOW" flag is a pills-to-clear tail statistic, not
a failure in the house taxonomy (TOPOUT / DIES_AHEAD / STALL), and `SEED_CENSUS.md`'s own
structure check already found NO SIGNATURE distinguishing the slow-decile seeds from matched
controls (largest |Δ|/pooled_sd = 0.35, virus_color_red, nowhere near a flag threshold). **There is
nothing here to perturb.** This is a second, independent documented negative stacked on top of
`SEED_CENSUS.md`'s own -- consistent with each other at small n, not manufactured. If Hunt A's own
background census job (also left running per its report) surfaces an actual TOPOUT/STALL/fatal
board later, that seed becomes a Hunt-A candidate and should be run through this same battery
before being called a finding.

## 2. Hunt B (ADVERSARIAL_PRESSURE.md) -- 4 candidates queued, methodology locked, results PENDING

### 2.1 What is queued and why (see `transfer_filter.py`'s own docstring for the authoritative
version -- summarized here)

| candidate | primary metric (per its own report framing) | genome source |
|---|---|---|
| `ga_near_spawn_a` | dies_ahead | GA-discovered, rank 1, §2.1 of ADVERSARIAL_PRESSURE.md |
| `ga_near_spawn_b` | dies_ahead | GA-discovered, rank 2 |
| `honest_shape_spawn_target` | dies_ahead | targeting-isolation control, §2.2 |
| `always_spawn_max` | **topout** (its own report shows it is *worse* than honest on dies_ahead, §2.3) |

Five perturbation categories per candidate, majority vote (>=3/5 survive => STRUCTURAL):

1. **neighbouring seeds** -- fresh, disjoint seed block (`5,000,200-5,000,239`, n=40), immediately
   adjacent to but never overlapping the original n=120 holdout (`5,000,000-5,000,119`) or the GA
   training pool (`4,000,000+`).
2. **history-shift** -- the SAME seed, pill stream shifted by exactly one pill via
   `nes_pills.NesPillSource(seed=seed, skip=2)` instead of the house-standard `skip=1` ("the ROM
   burns one before play") -- identical 16-bit RNG state, every subsequent pill draw moved one slot
   in the same 128-length sequence. Applied only to the seeds that were **actually** fatal for that
   candidate in a fresh n=40 baseline-capture batch (capped at 15 fatal seeds/candidate for cost).
3. **timing jitter** -- each volley's fire/size/column RNG draw anchored at `pills_placed +/- 1`
   (sign drawn per-event from an independent small RNG keyed on `(seed, pills_placed)`), simulating
   the adversary's decision clock being off by one pill.
4. **column jitter** -- each chosen target column shifted +/-1 (clipped to the 8-wide board),
   sign drawn per-event from the schedule's own event RNG stream, appended *after* the unperturbed
   draws so the unperturbed path is untouched.
5. **volley-size jitter** -- `n_cells` shifted +/-1 (floor 1, still capped at the 53-halve budget),
   same per-event draw convention as (4).

"Survives" a category = the perturbed run's 95% Wilson CI lower bound on the primary metric clears
the LOCAL honest-baseline's 95% CI upper bound, measured on the *same* seed set for that category
(not the original n=120 numbers) -- overlapping CIs count as NOT surviving (conservative by
design, per the honesty rules' instruction to not manufacture exploits).

### 2.2 Predecessor A/B (queued, follows perturbation results)

For every candidate that comes back STRUCTURAL, the script re-runs that exact schedule against the
**pre-#47 predecessor decide path** -- `reach_root.choose_base32(..., ws=0)` (winner weights, NO
`g_stranded` root-only term; `ws=20` is the strand20 champion, `ws=0` is everything that shipped
before task #47) -- on a third fresh seed block (`5,000,400-5,000,459`, n=60), paired against the
honest baseline run through the SAME `ws=0` path and against the champion (`ws=20`) run on the same
seed block for a clean same-seed three-way comparison. This is the check for "long-standing
weakness (kills both configs)" vs. "strand20-introduced regression (kills only ws=20)" the task
asks for. **Not yet run** -- gated on the perturbation stage finishing first (it only spends
compute on candidates that survive).

### 2.3 What actually ran before truncation

Only the honest-baseline reference batches (needed by every candidate's comparison, so run once up
front): `honest_v1_1_random` model fit (`n_volleys=28`, `n_clears=89`, freshly re-fit from footage
per house convention, not a stub) completed, then its evaluation on `base_seeds`
(`5,000,000-5,000,039`, n=40) and `neighbor_seeds` (`5,000,200-5,000,239`, n=40) were in flight.
**Zero candidate schedules had been evaluated at truncation** -- no perturbation numbers exist yet
for any of the four candidates.

## 3. Honesty-rule bookkeeping

- **n reported for every rate**: not applicable yet -- no candidate rates exist to report. This
  report does not manufacture placeholder numbers for missing data.
- **Structural vs. fluke**: **0 structural, 0 fluke is a count of what has been classified, which
  is nothing** -- not a claim that all four candidates are flukes. Treat both counts as "pending,"
  not "negative," when reading this report's `structural`/`fluke` fields.
- **Hunt A**: genuinely checked (not skipped) -- zero fatal boards exist in its own data, so zero
  candidates were available to feed this filter from that hunt. That part of this report IS final.
- **Reuse audit**: perturbation harness (`transfer_filter.py`) reuses `adversary_search.py`'s
  `bin_of`, `choose_target_cols`, `SIZE_POOL`, `BINS`, `_honest_inject`, `summarize`,
  `build_honest_v1_1_model`, `_chunksize` verbatim; only the injection/play functions are
  duplicated-with-jitter-hooks (documented in the module docstring), and the champion decide path
  (`reach_root.choose_base32`) and NES pill stream (`nes_pills.NesPillSource`) are untouched,
  called exactly as `adversary_harness.py`/`adversary_search.py` already call them, `ws` threaded
  through as a plain parameter for the predecessor A/B rather than re-derived.
- **Smoke-tested before the long run**: `play_seed_adversarial_perturbed` was hand-verified against
  seed 5,000,000 with `ws=20`/unperturbed, `ws=20`/all-three-jitters-on, and `ws=0`/unperturbed
  before launch -- all three ran to completion with sane `(result, pills, viruses_left,
  garbage_injected)` tuples (topout/6 viruses-left/40 garbage; clear/73 pills/24 garbage;
  topout/2 viruses-left/46 garbage respectively) -- see `tmp_logs/` for the smoke session.

## 4. Files

- `transfer_filter.py` -- the perturbation battery (jittered inject/play functions, CI-separation
  survival rule, predecessor A/B driver). Source of truth for exact perturbation semantics.
- `transfer_filter_result.json` -- will contain the full per-candidate, per-perturbation
  stat/honest/survives breakdown plus the predecessor A/B arms, once the background run completes.
  **Does not exist yet at the time of this report.**
- `tmp_logs/transfer_filter_run.log` -- live stdout of the background run; check this first in any
  follow-up session.
