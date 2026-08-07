# ADVERSARY FINDINGS -- turning survivors into assets

**Date:** 2026-08-06 · **Target:** the shipped strand20 decide path -- `fast_rtl_x.variant("winner")`
leaf + `eval47/terms47.g_stranded` at `ws=20`, root-only, exactly as `ab47.py::_choose_base(wt=0,
ws=20)` does it, bit-exact via `eval47/reach_root.py::choose_base32`. L11, real NES pill stream
(`NesPillSource`), 300-pill cap, house failure taxonomy (TOPOUT / DIES_AHEAD / STALL / SLOW).

**Inputs:** `SEED_CENSUS.md` (Hunt A, solo play), `ADVERSARIAL_PRESSURE.md` (Hunt B, adversarial
garbage scheduler), `TRANSFER_FILTER.md` (structural-vs-fluke perturbation battery for both hunts).
All three were themselves interim/truncated reports whose background jobs kept running after being
written; this document was compiled after re-checking those jobs and letting the structural filter
run to completion for all four Hunt B candidates (see §0).

**Headline: of the four Hunt B garbage schedules, only ONE (`always_spawn_max`, the crude
"fire everything at spawn" heuristic) is a structurally-confirmed exploit -- and its own report
already shows it's the WRONG lever for the DIES_AHEAD signature the task cares about most (it's a
topout/bury weakness, not a doorstep-death one). All three targeting-tuned dies-ahead candidates,
including the report's own headline "13x" number, FAIL the structural transfer filter (1-2 of 5
perturbation categories survived, below the >=3/5 majority bar) -- their strong n=120 holdout numbers
were real but seed-block-specific, not a general champion weakness. Separately, Hunt A's still-running
background census surfaced one new single-seed STALL candidate (a buried-virus blind spot matching
already-open task #47) that has not yet been transfer-filtered.**

---

## 0. State-of-the-world update since the three input reports were written

The three source reports each documented a background job left running (nohup+disowned) past their
own truncation point, per this project's own house convention. Before writing this document those
jobs were checked again, and in the case of `transfer_filter.py`, watched through to a complete
classification of all four Hunt B candidates:

- **Hunt A's `census_run.py`** kept running after `SEED_CENSUS.md` was written (n=674 there) and
  reached **n=2100** (seed-order-consumed 2112/65536, elapsed 3889s of its 10200s budget) before the
  background process stopped running (no `census/CENSUS_DONE` marker was written -- the process is no
  longer alive; whether it exited cleanly at some other stopping condition or was reaped by the box is
  not established here, and is flagged for a follow-up session, not glossed over). This run **found
  one real STALL** at seed 30999 that did not exist in `SEED_CENSUS.md`'s 674-seed snapshot -- see
  §1.1. `replay_failures.py` was re-run against it to attach a fatal-board fixture (already existed in
  the codebase for exactly this purpose, not written new here). **This candidate has NOT been
  transfer-filtered** -- a follow-up session should do that before treating it as more than a
  candidate.
- **`transfer_filter.py`** (the structural-vs-fluke perturbation battery for Hunt B's 4 candidates)
  was watched through to completion for all four candidates' 5-category perturbation batteries:

  | candidate | primary metric | categories survived | verdict |
  |---|---|---|---|
  | `ga_near_spawn_a` | dies_ahead | 1/5 (timing_jitter only) | **FLUKE** |
  | `ga_near_spawn_b` | dies_ahead | 2/5 (history-shift, timing_jitter) | **FLUKE** |
  | `honest_shape_spawn_target` | dies_ahead | 2/5 (neighbouring-seeds, timing_jitter) | **FLUKE** |
  | `always_spawn_max` | topout | 5/5 (every category survived) | **STRUCTURAL** |

  `always_spawn_max` went 5/5 -- every perturbation category, including the ones evaluated after the
  majority threshold was already reached, survived cleanly. The predecessor A/B (`ws=0` vs `ws=20`,
  gated on a STRUCTURAL verdict per `transfer_filter.py`'s own design) was in progress for
  `always_spawn_max` -- the only qualifying candidate -- when this document was finalized.
  `transfer_filter_result.json` will exist once that finishes; see §6 for the resume check. **This
  document's own `fixtures/runner.py --ws 0` spot-check (§4.1) independently ran a version of that same
  predecessor question on all 5 fixtures and is reported there, not withheld pending the official run
  -- it agrees with the direction the official run is expected to confirm for `always_spawn_max`
  specifically (fails under both configs, i.e. long-standing, not strand20-introduced).**

This document's headline and taxonomy status labels below reflect this complete-for-Hunt-B state, not
the as-written state of the three input reports alone.

---

## 1. TAXONOMY

Three named structural failure modes are documented below, each with its mechanism in plain language,
its evidence (seeds/schedules, n, rates), and its **transfer-filter status** -- CANDIDATE
(single/small-n sighting, not yet perturbation-tested), STRUCTURAL (survived >=3/5 perturbation
categories), or FLUKE (did not).

### 1.1 `buried_virus_stall` -- a single virus sealed behind the champion's own tower

**Mechanism (plain language):** the champion plays a clean, no-pressure game and clears 47 of 48
viruses without incident, but leaves the 48th buried at the bottom of a narrow well it built for
itself over the course of the game. By the time only that one virus remains, none of the 32 legal
`(variant, col)` base-search actions can deliver a matching-color half down into the well without
first being blocked by material the champion itself already stacked on top of it. The search does not
get stuck in the sense of finding no legal move (that would be TOPOUT) -- it keeps finding *legal,
useless* placements elsewhere on the board for the full 300-pill cap. Result: **STALL**, not TOPOUT.
This is the concrete, first-observed instance of a blind spot this project already had an open item
for -- task #47, "Abandoned-material blind spot: price unmatchable halves in the leaf eval" -- the
leaf eval has no term that prices a half it cannot currently reach as a liability, so it happily
keeps placing pills that do nothing for the one cell that matters.

**Evidence:** seed **30999**, `census_run.py`'s background continuation of Hunt A (seed-order index
consumed 2112/65536 at time of discovery, shuffle_rng_seed=20260806). `result=stall`, `pills=300`,
`viruses_left=1`, `dies_ahead=false` (STALL and DIES_AHEAD are disjoint categories in the house
taxonomy -- this is not a dies-ahead event). **n=1.**

**A cross-config observation (n=1, not a claim):** replaying this exact fixture through
`fixtures/runner.py --ws 0` (the pre-#47 predecessor decide path, no `g_stranded` term) **clears
cleanly** (`pills=101, viruses_left=0`) instead of stalling -- see §4.1.

**Status: CANDIDATE.** Per the honesty rules ("a failure found on ONE seed is a candidate, never a
finding, until it passes the transfer filter"), this is exactly that: one seed, not yet run through
neighbouring-seed / history-shift perturbation. It is queued as fixture
`fixtures/fx_hunt_a_buried_virus_stall_30999.json` for a follow-up session's transfer-filter run --
see §3 for the falsifiable proposal this motivates regardless of transfer-filter outcome (the
mechanism is independently plausible and already tracked as an open eval gap; the fixture's job is to
confirm it's not a one-off coincidence of this specific seed's geometry).

### 1.2 `garbage_column_targeting` -- aiming volleys at the spawn lane (large on its own holdout block, but FLUKE under structural transfer)

**Mechanism (plain language):** Hunt B's adversarial garbage scheduler searched over *when* to fire a
follow-up volley after the champion's own clears, *how big* the volley is, and *which columns* it
targets -- all within the same total-garbage budget (53 halves/game) a real human sender produces on
average. Every GA run independently converged on the same lever: **aim near the spawn columns (3,4),
not randomly** -- and that one change, even holding the real human-observed timing/size shape fixed
(`honest_shape_spawn_target`), reproduces most of the effect on its own n=120 holdout block. The
theorized mechanism: garbage landed near the spawn lane raises the floor directly under where new
pills must land, so the champion's own placements toward the endgame increasingly have to choose
between clearing a virus and keeping the spawn lane clear -- eventually it can't do both and dies
**while still holding viruses**, the DIES_AHEAD signature specifically (not a raw pile-up TOPOUT).

**Evidence (as reported in `ADVERSARIAL_PRESSURE.md`, n=120 holdout, seeds 5,000,000-5,000,119, disjoint
from the n<=36 GA training pool at 4,000,000+):**

| schedule | dies-ahead (n=120) | topout | avg garbage/game |
|---|---|---|---|
| honest v1.1 random (control) | 2.5% [0.0, 5.3] | 3.3% | 42.4 |
| `ga_near_spawn_a` | 32.5% [24.1, 40.9] | 65.8% | 35.1 |
| `ga_near_spawn_b` | 28.3% [20.3, 36.4] | 80.8% | 32.2 |
| `honest_shape_spawn_target` | 24.2% [16.5, 31.8] | 46.7% | 27.2 |

**Status: FLUKE, all three candidates, confirmed.** This is the load-bearing correction this document
makes to `ADVERSARIAL_PRESSURE.md`'s own framing, and the most important honest negative in this whole
program. The n=120 holdout table above is real (a genuinely disjoint re-run, not the GA's own training
numbers) -- but the holdout itself is *one* fixed seed block, and the structural-transfer-filter
battery (`transfer_filter.py`) asks a sharper question: does the *same* schedule still beat the honest
baseline on a **different, adjacent** seed block, on the **same** seed with its pill history shifted by
one draw, and under small timing/column/volley-size jitter? For all three candidates the answer is no:

| candidate | [a] neighbour seeds | [b] history-shift | timing_jitter | column_jitter | size_jitter | survived | verdict |
|---|---|---|---|---|---|---|---|
| `ga_near_spawn_a` | False | False | **True** | False | False | 1/5 | FLUKE |
| `ga_near_spawn_b` | False | **True** | **True** | False | False | 2/5 | FLUKE |
| `honest_shape_spawn_target` | **True** | False | **True** | False | False | 2/5 | FLUKE |

`honest_shape_spawn_target` was, a priori, the theoretically strongest candidate -- it holds the real
human-observed timing/size shape fixed and isolates targeting alone, a board-geometry mechanism that
should be *less* seed-specific than a GA-tuned numeric shape. **That expectation did not hold**: even
the targeting-only isolation manages only 2/5, the same as the more overfit `ga_near_spawn_b`. The
honest reading: the n=120 holdout's non-overlapping confidence intervals were a real, reproducible
effect **on that specific seed block**, not evidence of a general weakness in the champion's handling
of spawn-lane pressure. `column_jitter` and `size_jitter` failed for all three candidates without
exception -- worth flagging as its own pattern (the schedules are surprisingly brittle to exactly
*where* in the column/size space the garbage lands, which cuts against "the champion can't handle
spawn-lane pressure in general" and toward "these specific genomes found a narrow seed-dependent
groove").

### 1.3 `overwhelm_max_pressure` -- maximal, unconditional garbage buries the champion early (the ONE structurally-confirmed exploit in this document)

**Mechanism (plain language):** firing every possible volley at maximum observed size, aimed at spawn,
after every single clear -- the crudest, most obvious "just send everything" schedule. It is
devastating on raw TOPOUT but *worse than the honest baseline* on DIES_AHEAD specifically: it buries
the champion outright, early, while it is still holding many viruses, rather than reproducing the
"dies on the doorstep of clearing" signature. This was already `ADVERSARIAL_PRESSURE.md`'s own
documented negative (§2.3) for dies-ahead -- what this document adds is that, scored on its own correct
metric (topout, not dies-ahead), **it is the one candidate that survives the structural transfer
filter.**

**Evidence:** `always_spawn_max`, n=120 holdout: topout 95.8% [92.1,99.6] vs. honest baseline topout
3.3%, dies-ahead 0.8% [0.0,2.5] vs. honest baseline dies-ahead 2.5% (worse than honest -- see §1.2's
sibling report for why dies-ahead is the WRONG metric for this mode). Structural transfer filter
(topout_rate as primary metric, per `transfer_filter.py`'s own candidate table):

| category | rate | local honest baseline | survives |
|---|---|---|---|
| [0] baseline capture (unperturbed) | 97.5% [87.1,99.6] | 5.0% | -- |
| [a] neighbouring seeds (fresh 40-seed block) | 90.0% [76.9,96.0] | 2.5% | **True** |
| [b] history-shift (skip=2, 15 fatal seeds) | 93.3% [70.2,98.8] | 0.0% | **True** |
| timing_jitter | 100.0% [91.2,100.0] | 5.0% | **True** |
| column_jitter | 55.0% [39.8,69.3] | 5.0% | **True** |
| size_jitter | 82.5% [68.0,91.3] | 5.0% | **True** |

**Status: STRUCTURAL -- 5/5 perturbation categories survived, the cleanest sweep of any candidate
tested in this document.** This is a genuine, robust, transfer-filter-confirmed
weakness -- but it is a *topout/bury* weakness under near-maximal sustained pressure, not the
doorstep-of-clearing DIES_AHEAD signature the task names first. Both are real failure modes and both
belong in the regression suite (a future eval change that fixes `garbage_column_targeting`-style
precision-aim dies-ahead but regresses under raw sustained overwhelm would be a real regression this
fixture would catch) -- but this document is explicit that **`overwhelm_max_pressure`, not
`garbage_column_targeting`, is the one arm of Hunt B that survived contact with the transfer filter.**

---

## 2. Silicon caveat (read this before treating ANYTHING above as a hardware finding)

**Every exploit above was found in the offline py65 simulator.** This project's own
`dr-mario-canonical-wt/CANDIDATE_TIER3.md` §10 measured, on 30 fresh real-L11 boards, that the offline
py65 base-search's chosen `(col, orient)` move agrees with the real Verilator/RTL base search on only
**4/30 (13.3%)** of moves -- i.e. **the offline sim and real silicon disagree on ~87% of base-search
moves.** Column-only agreement (23.3%) and orientation-only agreement (26.7%) are both close to what
independent near-random tie-breaking would produce -- there is no consistent skew that would let you
"mentally correct" a sim result into a silicon prediction. `CANDIDATE_TIER3.md` §10's own conclusion
is blunt: "py65 cannot currently be trusted as an oracle for the *base* search's decision on arbitrary
boards, real or synthetic" and "the silicon A/B is therefore not optional confirmation -- it is the
only real measurement of this candidate that exists." That conclusion applies with full force to every
fixture in this library: **none of them are silicon findings. They are offline-sim findings that name
a specific, minimal, replayable scenario worth spending Verilator co-sim time on.** A fixture "passing"
(reproducing its documented failure) against the py65 harness says nothing about what the RTL board
would do on the same seed/schedule -- with an 87% per-move disagreement rate compounding over a
multi-pill sequence, the RTL trajectory very likely diverges from the py65 trajectory before the
fixture's fatal moment is even reached. **Being STRUCTURAL under this document's offline
transfer-filter (§1.3) means "robust across offline perturbations of the offline sim" -- it does NOT
mean "confirmed on hardware."** That confirmation is what §2.1 below is for.

### 2.1 Top 3 fixtures to validate on the Verilator co-sim first

Ranked by "cheapest to run × most informative if it survives":

1. **`fx_hb_always_spawn_max_seed5000001.json`** -- the one STRUCTURAL exploit in this document (§1.3).
   Highest prior of surviving contact with RTL simply because its offline effect size is enormous
   (90-100% topout across every perturbation tested, vs. a 2.5-5% honest baseline) -- an 87% per-move
   disagreement rate is far less likely to erase a ~35x effect than it is to erase the ~2x effects
   `garbage_column_targeting`'s candidates showed even before they failed the offline filter. If this
   fails to reproduce on RTL, that is itself the headline finding of a follow-up silicon session.
2. **`fx_hunt_a_buried_virus_stall_30999.json`** -- single seed, no pressure, no schedule RNG to
   reconcile -- the cheapest possible co-sim run (one game, no adversary injection logic to port).
   The `--ws 0` observation in §1.1/§4.1 (predecessor clears, champion stalls) makes this doubly
   interesting: if RTL's `ws=20` also stalls where `ws=0` doesn't, that's a real regression signal
   worth escalating; if RTL clears at `ws=20` too, the py65 stall was sim-specific.
3. **One `honest_shape_spawn_target` fixture** (`fx_hb_honest_shape_spawn_target_seed5000000.json`) --
   included even though §1.2 found it FLUKE offline, specifically *because* it's the most mechanistically
   defensible of the three FLUKE candidates (board-geometry, not tuned-policy) and RTL's different move
   choices could in principle make a board-geometry effect MORE reliable on silicon than it was in the
   fragile offline sim. Absence of an offline structural signature is evidence about *the py65 sim's*
   version of the champion, not dispositive evidence about hardware.

Do not promote any of these from "fixture" to "silicon finding" without an actual co-sim run and its
own n/CI, per the same honesty rules as everything else in this document.

---

## 3. PROPOSALS (falsifiable, NOT implemented)

For each failure mode, the cheapest plausible fix and the experiment that would test it -- named, not
built.

### 3.1 For `buried_virus_stall` (§1.1)

- **Proposal:** add an "abandoned/unreachable material" penalty term to the leaf eval -- a half whose
  color has zero remaining reachable matching cells (or whose reachable matches all require moves the
  search's own horizon can't see) is priced as a standing liability proportional to how buried it is
  (e.g. rows of same-or-taller neighbor material stacked above it), not as a neutral placement. This
  is exactly the gap task #47 already names.
- **Test:** re-run `census_run.py`'s remaining seed-space budget (or the exact-precision fixture scan
  used in §2.1) with the eval candidate swapped in, holding the schedule/pressure model fixed, and
  check whether seed 30999 (and any other STALL/high-pills-to-clear seeds the completed census
  surfaces) newly clears within the 300-pill cap. A single-seed pass/fail is not sufficient on its own
  -- pair it with a no-regression check against `REACH_ROOT_CLEAN.md`'s existing 99.2%-clear n=120
  reference set (same house standard used throughout this program) to confirm the new penalty term
  doesn't cost clear rate elsewhere by making the search over-cautious about ordinary (reachable)
  buried material. **Also run this fixture's `--ws 0` cross-config observation (§4.1) as a sanity
  check first**: since the pre-#47 predecessor already clears this exact seed, part of the
  experiment should determine whether `g_stranded` at ws=20 is itself contributing to the stall
  (a candidate root-cause, not assumed) before designing a new penalty term to patch around it.

### 3.2 For `garbage_column_targeting` (§1.2) -- now a LOWER-priority proposal given the FLUKE verdict

- **Proposal (still worth naming, de-prioritized):** a lightweight "spawn-lane guard" term in the
  root-only eval addition (analogous in spirit to how `g_stranded` is already applied root-only at
  ws=20) that adds a small penalty for placements that raise column-3/column-4 height above a
  threshold when the board is under active pressure (garbage landed in the last N pills). Given §1.2's
  FLUKE verdict, this proposal's justification is now weaker than it looked in `ADVERSARIAL_PRESSURE.md`
  alone -- the mechanism may still be real (board geometry doesn't stop being true because a specific
  seed block's exploit didn't generalize), but there is no longer a structurally-confirmed offline
  finding motivating it. Treat as speculative until either (a) a silicon A/B on the fixtures in §2.1
  surfaces a real effect, or (b) a wider/different seed-block re-run of `honest_shape_spawn_target`
  finds a signature the original 5,000,000-5,000,239 blocks didn't.
- **Test:** before building the guard term, first re-run `honest_shape_spawn_target` (the most
  defensible of the three) against a THIRD, larger, disjoint seed block (e.g. 5,000,500-5,000,999,
  n>=200) to see whether a bigger sample surfaces the CI separation the 40-seed perturbation categories
  couldn't. If that larger re-run also fails to separate from the honest baseline, this proposal should
  be shelved, not implemented -- a documented negative, not a manufactured target.

### 3.3 For `overwhelm_max_pressure` (§1.3) -- now the higher-priority proposal given the STRUCTURAL verdict

- **Proposal:** a driver-side hard constraint -- "never let column 3 or 4's stack height exceed row R"
  as a placement veto (not an eval penalty; a legality filter on the search's own candidate moves) when
  the recent-pills garbage-injection rate exceeds a threshold. This is deliberately a DIFFERENT
  mechanism from 3.2's soft eval penalty: `always_spawn_max`'s own report section already showed
  dies-ahead and topout are different levers, so a soft penalty tuned for the (FLUKE) dies-ahead mode
  is not assumed to transfer to this (STRUCTURAL) topout mode without its own test.
- **Test:** re-run `always_spawn_max` (and, once/if a wider re-run surfaces one, whichever
  `garbage_column_targeting` schedule holds up) against the eval+driver candidate on a fresh seed block
  disjoint from every block already spent in this program, holding budget/model fixed, scored against
  `always_spawn_max`'s own topout_rate (95.8% baseline-under-champion, 90-100% across every
  perturbation tested in §1.3). This is the highest-priority experiment in this proposals section
  precisely because it is the only one motivated by a structurally-confirmed (if still silicon-unverified)
  offline finding rather than a fluke.

---

## 4. FIXTURE LIBRARY

`fixtures/` (this directory): each structural-exploit candidate as a minimal, deterministic
reproducer plus `runner.py`, a driver that replays ANY fixture against ANY decide-path `ws` dose
(20 = shipped strand20 champion, 0 = pre-#47 predecessor -- the only two configs this program's
decide path (`reach_root.choose_base32`) currently exposes as an interchangeable knob; extending the
runner to a genuinely different eval/leaf variant is out of scope here and named as a gap, not
silently assumed away).

See `fixtures/README.md` for the fixture JSON schema, exact file listing, and `runner.py` usage
(`python runner.py`, `python runner.py --ws 0`, `python runner.py --json`). Every fixture is fully
reproducible from `(seed, schedule, ws, budget_halves, max_pills)` alone -- no board/trace blob is
read as an input; any `fatal_board`/`opening_board` field present is documentation captured at
discovery time, not a runner input. Exit code 0 iff every fixture's actual outcome matches its
`expected` block -- CI-usable, "every future core must pass this regression suite" per the task brief.

Fixtures currently in the library, all verified `5/5 PASS` against the shipped `ws=20` champion:

| file | family | seed | status |
|---|---|---|---|
| `fx_hunt_a_buried_virus_stall_30999.json` | buried_virus_stall | 30999 | CANDIDATE, n=1, not transfer-filtered |
| `fx_hb_ga_near_spawn_a_seed5000000.json` | garbage_column_targeting | 5000000 | FLUKE, 1/5 |
| `fx_hb_ga_near_spawn_b_seed5000001.json` | garbage_column_targeting | 5000001 | FLUKE, 2/5 |
| `fx_hb_honest_shape_spawn_target_seed5000000.json` | garbage_column_targeting | 5000000 | FLUKE, 2/5 |
| `fx_hb_always_spawn_max_seed5000001.json` | overwhelm_max_pressure | 5000001 | **STRUCTURAL, 5/5** |

Every Hunt-B fixture's genome is pulled at FULL float precision from `validate_result.json`'s own
"candidates" dict via `find_fixture_seeds_exact.py` (this directory) -- `best_schedules.json`'s own
"genome" field is rounded to 3 decimal places for readability, and a spot check found this rounding
flips the outcome for 1/120 holdout seeds (78 vs. 79 topouts under `ga_near_spawn_a` on an otherwise
-identical 120-seed scan). Fixtures here bit-exactly reproduce the numbers actually reported in
`ADVERSARIAL_PRESSURE.md` §2, not a rounded approximation of them.

### 4.1 A finding this fixture library surfaced on its own: `ws=0` vs `ws=20` cross-config check

Running `fixtures/runner.py --ws 0` against all 5 fixtures (a cheap A/B this library makes trivial,
independent of `transfer_filter.py`'s own gated predecessor A/B which was still running for
`always_spawn_max` at the time of writing) found:

| fixture | `ws=20` (champion) | `ws=0` (predecessor) |
|---|---|---|
| `fx_hunt_a_buried_virus_stall_30999` | stall (fails per its mechanism) | **clear** (pills=101) |
| `fx_hb_ga_near_spawn_a_seed5000000` | topout, dies_ahead (fails) | topout, dies_ahead (fails) |
| `fx_hb_ga_near_spawn_b_seed5000001` | topout, dies_ahead (fails) | topout, dies_ahead (fails) |
| `fx_hb_honest_shape_spawn_target_seed5000000` | topout, dies_ahead (fails) | **clear** (pills=107) |
| `fx_hb_always_spawn_max_seed5000001` | topout, viruses_left=21 (fails) | topout, viruses_left=21 (fails) |

**3 of 5 fixtures fail under BOTH configs (long-standing, not strand20-specific). 2 of 5
(`buried_virus_stall` and the `honest_shape_spawn_target` seed) fail ONLY under `ws=20` and CLEAR
under the pre-#47 predecessor.** This is `n=1 per fixture`, not a holdout claim -- but it is exactly
the "long-standing weakness vs. strand20-introduced regression" question `TRANSFER_FILTER.md` §2.2
designed its own gated predecessor A/B to answer, and on these two specific seeds it points the same
direction: **`g_stranded` at ws=20 is a plausible (not proven) contributor to both failures.** Named
here as a candidate observation motivating §3.1's proposed sanity check, not asserted as a finding --
a proper paired A/B (same seed pool, both configs, n and CI) is the actual test.

---

## 5. Honesty-rule bookkeeping

- **n reported for every rate** above and in every source report cited.
- **Nothing here claims silicon status** -- §2 is read-first and prominent per the task brief, and
  every fixture's JSON carries its own `silicon_status` field saying the same thing.
- **The headline number from `ADVERSARIAL_PRESSURE.md` is explicitly downgraded, not repeated**: the
  "13x" `ga_near_spawn_a` dies-ahead number is real on its own n=120 holdout block (non-overlapping
  CIs, genuinely disjoint from training) but does NOT survive the structural perturbation battery (1/5,
  and neither do the other two dies-ahead candidates at 2/5 each) -- this document reports that as a
  finding in its own right (a documented negative sitting on top of a documented positive), not a
  discrepancy to paper over. The ONE candidate that IS structural (`always_spawn_max`) is explicitly
  the one the source report's own §2.3 already said was the wrong lever for dies-ahead -- so even the
  structural finding does not vindicate the "13x dies-ahead" headline; it confirms a different,
  cruder failure mode instead.
- **`buried_virus_stall` is explicitly labeled CANDIDATE, not FINDING** -- one seed, not yet
  perturbation-tested. It is included because the task asks for a taxonomy of what survivors exist and
  a fixture library to test them against, not only fully-validated findings, and because the mechanism
  independently matches an already-open project item (#47).
- **The `ws=0`/`ws=20` cross-config table in §4.1 is explicitly n=1-per-cell** -- flagged as an
  observation motivating a real experiment (§3.1), not itself a paired-A/B finding.
- **Reuse audit:** `fixtures/runner.py` imports and calls `adversary_harness.play_seed` /
  `adversary_search.play_seed_adversarial` directly -- no board-mutation or decide-path logic is
  reimplemented. `find_fixture_seeds_exact.py` reuses `adversary_search.py`'s own
  `SIZE_POOL`/`BINS`/`_worker_init`/`play_seed_adversarial`, only rebuilding the genome dict from
  `validate_result.json`'s existing float fields (no new RNG or board mechanics). The perturbation
  categories and CI-separation survival rule are `transfer_filter.py`'s own (read from its live log
  output, not re-derived).

## 6. Files

- `ADVERSARY_FINDINGS.md` -- this document.
- `fixtures/` -- the reproducer library + `runner.py` + `README.md` (see §4).
- `find_fixture_seeds_exact.py` -- the exact-precision genome scanner used to pick fixture seeds;
  reusable for any future fixture (e.g. once Hunt A's census resumes and surfaces more STALL/TOPOUT
  seeds).
- `census/failures_with_boards.json` -- seed 30999's full fixture material (fatal board, opening
  board, 20-pill prefix, signature features), produced by re-running the pre-existing
  `replay_failures.py` (not new code) against the census's own live `failures_seen.jsonl`.
- `transfer_filter_result.json` -- will exist once `always_spawn_max`'s gated predecessor A/B
  finishes (its own perturbation battery is complete, 5/5); check `pgrep -af transfer_filter.py` /
  this file's existence in any follow-up session. `tmp_logs/transfer_filter_run.log` has the full
  live transcript this document's §0/§1.2/§1.3 tables were read from in the meantime.
