# REACH-ROOT verdict: synthesis of clean, bursty, and M3 death-board gates

**Date:** 2026-08-05 · Synthesizes `REACH_ROOT_CLEAN.md`, `REACH_ROOT_BURSTY.md`,
`REACH_ROOT_M3CASE.md`. Task #17-unified's central question: does spawn-time
BFS reachability (`reach_root.py`'s `reach32`/`reachfull` modes) explain and
fix a material share of bursty-pressure "dies-ahead" deaths, and is it ready
for the tuck-bfs-6502 copro port?

## Verdict: **ITERATE**

Ship neither tier to silicon yet. `reachfull` earns a real, statistically
significant win on the disease metric (bursty dies-ahead/bad-ends), but the
M3 death-board case study exposes a scoped implementation defect —
`reachfull`'s base-candidate branch is unfiltered and silently inherits
`base32`'s physically-unreachable argmax on exactly the high-holed,
near-death board shape the disease numbers are about. `reach32` alone is
refuted as a pressure mitigation and should not ship standalone. Fix the
defect, re-run the bursty gate to confirm the win survives (or grows), and
only then commit the ~1-frame/board copro budget.

## 1. Internal consistency check (adversarial pass)

- **Baselines match.** All three gates run the identical `base32` control
  (bit-exact reproduction of shipped `ab47.py::_choose_base(wt=0, ws=20)`,
  confirmed by each gate's own selftest/sanity check). Bursty's `base32`
  reproduces `BURSTY_V1_RESULTS.md`'s shipped-ws=20 baseline **exactly**
  (32/120 bad-ends, 16/120 dies-ahead, 21/11 topout/stall split) — same env,
  same seeds, same model fit, same injection convention. M3's `base32`
  reproduces `proxy_results.json`'s `shipped_strand20.chosen.val` bit-for-bit
  on all 6 commits. No baseline drift across the three reports.
- **Paired-seed counts consistent.** Clean and bursty both use n=120,
  seeds 0-119, workers=6, same `reach_root_ab.py` rig, same `theta=250`.
  Clean gate's divergence instrumentation (12,183 decisions) is a superset
  view of the same 120 seeds, not a different population. M3 is explicitly a
  6-board case study (real tape commits), not a statistical sample — its
  role is qualitative/mechanistic, and the report never claims otherwise.
- **reachfull's clean-board value (−10.61) vs the −18.05 prior is explained,
  not glossed over.** The clean gate is explicit that these are different
  estimators: the prior (`tuck_v3` mirror rig) is a tuck-fire on/off A/B atop
  the shipped decider; this gate is a single-search root-candidate-set swap
  (`base32` vs `reachfull`, both same decider family). CIs are compatible
  (`[−15.66,−5.80]` vs `[−25.69,−10.63]`, overlapping at `[−15.66,−10.63]`),
  same sign, same order of magnitude — correctly framed as sign/magnitude
  reproduction, not a tightened re-measurement. This is the right level of
  caution and I don't find a hidden discrepancy here.

## 2. What each tier is worth, independently

**Tier: reachable-root (`reach32` / `reachfull`, this evidence).**

- `reach32` (pure legality prune, no new capability): **worth ~zero, trends
  negative.** Clean-board WASH (bit-exact 120/120, 0/12,183 decisions
  diverged — the filter almost never binds on boards the AI actually
  reaches). Bursty-pressure REFUTED (pills WASH, bad-ends 32→34, dies-ahead
  moved the *wrong* way 13.3%→16.7%, McNemar p=0.625, only 4/120 seeds
  moved at all). M3 case makes the mechanism concrete: on 3/6 real death
  boards, `reach32`'s own "reachable" pick still needs 64-96 DAS hooks
  (2-3 column edges), exceeding the ~40-hook window PAIR_LATCH_AUDIT.md
  documents as executable — "reachable" is not "executable in the observed
  lock window." `reach32` also *loses* the human-preferred `{0,6,7}` column
  family on 4/6 M3 boards (vs base32/reachfull's 5/6), trading value and
  human-recognizable placement for a reachability guarantee that doesn't
  itself guarantee DAS-timing feasibility. **Do not ship `reach32` alone.**

- `reachfull` (adds genuine BFS-reachable tuck-class candidates, θ=250-gated):
  **real aggregate value, with a confirmed implementation gap.** Bursty:
  bad-ends 32→18, dies-ahead 13.3%→9.2%, clear 73.3%→85.0%, pills −29.87
  [−44.84,−14.42] REAL, McNemar p=0.0201 on 32/120 (26.7%) moved seeds —
  this is the one arm that actually moves the disease numbers, and the
  mechanism is confirmed as genuine tuck capability (4.17 tuck fires/game,
  118/120 games fired ≥1), not the legality subtraction (`reach32`'s
  tuck_fires/g = 0.00 by construction, and it's null). Clean-board cost
  reproduces the known tuck-value prior in sign and magnitude, as expected.
  **But** the M3 case study — the one place this evidence set looks at
  actual high-holed, near-death board shapes rather than aggregate seed
  averages — shows `reachfull` **never diverged from `base32` on any of the
  6 commits**, because its base-candidate loop is architecturally identical
  to `base32`'s (unfiltered), and on these boards the tuck candidates
  (2-4 legal per commit) never clear the θ=250 margin. Concretely,
  `reachfull` silently inherits `base32`'s *physically unreachable* argmax
  on the same 4/6 commits as `base32`. This means reach-filtering was never
  applied to the branch of `reachfull` that most needs it — the base
  32-candidate loop — only to the added tuck candidates. The bursty gate's
  aggregate 26.7%-of-seeds win is real, but it is coming from decisions
  where a legal, in-margin tuck happens to be available; on the specific
  board shape this program cares about most (deep, holed, near-death,
  base32-unreachable-argmax boards), the current `reachfull` implementation
  provides **zero additional reachability guarantee** over `base32`. This is
  a scoped, fixable defect (apply `reach32`-style filtering to `reachfull`'s
  base branch, not just its tuck branch) — not a refutation of the tuck
  capability itself.

**Tier: DRDISTGATE (commit clamp / distance-aware fall-budget gate) —
not directly tested by this evidence, but indirectly supported as
necessary.** None of the three gates exercise DRDISTGATE; it's explicitly
out of scope (late-arrival/mid-fall tier, owned elsewhere). But the M3 case
gives indirect evidence for *why* it's needed on top of reachable-root: even
`reach32`'s own reachable picks blow the ~40-hook DAS window on 3/6 boards.
Reachability (a spawn-time BFS fact) and DAS-executability (a
remaining-fall-budget fact) are different claims, and neither `reach32` nor
`reachfull` carries the fall-budget term — PAIR_LATCH_AUDIT.md §6.2/§7
already named this as "the real fix." This evidence set does not validate
DRDISTGATE's own implementation (untested here) but does strengthen the
case that reachable-root alone, even if the base-branch defect above is
fixed, is an incomplete answer — a placement can be BFS-reachable and still
arrive too late to matter.

## 3. Silicon integration cost, realistically

tuck-bfs-6502 branch budget: ~1 frame/board on the copro, capacity 64,
memory map pending sign-off. That is a real, non-trivial spend to port the
BFS onto hardware — and the value case for that spend currently rests on
`reachfull`'s bursty win (real, p=0.02, 26.7% of seeds moved) while the one
board-shape-level look this program has taken (M3) shows that exact
capability collapsing to `base32`-identical, unreachability-preserving
behavior on the highest-stakes board family. Porting the current
`reachfull` implementation to silicon as-is would spend the ~1 frame/board
+ capacity-64 + memory-map budget on a mechanism that, per the one
mechanistic case study available, does not close the gap on the boards that
look most like real dies-ahead deaths. The fix (filter the base branch too)
is cheap to test in software before committing to the port — do that first.

## 4. Recommendation detail

1. Patch `reach_root.py`'s `choose_reachfull` so the 32 straight-drop base
   candidates are reachability-filtered exactly as `reach32` does (not just
   the added tuck candidates), producing a `reachfull2` (or equivalent)
   that is `reach32`'s filtered-32 ∪ BFS tuck-reachable set.
2. Re-run the bursty gate (n=120, same seeds) for this patched arm. Confirm
   (a) the bad-ends/dies-ahead win is preserved or improved, and (b) it no
   longer inherits `base32`'s unreachable argmax on the M3-style board
   shape — re-run the 6-commit M3 case against the patched arm as the
   acceptance check (target: diverges from `base32` on the 4 commits where
   `base32` is unreachable, not 0/6).
3. Only after that passes, treat `reachfull`(-patched) as the candidate for
   the tuck-bfs-6502 copro port and spend the capacity-64/memory-map budget.
4. Do not carry `reach32` forward as a standalone shippable mode — its
   value is fully subsumed by (and its standalone downside avoided by) the
   patched `reachfull`.

## Files

- `REACH_ROOT_CLEAN.md`, `REACH_ROOT_BURSTY.md`, `REACH_ROOT_M3CASE.md` (this
  verdict's inputs, all in this directory)
- `reach_root.py` (modes under test, unmodified by this task)
- `reach_root_ab.py` (A/B runner, owned by this task)
- `tmp_logs/m3case.py`, `tmp_logs/m3case_raw.json` (M3 case raw data)

## ITERATION 2

**Date:** 2026-08-05 · Task #60 iteration pass, executing this verdict's own
§4 prescription (the base-branch reachability fix) plus a time-budgeted
extension. Inputs: `REACH_ROOT_M3CASE2.md`, `REACH_ROOT_BURSTY2.md`,
`REACH_ROOT_CLEAN2.md` (this iteration's 3 new gate reports, parallel to the
originals). `reach_root.py`'s `base32`/`reach32`/`reachfull` are
byte-for-byte unmodified; three new modes were added: `reachfull2` (the fix),
`reach32t` and `reachfull2t` (the time-budget extension).

### 1. THE PRESCRIBED FIX: CONFIRMED

`choose_reachfull2` reachability-filters the base-candidate branch exactly
like `reach32`, closing the gap this verdict's §2 described. Acceptance
check (§4.2 of this verdict, originally): on the M3 case study's 6 real
death-board commits, base32's own argmax is BFS-unreachable on 4/6 (1, 2, 4,
6, unchanged from the original finding). `reachfull2` now diverges from
`base32` on **4/4** of those boards (was 0/4 for the pre-fix `reachfull`) and
never picks an unreachable base placement on any of the 6 — confirmed both
by the M3 re-run (`REACH_ROOT_M3CASE2.md` §1-2) and by a new module-level
defect test in `reach_root.py` (`_selftest_reachfull2_never_unreachable_base`,
a fresh 20/20-case forced-unreachable-argmax sweep on random high/holed
boards, all clean). The bursty-gate aggregate barely moves though
(`REACH_ROOT_BURSTY2.md` §2: dies-ahead 9.2% both pre- and post-fix, pills
−29.87 vs −29.44) — the defect is real and confirmed on the specific board
shape M3 targets, but that combination (unreachable argmax AND no tuck
beating theta AND that argmax actually winning) is rare in the general n=120
bursty population. **This is a correctness fix, not an aggregate-metric
fix**, and both framings are true at once: ship the fix because it's
correct, don't expect it alone to move the n=120 topline further than the
pre-fix `reachfull` already did.

### 2. THE TIME-BUDGET EXTENSION: NEGATIVE (not merely a wash)

The extension was implemented exactly as prescribed — `reach32t` /
`reachfull2t` filter their base-candidate branch by `hooks_needed(edges to
target column) <= hooks_available(DIST_TABLE budget from the candidate's own
resting row)`, using DRDISTGATE's own arithmetic. **One correction made
in-flight, flagged rather than silently applied:** the task's own prescribed
constants (32 hooks/DAS-edge, 26 hooks/gravity-row, from
`CART_FIX_REPORT.md` section 7's prose) are STALE. The driver source file
that section describes (`patch_cartridge_copro.py`) was silicon-remeasured
the SAME DAY (2026-08-05, task #49 follow-on) with corrected values —
`DIST_DASEDGE=12`, `DIST_GRAVROW=30` — and its own comment explicitly marks
the 32/26 pair as an unmeasured guess inherited from a since-corrected
frame-rate assumption. This iteration uses the live, current constants
(cross-checked byte-for-byte against the actual driver artifact,
`_selftest_dist_table_matches_driver`, new selftest #5), not the stale pair.
Using the stale pair would have made the filter bind far more often (DAS
budgeted as 2.7x slower than measured) — the negative result below is
therefore, if anything, an UNDER-estimate of how often naive stale-constant
filtering would have hurt.

Three independent measurements agree on the mechanism, and disagree sharply
by pressure regime:

- **Clean L11 play (`REACH_ROOT_CLEAN2.md`):** the filter is a COMPLETE
  no-op. 0/4174 decisions diverge from `reach32`'s own picks, at every board
  height including 13-16 (the tallest bucket sampled). `reachfull2t` is
  byte-identical to `reachfull2` (same −11.15 [−19.03,−3.23] pills delta).
- **M3 real death-board case study (`REACH_ROOT_M3CASE2.md`):** also a
  complete no-op — 0/6 commits, `n_within_budget == n_reach` on every one,
  even though these are real near-topout, critically-stacked boards. **Team-
  lead follow-on check (§5 of that report):** is this zero-divergence an
  artifact of assuming steering starts at spawn, and would a "late decision
  arrival" (search-latency) penalty flip it, localizing the mechanism there
  instead of in movement physics? Swept a `late_start_hooks` penalty 0-84 —
  **no flip at the requested 20-hook probe, or anywhere up to 40.** 3 of 6
  boards do eventually flip, but only past ~50-70 hooks (25-35 frames,
  ~0.4-0.6s) of assumed decision latency, well beyond the probe point and
  not independently established by any search-latency measurement in this
  program. The "late decision arrival" hypothesis is refuted at the
  requested probe point; whether it holds at a much larger, unverified
  latency figure is an open question this check narrows but does not close.
- **Bursty-pressure gate, n=120 (`REACH_ROOT_BURSTY2.md`):** here the filter
  DOES bind (diagnostic: mean `time_frac` — the share of BFS-reachable
  candidates that also clear the time budget — is 0.982 for `reach32t`
  [removes ~1.8% of the reachable set on average] and 0.989 [~1.1%] for
  `reachfull2t`), and where it binds, it HURTS: `reach32t`'s dies-ahead
  is 22.5% (worse than plain `reach32`'s already-null 16.7%, and worse than
  `base32`'s own 13.3% baseline); `reachfull2t`'s dies-ahead is 12.5%
  (giving back more than half of the fix's own gain over baseline, 13.3%→
  9.2%→12.5%). McNemar direction confirms harm, not just mean-CI overlap
  (`reach32t`: 6 rescued / 14 harmed).

**Does time-budgeted filtering cut dies-ahead below reachfull2's 9.2%? NO —
it raises it to 12.5% when stacked on the fix, and to 22.5% when stacked on
the pure-legality arm.** This is a stronger and more specific finding than
"a wash localizing the win in the tuck expansion" (the task's own anticipated
fallback framing) — the filter is measurably harmful under exactly the
pressure regime this whole program cares about, while being fully inert
everywhere else this program has looked (clean boards, real captured death
boards). The likely mechanism (`REACH_ROOT_BURSTY2.md` §4): the filter is a
hard PRE-FILTER that can substitute a lower-value candidate for the true
argmax whenever its coarse, path-independent fall-height estimate rejects
the argmax's column — a fundamentally different (and more aggressive)
mechanism than DRDISTGATE's own live steering CLAMP, which recomputes every
hook from the actual position and only ever narrows toward the search's
answer, never vetoes it outright for a different one. This finding is
therefore evidence against "veto candidates at spawn time from a static
fall-height estimate," not evidence against DRDISTGATE's own live-clamp
design, which no evidence in this program has tested either way
(`CART_FIX_REPORT.md` §7.5's own "not silicon-ready" caveat about DISTGATE
stands, unrelated to this finding).

### 3. Ship candidate

**`reachfull2` is the ship candidate for the tuck-bfs-6502 copro port,
`reachfull2t` is NOT.** `reachfull2` carries the full pre-fix `reachfull`
bursty win (dies-ahead 13.3%→9.2%, bad-ends 32→18, pills −29.44 REAL,
McNemar p=0.016) plus the confirmed correctness fix (never proposes an
unreachable placement, verified on real death boards and by a dedicated
defect test), with zero measured cost anywhere the fix doesn't apply (clean
boards, byte-identical to the pre-fix `reachfull` there). The time-budget
extension should NOT be carried into the port: it is inert on 2 of 3
evidence sources and actively harmful on the third (the one that matters
most, bursty pressure), for a real and explained mechanism, not sampling
noise. Do not spend the tuck-bfs-6502 copro budget on the time filter.

### 4. Silicon integration cost, updated

The prior §3's ~1 frame/board budget estimate is unaffected in scope — this
iteration adds no new copro-side mechanism (the time filter, the only
candidate for new hardware cost, is being rejected, not shipped). `reachfull2`
is a pure software fix to the existing `reachfull` candidate-enumeration
logic (a reachability filter on the base branch, reusing the SAME
`tuck_enum`/BFS machinery `reach32` already ships) — no new RAM, no new
frame budget beyond what the original `reachfull` port already priced.

### Files (this iteration)

- `REACH_ROOT_M3CASE2.md`, `REACH_ROOT_BURSTY2.md`, `REACH_ROOT_CLEAN2.md`
  (this iteration's 3 gate reports)
- `reach_root.py` (`choose_reachfull2`, `choose_reach32t`,
  `choose_reachfull2t`, `_scored_base_candidates`, `_tuck_branch_pick`,
  `DIST_DASEDGE`/`DIST_GRAVROW`/`_within_time_budget` — all new this
  iteration; `choose_base32`/`choose_reach32`/`choose_reachfull` unmodified.
  New selftests: `_selftest_reachfull2_eq_reachfull_open_board`,
  `_selftest_reachfull2_never_unreachable_base` (the defect test),
  `_selftest_dist_table_matches_driver` — all 5 selftests pass.)
- `reach_root_ab.py` (added `time_frac`/`fallback_time_frac` diagnostics;
  `base32`/`reach32`/`reachfull` paths untouched)
- `tmp_logs/m3case2.py`, `tmp_logs/m3case2_raw.json` (new M3 runner/raw data)
- `tmp_logs/m3case_sensitivity.py`, `tmp_logs/m3case_sensitivity_raw.json`
  (team-lead follow-on: late-decision-arrival sweep, read-only, does not
  modify `reach_root.py`'s shipped choosers)
- `reach_divergence2.py`, `results/reach_divergence2_n40.json` (new
  divergence-by-height instrumentation for `reach32t`)
- `results/reach_root_bursty_n120_iter2_*.json`,
  `results/reach_root_clean_n40_iter2_*.json` (raw A/B results)

## ITERATION 3 — EXECUTABLE SUBSET

**Date:** 2026-08-05 · Team-lead follow-on, the final gate before `reachfull2`
goes to the silicon manifest. The tuck-bfs-6502 wiring landed the same night
with a hard finding: the CANDLIST execution vocabulary only accepts a
`~11%` MEDIAN OF `tuck_scan_v3`'s own broader candidate space (median 2/36
raw candidates/board; single-adjacent-column descriptors) — `reachfull2`'s
9.2% bursty dies-ahead was measured over the FULL BFS-reachable tuck set,
but silicon can only EXECUTE the translatable subset. New arm **`reachexec`**
= `reachfull2` with tuck-class candidates additionally filtered by
`translatable.py`'s `TL.executable()` (wraps `dr-mario-canonical-wt/tests/
translate_ref.py`'s already-validated CANDLIST derivation, 0/1846
disagreements vs the real 6502 chain — not re-validated here, only wired
in). Implementation: `reach_root.py::choose_reachexec` (new), `_tuck_branch_
pick` gained an optional `extra_filter` parameter (default `None`, so
`choose_reachfull2`/`choose_reachfull2t` are byte-for-byte unaffected) that
`reachexec` uses to compose `is_tuck and reachable and TL.executable(...)`.
New wiring-sanity selftest #6: every tuck `reachexec` ever picks is
independently re-confirmed executable by a fresh `TL.executable()` call
(0 mismatches over 60 boards) — the predicate's own correctness is upstream
and out of scope here; this only checks the plumbing didn't invert or
misdirect it. Note on the acceptance-rate sanity check inside that selftest:
it measures ~34% (88/258) against `TE.enumerate(..., mode="free")`'s
`is_tuck and reachable` candidate set specifically (the same denominator
`reachfull2`'s own tuck branch already uses, averaging ~3-4 candidates/board
per `tuck_enum.py`'s own corpus stats) — a DIFFERENT, smaller-count
denominator than `tuck_scan_v3`'s own "36 raw candidates/board" figure, so
the two percentages are not directly comparable; flagged as a counting-
convention difference, not a contradiction, since `TL.executable()` itself
is unmodified and independently verified against its own reference on each
call.

### 1. Bursty gate, n=120 (the decisive number)

Three-way paired run (`run_reachexec_bursty.py`, same 120 seeds across all
three arms so every comparison below is truly paired, not re-derived from
separate runs):

| comparison | pills Δ | 95% CI | verdict | clear rate | bad-ends | dies-ahead | McNemar (rescued/harmed, p) | tuck_fires/g |
|---|---|---|---|---|---|---|---|---|
| **reachfull2 vs base32** | −29.44 | [−44.58,−14.01] | REAL | 73.3%→85.0% | 32→18 | 13.3%→**9.2%** | 22/8, p=0.016 | 4.17 |
| **reachexec vs base32** | −14.64 | [−27.29,−2.23] | REAL | 73.3%→75.0% | 32→30 | 13.3%→**11.7%** | 15/13, **p=0.851** | 1.77 |
| **reachexec vs reachfull2** | +12.54 | [−1.99,+27.10] | WASH (barely) | 85.0%→75.0% | 18→30 | 9.2%→11.7% | 8/20, **p=0.036** | — |

**How much of reachfull2's win survives the executable subset, by metric:**

| metric | survival fraction |
|---|---|
| pills (mean, both-won pairs) | 49.7% |
| dies-ahead percentage-point reduction | 39.0% |
| bad-ends rescue count | **14.3%** |
| clear-rate gain | **14.5%** |

The two metrics this program treats as the disease definition (bad-ends,
McNemar rescued/harmed — the same convention `BURSTY_V1_RESULTS.md` and
`REACH_ROOT_BURSTY.md` both use) retain only ~14% of reachfull2's win, and
`reachexec` vs `base32` on that metric is statistically indistinguishable
from doing nothing at all (p=0.851, 15 rescued vs 13 harmed — a coin flip).
The DIRECT paired comparison against reachfull2 is the most decisive number
here: restricting to the executable subset causes a STATISTICALLY
SIGNIFICANT regression (p=0.036, 8 rescued vs 20 harmed) — not sampling
noise, a real cost. The weaker mean-pills metric retains about half the
value and stays nominally REAL (CI excludes 0), so the picture isn't a total
zero, but it is not the headline win reachfull2 advertised.

### 2. M3 case study: does reachexec still diverge from base32 on the 4 unreachable-argmax boards?

**Yes — 4/4, matching `reachfull2` exactly.** On all 6 M3 boards,
`reachexec`'s pick is IDENTICAL to `reachfull2`'s (`col4V`/`col3H`/`col3H`/
`col1V`/`col0V`/`col0V` on commits 1-6 respectively) — every commit resolves
to `kind=base`, meaning on this specific 6-board set no tuck candidate
survives BOTH the reachability filter AND `TL.executable()` AND the
theta=250 margin over the base branch. The base-branch fix (the actual
defect this program cares about most, per `REACH_ROOT_M3CASE2.md`) is
completely unaffected by the executable-subset question — it's a base-
branch phenomenon, `reachexec` only touches the tuck branch.

### 3. Clean L11 spot check, n=40: how much of the tuck value survives?

| arm | pills Δ vs base32 | 95% CI | verdict | tuck_fires/g |
|---|---|---|---|---|
| reachfull2 | −11.15 | [−19.03,−3.23] | REAL | 3.73 |
| reachexec | −6.23 | [−12.54,+0.03] | WASH (barely — upper bound +0.03) | 1.57 |

Paired directly (same 40 seeds, reachfull2 as the control instead of
base32): **reachexec vs reachfull2 = +4.92 [−3.90,+14.46] pills, WASH** —
not statistically distinguishable from reachfull2 at n=40, but the point
estimate says exec gives back roughly half the clean-board tuck value
(−6.23 of −11.15 ≈ 56% survives vs base32) and tuck-fire rate drops by more
than half (3.73 → 1.57/game), consistent with the ~34% (this wiring's
measured rate, see note above) tuck-candidate acceptance rate.

### 4. Ship call

**COLLAPSES, on the metric that matters for a pressure-death mitigation —
say it plainly, per the pre-registered guide.** `reachfull2`'s headline
result (13.3%→9.2% dies-ahead, bad-ends 32→18, McNemar p=0.016) was measured
over the full BFS-reachable tuck set, which the real firmware cannot
execute. Restricted to what `translatable.py`'s validated CANDLIST predicate
says silicon can actually play (`reachexec`), the bad-ends/McNemar disease
metric — this program's own primary metric, not the mean-pills side metric —
is statistically INDISTINGUISHABLE from doing nothing at all (`reachexec` vs
`base32`, p=0.851), and the DIRECT paired comparison against `reachfull2`
shows a STATISTICALLY SIGNIFICANT regression (p=0.036) from restricting to
the executable subset. This is not a modest haircut — on bad-ends/clear-rate
specifically only ~14% of the win survives. The single-adjacent-column
CANDLIST vocabulary was mostly gating out the deep candidates that did the
actual disease-metric work, exactly the "COLLAPSES" branch of the
pre-registered interpretation guide: **the richer-descriptor work (extending
CANDLIST beyond a single adjacent-column approach/trigger pair) is now the
REAL cost of the pressure fix, not an optional follow-on.**

**Practical recommendation, not just a verdict label:**
1. **Do not present `reachfull2`'s 9.2% dies-ahead figure as the silicon
   result anywhere** — it's a software-oracle upper bound the current
   CANDLIST vocabulary cannot deliver. That number belongs to the
   Iteration-2 record as the CEILING this vocabulary is priced against, not
   a shipped result.
2. **Ship `reachexec`, not `reachfull2`, if the tuck-bfs-6502 port ships at
   all in its current vocabulary.** `reachexec` is the only arm whose
   candidate set the driver can actually execute, and it does carry a real
   (if much smaller) improvement over `base32` on mean pills (−14.64 REAL,
   CI excludes 0) with a favorable-but-not-significant dies-ahead trend
   (13.3%→11.7%) and zero measured downside anywhere tested. There is no
   evidence it's worse than shipping nothing; there is decisive evidence
   it's worse than the number that was about to justify the copro budget.
3. **Re-scope the ask before spending more silicon budget on this
   mechanism.** The tuck-bfs-6502 capacity-64/memory-map spend (§3, prior
   iteration) was justified by `reachfull2`'s aggregate win; that win is now
   known not to transfer to the executable vocabulary. Before committing
   further hardware budget to ship `reachexec` as the pressure-death answer,
   price the richer-descriptor CANDLIST extension (multi-switch or
   multi-trigger-row descriptors) against how much of the missing 86% of the
   bad-ends win it would recover — that costing is the real open question
   this iteration surfaces, not done here.

### Files (this iteration)

- `reach_root.py` (`choose_reachexec`, `_tuck_branch_pick`'s new
  `extra_filter` param — additive, default `None`, `choose_reachfull2`/
  `choose_reachfull2t` unaffected; new selftest #6
  `_selftest_reachexec_wiring`)
- `translatable.py` (team-lead's file, unmodified — wrapped, not
  re-derived; wraps `dr-mario-canonical-wt/tests/translate_ref.py`)
- `run_reachexec_bursty.py` (new; reuses `reach_root_ab.run_arm`/`compare`
  directly for a 3-way paired base32/reachfull2/reachexec bursty run so the
  vs-base32 AND vs-reachfull2 McNemar comparisons share one set of games)
- `tmp_logs/m3case2.py` (MODES-driven, automatically picked up `reachexec`;
  its acceptance-check loop extended to include it)
- `results/reachexec_bursty_n120.json`,
  `results/reach_root_clean_n40_iter3_{reachfull2,reachexec}.json`

## ITERATION 4 — TIER KNEE

**Date:** 2026-08-05 · Task #67. The tuck-bfs agent's `translatable.tier_of(col,
candidate) -> int` landed the same night (5 tiers, `translatable.MAX_TIER=5`,
independently validated 0/1490 disagreements / 0 unreachable leaks on their
own 200-board corpus). Applied the documented one-line change
(`run_tier_sweep.py`: `TIER_SWEEP = range(1, translatable.MAX_TIER + 1)`,
`tier_fn=translatable.tier_of`) and re-ran the real n=120 bursty sweep, all 7
arms (base32, the reachfull2 oracle, tier≤1..5) paired on the same seeds.

### Headline: the knee is TIER 3, and it's not a close call

Tier 3 recovers **100% of the oracle's bad-ends rescue** and is
**bit-for-bit indistinguishable from `reachfull2`** on this n=120 sample (0
seeds moved, pills delta exactly `+0.00 [+0.00,+0.00]`). Tiers 4 and 5 add
**zero additional value** — every number is identical to tier 3's, digit for
digit. This independently confirms, on a THIRD corpus, `translatable.py`'s
own honest caveat that tiers 4/5 are unexercised on its two test corpora
(200-board real-L11, 110-candidate synthetic overflow) — the bursty-pressure
gameplay corpus this program cares about most shows the identical pattern.

### Bad-ends-survival-vs-tier curve

`base32` bad-ends = 32, `reachfull2` (oracle) bad-ends = 18, oracle rescue = 14.

| max_tier | bad_ends | rescued | survival of oracle rescue |
|---|---|---|---|
| 1 | 30 | 2 | 14.3% |
| **2** | **20** | **12** | **85.7%** |
| **3** | **18** | **14** | **100.0%** |
| 4 | 18 | 14 | 100.0% (identical to tier 3) |
| 5 | 18 | 14 | 100.0% (identical to tier 3) |

### Full per-tier comparison, n=120 bursty, paired on identical seeds

| max_tier | pills Δ vs base32 | verdict | bad-ends | dies-ahead | McNemar vs base32 (rescued/harmed, p) | McNemar vs oracle (rescued/harmed, p) | tuck_fires/g |
|---|---|---|---|---|---|---|---|
| 1 | −14.64 [−27.29,−2.23] | REAL | 32→30 | 13.3%→11.7% | 15/13, p=0.851 | 8/20, p=0.036 | 1.77 |
| 2 | −22.00 [−35.35,−8.59] | REAL | 32→20 | 13.3%→10.8% | 22/10, p=0.050 | 8/10, p=0.815 | 3.01 |
| **3** | **−29.44 [−44.58,−14.01]** | **REAL** | **32→18** | **13.3%→9.2%** | **22/8, p=0.016** | **0/0, p=nan (0 moved)** | **4.17** |
| 4 | −29.44 [−44.58,−14.01] | REAL | 32→18 | 13.3%→9.2% | 22/8, p=0.016 | 0/0, p=nan (0 moved) | 4.17 |
| 5 | −29.44 [−44.58,−14.01] | REAL | 32→18 | 13.3%→9.2% | 22/8, p=0.016 | 0/0, p=nan (0 moved) | 4.17 |

Reading the McNemar-vs-oracle column is the cleanest way to see the knee:
tier 1 is significantly WORSE than the oracle (p=0.036, harmed>rescued —
this is `reachexec` itself, already characterized as collapsed in Iteration
3); tier 2 is statistically indistinguishable from the oracle but with real
residual daylight (bad-ends 20 vs 18, 12/120 seeds discordant); tier 3
reaches EXACT equivalence (0 discordant pairs) and stays there through tier
5.

### Cost ladder (from `translatable.py`'s own tier-ladder documentation)

| tier | mechanism | firmware cost |
|---|---|---|
| 1 | single adjacent-column approach, bounded trigger row (today's shipped vocabulary) | $0 (already shipped) |
| 2 | single adjacent-column approach, UNBOUNDED trigger row (BFS-visited-verified) | +40-80B code, no new RAM |
| **3** | **unrestricted approach column, ≤1 lateral direction change** | **+150-250B code, +~128B RAM** |
| 4 | bounded-length path playback (≤`TIER4_MAX_STEER`=12 non-Down moves), needs BFS parent pointers | +512B new RAM (>2x current ~448B footprint) + ~100-150B replay code; flagged by its own author as needing a dedicated capacity/RAM audit |
| 5 (MAX) | unbounded playback = full BFS-reachable set | NOT a firmware byte cost (bitplane already computed) — an OPEN driver/input-model feasibility question (can the real frame pipeline execute an arbitrary, possibly-backtracking move sequence in time?), not priced here |

### Recommendation: ship TIER 3

Tier 3 is the unambiguous knee: it is the cheapest tier that captures the
**full** oracle recovery (100% of the bad-ends rescue, exact statistical
equivalence to `reachfull2`, McNemar p=0.016 significant vs `base32`), and
its cost (+150-250B code, +~128B RAM) is modest and only slightly above
tier 2's. Tiers 4 and 5 should NOT be built next: tier 4's cost is
substantial (more than doubling the current tuck-BFS RAM footprint) and
tier 5's cost is an unresolved driver-feasibility question — and BOTH add
measured **zero** additional recovery over tier 3, corroborated across three
independent corpora (the tuck-bfs agent's own 200-board and 110-candidate
corpora, plus this program's n=120 bursty-pressure gameplay corpus). If a
smaller code footprint is later needed, tier 2 is the fallback — cheapest
non-zero step (+40-80B), captures 85.7% of the value, borderline significant
(p=0.050) — but should not be the default target given tier 3 costs barely
more and closes the gap completely.

**Practical translation for the tuck-bfs-6502 port:** build tier 3's
motion vocabulary (unrestricted approach column, ≤1 direction change) as the
CANDLIST target, not today's shipped tier-1-only vocabulary. This is the
richer-descriptor work Iteration 3 identified as the real cost of realizing
`reachfull2`'s advertised pressure-death win — and this sweep prices it
precisely: a genuinely small, well-scoped increment (+150-250B/+128B RAM),
not the larger, open-ended tier-4/5 investment that isn't justified by any
evidence gathered so far.

### A harness bug caught and fixed mid-report (flagged, not hidden)

`run_tier_sweep.py`'s own endpoint-validation section (built for the earlier
stub run) hardcoded the "top of sweep" comparison target as
`RR.STUB_MAX_TIER` (=2, the two-tier stub's own upper bound). Under the real
5-tier ladder this silently compared tier≤2 (a real, narrower tier) against
the `reachfull2` oracle and printed a false `FAIL` (90/120 seeds "differ" —
correctly, since tier 2 legitimately differs from the oracle; the check was
just asking the wrong question). Fixed to derive the top-of-sweep tier from
`max(TIER_SWEEP)` dynamically. The `max_tier=1` vs `reachexec` check was
unaffected by this bug (hardcoded correctly, always index 1) and passed
directly: **0/120 seeds differ**. The corrected tier-5-vs-oracle identity is
not separately re-verified via a fresh row-level diff (the fix landed after
the run completed, and the raw per-seed tier rows were not persisted to
disk, only the aggregate comparison summaries) — but the aggregate evidence
already gathered is about as strong as a row-diff would be: an exact
zero-width pills CI (`+0.00 [+0.00,+0.00]`), zero McNemar-discordant pairs
(0/120), and identical bad-ends/dies-ahead/clear-rate counts. Re-running the
full 7-arm sweep solely to re-derive an already-overwhelming confirmation
was judged not worth the ~15 additional minutes of compute; flagged here so
the gap between "aggregate-confirmed" and "row-diff-confirmed" is visible,
not asserted away.

### Files (this iteration)

- `run_tier_sweep.py` (`TIER_SWEEP` now covers the real 5-tier range,
  `tier_fn=translatable.tier_of` wired into `play()`; endpoint-validation
  section's `RR.STUB_MAX_TIER` bug fixed to `max(TIER_SWEEP)`)
- `results/tier_sweep_bursty_n120_real.json` (this run's summaries + curve;
  contains the pre-fix, false-FAIL validation block from the run that
  produced the headline numbers — the numbers themselves are correct, only
  that one diagnostic sub-section was stale, per the note above)
- `tmp_logs/tier_sweep_bursty_n120_real.log` (full run log)
- `translatable.py` (tuck-bfs agent's file, read not modified: `tier_of`,
  `MAX_TIER`, `TIER4_MAX_STEER`, the tier-ladder cost documentation this
  section's cost table is sourced from)

## ITERATION 5 — V1.1 CITATION NUMBERS

**Date:** 2026-08-05 · `BURSTY_V1_RESULTS.md` section 5 found the bursty
pressure model's original fit (v1) was pool-contaminated: roughly half its
61 volleys were the AI copro's own sending events, not struktured's, which
pulled the fit toward faster/more-reliable attack behavior than an honest
human-only fit supports. v1.1 (struktured-only separated stream, n=28
volleys) is the corrected model. The paired tier CURVE (Iteration 4) is
unaffected — v1 vs v1.1 applies identically to both sides of every paired
arm, so contamination cancels — but the ABSOLUTE numbers any silicon
manifest quotes must come from v1.1.

Reused `run_bursty_v1_1_validity.py`'s `build_v1_1()` — the documented
single source of truth for "what v1.1 is," rebuilt in-process from
`bursty_model.fit_struktured_20260804()`'s live `raw_events` +
`fit_ensemble_source.fit_per_player()`, not a saved-JSON copy.
`bursty_model.py` was NOT imported directly or edited (reactive-mode owns
it). v1.1 fit reproduced exactly: n_volleys=28, n_clears=89,
volley_size_mean=2.679, gap_mean=27.42s — matching `BURSTY_V1_RESULTS.md`
section 5's own table digit-for-digit.

### Cross-check: base32's v1.1 numbers independently reproduce the other
### agent's own v1.1 validity rerun

`base32` here (reach_root.py's bit-exact reproduction of the SHIPPED
strand20 decider, `ab47.py::_choose_base(wt=0, ws=20)`) is the same
configuration `BURSTY_V1_RESULTS.md` section 5 calls "ws=20 (shipped)" in
its own, separately-run `pressure_rig.py`-based validity rerun. The two
numbers agree exactly: **bad-ends 20/120 (16.7%), dies-ahead 9/120 (7.5%)**
in both. Two independent rigs (this task's `reach_root_ab.py` vs
reactive-mode's `pressure_rig.py`), two independent v1.1 reconstructions,
same seeds-from-model convention, same answer — strong evidence the v1.1
model object is being applied correctly here, not a script artifact.

### The three arms, n=120 paired, bursty v1.1

| comparison | pills Δ | 95% CI | verdict | bad-ends | dies-ahead | McNemar (rescued/harmed, p) |
|---|---|---|---|---|---|---|
| tier≤3 vs base32 | −23.49 | [−36.06,−11.87] | REAL | 20→18 | 7.5%→8.3% | 15/13, **p=0.851** |
| tier≤3 vs reachfull2 (oracle) | +0.00 | [+0.00,+0.00] | WASH (exact) | 18→18 | 8.3%→8.3% | 0/0, p=nan (0 moved) |
| reachfull2 vs base32 (context) | −23.49 | [−36.06,−11.87] | REAL | 20→18 | 7.5%→8.3% | 15/13, p=0.851 |

**tier≤3 == reachfull2 oracle: CONFIRMED under v1.1 too** (bad-ends 18 vs
18, dies-ahead 8.3% vs 8.3%, 0/120 McNemar-discordant pairs, pills delta
exactly `+0.00 [+0.00,+0.00]`) — not assumed, directly re-measured. The
`tier≤3 vs base32` and `reachfull2 vs base32` rows being bit-identical is
the expected, consistent consequence of that equivalence, not a
coincidence or a bug.

### The honest finding: significance does NOT survive under v1.1, and the
### manifest citation must say so

**The bad-ends improvement is directionally the same (fewer bad-ends with
tier-3) but is NOT statistically distinguishable from noise at n=120 under
the corrected pressure model.** McNemar p=0.851 (15 rescued, 13 harmed — an
essentially even split), and dies-ahead does not improve at all — it ticks
UP slightly, 7.5%→8.3%. This is a materially different picture from every
earlier iteration's v1-based numbers, where the same base32-vs-oracle/tier
comparison was highly significant (p=0.016, bad-ends 32→18, a 44% relative
cut). The mean-pills metric alone still reads REAL (CI excludes 0,
−23.49), but per this program's own standing convention the DISEASE metric
(bad-ends, McNemar) — not mean pills among already-won games — is the one
that answers "does this help the AI stop dying," and that metric is a wash
here.

**Why:** v1.1's honest `base32` control is already much healthier (16.7%
bad-ends) than v1's contaminated control was (26.7%) — `BURSTY_V1_RESULTS.
md` section 5 already established this (v1.1's shipped-ws=20 arm nearly
halves v1's dies-ahead reading, 13.3%→7.5%). With less disease left to
cure in the honest regime, tier-3's incremental value ON TOP OF the
already-defended shipped decider has less room to show a measurable effect
at n=120 — the mechanism (tier≤3 == full oracle reach, confirmed again
here) is unchanged, but its measured payoff against the honest baseline is
smaller and not yet distinguishable from sampling noise.

**The citation line, delivered with its required caveat, not bare:**

> Under honest human cadence (bursty v1.1), tier-3 cuts bad-ends 20/120
> (16.7%) → 18/120 (15.0%), dies-ahead 7.5% → 8.3%. **This delta is NOT
> statistically significant at n=120 (McNemar p=0.85)** — cite the
> mechanism (tier-3 reaches full-oracle parity, confirmed under both
> pressure models) as established; do not cite this specific bad-ends/
> dies-ahead delta as a proven win. A larger n or a sharper (non-bursty,
> or higher-pressure) gate would be needed to resolve whether the true
> effect is real-but-small or genuinely zero against the honest baseline.

**Recommendation for the silicon manifest:** cite `tier-3 == reachfull2
oracle` (mechanism, confirmed twice, under both pressure models) and the
tier-knee cost table (Iteration 4) as the load-bearing claims — both are
solid. Do NOT cite a specific "tier-3 fixes bursty pressure deaths"
percentage-point claim against the honest v1.1 baseline; the evidence for
that specific claim is currently a wash, not a proof.

### Files (this iteration)

- `run_v1_1_citation.py` (new; reuses `run_bursty_v1_1_validity.py`'s
  `build_v1_1()`, `reach_root_ab.py`'s `run_arm`/`compare`, and
  `run_tier_sweep.py`'s `run_tier_arm` — no protected file touched or
  edited)
- `results/v1_1_citation_n120.json` (summaries + raw per-seed rows for all
  three arms)
- `tmp_logs/v1_1_citation_n120.log` (full run log)
