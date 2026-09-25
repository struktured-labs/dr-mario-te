"""
Shared vision module for the 20260804 Dr. Mario film review.

Reads an 8x16 Dr. Mario bottle grid (8 columns x 16 rows) out of a raw RGB
frame array and classifies each cell as empty / Red / Yellow / Blue, plus
whether the occupying sprite is a virus (vs. a pill half).

--------------------------------------------------------------------------
GRID CALIBRATION (refined from the COMMON-block starting point)
--------------------------------------------------------------------------
The COMMON block seeded P2 at x0=1130.0, y0=392.0, W=45.6, H=40.5. That
recipe passes the coarse sanity checks (col-5 tower, dense rows 12-14) but
is NOT pixel-accurate: a per-pixel vertical/horizontal edge scan on
frames/f1110.jpg (see scratch/ for the analysis) showed the true row pitch
is ~38.6px (not 40.5) and the true column pitch is ~44.0px (not 45.6), with
cumulative drift of ~15-19px by row 14 under the original recipe -- enough
to make the inner virus/pill discrimination patch bleed into the
neighboring cell. The values below were fit from repeated black/color
transition edges down column 5 (a clean unbroken pill tower, rows 0-15)
and across multiple pill rows (columns 0,1,2,4,5), then verified by
rendering the grid as an overlay on frames/f1110.jpg (P2), frames/f1118.jpg
and frames/f1085.jpg (P1) and visually confirming every gridline falls in
the black gap between sprites, all the way to row 14, in all three frames.

    P2 = dict(x0=1136.0, y0=382.5, W=44.0, H=38.6)
    P1 = dict(x0=432.0,  y0=382.5, W=44.0, H=38.6)   # mirror of P2 about x=960

P1's x0 is close to (but not exactly) the pure mirror of the COMMON-block
P2 (1920-1130-8*45.6=425.2) computed with the REFINED W: 1920-1136-8*44=432.0.
This mirror value was then independently verified against f1118.jpg and
f1085.jpg (both show a clean mid-height P1 board) and needed no further
per-frame refinement -- the mirror-by-construction value already lines up
pixel-exact with every sprite boundary in both frames.

--------------------------------------------------------------------------
COLOR CLASSIFICATION
--------------------------------------------------------------------------
Within each cell's centered inner patch (26 x 24 px, safely inside the
44 x 38.6 cell so it never bleeds into a neighboring row/col even with a
couple of px of residual error), classify by the pixel-fraction of three
color masks:
    R: r>140, g<100, b<140
    Y: r>140, g>140, b<130
    B: b>160, (b-g)>60, r<160        (b-g>60 excludes the teal bottle glass)
Whichever of R/Y/B has the largest fraction wins; if that fraction is
<0.10 the cell reads as empty ('.').

--------------------------------------------------------------------------
VIRUS vs. PILL DISCRIMINATION
--------------------------------------------------------------------------
Viruses are sprites with a dark/black face (teeth, eyes, mouth) punched
into the colored blob; pill halves are solid rounded blobs with only a
thin black anti-aliased border (no interior black). Measuring the
dark-pixel fraction (all channels < 60) inside the same 26x24 inner patch
used for color gives a clean separation on 30 hand-labeled cells from
frames/f1110.jpg (15 pills, 15 viruses):
    pills:   dark_frac == 0.000 for all 15
    viruses: dark_frac in [0.232, 0.359] for all 15
A threshold of 0.12 (isvirus = dark_frac >= 0.12) sits in the middle of
that gap and gives 30/30 (100%) on the labeled set. See
scratch/probe_final.py output for the raw per-cell numbers.

--------------------------------------------------------------------------
CROPPED-FRAME CALLERS (60fps clips)
--------------------------------------------------------------------------
classify_grid / classify_cells take the grid dict as a parameter, so
callers driving cropped 60fps footage must pass a dict shifted by the crop
origin rather than the full-frame P1/P2 above:

  * P1 60fps crops (tmp/film_review_20260804/p1_60fps/**) are cut at
    (x=392, y=348) out of the full 1920x1080 frame. Use:
        p1_crop = dict(P1, x0=P1['x0']-392, y0=P1['y0']-348)
                = dict(x0=40.0, y0=34.5, W=44.0, H=38.6)

  * P2 "death crop" 60fps frames (tmp/film_review_20260804/p2_60fps_death/**)
    are cut at (x=1120, y=224). Use:
        p2_death_crop = dict(P2, x0=P2['x0']-1120, y0=P2['y0']-224)
                       = dict(x0=16.0, y0=158.5, W=44.0, H=38.6)

Both crop dicts keep the same W/H as the full-frame grids -- only the
origin shifts, since cropping doesn't rescale the image.
"""

import numpy as np

NCOLS = 8
NROWS = 16

# Full-frame grid dicts (see module docstring for how these were derived).
P2 = dict(x0=1136.0, y0=382.5, W=44.0, H=38.6)
P1 = dict(x0=432.0, y0=382.5, W=44.0, H=38.6)

# Inner patch size used for both color and virus-vs-pill classification.
# Kept well inside the 44 x 38.6 cell so a few px of residual calibration
# error can never pull in a neighboring cell's content.
_PATCH_W = 26
_PATCH_H = 24

# Dark-pixel (all channels below this) fraction threshold that separates
# pill halves (measured 0.000) from viruses (measured 0.232-0.359) on the
# 30-cell hand-labeled set from frames/f1110.jpg.
_VIRUS_DARK_THRESHOLD = 0.12


def _cell_patch(arr, g, c, r, pw=_PATCH_W, ph=_PATCH_H):
    """Return the pw x ph pixel patch centered on grid cell (r, c)."""
    cx = g['x0'] + (c + 0.5) * g['W']
    cy = g['y0'] + (r + 0.5) * g['H']
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
    """Classify a color patch as '.', 'R', 'Y', or 'B'."""
    if patch is None or patch.size == 0:
        return '.'
    r_ch = patch[..., 0]
    g_ch = patch[..., 1]
    b_ch = patch[..., 2]
    red_mask = (r_ch > 140) & (g_ch < 100) & (b_ch < 140)
    yel_mask = (r_ch > 140) & (g_ch > 140) & (b_ch < 130)
    blu_mask = (b_ch > 160) & ((b_ch.astype(int) - g_ch.astype(int)) > 60) & (r_ch < 160)
    n = patch.shape[0] * patch.shape[1]
    if n == 0:
        return '.'
    fracs = {
        'R': red_mask.sum() / n,
        'Y': yel_mask.sum() / n,
        'B': blu_mask.sum() / n,
    }
    best = max(fracs, key=fracs.get)
    if fracs[best] < 0.10:
        return '.'
    return best


def _dark_fraction(patch, thr=60):
    """Fraction of pixels in patch with all channels below thr."""
    if patch is None or patch.size == 0:
        return 0.0
    mask = (patch[..., 0] < thr) & (patch[..., 1] < thr) & (patch[..., 2] < thr)
    return mask.sum() / (patch.shape[0] * patch.shape[1])


def classify_grid(arr, g):
    """
    Classify all 16x8 cells of grid dict g against frame array arr.

    arr: np.asarray(Image)[..., :3], int-typed (H x W x 3 RGB).
    g:   a grid dict with x0, y0, W, H (P1, P2, or a crop-shifted variant).

    Returns a list of 16 strings, each 8 chars long, over {'.','R','Y','B'}
    (row-major, row 0 = top of the bottle).
    """
    rows = []
    for r in range(NROWS):
        row_chars = []
        for c in range(NCOLS):
            patch = _cell_patch(arr, g, c, r)
            row_chars.append(_classify_patch_color(patch))
        rows.append(''.join(row_chars))
    return rows


def classify_cells(arr, g):
    """
    Classify all 16x8 cells of grid dict g, returning both color and
    virus/pill discrimination.

    Returns (colors, isvirus):
      colors:  16x8 list of lists of chars, over {'.','R','Y','B'}
      isvirus: 16x8 list of lists of bool -- True where the cell's dominant
               sprite is a virus (dark-pixel fraction >= threshold), False
               for pill halves or empty cells.
    """
    colors = []
    isvirus = []
    for r in range(NROWS):
        color_row = []
        virus_row = []
        for c in range(NCOLS):
            patch = _cell_patch(arr, g, c, r)
            ch = _classify_patch_color(patch)
            color_row.append(ch)
            if ch == '.':
                virus_row.append(False)
            else:
                virus_row.append(_dark_fraction(patch) >= _VIRUS_DARK_THRESHOLD)
        colors.append(color_row)
        isvirus.append(virus_row)
    return colors, isvirus


if __name__ == '__main__':
    # Smoke test / self-check against frames/f1110.jpg (P2) when run directly.
    import os
    from PIL import Image

    here = os.path.dirname(os.path.abspath(__file__))
    frame_path = os.path.join(here, 'frames', 'f1110.jpg')
    im = Image.open(frame_path).convert('RGB')
    arr = np.asarray(im)[..., :3].astype(int)

    print('P2 grid on f1110.jpg:')
    for i, row in enumerate(classify_grid(arr, P2)):
        print(f'{i:2d} {row}')

    colors, isvirus = classify_cells(arr, P2)
    print('\nVirus map (X=virus, o=pill, .=empty):')
    for r in range(NROWS):
        line = []
        for c in range(NCOLS):
            if colors[r][c] == '.':
                line.append('.')
            elif isvirus[r][c]:
                line.append('X')
            else:
                line.append('o')
        print(f'{r:2d} {"".join(line)}')
