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
| 5 | Candidate copro image + co-sim gate | candidate hash `12a0906bec7358fae6c914d5683a3dab`; RTL diff CONFIRMS tier-3 changes 4/12 real RTL decisions (reproduced in 2 independent build pairs); py65 cross-check surfaced an unrelated, pre-existing py65-vs-RTL gap in the base search (§9) — flagged, not resolved; silicon A/B gated on the platform wedge fix |

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

## 9. Milestone 5 — candidate build + co-sim gate (done, with an open finding)

**RTL SMOKE TEST** (both firmwares run cleanly): rebuilt `obj_mister/mister_vsim` from
source (verilator, `--build` incremental — 7.7s). Built `copro_rom.hex` with
`DRCOPRO_TUCKBFS=1 DRCOPRO_TUCKBFS_TIER3=1` via `dbg_build.py all 0`, generated a 12-board
synthetic corpus (`gen_corpus.py`), ran it through the REAL RTL (`CoproDrMario.sv` +
`LeafEval.sv` + `copro6502.v` + `copro_alu.v`). All 12 cases completed cleanly with sane
real decisions, ~0.3-1.2s of simulated 85.9MHz time each.

**RTL DIFF — tier-1 vs tier-3, same 12 boards** (per team-lead's explicit follow-up: "it
runs" is not "it does the thing"). Built a SECOND hex with `DRCOPRO_TUCKBFS_TIER3=0`
(tier-1 only) and ran the SAME corpus. **Result: 4 of 12 boards differ** (cases 0, 1, 6, 8)
— a real, non-trivial behavioral change under actual RTL, not just "the wiring runs without
crashing":

| case | tier-1 | tier-3 |
|---|---|---|
| 0 | (5,0) | (5,2) |
| 1 | (1,2) | (2,2) |
| 6 | (4,0) | (3,2) |
| 8 | (4,2) | (3,2) |

Reproduced IDENTICALLY (same 4 cases, same exact values both sides) in a second pair of
runs built via `dbg_build.py baseline 0` (`USE_DELTA=False`, see below) — the diff is
robust, not a one-off artifact of a single build.

**ACCEPTANCE CRITERION 2 — could NOT be completed as specified, and here is exactly why**
(team-lead's own standard: report this plainly rather than force a pass). The instruction
was to confirm each differing board's tier-3 RTL decision is one py65 also predicts.
Attempting this surfaced a real methodology problem, then a real and more consequential
discovery:

1. The RTL candidate above was built via `dbg_build.py all 0` — `USE_DELTA=True`, the
   hardware-accelerated CMD-6/CMD-7 incremental-leaf engine. Every py65 run this entire
   session (M2's bit-exact gate, M3's trajectory games, M4's spot-check) used
   `build_image()` directly, which defaults to `USE_DELTA=False` — and
   `attach_engine_emu`'s own `wr_cmd` handler only implements CMD 1/2/3, never CMD-6/7 (a
   PRE-EXISTING, DOCUMENTED limitation — `build_copro_d3.py`'s own `main()` docstring:
   "py65 cannot run the RTL delta engine"). So the first py65 cross-check was comparing
   against the wrong search path entirely — not a tier-3 bug, a comparison bug.
2. Fix attempted: rebuilt BOTH hexes via `dbg_build.py baseline 0` (`USE_DELTA=False`,
   matching py65's own capability) and reran the RTL diff — **identical result, same 4
   boards, same values** (table above) — confirming delta and non-delta modes agree on
   this corpus and ruling out USE_DELTA as the source of any remaining discrepancy.
3. Cross-checked py65 (correctly configured, `DRCOPRO_TUCKBFS_TIER3=1`, non-delta) against
   this baseline RTL run's differing boards: **0 of 4 matched** (py65 gave `(5,0)`,
   `(0,3)`, `(4,0)`, `(0,2)` for cases 0/1/6/8 vs RTL's `(5,2)`, `(2,2)`, `(3,2)`, `(3,2)`).
4. Before concluding tier-3 is broken, checked py65 against RTL on the 8 UNCHANGED boards
   (where tier-1 and tier-3 RTL AGREE with each other, so tier-3's own logic is not even
   in play) — **still only 4 of 8 matched** (cases 7, 9, 10, 11 matched; cases 2, 3, 4, 5
   did not). This is the decisive data point: **py65 disagrees with real RTL on half of
   this corpus's BASE search decisions, with zero tuck/tier-3 code involved at all.**

**Conclusion**: the RTL diff (4/12 boards, tier-3 changes real decisions) stands as strong,
robust, positive evidence — reproduced identically across two independent build/run pairs.
The attempted py65 cross-check did NOT confirm or refute it; instead it surfaced a
previously-unknown, general py65-vs-real-RTL discrepancy in the BASE search on
`gen_corpus.py`'s synthetic corpus, predating and unrelated to this branch's tier-3 work.
Plausible (not confirmed) explanation: `gen_corpus.py`'s own docstring states this corpus's
"oracle columns are dummy... the gate compares baseline-vs-delta moves on the SAME boards,
not vs any oracle" — it was built and only ever validated for RTL-internal
self-consistency, never for py65 agreement, and `test_depth2._rand_board`'s random
synthetic boards may produce near-tied eval states where py65's and the real RTL's
tie-breaking genuinely diverge (a different but equally "correct" pick), unlike this
branch's OWN 200-board real-L11 corpus (`tuck_bfs_corpus_200.json`) where M2's bit-exact
gate scored 0/1490 and M3's real-gameplay trajectory games produced consistently sane
results across many decisions. **Root-causing this base-search py65-vs-RTL gap is a
separate, larger investigation, out of scope for this candidate** — flagged here for
whoever owns py65/RTL fidelity work next, not swept under the rug.

**What this means for the ship decision**: unchanged from §8's read — tier-3 vs tier-1 is
still the comparison that matters, and the RTL diff is additional, robust, positive
evidence that tier-3 has a real effect on real hardware (not just "the wiring runs"). The
open finding is about py65's fidelity to RTL on ONE synthetic corpus, not about whether
tier-3's own translation logic is correct (M2's isolated bit-exact gate, 0/1490, is
untouched by this finding — it never depends on the base search's own decision).

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
| tier-1 only (`dbg_build.py baseline 0`, RTL diff control) | `DRCOPRO_TUCKBFS=1` | `c8e934e528a423974f7300a7ac4b0790` |
| tier-1 + tier-3 (`dbg_build.py baseline 0`, RTL diff control) | `DRCOPRO_TUCKBFS=1 DRCOPRO_TUCKBFS_TIER3=1` | `5d2c3783ca20da8d9322c3693704a1b9` |
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

## 10. Real-L11 fidelity follow-up (2026-08-05)

Team-lead's follow-up question after §9's synthetic-corpus finding: is the py65-vs-RTL
base-search gap corpus-specific (near-tied evals on `gen_corpus.py`'s random synthetic
boards) or general? Answered on 30 fresh real-L11 boards (proper NES-tile encoding via
`fast_rtl_x.board_flat()`, real na/nb next-pill values, generated the same way as this
branch's own `tuck_bfs_corpus_200.json` — `hostdata.txt` md5 `33d391b7dcb425a3e65e0339630877a6`),
using the tier-1-only, non-delta baseline hex (`c8e934e528a423974f7300a7ac4b0790`, the same
build used for §9's control) on both sides.

**Result: 4 of 30 full (col, orient) matches — 13.3%, WORSE than §9's 4/8 (50%) on the
synthetic corpus.** Column-only agreement is 7/30 (23.3%); orientation-only is 8/30
(26.7%) — both close to what independent/near-random tie-breaking would produce, no
skew toward either axis. The 4 full matches (cases 0, 12, 15, 17) show no shift or
board-position pattern (checked ±1 index shift against a corpus-alignment bug; no
improvement, ruling that out as an artifact).

**Conclusion: the gap is general, not corpus-specific — and more pronounced on real
gameplay boards than on `gen_corpus.py`'s synthetic set.** This raises the stakes on
§9's "separate, larger investigation" note: py65 cannot currently be trusted as an oracle
for the *base* search's decision on arbitrary boards, real or synthetic. It does **not**
touch this candidate's own bit-exact guarantees — M2's tier-3 translation gate (0/1490)
and the CANDLIST wiring never depend on which move the base search picks, only on
correctly translating whatever CANDLIST the search already built. But it means every
py65-only offline claim in this program (including §8's n=60 A/B, which runs entirely in
py65) is validating the *tuck logic*, not validating that py65's move choice matches what
silicon will actually do move-for-move. The silicon A/B in §11 is therefore not optional
confirmation — it is the only real measurement of this candidate that exists.

## 11. Silicon build + staged A/B protocol (2026-08-05)

**Build.** Candidate hex (`12a0906bec7358fae6c914d5683a3dab`, the M5 ship recipe —
`DRSTRAND=20 DRCOPRO_TUCKBFS=1 DRCOPRO_TUCKBFS_TIER3=1 DRCOPRO_ARM=1 DRFIX=1 DRCHAIN=180`
via `dbg_build.py all 0`) vendored into `~/projects/NES_MiSTer-winner`
(`claude/winner-single-copro@7f6ba69`, the exact tree that built s20b), `SEED 7` preserved
from the working tree (matches s20b's actually-deployed reseed, not `HEAD`'s stale
`SEED 5`). RTL confirmed byte-identical to what's already vendored (`LeafEval.sv`,
`CoproDrMario.sv`). Full rebuild (`rm -rf db incremental_db` first, per the
`update_mif`-is-a-no-op-for-`$readmemh` trap) launched via
`nohup nice -n 10 ./run_fit.sh > fit_s20t3.log 2>&1 < /dev/null & disown` from that
directory; log at `~/projects/NES_MiSTer-winner/fit_s20t3.log`. Compile flow itself
completed clean at SEED 7 (Assembler stage, 0 errors/169 warnings — the normal warning
count for this project, exit=0) in 18 minutes, much faster than the 1-2h estimate. Output
copied to `NES_stomper180s20t3_20260805_seed7_TIMINGFAIL.rbf`, md5
`1da3d05756f32e98c0e3cbcec034111a` — confirmed distinct from both known baselines
(`6fa85844…` s20 seed2, `72d5a92f…` s20b seed7), so the artifact genuinely embeds the new
firmware (the `update_mif`-is-a-no-op trap does not apply here).

**Timing closure: FAILS at SEED 7, a real finding, not a formality.** Worst-case slack is
**-0.074ns** (TNS -0.138ns) on `pll_hdmi|...|counter[0].output_counter|divclk` — the HDMI
PLL divider chain, a display-output clock domain, *not* the copro/emu clock domain (which
shows a clean +0.076ns on this same build). Checked against history before treating this
as either "probably fine" or "definitely broken": this exact path is s20b's own worst-case
path too, and s20b's SEED 7 build closed it at **+0.156ns**
(`fit_strand20_seed7.log:` `332119` line). Same RTL, same seed, only the ROM payload
differs — s20b's own seed sweep (`fit_strand20_seed3.log` -0.327, `_seed5.log` -0.049,
`_seed7.log` +0.156, unlabeled default +0.102) shows this design sits right at the timing
edge on this path and genuinely needs a seed search to close; SEED 7 was picked *for
s20b's firmware*, and this candidate's different ROM content was evidently enough to shift
placement/routing and flip that same path from pass to a marginal fail. **Do not flash
`..._seed7_TIMINGFAIL.rbf` to hardware for the A/B** — a failing HDMI clock domain risks
visible display glitches that would undermine a fair/watchable comparison (game-logic
clock domain is unaffected, but this is not a fit to hand off as-is).

Given the fit's actual 18-minute runtime (not 1-2h), a re-seed retry is cheap. Launched
`SEED 9` (`rm -rf db incremental_db` + relaunch, same recipe) at the time of writing —
log at `~/projects/NES_MiSTer-winner/fit_s20t3_seed9.log`. **This report will be updated
with the outcome; if SEED 9 also fails to close, the next step is to keep sweeping (11, 13,
…) following the exact pattern that found SEED 7 for s20b, not to ship a timing-failing
rbf.**

**Arms.**
- **A (control)**: the currently-shipped tier-1-only firmware, hash
  `e970e9ab0208cdbce1d39ed33e2f51ee`, currently live on MiSTer (s20b: rbf `72d5a92f…`,
  seed 7). Confirm the exact rbf filename on the box before the session — there are two
  seed variants (`s20` seed 2 `6fa85844…` and `s20b` seed 7 `72d5a92f…`) sharing this
  firmware; use whichever is actually deployed at session time.
- **B (candidate)**: firmware `12a0906bec7358fae6c914d5683a3dab` (this candidate),
  final rbf name/seed TBD pending timing closure — see the timing-closure note above.
  Do not substitute the SEED-7 build (`..._seed7_TIMINGFAIL.rbf`); use only a build that
  closes with positive slack on all paths.

**Cart / mgl.** Same probe cart both arms, `latch_converged_native_probe.nes`
(unchanged) — this is the pattern the s20/s20b rig already uses
(`combo_stomper_s20_probe.mgl`, `combo_stomper_s20b_probe.mgl`, per
`experiments/rtl_chain/ship/stomper180s20-seed2/REBUILD.md`). Create
`combo_stomper_s20t3_probe.mgl` by copying the s20b probe mgl and repointing its rbf
reference to the new candidate rbf — cart and controller/link config unchanged, only the
core swaps.

**Paired-seed handling.** The cart's RNG is deterministic per boot-frame-count on this
seed (`dr-mario-seed-is-deterministic-on-cart` — rebooting alone adds zero entropy); a
genuine paired design would need to pin the same boot-frame count across both arms'
launches, which the probe/tracker infrastructure does not currently control for. **Do
not assume pairing** unless that control is added — treat this as two independent
samples (arm A's N games, arm B's N games) and use an unpaired test (e.g., two-proportion
z-test or Fisher's exact on clear-rate; Mann-Whitney on pills-to-clear), not McNemar. If
frame-count pinning gets added before the session, switch to paired McNemar to match
§8's offline methodology and get more power per game.

**Decision metrics** (mirroring §8's offline A/B so the silicon result is directly
comparable to the py65 one): clear rate (win by full clear vs bad-end), and
pills-to-clear conditional on a clear. §8's offline numbers to beat/confirm: bad-ends
19→11 (n=60), clear rate 68.3%→81.7%, McNemar p=0.077 (directional, not conclusive at
that n). A silicon result landing in the same direction with a comparable or larger
effect size is the confirmatory signal; anything flat or reversed is a real finding
that overrides the offline read, per §10's fidelity caveat.

**Wedge watchdog requirement.** Team-lead's stability update narrows but does not
remove this: the wedge is root-caused to the CvC autonav driver loop specifically
(framework, copro RTL, and the strand20 brain are all exonerated — a non-CvC human cart
survived 47+ min clean). **This A/B is CvC by construction (both arms are the copro
playing itself/the control)**, so it sits squarely in the still-affected mode and must
run under the wedge watchdog (tracker + auto-relaunch-on-timeout, screenshot-timeout
proof of wedge per the adopted method rules in `MORNING_DIGEST_20260805.md` — a timeout
proves a wedge, frame content alone never does; motion-diff at 3+ second spacing is the
ambiguous-frame tiebreaker).

Measured wedge cadence from the 34h continuous-CvC soak in REBUILD.md (s20b, same
platform, most directly comparable data available): **7 wedges in ~34h** (mid-play
family 3-in-~29h ≈ 1 per 9.7h historically, before the black-screen family's late
acceleration; black-screen family clustered in the soak's final ~4h, uptime-correlated,
now mitigated by a standing **preventive core reload every ~2h**). This supersedes the
original task brief's "6-30 min" figure, which reflects an isolated fast-reproduction
test (the CMD-8 6m15s check), not the standing soak rate under the current preventive-
reload mitigation. Recovery is fast when it's the mid-play family (menu.rbf cycle +
relaunch, order of a few minutes per REBUILD.md's own recovery notes); the one
black-screen recurrence that survived a menu cycle needed a full MiSTer reboot,
observed taking on the order of 45 minutes end-to-end including diagnosis (06:0x→06:45).
Budget for occasional full-reboot recovery, not just quick cycles.

**Per-game duration — NOT YET MEASURED, flag before committing to a session length.**
No direct wall-clock-per-game number exists in this program's silicon records; the only
anchor is that the CMD-8 isolation test completed multiple games before wedging at
6m15s, implying single-digit minutes per game, but that is not a measurement. **Recommend
the session open with a 10-game calibration mini-run per arm** (cheap, inside the ~2h
preventive-reload window either way) to nail down real per-game time on THIS cart/core
combination before committing to a target N or session length — reporting a fabricated
minutes/game number here would break this program's own "every number at its true
strength" standard.

**Clean-game target.** To match §8's offline power (n=60, McNemar p=0.077 — already
underpowered even paired), and given the unpaired test above needs more total games than
a paired one for equivalent power, recommend targeting **N≥40 clean games per arm (80
total)** as a first checkpoint, with a stretch target of N=60/arm if the wedge cadence and
calibrated per-game time allow it inside a single supervised session. A "clean game" =
completed to a decisive result (clear or bad-end) with no wedge/watchdog-triggered
relaunch during that game; a wedge mid-game discards that game, not the session's whole
history to that point.

**Rough duration** (pending the calibration mini-run above to firm up the per-game
number): with the preventive 2h reload cadence and typical multi-minute games, a
session budget of **4-6 hours of wall-clock supervised time** is a reasonable planning
number for N=40-60/arm — this is a planning estimate, not a measurement, and should be
revised after the calibration mini-run's first real numbers land.

**Status**: staged, not run — the box is team-lead's to schedule, per the task brief.
This section is ready to execute once (a) a candidate rbf CLOSES TIMING (see §12 —
SEED 13 is the first genuinely closing build found) and is hash-verified, and (b)
`combo_stomper_s20t3_probe.mgl` is created.

## 12. Seed sweep + fallback analysis (2026-08-05)

**Full sweep table** (same RTL/qsf, tier-1+tier-3 candidate firmware `12a0906b…`, worst
setup path reported by Quartus's own Timing Analyzer Summary — the "path" column names
which clock domain was the tightest for that seed):

| seed | slack (ns) | TNS (ns) | path | verdict |
|---|---|---|---|---|
| 7 | −0.074 | −0.138 | `pll_hdmi` counter[0] divclk | MISS |
| 9 | −0.020 | −0.114 | `pll_hdmi` counter[0] divclk | MISS |
| 11 | −0.060 | −0.217 | `emu\|pll\|pll_inst` counter[0] divclk | MISS |
| **13** | **+0.051** | **0.000** | `pll_hdmi` counter[0] divclk | **CLOSED** (thin) |
| 15 | −0.504 | −20.288 | `pll_hdmi` counter[0] divclk | MISS (large — many paths, not one marginal path) |
| 17 | −0.132 | −1.257 | `pll_hdmi` counter[0] divclk | MISS |

**Seed 13 is a genuine, Quartus-verified pass — precision matters here.** TNS (total
negative slack, summed across every failing path) is exactly `0.000`, meaning there are
**zero** paths with negative slack at seed 13, not just "the worst one happens to be
positive." By Quartus's own closure criterion this build passes cleanly; it is thinner
than s20b's own +0.156ns margin, not broken. Artifact:
`NES_stomper180s20t3_20260805_seed13.rbf` (kept as-is per the sweep script, not yet
renamed to the final candidate name pending your go-ahead) — hash to be confirmed and
recorded once you sign off on using it.

**Important nuance for the "is the HDMI path even relevant" question below**: the worst
path is *not* consistently the HDMI PLL divider. Seed 11's tightest path was on
`emu|pll|pll_inst`'s own counter chain — a different PLL block entirely (this design has
separate PLL instances for `emu` and `pll_hdmi`). This means a fix that only targets the
HDMI path would not have rescued seed 11, and by extension isn't guaranteed to be *the*
story for every future seed either. Also worth flagging: I have not independently verified
whether `emu|pll|pll_inst`'s counter[0] output feeds anything in the copro's own dedicated
clock domain — project history (`dr-mario-copro-clock-tap` memory) states the copro clock
is tapped into its own async group specifically to avoid this kind of entanglement, which
would mean it's a third, separate source from either PLL discussed here — but I have not
re-confirmed that against this exact qsf/SDC in this session, so I'm not asserting it as
fact.

### Option 1: tier-2 fallback — does not exist as firmware; the real fallback is much weaker than assumed

Checked before answering: **there is no `DRCOPRO_TUCKBFS_TIER2` knob, no tier-2 6502
module, and no tier-2 build has ever been assembled.** Tier-2 exists only as an offline
Python analytical function (`translatable._derive_tier2()` in
`dr-mario-qa-wt/experiments/eval47/translatable.py:257-304`), used solely inside the
knee-sweep's `tier_of()` classifier. Unlike tier-1 (`tests/translate_ref.py` /
`tests/tuck_bfs_translate_6502.py`) and tier-3 (`tests/translate_ref_tier3.py` /
`tests/tuck_bfs_tier3_6502.py`), tier-2 was never ported to 6502 or wired into
`build_copro_d3.py`. Building a real tier-2 firmware variant would mean porting
`_derive_tier2()` to 6502 and validating it with the same rigor as the tier-3 port (bit-
exact gate, translation gate, full-chain gate) — a comparable-scope task to the tier-3
mission itself, not a quick swap. **I did not attempt this** — it's real, multi-hour new
engineering, not something to improvise under this task's scope.

**The actual smallest real buildable fallback is tier-1-only** (`DRCOPRO_TUCKBFS=1`,
`DRCOPRO_TUCKBFS_TIER3` unset) — already bit-exact validated (M2's own gates), already
ROM-budgeted (2461B/6144B = 40.1%, vs tier-1+tier-3's 3581B/6144B = 58.3%), and I built it
just now with the exact ship recipe (`DRSTRAND=20 DRCOPRO_TUCKBFS=1 DRCOPRO_ARM=1
DRFIX=1 DRCHAIN=180` via `dbg_build.py all 0`, hash `04b6600919c5c1902ddb85b3bd4287c9`).

**But its value is far weaker than "tier-2" implies — this is the sobering finding.** Per
the knee-sweep (`dr-mario-qa-wt/experiments/eval47/REACH_ROOT_VERDICT.md:477-483`,
n=120 bursty, oracle rescue = 14 bad-ends out of 32 base): tier-1 alone recovers **14.3%**
of the oracle's rescue (2 of 14), vs the un-built tier-2's 85.7% (12 of 14), vs tier-3's
100% (14 of 14). Tier-1-only is not a graceful one-step-down fallback from tier-3 — it's a
cliff. Fitting it now at SEED 13 (the best seed found) to see whether the smaller payload
buys meaningfully more timing margin — result pending, log at
`~/projects/NES_MiSTer-winner/fit_tier1only_seed13.log`.

### Option 2: HDMI-path constraint relaxation — not recommending this

The HDMI PLL divider clock feeds the video/display output pipeline, a different physical
PLL from `emu`'s own clock tree (which carries the copro/game-logic timing, confirmed
clean at +0.076ns in the seed-7 run). For a purely headless, unwatched CvC A/B run, a
thin/failing margin there would risk video glitches, not corrupted game state or
decisions — the metrics the A/B decides on (clear rate, pills-to-clear) come from the
copro/game-logic domain, not the display pipeline. **But** two things stop me from calling
this "safe to relax": (1) per the seed sweep above, the HDMI path is not reliably *the*
violator — seed 11 failed on a different PLL entirely, so a targeted relaxation wouldn't
generalize; (2) this core is meant for more than a one-off headless A/B — the September
booth runs on a real TV for hours, where an HDMI-domain violation is exactly the kind of
thing that shows up as an intermittent, hard-to-repro glitch under thermal drift, and I do
not have (and did not attempt to gain, within this task's scope) real command of this
project's SDC files to know whether a false-path or exception on this specific divider is
a legitimate, pre-existing MiSTer-framework pattern or a real constraint being loosened for
convenience. Given seed 13 already closes cleanly by Quartus's own criterion without
touching any constraint, **I'm not recommending the constraint-relaxation route** — it's
solving a problem we already have a real, unmodified-constraint solution for.

### Recommendation

**Ship SEED 13.** It is a genuine, unmodified-constraint, TNS=0.000 timing closure — not a
workaround, not a smaller/weaker payload, not a relaxed check. Its margin (+0.051ns) is
thinner than s20b's (+0.156ns), which is worth tracking as an open risk for the
multi-hour warm-room booth session, but it is a real pass under Quartus's own worst-case
silicon/temperature timing model (the STA numbers throughout this report are already
computed at worst-case corners, not typical operating conditions, which tempers — doesn't
eliminate — the thin-margin concern). If more margin is wanted before trusting it for a
multi-hour unattended booth run, the next step is a short, bounded continuation of the
seed sweep (a handful more odd seeds) looking specifically for something closer to
s20b's own margin, not a switch to the tier-1-only fallback (14.3% of the value, a real
regression in what the candidate is *for*) or a constraint relaxation (unverified,
possibly non-general, and exactly the kind of move that should require deliberate
sign-off, not a quiet fix to make a number go green).
