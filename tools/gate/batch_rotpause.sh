#!/bin/bash
# Pause-hypothesis arms. Runs at the ONE configuration known to wedge (orient 3, seed 114)
# so `leak` is a positive control: if leak does not wedge the run is VOID, not a fix.
set -u
D=/home/struktured/projects/dr-mario-rotexec-wt
while pgrep -f 'Release/Mesen .*probe_rotwedge' >/dev/null; do sleep 20; done
for arm in leak fix poke; do
  RQ_SEED=114 "$D/tools/gate/run_rotpause.sh" 3 12000 "$arm" </dev/null 2>&1 | command grep -a "^SUMMARY\|MISMATCH\|FAILED"
done
