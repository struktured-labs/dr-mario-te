#!/bin/bash
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd /home/struktured/projects/dr-mario-selfplay-wt/experiments/selfplay
# wait for the Stage-2 labeller AND the fit chain to finish before contending
while :; do
  n=$(wc -l < out/s2_labels.jsonl 2>/dev/null || echo 0)
  done_fit=0; [ -f STAGE2_RESULTS.txt ] && grep -q "STAGE2 DONE" STAGE2_RESULTS.txt && done_fit=1
  if [ "$n" -ge 2900 ] && [ "$done_fit" = "1" ]; then break; fi
  [ ! -d /proc/3583692 ] && [ "$done_fit" = "1" ] && break
  sleep 60
done
$PY measure_se_d3delta.py 60 > SE_D3DELTA.txt 2>&1
echo "SE MEASURE DONE $(date -Is)" >> SE_D3DELTA.txt
