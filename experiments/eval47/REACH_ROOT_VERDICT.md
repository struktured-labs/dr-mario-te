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
