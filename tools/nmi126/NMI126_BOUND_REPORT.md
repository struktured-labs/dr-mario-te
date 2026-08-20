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
