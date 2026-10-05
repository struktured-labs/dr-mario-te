"""Stream a window of a couch recording and read BOTH bottles (P1 = the owner, P2 = the AI) in ONE decode.

scan_frames.py reads only P2 (fixed crop). Here the reader geometry comes from a CF_GEOM-style json that also
carries P1_X0 (P1's tile origin; P1 shares P2's row origin, cell pitch and preview row). The P1 Reader is the same
reader.Reader with P2_X0 swapped for P1_X0 at construction (Reader reads the module globals at __init__ only).

Usage: python scan2_fair_20261004.py GEOM.json VIDEO T_START DURATION FPS OUT_PREFIX
  -> OUT_PREFIX_p1.jsonl, OUT_PREFIX_p2.jsonl (scan_frames.py line format: i, t, color, virus, link, prev, prev_link)
     OUT_PREFIX_hud.jsonl (HUD digit masks, every frame at FPS<=4, else every FPS//2-th frame)
t = T_START + i / FPS. Seeks with -ss (never -sseof: the recording may still be growing).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np

import reader as R

X_OFF, Y_OFF, W, H = 380, 180, 1140, 800       # covers both bottles, both previews, and the HUD digits


def make_readers(geom):
    for k in ("SX", "SY", "CW", "CH", "P2_Y0", "PREV_Y0"):
        setattr(R, k, geom[k])
    R.VIRUS_MIXED = bool(geom.get("VIRUS_MIXED", False))
    R.P2_X0 = geom["P1_X0"]
    r1 = R.Reader(X_OFF, Y_OFF)
    R.P2_X0 = geom["P2_X0"]
    r2 = R.Reader(X_OFF, Y_OFF)
    return r1, r2


def hud_masks(im, geom):
    """8x8 dark masks of the four HUD digits (hud_digits.py method), boxes from geom['HUD_X'], geom['HUD_Y']."""
    out = {}
    for k, x0 in geom["HUD_X"].items():
        m = np.zeros((8, 8), np.int8)
        for j in range(8):
            for i in range(8):
                cx = int(x0 - X_OFF + (i + 0.5) * geom["SX"]); cy = int(geom["HUD_Y"] - Y_OFF + (j + 0.5) * geom["SY"])
                p = im[cy - 1:cy + 2, cx - 1:cx + 2].reshape(-1, 3)
                m[j, i] = 1 if np.median(p.sum(1)) < 200 else 0
        out[k] = "".join(str(int(v)) for v in m.ravel())
    return out


def rec(i, t, x):
    return {"i": i, "t": t,
            "color": "".join(str(int(v)) for v in x["color"].ravel()),
            "virus": "".join("1" if v else "0" for v in x["virus"].ravel()),
            "link": "".join(str(int(v)) for v in x["link"].ravel()),
            "prev": x["prev"], "prev_link": x["prev_link"]}


def main(geom_path, video, t0, dur, fps, prefix):
    geom = json.load(open(geom_path))
    r1, r2 = make_readers(geom)
    vf = f"crop={W}:{H}:{X_OFF}:{Y_OFF}" if fps >= 60 else f"fps={fps},crop={W}:{H}:{X_OFF}:{Y_OFF}"
    cmd = ["ffmpeg", "-v", "error", "-threads", "1", "-ss", str(t0), "-i", video, "-t", str(dur),
           "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H * 3
    hud_every = 1 if fps <= 4 else max(1, int(fps) // 2)
    i = 0
    with open(prefix + "_p1.jsonl", "w") as f1, open(prefix + "_p2.jsonl", "w") as f2, open(prefix + "_hud.jsonl", "w") as fh:
        while True:
            buf = p.stdout.read(n)
            if len(buf) < n:
                break
            im = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(int)
            t = round(float(t0) + i / float(fps), 4)
            f1.write(json.dumps(rec(i, t, r1.read(im))) + "\n")
            f2.write(json.dumps(rec(i, t, r2.read(im))) + "\n")
            if "HUD_X" in geom and i % hud_every == 0:
                fh.write(json.dumps({"t": t, **hud_masks(im, geom)}) + "\n")
            i += 1
    p.wait()
    print(f"frames {i} -> {prefix}_p1/_p2/_hud.jsonl")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6])
