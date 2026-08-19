"""NES controller / pathfinding layer: PLACEMENT -> button presses.

This is the bridge between a *placement-based* policy (trained on the faithful
sim, see ``faithful_env.py``) and frame-by-frame control of the real Dr. Mario
NES ROM. The policy picks *where* the current pill should land (orientation,
column, colour order); this module turns that choice into a deterministic
sequence of controller button presses that maneuver the spawning pill to the
target and drop it.

Key facts it is built around
----------------------------
Board geometry (``faithful_game.py``): 16 rows x 8 cols, row 0 = top, row 15 =
floor. ``ORIENT_H`` occupies columns ``(c, c+1)`` (legal anchor cols 0..6);
``ORIENT_V`` occupies one column over two rows (legal anchor cols 0..7). The
ROM spawns a *horizontal* pill at the top centre, anchor column 3 (it covers
``SPAWN_COLS == (3, 4)``).

Env action encoding (``faithful_env.py``):
    action = variant * cols + col
    variant 0 = H     (a left,  b right)
    variant 1 = Hflip (b left,  a right)
    variant 2 = V     (a top,   b bottom)
    variant 3 = Vflip (b top,   a bottom)

The faithful env only distinguishes two *geometric* orientations (H, V); the
colour order is the other bit. On the NES there is a single 4-state rotation
register (``$00A5``: 0=horiz, 1=vert CCW, 2=reverse, 3=vert CW) that encodes
*both* geometry and colour order, because each press of A (rotate CW) / B
(rotate CCW) advances it by one. We therefore model rotation as a 4-state ring
and map each ring state to an env variant (see ``NES_ROT_TO_VARIANT``).

The kinematic model here is intentionally independent of the rules engine: it
only tracks the falling pill's ``(anchor_col, rotation)`` and the legal-column
limits implied by the current orientation. It does **not** model gravity / the
drop timer / DAS (auto-repeat). See ``CONTROLLER_NOTES.md`` for the full list of
assumptions and the sim-vs-ROM validation procedure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .faithful_game import ORIENT_H, ORIENT_V

# --------------------------------------------------------------------- buttons
# Abstract button identifiers. These are deliberately *not* raw bytes so the
# planner is independent of any particular controller wiring; convert to bytes
# at the bridge boundary with ``buttons_to_nes_bytes`` (see below).
BTN_NONE = 0
BTN_LEFT = 1
BTN_RIGHT = 2
BTN_A = 3      # rotate clockwise  (CW)
BTN_B = 4      # rotate counter-clockwise (CCW)
BTN_DOWN = 5   # soft drop / lock marker

BUTTON_NAMES = {
    BTN_NONE: "NONE",
    BTN_LEFT: "LEFT",
    BTN_RIGHT: "RIGHT",
    BTN_A: "A(CW)",
    BTN_B: "B(CCW)",
    BTN_DOWN: "DOWN",
}

# Standard NES joypad bitmask (the canonical hardware layout). The project can
# remap these at the bridge -- in particular the real Dr. Mario ROM uses a
# *non-standard* layout (see ``DRMARIO_NES_BUTTON_BYTES`` below), which is what
# the Mesen file-bridge must actually write to $F5/$F6.
NES_BUTTON_BYTES = {
    BTN_A: 0x80,
    BTN_B: 0x40,
    "SELECT": 0x20,
    "START": 0x10,
    "UP": 0x08,
    BTN_DOWN: 0x04,
    BTN_LEFT: 0x02,
    BTN_RIGHT: 0x01,
    BTN_NONE: 0x00,
}

# The actual byte layout Dr. Mario reads at $F5 (P1) / $F6 (P2). Taken from
# ``rl-training-new/src/memory_map.py`` -- Dr. Mario does NOT use the standard
# joypad bit order. THIS is the table the Mesen bridge should use when poking
# controller memory. Kept separate from ``NES_BUTTON_BYTES`` so the "standard"
# reference stays intact and remapping is explicit.
DRMARIO_NES_BUTTON_BYTES = {
    BTN_RIGHT: 0x01,
    BTN_LEFT: 0x02,
    "SELECT": 0x04,
    "START": 0x08,
    BTN_DOWN: 0x10,
    BTN_A: 0x40,     # rotate CW
    BTN_B: 0x80,     # rotate CCW
    BTN_NONE: 0x00,
}

# --------------------------------------------------------------------- geometry
# Spawn: horizontal, anchor at column 3 (covers cols 3,4). Matches
# FaithfulBoard.SPAWN_COLS == (3, 4).
SPAWN_COL = 3
N_COLS = 8

# Rotation ring. We use the 4-state NES rotation order and advance CW with A:
#   0 (horiz)        -> 1 (vert CCW) -> 2 (reverse horiz) -> 3 (vert CW) -> 0
# B (CCW) goes the other way. Each ring state maps to an (orientation, flip)
# pair, and from there to the env variant. The mapping is derived as follows:
#   * rot 0: horizontal, left = A-colour, right = B-colour          -> variant 0 (H)
#   * rot 1: after one CW step the left half swings to the BOTTOM,
#            so top = B, bottom = A                                  -> variant 3 (Vflip)
#   * rot 2: reverse horizontal, left = B, right = A                -> variant 1 (Hflip)
#   * rot 3: vertical, top = A, bottom = B                          -> variant 2 (V)
ROT_HORIZ = 0
ROT_VERT_CCW = 1
ROT_REVERSE = 2
ROT_VERT_CW = 3

# rotation-ring index -> env variant
NES_ROT_TO_VARIANT = {
    ROT_HORIZ: 0,      # H     (a left,  b right)
    ROT_VERT_CCW: 3,   # Vflip (b top,   a bottom)
    ROT_REVERSE: 1,    # Hflip (b left,  a right)
    ROT_VERT_CW: 2,    # V     (a top,   b bottom)
}
VARIANT_TO_NES_ROT = {v: k for k, v in NES_ROT_TO_VARIANT.items()}

# rotation-ring index -> geometric orientation (ORIENT_H / ORIENT_V)
ROT_ORIENT = {
    ROT_HORIZ: ORIENT_H,
    ROT_VERT_CCW: ORIENT_V,
    ROT_REVERSE: ORIENT_H,
    ROT_VERT_CW: ORIENT_V,
}


def variant_orientation_flip(variant: int) -> Tuple[int, bool]:
    """Decompose an env variant into ``(orientation, flip)``.

    ``flip`` is True when the colour order is swapped relative to the canonical
    A-first layout (variant 1 for H, variant 3 for V)."""
    orientation = ORIENT_H if variant in (0, 1) else ORIENT_V
    flip = variant in (1, 3)
    return orientation, flip


def orientation_width(orientation: int) -> int:
    """How many columns the pill occupies (H = 2, V = 1)."""
    return 2 if orientation == ORIENT_H else 1


def max_anchor_col(orientation: int, n_cols: int = N_COLS) -> int:
    """Largest legal anchor column for an orientation (H stops one short)."""
    return n_cols - orientation_width(orientation)


# --------------------------------------------------------------------- state
@dataclass
class PillState:
    """Kinematic state of the falling pill (engine-independent).

    Attributes
    ----------
    anchor_col : leftmost / only column the pill occupies.
    rotation   : index into the 4-state rotation ring (0..3).
    """
    anchor_col: int = SPAWN_COL
    rotation: int = ROT_HORIZ

    @property
    def orientation(self) -> int:
        return ROT_ORIENT[self.rotation]

    @property
    def variant(self) -> int:
        return NES_ROT_TO_VARIANT[self.rotation]

    @property
    def width(self) -> int:
        return orientation_width(self.orientation)

    def occupied_cols(self) -> Tuple[int, ...]:
        if self.orientation == ORIENT_H:
            return (self.anchor_col, self.anchor_col + 1)
        return (self.anchor_col,)

    def clone(self) -> "PillState":
        return PillState(self.anchor_col, self.rotation)


def spawn_state() -> PillState:
    """The state every pill starts in: horizontal, anchor column 3."""
    return PillState(SPAWN_COL, ROT_HORIZ)


# --------------------------------------------------------------------- dynamics
def _clamp_anchor(anchor_col: int, orientation: int, n_cols: int) -> int:
    return max(0, min(anchor_col, max_anchor_col(orientation, n_cols)))


def apply_button(state: PillState, button: int, n_cols: int = N_COLS) -> PillState:
    """Return the new pill state after pressing ``button`` for one frame.

    Rules
    -----
    * LEFT / RIGHT shift the anchor by -1 / +1, clamped to legal columns for
      the current orientation (an H pill cannot have anchor > n_cols-2).
    * A / B rotate one step CW / CCW around the rotation ring. When a rotation
      lands the pill in a horizontal orientation whose anchor would be off the
      right edge, we apply a simple **wall kick**: shift the anchor left until
      it is legal (the NES nudges the pill in from the wall when you rotate
      against it). Vertical orientations are one column wide and never need a
      kick at the right wall.
    * NONE / DOWN do not change the planar position. (DOWN is a soft-drop /
      lock marker for the bridge; vertical position is not modelled here.)
    """
    s = state.clone()
    if button == BTN_LEFT:
        s.anchor_col = _clamp_anchor(s.anchor_col - 1, s.orientation, n_cols)
    elif button == BTN_RIGHT:
        s.anchor_col = _clamp_anchor(s.anchor_col + 1, s.orientation, n_cols)
    elif button in (BTN_A, BTN_B):
        s.rotation = (s.rotation + (1 if button == BTN_A else -1)) % 4
        # wall-kick: keep the (possibly now wider) pill on the board.
        s.anchor_col = _clamp_anchor(s.anchor_col, s.orientation, n_cols)
    # BTN_NONE / BTN_DOWN: no planar change.
    return s


# --------------------------------------------------------------------- planning
def _rotation_presses(from_rot: int, to_rot: int) -> List[int]:
    """Minimal A/B presses to rotate from ``from_rot`` to ``to_rot``.

    The ring has 4 states; the shortest path is at most 2 presses. A diff of 0
    -> none, 1 or -3 -> one A, 3 or -1 -> one B, 2 -> two presses (A,A; the
    direction is irrelevant for a half-turn, A is conventional)."""
    diff = (to_rot - from_rot) % 4
    if diff == 0:
        return []
    if diff == 1:
        return [BTN_A]
    if diff == 3:
        return [BTN_B]
    return [BTN_A, BTN_A]  # diff == 2, half turn


def plan_moves(
    target_orientation: int,
    target_col: int,
    target_flip: bool,
    n_cols: int = N_COLS,
    insert_release: bool = True,
) -> List[int]:
    """Plan a minimal button sequence from spawn to a target placement.

    Parameters
    ----------
    target_orientation : ``ORIENT_H`` or ``ORIENT_V``.
    target_col         : desired anchor column.
    target_flip        : True if the colour order is swapped (variant 1 / 3).
    n_cols             : board width (default 8).
    insert_release     : if True, insert a ``BTN_NONE`` (release) frame after
                         every active press so the NES registers distinct
                         button-downs. The ROM reads "newly pressed" bits each
                         frame, so a held button only fires once; we model one
                         press frame + one release frame per input. See
                         CONTROLLER_NOTES.md. Set False to get the raw,
                         release-free press list (useful for the unit-test
                         simulator, which steps each press explicitly).

    Returns
    -------
    A list of single-frame button ids. Rotations come first (so the pill has
    its final width before we slide it -- this also lets a right-wall rotation
    kick safely), then horizontal moves, then a final ``BTN_DOWN`` drop/lock
    marker. The bridge should hold each non-NONE byte for one frame.
    """
    # Resolve the target rotation-ring state from (orientation, flip).
    target_variant = _variant_from(target_orientation, target_flip)
    target_rot = VARIANT_TO_NES_ROT[target_variant]

    state = spawn_state()
    presses: List[int] = []

    # 1) Rotations first (minimal A/B). Apply through the kinematic model so the
    #    anchor tracks any wall-kick that a rotation forces.
    for b in _rotation_presses(state.rotation, target_rot):
        presses.append(b)
        state = apply_button(state, b, n_cols)

    # 2) Horizontal moves: clamp the requested column to what is legal for the
    #    final orientation, then step the anchor toward it.
    goal_col = _clamp_anchor(target_col, state.orientation, n_cols)
    while state.anchor_col < goal_col:
        presses.append(BTN_RIGHT)
        state = apply_button(state, BTN_RIGHT, n_cols)
    while state.anchor_col > goal_col:
        presses.append(BTN_LEFT)
        state = apply_button(state, BTN_LEFT, n_cols)

    # 3) Final soft-drop / lock marker.
    presses.append(BTN_DOWN)

    if not insert_release:
        return presses

    out: List[int] = []
    for b in presses:
        out.append(b)
        out.append(BTN_NONE)  # 1 release frame so the next press is "new"
    return out


def _variant_from(orientation: int, flip: bool) -> int:
    if orientation == ORIENT_H:
        return 1 if flip else 0
    return 3 if flip else 2


# --------------------------------------------------------------------- reachability
def reachable(board, target_orientation: int, target_col: int) -> bool:
    """Conservative check that the pill can be slid from spawn to the target.

    v1 heuristic (intentionally simple / conservative): the pill maneuvers in
    the top rows before it descends, so we require rows 0 and 1 to be clear
    across every column the pill must pass through -- from the spawn span
    (cols 3,4) to the target span (``target_col`` .. ``target_col`` + width-1),
    inclusive. If any of those cells is occupied in ``board.color`` we declare
    the path blocked and return False.

    This is conservative: it may reject some placements the real ROM could
    still reach (e.g. by dropping into a notch), but it will not claim a
    blocked path is open. ``False`` here should map to "skip / re-plan".
    Returns True trivially on an empty board.
    """
    n_cols = board.cols
    target_col = _clamp_anchor(target_col, target_orientation, n_cols)
    width = orientation_width(target_orientation)

    # Column span the pill body sweeps through.
    spawn_lo, spawn_hi = SPAWN_COL, SPAWN_COL + 1          # spawn is horizontal
    tgt_lo, tgt_hi = target_col, target_col + width - 1
    lo = max(0, min(spawn_lo, tgt_lo))
    hi = min(n_cols - 1, max(spawn_hi, tgt_hi))

    rows_to_check = [r for r in (0, 1) if r < board.rows]
    for r in rows_to_check:
        for c in range(lo, hi + 1):
            if board.color[r, c] != 0:  # EMPTY == 0
                return False
    return True


# --------------------------------------------------------------------- convenience
def decode_action(action_index: int, n_cols: int = N_COLS) -> Tuple[int, int, bool]:
    """Decode an env action into ``(orientation, col, flip)``.

    Mirrors ``FaithfulDrMarioEnv._decode`` but returns geometry only (no Pill /
    colour data needed by the controller -- ``flip`` carries the colour-order
    bit)."""
    variant = action_index // n_cols
    col = action_index % n_cols
    orientation, flip = variant_orientation_flip(variant)
    return orientation, col, flip


def place_to_buttons(board, action_index: int, insert_release: bool = True):
    """Decode an env action and plan its buttons.

    Returns ``(buttons, reachable_flag)``. ``buttons`` is always produced (the
    plan toward the target); ``reachable_flag`` tells the caller whether the
    conservative path check believes the maneuver is feasible on ``board``."""
    orientation, col, flip = decode_action(action_index, board.cols)
    buttons = plan_moves(orientation, col, flip, n_cols=board.cols,
                         insert_release=insert_release)
    ok = reachable(board, orientation, col)
    return buttons, ok


def buttons_to_nes_bytes(buttons: List[int], mapping=None) -> List[int]:
    """Convert an abstract button list to controller bytes for the bridge.

    Defaults to the Dr. Mario-specific layout (what $F5/$F6 actually expect).
    Pass ``mapping=NES_BUTTON_BYTES`` for the standard joypad layout."""
    table = mapping or DRMARIO_NES_BUTTON_BYTES
    return [table.get(b, 0x00) for b in buttons]


def describe(buttons: List[int]) -> str:
    """Human-readable rendering of a button list (for logs / debugging)."""
    return " ".join(BUTTON_NAMES[b] for b in buttons)
