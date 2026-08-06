# BURSTY-PRESSURE gate, ITERATION 2: reachfull2 (the fix) + reach32t/reachfull2t (the time-budget extension)

**Date:** 2026-08-05 · **Rig:** `reach_root_ab.py --pressure bursty` (this
iteration added `time_frac`/`fallback_time_frac` diagnostics to `play()`/
`compare()` for the new `*t` modes; `base32`/`reach32`/`reachfull` code
paths and `pressure_rig.py` untouched). Same model, same seeds (0-119),
same env as `REACH_ROOT_BURSTY.md`.

## 1. Control sanity check

`base32`'s control numbers reproduce `REACH_ROOT_BURSTY.md`'s own control
exactly: 32/120 bad-ends, 16/120 (13.3%) dies-ahead, clear 73.3%. Same
baseline, same disease definition.

## 2. Results

| arm | pills Δ (both-won, n) | clear rate | bad-ends | **dies-ahead (v≤12)** | McNemar (rescued/harmed, p, moved) | tuck_fires/g |
|---|---|---|---|---|---|---|
| **base32 (control)** | — | 73.3% | 32/120 | 16/120 (**13.3%**) | — | 0.00 |
| reach32 (prior, unchanged) | −1.36 WASH | 71.7% | 34/120 | 20/120 (16.7%) | 1/3, p=0.625 (4/120=3.3%) | 0.00 |
| **reach32t** | −0.12 [−4.14,+4.04] **WASH** | 66.7% | 40/120 | 27/120 (**22.5%**) | 6/14, p=0.115 (20/120=16.7%) | 0.00 |
| reachfull (prior, unchanged, pre-fix) | −29.87 REAL | 85.0% | 18/120 | 11/120 (9.2%) | 23/9, p=0.020 (32/120=26.7%) | 4.17 |
| **reachfull2 (THE FIX)** | **−29.44 [−44.58,−14.01] REAL** | 85.0% | 18/120 | 11/120 (**9.2%**) | 22/8, p=0.016 (30/120=25.0%) | 4.17 |
| **reachfull2t** | **−32.14 [−45.31,−19.00] REAL** | 83.3% | 20/120 | 15/120 (**12.5%**) | 23/11, p=0.058 (34/120=28.3%) | 4.32 |

**`reachfull2` reproduces the pre-fix `reachfull`'s aggregate numbers almost
exactly** (dies-ahead 9.2% both, bad-ends 18 both, pills −29.44 vs −29.87,
McNemar both p<0.02) — the defect the fix corrects (inheriting an
unreachable base32 argmax) is real and confirmed on the M3 death-boards
(`REACH_ROOT_M3CASE2.md`), but it's a RARE combination in the general n=120
bursty-seed population (unreachable argmax AND no tuck beating theta=250 AND
that unreachable pick being the actual argmax at that decision) — common
enough to matter on the specific high-holed board family M3 targets, rare
enough not to move this aggregate statistic much. This is expected and
correctly scoped: the fix is about CORRECTNESS (never propose the physically
impossible), not about closing the aggregate dies-ahead gap further — that
was already `reachfull`'s own tuck-expansion mechanism, unchanged by the fix.

## 3. THE TIME-BUDGET EXTENSION IS NOT A WASH — IT'S DIRECTIONALLY HARMFUL

This is the central finding of this iteration, and it does NOT match the
"if reach32t is also a wash" framing the task anticipated — it's worse than
a wash on the disease metric:

- **`reach32t`'s dies-ahead is 22.5%** — worse than plain `reach32`'s 16.7%,
  worse than `base32`'s own 13.3% baseline, and the McNemar direction
  confirms it: 6 seeds rescued, 14 HARMED (vs `reach32`'s milder 1
  rescued/3 harmed). Pills delta is a WASH (CI includes 0), so the harm
  shows up specifically in the tail (bad-ends, dies-ahead), not the mean.
- **`reachfull2t`'s dies-ahead is 12.5%** — worse than `reachfull2`'s 9.2%,
  essentially erasing more than half of the fix's own dies-ahead
  improvement (13.3%→9.2% becomes 13.3%→12.5% once the time filter is
  stacked on top). Bad-ends also regress (18→20). The pills delta looks
  slightly BETTER (−32.14 vs −29.44) and McNemar is borderline (p=0.058,
  not significant at .05) — a case where the MEAN metric and the DISEASE
  metric disagree in direction, and per this program's own standing rule
  (`REACH_ROOT_BURSTY.md`, task #17-unified's own framing), the disease
  metric (dies-ahead, bad-ends) is the one that answers "does this help the
  AI stop dying," not the mean pill count among games it already won.

`time_frac`/`fallback_time_frac` diagnostics (mean over games, `*t` arms
only, this iteration's new instrumentation in `reach_root_ab.py::play`):

| arm | time_frac (within_budget / reach, mean/game) | fallback_time_frac (mean/game) |
|---|---|---|
| reach32t | 0.982 | 0.000 |
| reachfull2t | 0.989 | 0.000 |

`time_frac` is close to 1.0 (the filter removes only ~1.1-1.8% of the
already-reachable candidate set on average), and `fallback_time_frac` is
effectively 0 (decisions where the reachable set is nonempty but ZERO
candidates clear the budget — the 3-tier fallback's middle tier — are rare
enough to round to 0.000 at 3 decimals). The filter is not aggressive in
volume; it is a RARE, surgical removal that nonetheless measurably raises
dies-ahead when it happens to land on the argmax at a moment that matters —
consistent with a high-stakes, low-frequency decision problem (near-death
boards where one wrong placement can be the difference between clearing and
topping out).

These numbers show the filter DOES bind under bursty pressure — unlike the
clean-board gate (`REACH_ROOT_CLEAN2.md`, 0/4174 decisions, every height
bucket) and the M3 case study (`REACH_ROOT_M3CASE2.md`, 0/6 commits), where
it never binds at all. Bursty's injected garbage produces board shapes with
shallower resting rows (near the top of a tall stack) than either of those
samples, exactly the narrow window the corrected DIST_TABLE constants leave
open (row < ~3 from spawn).

## 4. Why this is plausible, not just noise: a mechanism note

`choose_reach32t`'s 3-tier fallback means that whenever the time filter
removes the argmax `reach32` would have picked but leaves at least one OTHER
reachable candidate within budget, it substitutes a LOWER-VALUE placement
for a HIGHER-VALUE one it judges (via the DIST_TABLE approximation) as
untimely — a deliberate trade of eval value for a modeled executability
guarantee. That trade is only worth making if the approximation is right.
The approximation here (`_within_time_budget`: fall height = the
candidate's own resting row, spawn row = 0, ignoring column-specific
obstacles along the path and any lateral progress that could happen before
or during the fall) is coarser than DRDISTGATE's own live mechanism, which
recomputes every hook from the ACTUAL current position and only ever
CLAMPS the steering target closer to spawn — it never rejects the search's
best answer outright in favor of a different, lower-valued one. This
iteration's root-candidate PRE-FILTER is a different mechanism than
DISTGATE's live steering clamp, testing a different (harder) hypothesis:
"can a spawn-time-only estimate safely veto candidates before search even
sees them." The bursty result here is evidence against that specific
mechanism (a hard candidate veto), not necessarily against DISTGATE's own
live-clamp design, which degrades more gracefully by construction and has
never been evaluated by this task (`CART_FIX_REPORT.md` §7.5 already flags
DISTGATE itself as "not silicon-ready without an A/B pass" for unrelated
reasons — this finding doesn't add new evidence about that mechanism either
way).

## 5. Verdict on the extension

**The time-budget extension, implemented as a root-candidate filter, does
NOT cut dies-ahead below `reachfull2`'s 9.2%.** It does the opposite: stacked
on `reach32` it makes dies-ahead worse (16.7%→22.5%), and stacked on
`reachfull2` it gives back more than half the fix's own gain (9.2%→12.5%).
Per the task's own honesty-rule framing, this localizes the ENTIRE pressure
win in `reachfull2`'s tuck expansion — the time filter is not merely
redundant with it, it actively fights it under bursty pressure. This demotes
the time-budgeted PRE-FILTER (as implemented here) out of the ship
candidate entirely; it does not, by the mechanism argument in §4, constitute
a re-test of DRDISTGATE's own live-clamp design, which remains untested by
any evidence in this program.

## Provenance

- Rig (edited this iteration): `reach_root_ab.py` — added `time_frac`/
  `fallback_time_frac` per-game diagnostics and their means to `compare()`'s
  printed line + returned summary dict. `base32`/`reach32`/`reachfull` code
  paths byte-identical to `REACH_ROOT_BURSTY.md`'s run.
- Modes: `reach_root.py` (`choose_reach32t`, `choose_reachfull2`,
  `choose_reachfull2t` — new this iteration; `choose_base32`/`choose_reach32`/
  `choose_reachfull` unmodified).
- Run commands:
  `reach_root_ab.py --seeds 120 --workers 6 --level 11 --arms reach32t
  reachfull2 reachfull2t --pressure bursty --out results/reach_root_bursty_n120_iter2`
  (headline numbers) and a second run with `--arms reach32t reachfull2t`
  only (`results/reach_root_bursty_n120_iter2_diag`) adding the `time_frac`
  instrumentation — same seeds, reproduces the headline numbers exactly
  (sanity-checked bit-for-bit against the first run) while also capturing
  the diagnostic fields.
- Raw results: `results/reach_root_bursty_n120_iter2_{reach32t,reachfull2,
  reachfull2t}.json`, `results/reach_root_bursty_n120_iter2_diag_
  {reach32t,reachfull2t}.json`.
- Driver logs: `tmp_logs/reach_root_bursty_n120_iter2.log`,
  `tmp_logs/reach_root_bursty_n120_iter2_diag.log`.
