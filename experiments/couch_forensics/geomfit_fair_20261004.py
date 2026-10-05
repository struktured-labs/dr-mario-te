"""Geometry check/fit for the 2026-10-04 couch recordings (both bottles).

Starts from geom_dist60_20261003.json (same rivalmage OBS 1080p60 path). P1's tile origin is searched on a grid
around P2_X0 - 128 NES px * SX (the 2P bottles sit 16 tiles apart); the P2 origin is re-checked on the same grid.
Score per frame set = consistently linked halves - 2 x link violations (violations alone is degenerate: a
half-cell shift reads every tile as an unlinked single = 0 violations); the cell pitch is held at the
10/03 fit. Also reports the per-board virus count, to compare with the HUD by eye.

Usage: python geomfit_fair_20261004.py FRAMEDIR   (FRAMEDIR holds 1920x1080 rgb24 .rgb dumps)
"""
import glob
import json
import os
import sys

import numpy as np

import reader as R

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, "geom_dist60_20261003.json")))
for k in ("SX", "SY", "CW", "CH", "P2_Y0", "PREV_Y0"):
    setattr(R, k, G[k])


def score(ims, x0, y0=None):
    R.P2_X0 = x0
    if y0 is not None:
        R.P2_Y0 = y0
    rd = R.Reader()
    viol = occ = linked = 0
    for im in ims:
        x = rd.read(im)
        viol += R.link_consistent(x["color"], x["link"]); occ += int((x["color"] > 0).sum())
        linked += int((x["link"] > 0).sum())
    R.P2_Y0 = G["P2_Y0"]
    return viol, occ, linked


def main(d):
    files = sorted(glob.glob(os.path.join(d, "*.rgb")))
    ims = [np.fromfile(f, np.uint8).reshape(1080, 1920, 3).astype(int) for f in files]
    p1_seed = G["P2_X0"] - 128 * G["SX"]
    out = {}
    for name, seed in (("P1", p1_seed), ("P2", G["P2_X0"])):
        rows = []
        for dx in np.arange(-12, 12.01, 0.5):
            v, o, lk = score(ims, seed + dx)
            rows.append((-(lk - 2 * v), v, o, round(seed + dx, 2), lk))
        rows.sort()
        print(name, "best x0", rows[0][3], "viol/occ/linked", rows[0][1], "/", rows[0][2], "/", rows[0][4],
              " seed", round(seed, 2), " top5", [(r[3], r[1], r[4]) for r in rows[:5]])
        best = rows[0][3]
        ry = []
        for dy in np.arange(-4, 4.01, 1.0):
            v, o, lk = score(ims, best, G["P2_Y0"] + dy)
            ry.append((-(lk - 2 * v), v, o, round(G["P2_Y0"] + dy, 2), lk))
        ry.sort()
        print(name, "  y0 sweep best", ry[0][3], ry[0][1], "/", ry[0][2], "/", ry[0][4], " (10/03 y0", G["P2_Y0"], ")",
              [(r[3], r[1], r[4]) for r in ry[:4]])
        out[name] = best
    R.P2_X0 = out["P1"]; r1 = R.Reader()
    R.P2_X0 = out["P2"]; r2 = R.Reader()
    for f, im in zip(files, ims):
        a, b = r1.read(im), r2.read(im)
        print(os.path.basename(f), "P1 vir", int(a["virus"].sum()), "occ", int((a["color"] > 0).sum()), "prev", a["prev"],
              "| P2 vir", int(b["virus"].sum()), "occ", int((b["color"] > 0).sum()), "prev", b["prev"])
    print(json.dumps(out))


if __name__ == "__main__":
    main(sys.argv[1])
