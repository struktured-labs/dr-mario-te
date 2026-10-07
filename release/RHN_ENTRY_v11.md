<!-- romhacking.net entry text for TE v11 (update of hack #9292). Source of truth for the paste;
     the full submission sheet (form fields, hashes, checklist) is in the release package SUBMIT.md.
     Policy: the in-cart CPU opponent is NOT advertised (owner directive); see SUBMIT.md for the optional line. -->

Dr. Mario Training Edition (TE)

A practice hack for Dr. Mario. Pause the game and the screen stays up so you
can STUDY the position -- and when a game or a round ends, the final board
stays on screen, so you can see exactly how it was won and lost.

NEW IN v11: 1-PLAYER GAME OVER STUDY SCREEN
- Top out in a 1-player game and your board is no longer wiped: no GAME
  OVER box, every virus and capsule stays where it was, including the
  capsule that had nowhere to go.
- The blinking START prompt moves below the bottle, off the board.
- START continues exactly as before (level select, high score).
- Also: the title screen reads V11.00 SL.

END-OF-ROUND STUDY SCREEN, 2 PLAYERS (since v10)
- When a player tops out: no X-sign virus over the loser's bottle, and the
  loser's lower half is no longer wiped.
- Match final (third win): no GAME OVER box over the two bottles, whether
  the match ended by a top-out or by clearing the last virus.
- Both boards stay exactly as they were until you press START; the next
  match starts clean.

STUDY MODE
- START during play pauses without blanking: "STUDY" at the top, the
  bottle, viruses and the falling capsule frozen in place.
- The next-capsule preview stays visible -- in 2-player games each
  player's preview above their own bottle.
- LEVEL and VIRUS counters stay readable. START again resumes cleanly.

HOW TO PATCH
Apply the IPS to the HEADERED Dr. Mario (Japan, USA) ROM, original
release (Rev 0, 65,552 bytes). Works with the classic iNES header and the
No-Intro NES 2.0 header. Not for Rev 1 / Rev A, and not for a headerless
file. The included BPS checks the source file and accepts only the
classic iNES-headered ROM (CRC32 B1F7E3E9). Hashes are in the readme.

KNOWN LIMITATIONS
- While paused, the Dr. Mario throwing figure and the dancing viruses in
  the magnifying glass are not shown (the board, capsules, previews and
  counters are).

Standard MMC1 (mapper 1), same size as the original -- runs on accurate
emulators and on MiSTer. Source, build scripts and tests:
https://github.com/struktured-labs/dr-mario-te
