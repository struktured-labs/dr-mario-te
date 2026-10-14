#!/usr/bin/env python3
"""pocketclk lane: run a STEER14 arm (dr-mario-h16-wt experiments/cvx/steer14_run.py, read-only, b18a251e) with the
ARM's copro slowed from MiSTer's 85.909 MHz to the Pocket's 54.669 MHz. Today's-cart reference (fw 1488) is untouched,
so the race tempo is priced against the same reference as the banked MiSTer rows (paired by seed).
Mechanism: every arm (fw "v11", incl. A16) publish time (anytime13.publishes) and its DONE leaf term
(steer14_donecal.leaves -> done_f = BETA * leaves * K + eps) are multiplied by K = 85.909088 / (601.362942 / 11).
The co-sim DONE residual eps is NOT scaled (a few frames, common to arm and reference).
  usage: steer14_pocket.py race ARM LAM SIZES LO CNT STEP OUT   (same as steer14_run.py race)"""
import os, runpy, sys
CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
K = float(os.environ.get("POCKET_K", 85.909088 / (601.362942 / 11)))
os.chdir(CVX); sys.path.insert(0, CVX)
import anytime13 as AT, steer14_donecal as DC
_pub, _lv = AT.publishes, DC.leaves
def publishes(roots, fw, coef, *a, **kw):
    out = _pub(roots, fw, coef, *a, **kw)
    return [(t * K, x) for t, x in out] if fw == "v11" else out
def leaves(roots, fw, *a, **kw):
    v = _lv(roots, fw, *a, **kw)
    return v * K if fw == "v11" else v
AT.publishes, DC.leaves = publishes, leaves
sys.argv = [os.path.join(CVX, "steer14_run.py")] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
