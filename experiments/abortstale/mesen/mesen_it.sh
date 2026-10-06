#!/bin/bash
# Mesen re-runs of the A cart on regenerated (chained-co-sim) case files. Honours the PAUSE file between runs.
O=/home/struktured/projects/dr_mario_rl/tmp/abort_stale
CA=$O/carts/drmario_te_couch_fair_abort_b1b57638.nes
for spec in "$@"; do          # TAG:CASES.lua
  tag=${spec%%:*}; cases=${spec#*:}
  while [ -e $O/PAUSE ]; do sleep 10; done
  timeout 5400 $O/tools/lateflip/run_lateflip.sh $tag $CA $cases 20000 0 2>&1 | tail -1
done
echo MESEN_IT_DONE
