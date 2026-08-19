#!/usr/bin/env python3
"""Conversion gate for analyze_shadowlat.py's clock-domain constants.

Hand-computed cases, per the house gate standard (a check must be shown to FAIL on
wrong inputs): the driver in tmp/shadowlat_gate runs this same file against
wrong-constant mutants of analyze_shadowlat.py and requires a non-zero exit.

The module under test is loaded from $LAT_MODULE if set (that is how the mutant
copies are pointed at), else from analyze_shadowlat.py next to this file.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.environ.get("LAT_MODULE", os.path.join(HERE, "analyze_shadowlat.py"))
spec = importlib.util.spec_from_file_location("lat_under_test", MOD_PATH)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

failures = []


def check(name, cond):
    if cond:
        print(f"  ok  {name}")
    else:
        failures.append(name)
        print(f"FAIL  {name}")


print(f"module under test: {MOD_PATH}")

# --- exact hand-computed unit cases --------------------------------------------
# 909,650 clocks is EXACTLY one silicon-domain frame (54.669 MHz async copro tap,
# NTSC 60.0988 fps).
check("909650 clocks == 1.0 silicon frame exactly",
      M.silicon_frames(909650) == 1.0)
# 48 master clocks per NES CPU cycle * 29,780.5 CPU cycles per NTSC frame.
check("1429464 clocks == 1.0 sim-lockstep frame exactly",
      M.sim_frames(48 * 29780.5) == 1.0)
check("sim-lockstep constant is exactly 48*29780.5 = 1,429,464",
      M.SIM_CLOCKS_PER_FRAME == 1429464.0)
# The pinned silicon constant must actually derive from 54.669e6/60.0988
# (= 909,652.1; the pin rounds to 909,650 -- tolerance 5 clocks, i.e. ~5.5e-6 frames).
check("silicon constant within 5 clocks of 54.669e6/60.0988",
      abs(M.SILICON_CLOCKS_PER_FRAME - 54.669e6 / 60.0988) < 5)
# Domain gap: silicon sees ~1.5714x fewer frames for the same clocks.
check("domain ratio sim/silicon == 1.5714 (4dp)",
      round(M.SIM_CLOCKS_PER_FRAME / M.SILICON_CLOCKS_PER_FRAME, 4) == 1.5714)
# Observed worst case ~33e6 clocks: 36.278 silicon frames, 23.086 sim frames.
check("33e6 clocks -> 36.278 silicon frames (3dp)",
      round(M.silicon_frames(33e6), 3) == 36.278)
check("33e6 clocks -> 23.086 sim-lockstep frames (3dp)",
      round(M.sim_frames(33e6), 3) == 23.086)

# --- budget arithmetic ----------------------------------------------------------
# L11 fall: 13 f/row from spawn row 0. Entry row 4 -> 52 frames; row 0 -> 0.
check("fall budget entry_row=4 == 52 frames", M.fall_budget_frames(4) == 52)
check("fall budget entry_row=0 == 0 frames", M.fall_budget_frames(0) == 0)
check("fall budget entry_row=15 == 195 frames", M.fall_budget_frames(15) == 195)
# Garbage window 264 - 16h (measured 8/8 exact): h=0 -> 264, h=6 -> 168, h=15 -> 24.
check("garbage window h=0 == 264", M.garbage_window_frames(0) == 264)
check("garbage window h=6 == 168", M.garbage_window_frames(6) == 168)
check("garbage window h=15 == 24", M.garbage_window_frames(15) == 24)
# h_hit == -1 means "hit set unknown" (game.garbage_hit_h, #124). The old code turned
# that into 264 + 16 = 280 f -- longer than the physical maximum -- and scored it as if
# measured. It must refuse instead.
try:
    got = M.garbage_window_frames(-1)
    check(f"garbage window h=-1 refuses (got {got})", False)
except ValueError:
    check("garbage window h=-1 raises ValueError", True)
except Exception as e:                                    # any non-ValueError is a fail
    check(f"garbage window h=-1 raises ValueError (got {type(e).__name__})", False)

# --- analyze(): -1 releases are skipped, counted, and stay in the denominator -----
# Six decisions on one game. clocks are chosen in the SILICON domain: 909,650 clocks
# = 1.000 frame exactly, so N frames = N * 909650.
F = 909650
# [clocks, entry_row, max_h, post_garbage, h_hit]
LAT = [
    [10 * F, 4, 3, 0, -1],    # not post_garbage: h_hit ignored entirely
    [10 * F, 4, 3, 1, 0],     # window 264 -> on time
    [300 * F, 4, 3, 1, 0],    # window 264 -> LATE (300 > 264)
    [270 * F, 4, 6, 1, -1],   # unknown hit set: 270 f would be "late" vs a bogus 280
    [270 * F, 4, 6, 1, -1],   # ... second one, so the counter has to count, not flag
    [10 * F, 4, 6, 1, 15],    # window 24 -> on time (10 < 24)
]
rep = M.analyze([{"seed": 7, "lat": LAT}])
check("n_post_garbage == 5 (the -1 releases stay in the release denominator)",
      rep["n_post_garbage"] == 5)
check("n_window_unscorable == 2", rep["n_window_unscorable"] == 2)
check("n_window_scored == 3 per domain (5 releases - 2 unscorable)",
      rep["silicon"]["n_window_scored"] == 3
      and rep["sim_lockstep"]["n_window_scored"] == 3)
check("late_vs_window == 1 silicon (only the 300 f decision)",
      rep["silicon"]["late_vs_window"] == 1)
check("band 0-4 carries 2 releases, 0 unscorable",
      rep["bands"]["0-4"]["n_post_garbage"] == 2
      and rep["bands"]["0-4"]["n_window_unscorable"] == 0)
check("band 5-8 carries 3 releases, 2 unscorable",
      rep["bands"]["5-8"]["n_post_garbage"] == 3
      and rep["bands"]["5-8"]["n_window_unscorable"] == 2)
# The whole point: had the -1 rows been scored against 280 f, both would have been
# on time (270 < 280) and late_vs_window_pct would be 1/5 = 20.0 rather than 1/3.
check("late_vs_window_pct == 33.333 (denominator excludes the unscorable)",
      rep["silicon"]["late_vs_window_pct"] == 33.333)

# --- height bands ---------------------------------------------------------------
check("band(0)=0-4 band(4)=0-4 band(5)=5-8 band(8)=5-8 band(9)=9-12 "
      "band(12)=9-12 band(13)=13+ band(16)=13+",
      [M.band_of(h) for h in (0, 4, 5, 8, 9, 12, 13, 16)]
      == ["0-4", "0-4", "5-8", "5-8", "9-12", "9-12", "13+", "13+"])

if failures:
    print(f"\n{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("\nall conversion checks pass")
sys.exit(0)
