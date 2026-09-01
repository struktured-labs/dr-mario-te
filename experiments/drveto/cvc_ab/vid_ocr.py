"""Read the Dr. Mario soak from 1080p60 OBS capture frames.

Same idea as virus_ocr (CHR-tile templates), different geometry and ONE important
difference in the matcher.

⚠ EXACT BITMAP EQUALITY DOES NOT SURVIVE THE VIDEO. The NES 256x224 image is
rescaled to 1920x1080 at non-integer factors (5.5156 x / 4.8889 y), so sampling a
NES pixel lands on interpolated content and a glyph comes back one or two pixels
different from its CHR template (measured: a '4' differed in a single row).
Exact matching returns None on a perfectly legible digit. So the video matcher is
NEAREST-TEMPLATE WITH A DECISIVE MARGIN: accept only when the best template is
within MAX_D pixels AND beats the runner-up by MIN_GAP. On a real frame the best
scores 3-6 and the runner-up 14-21, so the margin is enormous; a cell that is not
a digit fails both tests and returns None. This is not "nearest match wins" -- an
ambiguous cell is still refused.

GEOMETRY, measured on a real frame rather than assumed:
  * bottle inner walls: P1 x=431..784, P2 x=1136..1489 (found as columns bright on
    >85% of playfield rows); playfield y=346..962 (the wall's own vertical run).
    That is 353 px / 8 columns and 616 px / 16 rows.
  * the counter digits sit at NES tile row 182 in the affine fitted to those
    anchors -- two NES rows off what the 256x448 calibration implies, so the digit
    row is pinned EMPIRICALLY here rather than inherited.
"""
import numpy as np
from PIL import Image
from virus_ocr import TEMPLATES as _T, THROAT_COLS as _THROAT

P1_X0, P1_X1 = 431, 784
P2_X0, P2_X1 = 1136, 1489
PF_Y0, PF_Y1 = 346, 962
BOARDS = {"p1": (P1_X0, P1_X1), "p2": (P2_X0, P2_X1)}
SX = (P1_X1 - P1_X0) / 64.0                 # 1080p px per NES px, horizontal
SY = (PF_Y1 - PF_Y0) / 126.0                # ... vertical
OX = P1_X0 - 32 * SX
OY = PF_Y0 - 72 * SY
DIGIT_ROW = 182                             # NES tile row, pinned empirically
DIGIT_X = {"p1": 110, "p2": 131}            # tens; units is +8
# Thresholds CHOSEN BY MEASUREMENT, not by hand. Over 100 consecutive live frames
# (10 s of play), scanning MAX_D in {5,6,8,10} x MIN_GAP in {3,4,5,6}: every gap<=5
# gave 100% readable with ZERO monotonicity violations (a mid-round count INCREASE
# is necessarily a misread, so that is a real error count, not a proxy), while
# gap=6 silently discarded 33% of frames. The loss at 6 is the 9-vs-0 pair, whose
# CHR templates genuinely differ by only ~5 px -- a fixed gap is the wrong shape of
# rule for it. (6,4) sits INSIDE the plateau rather than at its edge.
MAX_D, MIN_GAP = 6, 4
DARK = 260
CELL_W, CELL_H = (P1_X1 - P1_X0) / 8.0, (PF_Y1 - PF_Y0) / 16.0


def _glyph(a, xn, yn):
    """8x8 boolean, majority vote over each NES pixel's footprint (inset 25%)."""
    g = np.zeros((8, 8), bool)
    for r in range(8):
        y0, y1 = OY + (yn + r + 0.25) * SY, OY + (yn + r + 0.75) * SY
        for c in range(8):
            x0, x1 = OX + (xn + c + 0.25) * SX, OX + (xn + c + 0.75) * SX
            blk = a[int(y0):int(y1) + 1, int(x0):int(x1) + 1]
            g[r, c] = (blk.sum(2) < DARK).mean() > 0.5
    return g


def _digit(a, xn):
    g = _glyph(a, xn, DIGIT_ROW)
    d = sorted((int((g != t).sum()), k) for k, t in _T.items())
    if d[0][0] <= MAX_D and d[1][0] - d[0][0] >= MIN_GAP:
        return d[0][1]
    return None


def read_counts(a):
    out = {}
    for seat, x in DIGIT_X.items():
        t, u = _digit(a, x), _digit(a, x + 8)
        out[seat] = None if t is None or u is None else t * 10 + u
    return out


def cell_grid(a, seat, nrows=16):
    """[[occupancy 0..1] * 8] * nrows for one seat's board."""
    c0, _ = BOARDS[seat]
    g = []
    for row in range(nrows):
        y0, y1 = int(PF_Y0 + row * CELL_H), int(PF_Y0 + (row + 1) * CELL_H)
        g.append([float((a[y0:y1, int(c0 + c * CELL_W):int(c0 + (c + 1) * CELL_W)]
                         .sum(2) > 200).mean()) for c in range(8)])
    return g


def plug_state(a, seat, thresh=0.25):
    g = cell_grid(a, seat, 3)
    throat = any(g[0][c] > thresh for c in _THROAT)
    ncells = sum(1 for row in g for x in row if x > thresh)
    return throat, ncells


def read_frame(path):
    a = np.array(Image.open(path).convert("RGB")).astype(int)
    if a.shape[:2] != (1080, 1920):
        return {"ok": False, "why": "shape %s" % (a.shape,)}
    c = read_counts(a)
    out = {"ok": True, "p1": c["p1"], "p2": c["p2"]}
    for seat in BOARDS:
        t, n = plug_state(a, seat)
        out["throat_" + seat], out["topcells_" + seat] = t, n
    return out
