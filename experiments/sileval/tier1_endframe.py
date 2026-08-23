#!/usr/bin/env python3
"""tier1_endframe.py -- cheap screenshot classifier: "did a match just end?"

TIER 1 of the two-tier detector. Reads a 7.0 KB screenshot (vs 1,296 KB for a
save-state -- 184x cheaper) and answers a single yes/no. It only has to be
SENSITIVE: a false positive costs one save-state, a false negative loses a match.

FEATURE -- playfield occupancy SYMMETRY.  In VS play the two bottles diverge
(the losing side stacks up while the winner clears).  At a match boundary the
game regenerates BOTH bottles with the same virus count and fills them in
lockstep, so the two playfields carry near-identical occupancy: the on-screen
VIRUS counters read 02/02, 17/17, 35/35, 48/48 through the whole fill.
So |occ_P1 - occ_P2| ~ 0 marks a boundary and is large during play.

  MEASURED on population A (labels = the save-state mode of the same sample;
  positives = mode $03/$05/$07, n=128; negatives n=4,465):
      thr      sensitivity   FP     FP-rate   save-states per true hit
      0.0005      0.930      133     2.98%       2.12
      0.0100      0.961      371     8.31%       4.02
  Default threshold 0.0005.

*** SCOPE LIMIT -- READ BEFORE TRUSTING THIS ***
This detects the frame AFTER the ending (the regeneration), not the game-over
screen itself.  No game-over frame exists anywhere in the 4,593 banked
screenshots to train on, because sileval_ab.sh takes its screenshot AFTER
pull_state (which polls up to 12 s), so every banked PNG lags its save-state.
Consequently a tier-2 save-state fired from this signal arrives AFTER mode $07
has passed.  Use this to detect THAT a match ended (and how many), not to
capture the mode byte.  For the winner, prefer e1_winner.py, which reads
$031E/$039E -- counters the ROM writes before it changes the mode, and which
survive the transition entirely.

Self-test (regenerates the table above from the banked corpus):
    python3 tier1_endframe.py --gate [OUT_DIR]
"""
import sys
import numpy as np
from PIL import Image

P1_XY, P2_XY = (32, 72), (160, 72)     # playfield origins, 8 cols x 16 rows of 8x8 tiles
PF_W, PF_H = 64, 128
DEFAULT_THR = 0.0005


def occupancy(img):
    """Fraction of non-background pixels in each playfield, as (p1, p2)."""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    out = []
    for x, y in (P1_XY, P2_XY):
        f = a[y:y + PF_H, x:x + PF_W]
        bg = f[0, 0]                    # the top-left playfield cell is background at every mode
        out.append(float((np.abs(f - bg).sum(axis=2) > 40).mean()))
    return out


def is_end_frame(png_path, thr=DEFAULT_THR):
    o1, o2 = occupancy(Image.open(png_path))
    return abs(o1 - o2) <= thr, (o1, o2)


def _gate(out_dir):
    import glob, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import e1_winner as E
    pos, neg = [], []
    for d in sorted(glob.glob(os.path.join(out_dir, "artifacts", "*"))):
        hint = None
        for f in sorted(glob.glob(os.path.join(d, "s*.ss"))):
            png = f[:-3] + ".png"
            if not os.path.exists(png):
                continue
            blob = open(f, "rb").read()
            try:
                base = hint = E.find_base(blob, hint)
            except ValueError:
                continue
            o1, o2 = occupancy(Image.open(png))
            (pos if blob[base + E.MODE] in (3, 5, 7) else neg).append(abs(o1 - o2))
    print(f"positives={len(pos)}  negatives={len(neg)}")
    print(f"{'thr':>8} {'sens':>8} {'FP':>6} {'FPrate':>9} {'shots/hit':>10}")
    for thr in (0.0005, 0.001, 0.002, 0.005, 0.01, 0.02):
        tp = sum(1 for v in pos if v <= thr)
        fp = sum(1 for v in neg if v <= thr)
        print(f"{thr:8.4f} {tp/max(len(pos),1):8.3f} {fp:6d} {fp/max(len(neg),1):9.4f} "
              f"{(tp+fp)/max(tp,1):10.2f}")


if __name__ == "__main__":
    import os
    args = sys.argv[1:]
    if args and args[0] == "--gate":
        _gate(args[1] if len(args) > 1 else
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    else:
        for p in args:
            hit, (o1, o2) = is_end_frame(p)
            print(f"{p}\t{'END' if hit else 'play'}\tocc=({o1:.4f},{o2:.4f}) d={abs(o1-o2):.4f}")
