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
# h_hit == -1 means "no column targeted" (game.garbage_hit_h, #124) -- unreachable once
# a volley has fired, so these cases pin DEFENSIVE behaviour rather than a live path.
# The old code turned -1 into 264 + 16 = 280 f, longer than the physical maximum, and
# scored it as if measured. It must refuse instead.
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
    [270 * F, 4, 6, 1, -1],   # no column targeted: 270 f slips under a bogus 280 f
    [270 * F, 4, 6, 1, -1],   # ... twice, so the counter has to count, not just flag
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

# --- by_h_hit: the #92 headline table, keyed on h_hit and NOT on max_h -------------
# Hand-built so the two variables DISAGREE: every decision below sits at max_h=3 (band
# "0-4") while carrying h_hit 12 or 13. A by_h_hit that silently keyed on max_h -- the
# variable the bands use, and the one #124 proved people conflate -- would collapse all
# five rows into one entry and cannot pass this.
LAT2 = [
    [10 * F, 4, 3, 1, 12],    # W = 264-192 = 72 -> on time
    [80 * F, 4, 3, 1, 12],    # W = 72 -> LATE (80 > 72)
    [50 * F, 4, 3, 1, 13],    # W = 264-208 = 56 -> on time (50 < 56)
    [60 * F, 4, 3, 1, 13],    # W = 56 -> LATE
    [70 * F, 4, 3, 1, 13],    # W = 56 -> LATE; median of {50,60,70} = 60
    # h_hit 11 (W = 264-176 = 88) is deliberately SKEWED so median != mean: median of
    # {10, 20, 300} is 20 while the mean is 110. Without an asymmetric cell a
    # mean-for-median mutant is unkillable -- {50,60,70} and {10,80} both agree.
    [10 * F, 4, 3, 1, 11],
    [20 * F, 4, 3, 1, 11],
    [300 * F, 4, 3, 1, 11],   # W = 88 -> LATE
    # h_hit 2 (W = 232) with a DEEP entry_row 15 (fall budget 13*15 = 195). 210 frames
    # busts the fall budget but fits the window, so the two budgets disagree on this
    # one decision. Without it, every cell above happens to be scored the same way by
    # either budget and a "table uses the fall budget" mutant is unkillable.
    [210 * F, 15, 3, 1, 2],
]
rep2 = M.analyze([{"seed": 8, "lat": LAT2}])
bh = rep2["by_h_hit"]
check("by_h_hit keys are the h_hit values 2, 11, 12, 13, not the max_h 3",
      sorted(bh, key=int) == ["2", "11", "12", "13"])
check("by_h_hit['2'] scores against the WINDOW (232 f), not the fall budget (195 f)",
      bh["2"]["n"] == 1 and bh["2"]["late"]["silicon"] == 0
      and bh["2"]["window_frames"] == 232)
check("by_h_hit['11'] median == 20.0, NOT the mean 110.0",
      bh["11"]["median_frames_silicon"] == 20.0)
check("by_h_hit['11'] n=3 late_si=1 W=88",
      bh["11"]["n"] == 3 and bh["11"]["late"]["silicon"] == 1
      and bh["11"]["window_frames"] == 88)
check("by_h_hit['12'] n=2 late_si=1 W=72",
      bh["12"]["n"] == 2 and bh["12"]["late"]["silicon"] == 1
      and bh["12"]["window_frames"] == 72)
check("by_h_hit['13'] n=3 late_si=2 W=56 (50 f fits, 60 and 70 do not)",
      bh["13"]["n"] == 3 and bh["13"]["late"]["silicon"] == 2
      and bh["13"]["window_frames"] == 56)
check("by_h_hit['13'] median silicon frames == 60.0",
      bh["13"]["median_frames_silicon"] == 60.0)
check("by_h_hit['12'] median silicon frames == 45.0 (even case averages 10 and 80)",
      bh["12"]["median_frames_silicon"] == 45.0)
# sim-lockstep is 1.5714x cheaper, so the SAME clocks must be late less often. 80 f
# silicon = 50.91 f sim, which fits the 72 f window: the domain split has to survive
# into this table too, or a silicon-only claim could be quoted from a sim number.
check("by_h_hit['12'] late_sim == 0 (same decision, other domain, fits)",
      bh["12"]["late"]["sim_lockstep"] == 0)
# Unscorable releases must not appear as an h_hit entry at all (they have no window).
check("by_h_hit has no entry for the -1 releases in the first fixture",
      "-1" not in rep["by_h_hit"])
check("by_h_hit n sums to n_window_scored (nothing dropped, nothing double-counted)",
      sum(e["n"] for e in bh.values()) == rep2["silicon"]["n_window_scored"])

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
