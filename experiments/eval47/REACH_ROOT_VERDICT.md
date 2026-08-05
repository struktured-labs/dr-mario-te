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
