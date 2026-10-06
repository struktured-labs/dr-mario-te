#!/bin/bash
# silfid: co-sim the given pills under several tie-break seeds (env SEEDS, PILLS, OUT, J)
cd /home/struktured/projects/dr_mario_rl/tmp/silfid/an
for s in $SEEDS; do
  SEED=$s SPU_OFF=${SPU_OFF:-0} J=${J:-5} /home/struktured/projects/dr_mario_rl/tmp/venv/bin/python cosim.py $OUT $PILLS
  echo "$(date +%T) seed $s done"
done
echo "$(date +%T) SWEEP DONE"
