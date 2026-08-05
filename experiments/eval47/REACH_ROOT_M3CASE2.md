# M3 DEATH-BOARD case study, ITERATION 2: reachfull2 (the fix) + reach32t/reachfull2t (the time-budget extension)

**Date:** 2026-08-05 · Re-runs `REACH_ROOT_M3CASE.md`'s exact 6 tape-commit
boards through all 6 `reach_root.py` modes (`base32`/`reach32`/`reachfull`
kept byte-for-byte unchanged for the before/after comparison; `reach32t`/
`reachfull2`/`reachfull2t` are new). Board source and conventions are
identical to the original report — see that file for the hooks-needed/
human-family definitions this one reuses.

Runner: `eval47/tmp_logs/m3case2.py` (new file; `tmp_logs/m3case.py` is
unmodified so its own 3-mode output stays reproducible). Raw JSON:
`eval47/tmp_logs/m3case2_raw.json`.

## 1. Acceptance check: does reachfull2 fix the defect?

`REACH_ROOT_VERDICT.md`'s prescription: reachfull2 must diverge from base32
on the boards where base32's own argmax is BFS-unreachable, not 0/6 like the
pre-fix `reachfull`.

Boards where base32's own argmax is BFS-unreachable: **4/6** (commits 1, 2,
4, 6 — identical to the original report's finding).

| mode | diverges from base32 on the 4 unreachable-argmax boards | still picks an unreachable base placement |
|---|---|---|
| `reachfull` (pre-fix, unchanged) | 0/4 | 4/4 |
| **`reachfull2` (THE FIX)** | **4/4** | **0/4** |
| `reachfull2t` | 4/4 | 0/4 |

**PASS.** `reachfull2` now diverges from `base32` on exactly the 4 boards the
verdict predicted, and never inherits an unreachable placement on any of the
6 commits. This matches the module-level defect test added to
`reach_root.py` (`_selftest_reachfull2_never_unreachable_base`, 20/20 forced
unreachable-argmax cases clean on a wider random-board sweep).

## 2. Per-commit table, all 6 modes

| # | base32 pick (reachable?) | reach32 pick | reachfull pick (pre-fix) | reach32t pick | **reachfull2 pick (fix)** | reachfull2t pick |
|---|---|---|---|---|---|---|
| 1 | col6 V (**NO**) | col4 V | col6 V (=base32, **BUG**) | col4 V | **col4 V** | col4 V |
| 2 | col7 V (**NO**) | col3 H | col7 V (=base32, **BUG**) | col3 H | **col3 H** | col3 H |
| 3 | col3 H (YES) | col3 H (=base32) | col3 H (=base32) | col3 H | col3 H | col3 H |
| 4 | col7 V (**NO**) | col1 V | col7 V (=base32, **BUG**) | col1 V | **col1 V** | col1 V |
| 5 | col0 V (YES) | col0 V (=base32) | col0 V (=base32) | col0 V | col0 V | col0 V |
| 6 | col7 V (**NO**) | col0 V | col7 V (=base32, **BUG**) | col0 V | **col0 V** | col0 V |

On every board where `base32`'s argmax was unreachable, `reachfull2` (and
`reachfull2t`) now land on the SAME reachable column `reach32` does (not
coincidence — no tuck candidate on any of these 6 boards beat the theta=250
margin over the now-corrected `best_base_val`, so the base branch's own
argmax wins in all 6 cases; this board family's fix is really about not
handing the AI an unreachable straight drop, not about unlocking a new tuck).

## 3. The time-budget extension is a COMPLETE NO-OP on this case study

`reach32t` and `reachfull2t` are **pixel-identical** to `reach32`/`reachfull2`
on all 6 commits: `n_within_budget == n_reach` on every single commit (18/18
for the base-branch candidates on 5 of the 6 boards, per the diagnostic
fields in `m3case2_raw.json`). `fallback_time` is `False` everywhere — the
time filter never has to fall back to an untimed choice because it never
removes anything in the first place.

This is a direct consequence of the CORRECTED DAS constants (see
`reach_root.py`'s own `DIST_DASEDGE`/`DIST_GRAVROW` comment, silicon-measured
2026-08-05, task #49 follow-on — NOT the stale 32/26 pair `CART_FIX_REPORT.md`
section 7's prose quotes): under `DIST_DASEDGE=12, DIST_GRAVROW=30`, the
DIST_TABLE budget saturates at its max (7 edges) once a candidate's resting
row is >= 3 rows from spawn, and the WORST-CASE column distance on an
8-column board is only 3 edges (columns 0 or 7). So the time filter can only
ever bind on a candidate resting in the top 1-2 rows of the board — an
extremely narrow window that this 6-board, real-death-board sample never
hits, even though these are exactly the "near-topout, critically-stacked"
boards DISTGATE's own silicon remeasurement targeted.

| commit | base32 hooks_needed, historical (32/edge, STALE) | exceeds historical 40-hook window | base32 hooks_needed, corrected (12/edge) |
|---|---|---|---|
| 1 | 64 | YES | 24 |
| 2 | 96 | YES | 36 |
| 3 | 0 | no | 0 |
| 4 | 96 | YES | 36 |
| 5 | 96 | YES | 36 |
| 6 | 96 | YES | 36 |

Under the historical (stale) constants 5/6 of base32's own picks "exceed the
window" — under the corrected constants, none of these numbers are compared
against a rescaled window in this report (that rescaling is out of this
task's scope, flagged not fixed), but the raw hooks_needed values are ~2.7x
smaller across the board, consistent with DAS being measured much faster
than the stale assumption.

## 4. Human-family ({0,6,7}) match

Unchanged from the original report's pattern: `base32`/`reachfull2`/
`reachfull2t` match the human-preferred family on 5/6 commits (only commit 3,
the documented tape-agreement counter-case, lands elsewhere — correctly, per
the original report's own note). `reach32`/`reach32t` still only match on
2/6 (5, 6) — the pure-legality (and legality+time) filters still trade value
and human-recognizable placement for physical feasibility on this board
family, exactly as `REACH_ROOT_M3CASE.md` §5 found for `reach32` alone.

## 5. Late-start (decision-latency) sensitivity — team-lead follow-on

**Question:** §3's zero-divergence result assumes steering can begin AT
SPAWN (hook 0). If the search itself burns hooks before a target column is
even known, the EFFECTIVE budget at the moment steering can actually start
is smaller than what `reach32t`/`reachfull2t` compute from a spawn-time
snapshot. Does accounting for that latency change §3's picks — i.e. does the
zero-divergence result "localize the mechanism in late decision arrival
(search latency), not movement physics," as hypothesized?

**Method:** `tmp_logs/m3case_sensitivity.py` (new, read-only — does not touch
the shipped `reach_root.py` choosers) re-scores the same 6 boards' reachable
candidates with `hooks_available` reduced by a `late_start_hooks` penalty
swept over 0 (the as-shipped assumption), 10, 20 (the requested probe point),
30, 40, 50, 60, 70, 80, 84 (the maximum possible `hooks_available`, at which
point every non-spawn-column candidate is excluded by construction).

**Result: NO flip at the requested 20-hook probe point, or anywhere up to
40.** Only 3 of the 6 boards (4, 5, 6) flip at all in the full sweep, and not
until a MUCH larger penalty:

| commit | flips at late_start_hooks= | from → to | at 20 (requested probe) |
|---|---|---|---|
| 1 | never (0-84) | — | no flip (pick is already col4, a spawn column, 0 edges — immune by construction) |
| 2 | never (0-84) | — | no flip (pick is col3, also a spawn column) |
| 3 | never (0-84) | — | no flip (base32-reachable, 0 edges, all arms agree already) |
| 4 | 70 | col1 → col3 | no flip |
| 5 | 50 | col0 → col1 (further: 70→col2, 80→col3) | no flip |
| 6 | 50 | col0 → col1 (further: 70→col2, 80→col3) | no flip |

**Reading:** commits 1, 2, 3 never flip because `reachfull2t`'s pick on those
boards was ALREADY a spawn-adjacent column (0 edges needed) — there's no
budget left to squeeze. Commits 5 and 6 (both picking `col0`, 3 edges, the
SAME far column `base32`/`reachfull2` prefer) DO eventually get squeezed
toward nearer columns, but only once the penalty reaches ~50-60 hooks
(25-30 frames, ~0.4-0.5s of decision latency) — more than double the
requested 20-hook probe, and commit 4 not until ~70 hooks. **This refutes
the "late decision arrival" hypothesis AT THE REQUESTED PROBE POINT**: a
20-hook (10-frame, ~0.17s) decision-latency assumption changes nothing on
any of the 6 boards. Whether a real depth-3 copro search actually burns
50+ hooks (~0.4-0.5s) before a target column is known is NOT established by
this task (no search-latency measurement is cited or made here) — flagged as
the open question this sensitivity check narrows but does not close. Given
the bursty-pressure gate's statistical (not modeled) evidence already shows
`reachfull2t` harmful under real play (`REACH_ROOT_BURSTY2.md`), this
sensitivity result doesn't change the ship recommendation — it does show
that IF a "late decision arrival" story is going to rescue the time filter,
it needs a decision-latency figure well north of 20 hooks, on real evidence,
not an assumption.

Raw data: `tmp_logs/m3case_sensitivity_raw.json`.

## Files

- Runner: `eval47/tmp_logs/m3case2.py` (new; `m3case.py` untouched)
- Raw JSON: `eval47/tmp_logs/m3case2_raw.json`
- Late-start sensitivity: `eval47/tmp_logs/m3case_sensitivity.py` (new,
  read-only re-scoring, does not modify `reach_root.py`), raw data
  `eval47/tmp_logs/m3case_sensitivity_raw.json`
- Modes under test: `eval47/reach_root.py` (`choose_reachfull2`/
  `choose_reach32t`/`choose_reachfull2t`, `_selftest_reachfull2_never_
  unreachable_base` for the defect test, `_selftest_dist_table_matches_
  driver` for the constants cross-check)
