#!/bin/bash
# diag_freeze.sh -- reproduction attempt for the two mid-play freezes.
#
# NOT population B. Seeds 48757 and 45431 froze mid-play on the SHIP arm on the
# NEW box (one virus state, one LFSR value, zero matches across a full 360 s
# cycle) while the SLICE arm of the SAME seed in the SAME session played
# normally. This re-runs both seeds on BOTH arms, at the registered 360s/20s
# cycle so conditions match the original rows as closely as the host allows.
#
# ⚠ This is a DIFFERENT BOX (old, Main 2024-05-07) than the one that froze
# (new, Main 260707), so it CANNOT satisfy prereg rule 5(a) as written.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SILEVAL_LIB_ONLY=1 . "$HERE/sileval_ab.sh"
for seed in 48757 45431; do
  for arm in ship slice; do
    note "DIAG seed=$seed arm=$arm"
    run_arm "$seed" "$arm"
  done
done
