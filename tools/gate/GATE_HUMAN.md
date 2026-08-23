# GATE SHEET — HUMAN-CHALLENGE cart #148: DRHUMAN on the #140 hardened+pipelined class

**Cart** `roms/human-hardened-pp3-20260823.nes` md5 `ae06cd1d4a08e27f1b147eba488eeb17`
Recipe `tools/build_human.sh`, manifest `roms/manifests/human-hardened-pp3-20260823.json`,
emitter `patch_cartridge_copro.py` md5 `307e16e5ee80c07b64e48bc15ef8e50a`,
base ROM `drmario_v28cs.nes` md5 `7d307c3051ebc0f8a10e259e3c270acb` (hook `4c00fb` @ 0x37CF
checked before building), `DRBUILDID=0`, romgen, branch `humancart-148`. 2026-08-22.

The person plays **P1** on a real pad; the certified copro AI plays **P2**.

## Why this sheet exists (RULE 13)

Every certificate on the shelf — GATE_HARDENED (#129/#133/#134/#114), test_prespipe
(#126 enforcement 2), test_p1slice, GATE_COMBO (#140) — certifies a **CvC** image, where
both sides are the driver. Putting a person on P1 emits a *different program*. The sheets
do not add up to a sheet for this cart, so this cart got its own.

## The flag answer the task asked for: **DRP1SLICE is NOT representable on a human cart**

Not "not useful" — **refused by the emitter**, transitively, and the gate demonstrates it
rather than asserting it:

```
DRP1NATIVE=1 with DRHUMAN=1 is refused   (P1 is a person; the cart must not drive them)
DRP1SLICE=1 without DRP1NATIVE=1 is refused   (there is no P1 native search to slice)
```

DRP1SLICE slices the **P1 native search**. A human cart has no P1 search. Consequently
#140's whole subject — the PP_RAN phase/slice interlock — has no second machine to guard
against on this image: the collision configuration cannot arise here. It is left out, and
`H3` proves all three P1-driving flags are rejected.

## Shipped flag set

`combo-hardened-pp3sl-20260820.json` flag_snapshot (the certified #140 cart `2b806db8`)
with exactly four deltas: `DRHUMAN=1`, `DRP1NATIVE=0` (forced), `DRP1SLICE=0` (forced),
`DRBUILDID=0` + `DRBUILDID_TAG=HUMN`. Carrying: DRVERFIX (#129), DRSTARTGUARD (#134),
DRROTDIR (#114), DRPRESTART + DRPRESPIPE Q=3 (#126 enforcement 2), DRTUCK.

**DRUNPAUSE (#133) is compiled OUT** (`if UNPAUSE and not HUMAN_P1`) — and does not need to
be in. #133's hazard was the P1 *executor* rewriting `$F5` every hook so the pause loop's
`$F5==$10` compare could never be satisfied. On this cart nothing reachable writes `$F5`
at all (H4a), so **START keeps stock pause/unpause semantics by construction.** The same
gate removes `DRNAVESC` (a human's pause would read as "stuck" and the watchdog would
un-pause them). Both are measured as byte-identity (H2b), not argued.

## Static gates — `tests/test_human_cart.py` (~7 min, py65 venv)

| gate | result |
|---|---|
| H1a deterministic rebuild == shipped bytes | PASS `ae06cd1d` (romgen `rebuild` also ✅ byte-exact) |
| H1b inverting ONLY the human deltas == certified combo | PASS — lands exactly on `2b806db8` |
| H2a DRVERFIX / DRSTARTGUARD / DRROTDIR / DRPRESPIPE / DRPRESTART / DRTUCK OFF | PASS — each changes the bytes, so each is LIVE here |
| H2b DRUNPAUSE=0, DRNAVESC=0 | PASS — BYTE-IDENTICAL (compiled out under DRHUMAN) |
| H2c DRNOFREEZE=0 | PASS — BYTE-IDENTICAL, but **SUBSUMED, not a DRHUMAN effect** (see below) |
| H3 DRP1SLICE=1 / DRP1NATIVE=1 / DRP1WIGGLE=1 | PASS — all three REFUSED by the emitter |
| H4a no **reachable** write to `$F5`/`$F7`/`GRAV_P1` | PASS — 0 reachable |
| H4b the dead P1 executor is really present | PASS — 8 dead stores |
| H5 admissible-frame certificate, this image's own scenario set | PASS — worst **23,322 of 29,780, margin +6,458** [`pp_ph1`+`pp_ph2`] |
| H6 NOT-INERT: unpipelined arm | PASS — still **OVER** at 34,075 |
| H7 M1 `act_p1` passthrough re-pointed at the executor | KILLED — H4a goes red (5 reachable stores) |
| H7 M2 sheet-inheritance detectable | KILLED — combo has `p1s_ppguard/p1s_tick/p1s_idle`, human has none |
| H7 M3 prespipe cuts bind | KILLED — 22 cuts bind; worst `('into','h2_cp')` 23,322 → 28,658 |

Companion suites green on this tree: `run_cart_gates.sh` ALL PASS (test_rtivec, test_mmc1rst,
test_rtivec_aclobber, test_prg_ram_map, test_combo_cart).

### Two findings worth writing down

**1. The P1 executor is still ASSEMBLED on a human cart — and is unreachable.** The emitter
does not omit it; it jumps over it (`act_p1: JMP act_done`). A naive "grep the opcodes" gate
reports **8 `STA $F5`/`$F7`/`GRAV_P1` stores** on a cart that can never execute one. H4 is
therefore a **reachability** result computed over the IR control-flow graph from the hook
entry, not an absence-of-opcodes result — and M1 is the plausible regression (re-point that
one jump, i.e. what reordering the emitter's `if/elif` chain would do), not a synthetic edit.

**2. DRNOFREEZE is byte-inert on this class, and *not* because of DRHUMAN.** Every site it
guards is `NO_FREEZE or X` for an X already on here (`COLDINIT or not NO_FREEZE`,
`NO_FREEZE or ROTFIX`, `NO_FREEZE or COLGATE`), and the RECOMMIT gate is opened by
`DRRECOMMIT_NOFREEZE=1`. Recorded so nobody later reads it as a live knob on this class.

## Play battery — probe6, 18k frames, headless Mesen (MMC1 remap), D135 guard ON

### The adaptation, stated plainly

**The CvC batteries do not transfer, and the #138 forced-release witness could not run at
all.** `probe_prespipe_force.lua` pokes `p1_attackSize` and lets the ROM's own
`checkReleaseAttack` make the release edge — the right mechanism — but it relies on the
**cart** to autonavigate into play. A DRHUMAN cart does not navigate: P1's menu inputs are
the person's, so the emitter emits no `$F5` writes and, with no pad attached, the cart sits
at mode 0 forever. Measured, both arms, 9,000 frames:

```
SUMMARY tag=control_human frames=9000 pokes=0 release_edges=0 starts=0 ... modes=0:9000
SUMMARY tag=flagon_human  frames=9000 pokes=0 release_edges=0 starts=0 ... modes=0:9000
```

An all-zero sheet that *looks* clean and certifies nothing. So the poke was grafted onto
**probe6** — which already walks a human cart into a match using its own D135-guarded
`press()` (the *fixed* START idiom, not the start-spam one that wedges the ROM) — as
`P6_ATK`, **default OFF so every prior probe6 invocation runs the identical program**.

### Stage 1 — 18k, attacks OFF (the cart as an idle-P1 soak)

`goes=157 dones=145 pills=138` · `MIXED_total=0 MIXED_PRG_nonboot=0 brk_a02e=0` ·
`matches 20/19/19 clean` · `ABORT_4to0=0` · `soft8036=2 wipes=19` · D135 `blocked=10 leaked=0`.

**But `tuck_opp=0 tuck_pub=0` and no prestart at all** — an idle P1 never attacks, so P2
never receives a volley, so DRPRESTART/DRPRESPIPE/DRTUCK are all **unexercised**. This
stage is a health check, not a certificate for those flags.

### Stage 2 — 18k, attacks FORCED (`P6_ATK=1`, size 4, ≥300f apart), with reverse-positive control

| | **human pp3** `ae06cd1d` | **control, DRPRESPIPE=0** `a1e2399a` |
|---|---|---|
| atk_pokes → atk_edges | 43 → **44** | 43 → **44** (identical workload) |
| pp starts / advances / completes / aborts | **43 / 124 / 42 / 1** | **0 / 0 / 0 / 0** ✓ |
| pp_maxphase / pp_swallows | 4 / 0 | 0 / 0 |
| atk_armedgos (prestart GO near a release edge) | 40 | 41 |
| matches started/ended/clean | 19/19/19 | 19/19/19 |
| MIXED_total / MIXED_PRG_nonboot / brk_a02e | 0 / 0 / 0 | 0 / 0 / 0 |
| ABORT_4to0 (wedges) | **0** | **0** |
| tuck opp / pub / EXEC_D1 / EXEC_D2 | 39 / 39 / **24** / **26** | 39 / 39 / 24 / 26 |
| D135 | blocked=10 leaked=0 guard=ON | blocked=10 leaked=0 guard=ON |

The kill pair, non-vacuous **by construction**: 44 real release edges are present on *both*
arms, the pipelined image runs 43 pipelines to phase 4 and completes 42, and the same
workload on the un-pipelined image produces **identically zero** — so the counter is
measuring the pipeline and not something else. `atk_armedgos` staying ~40 on both confirms
DRPRESTART itself still fires on the control; only the *pipelining* is gone.

Forcing garbage also unlocked the tuck path that Stage 1 could not reach: `tuck_opp` 0 → 39
with both independent detectors firing (`D1=24` cart-state, `D2=26` trajectory).

### Stage 3 — P1-IDLE WITNESS (added 2026-08-23 after the fault was found on the TV)

**The fault this stage exists for.** The owner loaded `drmario_copro_human_nofreeze`
(`4b98d6c8`) on the TV and reported *"dumb ai on P1 smart ai on P2"* — the cart named
"human" drives **both** bottles. No controller or OSD setting can fix a driver that owns P1,
and nothing in the battery up to Stage 2 would have caught it. So P1-idle became a measured
gate: probe6 never presses P1 during play (`modeCache ~= 4`), therefore any lateral move or
rotation of P1's capsule inside mode 4 is the **cart** moving it.

Same probe, same frames, zero input on port 0:

| | OLD `4b98d6c8` | NEW `ae06cd1d` (3k) | NEW `ae06cd1d` (18k) |
|---|---|---|---|
| p1 capsule DESCENDS | **0** | 71 | **377** |
| p1 spawns | 0 | 17 | 107 |
| **p1 lateral moves** | 0 | **0** | **0** |
| **p1 rotations** | 0 | **0** | **0** |
| P2 meanwhile | steering (x 1..5, o 0/3) | steering | steering |

**NEW:** P1's capsule falls at gravity through 107 pills / 377 descent steps, holds column 3
throughout, and never rotates. The seat is open.
**OLD:** P1's capsule **never moves at all** — frozen at `x=3 y=15 o=0` for the entire match
while P2 steers beside it. Not idle, **PINNED**: the cart owns P1's gravity (`$0312`), which
`H4a` proves this image never writes.

⚠ **Mesen does not reproduce the TV symptom, and that is not hidden here.** He saw a weak AI
playing P1; Mesen shows P1 frozen. `4b98d6c8` is a **dual-window** cart whose P1 search rides
the `$5000` mailbox, and probe6's Lua brain answers only `$5200` (P2) — so in Mesen P1 waits
forever for a result nobody sends. On real silicon the FPGA answers both windows and P1
plays, badly, exactly as described. Mesen shows the cart **claims** P1; the TV shows what it
does once claimed. Neither is a human seat.

★ **A correction worth keeping.** The first version of this counter had the fall direction
backwards — `$0306` **decreases** as the capsule descends and jumps back up on spawn, and the
descent was being treated as a spawn. That silently skipped the x/rotation check on exactly
the frames a capsule is falling, i.e. every frame a driven cart would be steering it. Its
`p1_xmoves=0` was zero **because it never looked**. Caught only because `p1_falls=12` /
`p1_spawns=60` was the wrong way round to be physical. Same pass removed a duplicated
`atk_tick()` call; re-running Stage 2 on the corrected instrument reproduced **every number
identically**, so the Stage 2 table above stands unchanged.

## Provenance of the cart it replaces

`drmario_copro_human_nofreeze` (`4b98d6c8`) appears in **no** `roms/manifests/*.json`. It has
no recipe, no flag snapshot, no recorded emitter — its flags cannot be read, only inferred
from behaviour. Behaviour says it owns P1 and runs a P1-side search on the `$5000` window:
the `DRP1NATIVE` / dual-window shape, **not** `DRHUMAN`. Under `DRHUMAN` the emitter cannot
emit any of it (no `$F5`/`$F7` writes, no P1 gravity pin). **A `DRHUMAN` MiSTer cart with a
recorded, reproducible recipe did not exist before `ae06cd1d`** — and no earlier candidate
could even be rebuilt to check.

## WHAT I COULD **NOT** CERTIFY

1. **No human-in-the-loop play test.** (Stage 3 narrows this: P1 is proven UNCLAIMED, but a
   person's own presses are still unobserved.) Every number here comes from headless Mesen with an
   idle or probe-driven P1. Nobody has held a controller against this image. The one thing
   a human uniquely does — press START, and press it at arbitrary times — is exercised only
   as the D135-guarded probe press (10 blocked, 0 leaked), never as a person mashing it.
   **The pause path in particular is argued from H4a (nothing reachable writes `$F5`), not
   observed.**
2. **Mapper-100 silicon is not what was gated.** probe6 runs an **MMC1-remapped** image
   under a Lua stand-in for the coprocessor. The FPGA copro firmware (theta*=400) is not in
   the loop, so tuck *rates* here measure the probe, not the shipped firmware.
3. **The attack workload is synthetic.** Size-4 volleys every ≥300 frames on a rotating
   colour triple. A human attacking in bursts, or landing a 2-volley overlap, is a
   distribution this run does not sample.
4. **No cross-cart A/B against the cart he plays today** (`drmario_copro_human_nofreeze`,
   `4b98d6c8`). That cart is from a **pre-manifest lineage** — it appears in no
   `roms/manifests/*.json` and has no recorded recipe — so it cannot be rebuilt or gated
   like-for-like, only compared as a black box. Flagged, not solved.
5. **DRSTUDY is held at 0** (the emitter would default it to **1** on a human cart). Held to
   keep this image a minimal delta from certified `2b806db8`. So there is **no study-pause**:
   pausing blanks the board the vanilla way. That is a deliberate choice, not a test result.
6. **DRLEVEL=11 / MED is baked in** as on the CvC class; not evaluated for human difficulty.

## LAST LINE

ALL GREEN: static H1–H6 pass with three killed mutants (M1 input-safety regression, M2
sheet-inheritance, M3 census-cut vacuity), admissible worst frame **23,322 / 29,780 (margin +6,458)**, unpipelined arm still OVER at 34,075, and the forced-attack play battery
non-vacuous by construction — 44 release edges → **43 pipelines started / 42 completed** on
`ae06cd1d` versus **identically zero** on the DRPRESPIPE=0 control, at 19/19 clean matches
and zero wedges on both. `human-hardened-pp3-20260823` (`ae06cd1d`) is **CERTIFIED as a
human-challenge cart**, with the six non-certifications above standing — the first of which
is that **no person has yet played it**.
