#!/bin/bash
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd /home/struktured/projects/dr-mario-selfplay-wt/experiments/selfplay
while pgrep -f 'venv/bin/python -u scale_label.py' >/dev/null 2>&1; do sleep 60; done
sleep 10
$PY merge_2x.py out/labels_main.jsonl out/scale_labels.jsonl out/merged_2x.jsonl \
    > logs/merge_2x.log 2>&1
{
  echo "=== 2x RESULT $(date -Is) ==="
  cat logs/merge_2x.log
  echo
  $PY stage2_scale.py --se-d3delta 6.30
  echo
  $PY stage2_fit.py --labels out/merged_2x.jsonl --corpus out/corpus.npz
  echo "EXIT $?"
} > RESULT_2X.txt 2>&1
echo "2X DONE $(date -Is)" >> RESULT_2X.txt
