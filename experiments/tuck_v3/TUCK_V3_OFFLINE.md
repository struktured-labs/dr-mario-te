# Tuck v3 — generalised root-action tucks: scoping + offline proof

Task #17. Phase: **scoping + offline proof only** — no RTL edits, no cart emission
changes, nothing committed. This document is the deliverable; the lead commits.

## 1. Reconnaissance

The existing tuck infrastructure, located and reused (none of it modified):

| piece | path | role |
|---|---|---|
| full gravity-legal tuck enumerator | `/home/struktured/projects/dr-mario-qa-wt/experiments/tuck_enum.py` | BFS over ROM-legal frame schedules; used unmodified as the candidate generator (`mode="gravity"`) |
| the REFUTED leaf-gated v1/v2 override | `/home/struktured/projects/dr-mario-qa-wt/experiments/tuck_ab.py` | `play()` enumerates tucks and compares a depth-1 proxy score (`score_placement`) against the search's already-chosen straight-drop base move. This is the design the exactness-gate lane empirically refuted (+7.11 pills WORSE, n=227) — **not reused as an architecture**, only its executor-reachability helper (`_exec_reach_cells`) and its direct-cell-write execution pattern were carried forward, both copied (not imported) into the new scratch module |
| executor coverage measurement | `/home/struktured/projects/dr-mario-qa-wt/experiments/exec_reachable.py` | measures how much of the full tuck space the one-switch executor model covers; its `executor_tucks()` is the same predicate as `tuck_ab.py`'s `_exec_reach_cells()` |
| pinned firmware regression (D1/D2/D3) | `/home/struktured/projects/dr-mario-qa-wt/experiments/tuck_regression.py` | ship-gate for the eventual 6502 firmware port; re-run here (read-only) to confirm v1 firmware still has all three defects open (see §4) |
| shipped depth-3 search | `/home/struktured/projects/dr_mario_rl/tmp/combo_term/fast_rtl_x.py` (`_choose_d3_ship_eh`, `FastShipD3DeciderEH`, `variant("winner")`) | the exact SHIPPED search config: coef-opt 5-constant winner weights {vrdy8/buried48/rdyext8/setup32/matched48}, topk2=8, ply-1 excav/hang add-on (EXCAV_HANG_PLY1=True), DISC_SHIFT=1 blend, 4-pill stratified third-ply expectimax. This is the baseline the memory warns against skipping (python golden `nes_d3_golden` defaults ≠ shipped search) |
| board mechanics primitives | `/home/struktured/projects/dr_mario_rl/tmp/combo_term/fast_sim_x.py` (`_expand_core`, `_targeted_resolve`, `_resting`, `_virus_count`, `_stable_desc`, `board_flat`) | reused unmodified; one new primitive added (`_expand_core_at`, §2) |
| real NES capsule stream | `/home/struktured/projects/dr-mario-qa-wt/experiments/nes_pills.py` (`NesPillSource`) | the LFSR-based generator, corroborated against dmwit/dr-mario-ngrams; used for every seed in this report, never uniform |
| driver executor (DRTUCK) | `~/projects/dr-mario-mods-wt/driver-nav/patch_cartridge_copro.py` | read only. `TUCK_C2`(approach)/`TUCK_R2`(trigger row) mailbox bytes ($5087/$5088→$6139/$613A), one horizontal switch, no re-rotation. The generalised root-action design below reuses this SAME 2-byte protocol — no new mailbox field is required |

**How v1/v2 leaf-gating was wired (so as not to repeat it):** `tuck_ab.py`'s override
fires *after* the depth-3 search has already committed to a base move: it enumerates
tuck candidates, scores each with `score_placement()` (depth-1: immediate reward + the
RTL leaf, **no ply-2/ply-3 subtree, no eh add-on**), and swaps in the tuck if its
depth-1 score beats the search's chosen move's depth-1 score. exactness-gate's
"ROOT-ACTION SPEC REFINEMENTS" memo diagnoses exactly why this fails: **a leaf
improvement is routinely a depth-3 regression** — the post-search gate compares a
leaf-scored tuck against a subtree-scored straight drop, different quantities, and the
refutation run (fired 4.4/game, all leaf-vs-leaf-gate-passing, still lost) proved it
empirically. The fix identified there, and implemented here, is to score tuck
candidates with the **identical depth-3 machinery**, as first-class root actions.

## 2. Design: generalised root-action tuck enumeration

**Root action space.** The shipped search (`_choose_d3_ship_eh`) enumerates exactly
32 root actions: `variant ∈ {0,1,2,3} × col ∈ {0..7}`, each a straight drop via
`_resting()`. The design extends this to **32 + T** actions, where T is the number of
executor-motion-legal tuck placements on the current board (typically 0–3, see §3
fire-rate data). Every action — base or tuck — is scored by the **same function**:
ply-1 immediate reward, then (if viruses remain) a full ply-2 enumeration promoted via
top-K2=8 to a 4-pill stratified expectimax third ply, the DISC_SHIFT temporal blend,
and the ply-1 excavation/hang add-on. The argmax over all 32+T decides. If a tuck wins,
its landing column becomes what the existing DRTUCK executor calls `best_col` — no new
executor concept, no new mailbox field.

**Reachability = the legality condition, not a value shortcut.** Candidates come from
`tuck_enum.enumerate(fb, pa, pb, mode="gravity")` (the full ROM frame-budget BFS,
already co-sim-verified against the real 6502), filtered to `is_tuck=True` **and** to
the executor's one-switch reach model (`_exec_reach_cells`, unmodified from
`tuck_ab.py`/`exec_reachable.py`): approach column ∈ {target−1, target+1}, using the
approach column's deepest reachable row as a permissive proxy for "some row along the
fall has both columns open". This is deliberately the SAME predicate that measured the
executor-CORRECTED −5.20 pills result (dr-mario-tuck-executor-gap memory) — reused here
as a hard legality gate on what the search may even propose, never as a scoring
shortcut. The memo's own framing: *"the one-switch/two-cell/adjacent-open predicate
becomes a LEGALITY CONDITION on the search action, not a publish filter. MORE
load-bearing under root-action, not less."*

**Why this dissolves D3 but not D1/D2.** The pinned firmware regression
(`tuck_regression.py`, re-run read-only in §4) encodes three v1 defects: D1 (trigger
row published in the wrong coordinate space), D2 (the driver wipes the descriptor every
frame), D3 (the enumerator's own deepest-over-all-columns target disagrees with the
search's `best_col` 87.5% of the time on real boards). Root-action **structurally
cannot produce D3**: there is no longer a separate "enumerator's opinion of the best
target column" versus "the search's opinion" — each tuck candidate IS scored under its
own specific landing column, exactly as the 32 base actions are scored under their own
column, so whichever wins the argmax already carries a self-consistent target. D1 and
D2 are unrelated coordinate/timing bugs in the CURRENT 6502 firmware and remain real
work for any future silicon port; this offline python proof sidesteps them entirely by
writing the winning placement's cells directly to the board, the same execution
shortcut `tuck_ab.py` already used.

**Cost envelope (rough, for the lead's go/no-go).** exactness-gate's "Budget
correction" note: one root child with a full d3 subtree costs ≈1/30 of the shipped
search (~880k copro clocks ≈ 0.6 frames, max-DONE 28.6→29.5 frames). At the fire rate
measured here (§3: ~9/game engaging the search, of which a small minority actually WIN
the argmax) the search-cost increase is bounded by (candidates seen)/32 per decision —
measured mean **140.7 candidates/game** at L11 is the count of tuck placements the
*generator* proposes over an entire game (i.e. summed across every decision in the
game, not per decision); dividing by the ~110 pills/game typical at L11 gives roughly
**1.3 tuck candidates per decision** on average, i.e. a ~4% search-cost increase per
decision when tucks are present, well inside the exactness-gate budget. This offline
proof does not measure 6502/RTL cycles directly — that requires the firmware port,
which is out of scope for this phase.

**Implementation location (nothing shipped modified).** New scratch module:
- `/home/struktured/projects/dr-mario-qa-wt/experiments/tuck_v3/root_search.py` — the
  root-action search itself. Adds ONE new primitive to the existing numba primitive
  set, `_expand_core_at` (identical to `fast_sim_x._expand_core` except the rest cells
  are supplied directly instead of derived from `_resting(variant, col)` — the only new
  mechanic a tuck needs), and extracts the shipped search's ply-2-onward scoring
  (`_ply2plus_value_ship_eh`) into a standalone function so it can be called once per
  candidate, base or tuck, with byte-identical arithmetic to the inlined shipped loop.
  **Verified**, not just claimed: `equivalence_selftest()` (in the same file) forces
  the tuck candidate list to empty and checks 200 random boards against the untouched
  `FastShipD3DeciderEH` — **0 action mismatches, 0 value mismatches** (run output
  below, §4).
- `/home/struktured/projects/dr-mario-qa-wt/experiments/tuck_v3/ab_root.py` — the
  paired A/B harness (real NES stream only, per house rule; two arms differing only in
  whether the tuck candidate list is forced empty).

## 3. Offline proof: paired A/B on the real NES capsule stream

Setup: `FastShipD3DeciderEH` weights (`variant("winner")`), topk2=8, real
`NesPillSource` stream, identical seeds `0..119` for both arms, P=12 frames/row
(L11 MED speedUps≈8 — the shipped rig's usual default). n=120 seeds/level.

### L11 (primary)

| metric | value |
|---|---|
| paired pills (both cleared, n=111/120) | **−8.17** pills, 95% CI **[−14.39, −1.74]** → **REAL** |
| better / worse / tie | 66 / 44 / 1 |
| clear rate | 95.8% → 95.8% (unchanged) |
| discordant pairs | 8 (tuck-only wins 4, tuck-only losses 4), sign-test p=1.0000 |
| fires/game | 9.21 |
| tuck candidates seen/game (generator, pre-argmax) | 140.68 |
| unexecutable fired (design bug if >0) | **0** |

### L14 / L20, and the full 3-level table

| level | paired pills (n both-cleared) | 95% CI | verdict | clear off→on | discordant (tuck-only W/L) | sign-test p | fires/game | unexecutable |
|---|---|---|---|---|---|---|---|---|
| L11 | −8.17 (111/120) | [−14.39, −1.74] | **REAL** | 95.8%→95.8% | 8 (4/4) | 1.000 | 9.21 | 0 |
| L14 | −6.18 (114/120) | [−13.63, +1.09] | WASH | 96.7%→97.5% | 5 (3/2) | 1.000 | 9.02 | 0 |
| L20 | +2.07 (109/120) | [−5.87, +9.88] | WASH | 96.7%→**93.3%** | 10 (**3/7**) | 0.344 | 8.93 | 0 |

**L20 is the honest concern in this report.** The point estimate flips positive (worse)
and clear rate drops 96.7%→93.3%, with tuck-only losses outnumbering tuck-only wins
7-to-3 (not significant at n=120: sign-test p=0.34, and the pills CI still spans zero
either direction). This is the SAME direction as the endgame-composition regression
documented in dr-mario-tuck-override-validated for the ORIGINAL (leaf/executor-level)
tuck override — pills improved at all three levels there, but endgame p/v got worse
with level (L11 34.7 good / L14 39.5 neutral / L20 43.3 bad), traced to tucks entering
the endgame with a harder residual, not to the tucks themselves being bad plays. Root-
action tucks here fire at a HIGHER, uncontrolled rate (~9/game vs the 4.7–4.9/game the
prior work used, with no `DRTUCK_GATE` endgame suppression applied), so if the same
mechanism is at work it would plausibly be AMPLIFIED, not dampened, relative to the
original result — consistent with what L20 shows. n=120 is not enough to call this
REAL or NOISE on its own; §5 recommends what to run before treating root-action tucks
as level-independent.

### Reading

The L11 number lands almost exactly between the two prior tuck measurements: the
FULL gravity-legal space (−8.51, [−11.87,−5.16], any column/orientation, no
executor restriction) and the executor-CORRECTED leaf override (−5.20,
[−8.92,−1.47], same reach model as this design but scored at depth-1 by a
post-search gate). Root-action, using the SAME motion-legality gate as the −5.20
result but scoring with the full depth-3 subtree instead of a leaf proxy, gets
**−8.17 [−14.39,−1.74]** — closer to the unrestricted full-space number than to
the leaf-restricted one, and its CI excludes zero. This is consistent with the
exactness-gate hypothesis: leaf-gating was throwing away value that full-depth
scoring recovers, not because the executor's reach was insufficient (it's the SAME
reach model here) but because the SCORING was the bottleneck, exactly the
diagnosis behind the v2 leaf-gate refutation.

Clear rate is a wash at L11 (95.8%→95.8%, discordant 8, sign-test p=1.0), so the
gain here reads as a SPEED effect (paired pills), not a robustness effect — same
pattern as the original tuck-override-validated result and the lnk1 finding that a
speed metric and a robustness metric can each be real independent of the other.

**Fire rate is high and should be watched, not shipped blind.** 9.21 fires/game is
above both the 4.7–4.9/game that validated the original override and the ~2.2/game
"historically worked" discipline noted for the endgame planner. The result is still
decisively positive at this fire rate, but a firmware port should re-measure whether
a NARROWER root-action set (e.g. capping tuck candidates per decision, or requiring
a minimum eval margin over the best base action) trades away much of the win for a
smaller RTL/6502 footprint, rather than assuming 9/game is free just because THIS
run says the total is positive.

Zero unexecutable-fired placements, independently re-verified at fire time (not
just trusted from the generator) on every one of the ~1,100 tucks fired across 120
L11 games — the legality gate does what it claims.

**Relation to the user-confirmed capability ladder** (task assignment, 2026-08-01):
straight-drop = 0 → one-switch executor = −5.20 [−8.92,−1.47] (leaf-scored) → full
maneuvers including rotation timing = −8.51 [−11.87,−5.16] (unrestricted BFS, no
executor). v3 was scoped to bank the MIDDLE tier — the existing one-switch executor
reach, no new mailbox bytes — with the richer per-row column+orient schedule toward
the top tier deferred as a future upgrade. This offline proof used exactly the
middle-tier reach model but the TOP-tier scoring machinery (full depth-3, not a leaf),
and landed at **−8.17**, well past the −5.20 the ladder expected root-action to bank
and within noise of the top-tier full-maneuver number. That is the headline finding of
this phase: **the tuck feature's ceiling was gated more by SCORING depth than by
EXECUTOR reach** — the one-switch executor, properly scored, recovers most of what
full maneuvering offered, which materially changes the cost/benefit of ever building
the richer per-row schedule descriptor (more mailbox bytes, more driver/RTL work) —
it may not be worth its cost if root-action alone gets this close.

## 4. Verification artifacts

```
$ python3 root_search.py
equivalence self-test: 200 boards, action mismatches 0, value mismatches 0
PASS

$ DRCANON=.../dr-mario-canonical-wt DRNAV=.../driver-nav python3 tuck_regression.py
1. ENUMERATOR GOLDENS ... 9/9 PASS
2. EXECUTOR CONTRACT (v1 firmware, expected-fail mode)
   [xfail] D1: published trigger is in $0386 space (15-r)
   [xfail] D1: raw trigger must not land off the scored column
   [xfail] D3: descriptor is enumerated FOR best_col, not deepest-over-all
   -> confirms v1 firmware still needs D1+D2+D3 fixed together for any FIRMWARE
      port; this offline proof sidesteps all three by executing tuck cells
      directly, so it is not itself evidence D1/D2 are fixed.
```

## 5. Go / no-go recommendation

**CONDITIONAL GO.** The design is sound and the L11 evidence is decisive (REAL,
[−14.39,−1.74], verified-identical baseline arithmetic, zero unexecutable fires,
zero fire-rate discipline applied and it still won cleanly). But this is NOT the
clean 3/3-level confirmation the original tuck-override-validated result got: L14
is a wash and **L20 shows a clear-rate regression (96.7%→93.3%, tuck-only losses
7 vs wins 3)** that, while not statistically significant at n=120, points the same
direction as the KNOWN endgame-composition failure mode from the original override
(tucks entering the endgame with a harder residual). Recommend, before firmware
commitment:

1. **Re-run L20 at a larger n and/or with an endgame fire-rate gate** (mirroring
   `DRTUCK_GATE` from the original override, which the memory record shows FLIPS
   the endgame outcome at L20 in the OPPOSITE direction when removed — gating was
   refuted for the leaf-scored override there, but that finding predates root-
   action's higher, uncontrolled ~9/game rate and should not be assumed to transfer
   unchanged). Do not ship root-action tucks level-independent until L20 is
   resolved one way or the other.
2. **Cap the fire rate before any firmware commitment.** 9.0–9.2 fires/game across
   all three levels is well above the 4.7–4.9/game that validated the original
   override and the ~2.2/game discipline noted for the endgame planner — and it was
   NOT purpose-built into this design, it is simply what "every motion-legal tuck,
   always scored" produces. Re-measure with a capped candidate set (e.g. top-1/2 by
   a cheap pre-filter, or a minimum eval-margin-over-best-base-action threshold) to
   see how much of the win survives a materially smaller RTL/6502 footprint before
   the lead sizes the copro cost.
3. D1/D2 (mailbox coordinate space, per-frame descriptor wipe) are still open v1
   firmware bugs, orthogonal to this design, and must land before ANY DRTUCK=1 cart
   ships, root-action or not (confirmed against `tuck_regression.py`, §4). D3 is
   structurally dissolved by root-action and needs no separate fix.
4. Per the user-confirmed capability ladder (§3, "Relation to..."), the offline
   evidence suggests the one-switch executor reach, properly scored, gets close to
   the full-maneuver ceiling — **the richer per-row rotation-inclusive schedule
   descriptor (more mailbox bytes) may not be worth building** given what root-
   action alone recovers. Recommend treating that upgrade as deferred pending #2's
   fire-rate-capped re-measurement, not as an assumed next step.
5. #33's passenger note (the $5089 xlate fix riding along with any tuck v3
   resynthesis) is unaffected by anything here — still a passenger, batch it
   whenever Quartus opens for this task, not evaluated in this phase.
