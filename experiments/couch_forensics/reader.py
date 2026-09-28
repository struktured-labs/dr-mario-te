"""Frame reader for the 2026-09-25 couch recording (1080p60 OBS, 4:3 pillarboxed NES image).

Geometry was FITTED on this capture (not inherited): each bottle cell is 8x8 NES pixels at
5.475 x 4.8214 video px per NES px (224 visible lines -> 1080). A drawn tile is the 7x7 NES px at
offsets 1..7 (offset 0 is the inter-tile gap). Tile origins (video px, cell (r, c)):
    P2 board   x = 1131.5 + 43.8 c,  y = 340.2 + 38.57 r
    P2 preview x = 1131.5 + 43.8 (3|4), y = 204.2
Fitted by (a) purity of cell colours (0.96) and (b) the folded occupancy profile's gap phase.

Tile classes, read at NES-pixel resolution (median of a 3x3 video-px window per NES px):
  * colour = majority capsule hue among coloured px (pill highlights are another hue, a minority)
  * virus  = >= VIRUS_MIN_DARK dark px in the 5x5 interior (eyes/mouth); capsule halves have ~0
  * link   = from which tile corners are notched (dark): the rounded end of a capsule half is
             chamfered, the joined side is square. TL+BL notched = left half (partner RIGHT), TR+BR =
             right half (partner LEFT), TL+TR = top half (partner DOWN), BL+BR = bottom half (partner
             UP), all four = single. Codes follow drmario.faithful_game (UP=1 DOWN=2 LEFT=3 RIGHT=4).
"""
from __future__ import annotations

import numpy as np

SX, SY = 5.475, 4.8214
CW, CH = 43.8, 38.57
P2_X0, P2_Y0 = 1131.5, 340.2
PREV_Y0 = 204.2
ROWS, COLS = 16, 8
VIRUS_MIN_DARK = 4

# Per-capture geometry override (a different MiSTer output / capture path moves and rescales the image):
# CF_GEOM=<json with SX, SY, CW, CH, P2_X0, P2_Y0, PREV_Y0>, fitted with fit_geometry-style gap folds.
import json as _json
import os as _os
if _os.environ.get("CF_GEOM"):
    _d = _json.load(open(_os.environ["CF_GEOM"]))
    SX, SY, CW, CH = _d["SX"], _d["SY"], _d["CW"], _d["CH"]
    P2_X0, P2_Y0, PREV_Y0 = _d["P2_X0"], _d["P2_Y0"], _d["PREV_Y0"]
    VIRUS_MIXED = bool(_d.get("VIRUS_MIXED", False))
else:
    VIRUS_MIXED = False
# VIRUS_MIXED (soft captures, e.g. 720p upscaled): one virus animation frame has only 1-2 dark interior px;
# a virus face still MIXES hues in the inner 3x3 (eyes/mouth), while a capsule half's inner 3x3 is its pure
# colour (the highlight bar sits on the tile edge). virus |= (#inner-3x3 px != tile colour) >= 3.

LINK_NONE, LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT = 0, 1, 2, 3, 4


def _classify_px(rgb):
    """rgb [..., 3] -> 0 dark, 1 red, 2 yellow, 3 blue, 9 other (bright but not a capsule hue)."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    out = np.full(r.shape, 9, np.int8)
    dark = (r + g + b) < 150
    red = (r > 110) & (g < 95) & (b < 140)
    yel = (r > 120) & (g > 120) & (b < 120)
    blu = (b > 160) & (g > 110) & (r < 170)
    out[red] = 1; out[yel] = 2; out[blu] = 3; out[dark] = 0
    return out


def _sample_grid(origins, x_off=0.0, y_off=0.0):
    """origins: list of (x, y) tile origins -> integer (N, 8, 8, 9) y/x index arrays for a 3x3 window."""
    ii = (np.arange(8) + 0.5)
    ys, xs = [], []
    for (x, y) in origins:
        cx = x - x_off + ii * SX           # [8] over i
        cy = y - y_off + ii * SY           # [8] over j
        gx = np.broadcast_to(cx[None, :], (8, 8))
        gy = np.broadcast_to(cy[:, None], (8, 8))
        wx, wy = [], []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                wx.append(gx.astype(int) + dx); wy.append(gy.astype(int) + dy)
        xs.append(np.stack(wx, -1)); ys.append(np.stack(wy, -1))
    return np.stack(ys), np.stack(xs)


class Reader:
    """Reads P2 board + preview from a frame (full 1920x1080, or a crop with its offset)."""

    def __init__(self, x_off=0.0, y_off=0.0):
        board = [(P2_X0 + c * CW, P2_Y0 + r * CH) for r in range(ROWS) for c in range(COLS)]
        prev = [(P2_X0 + 3 * CW, PREV_Y0), (P2_X0 + 4 * CW, PREV_Y0)]
        self.by, self.bx = _sample_grid(board, x_off, y_off)
        self.py, self.px = _sample_grid(prev, x_off, y_off)

    @staticmethod
    def _tiles(im, ys, xs):
        win = im[ys, xs]                       # (N, 8, 8, 9, 3)
        med = np.median(win, axis=3)           # (N, 8, 8, 3)
        return _classify_px(med)               # (N, 8, 8)

    @staticmethod
    def _decode(t):
        """t: (N, 8, 8) px classes -> colour, virus, link, n_coloured arrays."""
        core = t[:, 1:8, 1:8]
        col_px = np.isin(core, (1, 2, 3))
        ncol = col_px.sum((1, 2))
        colour = np.zeros(len(t), np.int8)
        for k in range(len(t)):
            if ncol[k] >= 12:
                cnt = np.bincount(core[k][col_px[k]], minlength=4)[1:4]
                colour[k] = int(cnt.argmax() + 1)
        interior = t[:, 2:7, 2:7]
        ndark = (interior == 0).sum((1, 2))
        virus = (colour > 0) & (ndark >= VIRUS_MIN_DARK)
        if VIRUS_MIXED:
            inner = t[:, 3:6, 3:6]
            nonmain = (inner != colour[:, None, None]).sum((1, 2))
            virus = virus | ((colour > 0) & (nonmain >= 3))
        # notched = the corner px is NOT the tile's own hue (dark, or a dark/hue blend the median
        # left as "other"); the square joined side keeps its corner in the tile colour.
        tl, tr = t[:, 1, 1] != colour, t[:, 1, 7] != colour
        bl, br = t[:, 7, 1] != colour, t[:, 7, 7] != colour
        link = np.zeros(len(t), np.int8)
        pill = (colour > 0) & ~virus
        link[pill & tl & bl & ~tr & ~br] = LINK_RIGHT
        link[pill & tr & br & ~tl & ~bl] = LINK_LEFT
        link[pill & tl & tr & ~bl & ~br] = LINK_DOWN
        link[pill & bl & br & ~tl & ~tr] = LINK_UP
        return colour, virus, link, ncol

    @staticmethod
    def _wall_links(t, colour, virus, link):
        """The bottle walls are light blue and bleed into the wall-side corners of columns 0 and 7, so a BLUE
        tile there reads its outer corners as 'square'. Decide those tiles' links from the inner corners only:
        col 0: TR,BR square -> left half (RIGHT); TR notched, BR square -> top (DOWN); TR square, BR notched ->
        bottom (UP); both notched -> single. Col 7 mirrors with TL,BL. Identical to the 4-corner rule whenever
        the outer corners read correctly."""
        link = link.copy()
        for k in range(len(t)):
            c = k % COLS
            if c not in (0, COLS - 1) or colour[k] == 0 or virus[k]:
                continue
            ic = 7 if c == 0 else 1                       # inner-side corner column
            top_n = t[k, 1, ic] != colour[k]
            bot_n = t[k, 7, ic] != colour[k]
            if not top_n and not bot_n:
                link[k] = LINK_RIGHT if c == 0 else LINK_LEFT
            elif top_n and not bot_n:
                link[k] = LINK_DOWN
            elif bot_n and not top_n:
                link[k] = LINK_UP
            else:
                link[k] = LINK_NONE
        return link

    def read(self, im):
        """im: HxWx3 uint8/int array. Returns dict with 16x8 colour/virus/link and preview (a, b)."""
        t = self._tiles(im, self.by, self.bx)
        colour, virus, link, _ = self._decode(t)
        link = self._wall_links(t, colour, virus, link)
        pt = self._tiles(im, self.py, self.px)
        pc, _, pl, _ = self._decode(pt)
        return {"color": colour.reshape(ROWS, COLS), "virus": virus.reshape(ROWS, COLS),
                "link": link.reshape(ROWS, COLS), "prev": (int(pc[0]), int(pc[1])),
                "prev_link": (int(pl[0]), int(pl[1]))}


def link_consistent(color, link):
    """Every linked half must point at a same-pill partner that points back. Returns #violations."""
    bad = 0
    d = {LINK_UP: (-1, 0, LINK_DOWN), LINK_DOWN: (1, 0, LINK_UP),
         LINK_LEFT: (0, -1, LINK_RIGHT), LINK_RIGHT: (0, 1, LINK_LEFT)}
    for r in range(ROWS):
        for c in range(COLS):
            lk = int(link[r, c])
            if lk == 0:
                continue
            dr, dc, back = d[lk]
            rr, cc = r + dr, c + dc
            if not (0 <= rr < ROWS and 0 <= cc < COLS) or color[rr, cc] == 0 or int(link[rr, cc]) != back:
                bad += 1
    return bad


GLYPH = {0: ".", 1: "r", 2: "y", 3: "b"}
LGLY = {0: "o", 1: "^", 2: "v", 3: "<", 4: ">"}


def ascii_board(rd):
    rows = []
    for r in range(ROWS):
        s = ""
        for c in range(COLS):
            k = int(rd["color"][r, c])
            if k == 0:
                s += ".  "
            elif rd["virus"][r, c]:
                s += GLYPH[k].upper() + "* "
            else:
                s += GLYPH[k] + LGLY[int(rd["link"][r, c])] + " "
        rows.append(s)
    return "\n".join(rows)
