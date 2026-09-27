# Game-over occlusion hazard: CHECKED, RULED OUT for our scoring window

Raised 2026-09-01 from an owner observation on the **TE ROM**: a virus on the RIGHT EDGE
was concealed by the game-over screen. The hazard if it transferred to our cart is exact
and would have been invisible: an occluded cell decodes as EMPTY, empty reads as FREE,
and FREE reads as **ADDRESSABLE** — so occlusion would systematically INFLATE the exposure
figure that sizes the whole experiment, while producing a clean, plausible board rather
than an error. Column 5 is the right escape gate, so `c5 free` was the single most
exposed result.

## Finding: NEGATIVE for our cart, in the window the scorer uses

**1. No static GAME OVER overlay covers the bottle during the death hold.** Olive
coverage (the MATCH_OVER box signature, RGB 189,184,37) of the dying seat's bottle
interior is FLAT across the whole death: 0.123 / 0.125 / 0.106 / 0.130 / 0.106 / 0.125 /
0.117 at lock-30, -10, -1, +0, +10, +30, +60 frames. No spike at the death — that
baseline is the yellow viruses and capsules, not a box.

**2. Cells DO disappear, but ~0.5 s AFTER the lock, and it is the death ANIMATION, not a
localized right-edge occlusion.** Same-seat, cells occupied at lock-1 and empty later:
`lock+5 -> 0`, `lock+15 -> 0`, `lock+30 -> 28 cells across columns 0,1,2,3,5,6,7`,
`lock+60 -> 42 across all eight`. A static overlay would take a fixed region; this takes
most of the board at once and grows.

**3. THE SCORER NEVER READS INSIDE THAT WINDOW.** `parent_board` walks back from the plug
hold to the last frame with a clear throat, which is strictly PRE-LOCK. Measured on all
**15** poll-indexed champion deaths available: every parent frame is at `hold-1`, and
cells lost versus 0.5 s earlier are **0-5** (ordinary play — a clear removing a few
cells), never the 28-42 that marks the animation. **Parent frames inside the death
animation: 0 of 15.**

⇒ **The 56% (5/9) exposure figure is NOT affected and does not need re-scoring.**

## My own error en route, recorded because it nearly produced a false positive

My first diff appeared to show exactly the predicted result — "2 cells lost, column 5" at
lock+20. It was an artifact of a badly constructed test: **I diffed P1's board across
P2's lock.** P1 was still alive and playing, so a capsule moving in its column 5 read as
occlusion at precisely the column the hypothesis named. Confirmation-shaped noise. The
fix was to diff the DYING seat against itself, which is what the numbers above do.

## Scope of the negative

This rules out occlusion **on our CvC cart, in the pre-lock window our scorer reads**. It
does **not** refute the owner's TE ROM observation — a different ROM with its own draw
code, and the TE lineage is not covered by this check. If board decoding is ever moved to
read AT or AFTER the lock, this check must be redone, because item 2 shows there is
genuinely destructive redraw 0.5 s in.
