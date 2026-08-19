#!/usr/bin/env python3
"""Verify the P1 crop grid for the 20260808 capture before any tracking is run.

Same check tracker_p2.py's docstring claims for P2 (the function it names was not
actually in the file): classify a full 1920x1080 frame with the full-frame P1 grid,
classify an in-memory crop of that same frame with the crop-local grid, and require
IDENTICAL boards. Then confirm the check has teeth by shifting the origin 8px and
requiring it to DISAGREE -- a check that cannot fail proves nothing.

In-memory cropping is deliberate: it isolates the grid arithmetic, which is the part
that can be wrong, without depending on two separate ffmpeg extractions lining up.
"""
import os
import sys

import numpy as np
from PIL import Image

FILM = "/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804"
sys.path.insert(0, FILM)
from vision import P1  # noqa: E402
import tracker as T    # noqa: E402

SESSION = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/tmp/dr_lulu_20260808"
FRAMES_1FPS = os.path.join(SESSION, "frames")

CROP_DX, CROP_DY = 392, 348      # refit_dr_lulu.py P1_CROP_ORIGIN
CROP_W, CROP_H = 440, 704
P1_CROP = dict(P1, x0=P1["x0"] - CROP_DX, y0=P1["y0"] - CROP_DY)


def board_of(arr, grid):
    rows_idx, cols_idx = T.build_patch_index(grid)
    labels, isvirus = T.classify_frame_vectorized(arr, rows_idx, cols_idx)
    return labels, isvirus


def compare(full_arr, grid_dx, grid_dy):
    """Crop is ALWAYS taken at the true origin; only the GRID moves.

    Shifting the crop and the grid together cancels exactly and makes the mutant
    equivalent -- it samples the same absolute pixels and can never disagree. The
    error this check must catch is a grid that is wrong relative to a correct crop.
    """
    grid = dict(P1, x0=P1["x0"] - grid_dx, y0=P1["y0"] - grid_dy)
    crop = full_arr[CROP_DY:CROP_DY + CROP_H, CROP_DX:CROP_DX + CROP_W]
    lab_full, vir_full = board_of(full_arr, P1)
    lab_crop, vir_crop = board_of(crop, grid)
    return (lab_full == lab_crop).all() and (vir_full == vir_crop).all()


def main():
    names = sorted(f for f in os.listdir(FRAMES_1FPS) if f.endswith(".jpg"))
    # Sample across the capture, avoiding the very start (menus/title).
    picks = [names[i] for i in (len(names) // 4, len(names) // 2, 3 * len(names) // 4)]
    print(f"P1 full-frame grid : {P1}")
    print(f"P1 crop grid       : {P1_CROP}   origin=({CROP_DX},{CROP_DY}) size={CROP_W}x{CROP_H}")
    assert P1_CROP == dict(x0=40.0, y0=34.5, W=44.0, H=38.6), P1_CROP

    MUTANTS = [8, 22]  # 22px ~= half a 44px cell
    agree = 0
    mutant_agree = {m: 0 for m in MUTANTS}
    n = 0
    for name in picks:
        full = np.asarray(Image.open(os.path.join(FRAMES_1FPS, name)).convert("RGB"))
        if full.shape[:2] != (1080, 1920):
            print(f"  {name}: UNEXPECTED SHAPE {full.shape} -- skipped")
            continue
        n += 1
        ok = compare(full, CROP_DX, CROP_DY)
        agree += ok
        muts = {}
        for m in MUTANTS:
            bad = compare(full, CROP_DX + m, CROP_DY)
            mutant_agree[m] += bad
            muts[m] = bad
        print(f"  {name}: correct grid identical={ok}   "
              + "  ".join(f"+{m}px identical={muts[m]}" for m in MUTANTS))

    print()
    print(f"RESULT: {agree}/{n} frames agree with the correct grid.")
    for m in MUTANTS:
        print(f"        {mutant_agree[m]}/{n} still agree with the grid shifted +{m}px (want 0).")
    killed = [m for m in MUTANTS if mutant_agree[m] == 0]
    ok = agree == n and n > 0 and killed
    print("GEOMETRY VERIFIED (check has teeth: killed mutants "
          + ", ".join(f"+{m}px" for m in killed) + ")" if ok
          else "GEOMETRY NOT VERIFIED -- do not track")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
