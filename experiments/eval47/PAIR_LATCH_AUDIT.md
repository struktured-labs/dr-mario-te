# Pair-latch commit-path guard — design proposal (2026-08-04)

Scope: read-only audit across `dr-mario-canonical-wt` (`copro-canonical`/`eval47-strand`,
HEAD `64f3860`, the confirmed source of the Pocket `nes.rev a0d5190f` build via
`fpga/copro/sync_to_pocket.sh`) and `dr-mario-mods-wt/driver-nav` (branch `driver-nav`,
clean, up to date with `origin/driver-nav`). No edits made to either tree. This file and
its evidence live entirely under `dr-mario-qa-wt/experiments/eval47/`.

## 0. Presence verdict (confirmed, not re-litigated)

**ABSENT from the shipped Pocket build, PRESENT and independently verified working on
`driver-nav`.** This matches the film-review adjudication passed into this task and the
prior `PAIR_LATCH_CANONICAL_AUDIT.md` in this same directory; I re-verified the load-bearing
claims directly rather than trusting either account:

- `dr-mario-canonical-wt/patch_cartridge_copro.py:968-998` (`dn_p2`): the confidence-gated
  slam is wrapped in a Python-level `if NO_FREEZE:` (build-time codegen, not a 6502 runtime
  branch). Since `DRNOFREEZE` defaults to `"0"` (`patch_cartridge_copro.py:106-110` on that
  tree), the gated block is **never assembled** into a `NO_FREEZE=0` cart — which is every
  Pocket/freeze-class build, confirmed by direct read of the file, not inference.
- `dr-mario-mods-wt/driver-nav/patch_cartridge_copro.py:277-285` (`COLGATE`) and `:1621`
  (`if NO_FREEZE or COLGATE:`) carry the fix that extends the same gate to `ROTFIX`
  (freeze-class) carts, default-ON. `:352-1361` implement `RECOMMIT` (default-ON on
  freeze-class carts, `:409-411`).
- Ran the existing regression, `driver-nav/tests/test_pocket_placement.py`, via
  `uv run --with py65 python3 tests/test_pocket_placement.py` (uv, not raw pip, per
  house convention) — **4/4 PASS**, confirmed live in this session, not taken on faith:
  ```
  1 COLGATE hold   : fixed DOWN=False  pre-fix DOWN=True
  2 RECOMMIT high  : fixed ROT_DONE2(Y=hi) = 0  (re-opened)
  3 RECOMMIT low   : fixed ROT_DONE2(Y=lo) = 1  pre-fix(Y=hi) = 1  (both keep/never-reopen)
  4 byte-exact AB  : NO_FREEZE=1 build identical with/without the flags
  ==== 4/4 checks passed ====
  ```
- `git merge-base --is-ancestor 3e8500e HEAD` from `dr-mario-canonical-wt` → **no** (exit
  1) — the fix commit is not an ancestor of the checkout that built `a0d5190f`.

So the task here is not "invent a guard from nothing" — a stronger guard already exists,
is tested, and is byte-exact-safe on the validated MiSTer AB control. The design work below
is: (1) show it actually covers candidates A/B/C, (2) recommend the port + provenance fix
rather than a new mechanism, (3) do the freeze-exposure analysis the task asks for, since
that analysis does not exist yet for this specific gate.

## 1. Chosen mechanism

**Port `driver-nav`'s `COLGATE` + `RECOMMIT` + phase-aware stability gate
(`K_OPEN`/`K_END`/`K_CROSS`/`CROSS_LOWY`) into the `copro-canonical`/`eval47-strand`
lineage that `sync_to_pocket.sh` actually vendors, with `DRROTFIX=1 DRCOLGATE=1
DRRECOMMIT=1 DRSLAM=1` as the shipping defaults** — the same defaults already validated
on `driver-nav`. This closes the gap by forward-porting a proven fix, not by adding new
logic.

Sketch of the mechanism (already-shipped code, file:line on `driver-nav`):

```
# act_p2 (driver-nav:1527-1550) — argmax-stability tracker, runs every hook post-settle:
if (TGT_C2, TGT_O2) != (LAST_COL2, LAST_ORI2):
    LAST_COL2, LAST_ORI2 = TGT_C2, TGT_O2
    STABLE_CT2 = 0                      # argmax moved -> must re-earn confidence
else:
    STABLE_CT2 = min(STABLE_CT2 + 1, 0xFE)

# act_p2_n (driver-nav:1553-1593) — orient pre-phase + RECOMMIT-eligible commit:
if ROT_DONE2 == 0:
    if orient != TGT_O2: rotate_toward(TGT_O2); return    # live gravity, no pin
    if DONE or WDOGH2>0 or (SLAM and Y<CROSS_LOWY and SLAM_ARM) or WDOG2>=MIN_THINK:
        ROT_DONE2 = 1                    # orient LOCKS here (unavoidably, some builds early)

# on DONE (idx==2 handler, driver-nav:1352-1361) — RECOMMIT:
if RECOMMIT and ROT_DONE2==1 and Y >= CROSS_LOWY and converged_orient != current_orient:
    ROT_DONE2 = 0                        # re-open: capsule still high enough to rotate safely
                                          # act_p2_n above will rotate once more, then re-lock

# dn_p2 (driver-nav:1620-1649) — column commit, COLGATE-gated:
if NO_FREEZE or COLGATE:
    if DONE: drop()                                  # unchanged ceiling
    elif Y < CROSS_LOWY: need = K_CROSS               # feasibility crossover: DONE physically
                                                       # unreachable before lock -> minimal bar
    elif virus_count < VC_ENDGAME: need = K_END        # =255 -> DONE-only
    else: need = K_OPEN                                # =255 -> DONE-only
    if STABLE_CT2 >= need: drop()
    else: hold()                          # NO button pressed; capsule still falls at gravity —
                                           # this is a "don't accelerate", never a "don't fall"
else:
    drop()                                # canonical's unconditional LDY #4 (the defect)
```

**Mapping onto the task's candidate mechanisms — this already synthesizes A+B, and
partially covers C:**

- **(A) column re-arm on DONE** — the column half of this is *already* unconditional and
  present on canonical too: `nf2` (`driver-nav:1494`, mirrored on canonical at
  `:838-880` per the prior audit) writes `TGT_C2` from the live mailbox every hook
  regardless of lock state — "column: always refine (anytime)". So A alone would not
  have closed the gap: the film-review signature is not "the column value is stale," it's
  "the column value is *fresh but not yet converged* (the running argmax) and nothing
  gates the drop on convergence." COLGATE supplies exactly that missing gate. The orient
  side of A (re-arm on DONE) *was* genuinely missing on canonical — that is what
  `RECOMMIT` adds, self-gated to fire only when doing so is safe (`Y >= CROSS_LOWY`, no
  backwards-lock).
- **(B) bounded fallback commit** — implemented, but keyed on the *physical* fall-time
  budget (`CROSS_LOWY`, a board-row threshold) rather than a fixed frame count `N`. This
  is a deliberate improvement over "pick N from the 20-95f window": a single global frame
  timeout is either too short for the slowest legitimate searches (forcing exactly the
  premature commit this bug is about) or too long to matter once the capsule is a few rows
  from the floor at fast gravity/late levels. `CROSS_LOWY` reduces to "how many rows of
  fall remain before DONE becomes physically unreachable," which auto-adapts to gravity
  speed instead of hard-coding a frame count that would need re-deriving per level/L11
  speed table (`dr-mario-gravity-table` memory: gravity is a table, not a constant).
- **(C) latch invalidation on board-height change near spawn** — partially covered:
  `STABLE_CT2` resets to 0 whenever the *argmax itself* changes (`p2_st_chg`,
  `driver-nav:1546-1549`), which is what a board reflow near spawn would produce (new
  clears/garbage change the search's best answer). A board-height trigger *independent* of
  an argmax change is not implemented and, given the above, is not needed: the failure
  mode C targets (stale commit after the board moved) is already a strict subset of "the
  published argmax hasn't been stable for K hooks," which COLGATE already gates on
  directly. Flagged as a nice-to-have, not a gap that changes the recommendation.

## 2. Rejected alternatives

1. **Pure (A), column-only re-arm, no confidence gate.** Rejected: the column is already
   live-refreshed on canonical (confirmed above); the film-review signature is a
   convergence problem, not a staleness problem. A-only ships no fix for the actual defect.
2. **Pure (B) with a fixed global frame timeout `N` (from the observed 20-95f window).**
   Rejected: this is structurally the *same* mistake as the original `MIN_THINK=90`
   (~18f) global floor, which the project already measured to be pure tempo loss with zero
   placement benefit once `K_OPEN=255`+`RECOMMIT` are in place (task #40 sweep,
   `driver-nav:240-243`: "placement stays OPTIMAL at floor {90,45,25,0}; only tempo
   moves"). A hand-picked `N` from one 6-death sample window is exactly the kind of
   constant that needs re-deriving every time gravity/search-latency changes (memory:
   `dr-mario-worse-than-weekend-causes` — a similar hard-coded timing assumption was a
   prior regression cause). `CROSS_LOWY` (a position, not a duration) sidesteps that by
   construction.
3. **New RTL-side fix (touch `CoproDrMario.sv`'s DONE/mailbox cadence, or the GO
   pulse).** Rejected outright: the defect is 100% driver-side — the RTL only ever
   publishes `best_col`/`best_orient`/`DONE` into the fixed `$5084-$5086` window; the race
   is in when and how the 6502 driver *reads and commits* that window, confirmed by the
   fact that the fix that closes it (`COLGATE`/`RECOMMIT`) touches zero RTL files. Touching
   RTL here would (a) violate this task's read-only-RTL-trees constraint, (b) risk the
   `clk85` async-CDC group the project has flagged as never-retune, for a bug that isn't
   there.
4. **(C) as the primary mechanism instead of a confidence gate.** Rejected as primary:
   it's reactive to a *symptom* (board changed) rather than the actual invariant that
   matters (has the argmax been stable long enough to trust). A board-height trigger would
   miss the exact film-review pattern where the board does *not* change near spawn but the
   search simply hasn't converged yet (opening pill on a mostly-empty board — 4/6 of the
   death commits had zero lateral movement with no board reflow implicated in VERDICT.md).

## 3. Freeze-exposure analysis (required by the task, not present in prior audits)

Constraints from project memory: copro clock is its own async CDC group (never retune);
driver runs 2×/frame in NMI; GO-storm re-entrancy and stale-ARMED2 are known adjacent
defect classes; CMD-8 already ~doubled GO traffic and is prime suspect for the s20b
freezes; DRBUSYESC exists for BUSY-latch escapes.

- **No GO-traffic widening.** Verified by direct grep: the *only* `STA_abs wgo` write in
  `driver-nav/patch_cartridge_copro.py` is at line 1420, inside the search-launch routine
  (`build_main`'s per-player DONE/RESULT teardown → new search), which is untouched by
  this change. `COLGATE`, `RECOMMIT`, and the `STABLE_CT2` tracker only read the
  already-published mailbox (`$5085`/`$5086`, via `TGT_C2`/`TGT_O2`) and driver-local RAM
  (`ROT_DONE2`, `STABLE_CT2`, `LAST_COL2`/`LAST_ORI2`, `SLAM_ARM`) — zero new copro
  commands, zero new GO pulses. This mechanism is structurally orthogonal to the CMD-8/
  GO-storm suspect class, not merely "probably fine."
- **Byte-exact on the validated control.** Regression scenario 4 (re-run live this
  session) proves the `NO_FREEZE=1` (MiSTer AB) build is bit-for-bit identical whether
  `DRCOLGATE`/`DRRECOMMIT` are on or off — the change cannot regress the already-shipped
  MiSTer AB baseline; its entire effect surface is `ROTFIX and not NO_FREEZE`, i.e.
  Pocket/freeze-class carts only.
- **No new hang surface.** When the confidence gate is unmet, `dn_hold`
  (`driver-nav:1646-1647`) does `LDY #0; STY $F6` — no button pressed, **no gravity pin**.
  The capsule keeps falling at whatever the level's gravity table dictates and locks
  naturally on collision; the gate only withholds the *forced* accelerated drop, it never
  blocks the game's own fall/lock. So even the worst case — `K_OPEN=K_END=255` (require
  DONE) combined with a search that never DONEs — degrades to "capsule falls at natural
  gravity and lands wherever it lands," not a hang. This is the same shape as the existing
  `MIN_THINK` tempo-only finding, not a new liveness risk.
- **Orthogonal to stale-ARMED2 / GO-storm / DRBUSYESC.** `RECOMMIT` only fires inside the
  DONE handler (`idx==2`, i.e. after `ARMED2` has already gone to 0 through the normal
  path, `driver-nav:1352`), so it cannot itself produce a stale-`ARMED2`. `COLGATE`/
  `RECOMMIT`/the stability tracker run downstream of `act_p2`'s existing `PEND2` settle
  guard (`:1533-1534`) and the re-entrancy/`BUSYESC` guard in `handle()`, which they never
  touch. These remain **open, unaddressed risks in their own right** (per memory: stale-
  ARMED2 is "best mechanism for freeze #56, unfixed") — this change neither fixes nor
  worsens them; it is scoped strictly to the post-entry steering/commit logic.
- **One real residual to flag, not a blocker:** `driver-nav`'s `DRSTALLWD` (a genuinely
  separate stall-watchdog covering "search wedged, not merely slow") defaults **OFF**
  (`:186`). It is unrelated to this gate (COLGATE/RECOMMIT never disable or interact with
  it) but should be considered together when this fix ships to Pocket, since a
  genuinely-wedged search plus `K_OPEN=255` (require DONE) means the *only* thing
  advancing the pill is natural gravity/fall-and-lock, with no accelerated escape — which
  is fine per the point above (not a hang) but is worth an explicit go/no-go decision
  rather than an implicit one when this ships.

## 4. Provenance gap (root cause of *why* the fix never reached Pocket)

Per the task's own verdict, `sync_to_pocket.sh` only ever copies RTL/firmware hex
(`cp "$SRC/$HEX" "$DST/$HEX"`) and never touches `patch_cartridge_copro.py` at all — the
Python driver source and its env-flag set for a given `.nes` build are not captured
anywhere traceable to the artifact hash (`a0d5190f` is unattributable in every tree
checked). Six divergent copies of `patch_cartridge_copro.py` exist across worktrees
(`canonical`, `main-wt`, `mods`, `playerstyles-wt`, `promote-wt`, `qa-wt`, `survey-wt`,
`te-v8`, `te-v8.2`, plus `driver-nav`) with no single source of truth. The mechanism fix
above does not by itself prevent a *repeat* of this exact gap (fix ships on one branch,
Pocket build comes from another) — that requires a build-provenance stamp (driver script
git commit + full `DR*` env-flag set, embedded in the `.nes` or logged alongside the
artifact hash) as a separate, non-RTL follow-up. Flagging per the task's own implication
section; not designed in full here as it's outside "commit-path guard" scope.

## 5. Test plan — prove the fix offline, before silicon

House rule: simulate the *defect* (the late-DONE / early-argmax race) and assert the
capsule commits to the search's converged column/orient, not merely that a guard flag
exists.

1. **Already-automated py65 regression (re-used, confirmed passing this session):**
   `driver-nav/tests/test_pocket_placement.py`, run via
   `uv run --with py65 python3 tests/test_pocket_placement.py` from
   `dr-mario-mods-wt/driver-nav`. Scenarios 1-3 directly simulate the defect states (searching
   + column-aligned + orient-locked + argmax-unstable; DONE-with-stale-latched-orient at
   high vs. low Y) and assert the *outcome* changes (no premature DOWN press; `ROT_DONE2`
   re-opens only when safe) between `DRCOLGATE=1 DRRECOMMIT=1` and the `=0` control — this
   is the defect-not-guard pattern the house rule requires, already implemented, already
   green. When porting to the canonical/eval47-strand tree, re-run this exact file
   unmodified against the ported driver to prove parity before any silicon step.
2. **New py65 harness case for the exact film-review signature:** construct a state that
   reproduces commit 6 from VERDICT.md — capsule at spawn column, `ARMED2=1` (still
   searching), a *shallow* running argmax equal to the spawn column (tape_rank 24/24
   condition: the true best is a *different* column that hasn't stabilized yet), then step
   the driver hook-by-hook across a simulated late convergence (mailbox column flips to the
   correct column at some hook `t`, `DONE` at `t+Δ`). Assert: (a) pre-fix drops at spawn
   column before `t`; (b) fixed build does **not** drop until `STABLE_CT2 >= K` post-flip
   or `DONE`, and lands on the *post-flip* column — i.e. assert the capsule goes to the
   search's column, per the house rule, not just that `$F6` stays 0 for one hook.
3. **Non-monotonic-timing regression:** VERDICT.md's own finding was that the shortest
   search window was worst and the 2nd-shortest was best — a race signature, not a
   compute-exhaustion one. Add a parametrized py65 case sweeping the DONE-arrival hook
   across a range (including *very* early, mimicking the shortest-window death) and assert
   commit-column correctness is now flat across that sweep (was previously a function of
   arrival timing), which is the falsifiable version of "this closes a race" rather than
   "this changes some numbers."
4. **Byte-exactness / no-GO-widening guard, made explicit and automated:** extend scenario
   4's hash check into an assertion runnable in CI: `NO_FREEZE=1` build hash must be
   invariant under `DRCOLGATE`/`DRRECOMMIT` toggles (already true, keep it a hard gate);
   additionally, `command grep -c 'STA_abs.*wgo\|ins16("STA_abs", wgo)' patch_cartridge_copro.py`
   (or an AST-level check on the generated instruction stream between the `COLGATE`/
   `RECOMMIT` code regions) should report the *same* GO-write count with the flags on vs.
   off, as a structural proof this class of change cannot be the thing that widens GO
   traffic in a future edit.
5. **Verilator co-sim cross-check (per `fpga/copro/run_gate.sh`), scoped correctly:** since
   the defect and fix are 100% driver-side, the RTL co-sim is not where the race lives —
   but it *is* the right tool to validate the timing inputs the driver logic depends on
   (`WDOGH2`/`FAST_HI` maturity thresholds, real search latency under `chain180` load) are
   still accurate on the actual silicon-clocked copro before trusting `CROSS_LOWY`/`K_CROSS`
   numbers derived from older latency measurements. Run `fpga/copro/run_gate.sh` (existing
   gate infra, e.g. `tb_strand`/`tb_seqfix` patterns) against the current strand20 firmware
   to re-confirm the `FAST_HI=2` (512-hook) threshold still classifies `chain180` searches
   as "fast" at today's latency before shipping — a stale threshold would silently disarm
   `SLAM_ARM` and fall back to the DONE-only path, which is safe but not the same tempo
   profile that was validated. This is a pre-ship sanity check on constants, not a defect
   reproduction, and should run *after* items 1-3 are green.

All of 1-4 are executable entirely off the read-only RTL trees (py65 + the driver Python
source only); only item 5 touches the verilator gate infra, and only to validate constants,
not RTL logic changes — consistent with the read-only-RTL-trees restriction on this task.

## 6. REVIEW (adversarial pass, 2026-08-04, read-only against `dr-mario-mods-wt/driver-nav`
HEAD at review time — `git status` clean, `up to date with origin/driver-nav`)

Verified the mechanism sketch in §1 directly against `driver-nav/patch_cartridge_copro.py`
(`dn_p2` at lines 1620-1650, `act_p2_n`'s rotation pre-phase at lines 1553-1593). One
load-bearing discrepancy and three unaddressed task questions found; test plan is broadly
sound (does simulate the defect, per house rule) but has a concrete, fillable gap.

### 6.1 CRITICAL — the mechanism sketch omits the `SLAM_ARM` pre-gate, and that gate is
the branch active in the worst tape commit

`patch_cartridge_copro.py:1635-1637`:
```
if MATURE:
    a.ins16("LDA_abs", SLAM_ARM); a.br("BEQ", "dn_hold")   # search not keeping pace: DONE-wait only
a.ins16("LDA_abs", 0x0386); a.ins("CMP_imm", CROSS_LOWY); a.br("BCC", "dn_slam_cross")
```
`SLAM_ARM` is checked and can branch straight to `dn_hold` **before** the `Y < CROSS_LOWY`
feasibility-crossover check ever runs. `SLAM_ARM` is set once per search, at DONE, based on
whether *that* search finished in under `FAST_HI*256` (512) hooks (`:1364-1369`) — i.e. it
encodes "was the *previous* search fast," not anything about the current descent. §1's
mechanism sketch (lines 74-86 of this file) shows only:
```
elif Y < CROSS_LOWY: need = K_CROSS
```
with no `SLAM_ARM` term at all. That is a materially incomplete picture of the actual
control flow: when `SLAM_ARM==0` the `K_CROSS` feasibility-crossover path (the part of the
mechanism specifically designed to commit *something* once `DONE` becomes physically
unreachable) **never executes**, for any `Y`. The driver instead behaves identically to
`K_OPEN=K_END=255` (wait for `DONE`, full stop) regardless of how low the capsule already
is.

This matters because `SLAM_ARM=0` is not a corner case for the m3 tape — it is the
*expected* state near a topout. Row 0 is already locked at column 5 from the first
recorded commit onward (VERDICT.md, "Board-state cross-check"), and a critically stacked
board is exactly where P2 searches are slowest (more legal placements to rank, deeper
cascades to score), which is what drives `SLAM_ARM` to 0 in the first place. Commit 6
(t=1117.083, `spawn_to_lock_frames=20`, `tape_rank 24/24`, the single worst commit in the
set) is precisely the kind of position where the *preceding* search(es) were plausibly
slow. §3 ("Freeze-exposure analysis") never traces `SLAM_ARM` state through any of the six
tape commits, and neither does the test plan (§5.2, §5.3) — both parametrize DONE-arrival
timing but never `SLAM_ARM`. **Required change:** either (a) show, with the actual
`WDOGH2`/latency numbers implied by the tape (or a documented assumption where they're
unavailable), what `SLAM_ARM` was during commits 2/4/5/6, or (b) if that can't be
recovered, treat `SLAM_ARM=0` as the pessimal case to test and demonstrate the fix still
improves on it — right now the proposal's safety story implicitly assumes the `K_CROSS`
branch is reachable, which is not guaranteed in the scenario the fix targets.

### 6.2 The gate has no notion of lateral travel distance — the worst commit may be
physically unfixable by any commit-timing policy

`CROSS_LOWY`/`K_CROSS` reason about *when* to commit (rows of fall remaining, hooks of
argmax stability) but never about *how far* the target column is from the capsule's
current column. Commit 6 needed col4 → col7 (3 columns) inside a 20-frame window. Per the
driver's own DAS-cadence comment (`patch_cartridge_copro.py:1554-1556`, "NAV_T=5*/frame ...
32-hook cycles = 6.4 frames per edge"), three column-edges cost ≈19.2 frames — essentially
the *entire* 20-frame budget — leaving ~0 frames of margin for `K_CROSS`'s own 8-hook
(4-frame) stability requirement, let alone for the search to have converged on col7 at all.
Even a hypothetically perfect gate that knew the right column at hook 1 and began steering
immediately would land with no slack; any additional latency the fix itself introduces
(waiting for `DONE`, or for 8 hooks of stability under `K_CROSS`) risks reproducing the
observed symptom (locks short of the target, near the spawn column) via natural gravity
instead of via a forced early slam — same visible failure, different proximate cause.
§1(B) markets `CROSS_LOWY` as an improvement over a fixed frame timeout because it "auto-
adapts to gravity speed," which is true for the *vertical* feasibility question (can `DONE`
arrive before landing) but says nothing about *horizontal* feasibility (can the piece
physically get there). **Required change:** either add a distance-aware term to the gate
(e.g. widen `CROSS_LOWY` or lower `K_CROSS` as a function of `|current_col - TGT_C2|`), or
explicitly document commit-6-shaped cases (large lateral distance, near-zero fall budget)
as an accepted residual failure mode the fix does not claim to close, rather than folding
them silently into "this closes the gap" (§1's framing).

### 6.3 The task's counter-case (t=1113.617, commit 3) is never named, traced, or tested

VERDICT.md flags commit 3 as the one case where the tape's fast, latch-shaped commit
*matched* the eval's own top column choice (gap 86) — direct evidence that not every fast
commit is a bug, and the task explicitly asks whether the guard could make commits like
this *worse*. This proposal's §3 and §5 never mention this timestamp or this commit by
index. The nearest thing offered is a citation to a *different* experiment ("task #40
sweep: placement stays OPTIMAL at floor {90,45,25,0}; only tempo moves," used in Rejected
Alternative #2) — that sweep validates a different flag (`MIN_THINK`) under different
conditions, not a replay of commit 3's actual board/timing state under `COLGATE`/
`RECOMMIT`. Given §6.1 (search-speed did not correlate monotonically with board state per
VERDICT.md discriminator (c), so `SLAM_ARM` at commit 3 cannot be assumed armed just
because the window was short), it is not established whether commit 3, now forced through
the `dn_hold`/wait-for-`DONE` path instead of slamming the instant it's aligned, still
reaches col3 before the board or search state moves on. **Required change:** add the
commit-3 replay explicitly to the test plan (see 6.4) — construct its board/timing
parameters from `proxy_results.json` board index 3 and assert the fixed build's landing
column/frame is unchanged or improved, not merely "not obviously worse."

### 6.4 Freeze-class exposure (GO-storm / stale-ARMED2 / copro-wait busy-loop)

The core argument in §3 — no new `wgo` writes, `RECOMMIT` only fires inside the
post-`ARMED2==0` `DONE` handler, `dn_hold` never pins gravity — is directionally sound and
I found no counterexample for GO-traffic widening or new re-entrancy surface in the source
(confirmed independently: the only `STA_abs wgo` in the file is the pre-existing
search-launch write, untouched by this change). One item is asserted rather than shown:
§3's "no new hang surface" claim covers `dn_p2`'s hold path but the *rotation* pre-phase
(`act_p2_n`, lines 1553-1593) has its own, separate `MATURE`/`SLAM_ARM`/`CROSS_LOWY` gate
(`p2_esc_skip`, lines 1584-1588) with the identical blind spot as §6.1 — when `SLAM_ARM==0`
it collapses to the `MIN_THINK`-only wait. The proposal doesn't cite the escape hatch
(`STK2`/`STUCK_LIM`, lines 1551-1552) explicitly re-arming inside *either* hold loop by line
number — worth confirming directly rather than assuming it covers both `SLAM_ARM=0`
branches, since that counter is what stands between "tempo cost" and "true stall" in the
degenerate case. Not a confirmed defect; flag as required verification, not a blocker.

### 6.5 Test plan: does it test the defect, or the guard? — mostly the former, one gap

Items 1-3 largely satisfy the house rule (simulate the defect, assert the outcome changes):
item 2 explicitly reconstructs commit 6's spawn/argmax/DONE-timing race and asserts the
capsule lands on the post-convergence column, not just that a flag is set; item 3 sweeps
DONE-arrival timing to falsify the "closes the race" claim rather than merely restating it.
That is good practice and should be kept. The gap, per 6.1-6.3: the sweep in item 3 varies
DONE-arrival hook only. **Required change:** extend items 2-3 into a small matrix over
`{SLAM_ARM ∈ {0,1}}` × `{lateral column distance ∈ {0,1,3}}` × `{DONE-arrival hook}`, plus
one case explicitly keyed to commit 3's parameters (short window, spawn-adjacent correct
column, near-tie/agreeing margin) asserting no regression. Without the `SLAM_ARM` axis, a
green test suite would not actually exercise the branch that governs the worst tape commit,
and would report success on a mechanism that — per 6.1 — degrades to plain DONE-wait in
exactly that case.

### 6.6 Net assessment

The mechanism is a real fix for the *diagnosed* pattern (force-drop firing the instant the
capsule is physically aligned with a not-yet-converged running argmax) and the freeze-class
non-interference argument holds up under direct source inspection for the parts it covers.
It is **not yet shown** to close the two extremes the task asked about: the worst tape
commit may hit an undocumented fallback branch (`SLAM_ARM=0`) that the mechanism sketch
omits and that reduces to the pre-fix "wait or don't move" shape, and may in any case be
lateral-distance-infeasible regardless of gating; the best tape commit (the counter-case)
is never traced through the new gate at all. Recommend: (1) fix the mechanism write-up in
§1 to include the `SLAM_ARM` branch so the design doc matches the code, (2) do the
commit-3 and commit-6 replays with real parameter values before claiming the gap is
closed, (3) extend the test matrix per 6.5, (4) explicitly scope commit-6-shaped
lateral-infeasible cases as accepted residual risk or add a distance-aware term — do not
ship "this closes the gap" language until 1-3 are done.

## 7. CORRECTION (artifact fingerprint, 2026-08-05 ~03:50)

The §2 ABSENT verdict is **overturned at the artifact level**: the shipping
Pocket cart (pocket_human_v4_coldinit.nes, md5 24dcd9dc…) reproduces
BYTE-EXACT from driver-nav HEAD via tools/romgen.py rebuild with
DRROTFIX/DRCOLGATE/DRRECOMMIT/DRSLAM at defaults-ON + DRRECOMMIT_NOFREEZE=1
(623-byte OFF-reference diff at $8456-$871F proves the flags assemble real
code). §2 was right that the CANONICAL tree's driver copy lacks the fix,
wrong to infer the cart came from that copy — the cart is a driver-nav
build. Also corrected: Pocket ships NO_FREEZE=1, so DRCOLGATE is a NO-OP
there (`if NO_FREEZE or COLGATE:` already true); RECOMMIT is the fix that
matters on this platform.

**Mechanism migrates accordingly**: with the fix present, the m3 signature
is explained by REVIEW §6.2's lateral-DAS-vs-gravity race — measured
(Test E): a commit-6-shaped ~40-hook window reaches 1-column-distant
targets, cannot reach 3-column-distant ones (~96 hooks needed), and fails
via ordinary gravity landing wherever WEAVE reached — never via forced
wrong-column slam. That is exactly the tape (search wanted cols 0/6/7,
capsule parked at spawn cols, no forced slams, non-monotonic timing).
**The real fix is the distance-aware commit gate** (§5): choose the best
REACHABLE column under the remaining fall budget. Implementation assigned.
Full fingerprint evidence: driver-nav/CART_FIX_REPORT.md.
