#!/bin/bash
set -u
S2=/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/stage2
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd "$S2"
# wait for the builder service to finish (systemd state, never pgrep)
while systemctl --user is-active --quiet s2corpus2; do sleep 20; done
echo "=== BUILDER EXITED: $(systemctl --user show s2corpus2 -p Result --value 2>/dev/null) ==="
journalctl --user -u s2corpus2 --no-pager -n 12 2>/dev/null | tail -12
if [ ! -f results/s2lulu_ctrl_local.npz ]; then echo "NO CORPUS WRITTEN"; exit 1; fi
echo "=== FEATURES + GATES A3/A4 ==="
$PY s2_features.py --tag local 2>&1
echo "=== CORPUS REPORT ==="
$PY s2_report.py --tag local 2>&1
echo "ALL_STAGES_COMPLETE"
