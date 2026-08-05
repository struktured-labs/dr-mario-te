Dr. Mario Training Edition (TE)

A ROM hack that transforms the pause screen into a study mode for practicing
Dr. Mario strategies and analyzing virus/capsule positions mid-game — plus a
built-in VS CPU mode so you always have a practice opponent.

*** IF YOU ARE RUNNING v6: UPGRADE ***
--------------------------------------
v6 can lock up: one of Study Mode's code fragments sat at an address the game
also executes as part of a print table. v9 relocates everything into documented
free space. Also fixed since v6: the "floating capsule after START" bug in
2-player, level-select corruption, and blanked counters while paused.

DOWNLOAD
--------
https://github.com/struktured-labs/dr-mario-te/raw/main/release/drmario_te_v9d.bps

(BPS patch — use Flips, beat, or any BPS-capable patcher. The BPS format
self-verifies against the correct base ROM. After patching, your ROM's MD5
should be 0f8f5d89dcf938144d24977d4faf2628. Previous releases remain
available in the repository.)

FEATURES
--------
- Playfield remains fully visible when paused (no blackout)
- "STUDY" text displayed at the top of the screen instead of "PAUSE"
- The falling capsule stays visible during pause, frozen exactly where it
  was — study the position with the piece in the air
- FIXED in v9: the next-pill preview during pause now genuinely renders
  above EACH player's own bottle in 2-player modes (in v6 it was drawn at
  the 1-player position over the right-hand board, and Player 2's preview
  was missing entirely)
- NEW in v9: the LEVEL and VIRUS counters stay readable while paused —
  and the virus count is BCD-correct (an earlier internal build rendered
  48 as "72"; v9 decodes the counter the way the game itself does)
- STUDY text is positioned per-mode (raised in 2P so it clears the score
  header and stays legible)
- Works identically in 1P and 2P modes

VS CPU MODE
-----------
Press SELECT on the title screen until the heart sits on 2 PLAYER GAME,
then press SELECT once more to arm CPU control of Player 2. Confirmation:
the level-select screen pins both players' level/speed together when armed.
Start the game and Player 2 plays itself — no second human needed. (A
visible "VS CPU" menu label is planned for a future release.)

The AI is an in-cartridge brain running on the NES's own CPU — a serviceable
practice opponent that will keep improving as a much stronger engine is
scaled down to fit stock hardware. Feedback welcome.

KNOWN LIMITATIONS
-----------------
- Dr. Mario throwing animation sprite disappears during pause
- Dancing virus sprites (magnifying glass) disappear during pause

These are drawn by a game routine the pause loop skips; the board, viruses,
capsules, previews, and counters are all preserved.

COMPATIBILITY
-------------
Base ROM: Dr. Mario (USA) Rev 0 - MD5: d3ec44424b5ac1a4dc77709829f721c9
Patched:  MD5: 0f8f5d89dcf938144d24977d4faf2628 (CRC32 5a7e5052)
Tested on: Mesen 2 (v9 verified); the v6 lineage also ran on Nestopia,
MiSTer FPGA NES core, and Analogue Pocket — mapper is unchanged
Mapper: MMC1 (no compatibility issues expected)

CREDITS
-------
Patch created with assistance from Claude Code (Anthropic).
Built against two community disassemblies: Nostaljipi's dr-mario-disassembly
(symbol vocabulary and the free-space catalogue Study Mode lives in) and
Brian Huffman's drmario ca65 disassembly (Rev 0 / Rev A base verification).
Dr. Mario (c) Nintendo. This patch distributes no Nintendo code.

VERSION HISTORY
---------------
v9 - Crash fix (v6 print-table collision relocated to free space);
     2P pause previews actually per-player; level-select corruption fix;
     LEVEL/VIRUS counters visible and BCD-correct while paused;
     (VS CPU arming unchanged: SELECT x2 at title;
      v7/v8 were internal builds, never published)
v6 - Study upgrade: frozen falling capsule + per-player next-pill previews
     during pause; per-mode STUDY text position; experimental built-in CPU
     opponent (SELECT x2 at title); release moved to BPS format
v5 - Fixed FEVER menu text corruption
v4 - Fixed title screen Mario eyes
v3 - Moved custom tiles to avoid conflicts
v2 - Added STUDY text with custom tiles
v1 - Initial release (visible playfield during pause)
