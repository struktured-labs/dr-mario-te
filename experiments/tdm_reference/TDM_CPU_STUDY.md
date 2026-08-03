# Tetris & Dr. Mario (SNES) CPU opponent study

Task #45. Studying Nintendo's SNES "Tetris & Dr. Mario" (1994) CPU opponent as
a benchmark and personality reference for our NES Dr. Mario AI (task #33's
E/M/H knob design) and as prior art / exhibition content (Combo Stomper vs a
shipped commercial Dr. Mario AI).

## 1. ROM identity (verified)

Source: user's own dump, `~/gaming/Tetris & Dr. Mario.zip` (owns two physical
carts; research/preservation use).

| Field | Value |
|---|---|
| Archive member | `Tetris & Dr. Mario (USA).sfc` |
| File size | 1,048,576 bytes (1024 KB / 8 Mb) |
| SHA-256 | `3cdebbd8adc4bb6773a7995f542fdac49adefca71cba583255a1c1bf37ac3946` |
| Internal title | `TETRIS&Dr.MARIO` |
| Game code | ATFE |
| Layout | LoROM, FastROM, Map Mode $30 |
| SRAM | 0 KB (no battery save) |
| Header checksum / complement | `6005` / `9ffa` (internal, self-consistent) |

No copier header (file size is an exact power-of-two-aligned ROM size).
Mesen2's own SNES core parses it cleanly as LoROM/FastROM, matching the
header fields above — confirms this is a clean, unmodified USA retail dump.

## 2. Prior art sweep

No SNES-specific disassembly or RAM map exists publicly (unlike the NES Dr.
Mario, which has multiple disassemblies/RAM maps on Data Crystal). What does
exist:

- **The Cutting Room Floor** (`tcrf.net/Tetris_&_Dr._Mario`) documents a
  disabled options menu — includes a **computer/CPU difficulty
  configuration** screen, alongside input config and a sound test — that was
  cut from the shipped build. **Caution:** when this agent WebFetched the
  live TCRF page directly, the fetch tool detected and refused a prompt-injection
  payload embedded in the page content (attempting to direct an AI agent to
  perform destructive file operations). This reads as wiki vandalism aimed at
  AI browsing agents, not a TCRF editorial position — flagging here so future
  agents don't WebFetch that URL directly. The technical facts above were
  recovered instead via WebSearch snippets and two independent secondary
  sources (below), not the vandalized page.
- **unseen64.net** ("Tetris & Dr. Mario [SNES - Unused Stuff]") documents
  working Pro Action Replay codes that unlock the cut options menus directly:
  - `7E1E1B03` — Tetris options menu
  - **`7E1E7203` — Dr. Mario options menu** (the one that reportedly includes
    computer-difficulty configuration per TCRF)
  - `7E1E0E02` — Mixed Match options menu (enter via Tetris first)
  - `7E1E0E09` — a debug menu ("very difficult to get working")
  This gives a concrete, real RAM address (`$7E1E72`, SNES WRAM bank $7E) as
  a menu-select variable — a genuine foothold for RAM recon, not yet
  exploited (see §4).
- **Super Mario Wiki** confirms VS COM has exactly 3 CPU difficulty tiers,
  visually keyed to virus color: **Blue = Easy, Yellow = Medium, Red =
  Hard**. Matches the household scouting report (dr_lulu) that Hard is the
  top tier and "beatable with effort."
- GameFAQs/strategy-guide summaries confirm the VS COM flow: each side picks
  a **level** (virus count/height, 0-20ish per Dr. Mario convention) and a
  **game speed** independently of CPU difficulty; first to 3 match wins;
  multi-color clears send garbage to the opponent (same attack rule family
  as the NES game, see [[dr-mario-rom-attack-rule]]).
- No Game Genie/PAR codes specifically toggle CPU difficulty or AI behavior
  directly (only level/speed/piece-RNG cheats were found) — the
  cut-content route (`7E1E7203`) is the only lead toward the actual
  difficulty variable's address.

## 3. Live navigation (Mesen2, headless Lua)

Tooling: Mesen2 (already built at `~/projects/dr-mario-mods/mesen2`, which
supports SNES since v2.0) driven via its file/CLI Lua bridge — no visible
window needed. Confirmed working API surface for this build:

- `emu.setInput({buttonName=bool,...}, port)` — **note the argument order is
  table-then-port**, not port-then-table (an example script in the Mesen2
  tree, `UI/Debugger/Utilities/LuaScripts/ReverseMode.lua`, confirms this;
  getting it backwards fails `luaL_checktype` silently on every frame with no
  visible error unless wrapped in `pcall`).
- `emu.takeScreenshot()` returns raw PNG bytes — cheap enough to call every
  frame for visual confirmation without a real display.
- `emu.createSavestate()` / `emu.loadSavestate()` — **do not work from a
  `startFrame` event callback** ("This function must be called inside an
  exec memory operation callback for the main CPU"); would need to be
  driven from an `addMemoryCallback` on a CPU-exec range instead. Not
  pursued this session — screenshots + deterministic replay were sufficient.
- `--enableStdout` + a file-based log (not `emu.log()`, whose routing to
  real stdout wasn't confirmed) is the reliable way to see script output
  from a backgrounded, headless launch.
- **The entire intro is on a fixed timer, independent of input.** Confirmed
  decisively: booting with **zero button presses at all** (only a continuous
  forced RAM write, see below) still clears the ELORG/Nintendo legal screen,
  the "Dr. Mario & Tetris"/"Tetris & Dr. Mario" logo loop, lands on Game
  Select by frame ~3000, auto-advances into the **Tetris** submenu, and
  keeps going all the way into live A-Type Tetris gameplay by frame 4800 —
  with nobody ever touching a control. This means every "duty cycle" theory
  from earlier in the session (sparse vs. frequent Start presses seeming to
  matter) was very likely a red herring: the screen was going to advance to
  Game Select around frame ~3000-3050 regardless of whether Start was ever
  pressed. What we'd been calling "navigation" for most of this session was
  actually racing against — not driving — the game's own uninterruptible
  attract-mode demo.

Game Select screen layout (confirmed via screenshot): Tetris icon top-left,
**Dr. Mario icon top-right**, Mixed Match icon bottom-left, "GAME SELECT" /
"PRESS START BUTTON" / Nintendo copyright bottom-right.

### Experiment 0 (team-lead directive): the PAR code as a nav bypass

Tried the unseen64.net PAR code `7E1E7203` (unlocks the cut Dr. Mario
options menu, §2) two ways, both from a fresh boot with **no button
presses at all**, to see if it could reroute the auto-advancing attract
demo away from Tetris and into a Dr. Mario/options context directly:

1. `emu.addCheat("7E1E7203", emu.cheatType.snesProActionReplay)` —
   **failed with "invalid cheat code"** despite the 8-hex-digit format
   matching Mesen2's own validator regex (`^[a-f0-9]{8}$`) and the enum
   ordinal (`snesProActionReplay = 6`, confirmed by dumping
   `emu.cheatType`'s contents) being exactly right. Root cause not
   determined — the C++ parser (`CheatManager::ConvertFromSnesProActionReplay`
   in `Core/Shared/CheatManager.cpp`) looked correct on inspection, so this
   may be a genuine Mesen2 bug in this build, or something subtle about how
   `LuaCallHelper` reads the packed `char[16]` cheat-code buffer. Not worth
   more time given the direct-write alternative below achieves the same
   effect.
2. Bypassed the cheat parser entirely: `emu.write(0x1E72, 0x03,
   emu.memType.snesWorkRam)` called **every single frame** from boot
   onward (this is literally what a real PAR/GameShark cheat does
   internally — sustained per-frame override, confirmed no write errors).
   **Result: no observable effect.** With this write active continuously
   from frame 1, the attract-mode demo proceeded exactly as it does with no
   cheat at all — legal screen, logos, Game Select, auto-confirm into the
   Tetris submenu, into live A-Type gameplay — never showing an options
   screen. Either the unseen64 code needs to be applied at a specific
   *already-in-game* state (not from a cold, pre-menu boot) that this test
   didn't reach, or the address mapping/game state machine differs from
   what unseen64 documented (possible ROM revision difference, though our
   hash matches a standard USA retail dump — see §1).

### Navigation wall (stopping point)

Reaching Dr. Mario requires moving the Game Select cursor off the default
Tetris icon before the auto-advance confirms it. **This did not work
across six independent timing variants and is where this session stopped**,
per the task brief's own guidance to report a wall rather than brute-force
it further:

- Sending `{right=true}` or `{down=true}` via `emu.setInput` immediately
  after arriving at Game Select, with *no* further Start press, produces no
  observable cursor movement over a 90-frame hold.
- **Pre-holding Right starting well *before* Game Select even renders**
  (asserted continuously from frame 2900, ~150 frames ahead of the ~3050
  arrival) — the experiment specifically designed to rule out a "screen
  ignores new input for its first few frames" effect — **still landed in
  the Tetris submenu**, identical to every other variant. This rules out
  that hypothesis: it isn't that Right arrives too late, it's that Right
  appears to have no effect on this screen's cursor at all, at any offset
  tested.
- Every attempt — 6 variants now, spanning hold durations, gap timings, and
  pre-vs-post-render timing — landed back in the **Tetris** submenu (1
  Player / 2 Player / VS.COM), never Dr. Mario, regardless of whether
  Right, Down, or nothing was held.
- The `"right"`/`"down"` key names themselves are correct (verified against
  `Core/SNES/Input/SnesController.cpp`'s `GetKeyNameAssociations()` in the
  Mesen2 source: lowercase `up`/`down`/`left`/`right`/`start`/`select`/`a`
  /`b`/`x`/`y`/`l`/`r`), so this isn't a button-name typo.
- Given the §3 discovery that the *entire* intro sequence, including Game
  Select, auto-advances on a fixed timer with zero input, the most likely
  explanation is that this attract-mode auto-play is simply
  **non-interruptible by direction input** on this particular screen (Start
  clearly *is* respected — it's what let us confirm into Tetris in earlier
  runs — but Right/Down apparently are not, at least not via
  `emu.setInput`). Whether a *real* player's controller would fare any
  differently is untested; this may be specific to how Mesen2's SNES core
  samples D-pad state versus Start/A/B during this demo mode, or it may be
  a genuine, surprising fact about the retail game's own attract-mode
  design (auto-play locked into showing off Tetris specifically, ignoring
  direction until Start is pressed to break out of *some* different, not
  yet identified, interaction path).

### Decisive discriminator (team-lead directive): is emulated input even alive?

The zero-input auto-advance discovery (§3) raised a sharper question: what if
*no* emulated input has ever reached the game at all, and the whole session's
apparent Start-press "confirms" were coincidental with the auto-advance's own
timer? Tested directly: two cold boots with an identical screenshot schedule
(same 17 checkpoint frames from 30 to 3900), one with **zero** input, one with
**Start held continuously from frame 0**.

**Result: input is alive.** Every checkpoint from frame 30 through 3000
matched byte-for-byte between the two runs (identical PNG sizes at every
single frame) — expected, since both runs are on the same auto-advance timer
before anything Start-sensitive happens. But at **frame 3100**, the two runs
diverge sharply: zero-input shows a blank black frame (247 bytes,
`discriminator_zero_f3100_blank.png`), while Start-held already shows a
rendering scene (1562 bytes, `discriminator_start_held_f3100_rendering.png`)
— visibly different content, not just a compression-size coincidence. This is
exactly the frame range where a Start-triggered confirm (title → Game Select,
or Game Select → Tetris submenu) would first become visible, so this is
strong, causal evidence that **Start reaches the game and measurably changes
its state** relative to no input at all. The "no input has ever reached the
game" hypothesis is refuted for Start specifically.

**Follow-up fix attempt** (the one the budget allowed): if a *continuous*
hold perturbs the state machine (as just proven for Start) where our earlier
*pulsed* Right/Down attempts didn't, maybe Right needed to be held
continuously **from true frame 0** — every earlier Right/Down experiment in
this session only started the hold once already near Game Select (frame
~2900 at the earliest). Tried it: Right held from frame 1 onward, Start added
in from frame 3200 to attempt a confirm. Byte sizes at frames 1200-2700 *do*
diverge from both the zero-input and Start-held baselines (proving Right is
also reaching the game and perturbing state, just as Start does) — but the
final outcome at frame 4500 is, again, **live Tetris A-Type gameplay**, not
Dr. Mario (`right_from_boot_still_tetris_f4500.png`). So the picture is now:
**both Start and Right demonstrably reach the game and perturb its internal
state** — this is not a dead-input or wrong-port problem — **but Right
specifically never flips the Game Select outcome away from the default
Tetris selection**, across all 7 variants tried (6 from the original wall
plus this one). The remaining puzzle is narrower than it looked an hour ago:
it's not "is input plumbed correctly," it's "why does this one screen's
cursor logic not respond to direction the way Start responds to confirm."

Per the team lead's budget (discriminator + one fix attempt), this is the
stopping point. Untried candidates most worth a future session's time, given
what's now known:
- Shoulder (`l`/`r`) or face (`a`/`b`/`x`/`y`) buttons for Game Select cursor
  movement — genuinely untested, and now higher-priority than before since
  we've ruled out "input is dead" as an explanation and there's precedent
  for non-d-pad menu navigation in some Nintendo titles of this era.
- Cross-core verification (`retroarch` + a libretro SNES core, or
  `snes9x-gtk`, both present on this box) to see if the same Right-inert
  result reproduces outside Mesen2 — if a second, independent SNES core
  shows the *same* wall, that's strong evidence it's a real fact about the
  game (or about how *all* emulators handle its input), not a Mesen2-specific
  quirk.

**Everything downstream of this point — an actual VS COM Dr. Mario match,
RAM recon (§4), and the behavioral profile (§5) — was not reached this
session.**

## 4. RAM recon (not yet reached)

Blocked on completing navigation into an actual VS COM Dr. Mario match (see
§3, §6). Once in a match, priority targets:

- P1/PSNES board array and P2(CPU)/PSNES board array (by analogy to the
  NES game's $0400/$0500-ish twin-board layout, see
  [[dr-mario-tile-encoding]] — expect a similar twin fixed-stride layout in
  SNES WRAM bank $7E, likely reachable by diffing WRAM snapshots across
  known virus placements).
- The CPU difficulty variable, ideally corroborated against `$7E1E72`'s
  neighborhood (the confirmed menu-select address from the unused options
  menu — cut menus and shipped VS COM difficulty selection may share
  underlying state).
- Any single byte/counter that changes exactly at CPU "decision moments"
  (candidate: an input-injection pattern analogous to how the NES
  cart-side AI's writes were found, see [[dr-mario-p1-side-and-input-model]]
  for the analogous NES investigation).

## 5. Behavioral profile (not yet reached)

Deferred — needs §4 (a running match) first. Household scouting report
(dr_lulu, strong player) stands as the only current behavioral data point:
"good and fast, but doesn't do combos"; Hard mode "beatable with effort."
Verifying the "doesn't do combos" claim on Hard specifically is the single
highest-value observation for task #33 personality-knob purposes, since our
own Combo Stomper's entire identity is chain/combo play
([[dr-mario-chain-attack-channel]]) — if confirmed, T&DM's Hard CPU
represents a *fast, non-combo* archetype at the opposite end of our own
knob space, which is a clean two-point calibration for E/M/H tuning.

## 6. Session handoff / resume state

- ROM + hashes: §1, no further work needed.
- Prior art: §2, complete for this session's search budget.
- Three Lua scripts saved at `experiments/tdm_reference/lua/`:
  `nav_probe.lua` (the pre-hold-Right decisive-test variant from the
  original 6-variant wall), `discriminator.lua` (the zero-input vs
  Start-held A/B comparison, mode selected via a `discriminator_mode.txt`
  marker file — see the script header for the launch recipe), and
  `right_from_boot.lua` (the Right-held-from-frame-0 follow-up). Key
  screenshots saved at `experiments/tdm_reference/shots/`:
  - `gameselect_unconfirmed.png` — the reproducible unconfirmed Game
    Select screen (Tetris/Dr. Mario/Mixed Match icons visible).
  - `right_hold_075_autoadvance.png` / `down_hold_075_tetris_submenu.png`
    / `prehold_right_at_gameselect_f3050.png` /
    `prehold_right_then_start_lands_tetris_f3130.png` — the original
    6-variant wall (all landed in Tetris regardless of Right/Down timing).
  - `discriminator_zero_f3100_blank.png` vs
    `discriminator_start_held_f3100_rendering.png` — the proof that Start
    input reaches the game (blank vs. rendering content at the identical
    frame, zero-input vs. Start-held).
  - `right_from_boot_still_tetris_f4500.png` — the 7th variant (Right held
    from true frame 0, combined with Start later): still Tetris.
- **Deterministic, reproducible recipe to reach the unconfirmed Game Select
  screen** (the part that *does* work, 100% reproducible from power-on):
  11 Start pulses, each 8 frames held, 300 frames apart (i.e. pulse at
  frames 0, 300, 600, ..., 3000; `frame % 300 < 8` while
  `frame <= 3008`). Confirmed by screenshot at frame 3048 across 3
  independent runs (v8, v9, v10 all agree).
- **Open problem to hand off:** getting off the default Tetris cursor at
  Game Select. This is now narrower than it first looked. Confirmed facts
  (see the "Decisive discriminator" callout in §3):
  - Emulated input is **not dead** — both Start and Right demonstrably
    reach the game and perturb its internal state (proven by frame-exact
    PNG divergence against a zero-input control, across 2 independent
    A/B comparisons).
  - Right specifically never changes the Game Select outcome, across **7**
    independent variants (hold-after-arrival, pre-hold-before-render,
    continuous-hold-from-frame-0, combined with a later Start, at multiple
    hold durations) — always Tetris, never Dr. Mario.
  - So the wall is not "is input plumbed correctly" (settled: yes) — it's
    "why doesn't Right's *effect* on the state machine ever manifest as
    moving this specific screen's default selection." Suggested next
    experiments, in order of cheapness:
  1. Try `l`/`r` shoulder buttons, and separately `a`/`b`/`x`/`y`, instead
     of d-pad `right`/`down` for Game Select cursor movement — some
     Nintendo menus of this era use shoulder buttons or face buttons for
     icon-grid navigation instead of the d-pad. Cheap to try (same script
     structure, swap the button name) and not yet tested at all. Now the
     single highest-priority untried lead.
  2. Cross-core verification: try `retroarch` + a libretro SNES core, or
     `snes9x-gtk` (both present on this box, `snap list` confirms
     `snes9x-gtk`), to see if the same "Right never flips Game Select"
     result reproduces outside Mesen2. If it doesn't reproduce on a second,
     independent core, the bug is Mesen2-specific; if it does, it's a real
     fact about the game (or a fact about all current SNES emulators'
     handling of this specific input sequence).
  3. Take a screenshot **every single frame** (not every 15) from frame
     3000 to 3300, with Right held the whole time, to see frame-by-frame
     whether the divergence we found (proof Right perturbs *some* WRAM
     state) ever shows up as a visible cursor movement that then silently
     reverts, versus never appearing at all.
  4. Try `emu.addMemoryCallback` on a CPU-exec range instead of
     `startFrame` for input injection — `emu.createSavestate` already
     requires this callback type (see §3), so it's possible input sampled
     via this contract is also more reliable, and it would additionally
     unblock true savestate checkpoints (skip replaying 3000+ frames per
     experiment, which would make iteration much faster).
  5. As a fallback if the wall persists: try genuinely random/exploratory
     input (all 12 buttons individually, held then released, one at a time,
     from the Game-Select-unconfirmed state) — brute-force but bounded
     (12 short experiments), and would definitively answer "does *any*
     button move this cursor" before concluding the auto-advance is
     unconditionally locked to Tetris.
- Mesen2-specific traps worth remembering for next time (cost real time
  this session):
  - `emu.setInput(buttonsTable, port)` — table first, port second (an
    example script in the Mesen2 tree,
    `UI/Debugger/Utilities/LuaScripts/ReverseMode.lua`, confirms this;
    reversed args fail `luaL_checktype` silently every frame unless
    wrapped in `pcall`).
  - Single-instance: always confirm zero prior Mesen processes with
    `pgrep -af Mesen` before launching. Mesen2's SingleInstance mechanism
    silently forwards args to an already-running instance's *already-open*
    script window instead of reloading edited script content on disk —
    this looked exactly like "my edits aren't taking effect" and cost
    significant time before being diagnosed.
  - `emu.createSavestate`/`emu.loadSavestate` require a CPU-exec memory
    callback context, not a `startFrame` event callback (raises "This
    function must be called inside an exec memory operation callback for
    the main CPU").
- Do **not** re-fetch `tcrf.net/Tetris_&_Dr._Mario` directly (see §2
  caution) — use WebSearch snippets or the unseen64.net/mariowiki mirrors
  of the same facts instead.

## 7. Personality reference (task #33) — preliminary

Too early for a full mapping (needs §5's behavioral profile), but the E/M/H
color-coded tiers give an immediately reusable UX pattern: Nintendo shipped
exactly 3 named difficulty tiers, visually distinguished by the opponent's
virus color, with no numeric difficulty exposed to the player. Worth
mirroring the *presentation* (3 tiers, thematically colored/labeled) even if
our own knob internals differ, since "Hard but beatable with effort" is
apparently an achieved, well-regarded design target on real hardware
(per dr_lulu) — a plausible target feel for our own Hard tier.
