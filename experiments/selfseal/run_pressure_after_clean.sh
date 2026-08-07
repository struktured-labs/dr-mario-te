#!/bin/bash
# Launch the bursty-v1.1 pressure A/B as soon as the clean-stream run frees its
# workers, so the box never carries more than 4 of our workers at once.
cd /home/struktured/projects/dr-mario-qa-wt/experiments/selfseal
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
until command grep -q "^DONE" logs/clean_n200.log 2>/dev/null; do sleep 30; done
exec $PY seal_pressure.py --seeds 200 --workers 4 \
     --arms base,veto_seal,veto_noopen --out results/pressure_n200.json \
     > logs/pressure_n200.log 2>&1
