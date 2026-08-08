# Dr. Mario Training Edition v9

A ROM hack that combines a **VS CPU** mode (play against an AI-controlled Player 2) with an
enhanced **Study Mode** pause — freeze the game mid-play and study the board, the falling
capsule, the upcoming pill, and the level/virus counters.

## Download

**Download BPS Patch (v9): `drmario_te_v9d.bps`**

Apply against an unmodified *Dr. Mario (USA)* ROM with any BPS-capable patcher
(e.g. [Floating IPS / beat](https://www.romhacking.net/utilities/1040/)).

## Why v9 matters if you have v6

**v6 — the version currently published — has a crash.** Study Mode's fifth code fragment
was placed at `$BC26`, which the game also executes as part of a print table; on that path
the CPU hits an illegal opcode and the game locks up. v9 fixes it, along with two other
defects v6 shipped with. If you are running v6, this is a recommended upgrade.

## Fixed in v9

- **Study Mode freeze (crash)** — the `$BC26` collision is gone. All five Study fragments
  were merged into a single 83-byte block relocated to genuinely free space at `$FB80`,
  so nothing sits inside the game's own tables any more.
- **"Floating capsule after START" in 2-player** — in v6/v8 the paused preview was drawn at
  the 1-player default position, i.e. floating over the *right-hand* board regardless of
  whose pill it was, and Player 2's preview was never drawn at all. Both previews now
  render above their own boards.
- **Level-select garble** — a Study fragment used to live inside the level-select print
  table and corrupted that screen. It no longer does.
- **Blank counters while paused** — the pause routine blanks the LEVEL and VIRUS digits.
  v9 redraws all eight of them, so the counts stay readable in Study Mode.
- **Virus count showed the wrong number** — the virus counter is stored as BCD, not binary.
  A first attempt at redrawing it divided by ten and rendered 48 viruses as "72". v9 splits
  the byte into nibbles for VIRUS (BCD) and keeps the divide for LEVEL (genuinely binary),
  which is what the game's own drawing code does.

## Features

- **VS CPU mode** — press SELECT on the title screen until the heart sits on
  2 PLAYER GAME, then press SELECT once more to arm CPU control of Player 2
  (the level-select screen pins both players' level/speed together when armed —
  that is your confirmation). Player 2 is then driven by a heuristic AI with a
  human-like move cadence. There is no separate menu line yet; a visible
  "VS CPU" label is planned.
- **Study Mode pause** — pressing START during play freezes the game while keeping the
  screen rendered, so positions can be studied:
  - "STUDY" text at the top of the screen instead of "PAUSE"
  - The full bottle, all viruses, and the falling capsule(s) stay visible and frozen
  - The next-pill preview stays visible — in 2-player and VS CPU, **both** players'
    previews, each above its own board
  - The LEVEL and VIRUS counters stay readable *(new in v9)*
  - Pressing START again resumes cleanly with no corruption

## Known Limitations

- The Dr. Mario throwing figure and the magnifier viruses are not shown while paused (these
  decorative sprites are built by a game phase the freeze skips). The study-relevant
  content — bottle, viruses, falling capsule, next-pill preview, and counters — is shown.
- In VS CPU / 2-player the "STUDY" text is lifted to the very top of the screen so it clears
  the two-player header and stays legible.

## Compatibility

- **Base ROM:** Dr. Mario (USA) — MD5 `d3ec44424b5ac1a4dc77709829f721c9`, CRC32 `b1f7e3e9`
- **Patched ROM:** MD5 `0f8f5d89dcf938144d24977d4faf2628`, CRC32 `5a7e5052`
- **Mapper:** standard MMC1 (mapper 1) — accurate NES emulators and the MiSTer NES core
- 912 bytes differ from the clean base.

## Validation

Everything below was measured on the **patched ROM's own bytes** under Mesen, not inspected
by eye. Logs are in `dr_mario_rl/tmp/study2p/`.

| check | result |
|---|---|
| 2-player Study: both previews above the correct boards, text lifted | **13/13 assertions pass** (`qa_v9d/`) |
| 1-player regression: preview at its 1P default, text NOT lifted | **11/11 assertions pass** (`qa_v9d_1p/`) |
| No Study freeze | pass — reaches play and renders STUDY |
| Level-select not garbled | nametable hash identical to the known-clean carts, and **different** from a cart that still has the old fragment at `$BE56` (`qa_v80_1p_hash/`) |
| Counters correct and BCD-safe | 84 viruses / level 20 render correctly before **and** after pause |
| Digit routine exhaustively checked | 656 + 404 py65 runs over the ROM bytes across all 0-99 pairs |

The level-select check is deliberately two-sided: a cart that still carries the defect
produces a *different* nametable (9 fewer non-blank tiles), which proves the test can see
the garble it is being used to rule out. See `LEVELSELECT_GARBLE_ASSERTION.md`.

## Credits

- Dr. Mario © Nintendo. This is an unofficial fan patch and distributes no Nintendo code —
  you must supply your own copy of the original ROM.
- Training Edition hack, VS CPU AI, and Study Mode by Struktured Labs.

Two community disassemblies made this possible, and both were genuinely used, for
different things:

- **Nostaljipi** — [dr-mario-disassembly](https://github.com/Nostaljipi/dr-mario-disassembly)
  (ASM6f, Rev A, fully labelled). The source of the symbol vocabulary this hack is written
  against — the RAM/zero-page map and the input, pause, combo and drawing routines. Its
  `unused/` directory, which documents each free region of the ROM, is a specific debt:
  Study Mode's code lives at `$D2CC`, one of the regions catalogued there
  (`unused/drmario_unused_data_d2cc.asm`). Finding that space by hand would have been the
  hard part.
- **Brian Huffman** — [drmario](https://github.com/brianhuffman/drmario) (ca65, builds
  Rev 0 **and** Rev A with `make test` md5 verification). Used to establish that this
  patch's base is the USA **Rev 0** ROM and not Rev A — the two are different images, and
  a patch applied to the wrong one produces garbage.

Nostaljipi's disassembly in turn credits Sour (author of the Mesen emulator, whose debugger
this project also leans on heavily), Data Crystal, and The Cutting Room Floor.

- Patch format: BPS (beat).
- Dr. Mario is a trademark of Nintendo. This project is unaffiliated with and unendorsed by
  Nintendo.
