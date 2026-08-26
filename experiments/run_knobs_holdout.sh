#!/bin/bash
# Fresh-seed HOLDOUT of the DA re-screen winners (#86). Endpoints pre-registered in
# experiments/PREREG_KNOBS_HOLDOUT.md, committed BEFORE this ran.
# Interpreter is tmp/venv -- the SAME one the screen used, so the holdout is measured by
# the same instrument (a different rig would confound replication with rig disagreement).
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd /home/struktured/projects/dr-mario-qa-wt/experiments
echo "KNOBS-HOLDOUT START $(date -Is)"
$PY holdout_knobs.py --seeds 1000 --seed0 300000 --workers 6 \
    --out ../tmp/selfplay/holdout_knobs_20260809.jsonl
echo "KNOBS-HOLDOUT DONE $(date -Is) exit=$?"
