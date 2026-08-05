# eval47 fixtures

## user_flag_20260803_slot4.ss

PROVENANCE CORRECTION (supersedes the adding commit's message): the slot-4
save was NOT a user hotkey. It was the duel tracker's own 180-second ring
capture ("SAVE TO STATE 4" OSD flash); the user saw the flash while watching
the live duel and reported that the board on screen at that moment was "a
good example of bad vertical placements." The state was scp'd off the MiSTer
before the next tracker tick could overwrite the slot. Same board either way
— the capture is the frame the user was looking at.

Content (decoded, P2 = Combo Stomper, 29 viruses vs P1's 46):
- **Exhibit A, col 5**: fresh Y-top/R-bottom vertical on a yellow single atop
  a 12-tall alternating (Y/R barber-pole) column — BOTH halves stranded under
  terms47.g_stranded at the moment of placement.
- **Exhibit B, col 7**: R/R vertical pair on a blue single (self-matching, so
  not "stranded" by the neighbour rule, but mismatched support two rows above
  a red virus it now can't reach).

Use: real-silicon regression board for the #47 terms — g_stranded must flag
Exhibit A's two halves; the height tax must make extending col 5 expensive.
Decode recipe: CPU RAM at file offset 0x102B08; P1 board +$0400, P2 +$0500;
EMPTY=0xFF, virus high-nibble 0xD, colour low-nibble {0:Y,1:R,2:B}, link
high-nibble {4:top,5:bottom,6:left,7:right,8:single}.
