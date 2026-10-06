#!/bin/bash
S=/home/struktured/projects/dr_mario_rl/tmp/silfid
for g in m1g1 m1g2 m1g4 m2g2 m2g3; do $S/tools/replay.sh spu2_$g $g $S/timelines/spu2_$g.jsonl > $S/logs/spu2_$g.log 2>&1; echo "$(date +%T) spu2 $g rc=$?"; done
echo "$(date +%T) SPU DONE"
