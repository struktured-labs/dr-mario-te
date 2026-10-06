#!/bin/bash
# silfid H2: Mesen replays with every publish (and DONE) shifted by +1 / -1 frame, plus the STALE=1 GO-hook read variant.
S=/home/struktured/projects/dr_mario_rl/tmp/silfid
CF=/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics
for g in m1g1 m1g2 m1g4 m2g2 m2g3; do
  for d in 1 -1; do $S/tools/replay.sh shift${d}_${g} $g $S/timelines/shift${d}_$g.jsonl > $S/logs/shift${d}_$g.log 2>&1; echo "$(date +%T) shift$d $g rc=$?"; done
  $S/tools/replay.sh stale_${g} $g $CF/pubtrace_${g}_lulu_20261005.jsonl "" 1 > $S/logs/stale_$g.log 2>&1; echo "$(date +%T) stale $g rc=$?"
done
echo "$(date +%T) H2 DONE"
