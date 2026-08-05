#!/usr/bin/env python3
"""Vision calibration for the 2024 DrMC Championship VS-bracket broadcast
overlay (clean digital render, boards positioned upper-center, VIR/pill-
preview/SPD header box per player, e.g. "THE 2024 DrMC ... Red Bracket").
Same classification METHOD as film_review_20260804/vision.py (band-edge
scan -> patch-fraction color classification + dark-fraction virus/pill
split) with source-specific geometry and thresholds -- see vision_speed2025.py
for the fuller design note; this module follows the identical pattern.

GEOMETRY (calibrated against
youtube-drmc-official-2024/003_..._Red_Bracket.mp4 frame at t=500s -- the
frame located by pixel-diff matching against
captions/hud_frame_2024_Red_Championship.png, confirming this is the exact
timestamp of the archived Jenny G vs Rob Burrito reference; mean abs diff
6.05/255 at t=500, consistent with one frame of normal gameplay motion, not
a different scene):
  P1 (top-left board, Jenny G):    x0=689, y0=20, W=32.75, H=31.5
  P2 (top-right board, Rob Burrito): x0=969, y0=20, W=32.75, H=31.5
Border band-edge scan found bottom inner edge ~521-524 for both boards and
left/right playfield edges via cyan-border detection (689/951 left board,
969/1231 right board, giving W=(951-689)/8=32.75, matching for both boards).
The TOP edge could not be pinned by border-color scanning (no distinct
colored trim line detected above the play area in this template, unlike the
double cyan/purple bottle border in vision_speed2025.py) -- y0=20 is set
from H=(524-20)/16=31.5 (near-square cells, consistent with W=32.75) and
cross-checked structurally: the occupied/empty silhouette this produces
(dense bottom 2/3, near-full bottom row, sparser top) visually matches the
reference frame's board shapes. LOWER CONFIDENCE than vision_speed2025.py's
geometry on the exact top row placement -- flagged in STYLE_ENSEMBLE_V1.md.

COLOR THRESHOLDS (patch-mean sampled from real board cells at t=500;
this source's palette is MORE saturated than vision_speed2025.py's, not
reused):
  Yellow: r>100, g>100, b<100, |r-g|<40      (bright ~(185,206,60), virus-dark
                                               variant ~(140,150,58))
  Blue:   b>100, g>90, r<b, r<g               (bright ~(112,194,215), virus-dark
                                               variant ~(88,131,143))
  Red:    g<70, r>60                          (bright ~(160,4,88), virus-dark
                                               variant ~(108,58,79))
Virus-vs-pill: same dark-fraction method, threshold 0.12 (not independently
re-derived for this source -- see the same caveat in vision_speed2025.py).
"""
from __future__ import annotations

import numpy as np

NCOLS = 8
NROWS = 16

P1 = dict(x0=689.0, y0=20.0, W=32.75, H=31.5)
P2 = dict(x0=969.0, y0=20.0, W=32.75, H=31.5)

_PATCH_W = 18
_PATCH_H = 18
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
    yel_mask = (r_ch > 100) & (g_ch > 100) & (b_ch < 100) & (np.abs(r_ch - g_ch) < 40)
    blu_mask = (b_ch > 100) & (g_ch > 90) & (r_ch < b_ch) & (r_ch < g_ch)
    red_mask = (g_ch < 70) & (r_ch > 60)
    n = patch.shape[0] * patch.shape[1]
    if n == 0:
        return "."
    fracs = {"R": red_mask.sum() / n, "Y": yel_mask.sum() / n, "B": blu_mask.sum() / n}
    best = max(fracs, key=fracs.get)
    if fracs[best] < 0.10:
        return "."
    return best


def _dark_fraction(patch, thr=45):
    if patch is None or patch.size == 0:
        return 0.0
    mask = (patch[..., 0] < thr) & (patch[..., 1] < thr) & (patch[..., 2] < thr)
    return mask.sum() / (patch.shape[0] * patch.shape[1])


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
        print("usage: vision_champ2024.py <frame.jpg>")
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
