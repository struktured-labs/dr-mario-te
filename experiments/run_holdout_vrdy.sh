#!/bin/bash
# Sequential foreground children -- no pgrep, no pattern waiting.
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd /home/struktured/projects/dr-mario-qa-wt/experiments
echo "HOLDOUT START $(date -Is)"
$PY holdout.py --only vrdy=12,setup=48 --rule rom \
    --tune0 2000 --tune-n 160 --hold0 40000 --seeds 320 --workers 5 \
    --out ../tmp/selfplay/holdout_vrdy_20260807.jsonl
echo "HOLDOUT DONE $(date -Is) exit=$?"
