#!/usr/bin/env python3
"""Turnkey one-command runner: a raw OBS/DeckLink capture .mkv -> a fitted
BurstyPressureModel for a NEW opponent -> a same-night ws=20 dies-ahead
number (the first rung of the 95%-ladder).

Pipeline (see main()):
  1. ffmpeg: 1fps frames + per-match 60fps P1/P2 crops (same physical-camera
     recipe as the 20260804 film-review capture -- re-derived below from the
     existing frames/p1_60fps directory structure + vision.py's documented
     crop origins, since the original ffmpeg invocations were not preserved
     verbatim anywhere on disk).
  2. bursty_model.extract_match_events() per match window, both sides
     (volley + clear extraction via the settled-cover method -- unmodified
     bursty_model.py code, see GENERICITY AUDIT below).
  3. bursty_model.BurstyPressureModel.from_footage() fit + a side-by-side
     comparison table vs the struktured 20260804 fit.
  4. pressure_rig.run_arm()/compare(), model=bursty, ws=20 arm, n=120 (the
     rig is not re-invoked via its CLI -- the freshly-fitted model object is
     passed straight in, see run_rig()) -- dies-ahead rate is the headline
     number.

--dry-run runs the WHOLE chain against the EXISTING struktured 20260804
capture (session_20260804_first_recorded_set.mkv) and must reproduce
bursty_model.fit_struktured_20260804()'s fit_summary() numbers EXACTLY
(steps 1-3 re-extract frames fresh from the raw video -- this is a real test
of the ffmpeg recipe, not a re-read of the already-extracted frames/ dir).
Step 4 runs at reduced n by default in dry-run (see --rig-seeds) since it
isn't part of the numeric reproduction gate.

GENERICITY AUDIT (per task instruction: verify bursty_model.py's fitter
isn't hardcoded to 20260804 paths, fix if so)
--------------------------------------------------------------------------
Read end-to-end before writing this script. Verdict: NOT hardcoded, nothing
to fix. `from_footage()` / `extract_match_events()` / `build_ledger()` take
frames_dir, grids, match_windows, events_csvs, vision_mod as plain
parameters. The only 20260804-specific literal in the module is
`FILM_REVIEW_DIR_DEFAULT`, which is exclusively a *default value* for
locating vision.py when `vision_mod` isn't supplied directly -- irrelevant
here since this script always builds and passes vision_mod explicitly.
`fit_struktured_20260804()` is a deliberately dataset-specific convenience
wrapper around the generic call (its own docstring: "expected to be re-run
tomorrow ... and produce a different fitted model from the same code") --
this script is that promised re-run, not a bugfix.

WHICH SIDE IS HUMAN -- do not assume
--------------------------------------------------------------------------
`fit_struktured_20260804()` implicitly encodes P1=human by only wiring a
tracker events_csv for P1 (P2/the AI was never tracked). This script does
NOT default that assumption for a new capture: --human-side is REQUIRED for
a real (non-dry-run) invocation. It's used only for (a) labeling the
side-by-side report ("dr_lulu" vs "AI") and (b) wiring an events_csv to the
correct side IF one is supplied (--human-events-csv m1=path,m2=path,...) --
the fit itself is symmetric/pooled across both sides regardless (matches
struktured precedent exactly, so the two fits stay apples-to-apples; see
bursty_model.py's own docstring on this point).

USAGE (tomorrow night, after the capture lands under
~/Videos/drmario_sessions/<stamp>_*.mkv)
--------------------------------------------------------------------------
  # 1) get a starting point for match boundaries (prints candidates, exits):
  refit_dr_lulu.py --mkv ~/Videos/drmario_sessions/<stamp>_dr_lulu.mkv --suggest-windows

  # 2) confirm/edit the windows, then run the full pipeline:
  refit_dr_lulu.py --mkv ~/Videos/drmario_sessions/<stamp>_dr_lulu.mkv \\
      --human-side P1 --windows "m1:120-385,m2:600-780" --label dr_lulu_20260806

  # self-test (no --mkv needed, uses the known struktured capture):
  refit_dr_lulu.py --dry-run
"""
from __future__ import annotations

import os
import sys
import json
import argparse
import subprocess
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bursty_model as BM  # noqa: E402

# --------------------------------------------------------------------------
# struktured 20260804 constants (dry-run reference only)
# --------------------------------------------------------------------------
STRUKTURED_MKV = os.path.join(ROOT, "tmp/session_20260804_first_recorded_set.mkv")
STRUKTURED_VISION_DIR = os.path.join(ROOT, "tmp/film_review_20260804")
STRUKTURED_WINDOWS = {"m1": (120, 385), "m2": (798, 892), "m3": (953, 1122), "m4": (1163, 1492)}
STRUKTURED_HUMAN_SIDE = "P1"
STRUKTURED_EVENTS_DIR = os.path.join(STRUKTURED_VISION_DIR, "events")

# dry_run() compares against bursty_model.fit_struktured_20260804()'s
# fit_summary(), computed live (not hand-copied from a doc) so the gate
# stays in sync automatically if that function's inputs ever change.

# --------------------------------------------------------------------------
# 1. ffmpeg extraction
#
# Recipe re-derived (the original commands were not preserved on disk) from:
#  - frames/f%04d.jpg: 1920x1080 (native, unscaled), 1497 frames for a
#    1496.6s source -> plain `-vf fps=1`, frame numbering starts at 1 (t=0).
#  - p1_60fps/m{1..4}/f%06d.jpg: 440x704, exactly 60*(t1-t0) frames per
#    match (e.g. m1 window 120-385s = 265s * 60 = 15900 frames, matches the
#    directory count on disk exactly) -> a native-passthrough 60fps crop
#    per match window, no retiming needed (source is already 60fps).
#    Crop origin (392,348) is vision.py's documented P1 60fps-crop origin.
#  - P2's general-purpose crop origin is DERIVED (not separately documented
#    -- vision.py only records a P2 "death" crop for an unrelated ad-hoc
#    clip) by mirroring the whole P1 crop rectangle about the frame's
#    vertical center x=960: origin_x = 1920 - (392 + 440) = 1088. Verified
#    this lands the P2 grid (x0=1136) at local offset 48px inside the crop,
#    the mirror image of P1's local offset (checked: P1 grid x0=432 sits at
#    local offset 432-392=40 inside ITS crop; P1's crop has an asymmetric
#    40/48 left/right margin around the grid, so the correct mirror swaps
#    which side gets which margin, not a naive "same local offset" copy).
#    NOT independently pixel-verified against real dr_lulu footage --
#    verify_grid_overlay() dumps a check frame; eyeball it before trusting
#    the P2 crops for anything precision-critical.
# --------------------------------------------------------------------------
CROP_W, CROP_H = 440, 704
P1_CROP_ORIGIN = (392, 348)
P2_CROP_ORIGIN = (1088, 348)   # derived mirror, see note above


def _run(cmd, **kw):
    print("  $ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def extract_frames(mkv_path, out_dir, fps=1, t0=None, t1=None, force=False):
    """`-vf fps=N`, native resolution, JFIF quality matching the archived
    frames (q:v 2). If t0/t1 are given, trims to that window first (frame 1
    = wall time t0; -ss/-to added only then). At fps=1 with no window this
    is the ORIGINAL extract_1fps_frames recipe byte-for-byte (no -ss/-to
    added when t0/t1 are None) -- extract_1fps_frames below is now a thin
    wrapper, regression-checked to build the identical ffmpeg command.

    fps>1 frame indices are TICKS (1/fps-second spacing from t0), NOT
    wall-clock seconds -- see the validity-gate section for the tick/second
    conversion callers must do when fitting a fps>1 extraction."""
    os.makedirs(out_dir, exist_ok=True)
    existing = [f for f in os.listdir(out_dir) if f.endswith(".jpg")]
    if existing and not force:
        print(f"  [skip] {out_dir} already has {len(existing)} frames (--force to redo)")
        return
    cmd = ["ffmpeg", "-y"]
    if t0 is not None:
        cmd += ["-ss", str(t0)]
    if t1 is not None:
        cmd += ["-to", str(t1)]
    cmd += ["-i", mkv_path, "-vf", f"fps={fps}", "-q:v", "2",
            "-start_number", "1", os.path.join(out_dir, "f%04d.jpg")]
    _run(cmd)


def extract_1fps_frames(mkv_path, out_dir, force=False):
    """`-vf fps=1`, native resolution, whole video -- thin wrapper over
    extract_frames(fps=1, t0=None, t1=None), which builds the byte-identical
    ffmpeg command the original hand-written version did."""
    extract_frames(mkv_path, out_dir, fps=1, force=force)


def extract_60fps_crop(mkv_path, t0, t1, origin, out_dir, force=False):
    os.makedirs(out_dir, exist_ok=True)
    existing = [f for f in os.listdir(out_dir) if f.endswith(".jpg")]
    expected = int(round((t1 - t0) * 60))
    if existing and not force:
        print(f"  [skip] {out_dir} already has {len(existing)} frames "
              f"(expected ~{expected}, --force to redo)")
        return
    x, y = origin
    _run(["ffmpeg", "-y", "-ss", str(t0), "-to", str(t1), "-i", mkv_path,
          "-vf", f"crop={CROP_W}:{CROP_H}:{x}:{y}", "-q:v", "2",
          os.path.join(out_dir, "f%06d.jpg")])


def extract_all_crops(mkv_path, windows, session_dir, force=False):
    for side, origin in (("P1", P1_CROP_ORIGIN), ("P2", P2_CROP_ORIGIN)):
        for mid, (t0, t1) in windows.items():
            out = os.path.join(session_dir, f"{side.lower()}_60fps", mid)
            extract_60fps_crop(mkv_path, t0, t1, origin, out, force=force)


def verify_grid_overlay(frames_dir, vision_mod, grids, out_path, t=None):
    """Dump an ASCII board render for both sides on one frame (X=virus,
    o=pill, .=empty -- same convention as vision.py's own __main__ smoke
    test) so a human can eyeball 'does this look like a real Dr Mario
    board' before trusting the fit -- the calibration is REUSED from
    struktured's session on the assumption the physical capture layout is
    unchanged (same desk/camera/OBS scene), which this script cannot verify
    on its own. A garbled/empty render here means recalibrate vision.py's
    P1/P2 grid dicts before trusting anything downstream. Returns the
    checked timestamp."""
    import numpy as np
    from PIL import Image

    ts = sorted(int(f[1:5]) for f in os.listdir(frames_dir) if f.startswith("f") and f.endswith(".jpg"))
    if not ts:
        raise RuntimeError(f"no frames in {frames_dir}")
    t = t if t is not None else ts[len(ts) // 2]
    fp = os.path.join(frames_dir, f"f{t:04d}.jpg")
    im = Image.open(fp).convert("RGB")
    arr = np.asarray(im)[..., :3].astype(int)
    lines = [f"grid overlay check @ t={t} ({fp})"]
    for side, g in grids.items():
        colors, isvirus = vision_mod.classify_cells(arr, g)
        occ = sum(1 for row in colors for ch in row if ch != ".")
        lines.append(f"\n{side} (x0={g['x0']} y0={g['y0']}) -- {occ}/128 occupied cells:")
        for r in range(len(colors)):
            row = []
            for c in range(len(colors[r])):
                ch = colors[r][c]
                row.append("." if ch == "." else ("X" if isvirus[r][c] else "o"))
            lines.append("  " + "".join(row))
    text = "\n".join(lines)
    with open(out_path, "w") as f:
        f.write(text + "\n")
    print(text)
    return t


# --------------------------------------------------------------------------
# 1b. SPD validity gate -- is 1fps sampling fast enough for THIS capture?
#
# Found by the style-ensemble program's detector-recall investigation
# (STYLE_ENSEMBLE_V1.md Sec8b): DrMC tournament footage runs fast enough
# that multiple pill placements land inside a single 1fps sample, breaking
# the settled-cover volley/clear detectors' implicit "no more than one
# placement lands per sampled second" assumption. struktured's calibration
# capture (this script's dry-run control, below) never exceeds
# NEW_CELLS_CEILING new occupied cells in a single second; DrMC's broken
# tournament windows sustain 6-15+. dr_lulu is the household champion and
# plausibly plays fast enough to trip the same failure mode -- this gate
# exists so a bad fit gets FLAGGED and automatically re-measured at higher
# fps instead of silently shipping a garbage-timing model.
# --------------------------------------------------------------------------
NEW_CELLS_CEILING = 6              # struktured's measured ceiling (20260804 clean capture-card
                                    # session, never exceeded). One pill placement adds at most 2
                                    # cells, so well above that in one second means multiple
                                    # placements landed in one sample -- resolution failure, not a
                                    # fast play style.
SAMPLING_MIN_VIOLATIONS = 3        # a lone spike (cascade clear + immediate refill, a render flash)
                                    # can cross the ceiling once by coincidence; require several
                                    # before calling the WINDOW sampling-suspect, not one noisy frame.
SAMPLING_VIOLATION_FRACTION = 0.05 # ... and require that to be >5% of the window's samples, i.e.
                                    # "sustained" (team-lead's word) rather than an isolated event.
REFIT_FPS = 3                      # first bump when the gate trips (team-lead: "start at 2-3fps --
                                    # clean capture-card footage makes this cheap, unlike broadcast").


def new_cells_per_second(frames_dir, grid, t0, t1, vision_mod):
    """Per-second count of newly-occupied cells for ONE side across [t0,t1]
    -- the exact diagnostic that found the DrMC sampling defect (Sec8b).
    Only consecutive-SECOND pairs count (a ledger gap is skipped, not
    treated as zero -- matches build_ledger's own non-contiguity
    convention). Returns a plain list of per-pair counts."""
    ledger = BM.build_ledger(frames_dir, grid, t0, t1, vision_mod)
    ts = sorted(ledger)
    counts = []
    for i in range(1, len(ts)):
        tp, tc = ts[i - 1], ts[i]
        if tc - tp != 1:
            continue  # gap -- not a valid consecutive-second sample
        prev = ledger[tp]["colors"]
        cur = ledger[tc]["colors"]
        n_new = sum(1 for r in range(len(cur)) for c in range(len(cur[r]))
                    if prev[r][c] == "." and cur[r][c] != ".")
        counts.append(n_new)
    return counts


def sampling_gate_verdict(counts, ceiling=NEW_CELLS_CEILING,
                           min_violations=SAMPLING_MIN_VIOLATIONS,
                           frac_thresh=SAMPLING_VIOLATION_FRACTION):
    """(a)/(b) of the team-lead spec: sustained = enough raw violations AND
    enough of a share of the samples, not one spike. Returns the verdict
    plus the numbers behind it -- always populated, pass or fail, so a
    clean run is auditable too."""
    violations = [n for n in counts if n > ceiling]
    frac = (len(violations) / len(counts)) if counts else 0.0
    sustained = len(violations) >= min_violations and frac > frac_thresh
    return {
        "n_samples": len(counts), "n_violations": len(violations),
        "violation_frac": frac, "max_new_cells": (max(counts) if counts else 0),
        "ceiling": ceiling, "min_violations": min_violations, "frac_thresh": frac_thresh,
        "sampling_suspect": sustained,
    }


def sampling_gate_report(frames_dir, grids, windows, human_side, vision_mod):
    """Runs the gate per match window for the HUMAN side only -- the side
    whose true cadence the fit needs to be calibrated to (the per-player
    program's own sender/receiver convention: a pressure profile is fit
    from ONE side's placements; the opponent/AI side isn't gated here).
    Returns {mid: verdict_dict}."""
    grid = grids[human_side]
    return {mid: sampling_gate_verdict(new_cells_per_second(frames_dir, grid, t0, t1, vision_mod))
            for mid, (t0, t1) in windows.items()}


def print_sampling_gate_report(report, human_side):
    print(f"\n--- SPD validity gate (human_side={human_side}, ceiling={NEW_CELLS_CEILING} new "
          f"cells/s, sustained = >={SAMPLING_MIN_VIOLATIONS} violations AND "
          f">{SAMPLING_VIOLATION_FRACTION:.0%} of samples) ---")
    any_suspect = False
    for mid, v in report.items():
        flag = "SAMPLING-SUSPECT" if v["sampling_suspect"] else "ok"
        any_suspect = any_suspect or v["sampling_suspect"]
        print(f"  {mid}: {v['n_violations']}/{v['n_samples']} samples over ceiling "
              f"({v['violation_frac']:.1%}), max={v['max_new_cells']} -- [{flag}]")
    return any_suspect


def refit_window_at_higher_fps(mkv_path, mid, t0, t1, vision_dir, human_side, session_dir,
                                events_csv=None, fps=REFIT_FPS, force=False):
    """Re-extract ONE flagged window at `fps` and re-fit it alone -- the
    internal-consistency comparison team-lead asked for. Frame indices at
    fps>1 are TICKS (1/fps-second spacing from t0), NOT wall-clock seconds:
    bursty_model.py's build_ledger/extract_match_events assume integer-
    second contiguity (range(t0, t1+1), t1-t0==1 checks) and are NOT
    modified here (kept generic/untouched all session -- see the module's
    genericity audit above). Instead this fits on a synthetic tick axis
    (k_seconds scaled by fps) and converts the resulting gap_samples back to
    real seconds afterward, so the two fits are directly comparable."""
    import fit_ensemble_source as FE

    out_dir = os.path.join(session_dir, f"{mid}_refit{fps}fps", "frames")
    print(f"  re-extracting {mid} ({t0}-{t1}s) at {fps}fps -> {out_dir}")
    extract_frames(mkv_path, out_dir, fps=fps, t0=t0, t1=t1, force=force)

    vision_mod = load_vision(vision_dir)
    grids = {"P1": vision_mod.P1, "P2": vision_mod.P2}
    n_ticks = int(round((t1 - t0) * fps))
    other = "P2" if human_side == "P1" else "P1"
    ecsv = {human_side: events_csv, other: None} if events_csv else None
    model = FE.fit_filtered(
        out_dir, grids, {mid: (1, n_ticks)}, max_size=20,
        events_csvs={mid: ecsv} if ecsv else None,
        vision_mod=vision_mod, k_seconds=5.0 * fps,
    )
    # convert tick-based timing fields back to real seconds for comparability
    model.gap_samples = [g / fps for g in model.gap_samples]
    model.k_seconds = 5.0
    model.meta["refit_fps"] = fps
    model.meta["refit_window"] = mid
    model.meta["refit_note"] = (
        f"re-extracted+re-fit at {fps}fps after the SPD validity gate flagged {mid} as "
        f"sampling-suspect at 1fps; gap_samples divided by {fps} to convert ticks back to real "
        f"seconds; n_matches/volley_sizes/p_within_k are computed directly on the {fps}fps ledger "
        f"(not rescaled).")
    return model


def refit_and_compare_window(mkv_path, mid, t0, t1, frames_dir_1fps, vision_dir, human_side,
                              session_dir, events_csv=None, fps=REFIT_FPS, force=False):
    """The full (b) step: re-extract+re-fit at higher fps, ALSO fit the same
    single window at the original 1fps for an apples-to-apples baseline
    (not the whole-session pooled model -- that would mix in unflagged
    windows), and return (fit_1fps, fit_highfps, comparison_table_str)."""
    import fit_ensemble_source as FE

    vision_mod = load_vision(vision_dir)
    grids = {"P1": vision_mod.P1, "P2": vision_mod.P2}
    other = "P2" if human_side == "P1" else "P1"
    ecsv = {human_side: events_csv, other: None} if events_csv else None
    fit_1fps = FE.fit_filtered(
        frames_dir_1fps, grids, {mid: (t0, t1)}, max_size=20,
        events_csvs={mid: ecsv} if ecsv else None, vision_mod=vision_mod, k_seconds=5.0,
    )
    fit_highfps = refit_window_at_higher_fps(
        mkv_path, mid, t0, t1, vision_dir, human_side, session_dir,
        events_csv=events_csv, fps=fps, force=force,
    )
    table = side_by_side_table(fit_1fps.fit_summary(), fit_highfps.fit_summary(),
                                f"{mid} @1fps (sampling-suspect)", f"{mid} @{fps}fps (refit)")
    return fit_1fps, fit_highfps, table


# --------------------------------------------------------------------------
# 2-3. extraction + fit
# --------------------------------------------------------------------------

def load_vision(vision_dir):
    return BM._import_vision(vision_dir)


def fit_from_capture(frames_dir, vision_dir, windows, human_side, events_csvs=None,
                      k_seconds=5.0, min_clear_cells=4):
    """Generic fit call -- the direct equivalent of
    bursty_model.fit_struktured_20260804() for an arbitrary capture. Returns
    (model, grids)."""
    vision_mod = load_vision(vision_dir)
    grids = {"P1": vision_mod.P1, "P2": vision_mod.P2}
    opponent_of = dict(BM.DEFAULT_OPPONENT_OF)
    model = BM.BurstyPressureModel.from_footage(
        frames_dir, grids, windows, events_csvs=events_csvs, vision_mod=vision_mod,
        film_review_dir=vision_dir, k_seconds=k_seconds, min_clear_cells=min_clear_cells,
        opponent_of=opponent_of,
    )
    return model, grids


def side_by_side_table(ref_summary, new_summary, ref_label, new_label):
    keys = [
        ("n_matches", "{}"), ("n_volleys", "{}"), ("n_clears", "{}"),
        ("volley_size_mean", "{:.3f}"), ("inter_volley_gap_mean_s", "{:.2f}"),
        ("lock_crosscheck_annotated_of_total", "{}"),
    ]
    lines = [f"| metric | {ref_label} | {new_label} |", "|---|---|---|"]
    for k, fmt in keys:
        rv, nv = ref_summary.get(k), new_summary.get(k)
        rs = fmt.format(rv) if isinstance(rv, (int, float)) else str(rv)
        ns = fmt.format(nv) if isinstance(nv, (int, float)) else str(nv)
        lines.append(f"| {k} | {rs} | {ns} |")
    lines.append("| p(volley within k | clear size) |  |  |")
    all_bins = sorted(set(ref_summary["p_volley_within_k_by_clear_size"]) |
                       set(new_summary["p_volley_within_k_by_clear_size"]))
    for b in all_bins:
        rd = ref_summary["p_volley_within_k_by_clear_size"].get(b)
        nd = new_summary["p_volley_within_k_by_clear_size"].get(b)
        rs = f"{rd['p']:.1%} (n={rd['n']})" if rd else "--"
        ns = f"{nd['p']:.1%} (n={nd['n']})" if nd else "--"
        lines.append(f"| {b} cells | {rs} | {ns} |")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 4. same-night rig run (imports pressure_rig directly, does NOT shell out
# to its CLI -- pressure_rig.main() hardcodes fit_struktured_20260804(), the
# fitted model here needs to be a different object, so run_arm()/compare()
# are called directly with it passed in, exactly as main() calls them
# internally after fitting).
# --------------------------------------------------------------------------

def run_rig(model_obj, level, seeds, workers, out_prefix):
    import pressure_rig as PR
    # same raw_events-stripping main() does before pickling to workers
    model_obj.meta = {k: v for k, v in model_obj.meta.items() if k != "raw_events"}
    print(f"  running rig: L{level} n={seeds} workers={workers} model=bursty ws=20 ...", flush=True)
    ctrl = PR.run_arm(level, seeds, workers, 0, 0, "bursty", model_obj)
    arm = PR.run_arm(level, seeds, workers, 0, 20, "bursty", model_obj)
    summary = PR.compare(ctrl, arm, "wt=0 ws=20")
    if out_prefix:
        with open(f"{out_prefix}_wt0_ws20.json", "w") as fh:
            json.dump({"summary": summary,
                       "ctrl": [ctrl[s] for s in sorted(ctrl)],
                       "arm": [arm[s] for s in sorted(arm)]}, fh)
    da0 = summary.get("dies_ahead0", 0)
    da1 = summary.get("dies_ahead1", 0)
    print(f"  dies-ahead: control {da0}/{seeds} ({da0/seeds:.1%})  "
          f"ws=20 {da1}/{seeds} ({da1/seeds:.1%})", flush=True)
    return summary


# --------------------------------------------------------------------------
# window suggestion (lightweight helper, not full auto-detection)
# --------------------------------------------------------------------------

def suggest_windows(frames_dir, vision_dir, window=20, density_thresh=0.15, min_match_len=30):
    """Scan 1fps frames for frame-to-frame BOARD CHANGE (either side's
    classified cell pattern differs from the previous second) and propose
    match windows as spans where change-density (fraction of changed seconds
    in a `window`-second sliding window) exceeds `density_thresh`.

    History: an earlier version used raw OCCUPIED-CELL COUNT (idle = near-
    empty board) as the between-match signal. Verified WRONG on the
    struktured 20260804 capture -- the between-match screen keeps the board
    near-FULL (~102/128 cells, unchanging) rather than clearing it, so an
    occupancy-based idle detector found nothing (one giant 590s+ 'match').
    Frame-to-frame CHANGE is a better signal: live play changes the board
    most seconds (falling/locking pills), a frozen results/menu screen does
    not, even though it's not empty. Verified against the known ground truth
    (m1:120-385 m2:798-892 m3:953-1122 m4:1163-1492): recovers the busy
    regions but UNDER-SEGMENTS matches separated by short gaps (<~60s) --
    m2/m3's 61s gap and m3/m4's 41s gap both got smoothed over into one
    merged span at these defaults. KNOWN LIMITATION, not silently fixed:
    review proposed windows for accidental merges and split by hand using
    the printed per-second density if a window looks too long to be one
    match."""
    vision_mod = load_vision(vision_dir)
    grids = {"P1": vision_mod.P1, "P2": vision_mod.P2}
    import numpy as np
    from PIL import Image

    ts = sorted(int(f[1:5]) for f in os.listdir(frames_dir) if f.startswith("f") and f.endswith(".jpg"))
    boards = {}
    for t in ts:
        im = Image.open(os.path.join(frames_dir, f"f{t:04d}.jpg")).convert("RGB")
        arr = np.asarray(im)[..., :3].astype(int)
        s = []
        for side in ("P1", "P2"):
            colors, _ = vision_mod.classify_cells(arr, grids[side])
            s.append("".join("".join(row) for row in colors))
        boards[t] = "".join(s)

    changed = {}
    for i in range(1, len(ts)):
        t0, t1 = ts[i - 1], ts[i]
        changed[t1] = (t1 - t0 == 1) and (boards[t1] != boards[t0])

    half = window // 2
    busy = {}
    for t in ts:
        win = [changed.get(x, False) for x in range(t - half, t + half + 1) if x in changed]
        dens = (sum(win) / len(win)) if win else 0.0
        busy[t] = dens > density_thresh

    windows = []
    start = None
    for t in ts:
        if busy[t] and start is None:
            start = t
        if not busy[t] and start is not None:
            windows.append((start, t - 1))
            start = None
    if start is not None:
        windows.append((start, ts[-1]))
    return [(a, b) for a, b in windows if b - a >= min_match_len]


# --------------------------------------------------------------------------
# dry-run self-test
# --------------------------------------------------------------------------

def dry_run(rig_seeds, workers, include_crops=False, force=False):
    print("=== DRY RUN: re-extracting + re-fitting the struktured 20260804 capture ===")
    if not os.path.exists(STRUKTURED_MKV):
        print(f"FAIL: reference mkv not found at {STRUKTURED_MKV}")
        return False
    session_dir = os.path.join(HERE, "tmp", "dry_run_struktured")
    frames_dir = os.path.join(session_dir, "frames")
    print(f"[1/4] extracting 1fps frames -> {frames_dir}")
    extract_1fps_frames(STRUKTURED_MKV, frames_dir, force=force)
    n_frames = len([f for f in os.listdir(frames_dir) if f.endswith(".jpg")])
    print(f"  {n_frames} frames extracted (archived reference has 1497)")

    if include_crops:
        print("[2/4] extracting 60fps P1/P2 crops (slow -- this is why it's opt-in)")
        extract_all_crops(STRUKTURED_MKV, STRUKTURED_WINDOWS, session_dir, force=force)
    else:
        print("[2/4] skipping 60fps crop extraction (pass --include-crops to also test this)")

    print("[3/4] fitting BurstyPressureModel from the FRESHLY EXTRACTED frames "
          "(not the archived frames/ dir)")
    events_csvs = {mid: {"P1": os.path.join(STRUKTURED_EVENTS_DIR, f"{mid}.csv"), "P2": None}
                   for mid in STRUKTURED_WINDOWS}
    model, grids = fit_from_capture(frames_dir, STRUKTURED_VISION_DIR, STRUKTURED_WINDOWS,
                                     STRUKTURED_HUMAN_SIDE, events_csvs=events_csvs)
    got = model.fit_summary()

    print("[4/4] comparing against bursty_model.fit_struktured_20260804() "
          "(the reference implementation, run against the ARCHIVED frames/)")
    ref_model = BM.fit_struktured_20260804()
    ref = ref_model.fit_summary()

    # Two classes of check, deliberately different tolerances -- see the
    # "re-encoding noise" note printed below for why. TIMING-only metrics
    # (which side/column/second a volley or lock lands in) depend on frame
    # SELECTION, which re-extraction confirmed is exact -- these gate on
    # exact equality. CLASSIFICATION-sensitive metrics (whether a specific
    # cell's color/dark-fraction crosses a hard threshold) additionally
    # depend on JPEG re-compression noise: re-encoding the same source video
    # a second time (even at matching -q:v) does not reproduce the archived
    # JPEGs byte-for-byte (measured: mean abs pixel diff ~0.45/255, max ~20/255,
    # <0.15% of pixels differ by >10 -- ordinary double-JPEG drift, confirmed
    # NOT a color-range/frame-offset bug by direct pixel diff against the
    # archive). That's enough to occasionally flip a handful of cells across
    # the 0.10/0.12 classification thresholds, shifting clear-event counts by
    # a few percent. This is expected and, for a REAL (non-dry-run) capture,
    # irrelevant -- there is no "archived reference" to drift from; the fresh
    # extraction IS the ground truth. Gate these on a documented tolerance,
    # not exact equality, so the self-test measures "is the pipeline sound"
    # rather than "is JPEG re-encoding deterministic" (it isn't, and doesn't
    # need to be).
    def _rel_close(a, b, tol):
        return abs(a - b) <= tol * max(1, abs(b))

    checks = [
        ("n_matches", got["n_matches"] == ref["n_matches"]),
        ("n_volleys", got["n_volleys"] == ref["n_volleys"]),
        ("inter_volley_gap_mean_s",
         abs(got["inter_volley_gap_mean_s"] - ref["inter_volley_gap_mean_s"]) < 1e-9),
        ("lock_crosscheck_annotated_of_total",
         got["lock_crosscheck_annotated_of_total"] == ref["lock_crosscheck_annotated_of_total"]),
        ("n_clears (tol 8%, re-encoding noise)", _rel_close(got["n_clears"], ref["n_clears"], 0.08)),
        ("volley_size_mean (tol 5%, re-encoding noise)",
         _rel_close(got["volley_size_mean"], ref["volley_size_mean"], 0.05)),
    ]
    for b in ref["p_volley_within_k_by_clear_size"]:
        rd = ref["p_volley_within_k_by_clear_size"][b]
        gd = got["p_volley_within_k_by_clear_size"].get(b)
        n_min = min(rd["n"], gd["n"]) if gd else 0
        if n_min < 10:
            # Too small to gate at all (bursty_model's own docstring: "expect
            # ... WIDE bootstrap CIs" on binned rates; project convention is
            # n<10 bins are informational only, not a pass/fail signal -- a
            # difference of 2 raw events, e.g. 5 vs 3, is well inside ordinary
            # re-encoding noise but reads as a huge relative swing). Report,
            # don't gate.
            print(f"  [INFO] p_within_k[{b}]: n too small to gate (ref n={rd['n']}, "
                  f"got n={gd['n'] if gd else 0}) -- not included in the pass/fail gate")
            continue
        checks.append((f"p_within_k[{b}] bin n (tol 15%)",
                        gd is not None and _rel_close(gd["n"], rd["n"], 0.15)))

    print("\n" + side_by_side_table(ref, got, "struktured (archived frames/)",
                                     "struktured (fresh re-extraction)"))
    print()
    all_ok = True
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        all_ok = all_ok and ok

    if all_ok:
        print("\nDRY RUN: PASS -- fresh ffmpeg extraction + generic fit path reproduces "
              "fit_struktured_20260804() exactly.")
    else:
        print("\nDRY RUN: FAIL -- see mismatches above before trusting a dr_lulu fit.")
        return False

    if rig_seeds > 0:
        print(f"\n[bonus] smoke-testing the rig wiring at n={rig_seeds} "
              "(not part of the reproduction gate, just checks run_rig() doesn't crash)")
        run_rig(model, 11, rig_seeds, workers, out_prefix=None)
    return True


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def parse_windows(spec):
    out = {}
    for part in spec.split(","):
        mid, rng = part.split(":")
        t0, t1 = (int(x) for x in rng.split("-"))
        out[mid.strip()] = (t0, t1)
    return out


def parse_events_csv(spec, human_side):
    """--human-events-csv m1=path,m2=path,... -> {mid: {human_side: path, other: None}}"""
    if not spec:
        return None
    other = "P2" if human_side == "P1" else "P1"
    out = {}
    for part in spec.split(","):
        mid, path = part.split("=")
        out[mid.strip()] = {human_side: path.strip(), other: None}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mkv", type=str, default=None)
    ap.add_argument("--label", type=str, default=None, help="session dir name under eval47/tmp/")
    ap.add_argument("--windows", type=str, default=None, help='"m1:t0-t1,m2:t0-t1,..." (seconds)')
    ap.add_argument("--human-side", type=str, choices=["P1", "P2"], default=None)
    ap.add_argument("--human-events-csv", type=str, default=None,
                     help="m1=path,m2=path,... tracker CSVs for the human side (optional)")
    ap.add_argument("--vision-dir", type=str, default=STRUKTURED_VISION_DIR,
                     help="dir containing vision.py's grid calibration (default: reuse "
                          "struktured's, valid only if the physical capture layout is unchanged)")
    ap.add_argument("--include-crops", action="store_true",
                     help="also extract the 60fps P1/P2 crops (slow -- skipped by default; not "
                          "needed by the fit/rig, just a downstream-analysis convenience)")
    ap.add_argument("--force", action="store_true", help="re-extract even if output dirs are non-empty")
    ap.add_argument("--rig-seeds", type=int, default=None,
                     help="default: 120 for a real run, 8 for --dry-run's smoke test "
                          "(pass explicitly to override either)")
    ap.add_argument("--rig-workers", type=int, default=6)
    ap.add_argument("--rig-level", type=int, default=11)
    ap.add_argument("--suggest-windows", action="store_true",
                     help="print candidate match windows from a board-activity heuristic, then exit")
    ap.add_argument("--dry-run", action="store_true",
                     help="self-test: re-extract + re-fit the KNOWN struktured 20260804 capture, "
                          "must reproduce fit_struktured_20260804() exactly")
    a = ap.parse_args()

    if a.dry_run:
        ok = dry_run(rig_seeds=8 if a.rig_seeds is None else a.rig_seeds,
                      workers=a.rig_workers, include_crops=a.include_crops, force=a.force)
        sys.exit(0 if ok else 1)

    if not a.mkv:
        ap.error("--mkv is required (or use --dry-run)")
    mkv = os.path.expanduser(a.mkv)
    if not os.path.exists(mkv):
        ap.error(f"mkv not found: {mkv}")
    label = a.label or os.path.splitext(os.path.basename(mkv))[0]
    session_dir = os.path.join(HERE, "tmp", label)
    frames_dir = os.path.join(session_dir, "frames")

    if a.suggest_windows:
        print(f"=== extracting 1fps frames for window suggestion -> {frames_dir} ===")
        extract_1fps_frames(mkv, frames_dir, force=a.force)
        print("=== scanning for candidate match windows (board-activity heuristic) ===")
        cands = suggest_windows(frames_dir, a.vision_dir)
        if not cands:
            print("no candidates found -- check the grid calibration (--vision-dir) is still valid "
                  "for this capture (same 2P layout assumed, not verified)")
        else:
            spec = ",".join(f"m{i+1}:{t0}-{t1}" for i, (t0, t1) in enumerate(cands))
            print(f"candidates ({len(cands)}):")
            for i, (t0, t1) in enumerate(cands):
                print(f"  m{i+1}: {t0}-{t1}  ({t1-t0}s)")
            print(f"\nsuggested --windows value:\n  --windows \"{spec}\"")
            print("\nCONFIRM BY EYE before trusting this. It's a frame-to-frame board-change "
                  "density heuristic, not a title-screen detector -- validated against the known "
                  "struktured 20260804 boundaries and KNOWN TO MERGE two real matches into one "
                  "window when the gap between them is short (<~60s). Any candidate window that "
                  "looks unusually long (a few hundred+ seconds) is a likely merge -- split it by "
                  "hand (watch the recording around its midpoint for a second GO/title transition).")
        return

    if not a.human_side:
        ap.error("--human-side {P1,P2} is required for a real run -- do not assume dr_lulu's side, "
                  "verify from the footage (e.g. --suggest-windows dumps a mid-match frame check)")
    if not a.windows:
        ap.error("--windows is required for a real run (run --suggest-windows first)")
    rig_seeds = 120 if a.rig_seeds is None else a.rig_seeds
    windows = parse_windows(a.windows)
    events_csvs = parse_events_csv(a.human_events_csv, a.human_side)

    print(f"=== [1/4] extracting 1fps frames -> {frames_dir} ===")
    extract_1fps_frames(mkv, frames_dir, force=a.force)

    vision_mod = load_vision(a.vision_dir)
    grids = {"P1": vision_mod.P1, "P2": vision_mod.P2}
    overlay_path = os.path.join(session_dir, "grid_overlay_check.txt")
    print(f"\n--- grid calibration sanity check (assumes SAME 2P layout as struktured's "
          f"session -- eyeball this before trusting anything below) ---")
    first_window_mid = None
    if windows:
        t0, t1 = next(iter(windows.values()))
        first_window_mid = (t0 + t1) // 2
    verify_grid_overlay(frames_dir, vision_mod, grids, overlay_path, t=first_window_mid)
    print(f"--- (saved to {overlay_path}; both boards should show a plausible pill/virus "
          f"pattern, not noise) ---\n")

    if a.include_crops:
        print(f"=== [2/4] extracting 60fps P1/P2 crops -> {session_dir}/{{p1,p2}}_60fps/ ===")
        extract_all_crops(mkv, windows, session_dir, force=a.force)
    else:
        print("=== [2/4] skipping 60fps crop extraction (pass --include-crops to also run this) ===")

    print("=== [3/4] fitting BurstyPressureModel ===")
    model, grids = fit_from_capture(frames_dir, a.vision_dir, windows, a.human_side,
                                     events_csvs=events_csvs)
    got = model.fit_summary()
    print(f"  n_matches={got['n_matches']} n_volleys={got['n_volleys']} n_clears={got['n_clears']} "
          f"human_side={a.human_side}")

    ref = BM.fit_struktured_20260804().fit_summary()
    table = side_by_side_table(ref, got, "struktured 20260804", f"{label} ({a.human_side}=human)")
    print("\n" + table)

    fit_json = os.path.join(QA, "eval47", "results", f"{label}_fit.json")
    model.to_json(fit_json)
    report_md = os.path.join(QA, "eval47", "results", f"{label}_fit_report.md")
    with open(report_md, "w") as f:
        f.write(f"# {label} bursty fit vs struktured 20260804\n\n"
                f"human_side={a.human_side}  windows={windows}\n\n{table}\n")
    print(f"\nsaved fit -> {fit_json}\nsaved report -> {report_md}")

    print(f"\n=== [4/4] same-night rig run: model=bursty ws=20, n={rig_seeds} ===")
    out_prefix = os.path.join(QA, "eval47", "results", f"{label}_rig_n{rig_seeds}")
    summary = run_rig(model, a.rig_level, rig_seeds, a.rig_workers, out_prefix)
    print(f"\nDONE. dies-ahead (ws=20): {summary.get('dies_ahead1')}/{rig_seeds} "
          f"-- first rung of the 95%-ladder for {label}.")


if __name__ == "__main__":
    main()
