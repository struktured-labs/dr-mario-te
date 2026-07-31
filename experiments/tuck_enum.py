#!/usr/bin/env python3
# -----------------------------------------------------------------------------
#  ATTRIBUTION / LICENSE NOTE
#
#  The "free" mode of this file is an INDEPENDENT IMPLEMENTATION of the pill
#  reachability algorithm published by Michael Birken ("meatfighter") in his
#  Dr. Mario AI, 2017 -- specifically the breadth-first search over
#  (x, y, orientation) in `drmarioai/Searcher.java`, which is licensed under the
#  GNU Lesser General Public License, version 2.1.
#
#  No meatfighter source was copied.  The algorithm was re-derived from a written
#  specification of its behaviour and re-expressed here against our own board
#  representation (`tmp/endgame/fb.py:FB`), our own orientation ring, our own
#  queue/visited structures and our own path encoding.  Credit for the algorithm
#  belongs to M. Birken; bugs in this rendering belong to us.
#
#  The "gravity" mode is NOT meatfighter's -- it is ours, and it is the point of
#  this file.  meatfighter's searcher runs with gravity switched OFF
#  (`DrMarioAI.stallDrop()` pins $0312 every frame while a plan executes), so his
#  reachable set is an UPPER BOUND obtained under infinite time.  "gravity" mode
#  re-runs the same reachability question under the real NES frame budget read
#  out of the ROM (drop period, edge-triggered rotation, tap cadence, lock-on-
#  failed-drop), and is the set we could actually execute.
# -----------------------------------------------------------------------------
"""Standalone tuck enumerator for NES Dr. Mario.

    enumerate(fb, pill_a, pill_b, mode=..., frames_per_row=...) -> [placement, ...]

Two modes:

  mode="free"      meatfighter's model.  State is exactly (x, y, orientation);
                   Left / Right / Down / Rotate90 / Rotate180 / Rotate_90 are all
                   unit-cost edges; there is no clock, so a pill may dwell on a
                   ledge forever and slide/rotate at will.  This is the UPPER
                   BOUND on the move space.

  mode="gravity"   OUR set.  A real frame-by-frame simulation of the ROM's
                   falling-pill handler: per frame it runs gravity ($8D70), then
                   lateral ($8DBF), then rotation ($8E2B), exactly in that order.
                   The pill LOCKS the instant a drop attempt fails -- there is no
                   lock delay in this game, the lock timer *is* the gravity timer
                   ($92), and neither sliding nor rotating resets it.  A placement
                   is reachable iff some frame schedule ends with a lock there.

COORDINATES.  Row 0 = top (spawn row), row 15 = floor; column 0 = left wall.
This is `FB`'s frame and meatfighter's frame.  (The ROM's own $0306 counts the
other way: 15 = top.  We never use ROM row numbers here.)

ORIENTATION RING.  4 states, matching meatfighter's `Orientation` and our
`drmario/controller.py` ring:

    o=0  H   horizontal, cells (y,x) (y,x+1),  left = a, right = b
    o=1  V   vertical,   cells (y-1,x) (y,x),  top  = b, bottom = a
    o=2  RH  horizontal, cells (y,x) (y,x+1),  left = b, right = a
    o=3  RV  vertical,   cells (y-1,x) (y,x),  top  = a, bottom = b

ANCHOR = the LEFT cell when horizontal, the BOTTOM cell when vertical.  A
rotation holds the anchor fixed; its only positional side effect is the left
kick (below).

ROTATION BUTTONS.  From the ROM ($8E2B, file 0x0E3B): the A button does
`DEC $A5` and the B button does `INC $A5`, both rising-edge only.  So

    A  ->  o-1 (mod 4)        B  ->  o+1 (mod 4)

Note this contradicts the comment at `drmario/controller.py:103` ("advance CW
with A"); the *geometry* of the ring is identical in both, only the button label
differs, and we follow the disassembly.  Our shipped cart driver emits A and
never B (`patch_cartridge_copro.py:1053`), which is why the direction matters.

SUPERSET (requirement).  `mode="free"` is guaranteed to contain every placement
`FB.resting(orient, col)` can produce.  This is NOT automatic: `FB.resting` will
happily return a drop into column 6 when column 5 is filled to row 0, which no
pill can physically reach -- meatfighter's BFS (correctly) rejects it, and the
existing `tmp/combo_term/tuck_reach.py` model records 423 such violations on real
game boards.  We therefore emit the straight-drop set unconditionally and tag
every placement with `reachable`: True if the search actually got there, False if
it is a straight drop the shipped brain believes in but no pill can reach.
Nothing is hidden -- the self-test prints both numbers.

WHAT "gravity" MODE MODELS
    * drop period P = gravityTable[speedBase[speed] + speedUps] + 1 frames.
      The +1 is real: $92 starts at 0 and $8D92 skips the drop while
      table >= counter, so it takes table+1 increments to move a row.
    * lock == the first failed drop attempt ($8D9A/$8D9F -> $8DAC JSR $8F52).
      No lock delay, no ARE, no reset on slide or rotate.  The tuck window is
      therefore exactly P - $92 frames from the moment the pill becomes
      supported, and it is non-resettable.  This falls out of the simulation --
      it is not coded as a special case.
    * soft drop: on ODD $43 frames only, and only when the held direction mask is
      *exactly* DOWN ($5C & $0F == $04).  Bypasses and zeroes the counter => 2
      frames/row.  DOWN+LEFT does not soft drop -- a ROM constraint on humans too.
    * rotation is rising-edge only, so two rotations in the same direction need a
      release frame between them: 2 frames per step, 3 frames for a 180.  There
      is NO direct 180 edge (unlike meatfighter) -- each step must be legal on
      its own or it reverts.
    * rotation kicks ($8E60): result vertical -> test in place only, else revert.
      Result horizontal -> test in place, else ONE left kick (x-1), else revert.
      No right kick, no floor kick, no up kick.
    * lateral: a press moves one column on its rising edge.  Consecutive presses
      need a release frame => 2 frames/column ("tapping").
    * right wall = anchor x <= 6 horizontal, x <= 7 vertical (ROM: 6 + rot&1).
    * a vertical pill at y=0 has its top half off the field.  That is legal
      (meatfighter models it too) and locking there yields a single cell.  We
      allow it as TRANSIT -- it is the only way into a column whose neighbour is
      filled at row 1 -- but do not emit it as a placement unless
      include_clipped=True, because `FB.place_at` cannot represent a half pill.

WHAT IT DELIBERATELY DOES NOT MODEL (each one makes us CONSERVATIVE -- our set
stays a subset of what a perfect human could do):
    * DAS.  Holding a direction repeats after 16 frames then every 6
      (F(k) = 6k+4).  Tapping costs 2 frames/column and beats DAS for every k, so
      the ladder never binds and we charge the tap cadence.  What we give up is
      the blocked-slide retry ($93 := $0F -> retry every frame), which lets a
      held direction enter a column on the exact frame it clears.
    * simultaneous buttons.  At most one input per frame, so LEFT+A and the ROM's
      "horizontal rotation succeeded and LEFT is held -> also shift left"
      ($8E6B) are both out of reach here.  Our cart driver has the same limit
      (one byte, one button, per frame).
    * $43 parity at spawn is assumed even (see spawn_parity).

OPTIONAL DRIVER-FIDELITY KNOBS (default OFF, so gravity mode == ROM-legal).  The
gap between ROM-legal and driver-emittable is the executor's cost:
    rot_lock_frame=N   orientation freezes after frame N.  The shipped driver
                       latches ROT_DONE2 at ~5 frames, which is exactly why
                       rotate-at-the-bottom is structurally impossible for it.
    monotone_lateral   forbid reversing lateral direction.  The driver steers
                       sign(target - current) only; serpentine paths are
                       unemittable.
    gate_frames=N      frames at the start during which no input is accepted
                       (the driver's PEND2 settle + MIN_THINK floor, ~8f).

MEASURED (self-test, 300 random boards; run `python tuck_enum.py`)
  straight drop (what we ship)            26.87 placements/board   1.00x
  free  = meatfighter upper bound         29.99                    1.12x
  gravity, P = 20 / 14 / 12 / 10          29.99                    1.12x
  gravity, P = 6                          29.85                    1.11x
  gravity, P = 2 (ROM speed cap)          24.66                    0.92x

  The headline: at every drop period a real L11 game actually runs at, the ROM
  frame budget costs NOTHING -- gravity mode recovers meatfighter's entire set.
  Tucks are not blocked by physics; they are blocked by the executor, and the
  driver knobs price that separately (ROT_DONE2 alone: 29.99 -> 28.12).
  Two second-order findings fall out:
    * at P = 2 the gravity set drops BELOW the straight-drop set (0.92x): at the
      ROM's speed cap even some straight drops become unreachable, because
      lateral alignment no longer fits inside the fall.
    * 2.70% of the straight drops FB.resting offers are physically unreachable
      on these boards (a column filled to row 0 walls them off).  The shipped
      search does not know this.  See SUPERSET above.

REFERENCES (read, not copied)
  meatfighter Searcher.java / DrMarioAI.java   (LGPL 2.1, M. Birken 2017)
  drmario.nes @ $8D70 $8DBF $8E2B $8E60 $A38D $A795   (gravity / DAS / rotation)
  tmp/endgame/fb.py                            (FB, resting, place_at)
  dr-mario-mods/driver-nav/patch_cartridge_copro.py   (what we can emit)
"""
from __future__ import annotations

import os
import sys
import time

# `enumerate` is shadowed by our API function further down; keep a handle first.
_ENUM = enumerate

_HERE = os.path.dirname(os.path.abspath(__file__))
_ENDGAME = "/home/struktured/projects/dr_mario_rl/tmp/endgame"
if _ENDGAME not in sys.path:
    sys.path.insert(0, _ENDGAME)

from fb import FB, ROWS, COLS, NCELL  # noqa: E402

# ----------------------------------------------------------------- orientations
H, V, RH, RV = 0, 1, 2, 3
_IS_H = (True, False, True, False)
# flip: 0 => cell0 (left/top) gets pill_a, 1 => cell0 gets pill_b
_FLIP = (0, 1, 1, 0)
# our ring index -> the 32-action `variant` of fast_rtl_x / faithful_env
# (drmario/controller.py NES_ROT_TO_VARIANT)
ROT_TO_VARIANT = (0, 3, 1, 2)
VARIANT_TO_ROT = (0, 2, 3, 1)

SPAWN_X, SPAWN_Y, SPAWN_O = 3, 0, H

# free-mode move tokens (meatfighter's Move set)
M_SPAWN, M_LEFT, M_RIGHT, M_DOWN, M_ROT_P1, M_ROT_180, M_ROT_M1 = range(7)
_FREE_TOKEN = ("Spawn", "Left", "Right", "Down", "RotB(+1)", "Rot180", "RotA(-1)")
# ORIENTATIONS[from][to] collapses to a Z4 lookup on (to - from) mod 4
_ROT_MOVE = (None, M_ROT_P1, M_ROT_180, M_ROT_M1)

# gravity-mode per-frame actions
A_NONE, A_LEFT, A_RIGHT, A_ROTA, A_ROTB, A_DOWN = range(6)
_GRAV_TOKEN = ("-", "L", "R", "A", "B", "D")
# `last` (for the rising-edge test) collapses NONE and DOWN: DOWN is level
# triggered ($5C is the held mask, not the edge mask), so it never consumes the
# edge that a following press needs.
_LAST_OF = (0, 1, 2, 3, 4, 0)

# ------------------------------------------------------------------ ROM gravity
# gravityTable @ $A795 (file 0x27A5), indices 0..80.  Index 80 is the last sane
# entry: speedUps caps at 49 ($8F32 CMP #$31) and HI base 31 + 49 = 80.
GRAVITY_TABLE = (
    69, 67, 65, 63, 61, 59, 57, 55, 53, 51, 49, 47, 45, 43, 41, 39, 37, 35, 33, 31,
    29, 27, 25, 23, 21, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 9, 8, 8, 7,
    7, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 4, 4, 4, 4, 4,
    3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    0,
)
SPEED_BASE = {"LOW": 15, "MED": 25, "HI": 31}  # @ $A38D (file 0x239D)
SPEEDUPS_CAP = 49
SOFT_DROP_PERIOD = 2  # frames/row while DOWN is the only held direction


def frames_per_row(speed="MED", speedups=0):
    """P = gravityTable[speedBase + speedUps] + 1, the natural fall period.

    The +1 is not a fudge: $92 starts at 0, $8D7E increments it *before* the
    compare, and $8D92 skips the drop while table >= counter, so it takes
    table+1 increments to move a row.  A cleared L11 (MED) game is ~50-90
    capsules => speedUps 5-9 => P = 15..11.
    """
    idx = SPEED_BASE[speed] + max(0, min(SPEEDUPS_CAP, int(speedups)))
    return GRAVITY_TABLE[min(idx, 80)] + 1


# --------------------------------------------------------------------- helpers
def _grid_of(fb):
    """Accept an FB, a flat 128-cell colour sequence, or bytes."""
    g = getattr(fb, "col", fb)
    if len(g) != NCELL:
        raise ValueError(f"expected {NCELL} cells, got {len(g)}")
    return list(g)


def _cells_of(x, y, o):
    """(r0,c0,r1,c1) with cell0 = left (H) or top (V) -- FB.place_at's order."""
    if _IS_H[o]:
        return (y, x, y, x + 1)
    return (y - 1, x, y, x)


def _legal_table(grid):
    """Legality of every (y, x, o), indexed (y*COLS + x)*4 + o.

    Legal iff both cells are in bounds and empty, EXCEPT that a vertical pill at
    y == 0 has its top half off the top of the field, which is accepted
    unconditionally (meatfighter Searcher.java:359 -- the half is clipped away
    when it locks and the survivor becomes a SQUARE).
    """
    t = bytearray(ROWS * COLS * 4)
    for y in range(ROWS):
        base = y * COLS
        for x in range(COLS):
            if grid[base + x] != 0:
                continue                       # anchor occupied
            if x <= COLS - 2 and grid[base + x + 1] == 0:
                t[(base + x) * 4 + H] = 1      # partner right; anchor col <= 6
                t[(base + x) * 4 + RH] = 1
            if y == 0 or grid[base - COLS + x] == 0:
                t[(base + x) * 4 + V] = 1      # partner above, or clipped at y=0
                t[(base + x) * 4 + RV] = 1
    return t


def straight_drop_placements(fb):
    """The <=15 cell-pairs FB.resting can produce: {(r0,c0,r1,c1): geom}.

    geom 0 = horizontal, 1 = vertical -- FB.resting's own argument.
    """
    b = fb if isinstance(fb, FB) else FB(_grid_of(fb))
    out = {}
    for geom in (0, 1):
        for c in range(COLS):
            cells = b.resting(geom, c)
            if cells is not None:
                out[cells] = geom
    return out


# ============================================================= FREE MODE (BFS)
def _bfs_free(grid, left_kick=True):
    """meatfighter's reachability BFS.  Returns (targets, pred).

    targets : [(x, y, o)] in BFS discovery order -- the resting states, reported
              as they are dequeued, exactly where `foundTarget` fires.
    pred    : {state: (move, from_x, from_y, from_o)} for path rebuilding.

    PORT TRAP (Searcher.java:352-361): the predecessor is recorded BEFORE the
    partner-cell gate, so `pred` is a table of *anchor-enterable* states, not of
    reachable ones.  Enumerate from `targets`, never from `pred`.  (Harmless for
    correctness -- legality is path independent, so blocking re-entry to an
    illegal state loses nothing -- but it is a real trap.)

    left_kick: OUR ADDITION to meatfighter's model, not his behaviour.  His
    Searcher models no kick at all except the right-wall clamp, so it slightly
    UNDER-approximates rotation; the ROM ($8E7D) shifts one column left when a
    rotation to horizontal is blocked in place.  Since free mode is supposed to
    be an upper bound -- and since gravity mode models the kick -- leaving it out
    would let gravity mode find placements free mode misses.
    """
    if grid[SPAWN_Y * COLS + SPAWN_X] != 0 or grid[SPAWN_Y * COLS + SPAWN_X + 1] != 0:
        return [], {}                          # canSpawn() == false: topped out

    legal = _legal_table(grid)
    pred = {}
    queue = []
    targets = []

    def enq(x, y, o, move, fx, fy, fo):
        # right-wall clamp: a vertical capsule in column 7 rotated to horizontal
        # kicks one column left.  `fx` is deliberately NOT clamped, so the path
        # still reads "be at x=7 vertical, press rotate".
        if _IS_H[o] and x == COLS - 1:
            x -= 1
        k = (x, y, o)
        if k in pred or grid[y * COLS + x] != 0:
            return
        pred[k] = (move, fx, fy, fo)           # marked before the partner gate
        if _IS_H[o]:
            if grid[y * COLS + x + 1] != 0:
                return
        elif y != 0 and grid[(y - 1) * COLS + x] != 0:
            return
        queue.append(k)

    enq(SPAWN_X, SPAWN_Y, SPAWN_O, M_SPAWN, -1, -1, -1)

    qhead = 0
    while qhead < len(queue):
        x, y, o = queue[qhead]
        qhead += 1
        # target test: is it resting?  Either half may be supported when
        # horizontal; only the bottom half when vertical.  A target is NOT
        # terminal -- it keeps expanding, which is exactly the tuck model.
        if _IS_H[o]:
            rest = (y == ROWS - 1 or grid[(y + 1) * COLS + x] != 0
                    or grid[(y + 1) * COLS + x + 1] != 0)
        else:
            rest = (y == ROWS - 1 or grid[(y + 1) * COLS + x] != 0)
        if rest:
            targets.append((x, y, o))
        # expansion order is load bearing for tie-breaks: rotations o=3..0, L, R, D
        for no in (3, 2, 1, 0):
            if no == o:
                continue
            mv = _ROT_MOVE[(no - o) & 3]
            tx = x - 1 if (_IS_H[no] and x == COLS - 1) else x
            enq(tx, y, no, mv, x, y, o)
            if left_kick and _IS_H[no] and tx >= 1 \
                    and not legal[(y * COLS + tx) * 4 + no]:
                enq(tx - 1, y, no, mv, x, y, o)
        if x != 0:
            enq(x - 1, y, o, M_LEFT, x, y, o)
        if x != COLS - 1:
            enq(x + 1, y, o, M_RIGHT, x, y, o)
        if y != ROWS - 1:
            enq(x, y + 1, o, M_DOWN, x, y, o)
    return targets, pred


def _free_path(pred, x, y, o):
    """spawn -> target token list."""
    rev = []
    guard = 0
    while True:
        move, fx, fy, fo = pred[(x, y, o)]
        if move == M_SPAWN:
            break
        rev.append(_FREE_TOKEN[move])
        x, y, o = fx, fy, fo
        guard += 1
        if guard > 4096:  # cannot happen: the visited test bounds paths at 512
            raise RuntimeError("free path reconstruction did not terminate")
    rev.reverse()
    return rev


# ========================================================= GRAVITY MODE (frames)
def _bfs_gravity(grid, period, gate_frames=0, spawn_parity=0,
                 rot_lock_frame=None, monotone_lateral=False,
                 max_frames=4096):
    """Frame-exact reachability.  Returns {(x, y, o): (lock_frame, [action,...])}.

    Every transition costs exactly one frame, so a level-synchronous BFS visits
    states in frame order and the first lock recorded for a placement is the
    fastest schedule that reaches it.

    Per frame, in the ROM's own order ($8D66 / $8D69 / $8D6C):
        1. gravity  ($8D70) -- may drop a row, or LOCK if the drop fails
        2. lateral  ($8DBF) -- rising edge only
        3. rotation ($8E2B) -- rising edge only, in place or one left kick

    State = (x, y, o, gravity_counter, last_button, frame_parity, lateral_dir).
    The gravity counter is what makes this different from meatfighter's
    (x, y, o): two arrivals at the same square with different counters are NOT
    equivalent, because the later one has strictly less manoeuvring budget.
    Collapsing them is precisely what certifies infeasible tuck paths.
    """
    legal = _legal_table(grid)
    if not legal[(SPAWN_Y * COLS + SPAWN_X) * 4 + SPAWN_O]:
        return {}

    g = period - 1                 # raw gravityTable entry; drop when counter > g
    # `lat` (last lateral direction) is only *read* when monotone_lateral is on,
    # but it is always WRITTEN, so it must always be part of the key -- sizing
    # the key without it silently aliases distinct states into one slot.
    n_lat = 3
    s_par = n_lat
    s_last = s_par * 2
    s_c = s_last * 5
    s_o = s_c * period
    s_pos = s_o * 4

    seen = bytearray(ROWS * COLS * s_pos)
    pred = {}
    start = (SPAWN_X, SPAWN_Y, SPAWN_O, 0, 0, spawn_parity & 1, 0)
    seen[(SPAWN_Y * COLS + SPAWN_X) * s_pos + SPAWN_O * s_o
         + (spawn_parity & 1) * s_par] = 1
    pred[start] = None
    frontier = [start]
    locks = {}
    frame = 0
    last_col = COLS - 1

    while frontier and frame < max_frames:
        nxt = []
        gated = frame < gate_frames
        frozen = rot_lock_frame is not None and frame >= rot_lock_frame
        acts = (A_NONE,) if gated else (
            (A_NONE, A_LEFT, A_RIGHT, A_DOWN) if frozen
            else (A_NONE, A_LEFT, A_RIGHT, A_ROTA, A_ROTB, A_DOWN))
        for st in frontier:
            x, y, o, c, last, par, lat = st
            for act in acts:
                if monotone_lateral and ((act == A_LEFT and lat == 2)
                                         or (act == A_RIGHT and lat == 1)):
                    continue
                nx, ny, no, nc, nlat = x, y, o, c, lat
                # ---- 1. gravity ($8D70) ---------------------------------
                if par == 1 and act == A_DOWN:
                    do_drop = True             # soft drop bypasses the counter
                else:
                    nc = c + 1
                    do_drop = nc > g
                if do_drop:
                    if ny + 1 < ROWS and legal[((ny + 1) * COLS + nx) * 4 + no]:
                        ny += 1
                        nc = 0
                    else:
                        # LOCK.  The only lock mechanism in the game: no delay,
                        # no grace, no reset from having slid or rotated.
                        pk = (x, y, o)
                        if pk not in locks:
                            locks[pk] = (frame + 1, _grav_path(pred, st, act))
                        continue
                # ---- 2. lateral ($8DBF), rising edge only ----------------
                if act == A_LEFT:
                    if last != 1 and nx > 0 \
                            and legal[(ny * COLS + nx - 1) * 4 + no]:
                        nx -= 1
                        nlat = 1
                elif act == A_RIGHT:
                    if last != 2 and nx < last_col \
                            and legal[(ny * COLS + nx + 1) * 4 + no]:
                        nx += 1
                        nlat = 2
                # ---- 3. rotation ($8E2B), rising edge only ---------------
                elif act == A_ROTA or act == A_ROTB:
                    if last != _LAST_OF[act]:
                        cand = (no - 1) & 3 if act == A_ROTA else (no + 1) & 3
                        if legal[(ny * COLS + nx) * 4 + cand]:
                            no = cand
                        elif _IS_H[cand] and nx > 0 \
                                and legal[(ny * COLS + nx - 1) * 4 + cand]:
                            no = cand          # the single left kick ($8E7D)
                            nx -= 1
                        # else revert ($8E84 restores $4A/$4B): no change at all
                nlast = _LAST_OF[act]
                npar = par ^ 1
                kk = ((ny * COLS + nx) * s_pos + no * s_o + nc * s_c
                      + nlast * s_last + npar * s_par + nlat)
                if seen[kk]:
                    continue
                seen[kk] = 1
                ns = (nx, ny, no, nc, nlast, npar, nlat)
                pred[ns] = (st, act)
                nxt.append(ns)
        frontier = nxt
        frame += 1
    return locks


def replay(grid, path, period, spawn_parity=0):
    """Re-simulate a gravity-mode frame schedule and report where it locks.

    Deliberately written a second time, straight down, against the raw
    occupancy grid instead of the precomputed legality table and without any of
    the BFS's state packing.  It is a check on the SEARCH (key packing, visited
    aliasing, predecessor chains, path reversal), not on the MODEL -- if the
    frame semantics themselves are wrong, both copies are wrong together.

    Returns (x, y, o) where the pill locked, or None if the schedule ran out
    with the pill still in the air.
    """
    grid = _grid_of(grid)

    def fits(x, y, o):
        if x < 0 or y < 0 or y >= ROWS:
            return False
        if _IS_H[o]:
            if x > COLS - 2:
                return False
            return grid[y * COLS + x] == 0 and grid[y * COLS + x + 1] == 0
        if x > COLS - 1:
            return False
        if grid[y * COLS + x] != 0:
            return False
        return y == 0 or grid[(y - 1) * COLS + x] == 0   # top half off-field at y=0

    act_of = {t: i for i, t in _ENUM(_GRAV_TOKEN)}
    x, y, o, c, last, par = SPAWN_X, SPAWN_Y, SPAWN_O, 0, 0, spawn_parity & 1
    if not fits(x, y, o):
        return None
    for tok in path:
        act = act_of[tok]
        if par == 1 and act == A_DOWN:          # soft drop bypasses the counter
            drop = True
        else:
            c += 1
            drop = c > period - 1
        if drop:
            if fits(x, y + 1, o):
                y += 1
                c = 0
            else:
                return (x, y, o)                # locked
        if act == A_LEFT and last != 1 and fits(x - 1, y, o):
            x -= 1
        elif act == A_RIGHT and last != 2 and fits(x + 1, y, o):
            x += 1
        elif act in (A_ROTA, A_ROTB) and last == _LAST_OF[act]:
            pass                                # no rising edge: nothing happens
        elif act == A_ROTA or act == A_ROTB:
            cand = (o - 1) & 3 if act == A_ROTA else (o + 1) & 3
            if fits(x, y, cand):
                o = cand
            elif _IS_H[cand] and fits(x - 1, y, cand):
                o, x = cand, x - 1
        last = _LAST_OF[act]
        par ^= 1
    return None


def _grav_path(pred, state, final_act):
    """Per-frame action tokens, spawn frame first, lock frame last."""
    rev = [_GRAV_TOKEN[final_act]]
    st = state
    guard = 0
    while True:
        p = pred[st]
        if p is None:
            break
        st, act = p
        rev.append(_GRAV_TOKEN[act])
        guard += 1
        if guard > 8192:
            raise RuntimeError("gravity path reconstruction did not terminate")
    rev.reverse()
    return rev


# ==================================================================== the API
def enumerate(fb, pill_a=1, pill_b=1, mode="free", frames_per_row=12,
              include_clipped=False, gate_frames=0, spawn_parity=0,
              rot_lock_frame=None, monotone_lateral=False,
              union_straight_drops=True, left_kick=True):
    """Every placement the pill (pill_a, pill_b) can lock into on board `fb`.

    fb              FB, or any flat 128-cell colour sequence (0 = empty).
    pill_a, pill_b  colours 1..3.  They only fill in `colors`; legality and
                    reachability depend on the occupancy grid alone.
    mode            "free"    -- meatfighter, gravity ignored: the UPPER BOUND.
                    "gravity" -- ROM frame budget: OUR set.
    frames_per_row  P = gravityTable[...] + 1.  Use frames_per_row("MED", n).
                    Ignored in "free" mode.
    include_clipped emit vertical locks at y = 0, whose top half is off the field
                    and which FB.place_at cannot represent.  Default False.
    union_straight_drops
                    free mode only: also emit every FB.resting placement, even
                    the ones the BFS proves unreachable (tagged reachable=False).
                    This is what makes free mode a strict superset of the
                    straight drops; see the module docstring.

    Returns a list of dicts sorted by (cells, orientation):
        cells          (r0,c0,r1,c1); cell0 = left (H) or top (V) -- place_at order
        orient         0..3 in our ring (H, V, RH, RV)
        col, row       the anchor (left cell when H, bottom cell when V)
        variant        the matching 0..3 `variant` of the 32-action space
        flip           0 => cell0 gets pill_a, 1 => cell0 gets pill_b
        colors         (colour at cell0, colour at cell1)
        path           free mode: move names.  gravity mode: ONE TOKEN PER FRAME
                       ("-" = no button), i.e. a literal frame schedule.
        n_inputs       number of actual button presses
        frames_needed  gravity mode: the frame on which the pill locks.
                       free mode: None -- meatfighter's model has no clock, and
                       that is the whole point, so we refuse to invent one.
        is_tuck        True iff no straight drop lands on these cells
        reachable      True iff the search reached it (False only for straight
                       drops unioned in under free mode)
        clipped        True iff vertical at y = 0 (top half off the field)
    """
    grid = _grid_of(fb)
    sd = straight_drop_placements(grid)
    out = []
    got = set()

    def emit(x, y, o, path, frames, reachable):
        cells = _cells_of(x, y, o)
        clipped = (not _IS_H[o]) and y == 0
        if clipped and not include_clipped:
            return
        k = (cells, o)
        if k in got:
            return
        got.add(k)
        flip = _FLIP[o]
        c0, c1 = (pill_b, pill_a) if flip else (pill_a, pill_b)
        n_in = (sum(1 for t in path if t != "-") if mode == "gravity"
                else len(path))
        out.append({
            "cells": cells,
            "orient": o,
            "col": x,
            "row": y,
            "variant": ROT_TO_VARIANT[o],
            "flip": flip,
            "colors": (c0, c1),
            "path": path,
            "n_inputs": n_in,
            "frames_needed": frames,
            "is_tuck": cells not in sd,
            "reachable": reachable,
            "clipped": clipped,
        })

    if mode == "free":
        targets, pred = _bfs_free(grid, left_kick=left_kick)
        for (x, y, o) in targets:
            emit(x, y, o, _free_path(pred, x, y, o), None, True)
        if union_straight_drops:
            # Straight drops the BFS could not reach are physically unreachable
            # (a column filled to row 0 walls off everything behind it), but the
            # shipped search enumerates them, so they must appear -- tagged.
            for cells, geom in sd.items():
                r0, c0, r1, c1 = cells
                x, y, os_ = ((c0, r0, (H, RH)) if geom == 0
                             else (c0, r1, (V, RV)))
                for o in os_:
                    if (cells, o) not in got:
                        emit(x, y, o, [], None, False)
    elif mode == "gravity":
        locks = _bfs_gravity(grid, int(frames_per_row), gate_frames=gate_frames,
                             spawn_parity=spawn_parity,
                             rot_lock_frame=rot_lock_frame,
                             monotone_lateral=monotone_lateral)
        for (x, y, o), (frame, path) in sorted(locks.items()):
            emit(x, y, o, path, frame, True)
    else:
        raise ValueError(f"mode must be 'free' or 'gravity', got {mode!r}")

    out.sort(key=lambda p: (p["cells"], p["orient"]))
    return out


enumerate_placements = enumerate      # non-shadowing alias for importers


def placement_keys(placements):
    """{(r0,c0,r1,c1,flip)} -- the key the other enumerations use."""
    return {(p["cells"][0], p["cells"][1], p["cells"][2], p["cells"][3], p["flip"])
            for p in placements}


# ==================================================================== self-test
def _rand_board(rnd):
    """Random column heights plus punched holes (= overhangs, = tuck targets).

    Heights run to the full 16 so that lateral blockades at row 0 occur; the
    spawn cells (0,3) and (0,4) are forced empty because a blocked spawn is a
    topped-out game, not a placement problem.
    """
    grid = [0] * NCELL
    for c in range(COLS):
        h = rnd.randrange(0, ROWS + 1)
        for r in range(ROWS - h, ROWS):
            grid[r * COLS + c] = rnd.randint(1, 3)
    for _ in range(rnd.randrange(0, 16)):
        grid[rnd.randrange(1, ROWS) * COLS + rnd.randrange(0, COLS)] = 0
    grid[SPAWN_X] = 0
    grid[SPAWN_X + 1] = 0
    return grid


def _check_invariants(grid, placements):
    """I3 emptiness, I4 support, bounds -- for every placement the search found."""
    bad = []
    for p in placements:
        if not p["reachable"]:
            continue        # unioned straight drops are FB.resting's own output
        r0, c0, r1, c1 = p["cells"]
        oob = False
        for (r, c) in ((r0, c0), (r1, c1)):
            if not (0 <= r < ROWS and 0 <= c < COLS):
                bad.append(("bounds", p["cells"], p["orient"]))
                oob = True
                break
            if grid[r * COLS + c] != 0:
                bad.append(("occupied", p["cells"], p["orient"]))
                oob = True
                break
        if oob:
            continue
        if _IS_H[p["orient"]]:
            sup = (r0 == ROWS - 1 or grid[(r0 + 1) * COLS + c0] != 0
                   or grid[(r0 + 1) * COLS + c1] != 0)
        else:
            sup = (r1 == ROWS - 1 or grid[(r1 + 1) * COLS + c1] != 0)
        if not sup:
            bad.append(("floating", p["cells"], p["orient"]))
    return bad


def _ENUM_MODE(grid, **kw):
    """enumerate() with a fixed pill; colours never affect legality."""
    return enumerate(grid, 1, 2, **kw)


def _cave_board():
    """A fixed regression board: a lip over columns 5-7 at row 9, floor at row 11.

    Nothing can straight-drop into row 10 columns 5,6,7 -- the only way in is to
    descend column 4 as a VERTICAL pill (horizontal is blocked at row 9 by the
    lip) and then rotate back to horizontal at row 10, or to slide in under the
    lip.  Both are true tucks, and the deepest one is the first casualty when
    the drop period gets short.
    """
    grid = [0] * NCELL
    for c in (5, 6, 7):
        grid[9 * COLS + c] = 1
    for c in range(COLS):
        grid[11 * COLS + c] = 2
        for r in (12, 13, 14, 15):
            grid[r * COLS + c] = 3
    return grid


CAVE_CELLS = ((10, 4, 10, 5), (10, 5, 10, 6), (10, 6, 10, 7))


def _selftest(n_boards=300, n_gravity=300, seed=20260728, period=12):
    import random
    rnd = random.Random(seed)
    fail = []

    print("=" * 78)
    print("tuck_enum self-test")
    print(f"  boards         : {n_boards} random "
          f"(column heights 0..16 + punched holes), seed {seed}")
    print(f"  gravity boards : {n_gravity}   at P = {period} frames/row")
    print(f"  ROM drop period: MED speedUps 0 -> P={frames_per_row('MED', 0)},"
          f"  8 -> P={frames_per_row('MED', 8)},"
          f"  18 -> P={frames_per_row('MED', 18)},"
          f"  49(cap) -> P={frames_per_row('MED', 49)}")
    print("=" * 78)

    boards = [_rand_board(rnd) for _ in range(n_boards)]

    # ---- (0) two boards whose answer is known by hand ----------------------
    print("\n(0) SANITY -- boards whose answer is known by hand")
    empty = [0] * NCELL
    ef = _ENUM_MODE(empty, mode="free")
    esd = set(straight_drop_placements(empty))
    ok0 = ({p["cells"] for p in ef} == esd and len(esd) == 15
           and not any(p["is_tuck"] for p in ef))
    print(f"    empty board: 15 resting cell-pairs (7 H + 8 V) at row 15 only,"
          f" free == straight drop, zero tucks : {'OK' if ok0 else 'FAIL'}")
    if not ok0:
        fail.append("empty-board")

    cave = _cave_board()
    csd = set(straight_drop_placements(cave))
    cfree = {p["cells"] for p in _ENUM_MODE(cave, mode="free") if p["reachable"]}
    ok1 = (not (set(CAVE_CELLS) & csd)) and set(CAVE_CELLS) <= cfree
    print(f"    cave board : the 3 cells under the lip are unreachable by"
          f" straight drop and all 3 are found by free mode : "
          f"{'OK' if ok1 else 'FAIL'}")
    if not ok1:
        fail.append("cave-board")

    # ---- (a) SUPERSET: every FB.resting placement must appear in free mode --
    t0 = time.time()
    sd_total = viol_superset = sd_not_bfs = boards_with_gap = inv_bad = 0
    viol_examples = []
    free_lists = []
    for grid in boards:
        pl = _ENUM_MODE(grid, mode="free")
        free_lists.append(pl)
        keys = placement_keys(pl)
        bfs_keys = placement_keys([p for p in pl if p["reachable"]])
        gap = 0
        for cells in straight_drop_placements(grid):
            for flip in (0, 1):
                sd_total += 1
                k = (cells[0], cells[1], cells[2], cells[3], flip)
                if k not in keys:
                    viol_superset += 1
                    if len(viol_examples) < 3:
                        viol_examples.append(k)
                if k not in bfs_keys:
                    sd_not_bfs += 1
                    gap += 1
        boards_with_gap += 1 if gap else 0
        inv_bad += len(_check_invariants(grid, pl))
    t_free = time.time() - t0

    print("\n(a) SUPERSET PROPERTY"
          "   [free mode must contain every FB.resting placement]")
    print(f"    straight-drop placements checked : {sd_total}"
          f"   ({n_boards} boards x 2 colour orders)")
    print(f"    NOT present in free mode         : {viol_superset}"
          f"    <-- must be 0")
    if viol_examples:
        print(f"    examples                         : {viol_examples}")
    print(f"    invariant failures (in bounds / cells empty / supported)"
          f" on searched placements : {inv_bad}    <-- must be 0")
    if viol_superset:
        fail.append("superset")
    if inv_bad:
        fail.append("invariants")
    print("\n    honest diagnostic -- of those same straight drops, how many can")
    print("    the BFS physically REACH?  A column filled to row 0 walls off")
    print("    everything behind it, and the shipped search never notices.")
    print(f"    straight drops the BFS cannot reach : {sd_not_bfs}/{sd_total}"
          f" = {sd_not_bfs / sd_total:.2%}   on {boards_with_gap}/{n_boards} boards")
    print("    (tuck_reach.py records 423 of these on real game boards.  Here")
    print("     they are unioned in and tagged reachable=False, never dropped.)")

    # ---- (b) EXTRA placements per mode, swept over the ROM's drop periods ---
    grav_boards = boards[:n_gravity]
    sd_n, free_n, freeb_n = [], [], []
    free_tuck = []
    for i, grid in _ENUM(grav_boards):
        sd_n.append(len({(c[0], c[1], c[2], c[3], f)
                         for c in straight_drop_placements(grid) for f in (0, 1)}))
        fl = free_lists[i]
        free_n.append(len(placement_keys(fl)))
        freeb_n.append(len(placement_keys([p for p in fl if p["reachable"]])))
        free_tuck.append(len({(p["cells"], p["flip"]) for p in fl if p["is_tuck"]}))

    def mean(v):
        return sum(v) / len(v) if v else 0.0

    m_sd, m_free, m_freeb = mean(sd_n), mean(free_n), mean(freeb_n)
    print("\n(b) HOW MANY PLACEMENTS DOES EACH MODEL SEE?"
          "   [placement = cells x colour-order]")
    print(f"    {'straight drop -- what we ship today':<41}{m_sd:7.2f}   1.00x"
          f"   ({'baseline'})")
    print(f"    {'free  -- meatfighter UB, BFS-reachable':<41}{m_freeb:7.2f}"
          f"   {m_freeb / m_sd:.2f}x   +{m_freeb - m_sd:.2f}/board"
          f"   ({mean(free_tuck):.2f} true tucks)")
    print(f"    {'free  -- u straight drops, as emitted':<41}{m_free:7.2f}"
          f"   {m_free / m_sd:.2f}x   +{m_free - m_sd:.2f}/board")
    print("\n    gravity mode, swept over the real ROM drop periods:")
    print(f"      {'P':>3} {'speedUps@MED':>13}  {'placements':>10} {'vs sd':>7}"
          f" {'extra':>7} {'tucks':>7}  {'lost vs free':>12}  {'lockframe':>9}")
    rows = []
    t0 = time.time()
    n_replay = replay_bad = contain_bad = grav_inv = 0
    for P, tag in ((20, "0  (opening)"), (14, "6"), (12, "8"), (10, "10-11"),
                   (6, "18-29"), (2, "49 (ROM cap)")):
        gn, gt, gf, lost = [], [], [], []
        for i, grid in _ENUM(grav_boards):
            gl = _ENUM_MODE(grid, mode="gravity", frames_per_row=P)
            gk = placement_keys(gl)
            fbk = placement_keys([p for p in free_lists[i] if p["reachable"]])
            contain_bad += len(gk - fbk)      # gravity must be inside free
            grav_inv += len(_check_invariants(grid, gl))
            gn.append(len(gk))
            gt.append(len({(p["cells"], p["flip"]) for p in gl if p["is_tuck"]}))
            lost.append(len(fbk - gk))
            if gl:
                gf.append(sum(p["frames_needed"] for p in gl) / len(gl))
            # ---- replay every emitted schedule through the independent sim
            for p in gl:
                n_replay += 1
                got = replay(grid, p["path"], P)
                if got is None or _cells_of(*got) != p["cells"] \
                        or got[2] != p["orient"] \
                        or len(p["path"]) != p["frames_needed"]:
                    replay_bad += 1
        m_g = mean(gn)
        rows.append((P, m_g))
        print(f"      {P:>3} {tag:>13}  {m_g:>10.2f} {m_g / m_sd:>6.2f}x"
              f" {m_g - m_sd:>+7.2f} {mean(gt):>7.2f}  {mean(lost):>12.2f}"
              f"  {mean(gf):>9.1f}")
    t_grav = time.time() - t0

    print(f"\n    containment: gravity placements NOT in the free set : "
          f"{contain_bad}    <-- must be 0")
    print(f"    invariant failures on gravity placements            : "
          f"{grav_inv}    <-- must be 0")
    print(f"    frame schedules replayed through the independent simulator:"
          f" {n_replay}")
    print(f"    schedules that did NOT lock where claimed           : "
          f"{replay_bad}    <-- must be 0")
    if contain_bad:
        fail.append("containment")
    if grav_inv:
        fail.append("gravity-invariants")
    if replay_bad:
        fail.append("replay")

    print("\n    READING: at every drop period a real L11 game runs at (P = 20")
    print("    down to ~10) the ROM frame budget costs NOTHING -- gravity mode")
    print("    recovers meatfighter's whole set.  It is still ~free at P = 6")
    print("    (~180+ capsules).  Only at the ROM speed cap P = 2 does it bite,")
    print("    and there it falls BELOW the straight-drop set, because lateral")
    print("    alignment stops fitting inside the fall.  So the tuck gap is an")
    print("    EXECUTOR problem, not a physics problem -- priced next:")

    # ---- (b2) what the SHIPPED driver can emit ------------------------------
    print("\n    the executor's own cost, at P = 12 (each knob alone):")
    for label, kw in (("ROM-legal (no knobs)", {}),
                      ("gate_frames=8   (PEND2 settle + MIN_THINK)",
                       {"gate_frames": 8}),
                      ("rot_lock_frame=5 (ROT_DONE2 latch)",
                       {"rot_lock_frame": 5}),
                      ("monotone_lateral (sign-steering only)",
                       {"monotone_lateral": True})):
        n = mean([len(placement_keys(_ENUM_MODE(g, mode="gravity",
                                                frames_per_row=12, **kw)))
                  for g in grav_boards])
        print(f"      {label:<44}{n:7.2f}   {n / m_sd:.2f}x vs straight drop")

    print(f"\n    timing: free {t_free:.1f}s / {n_boards} boards,"
          f" gravity sweep {t_grav:.1f}s / {n_gravity} boards x 6 periods")

    # ---- (c) worked example -------------------------------------------------
    gl = _ENUM_MODE(cave, mode="gravity", frames_per_row=period)
    tucks = [p for p in gl if p["is_tuck"]]
    if tucks:
        p = min(tucks, key=lambda q: q["frames_needed"])
        print(f"\n(c) A TUCK THE ROM FRAME BUDGET ALLOWS (cave board, P={period})")
        marks = {p["cells"][0] * COLS + p["cells"][1],
                 p["cells"][2] * COLS + p["cells"][3]}
        for line in FB(cave).ascii(mark=marks).splitlines():
            print("      " + line)
        print(f"      cells={p['cells']}  orient={p['orient']}"
              f"  variant={p['variant']}  flip={p['flip']}  is_tuck={p['is_tuck']}")
        print(f"      locks on frame {p['frames_needed']}"
              f" after {p['n_inputs']} button presses")
        print(f"      frame schedule = {''.join(p['path'])}")
        print(f"      replayed independently -> {replay(cave, p['path'], period)}"
              f"  (want ({p['col']}, {p['row']}, {p['orient']}))")

    print("\n" + "=" * 78)
    print("SELF-TEST " + ("PASS" if not fail else "FAIL " + ", ".join(fail)))
    print("=" * 78)
    return not fail


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--boards", type=int, default=300)
    ap.add_argument("--gravity-boards", type=int, default=300)
    ap.add_argument("--period", type=int, default=12,
                    help="frames per row (P = gravityTable + 1); 12 = MED speedUps 8")
    ap.add_argument("--seed", type=int, default=20260728)
    a = ap.parse_args()
    sys.exit(0 if _selftest(a.boards, a.gravity_boards, a.seed, a.period) else 1)
