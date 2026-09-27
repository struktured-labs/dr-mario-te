#!/bin/bash
set -u
cd /home/struktured/projects/dr-mario-qa-wt/experiments/eval47/stage2/rollout
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
mkdir -p out logs
# PRIMARY: lulu regime, N=3000 paired seeds 20000..22999
$PY run_ab.py --model lulu --term recommended --seed-start 20000 \
    --seed-count 3000 --workers 5 --out out/ab_lulu.jsonl >> logs/ab_lulu.log 2>&1
# SECONDARY: generic drip regime, N=1500 paired seeds 20000..21499
$PY run_ab.py --model drip --term recommended --seed-start 20000 \
    --seed-count 1500 --workers 5 --out out/ab_drip.jsonl >> logs/ab_drip.log 2>&1
echo "ALLDONE" >> logs/ab_lulu.log
