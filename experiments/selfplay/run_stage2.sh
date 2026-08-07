#!/bin/bash
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd /home/struktured/projects/dr-mario-selfplay-wt/experiments/selfplay
$PY -u stage2.py corpus --games 1200 --workers 4 --out out/s2_corpus.npz
$PY -u stage2.py label --corpus out/s2_corpus.npz --positions 3000 \
    --rollouts 8 --workers 4 --out out/s2_labels.jsonl
echo "STAGE2 LABELS DONE $(date -Is)"
