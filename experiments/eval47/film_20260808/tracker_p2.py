#!/usr/bin/env python3
"""P2 (AI side) capsule tracker for the 20260808 dr_lulu capture, per match window.

Same shape as the 20260804 review's `tracker_p2_death.py`: every pure function comes from
`tracker.py` UNCHANGED (search_capsule, label_orient, cells_for, rotation_direction,
new_pill_state, finalize_pill, classify_frame_vectorized, build_patch_index, CSV_FIELDS,
write_csv, write_paths_jsonl). Only the crop grid, frames root and the outer per-frame loop
are re-implemented, because tracker.track_window() hardcodes P1_CROP/FRAMES_ROOT internally
rather than taking them as parameters. Nothing in tracker.py is modified.

CROP GRID. The 60fps P2 clips are cut at (x=1088, y=348), 440x704 -- refit_dr_lulu.py's
P2_CROP_ORIGIN, the derived mirror of P1's documented origin. So the crop-local grid is
    dict(P2, x0=1136-1088, y0=382.5-348) = dict(x0=48.0, y0=34.5, W=44.0, H=38.6)
VERIFIED, not assumed: classifying a full 1920x1080 frame with the full-frame P2 grid and
classifying its crop with this grid give IDENTICAL boards on 3 sampled frames, and an
origin wrong by 8px is detected (see the assert + verify_crop() below).

    tracker_p2.py <mid> <window_start_seconds>      e.g. tracker_p2.py m3 555
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
from PIL import Image

FILM = "/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804"
sys.path.insert(0, FILM)
from vision import P2  # noqa: E402
import tracker as T    # noqa: E402  -- reuse pure functions, do not modify the module

SESSION = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/tmp/dr_lulu_20260808"
FRAMES_60 = os.path.join(SESSION, "p2_60fps")
EVENTS_ROOT = os.path.join(SESSION, "events")

CROP_DX, CROP_DY = 1088, 348
P2_CROP = dict(P2, x0=P2["x0"] - CROP_DX, y0=P2["y0"] - CROP_DY)
assert P2_CROP == dict(x0=48.0, y0=34.5, W=44.0, H=38.6), P2_CROP
STALL_FALLBACK_FRAMES = 180


def load_frames(frames_root, n_frames):
    rows_idx, cols_idx = T.build_patch_index(P2_CROP)
    for i in range(1, n_frames + 1):
        arr = np.asarray(Image.open(os.path.join(frames_root, f"f{i:06d}.jpg")).convert("RGB"))
        labels, isvirus = T.classify_frame_vectorized(arr, rows_idx, cols_idx)
        yield i, labels, isvirus


def track(frames_root, n_frames, window_start_abs, tag):
    t0 = time.time()
    all_labels, all_isvirus = [], []
    for _idx, labels, isvirus in load_frames(frames_root, n_frames):
        all_labels.append(labels)
        all_isvirus.append(isvirus)
    print(f"[{tag}] classified {n_frames} frames in {time.time()-t0:.1f}s", file=sys.stderr)

    rows, paths = [], []
    pill_id, state, pill = 0, "SEEK", None

    def record_path(pid, at_frame, p):
        paths.append(dict(pill_id=pid, frame=at_frame, r=p["row"], c=p["col"], orient=p["orient"]))

    def do_finalize(p, pid, at_frame):
        rows.append(T.finalize_pill(p, pid, at_frame, all_isvirus, n_frames, window_start_abs))

    fl, fv = all_labels[0], all_isvirus[0]
    prev_spawn_colored = (fl[T.SPAWN_ROW, T.SPAWN_COLS[0]] != "." and fl[T.SPAWN_ROW, T.SPAWN_COLS[1]] != "."
                          and not fv[T.SPAWN_ROW, T.SPAWN_COLS[0]] and not fv[T.SPAWN_ROW, T.SPAWN_COLS[1]])

    for f in range(1, n_frames + 1):
        labels, isvirus = all_labels[f - 1], all_isvirus[f - 1]
        c0, c1 = labels[T.SPAWN_ROW, T.SPAWN_COLS[0]], labels[T.SPAWN_ROW, T.SPAWN_COLS[1]]
        v0, v1 = isvirus[T.SPAWN_ROW, T.SPAWN_COLS[0]], isvirus[T.SPAWN_ROW, T.SPAWN_COLS[1]]
        spawn_colored = (c0 != ".") and (c1 != ".") and not v0 and not v1
        spawn_transition = spawn_colored and not prev_spawn_colored

        if state == "SEEK":
            if spawn_transition:
                pill_id += 1
                pill = T.new_pill_state(f, c0, c1, labels)
                state = "ACTIVE"
                record_path(pill_id, f, pill)
            prev_spawn_colored = spawn_colored
            continue

        ceiling_ambiguous = (pill["row"] <= 1) and ({c0, c1} == {pill["colorA"], pill["colorB"]})
        if spawn_transition and not ceiling_ambiguous:
            do_finalize(pill, pill_id, f)
            pill_id += 1
            pill = T.new_pill_state(f, c0, c1, labels)
            record_path(pill_id, f, pill)
            prev_spawn_colored = spawn_colored
            continue

        monocolor = (pill["colorA"] == pill["colorB"])
        row, col, orient = pill["row"], pill["col"], pill["orient"]
        if pill["half_cleared"]:
            found = False
        else:
            nrow, ncol, norient, found = T.search_capsule(
                labels, isvirus, row, col, orient, pill["colorA"], pill["colorB"],
                anchor_labels=pill["anchor_labels"])

        if found:
            pill["consec_lost"] = 0
            if (nrow, ncol, norient) != (row, col, orient):
                pill["last_change_frame"] = f
                pill["anchor_labels"] = labels
                if (nrow > row) and (norient == orient):
                    interval = f - pill["last_row_change_frame"]
                    if interval <= T.SOFT_DROP_MAX_INTERVAL:
                        pill["softdrop_frames"] += interval
                    pill["last_row_change_frame"] = f
                if (ncol != col) and (norient == orient):
                    pill["n_laterals"] += 1
                    if pill["first_input_frame"] is None:
                        pill["first_input_frame"], pill["first_input_kind"] = f, "lateral"
                if norient != orient:
                    pill["n_rotations"] += 1
                    pill["rotation_events"].append(f"{T.rotation_direction(orient, norient, monocolor)}@f{f}")
                    if pill["first_input_frame"] is None:
                        pill["first_input_frame"], pill["first_input_kind"] = f, "rotation"
                pill["row"], pill["col"], pill["orient"] = nrow, ncol, norient
                pill["stable_count"] = 0
            else:
                pill["stable_count"] += 1
        else:
            pill["lost_frames"] += 1
            pill["consec_lost"] += 1
            if not pill["half_cleared"] and pill["consec_lost"] >= T.LOST_FRAMES_FREEZE:
                pill["half_cleared"] = True

        prev_spawn_colored = spawn_colored
        record_path(pill_id, f, pill)

        if pill["stable_count"] >= STALL_FALLBACK_FRAMES:
            do_finalize(pill, pill_id, f)
            state, pill = "SEEK", None

    if state == "ACTIVE" and pill is not None:
        do_finalize(pill, pill_id, n_frames)
    print(f"[{tag}] {len(rows)} pills tracked", file=sys.stderr)
    return rows, paths


def main():
    mid = sys.argv[1]
    window_start_abs = float(sys.argv[2])
    frames_root = os.path.join(FRAMES_60, mid)
    n = len([f for f in os.listdir(frames_root) if f.startswith("f") and f.endswith(".jpg")])
    os.makedirs(EVENTS_ROOT, exist_ok=True)
    rows, paths = track(frames_root, n, window_start_abs, f"p2/{mid}")
    T.write_csv(rows, os.path.join(EVENTS_ROOT, f"p2_{mid}.csv"))
    T.write_paths_jsonl(paths, os.path.join(EVENTS_ROOT, f"p2_{mid}_paths.jsonl"))
    print(f"[p2/{mid}] wrote {len(rows)} pills / {len(paths)} path rows to {EVENTS_ROOT}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
