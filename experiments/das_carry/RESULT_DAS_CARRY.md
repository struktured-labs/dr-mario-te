# DAS carry ("momentum") — silicon test, 2026-09-25 (bluemage, CHAIN540 core + patched couch cart 4b4fce5e)

Owner's report: holding L/R through a pill's lock gives the next pill "momentum"; can you switch direction
and keep it? ROM (fallingPill_checkXMove $8DCF, NTSC): new L/R press edge while a pill is controlled ⇒
horVelocity := 0 and move 1 immediately; held ⇒ ++, move at 16, then reset to 10 (6 f/col); blocked ⇒ 15.
checkXMove runs ONLY from action_pillFalling, and nothing else writes horVelocity in play.

**Instrument.** `kbd.py` runs ON the MiSTer: a uinput keyboard with the misterclaw VID:PID (so the NES map
applies) that can HOLD keys, with ms-timed timelines and no network jitter. State is read from Alt+F1
save-states (CPU RAM @0x102B08): P1 X $0305, Y $0306, speedCounter $0312, horVelocity $0313, nextAction $0317,
pause $068D. Frame clock = 20·ΔY + Δspeed (MED, speedUps 0 ⇒ table $13 ⇒ 20 f/row). Every analysed snapshot has
nextAction=0 (a pill under control) and pause=5. The pause window stands in for the lock gap: in both,
checkXMove does not run.

| test | action | carry predicts | reset predicts | measured |
|---|---|---|---|---|
| A | press LEFT while paused (v=0), unpause 9 f | dX 0, v 9 | dX −1, v 9 | **dX 0, v 9** ⇒ edge consumed |
| B | charge LEFT (v=12), switch to RIGHT while paused, unpause 10 f | **dX +2, v 10** | dX +1, v 10 | **dX +2, v 10** ⇒ charge redirected |
| C | press LEFT while the pill is controlled | (v≥10) | dX −1, v<10 | **dX −1, v 8** ⇒ reset |

Also runs 1-2: v=12 and v=10 survived a lock and the next spawn unchanged (no reset at spawn).

**Conclusions (silicon):**
1. The charge carries across pills.
2. A direction switch made while no pill is being moved keeps the charge in the NEW direction.
3. A switch while controlling resets it.
4. A pre-hold with NO charge is SLOWER (first move at 16 f, test A), so pre-holding pays only when v ≥ ~10.

**Bigger lever found in the same code:** DRPROPH's escape pulse presses on alternate frames (a fresh press edge
each time), which moves 1 col / 2 f, 3× faster than DAS (6 f/col). Normal steering holds (DAS). A 4-col
move: DAS 28 f · charged carry 19 f · pulse 6 f. (Pulsing is a superhuman input rate; owner's call.)
