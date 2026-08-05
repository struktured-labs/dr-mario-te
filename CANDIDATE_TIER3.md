# Tier-3 tuck vocabulary — candidate report (task #17, tier-3 mission, 2026-08-05)

Branch: `tuck-bfs-6502` (worktree `dr-mario-canonical-wt`). Ship target decided by the
knee sweep: tier-3 motion vocabulary (any approach column, ≤1 lateral direction change) —
tier 3 recovers 100% of the reachfull2 oracle bit-for-bit (0/120 seeds under v1) and the
pills value (−23.49) is real under the honest v1.1 re-check, even though the bad-ends
delta alone is a wash. This document tracks the mission's five milestones.

## Status: ALL FIVE MILESTONES DONE

| # | Milestone | Result |
|---|---|---|
| 1a | Python reference for tier-3 translation | `tests/translate_ref_tier3.py`, 97.7% coverage of tier≤3, 0 over-accepts |
| 2 | Bit-exact 6502 port | `tests/tuck_bfs_tier3_6502.py`, 0/1490 mismatches |
| 3 | Full-chain trajectory games | tier-3 fires 3x more often than tier-1 on the same seed/window |
| 4 | Offline firmware A/B (θ250, n≥60) | firmware-tier3 rescues 72.7% of the oracle's bad-end value vs base32 (ship case); 8/9 firmware-spot-checked fires corroborated |
| 5 | Candidate copro image + co-sim gate | candidate hash `12a0906bec7358fae6c914d5683a3dab`; RTL smoke test 12/12 clean; silicon A/B gated on the platform wedge fix |

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
- **NAMED CAUSE of the residual gap** (the 2.3% per-candidate coverage miss in §2/§3, and
  the 3/60-seed game-outcome gap vs the oracle in §8): rotation happening LATE, interleaved
  with or after the final lateral move — the current 2-phase `(approach, trigger)`
  descriptor assumes the pill settles into its FINAL orientation before or during phase 1,
  which is false for candidates that rotate again near landing (sometimes with a kick that
  also shifts the column). This is a structural descriptor-format limit, not something the
  current design can close. **Cost of closing it**: a 3-phase (or explicitly rotation-timed)
  descriptor would need a second trigger row for the rotation event, roughly doubling each
  CANDLIST entry (5B → ~7-8B × 14 slots ≈ +42-56B RAM) plus a third mono-reachability-style
  search phase in the translation routine — by analogy to tier 3's own ~1120B cost for ONE
  new phase, a second one is plausibly several hundred bytes even with maximal code reuse.
  Against the 2563B margin tier 3 leaves in the $9000-$A7FF window (§5), it would likely
  still fit, but would eat meaningfully into that margin for a gap this size (5% of seeds,
  and not even conclusively all translation-caused per §8's spot-check). Not scoped for
  this ship — the next-generation lever, not this build's.

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
0.05 bar. Team-lead's ship-decision reading: this is the comparison that matters (tier-3 vs
TODAY'S SHIPPED tier-1 vocabulary), and it's a clear directional win; the oracle gap below
is a ceiling-chasing question, not a ship-blocker, and n was deliberately NOT tightened
further — the honest larger-n run belongs later, under dr_lulu's fitted pressure model,
not the current proxy.

**METHODOLOGY SPLIT, stated explicitly per team-lead's requirement** (so a reference-run
number is never later mistaken for a firmware-run number, the exact class of ambiguity that
already burned this program once with the oracle-ceiling numbers): **all 60 seeds** in the
table above ran `firmware_tier_of` — the Python cascade (`translate_ref.derive_verified` +
`translate_ref_tier3.derive_tier3_verified`), bit-exact-validated against the real 6502 in
§3, but a Python execution, not a firmware one. A SEPARATE follow-up script,
`firmware_tier3_spotcheck.py`, then replayed 3 of those 60 seeds byte-for-byte and queried
the ACTUAL 6502 firmware (fresh `build_image()` + py65 stub-flow, subprocess-isolated) at
every board where the sweep's own decider fired a tuck — seeds chosen from the sweep's own
fire distribution as required (44: 10 fires, 0: 9 fires, 41: 8 fires — the three most
active seeds, not cherry-picked for outcome), 9 boards total.

**Spot-check result**: 8/9 boards had the REAL firmware also fire a tuck; 1/9 (seed 41,
pill 6) did not. This check deliberately does NOT assert the firmware picks the identical
candidate the mirror rig (`reach_root.choose_reach_tier`) chose — the mirror rig is a
different, faster scorer built for large-n sweeps, not a re-implementation of the real
depth-3 D3 search wired into the copro, so move-for-move agreement was never a claim either
side made. What it does show: the tuck opportunities the sweep is counting are real,
firmware-executable ones on real boards (8/9), with one board where the real search's own
winner-selection did NOT fire — consistent with, and additional evidence for, the residual
gap already reported above (whether that specific miss is a translation gap or the D3
search's richer eval simply preferring a base move the mirror's simpler scorer ranked
lower was not disentangled, and is flagged as unresolved rather than assumed either way).

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

## 9. Milestone 5 — candidate build + co-sim gate (done)

**Co-sim gate**: rebuilt `obj_mister/mister_vsim` from source (verilator, `--build`
incremental — 7.7s, this tree already had a cached build from a prior session). Built
`copro_rom.hex` with `DRCOPRO_TUCKBFS=1 DRCOPRO_TUCKBFS_TIER3=1` via `dbg_build.py all 0`,
generated a 12-board synthetic corpus (`gen_corpus.py`), and ran it through the REAL RTL
(`CoproDrMario.sv` + `LeafEval.sv` + `copro6502.v` + `copro_alu.v`, not py65's software
approximation of it). **Result: all 12 cases completed cleanly with sane real decisions**
(e.g. `copro=(5,0)`, `(1,2)`, `(6,2)`, `(4,2)`, ...), ~0.3-0.9s of simulated 85.9MHz time
each — confirming the tier-3-capable firmware wiring runs correctly end-to-end under the
actual hardware model, not just under py65's CPU-only emulation. (The `MISMATCH`/`0/12`
lines in the raw log compare against `gen_corpus.py`'s own DUMMY `(0,0)` oracle for
non-case-0 boards — expected and not a pass/fail signal; `run_gate.sh`'s own cell-exact
comparison methodology is baseline-vs-delta move equality, not vs that dummy target, and
was not the question this smoke test was asking. Per team-lead's guidance, this RTL
smoke test — not a further tier1-vs-tier3 RTL move diff — was treated as sufficient
evidence for this milestone, given the already-strong py65 bit-exact gate (M2, 0/1490) and
the offline A/B (M4) already on record.)

**`copro_rom.hex` handling**: git-tracked, confirmed clean before starting
(`f4b6dfbf76c9beb80d19b3659fb99d26`, matching `HEAD`). Building the candidate necessarily
overwrites it on disk; restored via `git checkout --` and re-verified clean+matching after
EVERY build in this milestone. No shipping artifact was left touched.

**CANDIDATE HASHES**:

| build | command | md5 |
|---|---|---|
| shipped (unchanged) | — | `f4b6dfbf76c9beb80d19b3659fb99d26` |
| knob fully off (py65 `build_image`) | — | `753bfb2397d10b5de078a1c9068433d2` |
| tier-1 only (py65 `build_image`) | `DRCOPRO_TUCKBFS=1` | `c2a0ec2add239cb3c08d561a77799748` |
| tier-1 + tier-3 (py65 `build_image`) | `DRCOPRO_TUCKBFS=1 DRCOPRO_TUCKBFS_TIER3=1` | `f5480f74874ce64fb03f44a4e361224e` |
| **candidate** (`dbg_build.py all 0`, the real ship recipe) | `DRCOPRO_TUCKBFS=1 DRCOPRO_TUCKBFS_TIER3=1` | **`12a0906bec7358fae6c914d5683a3dab`** |

**SEQUENCING CONSTRAINT — the silicon A/B must wait for the wedge verdict.** New fact from
team-lead: the pre-strand20 core ALSO wedges (6m15s, independently confirmed), so the wedge
is a PLATFORM-level issue, not a regression in this branch's work — this candidate is not
implicated. But a box that dies every ~6-30 minutes under continuous play cannot measure a
brain delta either way, so **any silicon A/B of this candidate is gated on the platform fix
landing first, not on anything in this report.** Once cleared: deploy this candidate
(`DRCOPRO_TUCKBFS=1 DRCOPRO_TUCKBFS_TIER3=1` via the normal `dbg_build.py all 0` recipe),
A/B against the currently-shipped tier-1-only firmware on real hardware.

This closes the tuck-bfs-6502 branch's tier-3 mission (task #17): milestones 1-5 all done,
documented, committed, and pushed.
