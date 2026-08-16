#!/usr/bin/env python3
"""Machine-read a Dr. Mario bottle grid from OBS capture frames.

WHY NOT HAND-TRANSCRIBE. The one hand-read board this lane was handed
(`board_death_1321.json`) was shifted a row and carried no link plane, and
neither defect is visible in an ascii dump -- see
`dr-mario-transcribed-board-settle-gate`. Reading the pixels is both faster and
checkable.

GEOMETRY IS FITTED, NOT ASSUMED. The capture is a 4:3 pillarboxed NES image, but
rather than derive a scale the grid parameters (x0, y0, cell w, cell h) are fitted
by maximising CELL PURITY: with the grid aligned every cell centre is a near-solid
palette colour, and a grid off by a third of a cell straddles borders and mixes
them. `fit_grid` reports the purity it achieved so a bad fit is visible.

VIRUSES ARE A DARK-FRACTION THRESHOLD, AND IT MUST BE GATED. Virus sprites carry
eyes and a mouth; capsule halves are near-solid with one highlight. The separation
is real but not wide, so the threshold is calibrated against the on-screen VIRUS
counter (see `dr-mario-transcribed-board-settle-gate`: 0.42 gave exactly 26 on the
death board, matching the HUD). Never ship a virus map that was not counted
against the HUD.
"""
from __future__ import annotations

import numpy as np

COLS, ROWS = 8, 16
PAL = {1: (200, 40, 80), 2: (216, 200, 40), 3: (120, 176, 248)}
GLYPH = {0: ".", 1: "R", 2: "Y", 3: "B"}

# fitted on 20260815_130848_struktured_v6c_part2.mkv, 1920x1080
P2_GRID = (1145.5, 353.25, 43.8, 38.6)
P1_GRID = (421.5, 353.25, 43.8, 38.6)
VIRUS_DARK_THRESHOLD = 0.42


def classes(im):
    """Per-pixel palette class map: 0 = dark/background, 1..3 = nearest capsule hue."""
    d = np.stack([((im - np.array(c)) ** 2).sum(2) for c in PAL.values()], 0)
    k = d.argmin(0) + 1
    k[im.sum(2) < 150] = 0
    k[d.min(0) > 9000] = 0
    return k


def _patch(a, x0, y0, cw, ch, r, c, frac=0.30):
    cx, cy = x0 + (c + 0.5) * cw, y0 + (r + 0.5) * ch
    hw, hh = cw * frac, ch * frac
    return a[int(cy - hh):int(cy + hh), int(cx - hw):int(cx + hw)]


def fit_grid(km, x_rng, y_rng, w_rng, h_rng):
    """Grid params maximising the share of coloured pixels that agree with their
    own cell's modal colour. Returns (score, x0, y0, cw, ch)."""
    best = None
    for cw in w_rng:
        for ch in h_rng:
            for x0 in x_rng:
                for y0 in y_rng:
                    agree = tot = 0
                    bad = False
                    for r in range(ROWS):
                        for c in range(COLS):
                            p = _patch(km, x0, y0, cw, ch, r, c).ravel()
                            if p.size == 0:
                                bad = True
                                break
                            cnt = np.bincount(p, minlength=4)[1:]
                            agree += cnt.max()
                            tot += cnt.sum()
                        if bad:
                            break
                    if bad:
                        continue
                    s = agree / max(1, tot)
                    if best is None or s > best[0]:
                        best = (s, x0, y0, cw, ch)
    return best


def read_grid(km, grid=P2_GRID, occ_frac=0.20):
    """Colour plane. `occ_frac` is deliberately low: a virus is only ~40-60%
    its own colour (the face is dark), so a threshold tuned on solid capsule
    halves silently deletes every virus."""
    x0, y0, cw, ch = grid
    g = np.zeros((ROWS, COLS), int)
    for r in range(ROWS):
        for c in range(COLS):
            p = _patch(km, x0, y0, cw, ch, r, c).ravel()
            cnt = np.bincount(p, minlength=4)[1:]
            g[r, c] = 0 if cnt.max() < occ_frac * p.size else int(cnt.argmax() + 1)
    return g


def read_dark(im, grid=P2_GRID):
    x0, y0, cw, ch = grid
    d = np.zeros((ROWS, COLS))
    for r in range(ROWS):
        for c in range(COLS):
            p = _patch(im, x0, y0, cw, ch, r, c).reshape(-1, 3)
            d[r, c] = 0.0 if not p.size else float((p.sum(1) < 150).mean())
    return d


def read_frame(path, grid=P2_GRID):
    from PIL import Image
    im = np.array(Image.open(path).convert("RGB")).astype(float)
    km = classes(im)
    g = read_grid(km, grid)
    d = read_dark(im, grid)
    return g, d, (d >= VIRUS_DARK_THRESHOLD) & (g > 0)


def ascii_grid(g, vir=None):
    return "\n".join("".join(
        (GLYPH[int(g[r, c])].lower() if (vir is not None and vir[r, c] and g[r, c])
         else GLYPH[int(g[r, c])])
        for c in range(COLS)) for r in range(ROWS))
