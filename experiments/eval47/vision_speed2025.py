#!/usr/bin/env python3
"""Vision calibration for the 2025 DrMC "Speed Bracket" broadcast overlay
(vector-art bottle graphics on a purple checkerboard background, webcam PIPs
top corners -- e.g. "June 2025 Gold Speed Bracket", "Jan 2025 Gold Speed
Bracket"). Same classification METHOD as film_review_20260804/vision.py
(band-edge scanning to find the grid geometry, then patch-fraction color
classification + dark-fraction virus/pill discrimination) but with NEW
geometry and NEW color thresholds calibrated for this source -- the palette
here is visibly more muted/desaturated than the struktured capture's direct
NES-composite feed (this is a stylized vector rendering, not a straight
emulator passthrough), so the struktured thresholds do not transfer.

GEOMETRY (calibrated against
youtube-drmc-official-2025/20250728_xH8Jyz5cl3I_..._DaveSmithSays_vs_OOKtheLibrarian.mp4
frame at t=400s, via full-RGB vertical/horizontal scans through clean empty
and border regions -- see eval47/tmp/style_ensemble/calib_dsms_vs_ook/ for
the scan dumps this was derived from):
  P1 (left bottle):  x0=595, y0=291, W=40.5, H=41.0
  P2 (right bottle):  x0=1010, y0=291, W=40.5, H=41.0
Both bottles share identical W/H (verified: left playfield span 919-595=324px
over 8 cols=40.5; right bottle's border geometry matches left's by direct
scan). x0 origins found by scanning for the true INNER edge of a two-layer
cyan+purple border (the cyan trim line alone undershoots -- there's a
thicker purple layer beyond it that must also be excluded, unlike vision.py's
single-line struktured border).

COLOR THRESHOLDS (muted vector-art palette, patch-mean sampled, NOT the
struktured raw thresholds):
  Blue:   b > 180, g > 140, r < 160, b > g            (sample means ~(115,170,215))
  Yellow: r > 140, g > 140, b < 130, |r-g| < 30        (sample means ~(185,187,75))
  Red:    g < 40, r > 60, b > 30                       (sample means ~(95,12,55) --
          this palette's "red" renders as a dark magenta, g near-zero is the
          only reliable discriminator; r and b are both moderate and similar)
  Empty background steady-state ~(21,21,21) (near-black, NOT pure 0 -- there's
  a faint stream-compositing tint).

Virus-vs-pill: same dark-fraction method as struktured's vision.py (viruses
have a dark eyes/teeth/mouth texture), but NOT recalibrated against a
hand-labeled set here (out of scope for this pass -- ASCII validation below
checks the color/position discrimination is sound; virus-vs-pill accuracy
is the SECONDARY signal bursty_model needs, since extract_volleys/
extract_clears only look at occupied-cell counts, colors are used for volley
size/color -- but is not the primary trigger). Uses the same threshold value
(0.12) as struktured's calibration; not independently re-derived.
"""
from __future__ import annotations

import numpy as np

NCOLS = 8
NROWS = 16

P1 = dict(x0=595.0, y0=291.0, W=40.5, H=41.0)
P2 = dict(x0=1010.0, y0=291.0, W=40.5, H=41.0)

_PATCH_W = 22
_PATCH_H = 22
_VIRUS_DARK_THRESHOLD = 0.12


def _cell_patch(arr, g, c, r, pw=_PATCH_W, ph=_PATCH_H):
    cx = g["x0"] + (c + 0.5) * g["W"]
    cy = g["y0"] + (r + 0.5) * g["H"]
    x0 = int(round(cx - pw / 2))
    x1 = x0 + pw
    y0 = int(round(cy - ph / 2))
    y1 = y0 + ph
    h, w = arr.shape[0], arr.shape[1]
    x0c, x1c = max(0, x0), min(w, x1)
    y0c, y1c = max(0, y0), min(h, y1)
    if x1c <= x0c or y1c <= y0c:
        return None
    return arr[y0c:y1c, x0c:x1c, :]


def _classify_patch_color(patch):
    if patch is None or patch.size == 0:
        return "."
    r_ch = patch[..., 0].astype(int)
    g_ch = patch[..., 1].astype(int)
    b_ch = patch[..., 2].astype(int)
    blu_mask = (b_ch > 180) & (g_ch > 140) & (r_ch < 160) & (b_ch > g_ch)
    yel_mask = (r_ch > 140) & (g_ch > 140) & (b_ch < 130) & (np.abs(r_ch - g_ch) < 30)
    red_mask = (g_ch < 40) & (r_ch > 60) & (b_ch > 30)
    n = patch.shape[0] * patch.shape[1]
    if n == 0:
        return "."
    fracs = {"R": red_mask.sum() / n, "Y": yel_mask.sum() / n, "B": blu_mask.sum() / n}
    best = max(fracs, key=fracs.get)
    if fracs[best] < 0.10:
        return "."
    return best


def _dark_fraction(patch, thr=55):
    if patch is None or patch.size == 0:
        return 0.0
    mask = (patch[..., 0] < thr) & (patch[..., 1] < thr) & (patch[..., 2] < thr)
    return mask.sum() / (patch.shape[0] * patch.shape[1])


def classify_grid(arr, g):
    rows = []
    for r in range(NROWS):
        row_chars = []
        for c in range(NCOLS):
            patch = _cell_patch(arr, g, c, r)
            row_chars.append(_classify_patch_color(patch))
        rows.append("".join(row_chars))
    return rows


def classify_cells(arr, g):
    colors, isvirus = [], []
    for r in range(NROWS):
        color_row, virus_row = [], []
        for c in range(NCOLS):
            patch = _cell_patch(arr, g, c, r)
            ch = _classify_patch_color(patch)
            color_row.append(ch)
            if ch == ".":
                virus_row.append(False)
            else:
                virus_row.append(_dark_fraction(patch) >= _VIRUS_DARK_THRESHOLD)
        colors.append(color_row)
        isvirus.append(virus_row)
    return colors, isvirus


if __name__ == "__main__":
    import sys
    from PIL import Image

    fp = sys.argv[1] if len(sys.argv) > 1 else None
    if not fp:
        print("usage: vision_speed2025.py <frame.jpg>")
        sys.exit(1)
    im = Image.open(fp).convert("RGB")
    arr = np.asarray(im)[..., :3].astype(int)
    for side, g in (("P1", P1), ("P2", P2)):
        colors, isvirus = classify_cells(arr, g)
        occ = sum(1 for row in colors for ch in row if ch != ".")
        print(f"\n{side} ({occ}/128 occupied):")
        for r in range(NROWS):
            line = []
            for c in range(NCOLS):
                if colors[r][c] == ".":
                    line.append(".")
                elif isvirus[r][c]:
                    line.append("X")
                else:
                    line.append("o")
            print(f"{r:2d} {''.join(line)}")
