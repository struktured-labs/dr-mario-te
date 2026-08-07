#!/bin/bash
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd /home/struktured/projects/dr-mario-selfplay-wt/experiments/selfplay
while pgrep -f 'venv/bin/python -u stage1.py label' >/dev/null 2>&1; do sleep 30; done
{
  echo "=============== STAGE 1 RESULTS  $(date -Is) ==============="
  echo "labelled positions: $(wc -l < out/labels_main.jsonl)"
  echo
  $PY stage1.py analyze --labels out/labels_main.jsonl --json-out out/stage1.json
  echo
  echo "=============== 1d  DE-NOISED ORACLE GAIN ==============="
  $PY stage1_denoise.py --labels out/labels_main.jsonl --json-out out/denoise.json
  echo
  echo "=============== 1b  HEADROOM SPLIT ==============="
  $PY stage1_features.py extract --labels out/labels_main.jsonl \
      --corpus out/corpus.npz --out out/feats.npz && \
  $PY stage1_features.py fit --feats out/feats.npz \
      --labels out/labels_main.jsonl --corpus out/corpus.npz --folds 5
} > logs/stage1_results.txt 2>&1
echo "DONE $(date -Is)" >> logs/stage1_results.txt
