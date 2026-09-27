#!/bin/bash
set -u
cd /home/struktured/projects/dr-mario-qa-wt/experiments/eval47/stage2/rollout
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
# wait for the drip A/B to finish so the 6-worker cap is never exceeded
while pgrep -f "run_ab.py --model drip" > /dev/null; do sleep 20; done
$PY run_ctrl.py --model lulu --pairs out/ab_lulu.jsonl --workers 5 \
    --verify 25 --out out/ctrl_lulu_shuf.jsonl >> logs/ctrl_lulu.log 2>&1
echo CTRLDONE >> logs/ctrl_lulu.log
