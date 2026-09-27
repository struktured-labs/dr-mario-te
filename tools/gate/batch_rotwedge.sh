#!/bin/bash
# Replication matrix for #132: does the match-start wedge track the published orient?
set -u
D=/home/struktured/projects/dr-mario-rotexec-wt
for s in 114 271 999; do
  for o in 0 1 2 3; do
    RW_SEED=$s "$D/tools/gate/run_rotwedge.sh" "$o" 12000 </dev/null 2>&1 | command grep -a "^SUMMARY\|MISMATCH\|FAILED"
  done
done
