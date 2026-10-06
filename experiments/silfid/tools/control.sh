#!/bin/bash
S=/home/struktured/projects/dr_mario_rl/tmp/silfid
CF=/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics
for g in m1g1 m1g2 m1g4 m2g2 m2g3; do
  $S/tools/replay.sh ctl_${g}_D $g $CF/pubtrace_${g}_lulu_20261005.jsonl > $S/logs/ctl_$g.log 2>&1; echo "$(date +%T) ctl $g rc=$?"
done
echo "$(date +%T) CONTROL DONE"
