"""Read both seats' VIRUS counters (and per-seat stack height) from a MiSTer framebuffer grab.

WHY OCR AND NOT RAM: there is no RAM read channel to the running core on silicon.
The counters are on screen continuously, and the NES draws them from CHR tiles, so
the glyphs are EXACT bitmaps -- this is template matching against the cart's own
CHR, not fuzzy OCR. A cell that matches no template returns None rather than a
guess (see read_counts).

GLYPH PROVENANCE: the digit tiles are CHR 512+d (d=0..9), located by matching the
'4' glyph lifted from a live frame and CONFIRMED on two further independent glyphs
('2' and '3') at their expected offsets in the contiguous run. Colour index 3.

CELL GEOMETRY (measured on a 256x448 grab of the ship pairing, 2026-08-31): grabs
are 2x vertically (448 = 224*2) and 1x horizontally, so an 8x8 tile is 8 wide by
16 tall. Digit row y=368..384; P1 tens/units x=110/118, P2 tens/units x=131/139.
"""
import numpy as np
from PIL import Image

CART = "/home/struktured/projects/dr-mario-tempo-wt/tmp/proph_cvc/proph1.nes"
DIGIT_TILE0, DIGIT_COLOUR = 512, 3
ROW0, ROW1 = 368, 384
CELLS = {"p1": (110, 118), "p2": (131, 139)}      # x of the TENS cell; units is +8
# Bottle INTERIORS, measured here rather than inherited: the rig's MATCH_OVER
# columns (38,110)/(148,220) straddle the bottle WALLS, and a wall is bright on
# every row, so an empty board read as "full to the ceiling". Walls found by
# scanning for columns bright on >85% of playfield rows: P1 25-31 / 96-102,
# P2 145-159 / 224-230. Interiors are the 64 px (8 cells) between them; the
# playfield's vertical extent is the wall's own bright run, rows 136-407.
BOARDS = {"p1": (32, 96), "p2": (160, 224)}
# rows 130-143 are the bottle NECK/rim (bright on every frame, both seats);
# the playfield proper is 144..396.
BOARD_R0, BOARD_R1 = 144, 396


def _templates(path=CART):
    rom = open(path, "rb").read()
    off = 16 + rom[4] * 16384
    out = {}
    for d in range(10):
        b = rom[off + (DIGIT_TILE0 + d) * 16: off + (DIGIT_TILE0 + d) * 16 + 16]
        t = np.zeros((8, 8), int)
        for r in range(8):
            lo, hi = b[r], b[r + 8]
            for c in range(8):
                t[r, c] = ((lo >> (7 - c)) & 1) | (((hi >> (7 - c)) & 1) << 1)
        out[d] = (t == DIGIT_COLOUR)
    assert len({g.tobytes() for g in out.values()}) == 10, "digit templates are not distinct"
    return out


TEMPLATES = _templates()


def _cell(a, x):
    """8x8 boolean glyph from the 2x-vertical grab. Dark ink on the light box."""
    return (a[ROW0:ROW1, x:x + 8].sum(2) < 250)[::2]


def _digit(g):
    for d, t in TEMPLATES.items():
        if np.array_equal(g, t):
            return d
    return None


def read_counts(a):
    """{'p1': int|None, 'p2': int|None}. None = this seat's box was not readable
    on this frame (round-end overlay, transition, wipe) -- NEVER a guessed value."""
    out = {}
    for seat, (x, _) in CELLS.items():
        tens, units = _digit(_cell(a, x)), _digit(_cell(a, x + 8))
        out[seat] = None if tens is None or units is None else tens * 10 + units
    return out


def board_fill(a):
    """{'p1': float, 'p2': float} = fraction of the playfield that is occupied.

    ⚠ NOT "height of the highest occupied cell": the ACTIVE FALLING CAPSULE sits in
    the spawn rows at the ceiling for part of every pill cycle, so a topmost-row
    measure reads ~0 headroom on a nearly empty board (measured: P2 with 23 viruses
    and a low stack read 0.008). Total fill is barely moved by the capsule's 2 cells.
    Used only to discriminate WHICH seat plugged on a topout round; never to infer a
    virus count."""
    out = {}
    for seat, (c0, c1) in BOARDS.items():
        r = a[BOARD_R0:BOARD_R1, c0:c1].astype(int)
        out[seat] = float((r.sum(2) > 120).mean())
    return out


def read_frame(path):
    a = np.array(Image.open(path).convert("RGB")).astype(int)
    if a.shape[:2] != (448, 256):
        return {"ok": False, "why": "BADSIZE"}
    c = read_counts(a)
    out = {"ok": True, "p1": c["p1"], "p2": c["p2"], "fill": board_fill(a)}
    for seat in BOARDS:
        thr, n = plug_state(a, seat)
        out["throat_" + seat], out["topcells_" + seat] = thr, n
    return out


# ---- cell grid + throat occupancy (the ROM's own loss condition) --------------
# Dr. Mario has exactly ONE loss condition: cells (0,3)/(0,4) occupied at pill
# throw. The playfield is 16 cell-rows over rows 144..396 and 8 cell-columns over
# the 64 px interior, so a cell is 15.75 x 8 px. Verified: the grid isolates the
# active capsule to single cells (P2 row0 col3 = 0.74 with every neighbour 0.00).
CELL_H = (BOARD_R1 - BOARD_R0) / 16.0
THROAT_COLS = (3, 4)


def cell_grid(a, seat, nrows=3):
    c0, _ = BOARDS[seat]
    out = []
    for row in range(nrows):
        r0, r1 = int(BOARD_R0 + row * CELL_H), int(BOARD_R0 + (row + 1) * CELL_H)
        out.append([float((a[r0:r1, c0 + c * 8: c0 + c * 8 + 8].sum(2) > 120).mean())
                    for c in range(8)])
    return out


def plug_state(a, seat, thresh=0.25):
    """(throat_occupied, occupied_cells_in_rows_0_2).

    ⚠ THE TRAP THIS ENCODES: the ACTIVE CAPSULE spawns in exactly the throat
    cells, so 'throat occupied' ALONE fires on ordinary mid-round spawn frames.
    A seat that actually plugged has the throat occupied AND a stack present in
    the top three rows; a lone spawning capsule occupies ~2 cells of row 0 only.
    The caller's rule (rounds.plugged) requires both."""
    g = cell_grid(a, seat, 3)
    throat = any(g[0][c] > thresh for c in THROAT_COLS)
    ncells = sum(1 for row in g for v in row if v > thresh)
    return throat, ncells
