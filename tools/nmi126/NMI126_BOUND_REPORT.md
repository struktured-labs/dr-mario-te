# #126 — Bounding the NMI hook: cycle census, verdicts, enforcement

**Branch** `nmi-bound-126` off `v8-rematch@1bb81bc`. **Status: DRAFT — Mesen
measurement columns land as runs complete.**

## The question

The shipped NMI fixes (DRRTIVEC + DRMMC1RST) make an NMI overrun *survivable*
(one absorbed game NMI; self-aligning MMC1 writes). #126 asks for a *bound*:
prove — or enforce by construction — that the driver's NMI hook cannot exceed
its frame budget on any path, so overruns stop happening rather than stop
killing.

Overrun condition: the NMI handler's total work exceeds the NTSC frame period,
**29,780 CPU cycles**. The handler = the game's own NMI work + exactly TWO
driver hook invocations (both inside the NMI; there is no main-loop call).

## Rig coverage (rule 10)

| question | rig | why |
|---|---|---|
| worst-case cycles of any hook path | static census of the emitter's IR | only static analysis quantifies over *all* paths |
| is the static bound sane / real | py65 on the real emitted bytes | cycle-exact, adversarial states we choose |
| game-NMI head cost + real overruns | Mesen on the real cart | only rig that executes the game+driver together; copro mailbox is Lua-emulated (Mesen never executes firmware — irrelevant here, the hook cost is host-side by construction) |
| silicon | **not covered** | no full-core sim exists; residual risk stated at the end |

## Method and its gates

1. `capture_ir.py` — runs the REAL emitter under a manifest's `flag_snapshot`,
   captures the Asm6502 instruction stream + labels for every unit that runs
   in the hook (wrapper `$FF54`, main `$8000`, and on P1NATIVE builds the v18
   AI `$9000` + swap-eval `$9200`). **Ground-truth gate:** reassembling the
   captured IR must reproduce the emitter's own bytes, byte-exact, per unit
   (hard fail). Both ship configs rebuild byte-exact from their manifests via
   `romgen rebuild` (verified 2026-08-18), so IR == ship bytes.
2. `census.py` — CFG worst-case over the IR. Sound-by-construction rules, all
   hard failures: undeclared loop back-edge, unknown opcode, unresolved
   JSR/JMP target, recursion. All 15 loops enumerated and bounded with
   justifications in `LOOP_BOUNDS`; `pre_run` gets call-context bounds
   (row scan 8 / column scan 16), auto-derived from the IR's own PRE_TMP
   stores. Conservatisms are one-directional (indexed reads always +1;
   branch direction free choice; every loop iteration charged its worst).
3. `test_census.py` — the analyzer's own killed-mutant sheet: EXACT on four
   hand-computed fixtures (diamond, counted loop, nested loop, JSR); mutants
   **M1** undeclared loop, **M2** unknown opcode, **M3** recursion,
   **M4** bound−1 (shifts the answer by exactly one worst-iteration),
   **M5** +10-cycle insertion (moves the bound by exactly 10) — ALL KILLED.
   Whole-chain anchor: real v6e bytes on py65 from three concrete states,
   actual ≤ bound.
4. `measure_py65.py` — adversarial measured worst of the two spike paths on
   the real bytes (boards chosen to maximise scan depth / run length).
5. `probe_nmi126.lua` + `run_probe.sh` — Mesen per-NMI anatomy
   (pre/h1/mid/h2 via `cpu.cycleCount`, proven exposed in this build) plus
   DIRECT overrun witnesses: shield-absorb executions (`$CEEC` with
   `$A02E==$40`) and wrapper BUSY-bail executions. VOID guard: frozen
   callback counters abort the run rather than thin-pass.

## Budget table (cycles; frame = 29,780)

### v6e (`c0082cb3`, Pocket rematch line — DRPRESTART=1, DRHUMAN, P2 copro @$5000)

| hook class | static bound | py65 adversarial | Mesen max (measured) |
|---|---|---|---|
| steady play | 5,279 | 326–1,062 (typical) | TBD |
| spawn edge (128 B upload + GO) | 7,963 | — | TBD |
| **prestart release edge** | **27,960** | **12,871** (ROM-max 4-col volley, commit) | TBD |
| same-frame pair (h1+h2) | 33,239 | — | TBD |
| game NMI head (`pre`) | not bounded statically (stock game) | — | TBD |

### TCVC (`9fefaedb`, CvC tuck MiSTer — DRP1NATIVE, DRTUCK, P2 copro @$5200)

| hook class | static bound | py65 adversarial | Mesen max (measured) |
|---|---|---|---|
| steady play | 4,751 | — | TBD |
| spawn edge P2 | 7,420 | — | TBD |
| **P1NATIVE depth-1 search** | **94,784** | **26,398** (tall same-colour board) | TBD |
| same-frame pair | 102,204 | — | TBD |

## Verdicts (a)=proof holds / (b)=enforcement needed

- **v6e steady + spawn frames: (a) provable** pending the measured game-NMI
  head: pair bound 13,242 leaves 16.5k for the game head — TBD confirm.
- **v6e prestart release frames: (b).** The sound bound (27,960) is ~94% of
  the frame *before* the game head and the second hook. The *reality* is
  ~12.9k worst — likely fits — but "measured, not proven" is exactly the
  standard #126 rejects, and the pair bound exceeds the frame. Enforcement
  spec below.
- **TCVC P1-spawn frames: (b), and it is not close.** Even the measured
  search (26.4k) plus the same hook's remaining work, the second hook, and
  any game head exceeds the frame. **The live-soak cart overruns on every P1
  spawn today** and survives only through the DRRTIVEC absorb (cost: one
  skipped game NMI + one skipped sound/timer tick per pill). This also means
  hazard exposure is not hypothetical: the shield is load-bearing at ~1
  absorb per pill. Mesen witness counts: TBD.

## Enforcement spec (the (b) changes — NOT implemented tonight; each needs its
## own gate battery per the 12 rules)

1. **TCVC: slice the P1 search across hooks.** The search is already per-pill
   cached (keyed on pill Y); make the cache a 3-field state machine in free
   driver PRG-RAM (phase, col, best-so-far) and evaluate ≤2 placements per
   hook (≤ ~4k adversarial cycles). 15 placements finish in ≤8 hooks = 4
   frames; the anytime driver already steers from stale targets while
   searching, and P1 is the deliberately-slow spectator side. Kill-test: the
   probe's shield-absorb count must go to 0 on the sliced build and stay >0
   on ship (test-the-defect, not the fix).
2. **v6e: pipeline pre_tick.** Phases per hook: (copy 128 B) → (orphan guard
   + settle) → (match scan) → (upload + GO). Worst phase ≤ ~8k bound; the
   prestart's lead shrinks by ≤3 hooks = 1.5 frames out of a 24–264-frame
   window. The volley state is stable across the pipeline (garbage sits in
   row 0 for 16 frames/row); re-verify the tear-down path (second volley
   mid-pipeline → abandon whole, same as today's PRE_ACT2 teardown).
3. **Rule for garbage-window compute (the successor lane):** no new
   host-hook cycles, period — new work goes to copro firmware behind a
   capability byte (as the gw design already specifies); any host-side
   addition must come with a census re-run and stay under the per-class
   bounds above.

## What remains unproven on silicon

- The census + py65 are cycle-exact for the 6502 model; the MiSTer/Pocket
  core's cycle timing is the same 2A03 model but no full-core sim exists to
  confirm the NMI cadence end-to-end (rule 10 rig map).
- The game-NMI head is MEASURED (Mesen), not statically bounded — the stock
  game is out of scope for path enumeration; the measured max over
  menu/play/render/garbage frames is used with a stated margin.
- Mesen's mapper-100 handling routes to MMC1 like the cores do, but Mesen
  timing of OAM DMA/odd cycles may differ ±~10 cycles per frame from
  silicon; margins are quoted accordingly.
