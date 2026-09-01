"""DRPROPH eligibility, computed the way proph_trigger computes it.

Transcribed from the EMITTED code (patch_cartridge_copro.py, label `proph_trigger`),
not from its comment. Strata are pre-registered in PREREG_STRATA.md.

    fo(col)   first row 0..15 whose cell is occupied; 16 if the column is empty
    TRIGGER   fo(3) <= 2 OR fo(4) <= 2
    DIRECTION fo(4) > fo(3) -> prefer RIGHT, else prefer LEFT (ties LEFT)
    GATE L    cells (0,2) and (1,2) empty      GATE R  cells (0,5) and (1,5) empty
    ELIGIBLE  preferred gate free, else the other; both blocked -> stand aside

The firmware treats $00 and $FF as empty; the video decoder sees "not occupied", which
is the same predicate for this purpose.
"""
import numpy as np
from PIL import Image
import vid_ocr

OCC = 0.25          # cell occupancy fraction that counts as a filled cell


def _grid(a, seat="p2"):
    return vid_ocr.cell_grid(a, seat, 16)


def fo(grid, col):
    for row in range(16):
        if grid[row][col] > OCC:
            return row
    return 16


def evaluate(grid):
    """Return the firmware's decision for this board."""
    f3, f4 = fo(grid, 3), fo(grid, 4)
    trig = f3 <= 2 or f4 <= 2
    gate_l = grid[0][2] <= OCC and grid[1][2] <= OCC
    gate_r = grid[0][5] <= OCC and grid[1][5] <= OCC
    if not trig:
        return {"fo3": f3, "fo4": f4, "trigger": False, "gate_l": gate_l,
                "gate_r": gate_r, "direction": None, "stratum": "OTHER"}
    prefer = "RIGHT" if f4 > f3 else "LEFT"
    first, second = (gate_r, gate_l) if prefer == "RIGHT" else (gate_l, gate_r)
    other = "LEFT" if prefer == "RIGHT" else "RIGHT"
    direction = prefer if first else (other if second else None)
    return {"fo3": f3, "fo4": f4, "trigger": True, "gate_l": gate_l, "gate_r": gate_r,
            "direction": direction,
            "stratum": "ADDRESSABLE" if direction else "UNADDRESSABLE"}


def parent_board(frames, hold_start, seat="p2"):
    """The board at the new-pill edge: walk back from the death hold to the last frame
    whose throat cells (0,3),(0,4) are BOTH clear -- i.e. before the fatal capsule
    entered the throat. Returns (index, grid) or (None, None)."""
    for i in range(hold_start, -1, -1):
        a = np.array(Image.open(frames[i]).convert("RGB")).astype(int)
        g = _grid(a, seat)
        if g[0][3] <= OCC and g[0][4] <= OCC:
            # R95: report how far back the parent search had to walk. A parent frame
            # many seconds before the death is not this pill's parent board.
            return i, g, {"parent_index": i, "walked_back_frames": hold_start - i}
    return None, None, {"parent_index": None, "walked_back_frames": hold_start + 1,
                        "warning": "no clear-throat frame in the window"}
