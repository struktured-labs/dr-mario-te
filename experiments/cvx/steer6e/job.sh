#!/bin/bash
# one STEER6e job: NUMBADIR KIND ARM LO OUT
cd /home/struktured/projects/dr-mario-h16-wt/experiments/cvx
export NUMBA_CACHE_DIR=/home/struktured/projects/dr_mario_rl/tmp/dist60_20261003/$1
exec nice -n 19 /home/struktured/projects/dr_mario_rl/tmp/venv/bin/python steer6e_run.py $2 $3 $4 50 2 $5 > steer6e/logs/$(basename $5 .jsonl).log 2>&1
