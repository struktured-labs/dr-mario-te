#!/bin/bash
# Sequential foreground children. NO pgrep, NO pidfile, NO pattern waiting --
# the shell's exit code does the waiting. (Three deadlocks today from the
# alternative; see harness-pgrep-self-match.)
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd /home/struktured/projects/dr-mario-qa-wt/experiments
echo "KNOBS-ROM START $(date -Is)"
$PY sweep_knobs.py --rule rom --seeds 160 --seed0 2000 --workers 6 \
    --out ../tmp/selfplay/screen_rom_20260807.jsonl
echo "KNOBS-ROM DONE $(date -Is) exit=$?"
