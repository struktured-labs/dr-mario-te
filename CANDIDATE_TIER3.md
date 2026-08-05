# Tier-3 tuck vocabulary — candidate report (task #17, tier-3 mission, 2026-08-05)

Branch: `tuck-bfs-6502` (worktree `dr-mario-canonical-wt`). Ship target decided by the
knee sweep: tier-3 motion vocabulary (any approach column, ≤1 lateral direction change) —
tier 3 recovers 100% of the reachfull2 oracle bit-for-bit (0/120 seeds under v1) and the
pills value (−23.49) is real under the honest v1.1 re-check, even though the bad-ends
delta alone is a wash. This document tracks the mission's five milestones.

## Status: M1–M3 done, M4 (offline A/B) and M5 (candidate build + co-sim gate) in progress

| # | Milestone | Result |
|---|---|---|
| 1a | Python reference for tier-3 translation | `tests/translate_ref_tier3.py`, 97.7% coverage of tier≤3, 0 over-accepts |
| 2 | Bit-exact 6502 port | `tests/tuck_bfs_tier3_6502.py`, 0/1490 mismatches |
| 3 | Full-chain trajectory games | tier-3 fires 3x more often than tier-1 on the same seed/window |
| 4 | Offline firmware A/B (θ250, n≥60) | in progress |
| 5 | Candidate copro image + co-sim gate | in progress |

## 1. The driver finding (why tier 3 needs no new descriptor format)

The real executor (`dr-mario-mods-wt/driver-nav/patch_cartridge_copro.py`, `mv_p2`) steers
with a plain compare-and-hold: while row < trigger, hold toward the approach column; once
row ≥ trigger, hold toward the target column instead. This is already general over all 8
columns — nothing in the driver enforces `target±1`. That restriction was purely
`tuck_scan_v3`'s own enumerator (`TS_SIDE` hardcoded to `{target-1, target+1}`). So the
CANDLIST descriptor `(target, approach, trigger, rest, orient)` needs no format change —
only the *derivation* (which `(approach, trigger)` pairs are safe to publish) needed to
widen.

## 2. Python reference: `mono_reach` + the safety axis tier 1/2 never checked

`tests/translate_ref_tier3.py`'s `mono_reach(board, 'L'/'R')` computes a restricted variant
of the row-monotonic BFS fixed point with one lateral direction disabled — this is the REAL
safety check tier 1/2 never performed (they verify a column is "empty enough" or "visited
via some path", never that the driver's *specific* monotonic hold can reach it).
`derive_tier3()` searches all approach columns (nearest-to-target first, including
`approach == target` for rotation-kick-only landings) gated on `mono_reach`, reusing tier
1/2's own geometric phase-2 acceptance test verbatim for the final entry+fall.

**Validated** (`tests/test_translate_tier3.py`, 200-board real-L11 corpus): the cascade
(tier 1 unchanged + tier 3 fallback) recovers **1456/1490 (97.7%)** of
`translatable.py`'s `tier_of()<=3` population, **zero over-accepts** (nothing `tier_of()>3`
ever gets a descriptor). More than double the tier-1-only baseline (668/1490 = 44.8%). The
34 misses (2.3%) all share one documented root cause: rotation happening late, interleaved
with or after the final lateral move — a real structural limit of a fixed-final-orientation
2-phase descriptor, not a bug; left untranslated rather than force-matched (the "permissive
direction is dangerous" warning in `tuck_scan.py`'s own docstring).

## 3. 6502 port: bit-exact, with two real bugs found and fixed

`tests/tuck_bfs_tier3_6502.py`. Reuses `tb_is_legal`/`tb_vbit`
(`tuck_bfs_6502.py`) and `tr_first_occ`/`tr_is_empty`/`tr_fall_vert`/`tr_fall_horiz`
(`tuck_bfs_translate_6502.py`) verbatim. `mono_reach` needs two 64-bit-plane fixed-point
closures (L-restricted, R-restricted); rather than duplicating
`row_fixedpoint`/`down_propagate`/`row_step`/`check_and_mark`/`mark_state`/`vis_test`/
`vis_set_new` per direction, a single `T3_MODE` flag threads through one shared copy of
each. New RAM: `MONO_VIS_L` ($0F80), `MONO_VIS_R` ($0FC0), extending
`tuck_bfs_6502.py`'s already-validated $0E00-$0F7F claim to the end of that page. New ZP
$A9-$B3 (11B). `tr_derive_cascade` (tier1 then tier3) + `tr_translate_tier3` wire this in
as a new additive entry point — `tuck_bfs_6502.py`/`tuck_bfs_translate_6502.py` are never
modified.

**Bug 1** (SD computation): first draft used `first_occ(target)-1` for both orientations;
horizontal needs `min(first_occ(target), first_occ(target+1))-1` (the same rule
`tr_try_horiz` already implements for tier 1). Missing it silently rejected valid
candidates whenever the target column was empty but its horizontal partner wasn't. Found by
the bit-exact gate diverging on board 8 of the corpus; fixed by branching on orientation.

**Bug 2** (performance, not correctness): `tr3_derive` originally rebuilt both `mono_reach`
planes from scratch on *every* candidate that fell through to tier 3, not once per board.
Factored into `t3_setup_board`, called once per board. Bit-exact gate re-confirmed 0/1490
mismatches after the fix; direct-call gate time dropped 104.2s → 43.2s (2.4x).

**Validated**: 0/1490 mismatches (direct `tr_derive_cascade` calls vs the Python cascade,
every tuck-class candidate in the 200-board corpus), 0/15-board mismatches through the real
`tuck_bfs → tr_translate_tier3 → CANDLIST` integration path.

## 4. Firmware wiring

New env knob `DRCOPRO_TUCKBFS_TIER3=1` in `fpga/copro/build_copro_d3.py` (requires
`DRCOPRO_TUCKBFS=1` — tier 3 is a translation upgrade, not a standalone enumerator). Swaps
one call in the `tuck_bfs_v3` entry point (`tr_translate` → `tr_translate_tier3`).
Byte-identity re-confirmed: `DRCOPRO_TUCKBFS=1` image hash
(`c2a0ec2add239cb3c08d561a77799748`) is identical before and after this edit.

## 5. ROM budget (ahead of the candidate build, per the team's scope note)

Measured the actual assembled `tuck_bfs_code` size in the real $9000-$A7FF window
(`tuck_bfs` + `tr_translate*` + tier 3 + `tuck_v3`'s scoring functions — exactly what
ships):

| build | size | window avail | margin | utilization |
|---|---|---|---|---|
| tier-1 only | 2461 B | 6144 B | 3683 B | 40.1% |
| tier-1 + tier-3 | 3581 B | 6144 B | 2563 B | 58.3% |

**Tier 3 fits comfortably.** No tier-2 fallback needed on the ROM-budget axis. (The
search/stub window is unaffected by either knob: 2356 B + 48 B.)

## 6. Full-chain trajectory games (milestone 3)

Same seed (0), same 50-pill window, same board sequence, only `DRCOPRO_TUCKBFS_TIER3`
differs (`tests/trajectory_results/tier3_mission/`):

| arm | fires / 50 pills | verification failures |
|---|---|---|
| tier-1 | 1 | 0 |
| tier-3 | 3 | 0 |

3x the fire rate on this single-seed sample, directionally consistent with the corpus-level
coverage jump (44.8% → 97.7% of tier≤3). Pill 48's tier-3 fire
(`target=2,rest=14,orient=2,approach=2,trigger=14`) is a genuine tier-3-only case (the
`approach==target` rotation-kick-only path). Every fire's published descriptor matched its
CANDLIST entry and landed on empty cells.

## 7. Known follow-ups

- Real firmware step count per decision under py65 is still ~3-4x the tier-1 baseline even
  after the mono_reach-per-candidate fix (two fixed-point closures aren't free even
  computed once per board). Not a correctness concern; a real consideration for anything
  timing-sensitive.
- The 2.3% coverage gap (§2) is a structural descriptor-format limit, not something the
  current design can close without a genuinely richer descriptor (out of scope for this
  ship target).

## 8. Milestone 4 — offline firmware A/B (done)

**Context**: `dr-mario-qa-wt/experiments/eval47/run_tier_sweep.py` (commit `414a1e8`,
another agent, task #67) already ran an n=120 sweep using `translatable.tier_of()`'s
ABSTRACT classification as the tuck-eligibility filter, and found tier≤3 bit-for-bit
indistinguishable from the `reachfull2` oracle (0/120 seeds moved). That's a ceiling —
"if the search could pick ANY tier≤3-classified candidate, does it match the oracle" — not
a measurement of whether THIS FIRMWARE (which only finds a publishable descriptor for
97.7% of that population, §2/§3) actually delivers that value.

**This milestone**: new script `dr-mario-qa-wt/experiments/eval47/firmware_tier3_ab.py`
(pushed to `copro-qa-harness`). A new `tier_fn`, `firmware_tier_of`, wraps the ACTUAL
firmware-validated cascade (`translate_ref.derive_verified` for tier 1,
`translate_ref_tier3.derive_tier3_verified` as the fallback — the exact same code path
bit-exact-validated against the 6502 in §3) instead of the abstract `tier_of()` ladder.
`play()` duplicates `run_tier_sweep.py`'s own loop (same convention that file's docstring
documents: new file over refactor-in-place), calling `reach_root.choose_reach_tier(...,
max_tier=1, tier_fn=firmware_tier_of)` — `reach_root.py` itself untouched (owned by
another agent mid-run; read-only import, same as `run_tier_sweep.py`'s own pattern).

**Result, n=60 (bursty pressure, L11), three paired arms (base32, firmware-tier3,
reachfull2 oracle)**:

| comparison | pills | clear rate | bad-ends | mcnemar | seeds moved |
|---|---|---|---|---|---|
| firmware-tier3 vs base32 | −17.57 [−36.46,+2.30] wash | 68.3%→81.7% | 19→11 | rescued=12 harmed=4, p=0.077 | 16/60 (26.7%) |
| firmware-tier3 vs reachfull2 | +0.67 [−3.18,+6.37] wash | 86.7%→81.7% | 8→11 | rescued=0 harmed=3, p=0.25 | 3/60 (5.0%) |

Firmware-tier3 rescues **8 of the oracle's 11 total bad-end rescues (72.7%)** relative to
base32 — a clear, directional win over what's currently shipped (tier 1 only), though at
n=60 the pills CI is wide and the vs-base32 mcnemar p=0.077 doesn't clear the conventional
0.05 bar (worth a larger n if a tighter number is ever needed).

**The honest gap this milestone was built to surface**: the firmware does NOT achieve
game-outcome parity with the oracle the way the abstract tier≤3 classification promised.
It diverges from `reachfull2` on 3/60 seeds (5%), and — notably — all 3 are losses relative
to the oracle (mcnemar rescued=0, harmed=3), not a wash of wins and losses. This is
consistent with, and gives real weight to, the 2.3% per-candidate coverage gap documented
in §2/§3: a small number of missed descriptors evidently CAN cascade into a worse game
outcome on the seed where they matter, even though the abstract classification (which
doesn't know the firmware fails to publish some of those candidates) reported zero gap at
n=120. Not statistically nailed down at n=60 (p=0.25 on the 3 moved seeds), but the
DIRECTION (100% harmed, 0% helped, among the seeds that moved) is exactly what "the
firmware, not the python model, actually delivers the value" was asking to check, and it
found a real, if small and imprecisely-sized, shortfall.

Raw results: `dr-mario-qa-wt/experiments/eval47/results/firmware_tier3_ab_n60.json`.

## 9. Milestone 5 — candidate build + co-sim gate (in progress)

Plan: `dbg_build.py all 0` with `DRCOPRO_TUCKBFS=1 DRCOPRO_TUCKBFS_TIER3=1` exported, then
`run_gate.sh` (verilator co-sim, cell-exact move comparison) — NOT touching the shipped
`copro_rom.hex` on this branch.
