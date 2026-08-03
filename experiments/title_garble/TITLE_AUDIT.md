# Title-screen garble/flash audit (static analysis)

**Task:** #42-adjacent sub-item. Eyewitness report 2026-08-02 ~21:00: garbled/flashing title
screen on the MiSTer CvC duel cart (`latch_converged_native.nes`), mid-match video clean on
the same display, title only visible briefly between auto-rematches. STATIC ANALYSIS ONLY —
no MiSTer touched, no cart modified, live duel + ledger left undisturbed.

**Cart under audit:** `latch_converged_native.nes`, built by
`~/projects/dr-mario-mods-wt/driver-nav/patch_cartridge_copro.py` from `drmario_v28cs.nes`, with
`DRCOLDINIT=1 DRNAVDWELL=0 DRNOFREEZE=1 DRP1NATIVE=1 DRRECOMMIT_NOFREEZE=1 DRNAVESC=1` + tempo
+ armor knobs. `DRP1NATIVE=1` refuses combination with `DRHUMAN=1`
(`patch_cartridge_copro.py:403`), so `HUMAN_P1=False`, so `DRSTUDY` defaults OFF
(`STUDY = ... "1" if HUMAN_P1 else "0"`, line 534) — **the STUDY 2P-tail evac (the only known
title-table collision mechanism in this ROM family) is not engaged on this cart.**

## TL;DR verdict

| Question | Verdict |
|---|---|
| Q1: patch region collides with a title draw table/routine | **No evidence found.** Every active patch site sits outside the title's code and data footprint. |
| Q2: fast nav writes/START-injection produce the flashing | **Yes, by design — `DRNAVDWELL=0` is the mechanism.** No dwell hold means the title is visible for only ~4 hooks (~2 frames) per rematch, all night. This is almost certainly what was seen; it is a cosmetic side-effect of a deliberate build flag, not corruption. |
| Q3: save-hotkey-ignored / 0-byte saves | **Framework-level, and it has a plausible common root with the black-screen wedge already tracked as task #42 (Freeze #5).** The MiSTer savestate FSM cannot complete unless the core reaches a specific pause handshake; a hung game CPU or a PPU stuck outside vblank blocks that handshake indefinitely, which reads exactly as "mtime never changes, 0 bytes." |

## 1. Title draw path map (base ROM, from `dr-mario-disassembly`)

Located in `~/projects/dr-mario-mods-wt/driver-nav/tmp/refs/dr-mario-disassembly/`:

- **`toTitle`** — `prg/drmario_prg_game_logic.asm:2269` (`$982A`). Entry point on every
  demo-end / game-over / soft-reset transition back to the title. Sequence: set title music →
  `changeCHRBank0` (load `CHR_titleSprites`) → clear `flag_inLevel_NMI`/`visualUpdateFlags` →
  `jsr NMI_off` → `jsr copyBkgOrPalToPPU` with inline pointer `.word bkgTitle` (line 2306-2307)
  → set `palNb_title` → (optional anti-piracy checksum) → `jsr finishVblank_NMI_on` →
  `jsr audioUpdate_NMI_enableRendering`. This is a **synchronous, vblank-paced full nametable +
  palette reload**, unmodified vanilla code, executed on *every* rematch transition.
- **`bkgTitle`** — `data/drmario_data_nametables.asm:14`, table at **`$B936`**.
- **`palTitle`** — `data/drmario_data_game.asm:636`, referenced from
  `prg/drmario_prg_visual_nametable.asm:383`.
- **`title_mainLoop`** — `prg/drmario_prg_game_logic.asm:2321` (`@title_mainLoop`). Runs the
  glow-tile animation (`frameCounter & titleAnim_speed($10)` → `changeCHRBank1`), cursor
  up/down/select handling from `p1_btns_pressed`, `titleDanceAnim`
  (`prg/drmario_prg_visual_sprites.asm:825`, `$8BF5`), and the START check that increments
  `mode` to leave the title. Button reads here come from `p1_btns_pressed`, populated by
  `getInputs`/`addExpansionCTRL` every frame (see §2).
- **RB6C2_PRINT title table**: per `~/projects/dr-mario-te-v8.2/FREE_SPACE_MAP.md`, the title
  nametable's *printing-program* table is **`$B91C-$BD7B`** (this is the table whose mid-range
  byte `$BC26` was the site of the historic KIL corruption from the STUDY 2P-tail relocation —
  see `dr-mario-te-freeze-rootcause` memory). `bkgTitle` at `$B936` sits inside this range,
  confirming `$B91C-$BD7B` is the live title draw table, walked fresh on every `toTitle` call.

## 2. Patch-site cross-reference (this cart's active flags only)

From `patch_cartridge_copro.py`, addresses computed against `drmario_v28cs.nes`
(`file_offset - 0x10 + 0x8000 = CPU addr` for the fixed 32KB region):

| Site | CPU addr (approx) | What it touches | Overlaps title footprint? |
|---|---|---|---|
| `HOOK_FILE = 0x37CF` | `~$B7BF`, inside `getInputs`, immediately after the **second** `addExpansionCTRL` call and before `_pressedVsHeld` (confirmed via `prg/drmario_prg_general.asm:325-360`; matches the `dr-mario-p1-side-and-input-model` memory's "tail of addExpansionCTRL" note) | 3-byte `JMP $FB00` replacing code inside the controller-read routine | **No.** This is CODE in the input path, not a data table. It runs every frame including title frames (title needs button reads), but doesn't write PPU/CHR/nametable state. |
| `BLOB_FILE = 0x7B10` → `$FB00` | driver trampoline body | `$FB00-$FCFF`, per `FREE_SPACE_MAP.md` explicitly "free in the copro carts" (driver owns it) | **No.** Confirmed dead space, not in any of the 21 `RB6C2_PRINT` tables. |
| `WRAP_CPU = 0xFF54`, asserted `<= 0xFFD2` | "dead-v17 window" | trampoline entry stub | **No.** `$FF30-$FFCF` is documented dead (old embedded-AI code, superseded), well clear of `$B91C-$BD7B`. |
| `P1AI_CPU/P1SWAP_CPU = 0x9000/0x9200` | P1-native d1 AI + swap_eval | lives in **unit1, bank 2** (the *added* 16KB bank at `UNIT1_CPU=0x8000`, switched in by the mapper only while the driver code runs) | **No — different PRG bank.** The base ROM's own `$9000-$92FF` content (in the *original*, always-mapped 32KB bank) is untouched; this is bank-switched CPU-address reuse, not a byte overwrite of the base ROM. Real collision risk here would be a *bank-switch race* (driver bank left switched in while game code executes), not a table overlap — see caveat below. |
| STUDY evac sites `$9FF8`/`$A371`/`$BE56`/`$BC26` | 2P-study tail (part2-part3c) | **Not applied — `DRSTUDY` is OFF on this cart** (see header). Vanilla bytes remain, including at `$BC26` inside the title table. | **N/A — mechanism not engaged.** |

**Caveat (not fully resolvable statically):** the P1-native AI executes from a switched-in
bank. If the mapper's bank-select register were left pointing at bank 2 at the exact moment the
game's own code (e.g. `toTitle`, which is in the base/fixed bank) tries to execute or read data,
the CPU would read AI code as game code/data — this is the general class of bug that would look
like "garbled" rather than "flashing" (wrong tiles/bytes, not just fast transitions). I could not
find, by static reading, any code path where the driver leaves the bank switched in across a
return to the base bank's control flow — the hook is a call-out/return pattern
(`JMP $FB00` → trampoline → back into `getInputs`), and mapper 100 bank-select writes should be
symmetric (switch in, do work, switch back) — but I have not traced the *exact* bank-select byte
sequence around every driver entry/exit to prove no race exists. **This is the one place a
dynamic test would add real confidence** (see §4).

## 3. Q2 — is the flashing "cosmetic strobe" or "corrupted tiles"?

`DRNAVDWELL` (default ON, holds ~180 real frames/~3s at the title so branding is visible —
`patch_cartridge_copro.py:452-465`) is **explicitly `DRNAVDWELL=0` on this cart**. Per the same
comment block: "DRNAVDWELL=0 reverts (byte-identical nav)... nav still lands VS-CPU, just ~4
hooks later" (`NAV_M4=4`, i.e. ~2 frames at the driver's 2-hooks/frame rate). Combined with
`toTitle`'s vanilla title animation running at a 16-frame CHR-bank-swap period and the cursor's
own render logic, a title visible for only ~2 frames between rematches — repeated for every
match all night — reads exactly like a "flash": the eye catches a strobe of title art, not a
static screen, because the nav is deliberately racing through it as fast as the code allows.

I found no code path where `toTitle`'s own controller reads happen *before* its background/
palette copy completes (button reads only start inside `title_mainLoop`, which runs after
`finishVblank_NMI_on`), so the fast START press cannot interrupt the vanilla nametable copy
mid-write. That argues against genuine tile corruption from the nav timing, and for "legitimate
but very fast, by-design screen strobing" as the dominant explanation. I cannot fully rule out a
1-2 frame glitch from the bank-switch race noted in §2 above without a dynamic capture.

## 4. Q3 — save-hotkey-ignored / 0-byte saves

Traced the actual MiSTer NES core savestate FSM (`~/projects/NES_MiSTer/rtl/`):

- `savestate_ui.sv` decodes F1-F4/gamepad-SS input into `ss_save`/`ss_load` pulses — **no
  screen-mode gating at this layer** (answers the "does the framework refuse saves during
  certain modes" sub-question: not by policy/allowlist).
- `rtl/savestates.vhd:158` (`SAVE_WAITSETTLE`, also `:251` for load): the FSM will not leave this
  state until its `paused` input has been high for `SETTLECOUNT=100` (`:57`) consecutive cycles;
  if `paused` drops even once, `settle` resets to 0 (`:159-160`). **The FSM never reaches the
  actual memory-dump states if `paused` never asserts — this is precisely "created at size 0,
  never settled."**
- `NES.sv:704-709`: `sleep_savestate` (driven by the save/load request) feeds `pausecore`.
- `rtl/nes.v:867-891` instantiates `savestates`, wiring its `paused` port to
  `corepause_active_delay`.
- `rtl/nes.v:343` — the actual latch condition:
  `corepause_active` only asserts when `pausecore` is up **and** `div_cpu/div_ppu/div_sys`
  clock-divider phase aligns **and** `~freeze_clocks` **and** `is_in_vblank_paused` **and**
  `~pause_cpu` **and** `cpu_Instrnew` (CPU is between instructions).

**This means the pause handshake — and therefore any savestate — categorically cannot complete
if either (a) the 6502 never reaches a clean instruction boundary again (a true KIL/JAM opcode
halts fetch permanently), or (b) the PPU never re-enters vblank (e.g. rendering left disabled,
as `toTitle` itself does transiently via `NMI_off`/`finishVblank_NMI_on`).** Both are exactly the
candidate mechanisms task #42 (Freeze #5, black-screen wedge, save-states dead, same day
2026-08-02 ~13:47, recurred ~16:10 per `experiments/freeze5_20260802/f5b_a_160947.png`) already
lists ("KIL execution... PPU write corruption... copro clock-domain lockup"). I did not find
evidence linking the 21:00 title-flash sighting to a CPU hang specifically — the ~21:00 event's
own report says mid-match video was clean and the title *did* eventually advance (auto-rematch
kept running), which is inconsistent with a true hard hang at that moment. I read this as: the
RTL trace explains *why* Freeze #5's save-states go to 0 bytes, and gives task #42 a concrete
hardware-level mechanism to test against, but it does **not** independently prove the 21:00
title flashing and Freeze #5 are the same event — they may just share exposure to the same
`toTitle`/`NMI_off` code path (see below).

**Confound worth flagging to whoever runs the overnight ledger:** the QA harness's own polling
scripts intentionally trigger visible MiSTer savestates —
`experiments/duel_ledger/track.sh` (90s interval, started **2026-08-02 21:56:24**, i.e. *after*
the 21:00 sighting, confirmed via `ps -eo lstart`) and its successor `track2.sh`
(3 min interval, via `tools/livecatch/ring_capture.sh`, started 22:31:47). `ring_capture.sh`'s
own header says outright: **"THE USER SEES THIS. Triggering a save-state flashes MiSTer's
on-screen message"**, and separately documents a known scp-side "0-byte race" (a partial-write
transfer race, already mitigated by polling for final size + settle + md5 verification
device-side) — this is a *different* 0-byte phenomenon from the FSM-level one above (transfer
race vs. core-level stuck FSM) and should not be conflated with it. Because `track.sh` started
after 21:00, it is **not** the cause of the reported sighting, but any *future* "flash" reports
during this overnight run should first be checked against the ledger's own save-trigger
timestamps in `experiments/duel_ledger/ledger_*.csv` before being attributed to the cart.

## 5. Recommendation

No ROM-level fix is indicated — no collision found, and the STUDY-evac mechanism that caused the
historical `$BC26`/`$BE56` corruption isn't engaged on this cart. Two follow-ups, both dynamic
(cannot be settled by static reading):

1. **Confirm Q2 is cosmetic, not corrupt:** capture a screenshot or short recording spanning a
   title transition (Mesen with the driver-nav build reproduces `DRNAVDWELL=0` timing; or a
   MiSTer screenshot burst timed off the ledger's own match-end detection) and check whether the
   title tiles/palette during the ~2-frame window are ever wrong values vs. just a fast normal
   frame of the vanilla title. If confirmed cosmetic-only, the fix (if wanted) is trivial: set
   `DRNAVDWELL=1` (or a short `DRNAVDWELL_F`) on future spectator/demo builds so the title holds
   long enough to read as "clean" rather than "flash" — pure UX polish, no defect to fix.
2. **For task #42 (Freeze #5):** when it recurs, in addition to the existing WATCH list, capture
   whether `cpu_Instrnew`-class activity is still happening (if a Mesen-side co-sim or debug
   read is available) — the RTL trace above gives a specific, testable prediction: if this is a
   true CPU halt, no savestate will EVER complete no matter how long you wait past
   `SETTLECOUNT=100` cycles, whereas a transient PPU/vblank glitch should self-clear within a
   frame or two. That distinguishes "hard hang" from "long stall" without new instrumentation.

## References

- `~/projects/dr-mario-mods-wt/driver-nav/patch_cartridge_copro.py` (patch site definitions, flag
  defaults, STUDY-evac mechanism)
- `~/projects/dr-mario-mods-wt/driver-nav/tmp/refs/dr-mario-disassembly/` (base ROM disasm:
  `prg/drmario_prg_game_logic.asm`, `prg/drmario_prg_general.asm`, `prg/drmario_prg_visual_*.asm`,
  `data/drmario_data_nametables.asm`, `data/drmario_data_game.asm`)
- `~/projects/dr-mario-te-v8.2/FREE_SPACE_MAP.md` (title/settings printing-table ranges,
  allocation rules)
- `~/projects/NES_MiSTer/rtl/savestates.vhd`, `rtl/nes.v`, `NES.sv`, `rtl/savestate_ui.sv`
  (savestate FSM + pause handshake)
- `~/projects/dr-mario-qa-wt/experiments/duel_ledger/track.sh`, `track2.sh`,
  `tools/livecatch/ring_capture.sh` (QA harness's own known OSD-flash / scp-race artifacts)
- `~/projects/dr-mario-qa-wt/experiments/freeze5_20260802/` (Freeze #5 screenshots, same-day)
- Related task-system items: #9 (DRNAVDWELL title hang, completed), #42 (Freeze #5, in progress)
- Related memories: `dr-mario-navdwell-rootcause`, `dr-mario-pocket-freeze-storm`,
  `dr-mario-te-freeze-rootcause`, `dr-mario-free-space-rules`, `dr-mario-p1-side-and-input-model`
