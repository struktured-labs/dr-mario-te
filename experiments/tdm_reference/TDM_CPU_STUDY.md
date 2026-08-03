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
- Working Lua script (final "pre-hold Right" decisive-test variant) is
  saved at `experiments/tdm_reference/lua/nav_probe.lua`. Key screenshots
  saved at `experiments/tdm_reference/shots/`:
  - `gameselect_unconfirmed.png` — the reproducible unconfirmed Game
    Select screen (Tetris/Dr. Mario/Mixed Match icons visible).
  - `right_hold_075_autoadvance.png` — ~75 frames into holding Right with
    no Start, mid-transition to something else (not a moved cursor).
  - `down_hold_075_tetris_submenu.png` — where every early attempt ended
    up: the Tetris submenu, never Dr. Mario.
  - `prehold_right_at_gameselect_f3050.png` — Game Select, with Right
    already held continuously since frame 2900 (150 frames before this
    shot) — cursor still shows no sign of having moved off Tetris.
  - `prehold_right_then_start_lands_tetris_f3130.png` — the very next
    Start pulse after that sustained Right hold still confirms **Tetris**,
    not Dr. Mario — the decisive negative result that closed off the
    "input arrives too late" hypothesis.
- **Deterministic, reproducible recipe to reach the unconfirmed Game Select
  screen** (the part that *does* work, 100% reproducible from power-on):
  11 Start pulses, each 8 frames held, 300 frames apart (i.e. pulse at
  frames 0, 300, 600, ..., 3000; `frame % 300 < 8` while
  `frame <= 3008`). Confirmed by screenshot at frame 3048 across 3
  independent runs (v8, v9, v10 all agree).
- **Open problem to hand off:** getting off the default Tetris cursor at
  Game Select. See the "Navigation wall" callout in §3 for what was tried
  and ruled out (now 6 variants, including pre-holding Right before Game
  Select even renders — that was the strongest remaining hypothesis and it
  was refuted). Suggested next experiments, in order of cheapness:
  1. Try `l`/`r` shoulder buttons, and separately `a`/`b`/`x`/`y`, instead
     of d-pad `right`/`down` for Game Select cursor movement — some
     Nintendo menus of this era use shoulder buttons or face buttons for
     icon-grid navigation instead of the d-pad. Cheap to try (same script
     structure, swap the button name) and not yet tested at all.
  2. Take a screenshot **every single frame** (not every 15) from frame
     3000 to 3300, with Right held the whole time, to see frame-by-frame
     whether *anything at all* changes on screen in response to Right —
     even a half-pixel cursor nudge that later reverts would tell us
     input is reaching the game but being overridden, versus truly inert.
  3. Try `emu.addMemoryCallback` on a CPU-exec range instead of
     `startFrame` for input injection — `emu.createSavestate` already
     requires this callback type (see §3), so it's possible input sampled
     via this contract is also more reliable, and it would additionally
     unblock true savestate checkpoints (skip replaying 3000+ frames per
     experiment, which would make iteration much faster).
  4. RAM-diff the Game Select screen's state between two runs — one with
     Right held, one without — to see if *any* WRAM byte differs at all
     during the hold. If literally nothing differs, that's strong evidence
     Right truly isn't reaching the controller-read routine in this state
     (a Mesen2 SNES-core quirk specific to this game/screen), and the next
     step would be to test on a second SNES core (e.g. via `retroarch` +
     a libretro SNES core, both present on this box) to see if the same
     wall reproduces outside Mesen2 — if it doesn't, the bug is in Mesen2,
     not the game.
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
