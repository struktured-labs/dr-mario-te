#!/usr/bin/env python3
"""
CV junk reader for MiSTer NES Dr. Mario CvC, from clean 4K HDMI (OBS) frames.

junk = P2 non-virus occupied cells. A cell is EMPTY / VIRUS / PILL by:
  - occupancy: bright, not the cyan bottle wall, not the purple checkerboard bg
  - virus vs pill: interior-DARK-FRACTION (virus eyes/mouth are dark; pills solid).
    Clean bimodal split measured on live frames: pills 0.00-0.01, viruses 0.22-0.39.
junk = # pill cells; viruses = # virus cells (this virus count matches the game's
own on-screen VIRUS counter EXACTLY -- validated on 3 independent live frames).

CLEAN-HDMI ONLY. Does NOT work on phone-recorded VODs (virus faces don't resolve
at ~33px cells; see memory dr-mario-cv-junk-reader / dr-mario-vod-misreads-not-misses).

Geometry is calibrated to the bluemage MiSTer NES video mode (3840x2160). MiSTer
applies pixel-aspect correction, so the horizontal scale is ~11 px/NES-px (88 px/col)
vs ~9 vertical -- work in 4K px, do not assume 256->3840 linear. Re-detect the cyan
walls if the video mode changes.

Usage:  python3 read_board.py 'frames/*.png'
"""
import sys, glob, numpy as np
from PIL import Image

# Bottle interiors in 4K px (from the cyan walls): 88 px/col x 8 cols.
BOTTLES = {"P1": (863, 1567), "P2": (2273, 2977)}

def read_frame(path):
    """Return {'P1': (viruses, junk), 'P2': (viruses, junk)} for one 4K frame."""
    A = np.asarray(Image.open(path).convert("RGB")).astype(int)
    r, g, b = A[:, :, 0], A[:, :, 1], A[:, :, 2]
    mx = A.max(axis=2)
    wall = (r < 120) & (g > 155) & (b > 155) & (np.abs(g - b) < 75)   # bright teal bottle wall
    purple = (r < 130) & (g < 85) & (b > 45) & (b < 205)              # dark-violet checkerboard bg
    piece = (mx > 90) & (~wall) & (~purple)
    dark = (mx < 70)                                                  # near-black (virus eyes/mouth, gaps)

    def floor_ceil(x0, x1):
        xs = slice(x0 + 30, x1 - 30)
        cyc = wall[:, xs].sum(axis=1)
        thr = max(1, cyc.max() * 0.5)
        ceil_rows = [y for y in range(560, 1000) if cyc[y] > thr]
        floor_rows = [y for y in range(1600, 2050) if cyc[y] > thr]
        return (max(ceil_rows) + 6 if ceil_rows else 697), (min(floor_rows) - 2 if floor_rows else 1863)

    out = {}
    for name, (x0, x1) in BOTTLES.items():
        y0, y1 = floor_ceil(x0, x1)
        cw, ch = (x1 - x0) / 8.0, (y1 - y0) / 16.0
        vir = junk = 0
        for rr in range(16):
            for c in range(8):
                cx, cy = x0 + c * cw + cw / 2, y0 + rr * ch + ch / 2
                yy0, yy1 = int(cy - ch * .30), int(cy + ch * .30)
                xx0, xx1 = int(cx - cw * .30), int(cx + cw * .30)
                if piece[yy0:yy1, xx0:xx1].mean() > 0.28:            # occupied
                    if dark[yy0:yy1, xx0:xx1].mean() > 0.10:
                        vir += 1                                     # virus (eyes)
                    else:
                        junk += 1                                    # pill (junk)
        out[name] = (vir, junk)
    return out

if __name__ == "__main__":
    for p in sorted(glob.glob(sys.argv[1] if len(sys.argv) > 1 else "*.png")):
        rr = read_frame(p)
        print(f"{p.split('/')[-1]}: "
              f"P1 vir={rr['P1'][0]:2d} junk={rr['P1'][1]:2d} | "
              f"P2 vir={rr['P2'][0]:2d} junk={rr['P2'][1]:2d}")
