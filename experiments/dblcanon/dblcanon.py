"""Double-capsule placement canonicalisation (task #123) -- the shared core.

A capsule whose two halves share a colour (`cur.a == cur.b`, one capsule in
three) produces every PHYSICAL placement twice in the 32-slot action space,
because the two colour-orderings within an axis are indistinguishable once the
colours are equal.  The duplicate members are the SAME board but NOT the same
cost to reach: the cart's rotation executor is CCW-only, so the two members of
a pair sit 180 degrees apart and differ by exactly two rotations from spawn.

This module holds three things and nothing else:

  * `ROT_COST_O4`  -- rotations-from-spawn, DERIVED from the driver's own two
    tables rather than asserted, so a driver change breaks this loudly.
  * `pair_partner` / `canonical_o4` -- the canonicalisation itself.
  * `pairing_from_boards` -- the pairing DERIVED FROM RESULTING BOARDS.

⚠⚠ THE PAIRING IS NOT `(v, v+2)` AND IT IS NOT READABLE OFF `_VAR_OF_O4`.
The `(v, v+2)` key was tried, removes nothing, and reports a clean bill of
health while doing so (1.1% on doubles vs 0.9% on non-doubles -- pure noise --
against a board-level tie rate of exactly 1.0000 on the same plies).  Nothing
in this file may derive the pairing from slot arithmetic; `pairing_from_boards`
is the only sanctioned derivation and the gate re-derives it every run.
"""

import numpy as np

# --- the two driver tables, transcribed from the cart emitter -----------------
# `patch_cartridge_copro.py` maps the copro result mailbox ($x086 / $616C, which
# is COPRO-space `a_o4`) to the ROM's game orientation ($03A5) at two sites --
# `handle()`'s DONE branch (`{L}_map` .. `{L}_pst`) and the DRROTFIX anytime
# weave path (`nf2_o1` .. `nf2_ost`) -- both emitting the same map:
GAME_OF_O4 = {0: 3, 1: 1, 2: 0, 3: 2}

# The executor presses ONLY A.  A is CCW, which is `DEC $A5` at ROM $8E2B, so
# the game orientation walks 0 -> 3 -> 2 -> 1 -> 0, one step per rotation.  A
# capsule spawns at game orientation 0.  There is no B / clockwise path, so the
# cost of a target is the CCW distance from 0 and nothing else.
SPAWN_GAME_ORIENT = 0


def rot_cost_game(game_orient):
    """CCW rotations to reach `game_orient` from spawn.  DEC wraps 0->3."""
    return (SPAWN_GAME_ORIENT - int(game_orient)) % 4


ROT_COST_O4 = {o4: rot_cost_game(g) for o4, g in GAME_OF_O4.items()}
# = {0: 1, 1: 3, 2: 0, 3: 2}


# --- the canonicalisation ----------------------------------------------------
# Which o4 pairs with which is a MEASURED fact (`pairing_from_boards`, and the
# gate that re-derives it on every real double ply).  It is recorded here as a
# constant only so the silicon has something to compile; `assert_pairing` is
# what makes it true.
PAIR_PARTNER_O4 = {0: 1, 1: 0, 2: 3, 3: 2}


def canonical_o4(o4):
    """The cheaper-to-reach member of `o4`'s duplicate pair.

    Only meaningful when the capsule is a double; the caller gates on that.
    """
    o4 = int(o4)
    partner = PAIR_PARTNER_O4[o4]
    if ROT_COST_O4[partner] < ROT_COST_O4[o4]:
        return partner
    return o4


def is_canonical_o4(o4):
    return canonical_o4(o4) == int(o4)


def rotations_saved(o4):
    """Rotations this canonicalisation removes for a chosen `o4` on a double."""
    return ROT_COST_O4[int(o4)] - ROT_COST_O4[canonical_o4(o4)]


def is_double(cur):
    return int(cur.a) == int(cur.b)


# --- deriving the pairing from boards, which is the only honest way ----------
def board_key(board):
    """Cell-for-cell identity of a resolved board.

    Colour plane only would be enough for the placement claim, but the link
    plane is what distinguishes a linked pair from two loose halves and a
    canonicalisation that silently unlinked a capsule would still be a defect.
    Both planes go into the key when the board carries one.
    """
    parts = [np.asarray(board.color).tobytes()]
    link = getattr(board, "link", None)
    if link is not None:
        parts.append(np.asarray(link).tobytes())
    return b"|".join(parts)


def pairing_from_boards(env, legal_slots, var_of_o4):
    """Group `legal_slots` (32-space indices) by the board each one produces.

    Returns {board_key: sorted[slot, ...]}.  Every step runs on a deepcopy, so
    `env` is untouched -- `import mutates BOARD` is a live trap in this repo.
    """
    import copy
    groups = {}
    for s in legal_slots:
        e = copy.deepcopy(env)
        e.step(int(s))
        groups.setdefault(board_key(e.board), []).append(int(s))
    return {k: sorted(v) for k, v in groups.items()}


def slot_to_o4_col(slot, var_of_o4):
    """32-slot index -> (o4, column).  `_VAR_OF_O4` is self-inverse."""
    slot = int(slot)
    return int(var_of_o4[slot // 8]), slot % 8


def o4_col_to_slot(o4, col, var_of_o4):
    return int(var_of_o4[int(o4)]) * 8 + int(col)


def assert_pairing(groups, var_of_o4, ctx=""):
    """The claim, checked against a real ply's board grouping.

    On a DOUBLE every group must be exactly one o4-pair at one column, or a
    singleton (the partner was illegal).  Anything else -- a group of three, a
    group spanning two columns, a pair that is not `PAIR_PARTNER_O4` -- means
    the pairing this lane is built on is wrong, and the caller must stop.
    """
    bad = []
    for key, slots in groups.items():
        oc = [slot_to_o4_col(s, var_of_o4) for s in slots]
        cols = {c for _, c in oc}
        o4s = sorted(o for o, _ in oc)
        if len(slots) == 1:
            continue
        if len(slots) != 2 or len(cols) != 1:
            bad.append((ctx, slots, oc, "group size/column"))
            continue
        if PAIR_PARTNER_O4[o4s[0]] != o4s[1]:
            bad.append((ctx, slots, oc, "not the recorded partner"))
    return bad
