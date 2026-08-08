#!/usr/bin/env python3
"""Selftest for av_verdict.py's PRE-REGISTERED routing.

House rule: test the DEFECT, not the fix.  A verdict script that only ever sees
one real table has never been shown to DISCRIMINATE -- so here it is driven with
SYNTHETIC tables (clearly fabricated, never written to results/) constructed to
sit on each side of every threshold, and the routing it returns is asserted.

Exit codes under test: 0 = PASS, 1 = REFUTED, 3 = ROUTE_A_H.

Run:  test_av_verdict.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import av_verdict


def arm(tag, da_pts, be_pts, disc, n=300, base_da=30, base_be=60):
    """One synthetic summary row shaped exactly like av_rig.summarise()'s output."""
    da1 = round(base_da - da_pts * n / 100.0)
    be1 = round(base_be - be_pts * n / 100.0)
    return {"tag": tag, "n": n,
            "dies_ahead0": base_da, "dies_ahead1": da1,
            "dies_ahead_rate0": base_da / n, "dies_ahead_rate1": da1 / n,
            "dies_ahead_delta_pts": da_pts,
            "da_discordant_b": disc // 2, "da_discordant_c": disc - disc // 2,
            "da_discordant_n": disc, "da_p": 0.05,
            "bad_ends0": base_be, "bad_ends1": be1,
            "bad_rate0": base_be / n, "bad_rate1": be1 / n,
            "bad_delta_pts": be_pts,
            "be_discordant_b": disc // 2, "be_discordant_c": disc - disc // 2,
            "be_discordant_n": disc, "be_p": 0.05,
            "clear0": 0.80, "clear1": 0.80 + da_pts / 100.0,
            "pills_delta": 0.0, "pills_ci": [-1.0, 1.0], "pills_n": 200,
            "garbage0": 50.0, "garbage1": 50.0, "kernel_hash": "SYNTHETIC"}


def table(av_rows, ctrl_rows):
    return {"kernel_hash": "SYNTHETIC-NOT-A-REAL-RESULT", "n": 300, "level": 11,
            "wt": 0, "ws": 20, "control_weight": [6.004, 12.009, 18.013],
            "baseline": {"n": 300, "dies_ahead": 30, "bad_ends": 60},
            "arms": av_rows + ctrl_rows, "raw": {}}


def run(d):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(d, fh)
        path = fh.name
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = av_verdict.main(path)
        return code, buf.getvalue()
    finally:
        os.unlink(path)


CASES = []


def case(name, expect, av_rows, ctrl_rows):
    CASES.append((name, expect, av_rows, ctrl_rows))


# 1. Everything clears: big DA, big BE, plenty of discordant pairs, control flat.
case("clean PASS", 0,
     [arm("A_v w_rdyext=24", 4.0, 5.0, 80)],
     [arm("SCALE-CTRL (no reach) w=18.013", 0.3, 0.4, 70)])

# 2. DA clears but BE misses by a hair -> not a pass.  Directional, healthy
#    discordant count, beats its own control => ROUTE, never a softened pass.
case("BE just under bar -> ROUTE", 3,
     [arm("A_v w_rdyext=24", 4.0, 2.9, 80)],
     [arm("SCALE-CTRL (no reach) w=18.013", 0.3, 0.4, 70)])

# 3. THE INADMISSIBLE-AMENDMENT CASE: a gain about a quarter of the bar -- exactly
#    what "scale the bar to the 24.9% lever" would have waved through.  Must NOT
#    return PASS.
case("quarter-size gain must not PASS", 3,
     [arm("A_v w_rdyext=24", 1.0, 1.2, 75)],
     [arm("SCALE-CTRL (no reach) w=18.013", 0.2, 0.1, 70)])

# 4. Directional and over the bar, but the SCALAR reproduces it -> the shape is
#    not carrying it.  Must be REFUTED, not routed.
case("control reproduces -> REFUTED", 1,
     [arm("A_v w_rdyext=24", 4.0, 5.0, 80)],
     [arm("SCALE-CTRL (no reach) w=18.013", 4.2, 5.1, 78)])

# 5. Directional and beats its control, but discordant counts too thin.
case("underpowered -> REFUTED", 1,
     [arm("A_v w_rdyext=24", 1.5, 1.0, 41)],
     [arm("SCALE-CTRL (no reach) w=18.013", 0.1, 0.1, 40)])

# 6. Wrong direction entirely.
case("negative -> REFUTED", 1,
     [arm("A_v w_rdyext=24", -2.0, -1.0, 80)],
     [arm("SCALE-CTRL (no reach) w=18.013", -0.1, 0.0, 70)])

# 7. Per-dose matching: the best A_v is w=8, whose OWN control is w=6.004.  A
#    different dose's control (w=18.013) looking bad must not rescue it -- the
#    comparison has to be dose-matched.
case("dose-matched control, not any control", 1,
     [arm("A_v w_rdyext=8", 1.5, 1.0, 80),
      arm("A_v w_rdyext=24", 0.5, 0.3, 80)],
     [arm("SCALE-CTRL (no reach) w=6.004", 2.0, 1.5, 75),
      arm("SCALE-CTRL (no reach) w=18.013", -3.0, -2.0, 75)])


def main():
    fails = []
    for name, expect, av_rows, ctrl_rows in CASES:
        code, out = run(table(av_rows, ctrl_rows))
        verdict = ("PASS" if code == 0 else "ROUTE_A_H" if code == 3 else
                   "REFUTED" if code == 1 else f"?{code}")
        want = ("PASS" if expect == 0 else "ROUTE_A_H" if expect == 3 else "REFUTED")
        ok = code == expect
        if not ok:
            fails.append(f"{name}: got {verdict}, want {want}\n{out}")
        print(f"  {'ok  ' if ok else 'FAIL'}  {name:<38s} -> {verdict:>9s} "
              f"(want {want})")
    print()
    if fails:
        print(f"SELFTEST FAILED -- {len(fails)} case(s):")
        for f in fails:
            print(f)
        return 1
    print(f"SELFTEST PASSED: {len(CASES)} synthetic tables, routing correct on every "
          f"side of every threshold (including the quarter-size-gain case the "
          f"inadmissible amendment would have passed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
