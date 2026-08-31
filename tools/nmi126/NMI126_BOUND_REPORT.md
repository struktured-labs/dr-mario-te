# #126 — Bounding the NMI hook: cycle census, measurement, verdicts

**Branch** `nmi-bound-126` off `v8-rematch@1bb81bc`. 2026-08-19.

## The question

The shipped NMI fixes (DRRTIVEC + DRMMC1RST) make an NMI overrun *survivable*.
#126 asks for a *bound*: prove — or enforce by construction — that the
driver's NMI hook cannot exceed its frame budget on any path.

Overrun condition: total NMI handler work > the NTSC frame period,
**29,780 CPU cycles**. Handler = game NMI head + exactly TWO hook invocations
(both inside the NMI; no main-loop call) + a small post-hook tail (register
restore + RTI; the hook is the tail of `addExpansionCTRL`, the NMI's last
call), estimated ε ≈ 100–300 cycles.

## Rig coverage (rule 10)

| question | rig |
|---|---|
| worst case over ALL hook paths | static census of the emitter's IR (sound upper bound) |
| how loose is the bound / what is reachable | py65 on the real emitted bytes, adversarial states |
| game-NMI head + live overrun witnesses | Mesen on the real cart (mapper-100→MMC1 header remap, byte-identical PRG/CHR; Lua copro mailbox; game+driver both really execute) |
| silicon | **not covered** — no full-core sim; residual risk at the end |

## Method gates (all green)

- `capture_ir.py` ground-truth gate: IR reassembly == emitter bytes, per unit,
  both configs (hard fail otherwise). Ship carts rebuild byte-exact from
  manifests (romgen, verified 2026-08-18), so IR == ship bytes.
- `census.py`: hard-fails on undeclared loop / unknown opcode / unresolved
  target / recursion. 15 loops bounded with justifications; `pre_run` gets
  call-context bounds auto-derived from the IR's own `PRE_TMP` stores.
  Conservatisms one-directional.
- `test_census.py`: EXACT on 4 hand-computed fixtures; mutants M1 undeclared
  loop, M2 unknown opcode, M3 recursion, M4 bound−1 (answer shifts by exactly
  one worst-iteration), M5 +10-cycle insertion (bound moves by exactly 10) —
  ALL KILLED. py65 whole-chain anchor holds on real v6e bytes.
- `probe_nmi126.lua` VOID guard (frozen counters ⇒ VOID, not thin-pass);
  every switched-window exec callback bank-qualified via `$A02E`
  (`dr-mario-mesen-exec-callbacks-bank-blind`). Instrument self-checks in the
  TCVC run: entry==exit==2×frames (23,992/12,000), bail=0,
  shield=11,995≈nmi=11,996 (shield on every NMI — the known DRMMC1RST mode-3
  effect, reconfirmed live).

## Budget table (cycles; frame = 29,780)

### TCVC `9fefaedb` (CvC tuck MiSTer, the live-soak lineage — DRP1NATIVE, P2 copro @$5200)

| quantity | static bound | py65 adversarial | Mesen live (12,000 f, real CvC play) |
|---|---|---|---|
| game NMI head (`pre`) | n/a (stock game) | — | **2,040 max** |
| steady hook | 4,751 | — | (typ. <1.1k) |
| spawn-edge P2 hook (upload+GO) | 7,420 | — | ≤1,269 (h2 max) |
| **P1NATIVE search hook** | **94,784** | **26,398** (tall same-colour towers) | **19,818 max** |
| worst whole NMI (pre+h1+mid+h2) | 102,204+pre | ~30,100 (adversarial h1 + measured rest) | **22,602 max** |
| overruns | — | — | **0** (shield-absorb = 0 / 11,995 shield entries) |

### v6e `c0082cb3` (Pocket rematch line — DRPRESTART=1, DRHUMAN, P2 copro @$5000)

| quantity | static bound | py65 adversarial | Mesen live |
|---|---|---|---|
| steady hook | 5,279 | 326–1,062 (typical states) | (menu-only run; play not reached — DRHUMAN cart does not self-navigate; game head reused from TCVC, same base game code) |
| spawn-edge hook | 7,963 | — | |
| **prestart release-edge hook** | **27,960** | **18,495** (`mixed8`: 4 deep-fall volley singles + 4 ROM-legal supported row-0 singles, no 4-run, full commit) | |
| worst release frame (spike + pre + mid + steady h2) | **35,687** | ~22,200 (measured parts) / 26,200 (h2 at bound) | |

⚠ The previously quoted prestart worst (11.9k, "40% of a frame") **understates
the reachable worst by ~1.55×** — the `mixed8` state (row-0 singles supported
by full columns, legal near death) drives `pre_tick` to 18,495 because PRE_N
reaches 8 and every match scan walks its whole axis. Still under one frame,
but the margin near death is ~25%, not ~60%.

## Verdicts

1. **TCVC steady + spawn frames: (a) proof holds.** Pair bound 4,751+7,420+12
   + game head 2,040 + ε ≈ **14.5k of 29,780 — 51% margin**, and that is the
   SOUND bound, not an estimate.
2. **TCVC P1-search frames: (b) enforcement needed.** The sound bound (94.8k)
   is 3.2 frames; the adversarial reachable is ~30.1k for the whole NMI —
   OVER the frame. Live play showed 0 overruns in 12,000 frames with worst
   22.6k (76%), so this is a TAIL risk, not a routine one — concentrated on
   tall same-colour tower boards, i.e. **exactly the near-death regime**
   (`dr-mario-clean-failure-geometry`), where a skipped game NMI (the shield's
   absorb cost) is least affordable. Interim claim "overruns at every P1
   spawn" is hereby CORRECTED: refuted by the live measurement.
3. **v6e steady + spawn frames: (a) proof holds** — pair bound 13,254 + head
   2,040 + ε ≈ 15.5k, 48% margin.
4. **v6e prestart release frames: (b) enforcement needed by the proof
   standard.** Sound bound 35,687 > frame. Reachable measured ≈ 22.2k (75%),
   so empirically safe today — but "measured, not proven" is the standard
   #126 rejects, and the analyzer cannot tighten below the frame because the
   9-pass match scan and 8-column settle are genuinely ROM-reachable
   (`mixed8` proves the 8-record state is real, killing the tempting
   "volley ≤ 4 ⇒ PRE_N ≤ 4" refinement).

## Enforcement spec (the (b) changes — each needs its own gate battery)

1. **TCVC: slice the P1 search across hooks.** Already per-pill cached (keyed
   on pill Y); make it a small state machine in free driver PRG-RAM (phase,
   col, best-so-far), ≤2 placements per hook (≤ ~4k cycles). 15 placements
   finish in ≤8 hooks = 4 frames; the anytime driver already steers from
   stale targets, and P1 is the deliberately-slow spectator side.
   Kill-test: probe_nmi126 absorb-count and mxsum — the sliced build's mxsum
   must stay <29,780 on the adversarial tower board where ship exceeds it
   (test the defect, not the fix).
2. **v6e: pipeline `pre_tick`.** Phases per hook: copy 128 B → orphan guard +
   settle → match scan → upload + GO. Worst phase ≤ ~8k bound; lead shrinks
   ≤3 hooks = 1.5 frames of a 24–264-frame window. Second-volley-mid-pipeline
   ⇒ abandon whole (existing PRE_ACT2 teardown semantics).
3. **Binding rule for the garbage-window lane:** ZERO new host-hook cycles —
   new compute is copro firmware behind a capability byte; any host-side
   addition requires a census re-run against the per-class bounds above.
   See `GW_INCREMENT_SPEC.md`.

## What remains unproven on silicon

- No full-core sim: the 2A03 cycle model (py65/Mesen) is the same one the
  cores implement, but the end-to-end NMI cadence on MiSTer/Pocket silicon is
  unverified; Mesen OAM-DMA/odd-cycle timing may differ ±~10 cycles/frame.
- The game NMI head (2,040 max) is measured over one 12,000-frame CvC run
  (menus, play, clears, game-over, board init all visited); it is not a
  static bound. A field-re-render worst frame beyond what this run visited
  would eat margin — verdicts 1 and 3 keep >14k of slack against that.
- v6e was not driven into play in Mesen (DRHUMAN cart, no self-nav); its
  game head is inherited from TCVC (identical base-game code, different
  driver — driver cost is separately bounded).

## #129-family entry-point witness (team-lead addition, 2026-08-19)

The probe additionally watches writes of any colour-`$F` byte into either
field page and into attackColors (both homes: zero-page `$A9-$AC` live store
AND the `$0329/$03A9` swap copies), with PC, mode, and distance to the last
shield-absorb event on every hit. renderGameOver's mode-7 box tiles
(`$8F/$EF/$1F`) are the built-in positive control: a run that visits mode 7
with zero non-play field-`$F` writes is stamped `VOID129`, never a thin zero.

RESULTS (tcvc129: 24,000 frames real CvC play, multiple match ends, mode-7
visited):

| class | count | liveness of its watch region |
|---|---|---|
| `$xF` into a field DURING PLAY (the finding class) | **0** | field writes 27,003 / 29,802 |
| `$xF` into a field, other modes | 98 — ALL pc=$96E3 renderGameOver, values $8F/$1F, mode 07 (**positive control: FIRED**) | — |
| colour-$F into attackColors (zp $A9-$AC or $0329/$03A9) | **0** | 141,541 zp + 72,968×2 copy writes |
| shield absorbs | **0** / 23,995 shield entries | — |

Correlation: vacuous — both event classes were zero; every XF hit logged
`dAbsorb=never`. The known-benign arm events (mode-7 box writes) never
coincided with an absorb in this run.

Rule-8 framing: this is BOUNDED EXPOSURE, not absence — 24,000 frames, one
cart (TCVC `9fefaedb`), Lua-mailbox harness, deterministic boot-seed path.
The #129 entry-point question (what writes the FIRST stray `$0F` into
attackColors) remains open; this run adds that under #126's own witness
conditions — the exact runs where the NMI-corruption family would be the
prime suspect — nothing fired.

## Enforcement 1 SHIPPED-AS-CANDIDATE: DRP1SLICE (2026-08-19, same night)

`DRP1SLICE=1` (default OFF, requires DRP1NATIVE) slices the P1 native search:
ONE column-step per hook via a PRG-RAM state machine ($61BB-$61C1), loop
bodies verbatim from the v18 AI, swap re-eval + publish as the final step,
<=16 hooks = 8 frames per pill. Two documented behaviour deltas, both
spectator-grade: one possible AND-cancelled input frame per pill at publish,
and a <=8-frame board-drift window mid-search (anytime-steering class).

Candidate cart `roms/tcvc-p1slice.nes` md5 `010f4ffe` = TCVC ship flags +
DRP1SLICE=1 (manifest `roms/manifests/tcvc-p1slice.json`; ship cart
`9fefaedb` still rebuilds byte-exact — the flag is default-proof).

Gate battery `tests/test_p1slice.py`, ALL PASS:
- G1 byte-identity OFF (unset == "0"; flag demonstrably not inert)
- G2 whole-chain argmax equivalence: 44 boards x colours, sliced ==
  unsliced (column, orient, best score), with ALL v18 zp scratch clobbered
  0xA5 between ticks and boards bit-restored; max 16 ticks
- G3 mutants 4/4 KILLED: skip-a-column, no-save-best, skip-swap (orient 3
  vs 1 — swap-decisive corpus case), no-restore-col
- G4 measured tick 1,868 <= census bound 6,029; census same-frame pair
  24,319 + game head 2,040 + eps 300 = 26,659 < 29,780 — the sliced cart
  carries the SOUND whole-frame certificate the ship cart cannot
  (ship p1-hook bound: 94,784)

Mesen A/B (12,000 frames each, same probe/harness, matches cycling on both):

| | ship `9fefaedb` | sliced `010f4ffe` |
|---|---|---|
| P1 hook worst (mxh1) | 19,818 | **4,745** |
| worst whole NMI | 22,602 (76% of frame) | **8,741 (29%)** |
| NMIs >=16k cycles | 54 | **0** |
| overruns / bails | 0 / 0 | 0 / 0 |
| #129 witness | clean, control fired | clean, control fired (42 mode-7 writes) |

The kill pair, stated per the standard: on the adversarial tower board the
SHIP configuration's whole-NMI (~30.1k measured parts) exceeds the frame and
only the DRRTIVEC absorb stands behind it; the SLICED configuration cannot
exceed the frame BY THE SOUND BOUND (26,659 incl. game head + tail). No wedge
appeared in either arm (modes cycled 04/07/08 normally), so the f%30
discriminator had nothing to adjudicate.

NOT yet done: silicon soak of `010f4ffe` (no MiSTer/Pocket exposure; the
live soak cart is untouched), and the prestart pipelining (enforcement 2)
remains open for the next session.

## Enforcement 2 SHIPPED-AS-CANDIDATE: DRPRESPIPE (2026-08-20)

`DRPRESPIPE=1` (default OFF, requires DRPRESTART) pipelines the prestart
release path across hooks via a PRG-RAM phase byte (`PP_PH` $61C2, `PP_SWAL`
$61C3):

| hook | work (Q=3 default) | (Q=4 variant) |
|---|---|---|
| 0 (release edge) | detect + the `$0500` -> `PRE_BUF` snapshot copy | same |
| 1 | orphan guard + settle | same |
| 2 | match records 0-2 | match 0-3 |
| 3 | match records 3-5 | match 4-7 + upload + GO |
| 4 | match records 6-7 + upload + GO | -- |

GO lands on edge+NM hooks: **2.0 frames** at the Q=3 default (1.5 at Q=4), of
a 24-264 frame lead. The copy
stays in the edge hook deliberately: garbage falls a row per 16 frames and the
settle scan keys on row 0, so a copy delayed a hook would project a different
board (gated: G3 wipes the live board after the edge hook and asserts the
upload is still the snapshot).

`DRPRESPIPE_Q` (default **3**, team-lead ruling 2026-08-20: the Q=4 shape's
1,154-cycle margin rests on a measured-not-bounded game head plus an estimated
eps, while 0.5 frame of a >=24-frame lead is noise) is records per match
phase. **The pair, not the
phase, is the constraint** -- two hooks run per NMI -- and the total work is
fixed, so the worst adjacent pair shrinks only by ADDING phases; rebalancing
work between two adjacent phases cannot change their sum.

### Bound table (v6e class, sound census bounds, cycles; frame = 29,780)

| quantity | ship (DRPRESTART) | Q=4 variant | **Q=3 (DEFAULT, ships)** |
|---|---|---|---|
| worst release-edge hook | 27,960 | **13,561** | 11,269 |
| worst release FRAME | **35,595 (OVER)** | **28,626 (96.1%)** | **24,854 (83.5%)** |
| margin | none | +1,154 | +4,926 |
| hooks to GO | 1 | 3 (1.5 f) | 4 (2.0 f) |

Per-hook (Q=4): edge 8,019 / ph1 11,268 / ph2 12,725 / ph3 13,561, each
including the ~5.3k steady residue.

⚠ **The generic `SAME-FRAME PAIR` census line is the WRONG MODEL on a
pipelined image** -- it pairs a spawn upload with a phase hook, which cannot
happen. `census.py` now emits an ADMISSIBLE-FRAME table instead, and the
exclusion is proven, not assumed: `handle(2)`'s `_start` opens
`LDA PEND2 / BNE st1 / JMP h2_done`, so the 128-byte spawn upload requires
PEND2 != 0, and the dispatcher ABORTS the pipeline whenever PEND2 != 0 (or
ARMED2 != 0). The abort checks are therefore load-bearing for the
CERTIFICATE, not only for correctness -- `test_prespipe.py` M3 deletes the
check and must fail.

Census additions: per-phase scenario classes derived from the labels the image
carries (the phase count is a knob), and match-driver loop bounds DERIVED from
the IR's own quota compares rather than hand-declared -- a hand-written bound
would silently survive a re-split.

### Gate battery `tests/test_prespipe.py`, ALL PASS (both Q=4 and Q=3)

- G1 byte-identity OFF (unset == "0"; flag demonstrably not inert). Also
  proven at the CART level: `hardened-prestart-20260820` still rebuilds
  byte-exact `4ac725cf` from the changed emitter.
- G2 whole-chain equivalence, 53 boards (43 commit / 10 bail): same 128
  upload bytes, same mailbox +$80..+$84, same commit-or-bail decision and same
  PRE_ACT2/ARMED2/PEND2/WDOG2/WDOGH2 end state as ONE synchronous `pre_tick`,
  with ALL zero page and both index registers clobbered 0xA5 between hooks,
  and GO on exactly the designed hook. Population check: PRE_N=8 on 4 boards
  (the state the whole bound is about -- it was 1 of 50 before the check).
- G3 snapshot semantics.
- G4 mutants 5/5 KILLED: M1 dispatcher never reaches phase 1, M2 commit
  uploads from the LIVE board, M3 PEND2 abort deleted, M5 `pt_bail` does not
  disarm, and **M4 quota 4 -> 8, which is behaviourally EQUIVALENT** (the
  quota only decides which hook does which record) and is therefore invisible
  to every behaviour gate -- it is killed by the CERTIFICATE, which is what
  proves G6 constrains the split.
  ⚠ M3 first died of the harness (rule 12): NOPing only its LDA+BEQ left the
  following `JMP pt_bail` exposed and made the dispatcher bail
  unconditionally. Fixed to delete all 8 bytes.
- G5 abort obligations: PEND2, ARMED2 and a second buffered volley each
  abandon whole with no commit and no GO; the second volley's own release edge
  is swallowed once, matching what the synchronous teardown does there.
- G6 certificate, with a NOT-INERT arm asserting the UNPIPELINED image is
  still OVER the frame (35,595) -- without it a PASS could mean the defect was
  simply absent.

### Mesen play battery, 18,000 frames each, chained A/B

**Ship candidate `roms/prespipe-hardened-q3.nes` md5 `7e73d4a3`** = the
hardened prestart ship flags + `DRPRESPIPE=1` at the Q=3 default; the Q=4
variant `prespipe-hardened.nes` `29924c14` is kept per keep-versions and its
manifest still replays byte-exact after the default flip (snapshot recorded
DRPRESPIPE_Q=4 -- default-proof both directions). Control
`hardened-prestart-20260820` `4ac725cf`. The battery below was run on BOTH
flag-ON carts (Q=4 first as a dry run, then the Q=3 ship bytes -- rule 6);
the two flag-ON columns were numerically IDENTICAL, so one is shown.

On the exact Q=3 ship image the release-class certificate is
**worst admissible frame 23,648 of 29,780 (79.4%), margin 6,132** (hardened
class; the v6e class gives 24,854 / margin 4,926). The P1-search class on this
cart (unsliced, 103.5k ALL_PATHS) remains enforcement 1's territory and is NOT
certified here -- the combined DRPRESPIPE+DRP1SLICE cart is blocked on the
$61BB collision.

| | control `4ac725cf` | pipelined (`7e73d4a3` and `29924c14`) |
|---|---|---|
| goes / dones | 178 / 172 | 181 / 173 |
| matches started / ended / clean | 15 / 14 / 14 | 14 / 14 / 14 |
| pills | 163 | 167 |
| MIXED_total / brk_a02e / ABORT_4to0 | 0 / 0 / 0 | 0 / 0 / 0 |
| soft8036 / wipes | 2 / 14 | 2 / 13 |
| D135 | blocked=10 leaked=0 | blocked=10 leaked=0 |
| fail_hi / fail_lo | 0 / 2 | 0 / 2 |

The control arm reproduced the merge lane's own recorded numbers exactly
(`GATE_PRESTART_20260820_raw.md` G1), which is the provenance check on a
harness copy repointed to a different worktree. No fire-rate loss appears
(goes 178 -> 181). `soft8036=2` and the wipe counts are present in BOTH arms
and are a property of this cart class, not of the flag. No wedge appeared in
either arm (14 clean ends both), so the `f%30` discriminator had nothing to
adjudicate -- and DRPRESPIPE shifts GO by 3 hooks, so it IS a tempo-shifting
flag and any future wedge on it gets that check first.

### ⚠ The 18k battery is VACUOUS for this path -- and so is every prior one

Measured on BOTH carts, 12,000 frames, with a positive control in the same
callback shape: `CTL_hookwrites` 6,706 / 6,490 (pre_tick's per-hook store --
the probe demonstrably sees this driver's writes) with
**`atk_release_edges` = 0**. P2 never receives a garbage volley in a probe6
CvC run, so DRPRESTART -- and therefore DRPRESPIPE -- NEVER FIRES there. The
battery above is real evidence the flag-ON cart is HEALTHY; it is no evidence
that the pipeline WORKS.

Scope it correctly: this is a property of the CvC self-play harness, whose P1
is the deliberately-weak DRP1NATIVE spectator search. A human P1 produces
volleys -- but the DRHUMAN carts are exactly the ones this report already
records as "menu-only run; play not reached". Neither `probe6.lua` nor
`probe9.lua` watches `$0318`, `PRE_ACT2`, or any prestart state (probe6 has
one COMMENT acknowledging the early publish, and no counter), so no play-level
gate has ever observed the prestart firing on any cart, while DRPRESTART=1 has
shipped on v6e, the hardened line, c-v8ship and the Pocket v7 artifact.

### Forced-release liveness, both arms (`probe_prespipe_force.lua`)

Pokes `p1_attackSize` + attackColors during play -- what the ROM itself writes
on a multi-virus clear -- and lets the ROM's own `checkReleaseAttack` drop the
garbage and clear the byte, which IS the release edge. One byte at an NMI
boundary, not probe9's whole-RAM restore.

| 6,000 frames | control `4ac725cf` | Q=4 `29924c14` | **Q=3 `7e73d4a3`** |
|---|---|---|---|
| release edges (forced) | 7 | 6 | 6 |
| PP_PH starts / advances / completes | **0 / 0 / 0** | 6 / 12 / 6 | **6 / 18 / 6** |
| aborts / max phase | 0 / 0 | 0 / 3 | **0 / 4** |
| GO within 4 f of a release edge | 5 | 6 | **6** |
| fc_stuck (wedge canary) | 0 | 0 | 0 |

`advances` per start is exactly NM-1 on each variant (2 at Q=4's 3 phases, 3
at Q=3's 4), i.e. the machine walking its designed phase sequence, and every
start reached the last phase and issued the GO. The
control's 0 starts is the discriminator -- same forced edges, no phase machine.
A GO within 4 frames of the edge can only be the prestart's: the ordinary
spawn-edge GO is >= 24 frames away by the window formula. The control also
committed 5 of 7, which is the first play-level evidence in this report that
the SYNCHRONOUS prestart fires at all.

⚠ Counts, not rates (n = 6 and 7, one seed). The two arms' poke counts differ
because the trajectories differ by a few frames -- DRPRESPIPE shifts GO by 3
hooks and is a tempo-shifting flag, exactly the phase-dial class.
⚠ `completes` counts the phase-3 -> 0 transition, which the 4-run BAIL reaches
too; it is the GO-register column, not that one, that shows a commit.

### NOT PROVEN

- **No silicon exposure.** MiSTer/Pocket untouched; the live soak cart is
  untouched.
- The game NMI head (2,040) is inherited MEASURED, not bounded, and eps 300 is
  an estimate. At Q=4 the margin is 1,154 cycles, so a game-head excursion
  beyond what the 12,000-frame CvC run visited could eat a large fraction of
  it. Q=3 (margin 4,926) exists for exactly this reason and passes the
  identical gate sheet.
- Commit/bail PARITY between the arms on the same board is proven only in
  py65 (G2, 53 boards). The forced-release runs show both arms commit, but
  they are different trajectories, so they are not a matched comparison.
- **Fire-rate cost of the lock-edge abort is not measured.** A P2 spawn inside
  the 3-hook window aborts a prestart the synchronous path would have
  delivered. The designed case is safe by construction -- a release opens a
  window of W = 264-16*h_min >= 24 frames before the next spawn, against a
  1.5-frame pipeline -- but a release landing one or two frames before a spawn
  is not excluded by that argument. The 18k A/B shows no loss (goes 178 ->
  181), which bounds it as small on this cart and workload; it is not a rate.
- No combined `DRPRESPIPE` + `DRP1SLICE` image is certified, and it cannot be
  built safely yet: **`FC_STAB` (DRSTARTGUARD, #134) and `SL_PH` (DRP1SLICE)
  both claim `$61BB`.** Verified directly -- an image with both flags emits 6
  writers at `$61BB`. Latent today (no shipped cart carries both), but
  `derive_prg_ram_map.py` reported 0 collisions on that config, so the map's
  check appears blind to two DECLARED symbols sharing one address.
  **RESOLVED 2026-08-20 (collision-140):** mechanism confirmed as THREE
  independent blind spots -- (1) `declared()` kept one symbol per address via
  `dict.setdefault`, silently dropping `SL_PH`; (2) `collisions()` skips every
  ABSOLUTE store (`if lo == hi: continue`) and only checks indexed spans, so
  even a correct owner map could not flag the six absolute writers; (3) no
  derived config enabled `DRSTARTGUARD` or `DRP1SLICE`, so the emitted view
  never saw a `$61BB` writer at all. Fix: `FC_STAB` relocated to `$61C4`,
  `declared()` now keeps every claimant, a `dup_declared` finding fails
  `--check`, the three missing configs are derived, and the gate carries the
  retired one-owner implementation as a named killed mutant (M4/M4m in
  `tests/test_prg_ram_map.py`).
