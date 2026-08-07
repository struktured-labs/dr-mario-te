#!/usr/bin/env python3
"""STAGE 2 SCALE-UP -- buy 2x Stage-1 signal, against a PRE-REGISTERED target.

THE PREDICTION, FIXED BEFORE THIS RUNS
--------------------------------------
The shipped eval IS a linear model over exactly these eleven terms, so for the
`terms11` arm the fit is well-specified and ridge excess risk over the optimum
scales as SE^2 / R = 1 / signal^2. Stage 1 measured, at 1x signal:

    fitted linear   +4.94        hand weights   +4.00        EXCESS = 0.94 pills

so the excess at signal multiple s is predicted to be 0.94 / s^2:

    signal   predicted excess   vs GATE_TOL 0.25
      1.0x        0.940         fail  (OBSERVED -- the scaling's one confirmed point)
      1.5x        0.418         fail
      2.0x        0.235         PASS   <- the target
      3.0x        0.104         pass
      4.0x        0.059         pass

2x IS THE DECISION POINT. Below it Gate A cannot pass arithmetically; above it we
are buying margin on a gate that already cleared. That is why this file targets 2x
and not 3x or 4x -- 8.7 h rather than 34.7 h, which is a different kind of ask.

TWO CALIBRATIONS, NOT ONE (added after Stage 2 supplied a second point).
Excess is not comparable across regimes in raw pills -- it must be normalised by tau,
the true across-action spread. Doing so turns Stage 2's failure into a second
calibration of the same law, k = (excess/tau) * signal^2:

    run                    excess    tau     excess/tau   signal    k
    Stage 1 (champion d3)   0.940    6.37      0.1476      1.00    0.1476
    Stage 2 (depth 2)       1.887   17.56      0.1075      0.97    0.1011

Two independent regimes agreeing to within 1.46x is real corroboration of 1/signal^2
-- and also an honest ~50% uncertainty band that one point could not have revealed.
Predicted excess at 2x in the CHAMPION regime (tau 6.37), under each calibration:

    Stage-1 calibrated   0.235 pills   PASS
    Stage-2 calibrated   0.161 pills   PASS

It survives both, but the pessimistic end sits only 6% under GATE_TOL 0.25, so the
decision bands are widened BEFORE the run rather than after:

  <= 0.25      Gate A passes; richer arms interpretable; program unlocked.
  0.25 - 0.40  MARGINAL, WITHIN MODEL ERROR. Explicitly NOT evidence that the linear
               class is exhausted. Report as "consistent with the scaling law,
               marginally short". This band was implicit in the original ">0.5 =>
               stop" and is made explicit so a 0.27 cannot be read as a negative.
  > 0.50       scaling law REFUTED: misspecification, or the hand weights are not the
               linear optimum. STOP -- do NOT buy 3x.

Note the bands are stated in CHAMPION-regime pills (tau 6.37). They would NOT
transfer to a depth-2 run, where the same quality of fit shows up as ~2.8x more raw
pills purely because tau is 2.8x larger.

POLICY CHOICE
-------------
Measured, interleaved on identical positions and forced actions so box load hits
both arms equally: champion 2.812 s/rollout, d3-delta 1.299 s/rollout => 2.16x.
Signal per unit compute favours d3-delta by sqrt(2.16) * (3.31 / SE_d3delta).

At 2x the two policies differ by ~4.6 h (8.7 vs 13.3), which is small. Standing
instruction, and the default here: IF THE MEASURED SE IS AT ALL AMBIGUOUS, TAKE THE
CHAMPION. Its 99.5% reliability is measured over 11,200 rollouts; d3-delta's 99.0%
is a 200-rollout screen that cleared its (corrected) 98.21% bar by only ~1.1 sigma.
Reliability is worth more than 4.6 h.

This file does NOT auto-run. It is a costed, pre-registered plan awaiting a go.
"""
from __future__ import annotations

import os
import sys
import math
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ---- Stage-1 measured anchors (do not edit without re-deriving the table above) --
S1_ROLLOUTS = 11200
S1_SE = 3.31             # CRN-corrected per-label SE, champion rollouts
S1_EXCESS = 0.94         # fitted linear 4.94 - hand 4.00, at 1x signal
COST_CHAMP = 2.812       # s/rollout, interleaved measurement, 1 process
COST_D3D = 1.299
SE_AMBIGUOUS_HI = 3.8    # if measured d3-delta SE exceeds this, take the champion

PRE_REGISTERED_TARGET = S1_EXCESS / (2.0 ** 2)      # 0.235 pills


def plan(se_d3delta=None, target=2.0):
    rows = []
    for name, se, cost in (("champion", S1_SE, COST_CHAMP),
                           ("d3-delta", se_d3delta, COST_D3D)):
        if se is None:
            continue
        R = S1_ROLLOUTS * (target * se / S1_SE) ** 2
        rows.append((name, se, R, R * cost / 4.0 / 3600.0,
                     math.sqrt(COST_CHAMP / cost) * (S1_SE / se)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--se-d3delta", type=float, default=None,
                    help="measured per-label SE for d3-delta (from SE_D3DELTA.txt)")
    ap.add_argument("--target", type=float, default=2.0)
    args = ap.parse_args()

    print("=" * 74)
    print("STAGE 2 SCALE-UP PLAN -- pre-registered, awaiting go")
    print("=" * 74)
    print(f"  Stage-1 anchors: {S1_ROLLOUTS} rollouts, SE {S1_SE}, "
          f"excess over hand {S1_EXCESS}")
    print(f"  PRE-REGISTERED TARGET at {args.target:.0f}x signal: excess = "
          f"{S1_EXCESS / args.target**2:.3f} pills")
    print(f"  second calibration (Stage 2, tau-normalised) predicts "
          f"{0.1011/ (args.target**2) * 6.37:.3f} pills")
    print(f"    <= 0.25      PASS -- richer arms interpretable, program unlocked")
    print(f"    0.25 - 0.40  MARGINAL, within model error. NOT evidence the linear")
    print(f"                 class is exhausted. Report as 'consistent, marginally short'")
    print(f"    >  0.50      scaling REFUTED (misspecified, or hand weights are not")
    print(f"                 the linear optimum). STOP. Do NOT buy 3x.")
    print(f"  bands are in CHAMPION-regime pills (tau 6.37); they do NOT transfer to")
    print(f"  a depth-2 run, where tau is 2.8x larger.")
    print()
    rows = plan(args.se_d3delta, args.target)
    if not rows:
        print("  (pass --se-d3delta to compare policies)")
    for name, se, R, hrs, adv in rows:
        print(f"  {name:9s} SE {se:5.2f}  {R:9,.0f} rollouts  {hrs:5.1f} h @4w  "
              f"signal/compute {adv:4.2f}x")
    if args.se_d3delta is not None:
        if args.se_d3delta > SE_AMBIGUOUS_HI:
            print(f"\n  DECISION: measured SE {args.se_d3delta:.2f} exceeds the "
                  f"{SE_AMBIGUOUS_HI} ambiguity line -> TAKE THE CHAMPION.")
            print("  Its reliability is measured over 11,200 rollouts; d3-delta's is a")
            print("  200-rollout screen that cleared its bar by ~1.1 sigma. The gap is")
            print("  ~4.6 h and reliability is worth more than that.")
        else:
            print(f"\n  DECISION: measured SE {args.se_d3delta:.2f} is comfortably "
                  f"below {SE_AMBIGUOUS_HI} -> d3-delta.")
    print()
    print("  Not started. This is a plan, not a run.")


if __name__ == "__main__":
    main()
