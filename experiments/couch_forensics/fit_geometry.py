"""Fit the P2 tile origin for a capture from its own frames (GATE 1 prerequisite per video).

The tile period is fixed by NES geometry (43.8 x 38.57 video px per cell at 1080p, 224 visible lines);
only the phase can move between OBS sessions. Fold the capsule-hue occupancy of the P2 bottle region
over the period: the 1-NES-px inter-tile gap is the minimum. Reported origin = start of the cell period
whose first NES px is the gap (the same convention reader.py uses).

Usage: python fit_geometry.py VIDEO T1 [T2 ...]
"""
import subprocess
import sys

import numpy as np

import reader as R

X0, Y0, W, H = 1100, 320, 420, 680        # search window around the P2 bottle


def frame(video, t):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(t), "-i", video, "-frames:v", "1",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    buf = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(buf, np.uint8).reshape(1080, 1920, 3).astype(int)


def fit(video, times):
    occ = None
    for t in times:
        im = frame(video, t)[Y0:Y0 + H, X0:X0 + W]
        k = R._classify_px(im)
        o = np.isin(k, (1, 2, 3)).astype(float)
        occ = o if occ is None else occ + o
    colp, rowp = occ.mean(0), occ.mean(1)

    def phase(p, period):
        xs = np.arange(len(p))
        best = None
        for ph in np.arange(0, period, 0.25):
            m = (xs - ph) % period
            gap = p[m < period / 8].mean()
            if best is None or gap < best[0]:
                best = (gap, ph)
        return best

    gx, px = phase(colp, R.CW)
    gy, py = phase(rowp, R.CH)
    ax, ay = X0 + px, Y0 + py
    # bring the phase to the column-0 / row-0 period nearest the 9/25 fit
    ax += round((R.P2_X0 - ax) / R.CW) * R.CW
    ay += round((R.P2_Y0 - ay) / R.CH) * R.CH
    return ax, ay, gx, gy


if __name__ == "__main__":
    v = sys.argv[1]
    ts = [float(x) for x in sys.argv[2:]]
    ax, ay, gx, gy = fit(v, ts)
    print(f"P2 tile origin x0={ax:.2f} y0={ay:.2f} (gap fold x {gx:.3f}, y {gy:.3f}); "
          f"9/25 fit was x0={R.P2_X0} y0={R.P2_Y0}")
